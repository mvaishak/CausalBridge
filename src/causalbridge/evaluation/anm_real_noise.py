"""Frozen residual-spread investigation; original ANM directions/settings are unchanged."""

import json
import math
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from causalbridge.discovery.anm import _hsic
from causalbridge.discovery.anm_requests import write_json_exclusive
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_failure_audit import (
    ARCHIVE,
    MANIFEST,
    VALIDATION,
    outcome,
    read,
    sha,
    verified_archive,
    verify_attempt,
    write,
)
from causalbridge.evaluation.anm_mechanism_study import mechanism

CONFIG = Path("configs/anm-real-noise-v1.json")
PILOT = Path("artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip")
SYNTHETIC = Path("artifacts/anm-mechanism-study-20261121")
DIRECTIONS = ("A_to_B", "B_to_A")
MODES = ("raw", "mean_detrended")
SCHEMES = ("iid", "saved_order_blocks")


def source_hashes():
    paths = [
        CONFIG,
        PILOT,
        ARCHIVE,
        MANIFEST,
        SYNTHETIC / "run-records.tar.gz",
        SYNTHETIC / "manifest.json",
        Path("configs/evaluation-roster.json"),
        Path("scripts/anm_real_noise.py"),
        Path("artifacts/final-delivery/track-b-pilot/evaluator-records.json"),
        Path("uv.lock"),
    ]
    paths += sorted(Path("src/causalbridge").rglob("*.py"))
    return {str(p): sha(p) for p in paths}


def seed_for(seed, key):
    return int(canonical_digest([seed, key]).split(":")[1][:16], 16)


def save_original(files, prefix, output, record_id):
    target = output / "originals" / record_id
    target.mkdir(parents=True)
    for name in (
        "request.json",
        "sample.json",
        "config.json",
        "inputs.json",
        "result.json",
        "reproducibility.json",
        "execution_started.json",
    ):
        with (target / name).open("xb") as handle:
            handle.write(files[prefix + "/" + name])
    return str(target.relative_to(output))


