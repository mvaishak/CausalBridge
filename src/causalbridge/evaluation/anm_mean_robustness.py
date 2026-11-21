"""Fixed exploratory mean-estimator sensitivity; no production ANM changes."""

from pathlib import Path

import numpy as np

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_failure_audit import read, sha, verify_attempt, write
from causalbridge.evaluation.anm_real_noise import diagnose_vectors, holm, reconstruct

CONFIG = Path("configs/anm-mean-robustness-v1.json")
PREVIOUS = Path("artifacts/anm-real-noise-20261121")


def predict(xt, yt, x, spec):
    """Fit only training observations; all hyperparameters fixed in protocol."""
    if spec["kind"] == "krr":
        kernel = np.exp(-spec["gamma"] * (xt[:, None] - xt) ** 2)
        coefficient = np.linalg.solve(kernel + spec["ridge"] * np.eye(len(xt)), yt)
        return np.exp(-spec["gamma"] * (x[:, None] - xt) ** 2) @ coefficient
    if spec["kind"] != "local_linear":
        raise ValueError("Unknown estimator")
    result = []
    for point in x:
        delta = xt - point
        # Relative scaling prevents underflow without changing weighted least squares.
        weights = np.exp(
            -0.5 * (delta / spec["bandwidth"]) ** 2 + 0.5 * np.min((delta / spec["bandwidth"]) ** 2)
        )
        design = np.column_stack([np.ones(len(xt)), delta])
        coefficients, _, rank, _ = np.linalg.lstsq(
            design * np.sqrt(weights[:, None]), yt * np.sqrt(weights), rcond=None
        )
        if rank < 2:
            raise ValueError("Rank-deficient local linear fit")
        result.append(coefficients[0])
    return np.asarray(result)


def inputs(directory, reference):
    saved, _, _ = verify_attempt(
        directory, {"numeric_relative_tolerance": 1e-9, "numeric_absolute_tolerance": 1e-12}
    )
    values = np.asarray(saved.sample.rows)
    training = values[list(saved.training_indices)]
    evaluation = values[list(saved.evaluation_indices)]
    means, scales = training.mean(axis=0), training.std(axis=0)
    training, evaluation = (training - means) / scales, (evaluation - means) / scales
    evaluation = evaluation[np.argsort(saved.evaluation_indices)]
    cause, effect = (0, 1) if reference == "A_to_B" else (1, 0)
    return training[:, cause], training[:, effect], evaluation[:, cause], evaluation[:, effect]


def prepare(output, originals):
    """Freeze protocol, code, and complete original input records before executing."""
    output, originals = Path(output), Path(originals)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    records = read(PREVIOUS / "real-records.json")
    selected = [
        r
        for r in records
        if r["panel"] == "pilot17"
        and r["direction_tested"] == r["reference"]
        and r["pair_id"] in cfg["target_pairs"] + cfg["comparison_pairs"]
    ]
    if len(selected) != 8:
        raise ValueError("Expected two targets and six comparisons")
    inventory = {}
    for record in selected:
        target = output / record["directory"]
        target.mkdir(parents=True)
        for path in sorted((originals / record["directory"]).glob("*.json")):
            destination = target / path.name
            destination.write_bytes(path.read_bytes())
            inventory[str(destination.relative_to(output))] = sha(destination)
    sources = [
        CONFIG,
        Path("configs/anm-real-noise-v1.json"),
        Path("uv.lock"),
        Path("scripts/anm_mean_robustness.py"),
    ]
    sources += sorted(Path("src/causalbridge").rglob("*.py"))
    for path in sources:
        destination = output / "frozen-source" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    manifest = {
        "protocol": cfg,
        "spread_protocol": read("configs/anm-real-noise-v1.json"),
        "real": [
            {
                k: r[k]
                for k in (
                    "pair_id",
                    "reference",
                    "original_outcome",
                    "directory",
                    "request_digest",
                    "result_digest",
                )
            }
            for r in selected
        ],
        "inputs_sha256": inventory,
        "source_sha256": {str(p): sha(p) for p in sources},
    }
    write(output / "manifest.json", manifest)
    return manifest


