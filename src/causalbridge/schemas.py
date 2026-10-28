"""Versioned runtime contracts. Oracle metadata is deliberately absent."""

from __future__ import annotations

import hashlib
import itertools
import json
from typing import Annotated, Literal

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, model_validator

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Probability = Annotated[float, Field(strict=True, gt=0, lt=1, allow_inf_nan=False)]
QuestionType = Literal[
    "reachability",
    "effect_direction",
    "effect_magnitude",
    "intervention_probability",
    "adjustment_validity",
]
Operation = Literal[
    "has_directed_path",
    "compute_effect",
    "compute_intervention",
    "is_valid_adjustment_set",
    "backdoor_adjustment",
]
Answer = StrictBool | StrictFloat | Literal["positive", "negative", "zero"] | None


class Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, hide_input_in_errors=True
    )


class Assumptions(Record):
    correct_dag: StrictBool
    fully_observed: StrictBool
    independent_noise: StrictBool
    positivity: StrictBool

    def satisfied(self) -> bool:
        return all(self.model_dump().values())


def bit_keys(size: int) -> set[str]:
    return {"".join(bits) for bits in itertools.product("01", repeat=size)}


class CPT(Record):
    node: str
    parents: tuple[str, ...] = ()
    p_one: dict[str, Probability]

    @model_validator(mode="after")
    def validate_rows(self):
        if len(set(self.parents)) != len(self.parents):
            raise ValueError("CPT parents must be unique")
        if set(self.p_one) != bit_keys(len(self.parents)):
            raise ValueError("CPT must have one p_one entry per parent assignment")
        return self


class JointDistribution(Record):
    variables: tuple[str, ...]
    probabilities: dict[str, Probability]

    @model_validator(mode="after")
    def validate_distribution(self):
        if not self.variables or len(set(self.variables)) != len(self.variables):
            raise ValueError("Joint variables must be nonempty and unique")
        if set(self.probabilities) != bit_keys(len(self.variables)):
            raise ValueError("Joint must enumerate every binary assignment")
        if abs(sum(self.probabilities.values()) - 1.0) > 1e-9:
            raise ValueError("Joint probabilities must sum to one")
        return self


class RuntimeCase(Record):
    schema_version: Literal["1.0"] = "1.0"
    case_id: str = Field(min_length=1)
    graph_group_id: str | None = None
    graph_nodes: tuple[str, ...]
    graph_edges: tuple[tuple[str, str], ...]
    question: str = Field(min_length=1)
    evidence_level: str | None = None
    visible_cpts: tuple[CPT, ...] = ()
    visible_joint: JointDistribution | None = None
    assumptions: Assumptions | None = None

    @model_validator(mode="after")
    def validate_graph_evidence(self):
        nodes = set(self.graph_nodes)
        if not nodes or len(nodes) != len(self.graph_nodes) or any(not n.strip() for n in nodes):
            raise ValueError("Graph nodes must be nonempty, named and unique")
        if any(a not in nodes or b not in nodes for a, b in self.graph_edges):
            raise ValueError("Every edge endpoint must be listed in graph_nodes")
        graph = self.graph()
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Graph must be a DAG")
        if len({c.node for c in self.visible_cpts}) != len(self.visible_cpts):
            raise ValueError("Duplicate CPT node")
        for cpt in self.visible_cpts:
            if cpt.node not in nodes or set(cpt.parents) != set(graph.predecessors(cpt.node)):
                raise ValueError("CPT parents must match the supplied graph")
        if self.visible_joint and not set(self.visible_joint.variables) <= nodes:
            raise ValueError("Joint references an unknown variable")
        return self

    def graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_nodes_from(self.graph_nodes)
        graph.add_edges_from(self.graph_edges)
        return graph

    def evidence_digest(self) -> str:
        payload = self.model_dump(mode="json")
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @classmethod
    def from_benchmark(cls, raw: dict) -> RuntimeCase:
        """Project a dataset row onto the visible allowlist, then validate it.

        Producers must identify visible evidence correctly. This cannot detect
        oracle parameters deliberately mislabeled as visible by a caller.
        """
        if not isinstance(raw, dict):
            raise ValueError("Benchmark row must be a JSON object")
        visible = {k: v for k, v in raw.items() if k in cls.model_fields}
        if visible.get("visible_cpts") is None:
            visible["visible_cpts"] = ()
        if "graph_nodes" not in visible:
            visible["graph_nodes"] = sorted({n for e in visible.get("graph_edges", []) for n in e})
        return cls.model_validate(visible)


class Query(Record):
    cause: str
    outcome: str
    question_type: QuestionType
    from_value: Literal[0, 1] = 0
    to_value: Literal[0, 1] = 1
    intervention_value: Literal[0, 1] = 1
    adjustment_set: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def reject_bool_values(cls, data):
        if isinstance(data, dict):
            for name in ("from_value", "to_value", "intervention_value"):
                if name in data and type(data[name]) is not int:
                    raise ValueError("Binary intervention values must be integers, not booleans")
        return data

    @model_validator(mode="after")
    def validate_roles(self):
        if self.cause == self.outcome:
            raise ValueError("Cause and outcome must differ")
        if self.from_value == self.to_value:
            raise ValueError("Effect contrast must compare different treatment values")
        if len(set(self.adjustment_set)) != len(self.adjustment_set):
            raise ValueError("Adjustment set must not repeat variables")
        if {self.cause, self.outcome} & set(self.adjustment_set):
            raise ValueError("Adjustment variables cannot include cause or outcome")
        return self

    def bind(self, case: RuntimeCase) -> None:
        if not {self.cause, self.outcome, *self.adjustment_set} <= set(case.graph_nodes):
            raise ValueError("Query refers to unknown graph variables")


class Proposal(Record):
    query: Query
    requested_operation: Operation
    proposed_tool: Operation
    proposed_answer: Answer = None
    response_action: Literal["answer", "abstain"] = "answer"


class ToolRequest(Record):
    operation: Operation
    query: Query
    evidence_digest: str


class ToolResult(Record):
    request: ToolRequest
    value: StrictBool | StrictFloat | None = None
    error: str | None = None


class Verdict(Record):
    status: Literal["verified", "unsupported", "wrong_operation", "execution_error"]
    response_action: Literal["answer", "abstain"]
    reason_code: str
    explanation: str
    answer: Answer = None
    missing_evidence: tuple[str, ...] = ()
