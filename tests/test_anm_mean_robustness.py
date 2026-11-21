"""Mean robustness fitting and result replay regression tests."""

from pathlib import Path

import numpy as np
import pytest

from causalbridge.evaluation.anm_failure_audit import read
from causalbridge.evaluation.anm_mean_robustness import CONFIG, predict, report


def test_local_linear_reproduces_line_including_extrapolation():
    x = np.linspace(-2, 2, 80)
    evaluation = np.array([-4.0, -0.3, 0.7, 4.0])
    result = predict(x, 3 * x + 2, evaluation, {"kind": "local_linear", "bandwidth": 0.5})
    assert result == pytest.approx(3 * evaluation + 2, abs=1e-10)


def test_krr_matches_explicit_training_only_solution():
    x = np.linspace(-2, 2, 20)
    y = np.sin(x)
    z = np.array([-0.7, 0.3])
    spec = {"kind": "krr", "gamma": 4.0, "ridge": 0.1}
    coefficients = np.linalg.solve(np.exp(-4 * (x[:, None] - x) ** 2) + 0.1 * np.eye(20), y)
    assert predict(x, y, z, spec) == pytest.approx(
        np.exp(-4 * (z[:, None] - x) ** 2) @ coefficients
    )


def test_degenerate_local_linear_is_explicit_failure():
    with pytest.raises(ValueError, match="Rank-deficient"):
        predict(
            np.ones(10),
            np.arange(10.0),
            np.array([1.0]),
            {"kind": "local_linear", "bandwidth": 0.5},
        )


def test_protocol_has_all_correct_comparisons_and_no_model_selection():
    cfg = read(CONFIG)
    assert cfg["comparison_pairs"] == [2, 3, 13, 16, 23, 86]
    assert cfg["target_pairs"] == [56, 88]
    assert len(cfg["estimators"]) == 4


def test_saved_report_replay_never_refits(monkeypatch, tmp_path):
    import causalbridge.evaluation.anm_mean_robustness as module

    def forbidden(*args, **kwargs):
        raise AssertionError("Report replay must not fit")

    monkeypatch.setattr(module, "predict", forbidden)
    plan = "artifacts/anm-mean-robustness-20261121"
    if not Path(plan, "records.json").exists():
        pytest.skip("New diagnostic artifacts not present")
    report(plan, tmp_path / "table.md")
    assert (tmp_path / "table.md").read_bytes() == Path(plan, "tables.md").read_bytes()


def test_all_configurations_retained_and_candidates_survive_checks():
    rows = read("artifacts/anm-mean-robustness-20261121/records.json")
    assert len(rows) == 96
    real = [r for r in rows if r["kind"] == "real"]
    assert len(real) == 32
    for pair in (56, 88):
        selected = [r for r in real if r["pair_id"] == pair]
        assert len(selected) == 4
        for record in selected:
            for mode in ("raw", "mean_detrended"):
                for scheme in ("iid", "saved_order_blocks"):
                    assert record["modes"][mode][scheme]["holm_pvalue_nominal"] <= 0.05
    assert all(r["n_eval"] == 64 for r in real)
