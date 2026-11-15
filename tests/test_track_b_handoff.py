"""Adversarial acceptance checks at external data and scorer boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_native_integration_runner import NativeModel, configuration, selected_pair

from causalbridge.discovery.contracts import SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.export import analysis_rows
from causalbridge.evaluation.handoff import validate_analysis_handoff, validate_loader_handoff
from causalbridge.evaluation.integration import IntegratedRunner, build_native_packages, condition
from causalbridge.llm.predictor import direction_messages


@pytest.fixture
def loader():
    return json.loads((Path(__file__).parent / "fixtures/track_b_handoff/loader.json").read_text())


def accept(loader):
    return validate_loader_handoff(loader["runtime"], loader["evaluator"])


def test_fixture_roundtrip_and_runtime_separation(loader):
    before = deepcopy(loader)
    runtime, evaluator = accept(loader)
    assert len(runtime) == len(evaluator) == 2
    assert loader == before
    assert json.loads(runtime[0].model_dump_json()) == loader["runtime"][0]  # units provided
    selected = select_pair(runtime[0], SelectionSpec())
    assert selected.selection.source_digest
    assert "weight" not in runtime[0].model_dump()


@pytest.mark.parametrize(
    "field",
    ["cause_column", "reference_direction", "source_group", "weight", "split", "original_pair_id"],
)
def test_private_fields_rejected_at_runtime_boundary(loader, field):
    loader["runtime"][0][field] = "PRIVATE_SENTINEL"
    with pytest.raises(ValidationError):
        accept(loader)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), True, "2.0", None])
def test_invalid_weights(loader, value):
    loader["evaluator"][0]["weight"] = value
    with pytest.raises(ValidationError):
        accept(loader)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate_runtime",
        "duplicate_evaluator",
        "missing_evaluator",
        "extra_evaluator",
        "group_overlap",
        "empty",
        "bad_split",
        "bad_column",
        "boolean_column",
    ],
)
def test_incomplete_or_inconsistent_loader_handoff(loader, fault):
    if fault == "duplicate_runtime":
        loader["runtime"].append(deepcopy(loader["runtime"][0]))
    elif fault == "duplicate_evaluator":
        loader["evaluator"].append(deepcopy(loader["evaluator"][0]))
    elif fault == "missing_evaluator":
        loader["evaluator"].pop()
    elif fault == "extra_evaluator":
        loader["evaluator"].append(loader["evaluator"][0] | {"case_id": "D9999"})
    elif fault == "group_overlap":
        loader["evaluator"][1]["source_group"] = loader["evaluator"][0]["source_group"]
    elif fault == "empty":
        loader["runtime"].clear()
        loader["evaluator"].clear()
    elif fault == "bad_split":
        loader["evaluator"][0]["split"] = "heldout_typo"
    else:
        loader["evaluator"][0]["cause_column"] = True if fault == "boolean_column" else 2
    with pytest.raises(ValueError):
        accept(loader)


@pytest.mark.parametrize(
    "fault", ["nonfinite", "missing_rows", "third_column", "missing_id", "nested_private"]
)
def test_malformed_runtime_records(loader, fault):
    r = loader["runtime"][0]
    if fault == "nonfinite":
        r["rows"][0][0] = float("nan")
    elif fault == "missing_rows":
        r.pop("rows")
    elif fault == "third_column":
        r["rows"][0].append(4.0)
    elif fault == "missing_id":
        r.pop("case_id")
    else:
        r["variables"][0]["source_description"] = "PRIVATE_SENTINEL"
    with pytest.raises(ValidationError):
        accept(loader)


@pytest.fixture(params=["timeout", "honest", "abstain", "malformed", "misbound", "unavailable_row"])
def exported(tmp_path, request):
    packages = build_native_packages(selected_pair(), tmp_path / "anm", configuration())
    runner = IntegratedRunner(
        tmp_path / "run",
        model_identity="fixture",
        model_mode="scripted_fixture",
        observation_kind="synthetic",
    )
    run = runner.run(packages, NativeModel(request.param))
    rows = analysis_rows(run, runner.replay_s2(run["manifest_id"]))
    # Planned matrix is independent of what the exporter happened to retain.
    schedule = {
        (run["manifest_id"], "D0001", p, c)
        for p in ("E1", "E2", "E3", "E4")
        for c in ("S0", "S1", "S2", "SIMPLE_GATE")
    }
    schedule.add((run["manifest_id"], "D0001", "E4", "ANM_ONLY"))
    return rows, schedule


def test_export_acceptance_keeps_all_scheduled_slots(exported):
    rows, schedule = exported
    accepted = validate_analysis_handoff(rows, expected_slots=schedule)
    assert len(accepted) == 17
    primaries = [r for r in accepted if r.condition in {"S0", "S1"}]
    assert len(primaries) == 8
    for primary in primaries:
        if primary.outcome == "prediction_failure":
            assert primary.predicted_direction is None and primary.failure_stage is not None
    assert len([r for r in accepted if r.condition == "S2"]) == 4


@pytest.mark.parametrize(
    "fault",
    [
        "missing_failure",
        "duplicate",
        "extra_slot",
        "private_label",
        "invalid_direction",
        "missing_identity",
        "negative_tokens",
        "boolean_tokens",
        "unknown_field",
    ],
)
def test_bad_analysis_handoffs(exported, fault):
    rows, schedule = deepcopy(exported)
    if fault == "missing_failure":
        rows.pop(0)
    elif fault == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif fault == "extra_slot":
        rows.append(rows[0] | {"case_id": "D9999"})
    elif fault == "private_label":
        rows[0]["causal_correctness"] = True
    elif fault == "invalid_direction":
        rows[0]["predicted_direction"] = "positive"
    elif fault == "missing_identity":
        rows[0].pop("ab_mapping_id")
    elif fault in {"negative_tokens", "boolean_tokens"}:
        rows[0]["input_tokens"] = True if fault == "boolean_tokens" else -1
    else:
        rows[0]["reference_direction"] = "A_to_B"
    with pytest.raises(ValueError):
        validate_analysis_handoff(rows, expected_slots=schedule)


def test_private_sentinels_never_enter_native_messages(loader, tmp_path):
    runtime, evaluator = accept(loader)
    selected = select_pair(runtime[0])
    packages = build_native_packages(selected, tmp_path / "anm", configuration())
    for p in packages:
        for name in ("S0", "S1"):
            text = json.dumps(direction_messages(p.evidence, condition(name)))
            assert all(r.source_group not in text for r in evaluator)
            assert "cause_column" not in text and "weight" not in text
    request = (Path(packages[-1].method_directory) / "request.json").read_text()
    assert "private-family-sentinel" not in request
    assert "cause_column" not in request


@pytest.mark.parametrize(
    "fault",
    [
        "failed_arrow",
        "truncated_scorable",
        "s2_disagreement",
        "s2_rejected_release",
        "missing_parent",
    ],
)
def test_contradictory_analysis_states(exported, fault):
    rows, schedule = deepcopy(exported)
    if fault == "failed_arrow":
        rows[0].update(failure_stage="generate", predicted_direction="A_to_B")
    elif fault == "truncated_scorable":
        rows[0].update(prediction_scorable=True, generation_status="truncated")
    else:
        row = next(r for r in rows if r["condition"] == "S2")
        if fault == "s2_disagreement":
            row.update(predicted_direction="A_to_B", released_direction="B_to_A")
        elif fault == "s2_rejected_release":
            row.update(outcome="fail", predicted_direction="A_to_B", released_direction="A_to_B")
        else:
            row["parent_attempt_id"] = None
    with pytest.raises(ValueError):
        validate_analysis_handoff(rows, expected_slots=schedule)


def test_model_instance_bypass_is_revalidated(loader):
    runtime, evaluator = accept(loader)
    corrupt = evaluator[0].model_copy(update={"weight": -1.0})
    with pytest.raises(ValidationError):
        validate_loader_handoff(runtime, [corrupt, evaluator[1]])


@pytest.mark.parametrize(
    "field,value",
    [
        ("prediction_scorable", False),
        ("prediction_binding", "invalid_or_unavailable"),
        ("outcome", "prediction_failure"),
    ],
)
def test_primary_usability_cannot_be_contradictory(exported, field, value):
    from causalbridge.evaluation.handoff import AnalysisHandoff

    rows, _ = exported
    row = deepcopy(rows[0])
    row.update(
        failure_stage=None,
        prediction_scorable=True,
        prediction_binding="valid",
        generation_status="complete",
        predicted_direction="A_to_B",
        outcome="answer",
    )
    row[field] = value
    with pytest.raises(ValueError):
        AnalysisHandoff.model_validate(row)


def test_method_generation_not_applicable_is_accepted(exported):
    from causalbridge.evaluation.handoff import AnalysisHandoff

    rows, _ = exported
    row = deepcopy(next(r for r in rows if r["condition"] == "ANM_ONLY"))
    row["generation_status"] = "not_applicable"
    assert AnalysisHandoff.model_validate(row).generation_status == "not_applicable"


def test_model_generation_not_applicable_is_rejected(exported):
    from causalbridge.evaluation.handoff import AnalysisHandoff

    rows, _ = exported
    row = deepcopy(rows[0])
    row["generation_status"] = "not_applicable"
    with pytest.raises(ValueError, match="Only ANM-only"):
        AnalysisHandoff.model_validate(row)
