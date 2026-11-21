"""Component-study controls and independent score checks, not performance targets."""

import json

import numpy as np
import pytest

from causalbridge.evaluation.anm_failure_audit import read
from causalbridge.evaluation.anm_mechanism_analysis import analyze
from causalbridge.evaluation.anm_mechanism_study import (
    CONFIG,
    arrange,
    centered_kernel,
    execute,
    generate,
    mechanism,
    permutation_check,
    prepare,
    validate_plan,
)


def test_paired_noise_regimes_preserve_exogenous_draws_and_mean():
    cfg = read(CONFIG)
    pools, reference = generate(cfg, "scaled_cubic", 0, "preflight")
    assert reference == "A_to_B"
    baseline = np.asarray(pools["independent_additive"]["training_pool"])
    changed = np.asarray(pools["heteroscedastic"]["training_pool"])
    assert np.array_equal(baseline[:, 0], changed[:, 0])
    scale = (1 + 0.375 * baseline[:, 0]) / np.sqrt(1 + 0.375**2 * 4 / 3)
    f = mechanism(baseline[:, 0], "scaled_cubic")
    assert np.allclose(changed[:, 1] - f, scale * (baseline[:, 1] - f))
    _, swapped_reference = generate(cfg, "sine", 0, "preflight")
    assert swapped_reference == "B_to_A"


def test_pool_arrangement_matches_production_split():
    import random

    train = [[float(i), 1.0] for i in range(64)]
    evaluation = [[-float(i) - 1, 2.0] for i in range(256)]
    rows = arrange(train, evaluation, 261)
    indices = list(range(320))
    random.Random(261).shuffle(indices)
    assert [rows[i] for i in indices[:64]] == train
    assert [rows[i] for i in indices[64:]] == evaluation


def test_hsic_centering_against_explicit_projection_reference():
    rng = np.random.default_rng(76)
    x, residual = rng.normal(size=12), rng.normal(size=12)
    h = np.eye(12) - np.ones((12, 12)) / 12
    kernels = []
    for v in (x, residual):
        d = np.abs(v[:, None] - v[None, :])
        bandwidth = np.median(d[np.triu_indices(12, 1)])
        k = np.exp(-0.5 * (d / bandwidth) ** 2)
        kernels.append(h @ k @ h)
    reference = float(np.sum(kernels[0] * kernels[1]) / 12**2)
    cfg = {**read(CONFIG), "permutations": 9}
    check = permutation_check(x, residual, cfg, np.random.SeedSequence(44))
    assert check["hsic"] == pytest.approx(reference, abs=1e-14)
    assert check["pvalue"] == (1 + check["exceedances"]) / 10
    assert np.max(np.abs(centered_kernel(x).sum(axis=0))) < 1e-12
    again = permutation_check(x, residual, cfg, np.random.SeedSequence(44))
    assert check == again


def test_preflight_plan_is_complete_nested_and_bound(tmp_path):
    plan = tmp_path / "plan"
    manifest = prepare(plan, "preflight")
    assert len(manifest["schedule"]) == 16
    validate_plan(plan)
    dataset = plan / manifest["schedule"][0]["dataset"]
    content = read(dataset)
    content["reference"] = "impossible"
    dataset.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="dataset"):
        validate_plan(plan)


def test_full_run_requires_real_numerical_preflight(tmp_path):
    plan = tmp_path / "plan"
    prepare(plan, "full")
    with pytest.raises(ValueError, match="preflight"):
        execute(plan)


def test_preflight_execution_and_saved_replay_without_fits(tmp_path, monkeypatch):
    plan = tmp_path / "plan"
    prepare(plan, "preflight")
    result = execute(plan)
    assert result["passed"] and result["scheduled"] == 16
    assert result["failures"] == 0  # Numerical agreement, not desired direction accuracy.

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved analysis must not refit")

    monkeypatch.setattr(np.linalg, "solve", forbidden)
    analysis = analyze(plan, tmp_path / "analysis")
    assert analysis["scheduled_cells"] == 16
    assert analysis["base_worlds"] == 2
    assert analysis["permutations_replayed_without_refitting"]
    assert all(sum(c["counts"].values()) == 2 for c in analysis["cells"])
    with pytest.raises(FileExistsError):
        execute(plan)


def test_frozen_main_results_independently_recount_original_producer_outputs():
    from collections import Counter, defaultdict
    from pathlib import Path

    from causalbridge.discovery.schemas import ANMResult, canonical_digest
    from causalbridge.evaluation.anm_failure_audit import verified_archive

    root = Path("artifacts/anm-mechanism-study-20261121")
    files = verified_archive(root / "run-records.tar.gz", root / "manifest.json")
    manifest = json.loads(files["full/manifest.json"])
    assert len(manifest["schedule"]) == 192
    assert len({c["world_id"] for c in manifest["schedule"]}) == 24
    counts = defaultdict(Counter)
    for cell in manifest["schedule"]:
        result = ANMResult.model_validate_json(
            files["full/attempts/" + cell["cell_id"] + "/result.json"]
        )
        diagnostic = json.loads(files["full/diagnostics/" + cell["cell_id"] + ".json"])
        assert result.status == "ok" and diagnostic["failure"] is None
        assert canonical_digest(result.model_dump(mode="json")) == diagnostic["result_digest"]
        label = (
            "A"
            if result.predicted_direction is None
            else "C"
            if result.predicted_direction == cell["reference"]
            else "W"
        )
        counts[cell["regime"], cell["n_train"], cell["n_eval"]][label] += 1
    assert counts["independent_additive", 256, 256] == {"C": 24}
    assert counts["heteroscedastic", 256, 256] == {"C": 2, "W": 17, "A": 5}
    assert counts["heteroscedastic", 64, 64] == {"C": 6, "W": 17, "A": 1}
    assert counts["heteroscedastic", 64, 256] == {"C": 1, "W": 23}
    assert all(sum(c.values()) == 24 for c in counts.values())
