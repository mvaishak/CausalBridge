"""Corrupt real native exports before scoring; never create fresh model replies."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from causalbridge.evaluation.acceptance_demo import run_acceptance
from causalbridge.evaluation.scoring import score_pilot


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    output = tmp_path_factory.mktemp("lineage") / "acceptance"
    run_acceptance(output, Path(__file__).parent / "fixtures/track_b_scoring")
    rows = json.loads((output / "analysis.json").read_text())
    mappings = json.loads((output / "mappings.json").read_text())
    metadata = json.loads((output / "evaluator.json").read_text())
    by_case = {m["case_id"]: m for m in mappings}
    evaluator = [
        dict(
            case_id=e["case_id"],
            source_group=e["source_group"],
            weight=e["weight"],
            reference_direction="first_to_second" if e["cause_column"] == 0 else "second_to_first",
            source_digest=by_case[e["case_id"]]["source_digest"],
        )
        for e in metadata
    ]
    return rows, evaluator, mappings


@pytest.mark.parametrize("condition", ["S2", "SIMPLE_GATE"])
@pytest.mark.parametrize(
    "fault",
    [
        "wrong_parent",
        "missing_parent",
        "missing_parent_row",
        "different_manifest",
        "different_package",
        "different_run",
        "different_attempt",
        "missing_run",
        "reversed_arrow",
        "answer_after_failure",
        "answer_after_abstention",
        "rejected_answer",
    ],
)
def test_corrupt_derived_lineage_is_rejected(exported, condition, fault):
    rows, evaluator, mappings = deepcopy(exported)
    case = (
        "D0206"
        if fault == "answer_after_failure"
        else ("D0205" if fault == "answer_after_abstention" else "D0201")
    )
    row = next(
        r
        for r in rows
        if r["case_id"] == case and r["package"] == "E2" and r["condition"] == condition
    )
    if fault == "wrong_parent":
        row["parent_attempt_id"] = "nonexistent-parent"
    elif fault == "missing_parent":
        row.pop("parent_attempt_id")
    elif fault == "missing_parent_row":
        rows = [
            r
            for r in rows
            if not (r["case_id"] == case and r["package"] == "E2" and r["condition"] == "S1")
        ]
    elif fault == "different_manifest":
        row["manifest_id"] = "other-manifest"
    elif fault == "different_package":
        row["package_digest"] = "sha256:" + "ab" * 32
    elif fault == "different_run":
        row["run_id"] = "other-run"
    elif fault == "different_attempt":
        row["attempt_id"] = "other-attempt"
    elif fault == "missing_run":
        row.pop("run_id")
    elif fault in {"reversed_arrow", "answer_after_failure", "answer_after_abstention"}:
        row.update(
            predicted_direction="B_to_A" if fault == "reversed_arrow" else "A_to_B",
            released_direction="B_to_A" if fault == "reversed_arrow" else "A_to_B",
            outcome="pass" if condition == "S2" else "gate_pass",
            prediction_scorable=True,
        )
    else:
        row["outcome"] = "fail" if condition == "S2" else "method_unavailable_or_unconfigured"
    with pytest.raises(ValueError):
        score_pilot(rows, evaluator, mappings)


def test_valid_native_exports_retain_fixed_denominators(exported):
    rows, evaluator, mappings = deepcopy(exported)
    before = deepcopy(rows)
    scores = score_pilot(rows, evaluator, mappings)
    assert len(scores) == 17 and rows == before
    assert all(s["total_weight"] == 16 and s["case_count"] == 8 for s in scores)
    s1 = next(s for s in scores if s["package"] == "E4" and s["condition"] == "S1")
    s2 = next(s for s in scores if s["package"] == "E4" and s["condition"] == "S2")
    assert s1["correct_yield"] == 5 / 16 and s2["correct_yield"] == 2 / 16
