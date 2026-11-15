"""Independent direction truth table and adversarial evaluator-only joins."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_native_integration_runner import NativeModel, configuration

from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.export import analysis_rows, evaluator_mapping
from causalbridge.evaluation.integration import IntegratedRunner, build_native_packages, condition
from causalbridge.evaluation.joins import join_evaluator_records
from causalbridge.llm.predictor import direction_messages


@pytest.fixture
def bundle(tmp_path):
    return make_bundle(tmp_path)


def make_bundle(tmp_path, seed=0, cause=0, behavior="honest", case_id="D0101"):
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/track_b_handoff/loader.json").read_text()
    )
    runtime = [fixture["runtime"][0] | {"case_id": case_id}]
    evaluator = [fixture["evaluator"][0] | {"cause_column": cause, "case_id": case_id}]
    selected = select_pair(RuntimePair.model_validate(runtime[0]), SelectionSpec(mapping_seed=seed))
    packages = build_native_packages(selected, tmp_path / "anm", configuration())
    runner = IntegratedRunner(
        tmp_path / "experiment",
        model_identity="fixture",
        model_mode="scripted_fixture",
        observation_kind="synthetic",
    )
    run = runner.run(packages, NativeModel(behavior))
    rows = analysis_rows(run, runner.replay_s2(run["manifest_id"]))
    schedule = {
        (run["manifest_id"], case_id, p, c)
        for p in ("E1", "E2", "E3", "E4")
        for c in ("S0", "S1", "S2", "SIMPLE_GATE")
    }
    schedule.add((run["manifest_id"], case_id, "E4", "ANM_ONLY"))
    return dict(
        rows=rows,
        mappings=evaluator_mapping(packages),
        runtime_records=runtime,
        evaluator_records=evaluator,
        expected_slots=schedule,
    ), packages


def join(bundle):
    return join_evaluator_records(**bundle[0])


@pytest.mark.parametrize(
    "seed,cause,order,reference",
    [
        (0, 0, (0, 1), "A_to_B"),
        (0, 1, (0, 1), "B_to_A"),
        (1, 0, (1, 0), "B_to_A"),
        (1, 1, (1, 0), "A_to_B"),
    ],
)
def test_four_reference_orientation_cases(tmp_path, seed, cause, order, reference):
    data, packages = make_bundle(tmp_path, seed=seed, cause=cause)
    before = deepcopy(data)
    assert tuple(data["mappings"][0]["original_to_runtime_column_order"]) == order
    original_rows = data["runtime_records"][0]["rows"]
    for p in packages:
        assert tuple(p.selected.selection.column_order) == order
        if p.evidence.package != "E1":
            assert p.evidence.display_rows == tuple(
                tuple(row[i] for i in order) for row in original_rows
            )
    result = join_evaluator_records(**data)
    assert len(result) == 17 and data == before
    assert {r["reference_direction"] for r in result} == {reference}
    for row in result:
        expected = None if row["predicted_direction"] is None else reference == "A_to_B"
        assert row["reference_agreement"] is expected
        assert row["weight"] == 2.0
        assert row["causal_correctness"] is None


def test_reference_label_never_changes_execution_or_mapping(bundle):
    data, packages = bundle
    messages = [
        direction_messages(p.evidence, condition(c)) for p in packages for c in ("S0", "S1")
    ]
    original = join(bundle)
    changed = deepcopy(data)
    changed["evaluator_records"][0]["cause_column"] = 1
    updated = join_evaluator_records(**changed)
    assert all(
        a["reference_direction"] != b["reference_direction"]
        for a, b in zip(original, updated, strict=True)
    )
    assert data["rows"] == changed["rows"] and data["mappings"] == changed["mappings"]
    assert messages == [
        direction_messages(p.evidence, condition(c)) for p in packages for c in ("S0", "S1")
    ]
    assert "private-family-sentinel" not in json.dumps(messages)
    assert "cause_column" not in json.dumps(messages)


@pytest.mark.parametrize("behavior", ["timeout", "malformed", "misbound", "abstain"])
def test_nonanswers_retained_with_null_agreement(tmp_path, behavior):
    bundle = make_bundle(tmp_path, behavior=behavior)
    result = join(bundle)
    assert len(result) == 17
    assert all(r["reference_agreement"] is None for r in result)
    assert all(r["weight"] == 2.0 for r in result)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "missing",
        "extra",
        "bad_order",
        "bool_order",
        "wrong_digest",
        "wrong_id",
        "swapped_order",
        "wrong_seed",
        "wrong_runtime",
        "row_mapping",
        "row_case",
        "missing_label",
        "duplicate_label",
        "borrowed_parent",
        "invented_arrow",
        "duplicate_attempt",
    ],
)
def test_corrupt_joins_rejected(bundle, fault):
    data = deepcopy(bundle[0])
    m = data["mappings"][0]
    if fault == "duplicate":
        data["mappings"].append(deepcopy(m))
    elif fault == "missing":
        data["mappings"].clear()
    elif fault == "extra":
        data["mappings"].append(m | {"case_id": "D9999"})
    elif fault in {"bad_order", "bool_order"}:
        m["original_to_runtime_column_order"] = [0, 0] if fault == "bad_order" else [False, True]
    elif fault == "wrong_digest":
        m["source_digest"] = "f" * 64
    elif fault == "wrong_id":
        m["ab_mapping_id"] = "sha256:" + "f" * 64
    elif fault == "swapped_order":
        m["original_to_runtime_column_order"] = [1, 0]
        m["ab_mapping_id"] = canonical_digest({"case_id": "D0101", "order": [1, 0], "seed": 0})
        for row in data["rows"]:
            row["ab_mapping_id"] = m["ab_mapping_id"]
    elif fault == "wrong_seed":
        m["mapping_seed"] = 1
    elif fault == "wrong_runtime":
        data["runtime_records"][0]["rows"][0][0] += 1.0
    elif fault == "row_mapping":
        data["rows"][0]["ab_mapping_id"] = "sha256:" + "f" * 64
    elif fault == "row_case":
        data["rows"][0]["case_id"] = "D9999"
    elif fault == "missing_label":
        data["evaluator_records"].clear()
    elif fault == "duplicate_label":
        data["evaluator_records"].append(deepcopy(data["evaluator_records"][0]))
    elif fault == "borrowed_parent":
        parent = next(r for r in data["rows"] if r["package"] == "E2" and r["condition"] == "S1")
        next(r for r in data["rows"] if r["condition"] == "S2")["parent_attempt_id"] = parent[
            "attempt_id"
        ]
    elif fault == "invented_arrow":
        next(r for r in data["rows"] if r["condition"] == "SIMPLE_GATE")["predicted_direction"] = (
            "B_to_A"
        )
    else:
        primaries = [r for r in data["rows"] if r["condition"] in {"S0", "S1"}]
        primaries[1]["attempt_id"] = primaries[0]["attempt_id"]
    with pytest.raises(ValueError):
        join_evaluator_records(**data)


def test_row_and_mapping_order_do_not_control_join(bundle):
    data = deepcopy(bundle[0])
    data["rows"].reverse()
    result = join_evaluator_records(**data)
    assert {r["reference_direction"] for r in result} == {"A_to_B"}
    assert [r["condition"] for r in result] == [r["condition"] for r in data["rows"]]


def test_two_cases_join_by_identity_not_position(tmp_path):
    first, _ = make_bundle(tmp_path / "first")
    second, _ = make_bundle(tmp_path / "second", seed=1, cause=1, case_id="D0102")
    second["evaluator_records"][0].update(weight=7.0, source_group="another-private-family")
    combined = dict(
        rows=second["rows"] + first["rows"],
        mappings=first["mappings"] + second["mappings"],
        runtime_records=second["runtime_records"] + first["runtime_records"],
        evaluator_records=first["evaluator_records"] + second["evaluator_records"],
        expected_slots=first["expected_slots"] | second["expected_slots"],
    )
    result = join_evaluator_records(**combined)
    assert len(result) == 34
    assert all(r["weight"] == (2.0 if r["case_id"] == "D0101" else 7.0) for r in result)
    assert all(
        r["source_group"] == "another-private-family" for r in result if r["case_id"] == "D0102"
    )


@pytest.mark.parametrize("field", ["package_digest", "run_id"])
def test_derived_row_binds_parent_content(bundle, field):
    data = deepcopy(bundle[0])
    row = next(r for r in data["rows"] if r["condition"] == "S2")
    row[field] = "wrong-run" if field == "run_id" else "sha256:" + "a" * 64
    with pytest.raises(ValueError, match="parent's package and run"):
        join_evaluator_records(**data)
