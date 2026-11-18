"""Local acceptance boundaries, not dataset ingestion, eligibility or scoring.

External loaders adapt to RuntimePair plus a separate evaluator-only record.
The evaluator field names are provisional until the data owner accepts them.
"""

from collections.abc import Iterable, Mapping
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from causalbridge.discovery.contracts import RuntimePair
from causalbridge.discovery.schemas import Digest, Direction
from causalbridge.schemas import Record

PositiveWeight = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Count = Annotated[StrictInt, Field(ge=0)]
Nonempty = Annotated[StrictStr, Field(min_length=1)]


class EvaluatorHandoff(Record):
    """Private metadata: cause_column refers to original loader column order."""

    case_id: str = Field(pattern=r"^D[0-9]{4,}$")
    source_group: Nonempty
    weight: PositiveWeight
    split: Literal["pilot", "development", "test"]
    cause_column: Annotated[StrictInt, Field(ge=0, le=1)]


def validate_loader_handoff(runtime_records, evaluator_records):
    """Reject incomplete/duplicate handoffs; never merge labels into runtime data.

    Validates structure and group disjointness only. Names/units must already be
    sanitized by the owner; arbitrary text cannot be certified safe by a schema.
    """
    runtime = tuple(
        RuntimePair.model_validate(r.model_dump() if isinstance(r, RuntimePair) else r)
        for r in runtime_records
    )
    evaluator = tuple(
        EvaluatorHandoff.model_validate(r.model_dump() if isinstance(r, EvaluatorHandoff) else r)
        for r in evaluator_records
    )
    runtime_ids = [r.case_id for r in runtime]
    evaluator_ids = [r.case_id for r in evaluator]
    if not runtime or len(set(runtime_ids)) != len(runtime_ids):
        raise ValueError("Runtime handoff must be nonempty with unique case IDs")
    if len(set(evaluator_ids)) != len(evaluator_ids):
        raise ValueError("Duplicate evaluator case IDs")
    if set(runtime_ids) != set(evaluator_ids):
        raise ValueError("Runtime/evaluator case sets differ")
    group_splits = {}
    for record in evaluator:
        if group_splits.setdefault(record.source_group, record.split) != record.split:
            raise ValueError("One source group occurs in multiple splits")
    return runtime, evaluator


class AnalysisHandoff(Record):
    """Strict label-free native-analysis-v2 consumer shape; no score computation."""

    export_version: Literal["native-analysis-v2"]
    manifest_id: Nonempty
    case_id: str = Field(pattern=r"^D[0-9]{4,}$")
    package: Literal["E1", "E2", "E3", "E4"]
    condition: Literal["S0", "S1", "S2", "SIMPLE_GATE", "ANM_ONLY"]
    ab_mapping_id: Nonempty
    package_digest: Digest
    attempt_id: Nonempty | None
    run_id: Nonempty | None
    parent_attempt_id: Nonempty | None
    model_identity: Nonempty | None
    model_mode: Nonempty
    observation_kind: Literal["unspecified", "synthetic", "real_observational"]
    prediction_binding: Literal["valid", "invalid_or_unavailable"]
    prediction_scorable: StrictBool
    generation_status: Literal[
        "complete", "truncated", "incomplete", "unavailable", "not_applicable"
    ]
    generation_failure_reason: Nonempty | None
    supplied_claim_count: Count | None
    supporting_claims_status: Literal["not_checked", "no_supporting_claims_supplied", "checked"]
    checked_claim_count: Count
    released_direction: Direction | None
    predicted_direction: Direction | None
    causal_correctness: None
    causal_correctness_status: Literal["requires_separate_evaluator_labels"]
    protocol: Nonempty
    failure_stage: Nonempty | None
    input_tokens: Count | None
    output_tokens: Count | None
    outcome: Nonempty
    reason_codes: tuple[Nonempty, ...]
    checker_version: Nonempty | None = None
    method_config_digest: Digest | None = None

    @model_validator(mode="after")
    def release_invariants(self):
        if self.generation_status == "not_applicable" and self.condition != "ANM_ONLY":
            raise ValueError("Only ANM-only rows may declare generation not applicable")
        if self.condition in {"S0", "S1"}:
            usable = self.failure_stage is None
            if self.prediction_scorable != usable or self.prediction_binding != (
                "valid" if usable else "invalid_or_unavailable"
            ):
                raise ValueError("Primary usability must match its failure and binding state")
            expected_outcome = (
                "prediction_failure"
                if not usable
                else "model_abstention"
                if self.predicted_direction is None
                else "answer"
            )
            if self.outcome != expected_outcome:
                raise ValueError("Primary outcome contradicts its answer/failure state")
            if self.failure_stage is not None and self.predicted_direction is not None:
                raise ValueError("Failed prediction cannot supply a directional answer")
            if self.prediction_scorable and self.generation_status != "complete":
                raise ValueError("Incomplete generation cannot be scorable")
        if self.condition == "S2":
            if self.released_direction != self.predicted_direction:
                raise ValueError("S2 answer must equal its recorded release")
            if self.released_direction is not None and self.outcome != "pass":
                raise ValueError("Only a passing S2 outcome can release")
        if self.condition in {"S2", "SIMPLE_GATE"} and self.parent_attempt_id is None:
            raise ValueError("Derived condition requires a parent attempt")
        if self.condition == "ANM_ONLY" and self.package != "E4":
            raise ValueError("ANM-only baseline requires E4")
        return self


def validate_analysis_handoff(
    rows: Iterable[Mapping], *, expected_slots: set[tuple[str, str, str, str]]
) -> tuple[AnalysisHandoff, ...]:
    """Require exactly the caller's scheduled (manifest, case, package, condition).

    Never infer completeness from supplied rows: that would hide missing failures.
    Schedule includes baseline slots and must come from the execution plan.
    Orientation/label joins and metric interpretation are separate acceptance gates.
    """
    records = tuple(AnalysisHandoff.model_validate(r) for r in rows)
    slots = [(r.manifest_id, r.case_id, r.package, r.condition) for r in records]
    if not expected_slots or len(slots) != len(set(slots)):
        raise ValueError("Expected nonempty schedule and unique analysis slots")
    if set(slots) != expected_slots:
        raise ValueError("Analysis rows differ from the scheduled slots")
    return records
