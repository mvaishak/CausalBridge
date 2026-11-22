"""Policy mechanics, denominator preservation, and deterministic opened-data replay."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from causalbridge.evaluation.anm_adequacy_comparison import (
    CONFIG,
    adequacy,
    apply_policy,
    calculate,
    execute,
    prepare,
    summarize,
)
from causalbridge.evaluation.anm_failure_audit import read, write


def checks(a, b):
    return {d: {"iid": {"pvalue_nominal": p}} for d, p in [("A_to_B", a), ("B_to_A", b)]}


@pytest.mark.parametrize("direction", ["A_to_B", "B_to_A"])
def test_rules_separate_both_rejected_from_unique_nonrejection(direction):
    both = adequacy(checks(0.001, 0.002), "iid", 0.025)
    neither = adequacy(checks(0.4, 0.5), "iid", 0.025)
    selected_only = adequacy(
        checks(0.001, 0.5) if direction == "A_to_B" else checks(0.5, 0.001), "iid", 0.025
    )
    opposite_only = adequacy(
        checks(0.5, 0.001) if direction == "A_to_B" else checks(0.001, 0.5), "iid", 0.025
    )
    assert apply_policy(direction, both, "original")[0] == direction
    assert apply_policy(direction, both, "warning_only")[0] == direction
    assert apply_policy(direction, both, "withhold_if_both_rejected")[0] is None
    assert apply_policy(direction, selected_only, "withhold_if_both_rejected")[0] == direction
    assert apply_policy(direction, selected_only, "withhold_if_selected_rejected")[0] is None
    assert apply_policy(direction, opposite_only, "require_unique_nonrejected")[0] == direction
    assert apply_policy(direction, neither, "require_unique_nonrejected")[0] is None


def test_unavailable_is_never_imputed_as_nonrejection_and_boundary_is_closed():
    missing = adequacy(checks(None, 0.8), "iid", 0.025)
    assert missing["status"] == "unavailable"
    assert apply_policy("A_to_B", missing, "warning_only")[0] == "A_to_B"
    assert apply_policy("A_to_B", missing, "withhold_if_both_rejected") == (
        None,
        "diagnostic_unavailable",
    )
    assert adequacy(checks(0.025, 0.026), "iid", 0.025)["rejected"] == {
        "A_to_B": True,
        "B_to_A": False,
    }


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -0.01, 1.01, True, "0.01"])
def test_invalid_p_values_fail_instead_of_becoming_evidence(invalid):
    with pytest.raises(ValueError, match="p-value"):
        adequacy(checks(invalid, 0.1), "iid", 0.025)


def test_real_replay_is_label_blind_and_only_withholds():
    inputs = read("artifacts/anm-adequacy-policy-comparison-20261121/inputs.json")
    cfg = read(CONFIG)
    rows, _ = calculate(inputs, cfg)
    changed = deepcopy(inputs)
    for row in changed:
        row["reference"] = "B_to_A" if row["reference"] == "A_to_B" else "A_to_B"
    other, _ = calculate(changed, cfg)
    assert [r["policy_direction"] for r in rows] == [r["policy_direction"] for r in other]
    assert all(r["policy_direction"] in (None, r["original_direction"]) for r in rows)
    for row in rows:
        if row["original_direction"] is None:
            assert row["policy_direction"] is None


def test_execution_failure_is_not_converted_to_abstention():
    original = deepcopy(read("artifacts/anm-adequacy-policy-comparison-20261121/inputs.json")[0])
    original.update(original_direction=None, original_outcome="execution_failure")
    cfg = read(CONFIG)
    rows, _ = calculate([original], {**cfg, "panels": {original["panel"]: 1}})
    assert all(r["policy_outcome"] == "execution_failure" for r in rows)
    metrics = summarize(rows)
    assert metrics["counts"]["abstention"] == 0
    assert metrics["execution_failure_rate"]["rate"] == 1
    assert metrics["directional_accuracy"]["rate"] is None


def test_preparation_execution_and_replay_need_no_fits_or_permutations(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No numerical fits/permutations in saved-policy replay")

    monkeypatch.setattr(np.linalg, "solve", forbidden)
    monkeypatch.setattr(np.linalg, "eigh", forbidden)
    from causalbridge.evaluation import anm_decision_audit

    monkeypatch.setattr(anm_decision_audit, "permutation_checks", forbidden)
    plan = tmp_path / "plan"
    prepare(plan)
    output = tmp_path / "output"
    execute(plan, output)
    replay = tmp_path / "replay"
    execute(plan, replay, replay=True)
    for name in ["case-results.json", "metrics.json", "tables.md"]:
        assert (output / name).read_bytes() == (replay / name).read_bytes()
    with pytest.raises(FileExistsError):
        execute(plan, output)
    inputs = read(plan / "inputs.json")
    inputs[0]["weight"] += 1
    write(plan / "inputs.json", inputs)
    with pytest.raises(ValueError, match="inputs changed"):
        execute(plan, tmp_path / "tampered", replay=True)


def test_saved_counts_do_not_hide_coverage_loss_or_original_abstentions():
    root = Path("artifacts/anm-adequacy-policy-comparison-20261121")
    metrics = read(root / "metrics.json")
    assert len(read(root / "case-results.json")) == 550
    assert len(metrics["tables"]) == 20
    for t in metrics["tables"]:
        assert sum(t["counts"].values()) == t["n"]
        assert t["correct_yield"]["denominator"] == t["n"]
        assert (
            t["counts"]["abstention"] == t["original_abstentions"] + t["added_policy_abstentions"]
        )
        assert (
            t["added_policy_abstentions"] == t["wrong_answers_removed"] + t["correct_answers_lost"]
        )
    iid = next(
        t
        for t in metrics["tables"]
        if t["panel"] == "validation38"
        and t["scheme"] == "iid"
        and t["policy"] == "withhold_if_both_rejected"
    )
    assert iid["counts"] == {"correct": 6, "wrong": 8, "abstention": 24, "execution_failure": 0}
    strict = next(
        t
        for t in metrics["tables"]
        if t["panel"] == "validation38"
        and t["scheme"] == "saved_order_blocks"
        and t["policy"] == "require_unique_nonrejected"
    )
    assert strict["counts"] == {"correct": 9, "wrong": 1, "abstention": 28, "execution_failure": 0}
    assert strict["coverage"]["numerator"] == 10 and strict["coverage"]["denominator"] == 38
