"""Test spread-diagnostic mechanics and cautionary controls without fitting ANM."""

import numpy as np
import pytest

from causalbridge.evaluation.anm_failure_audit import read
from causalbridge.evaluation.anm_real_noise import (
    CONFIG,
    detrend,
    diagnose_vectors,
    group_data,
    holm,
    prepare,
    spread_checks,
    validate_plan,
)


def small_config():
    return {**read(CONFIG), "permutations": 99, "permutation_batch": 32}


def test_holm_missing_slots_and_ties():
    assert holm([0.001, 0.02, 0.9, None]) == [0.004, 0.06, 1.0, None]
    assert holm([None, None]) == [None, None]
    assert holm([0.01, 0.01]) == [0.02, 0.02]


def test_empty_cause_bins_are_unavailable_not_negative():
    cfg = small_config()
    training = np.repeat([0.0, 1.0, 2.0], [80, 10, 10])
    test = np.repeat([0.0, 1.0, 2.0], [40, 5, 5])
    result = spread_checks(training, test, np.arange(50.0), cfg, "ties")
    for check in result.values():
        assert check["status"] == "unavailable" and "pvalue_nominal" not in check


def test_spread_contrast_and_mean_shift_invariance():
    rng = np.random.default_rng(902)
    training = np.linspace(-2, 2, 240)
    cause = np.linspace(-2, 2, 240)
    residual = rng.normal(size=240) * np.repeat([1.0, 1.0, 5.0], 80)
    cfg = small_config()
    before = spread_checks(training, cause, residual, cfg, "fixture")
    shifted = residual + np.repeat([-10.0, 0.0, 8.0], 80)
    after = spread_checks(training, cause, shifted, cfg, "fixture")
    assert before["iid"]["pvalue_nominal"] == after["iid"]["pvalue_nominal"]
    assert before["iid"]["statistic_eta2"] == pytest.approx(after["iid"]["statistic_eta2"])
    assert before["iid"]["pvalue_nominal"] <= 0.05
    assert before == spread_checks(training, cause, residual, cfg, "fixture")


def test_crossfit_removes_exact_quadratic_mean_without_in_sample_leakage():
    x = np.linspace(-2, 2, 100)
    residual = 2 + 3 * x + 0.5 * x * x
    corrected = detrend(x, residual, small_config(), "quadratic")
    assert np.max(np.abs(corrected)) < 1e-12
    damaged = residual.copy()
    damaged[0] += 10
    new = detrend(x, damaged, small_config(), "quadratic")
    # Its own held-out observation cannot change its fitted correction.
    assert new[0] - corrected[0] == pytest.approx(10)


def test_rank_deficiency_is_reported_separately():
    cfg = small_config()
    xt = np.linspace(-2, 2, 100)
    x = np.tile([0.0, 1.0], 50)
    r = np.arange(100.0) % 7
    result = diagnose_vectors(xt, x, r, cfg, "two values")
    assert result["modes"]["mean_detrended"]["iid"]["status"] == "unavailable"
    assert "rank_deficient" in result["modes"]["mean_detrended"]["iid"]["reason"]


def test_between_group_statistic_matches_manual_median_deviations():
    cfg = {**small_config(), "minimum_bin_count": 2}
    xt = np.arange(12.0)
    x = np.arange(12.0)
    r = np.array([1, 2, 1, 2, 3, 5, 3, 5, 1, 9, 1, 9], dtype=float)
    prepared, _ = group_data(xt, x, r, cfg)
    groups, counts, z, total = prepared
    between = sum(counts[g] * (z[groups == g].mean() - z.mean()) ** 2 for g in range(3))
    got = spread_checks(xt, x, r, cfg, "manual")["iid"]
    assert got["statistic_eta2"] == pytest.approx(between / total)
    assert got["pvalue_nominal"] == (got["exceedances"] + 1) / 100


def test_prepare_freezes_all_real_originals_without_numeric_reconstruction(tmp_path, monkeypatch):
    def no_fits(*args, **kwargs):
        raise AssertionError("Preparation must not fit or diagnose data")

    monkeypatch.setattr(np.linalg, "solve", no_fits)
    plan = tmp_path / "plan"
    manifest = prepare(plan)
    assert len(manifest["real"]) == 131 and len(manifest["controls"]) == 72
    assert len({r["record_id"] for r in manifest["real"]}) == 131
    assert sum(r["panel"] == "pilot17" for r in manifest["real"]) == 17
    validate_plan(plan)
    name = next(iter(manifest["original_files_sha256"]))
    p = plan / name
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="Original ANM"):
        validate_plan(plan)


def frozen_records():
    import json
    from pathlib import Path

    from causalbridge.evaluation.anm_failure_audit import verified_archive

    root = Path("artifacts/anm-real-noise-20261121")
    files = verified_archive(root / "run-records.tar.gz", root / "manifest.json")
    return (
        files,
        json.loads(files["analysis/real-records.json"]),
        json.loads(files["analysis/calibration-records.json"]),
    )


def test_archived_real_results_keep_both_panels_and_original_outcomes():
    from collections import Counter

    _, rows, _ = frozen_records()
    assert len(rows) == 262
    for panel, expected in [
        ("pilot17", {"correct": 6, "wrong": 8, "abstention": 3}),
        ("validation38", {"correct": 13, "wrong": 13, "abstention": 12}),
    ]:
        selected = [
            r
            for r in rows
            if r["panel"] == panel
            and r["split_seed"] == 261
            and r["direction_tested"] == r["reference"]
        ]
        assert Counter(r["original_outcome"] for r in selected) == expected
    selected = [
        r for r in rows if r["panel"] == "pilot17" and r["direction_tested"] == r["reference"]
    ]
    flagged = [
        r["pair_id"]
        for r in selected
        if r["modes"]["mean_detrended"]["saved_order_blocks"]["flag_holm_nominal"]
    ]
    assert sorted(flagged) == [56, 88]
    assert all(r["original_outcome"] == "wrong" for r in selected if r["pair_id"] in flagged)


def test_archived_calibration_exposes_mean_error_false_attribution():
    _, _, controls = frozen_records()
    assert len(controls) == 72 and len({r["world_id"] for r in controls}) == 24
    for mode, expected in [("raw", 22), ("mean_detrended", 0)]:
        checks = [
            r["modes"][mode]["iid"]
            for r in controls
            if r["label"] == "constant_noise_quadratic_mean_error"
        ]
        assert sum(c["pvalue_nominal"] <= 0.05 for c in checks) == expected
    for mode in ("raw", "mean_detrended"):
        checks = [r["modes"][mode]["iid"] for r in controls if r["label"] == "heteroscedastic"]
        assert sum(c["pvalue_nominal"] <= 0.05 for c in checks) == 24


def test_frozen_fit_reconstruction_matches_original_hsic(tmp_path):
    import json

    from causalbridge.evaluation.anm_real_noise import reconstruct

    files, _, _ = frozen_records()
    manifest = json.loads(files["plan/manifest.json"])
    record = next(r for r in manifest["real"] if r["panel"] == "pilot17" and r["pair_id"] == 56)
    prefix = "plan/" + record["directory"] + "/"
    directory = tmp_path / "original"
    directory.mkdir()
    for name, data in files.items():
        if name.startswith(prefix):
            (directory / name.removeprefix(prefix)).write_bytes(data)
    vectors, result = reconstruct(directory)
    assert vectors["A_to_B"][3] == pytest.approx(result.score_ab, abs=1e-12)
    assert vectors["B_to_A"][3] == pytest.approx(result.score_ba, abs=1e-12)
    assert result.predicted_direction == record["original_direction"]
