"""Strict JSON parsing and versioned, inspectable prompts."""

import json
from typing import TypeVar

from causalbridge.schemas import Proposal, Query, Record, RuntimeCase, ToolResult

PROMPT_VERSION = "1.0"
T = TypeVar("T", bound=Record)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json[T: Record](text: str, model: type[T]) -> T:
    if len(text) > 64_000:
        raise ValueError("Structured response exceeds 64000 characters")
    payload = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(payload, dict):
        raise ValueError("Expected one JSON object")
    return model.model_validate(payload)


def messages(system: str, payload: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ]


def query_messages(case: RuntimeCase) -> list[dict[str, str]]:
    return messages(
        "Extract the causal query as JSON matching the supplied schema. Preserve exact node names, "
        "cause/outcome, intervention versus observation, and treatment direction. "
        "For increases use from_value=0,to_value=1; for decreases use from_value=1,to_value=0. "
        "A probability query is P(outcome=1|do(cause=intervention_value)). "
        "Direction/magnitude queries ask about the signed "
        "difference P(Y=1|do(X=to_value))-P(Y=1|do(X=from_value)). Do not translate a conditional "
        "effect or individual counterfactual into a supported population query. If unsupported, "
        "return the actual unsupported question_type; validation will abstain. Return JSON only.",
        {
            "question": case.question,
            "graph_nodes": case.graph_nodes,
            "graph_edges": case.graph_edges,
        },
    )


def plan_messages(case: RuntimeCase, query: Query) -> list[dict[str, str]]:
    return messages(
        "Plan one causal tool call as JSON matching the supplied Proposal schema. Copy the query "
        "exactly. requested_operation names the operation the QUESTION requires; proposed_tool is "
        "your chosen runtime operation. Available tools: has_directed_path returns only a bool; "
        "compute_effect returns the signed to-minus-from contrast from complete visible CPTs; "
        "compute_intervention returns P(Y=1|do(X=x)) from complete visible CPTs; "
        "is_valid_adjustment_set checks the backdoor criterion; backdoor_adjustment computes "
        "P(Y=1|do(X=x)) using a valid adjustment_set and a visible joint over X,Y,Z. "
        "An empty adjustment set permits observational substitution only if graph-valid. "
        "A directed path alone does not determine sign; no directed path implies zero total "
        "effect under stated assumptions. Use null for proposed_answer until the tool has run. "
        "Use response_action=abstain when you choose to abstain. Do not invent probabilities.",
        {"runtime_case": case.model_dump(mode="json"), "query": query.model_dump(mode="json")},
    )


def interpretation_messages(case: RuntimeCase, plan: Proposal, result: ToolResult):
    return messages(
        "Interpret the actual tool result as JSON matching the supplied Proposal schema. Copy "
        "query, requested_operation and proposed_tool exactly from the plan; only proposed_answer "
        "and response_action may change. Use true/false for structural queries, a JSON floating "
        "number for magnitude or intervention probability, and positive/negative/zero for effect "
        "direction. Effect direction is the sign of the specified to-minus-from contrast. "
        "A positive path result alone cannot establish effect sign or magnitude. Abstain if the "
        "tool does not justify the requested answer. Return JSON only.",
        {
            "runtime_case": case.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "tool_result": result.model_dump(mode="json"),
        },
    )
