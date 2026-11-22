"""Independent ANM mathematical references and saved audit evidence."""

from pathlib import Path

import numpy as np
import pytest

from causalbridge.discovery.anm import _hsic
from causalbridge.evaluation.anm_decision_audit import (
    CONFIG,
    permutation_checks,
    reference_fit,
    reference_kernel,
    report,
)
from causalbridge.evaluation.anm_failure_audit import read


def test_hsic_independent_formula_and_affine_row_invariance():
    rng = np.random.default_rng(719)
    x, y = rng.normal(size=(2, 55))
    expected = np.trace(reference_kernel(x) @ reference_kernel(y)) / len(x) ** 2
    assert _hsic(x, y)[0] == pytest.approx(expected, abs=1e-14)
    order = rng.permutation(len(x))
    assert _hsic(x[order], y[order])[0] == pytest.approx(expected, abs=1e-14)
    assert _hsic(3 * x + 7, -2 * y - 9)[0] == pytest.approx(expected, abs=1e-14)


def test_eigen_reference_matches_normal_equation_solution():
    rng = np.random.default_rng(718)
    train = rng.normal(size=(64, 2))
    test = rng.normal(size=(40, 2))
    score, _, _, error = reference_fit(train, test, 1.0, 0.1)
    kernel = np.exp(-(np.subtract.outer(train[:, 0], train[:, 0]) ** 2))
    coefficients = np.linalg.solve(kernel + 0.1 * np.eye(len(train)), train[:, 1])
    prediction = np.exp(-(np.subtract.outer(test[:, 0], train[:, 0]) ** 2)) @ coefficients
    assert score == pytest.approx(_hsic(test[:, 0], test[:, 1] - prediction)[0], abs=1e-12)
    assert error < 1e-10


def test_permutation_is_plus_one_and_reproducible():
    x = np.linspace(-2, 2, 64)
    k = reference_kernel(x)
    cfg = {**read(CONFIG), "permutations": 99}
    checks = permutation_checks(k, k, cfg, "fixture")
    assert checks == permutation_checks(k, k, cfg, "fixture")
    for value in checks.values():
        assert value["pvalue_nominal"] == (value["exceedances"] + 1) / 100
        assert value["rejected_pair_bonferroni"]


def test_saved_tables_replay_without_fitting(monkeypatch, tmp_path):
    import causalbridge.evaluation.anm_decision_audit as module

    def forbidden(*args, **kwargs):
        raise AssertionError("No fitting or permutations during table replay")

    monkeypatch.setattr(module, "reference_fit", forbidden)
    monkeypatch.setattr(module, "permutation_checks", forbidden)
    root = Path("artifacts/anm-decision-audit-20261121")
    assert (root / "records.json").exists()
    report(root, tmp_path / "tables.md")
    assert (tmp_path / "tables.md").read_bytes() == (root / "tables.md").read_bytes()


def test_frozen_reference_decisions_and_distinct_real_failure_patterns():
    rows = read("artifacts/anm-decision-audit-20261121/records.json")
    assert len(rows) == 55
    assert all(r["reference_decision_matches"] for r in rows)
    assert (
        max(d["relative_normal_equation_error"] for r in rows for d in r["directions"].values())
        < 1e-10
    )
    targets = {r["pair_id"]: r for r in rows if r["panel"] == "pilot17"}
    both = targets[88]["directions"]
    assert all(d["iid"]["rejected_pair_bonferroni"] for d in both.values())
    case = targets[56]
    assert case["directions"][case["reference"]]["iid"]["rejected_pair_bonferroni"]
    assert not case["directions"][case["original_direction"]]["iid"]["rejected_pair_bonferroni"]