def run(plan):
    """Save held-out predictions, residuals, spread diagnostics, and all configurations."""
    plan = Path(plan)
    manifest = read(plan / "manifest.json")
    for path, digest in manifest["source_sha256"].items():
        if sha(path) != digest:
            raise ValueError("Source changed after freeze")
    for path, digest in manifest["inputs_sha256"].items():
        if sha(plan / path) != digest:
            raise ValueError("Input changed after freeze")
    if (plan / "started.json").exists():
        raise FileExistsError("Preserve existing execution")
    write(plan / "started.json", {"manifest_digest": canonical_digest(manifest)})
    cfg, spread = manifest["protocol"], manifest["spread_protocol"]
    records = []
    for case in manifest["real"]:
        directory = plan / case["directory"]
        xt, yt, x, y = inputs(directory, case["reference"])
        original_vectors, result = reconstruct(directory)
        if canonical_digest(result.model_dump(mode="json")) != case["result_digest"]:
            raise ValueError("Original result digest mismatch")
        for spec in cfg["estimators"]:
            prediction = predict(xt, yt, x, spec)
            residual = y - prediction
            if spec["name"] == "original_krr" and not np.allclose(
                residual, original_vectors[case["reference"]][2], rtol=1e-9, atol=1e-12
            ):
                raise ValueError("Original residual mismatch")
            record = {
                "kind": "real",
                **case,
                "estimator": spec["name"],
                "n_train": len(xt),
                "n_eval": len(x),
                "training_effect": yt.tolist(),
                "evaluation_effect": y.tolist(),
                "prediction": prediction.tolist(),
                "heldout_mse": float(np.mean(residual**2)),
                **diagnose_vectors(xt, x, residual, spread, ["robustness", case["pair_id"]]),
            }
            records.append(record)
    for family in cfg["synthetic_families"]:
        for seed in cfg["synthetic_seeds"]:
            rng = np.random.default_rng(seed)
            xt = rng.uniform(-2, 2, cfg["synthetic_training"])
            x = rng.uniform(-2, 2, cfg["synthetic_evaluation"])
            et, e = rng.normal(0, 0.5, len(xt)), rng.normal(0, 0.5, len(x))
            mt, m = (
                (0.25 * xt**3, 0.25 * x**3)
                if family == "cubic"
                else (np.sin(2 * xt), np.sin(2 * x))
            )
            for regime in cfg["synthetic_regimes"]:
                st, s = (
                    (np.ones(len(xt)), np.ones(len(x)))
                    if regime == "independent_additive"
                    else (
                        (1 + 0.375 * xt) / np.sqrt(1 + 0.375**2 * 4 / 3),
                        (1 + 0.375 * x) / np.sqrt(1 + 0.375**2 * 4 / 3),
                    )
                )
                yt, y = mt + st * et, m + s * e
                # Standardize using training observations only, as in the real analysis.
                xm, xs, ym, ys = xt.mean(), xt.std(), yt.mean(), yt.std()
                a, b = (xt - xm) / xs, (x - xm) / xs
                for spec in cfg["estimators"]:
                    prediction = predict(a, (yt - ym) / ys, b, spec) * ys + ym
                    residual = y - prediction
                    records.append(
                        {
                            "kind": "synthetic",
                            "family": family,
                            "seed": seed,
                            "regime": regime,
                            "estimator": spec["name"],
                            "mean_function_mse": float(np.mean((m - prediction) ** 2)),
                            "prediction": prediction.tolist(),
                            "true_mean": m.tolist(),
                            **diagnose_vectors(a, b, residual, spread, [family, seed, regime]),
                        }
                    )
    real = [r for r in records if r["kind"] == "real"]
    for spec in cfg["estimators"]:
        selected = [r for r in real if r["estimator"] == spec["name"]]
        for mode in ("raw", "mean_detrended"):
            for scheme in ("iid", "saved_order_blocks"):
                checks = [r["modes"][mode][scheme] for r in selected]
                adjusted = holm([c.get("pvalue_nominal") for c in checks])
                for check, p in zip(checks, adjusted, strict=True):
                    check["holm_pvalue_nominal"] = p
    write(plan / "records.json", records)
    write(
        plan / "completion.json",
        {
            "record_digest": canonical_digest(records),
            "real_configurations": len(real),
            "synthetic_configurations": len(records) - len(real),
        },
    )
    return records


def report(plan, output):
    """Replay tables solely from saved results, without regression or inference."""
    plan, output = Path(plan), Path(output)
    records = read(plan / "records.json")
    if canonical_digest(records) != read(plan / "completion.json")["record_digest"]:
        raise ValueError("Result digest mismatch")
    lines = [
        "# Fixed mean-estimator robustness results",
        "",
        "Exploratory, selected opened pilot cases. MSE is held-out effect prediction error "
        "in original ANM training-standardized units, not true mean-function error.",
        "",
        "All p-values below are nominal Holm-adjusted across eight cases separately per "
        "estimator/mode/scheme. Block permutation is only a row-order heuristic.",
        "",
        "| Pair | Original outcome | Estimator | MSE | Raw spread ratio | Raw IID p | "
        "Raw block p | Detrended spread ratio | Detrended IID p | Detrended block p |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        if r["kind"] != "real":
            continue
        raw, det = r["modes"]["raw"], r["modes"]["mean_detrended"]
        values = [
            r["pair_id"],
            r["original_outcome"],
            r["estimator"],
            r["heldout_mse"],
            raw["iid"].get("spread_ratio"),
            raw["iid"].get("holm_pvalue_nominal"),
            raw["saved_order_blocks"].get("holm_pvalue_nominal"),
            det["iid"].get("spread_ratio"),
            det["iid"].get("holm_pvalue_nominal"),
            det["saved_order_blocks"].get("holm_pvalue_nominal"),
        ]
        lines.append(
            "| " + " | ".join(f"{v:.6g}" if isinstance(v, float) else str(v) for v in values) + " |"
        )
    lines += [
        "",
        "## Synthetic controls",
        "",
        "Eight function/seed settings (four random draws reused across two fixed functions), "
        "reused across regimes/estimators. Counts use unadjusted IID p≤0.05; trials are paired.",
        "",
        "| Regime | Estimator | N | Median true mean MSE | Raw flags | Detrended flags |",
        "|---|---|---|---|---|---|",
    ]
    cfg = read(plan / "manifest.json")["protocol"]
    for regime in cfg["synthetic_regimes"]:
        for spec in cfg["estimators"]:
            rows = [
                r
                for r in records
                if r["kind"] == "synthetic"
                and r["regime"] == regime
                and r["estimator"] == spec["name"]
            ]
            flags = [
                sum(r["modes"][mode]["iid"].get("pvalue_nominal", 1) <= 0.05 for r in rows)
                for mode in ("raw", "mean_detrended")
            ]
            error = np.median([r["mean_function_mse"] for r in rows])
            lines.append(
                f"| {regime} | {spec['name']} | {len(rows)} | {error:.6g} | "
                f"{flags[0]} | {flags[1]} |"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
    return {"records": len(records), "table": str(output)}