def prepare(output):
    """Freeze all 55 real pairs, sensitivities and reused synthetic controls before tests."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    if sha(PILOT) != cfg["pilot_archive_sha256"]:
        raise ValueError("Pilot archive hash mismatch")
    inventory = source_hashes()
    files = verified_archive(ARCHIVE, MANIFEST)
    inputs = json.loads(files[VALIDATION + "/inputs.json"])
    evaluations = json.loads(files[VALIDATION + "/evaluations.json"])
    cases = {c["case_id"]: c for c in inputs["cases"]}
    real = []
    for record in evaluations:
        case = cases[record["case_id"]]
        order = record["selection"]["column_order"]
        cause = 0 if case["reference_direction"] == "first_to_second" else 1
        reference = "A_to_B" if order[0] == cause else "B_to_A"
        identity = f"validation38-{case['case_id']}-{record['split_seed']}"
        directory = save_original(files, VALIDATION + "/" + record["directory"], output, identity)
        real.append(
            {
                "record_id": identity,
                "directory": directory,
                "panel": "validation38",
                "case_id": case["case_id"],
                "pair_id": case["pair_id"],
                "source_group": case["source_group"],
                "weight": case["weight"],
                "reference": reference,
                "split_seed": record["split_seed"],
                "request_digest": record["request_digest"],
                "result_digest": record["result_digest"],
                "original_direction": record["result"]["predicted_direction"],
                "original_outcome": outcome(
                    record["result"]["predicted_direction"], reference, record["result"]["status"]
                ),
            }
        )
    with zipfile.ZipFile(PILOT) as z:
        mapping = {
            r["case_id"]: r for r in json.loads(z.read("real-pilot-01/evaluation_mapping.json"))
        }
        evaluator = read("artifacts/final-delivery/track-b-pilot/evaluator-records.json")
        for case in evaluator:
            cid = case["case_id"]
            prefix = "real-pilot-01/anm/" + cid
            payload = {
                prefix + "/" + name: z.read(prefix + "/" + name)
                for name in (
                    "request.json",
                    "sample.json",
                    "config.json",
                    "inputs.json",
                    "result.json",
                    "reproducibility.json",
                    "execution_started.json",
                )
            }
            result = json.loads(payload[prefix + "/result.json"])
            request = json.loads(payload[prefix + "/request.json"])
            if request["ab_mapping_id"] != mapping[cid]["ab_mapping_id"]:
                raise ValueError("Pilot mapping is not bound to original request")
            cause = 0 if case["reference_direction"] == "first_to_second" else 1
            reference = (
                "A_to_B"
                if mapping[cid]["original_to_runtime_column_order"][0] == cause
                else "B_to_A"
            )
            identity = f"pilot17-{cid}-261"
            directory = save_original(payload, prefix, output, identity)
            real.append(
                {
                    "record_id": identity,
                    "directory": directory,
                    "panel": "pilot17",
                    "case_id": cid,
                    "pair_id": case["original_pair_id"],
                    "source_group": case["source_group"],
                    "weight": case["weight"],
                    "reference": reference,
                    "split_seed": 261,
                    "request_digest": canonical_digest(request),
                    "result_digest": canonical_digest(result),
                    "original_direction": result["predicted_direction"],
                    "original_outcome": outcome(
                        result["predicted_direction"], reference, result["status"]
                    ),
                }
            )
    if len(real) != 131 or len({r["record_id"] for r in real}) != 131:
        raise ValueError("Expected 114 validation attempts and 17 pilot attempts")
    controls = []
    synthetic = verified_archive(SYNTHETIC / "run-records.tar.gz", SYNTHETIC / "manifest.json")
    synthetic_manifest = json.loads(synthetic["full/manifest.json"])
    source_path = "src/causalbridge/evaluation/anm_mechanism_study.py"
    if sha(source_path) != synthetic_manifest["source_sha256"][source_path]:
        raise ValueError("Synthetic oracle function source changed")
    schedule = synthetic_manifest["schedule"]
    for cell in schedule:
        if cell["n_train"] != 256 or cell["n_eval"] != 256:
            continue
        dataset = json.loads(synthetic["full/" + cell["dataset"]])
        x, y = (0, 1) if cell["reference"] == "A_to_B" else (1, 0)
        training, evaluation = (
            np.asarray(dataset["training_pool"]),
            np.asarray(dataset["evaluation_pool"]),
        )
        residual = evaluation[:, y] - mechanism(evaluation[:, x], cell["family"])
        classes = [(cell["regime"], residual)]
        if cell["regime"] == "independent_additive":
            drift = cfg["quadratic_control_amplitude"] * (evaluation[:, x] ** 2 - 4 / 3)
            classes.append(("constant_noise_quadratic_mean_error", residual + drift))
        for label, values in classes:
            identity = cell["world_id"] + "-" + label
            payload = {
                "control_id": identity,
                "world_id": cell["world_id"],
                "family": cell["family"],
                "label": label,
                "cause_training": training[:, x].tolist(),
                "cause_evaluation": evaluation[:, x].tolist(),
                "residual": values.tolist(),
            }
            path = output / "controls" / (identity + ".json")
            path.parent.mkdir(exist_ok=True)
            write(path, payload)
            controls.append(
                {"control_id": identity, "path": str(path.relative_to(output)), "sha256": sha(path)}
            )
    if len(controls) != 72:
        raise ValueError("Expected 24 paired worlds and three residual-control classes")
    manifest = {
        "protocol": cfg,
        "prepared_at_utc": datetime.now(UTC).isoformat(),
        "source_sha256": inventory,
        "real": real,
        "controls": controls,
        "inputs_digest": canonical_digest([real, controls]),
        "original_files_sha256": {
            str(p.relative_to(output)): sha(p)
            for p in sorted((output / "originals").rglob("*.json"))
        },
    }
    write(output / "manifest.json", manifest)
    return manifest


def validate_plan(plan):
    plan = Path(plan)
    manifest = read(plan / "manifest.json")
    if manifest["protocol"] != read(CONFIG) or manifest["source_sha256"] != source_hashes():
        raise ValueError("Source/protocol changed after freeze")
    if manifest["inputs_digest"] != canonical_digest([manifest["real"], manifest["controls"]]):
        raise ValueError("Frozen schedule changed")
    for relative, digest in manifest["original_files_sha256"].items():
        if sha(plan / relative) != digest:
            raise ValueError("Original ANM record changed")
    for control in manifest["controls"]:
        if sha(plan / control["path"]) != control["sha256"]:
            raise ValueError("Control changed")
    return manifest


def detrend(cause, residual, cfg, key):
    """Cross-fitted quadratic residual mean; sensitivity only, not an oracle."""
    rng = np.random.default_rng(seed_for(cfg["detrending_seed"], key))
    order = rng.permutation(len(cause))
    folds = np.empty(len(cause), dtype=int)
    folds[order] = np.arange(len(cause)) % cfg["detrending_folds"]
    design = np.column_stack([cause**degree for degree in range(cfg["detrending_degree"] + 1)])
    corrected = np.empty(len(cause))
    for fold in range(cfg["detrending_folds"]):
        selected = folds != fold
        coefficients, _, rank, _ = np.linalg.lstsq(design[selected], residual[selected], rcond=None)
        if rank < design.shape[1]:
            raise ValueError("rank_deficient_quadratic_detrending")
        corrected[~selected] = residual[~selected] - design[~selected] @ coefficients
    return corrected


def group_data(cause_training, cause, residual, cfg):
    edges = np.unique(np.quantile(cause_training, cfg["training_quantiles"]))
    groups = np.searchsorted(edges, cause, side="right")
    counts = np.bincount(groups, minlength=len(edges) + 1)
    if len(counts) < 2 or min(counts) < cfg["minimum_bin_count"]:
        return None, {
            "status": "unavailable",
            "reason": "insufficient_or_empty_cause_bin",
            "bin_counts": counts.tolist(),
            "edges": edges.tolist(),
        }
    medians = np.array([np.median(residual[groups == i]) for i in range(len(counts))])
    means = np.array([np.mean(residual[groups == i]) for i in range(len(counts))])
    variance = np.array([np.var(residual[groups == i], ddof=1) for i in range(len(counts))])
    deviations = np.abs(residual - medians[groups])
    spreads = np.array([np.mean(deviations[groups == i]) for i in range(len(counts))])
    total = float(np.sum((deviations - deviations.mean()) ** 2))
    if total <= 0:
        return None, {
            "status": "unavailable",
            "reason": "constant_absolute_deviation",
            "bin_counts": counts.tolist(),
        }
    record = {
        "status": "ok",
        "bin_counts": counts.tolist(),
        "edges": edges.tolist(),
        "bin_residual_mean": means.tolist(),
        "bin_residual_median": medians.tolist(),
        "bin_residual_variance": variance.tolist(),
        "bin_median_absolute_deviation_mean": spreads.tolist(),
        "spread_ratio": float(spreads.max() / spreads.min()) if spreads.min() > 0 else None,
        "zero_spread_bin": bool(spreads.min() == 0),
        "residual_mean_range_sd": float(np.ptp(means) / residual.std())
        if residual.std() > 0
        else None,
    }
    return (groups, counts, deviations, total), record


def spread_checks(cause_training, cause, residual, cfg, key):
    """Median-centered spread contrast; permutation p-values have explicit assumptions."""
    prepared, record = group_data(cause_training, cause, residual, cfg)
    if prepared is None:
        return {scheme: dict(record) for scheme in SCHEMES}
    groups, counts, z, total = prepared
    masks = [groups == i for i in range(len(counts))]
    mean = z.mean()

    def statistic(values):
        return (
            sum(
                n * (values[:, mask].mean(axis=1) - mean) ** 2
                for n, mask in zip(counts, masks, strict=True)
            )
            / total
        )

    observed = float(statistic(z[None, :])[0])
    results = {}
    blocks = [
        np.arange(i, min(i + cfg["block_length"], len(z)))
        for i in range(0, len(z), cfg["block_length"])
    ]
    for scheme in SCHEMES:
        rng = np.random.default_rng(seed_for(cfg["permutation_seed"], [key, scheme]))
        exceedances = 0
        for start in range(0, cfg["permutations"], cfg["permutation_batch"]):
            size = min(cfg["permutation_batch"], cfg["permutations"] - start)
            if scheme == "iid":
                indices = np.stack([rng.permutation(len(z)) for _ in range(size)])
            else:
                indices = np.stack(
                    [
                        np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])
                        for _ in range(size)
                    ]
                )
            exceedances += int(
                np.count_nonzero(statistic(z[indices]) >= observed - cfg["tie_tolerance"])
            )
        pvalue = (exceedances + 1) / (cfg["permutations"] + 1)
        results[scheme] = {
            **record,
            "statistic_eta2": observed,
            "permutations": cfg["permutations"],
            "exceedances": exceedances,
            "pvalue_nominal": pvalue,
        }
    return results


def diagnose_vectors(cause_training, cause, residual, cfg, key):
    """Raw and residual-mean corrected diagnostics; all vectors retained for replay."""
    mean, sd = float(np.mean(cause_training)), float(np.std(cause_training))
    if sd <= 0:
        raise ValueError("constant_training_cause")
    xt, x = (cause_training - mean) / sd, (cause - mean) / sd
    modes = {"raw": spread_checks(xt, x, residual, cfg, key)}
    corrected = None
    try:
        corrected = detrend(x, residual, cfg, key)
        modes["mean_detrended"] = spread_checks(xt, x, corrected, cfg, key)
    except ValueError as exc:
        modes["mean_detrended"] = {
            scheme: {"status": "unavailable", "reason": str(exc)} for scheme in SCHEMES
        }
    return {
        "vectors": {
            "cause_training": cause_training.tolist(),
            "cause": cause.tolist(),
            "residual": residual.tolist(),
            "mean_detrended_residual": corrected.tolist() if corrected is not None else None,
        },
        "modes": modes,
    }


def reconstruct(directory):
    """Reconstruct only the frozen fits, requiring original HSIC agreement."""
    saved, result, _ = verify_attempt(
        directory, {"numeric_relative_tolerance": 1e-9, "numeric_absolute_tolerance": 1e-12}
    )
    values = np.asarray(saved.sample.rows)
    training, evaluation = (
        values[list(saved.training_indices)],
        values[list(saved.evaluation_indices)],
    )
    means, scales = training.mean(axis=0), training.std(axis=0)
    train, test = (training - means) / scales, (evaluation - means) / scales
    ordered = np.argsort(saved.evaluation_indices)
    vectors = {}
    for name, x, y in (("A_to_B", 0, 1), ("B_to_A", 1, 0)):
        kernel = np.exp(-saved.config.kernel_gamma * (train[:, x, None] - train[:, x]) ** 2)
        coef = np.linalg.solve(kernel + saved.config.ridge_alpha * np.eye(len(train)), train[:, y])
        prediction = (
            np.exp(-saved.config.kernel_gamma * (test[:, x, None] - train[:, x]) ** 2) @ coef
        )
        residual = test[:, y] - prediction
        normalized = (residual - residual.mean()) / residual.std()
        score, _ = _hsic(test[:, x], normalized)
        original = result.score_ab if name == "A_to_B" else result.score_ba
        if not math.isclose(score, original, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError("Frozen ANM score reconstruction mismatch")
        vectors[name] = (train[:, x], test[ordered, x], residual[ordered], score)
    return vectors, result


def execute(plan):
    plan = Path(plan)
    manifest = validate_plan(plan)
    if (plan / "execution_started.json").exists():
        raise FileExistsError("Study already started; preserve it rather than overwrite")
    write_json_exclusive(
        plan / "execution_started.json", {"manifest_digest": canonical_digest(manifest)}
    )
    (plan / "diagnostics").mkdir()
    cfg, records = manifest["protocol"], []
    start = time.perf_counter()
    for original in manifest["real"]:
        vectors, result = reconstruct(plan / original["directory"])
        if canonical_digest(result.model_dump(mode="json")) != original["result_digest"]:
            raise ValueError("Original result digest mismatch")
        for direction, (xt, x, residual, score) in vectors.items():
            key = [original["record_id"], direction]
            record = {
                "kind": "real",
                **original,
                "direction_tested": direction,
                "request_digest": original["request_digest"],
                "reproduced_hsic": score,
                **diagnose_vectors(xt, x, residual, cfg, key),
            }
            name = original["record_id"] + "-" + direction + ".json"
            write(plan / "diagnostics" / name, record)
            records.append(name)
        print(original["record_id"], "reconstructed", flush=True)
    for control in manifest["controls"]:
        payload = read(plan / control["path"])
        xt, x, residual = (
            np.asarray(payload[k]) for k in ("cause_training", "cause_evaluation", "residual")
        )
        record = {
            "kind": "calibration",
            "control_id": payload["control_id"],
            "world_id": payload["world_id"],
            "label": payload["label"],
            "family": payload["family"],
            **diagnose_vectors(xt, x, residual, cfg, ["calibration", payload["world_id"]]),
        }
        name = payload["control_id"] + ".json"
        write(plan / "diagnostics" / name, record)
        records.append(name)
    completion = {
        "manifest_digest": canonical_digest(manifest),
        "records": records,
        "records_digest": canonical_digest([read(plan / "diagnostics" / name) for name in records]),
        "real_directional_reconstructions": 262,
        "residual_calibration_controls": 72,
        "elapsed_seconds": time.perf_counter() - start,
    }
    write(plan / "completion.json", completion)
    return completion


def holm(pvalues):
    """Missing diagnostics retain their planned family slot but never become evidence."""
    m, maximum = len(pvalues), 0.0
    ordered = sorted(enumerate(pvalues), key=lambda x: 1 if x[1] is None else x[1])
    adjusted = [None] * m
    for rank, (index, value) in enumerate(ordered):
        maximum = max(maximum, (m - rank) * (1 if value is None else value))
        if value is not None:
            adjusted[index] = min(1.0, maximum)
    return adjusted


def analyze(plan, output, *, replay=False):
    plan, output = Path(plan), Path(output)
    manifest = validate_plan(plan)
    completion = read(plan / "completion.json")
    records = [read(plan / "diagnostics" / name) for name in completion["records"]]
    if completion["manifest_digest"] != canonical_digest(manifest) or completion[
        "records_digest"
    ] != canonical_digest(records):
        raise ValueError("Diagnostic completion binding mismatch")
    cfg = manifest["protocol"]
    if replay:
        for row in records:
            v = row["vectors"]
            key = (
                [row["record_id"], row["direction_tested"]]
                if row["kind"] == "real"
                else ["calibration", row["world_id"]]
            )
            result = diagnose_vectors(
                np.asarray(v["cause_training"]),
                np.asarray(v["cause"]),
                np.asarray(v["residual"]),
                cfg,
                key,
            )
            if result["modes"] != row["modes"]:
                raise ValueError("Residual diagnostic replay mismatch")
    real = [r for r in records if r["kind"] == "real"]
    calibration = [r for r in records if r["kind"] == "calibration"]
    families = []
    for panel in ("pilot17", "validation38"):
        splits = [261] if panel == "pilot17" else cfg["validation_splits"]
        for split in splits:
            rows = [r for r in real if r["panel"] == panel and r["split_seed"] == split]
            expected = 34 if panel == "pilot17" else 76
            if len(rows) != expected:
                raise ValueError("Incomplete directional family")
            for mode in MODES:
                for scheme in SCHEMES:
                    checks = [r["modes"][mode][scheme] for r in rows]
                    adjusted = holm([c.get("pvalue_nominal") for c in checks])
                    for check, pvalue in zip(checks, adjusted, strict=True):
                        check["pvalue_holm_nominal"] = pvalue
                        check["flag_holm_nominal"] = pvalue is not None and pvalue <= cfg["alpha"]
                    families.append(
                        {
                            "panel": panel,
                            "split": split,
                            "mode": mode,
                            "scheme": scheme,
                            "planned_tests": expected,
                        }
                    )
    tables = []
    for panel in ("pilot17", "validation38"):
        for mode in MODES:
            for scheme in SCHEMES:
                for kind in ("correct", "wrong", "abstention"):
                    rows = [
                        r
                        for r in real
                        if r["panel"] == panel
                        and r["split_seed"] == 261
                        and r["direction_tested"] == r["reference"]
                        and r["original_outcome"] == kind
                    ]
                    checks = [r["modes"][mode][scheme] for r in rows]
                    tables.append(
                        {
                            "panel": panel,
                            "mode": mode,
                            "scheme": scheme,
                            "original_outcome": kind,
                            "scheduled_pairs": len(rows),
                            "available": sum(c["status"] == "ok" for c in checks),
                            "nominal_flags": sum(
                                c.get("pvalue_nominal", 1) <= cfg["alpha"] for c in checks
                            ),
                            "holm_nominal_flags": sum(c["flag_holm_nominal"] for c in checks),
                        }
                    )
    control_tables = []
    for label in sorted({r["label"] for r in calibration}):
        for mode in MODES:
            for scheme in SCHEMES:
                checks = [r["modes"][mode][scheme] for r in calibration if r["label"] == label]
                control_tables.append(
                    {
                        "label": label,
                        "mode": mode,
                        "scheme": scheme,
                        "n": len(checks),
                        "available": sum(c["status"] == "ok" for c in checks),
                        "nominal_flags": sum(
                            c.get("pvalue_nominal", 1) <= cfg["alpha"] for c in checks
                        ),
                    }
                )
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "version": cfg["version"],
        "scope": cfg["scope"],
        "manifest_digest": canonical_digest(manifest),
        "real_directional_records": len(real),
        "calibration_records": len(calibration),
        "tables": tables,
        "calibration": control_tables,
        "adjustment_families": families,
        "permutation_replay_performed": replay,
        "execution": completion,
    }
    write(output / "metrics.json", result)
    write(output / "real-records.json", real)
    write(output / "calibration-records.json", calibration)
    return result
