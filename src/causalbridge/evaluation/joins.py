"""Evaluator-only reference joins after inference; never a runtime dependency."""

from typing import Annotated

from pydantic import Field, StrictInt, model_validator

from causalbridge.discovery.contracts import Digest as SourceDigest
from causalbridge.discovery.evidence import digest, rng
from causalbridge.discovery.schemas import Digest, canonical_digest
from causalbridge.evaluation.handoff import (
    validate_analysis_handoff,
    validate_loader_handoff,
)
from causalbridge.schemas import Record


class EvaluatorMapping(Record):
    """Existing evaluator_mapping export; order lists original columns at A/B."""

    case_id: str = Field(pattern=r"^D[0-9]{4,}$")
    ab_mapping_id: Digest
    original_to_runtime_column_order: tuple[StrictInt, StrictInt]
    mapping_seed: Annotated[StrictInt, Field(ge=0)]
    source_digest: SourceDigest

    @model_validator(mode="after")
    def valid_permutation(self):
        if sorted(self.original_to_runtime_column_order) != [0, 1]:
            raise ValueError("Mapping must be a permutation of original columns 0 and 1")
        return self


def join_evaluator_records(rows, mappings, runtime_records, evaluator_records, *, expected_slots):
    """Join exact case/mapping identities; retain every scheduled nonanswer.

    Runtime records are the independently retained original-order handoff, not
    reconstructed from mapped evidence. Reference labels never choose the order.
    Returns new private dictionaries; original label-free exports stay untouched.
    This establishes agreement with supplied references, not causal truth.
    """
    runtime, evaluator = validate_loader_handoff(runtime_records, evaluator_records)
    records = validate_analysis_handoff(rows, expected_slots=expected_slots)
    mapping_records = tuple(
        EvaluatorMapping.model_validate(m.model_dump() if isinstance(m, EvaluatorMapping) else m)
        for m in mappings
    )
    by_case = {m.case_id: m for m in mapping_records}
    cases = {r.case_id for r in runtime}
    if len(by_case) != len(mapping_records) or set(by_case) != cases:
        raise ValueError("Mappings must have exactly one record per runtime case")
    if {r.case_id for r in records} != cases:
        raise ValueError("Analysis/runtime case sets differ")
    for pair in runtime:
        mapping = by_case[pair.case_id]
        order = mapping.original_to_runtime_column_order
        expected_order = (
            (1, 0) if rng(mapping.mapping_seed, pair.case_id, "mapping").getrandbits(1) else (0, 1)
        )
        if order != expected_order or mapping.source_digest != digest(pair.model_dump()):
            raise ValueError("Mapping does not match retained original runtime data/seed")
        expected_id = canonical_digest(
            {"case_id": pair.case_id, "order": order, "seed": mapping.mapping_seed}
        )
        if mapping.ab_mapping_id != expected_id:
            raise ValueError("Mapping ID does not bind its original column order and seed")
    parents = {}
    attempt_ids = set()
    for row in records:
        if row.ab_mapping_id != by_case[row.case_id].ab_mapping_id:
            raise ValueError("Analysis row references a different A/B mapping")
        if row.condition in {"S0", "S1"}:
            if row.attempt_id is None or row.attempt_id in attempt_ids:
                raise ValueError("Primary attempt IDs must be present and unique")
            attempt_ids.add(row.attempt_id)
        if row.condition == "S1":
            parents[(row.manifest_id, row.case_id, row.package)] = row
    labels = {r.case_id: r for r in evaluator}
    joined = []
    for row in records:
        if row.condition in {"S2", "SIMPLE_GATE"}:
            parent = parents.get((row.manifest_id, row.case_id, row.package))
            if parent is None or row.parent_attempt_id != parent.attempt_id:
                raise ValueError("Derived row does not join its exact S1 parent")
            if row.package_digest != parent.package_digest or row.run_id != parent.run_id:
                raise ValueError("Derived row does not bind its parent's package and run")
            if row.predicted_direction is not None and (
                not parent.prediction_scorable
                or parent.failure_stage is not None
                or row.predicted_direction != parent.predicted_direction
            ):
                raise ValueError("Derived row cannot invent or reverse its parent answer")
        label = labels[row.case_id]
        order = by_case[row.case_id].original_to_runtime_column_order
        reference = "A_to_B" if order[0] == label.cause_column else "B_to_A"
        joined.append(
            row.model_dump(mode="json")
            | dict(
                evaluator_join_version="track-b-evaluator-join-v1",
                reference_direction=reference,
                reference_agreement=None
                if row.predicted_direction is None
                else row.predicted_direction == reference,
                weight=label.weight,
                source_group=label.source_group,
                split=label.split,
            )
        )
    return tuple(joined)
