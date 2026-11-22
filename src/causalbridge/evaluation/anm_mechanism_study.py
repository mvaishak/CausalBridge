"""Frozen known-truth ANM component study, isolated from production method policy."""

import math
import platform
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from causalbridge.discovery.anm import _hsic, execute_anm_request
from causalbridge.discovery.anm_requests import (
    ANMConfig,
    load_anm_request,
    save_anm_request,
    write_json_exclusive,
)
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_failure_audit import read, sha, write

CONFIG = Path("configs/anm-mechanism-study-v1.json")


def source_hashes():
    paths = [CONFIG, Path("uv.lock"), Path("scripts/anm_mechanism_study.py")]
    paths += sorted(Path("src/causalbridge").rglob("*.py"))
    return {str(p): sha(p) for p in paths}


def mechanism(x, family):
    if family == "scaled_cubic":
        return 0.25 * x**3
    if family == "sine":
        return np.sin(2 * x)
    raise ValueError("Unknown mechanism")


def generate(cfg, family, replicate, phase):
    """Independent train/evaluation pools; reuse exogenous draws across noise regimes."""
    seed = cfg["preflight_data_seed"] if phase == "preflight" else cfg["data_seed"]
    family_index = cfg["families"].index(family)
    streams = np.random.SeedSequence([seed, family_index, replicate]).spawn(4)
    tx = np.random.default_rng(streams[0]).uniform(-2, 2, max(cfg["train_sizes"]))
    ex = np.random.default_rng(streams[1]).uniform(-2, 2, max(cfg["evaluation_sizes"]))
    te = np.random.default_rng(streams[2]).normal(size=len(tx))
    ee = np.random.default_rng(streams[3]).normal(size=len(ex))
    # Alternate orientation before any outcomes; neither estimator receives this label.
    reverse = bool((family_index + replicate) % 2)
    pools = {}
    for regime in cfg["regimes"]:
        samples = []
        for x, epsilon in ((tx, te), (ex, ee)):
            scale = np.ones(len(x))
            if regime == "heteroscedastic":
                coefficient = cfg["heteroscedastic_coefficient"]
                scale = (1 + coefficient * x) / math.sqrt(1 + coefficient**2 * 4 / 3)
            y = mechanism(x, family) + cfg["noise_sd"] * scale * epsilon
            rows = np.column_stack((y, x) if reverse else (x, y))
            samples.append(rows.tolist())
        pools[regime] = {"training_pool": samples[0], "evaluation_pool": samples[1]}
    return pools, "B_to_A" if reverse else "A_to_B"


def arrange(training, evaluation, split_seed):
    """Place independent pools into the producer's seeded split, preserving its API."""
    indices = list(range(len(training) + len(evaluation)))
    random.Random(split_seed).shuffle(indices)
    rows = [None] * len(indices)
    for index, row in zip(indices, training + evaluation, strict=True):
        rows[index] = row
    return rows


def prepare(output, phase):
    """Persist protocol, all samples and original requests before any fit or score."""
    if phase not in ("preflight", "full"):
        raise ValueError("Unknown phase")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    count = (
        cfg["preflight_replicates_per_family"]
        if phase == "preflight"
        else cfg["replicates_per_family"]
    )
    schedule = []
    hashes = source_hashes()
    for family in cfg["families"]:
        for replicate in range(count):
            world_id = f"{family}-{replicate:02d}"
            pools, reference = generate(cfg, family, replicate, phase)
            for regime, pool in pools.items():
                dataset = {
                    "world_id": world_id,
                    "family": family,
                    "replicate": replicate,
                    "regime": regime,
                    "reference": reference,
                    **pool,
                }
                dataset_path = output / "datasets" / f"{world_id}-{regime}.json"
                dataset_path.parent.mkdir(exist_ok=True)
                write(dataset_path, dataset)
                for nt in cfg["train_sizes"]:
                    for ne in cfg["evaluation_sizes"]:
                        identity = f"{world_id}-{regime}-t{nt}-e{ne}"
                        directory = output / "attempts" / identity
                        rows = arrange(
                            pool["training_pool"][:nt],
                            pool["evaluation_pool"][:ne],
                            cfg["split_seed"],
                        )
                        configuration = ANMConfig(
                            configuration_version=cfg["version"],
                            threshold=cfg["direction_threshold"],
                            threshold_selection_version="fixed_historical_threshold_not_retuned",
                            sampling_seed=cfg["data_seed"]
                            if phase == "full"
                            else cfg["preflight_data_seed"],
                            split_seed=cfg["split_seed"],
                            training_fraction=nt / (nt + ne),
                            maximum_rows=nt + ne,
                            kernel_gamma=cfg["kernel_gamma"],
                            ridge_alpha=cfg["ridge_alpha"],
                        )
                        request = save_anm_request(
                            rows,
                            case_id=identity,
                            ab_mapping_id=canonical_digest(
                                {"world_id": world_id, "reference": reference}
                            ),
                            directory=directory,
                            config=configuration,
                        )
                        schedule.append(
                            {
                                "cell_id": identity,
                                "world_id": world_id,
                                "family": family,
                                "replicate": replicate,
                                "regime": regime,
                                "reference": reference,
                                "n_train": nt,
                                "n_eval": ne,
                                "dataset": str(dataset_path.relative_to(output)),
                                "dataset_sha256": sha(dataset_path),
                                "request_digest": canonical_digest(request.model_dump(mode="json")),
                            }
                        )
    manifest = {
        "phase": phase,
        "protocol": cfg,
        "prepared_at_utc": datetime.now(UTC).isoformat(),
        "source_sha256": hashes,
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "schedule": schedule,
        "schedule_digest": canonical_digest(schedule),
    }
    write(output / "manifest.json", manifest)
    return manifest


def validate_plan(plan):
    plan = Path(plan)
    manifest = read(plan / "manifest.json")
    if manifest["protocol"] != read(CONFIG) or manifest["source_sha256"] != source_hashes():
        raise ValueError("Protocol/source changed after freeze")
    if manifest["schedule_digest"] != canonical_digest(manifest["schedule"]):
        raise ValueError("Schedule digest mismatch")
    seen = set()
    expected_cells = set()
    count = (
        manifest["protocol"]["preflight_replicates_per_family"]
        if manifest["phase"] == "preflight"
        else manifest["protocol"]["replicates_per_family"]
    )
    for family in manifest["protocol"]["families"]:
        for replicate in range(count):
            for regime in manifest["protocol"]["regimes"]:
                for nt in manifest["protocol"]["train_sizes"]:
                    for ne in manifest["protocol"]["evaluation_sizes"]:
                        expected_cells.add((family, replicate, regime, nt, ne))
    actual_cells = set()
    for cell in manifest["schedule"]:
        if cell["cell_id"] in seen:
            raise ValueError("Duplicate planned cell")
        seen.add(cell["cell_id"])
        identity = (
            cell["family"],
            cell["replicate"],
            cell["regime"],
            cell["n_train"],
            cell["n_eval"],
        )
        if identity in actual_cells:
            raise ValueError("Repeated factorial cell")
        actual_cells.add(identity)
        dataset_path = plan / cell["dataset"]
        if sha(dataset_path) != cell["dataset_sha256"]:
            raise ValueError("Frozen dataset changed")
        saved = load_anm_request(plan / "attempts" / cell["cell_id"])
        if canonical_digest(saved.request.model_dump(mode="json")) != cell["request_digest"]:
            raise ValueError("Original request identity mismatch")
        if (len(saved.training_indices), len(saved.evaluation_indices)) != (
            cell["n_train"],
            cell["n_eval"],
        ):
            raise ValueError("Incorrect experimental sample sizes")
        dataset = read(dataset_path)
        generated, reference = generate(
            manifest["protocol"], cell["family"], cell["replicate"], manifest["phase"]
        )
        if (
            cell["reference"] != reference
            or any(
                dataset[k] != cell[k]
                for k in ("world_id", "family", "replicate", "regime", "reference")
            )
            or any(
                dataset[k] != generated[cell["regime"]][k]
                for k in ("training_pool", "evaluation_pool")
            )
        ):
            raise ValueError("Generated truth/pool metadata mismatch")
        training = [list(saved.sample.rows[i]) for i in saved.training_indices]
        evaluation = [list(saved.sample.rows[i]) for i in saved.evaluation_indices]
        if (
            training != dataset["training_pool"][: cell["n_train"]]
            or evaluation != dataset["evaluation_pool"][: cell["n_eval"]]
        ):
            raise ValueError("Independent-pool/nesting contract violated")
    expected = 16 if manifest["phase"] == "preflight" else 192
    if len(seen) != expected or actual_cells != expected_cells:
        raise ValueError("Incomplete factorial plan")
    return manifest


def centered_kernel(vector):
    distances = np.abs(vector[:, None] - vector[None, :])
    positive = distances[np.triu_indices(len(vector), 1)]
    positive = positive[positive > 0]
    if not positive.size:
        raise ValueError("No positive kernel distances")
    bandwidth = float(np.median(positive))
    kernel = np.exp(-0.5 * (distances / bandwidth) ** 2)
    return kernel - kernel.mean(axis=0) - kernel.mean(axis=1)[:, None] + kernel.mean()


def permutation_check(cause, residual, cfg, seed):
    """Plus-one Monte Carlo p-value with frozen tolerance and matching permutations."""
    k, residual_kernel = centered_kernel(cause), centered_kernel(residual)
    statistic = float(np.sum(k * residual_kernel) / len(cause) ** 2)
    production, _ = _hsic(cause, residual)
    if not math.isclose(statistic, production, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("Component HSIC does not match production")
    rng = np.random.default_rng(seed)
    exceedances = 0
    for _ in range(cfg["permutations"]):
        permutation = rng.permutation(len(cause))
        value = float(np.sum(k * residual_kernel[permutation][:, permutation]) / len(cause) ** 2)
        exceedances += value >= statistic - cfg["permutation_tie_tolerance"]
    pvalue = (1 + exceedances) / (1 + cfg["permutations"])
    return {
        "cause_vector": cause.tolist(),
        "residual_vector": residual.tolist(),
        "hsic": statistic,
        "permutations": cfg["permutations"],
        "exceedances": int(exceedances),
        "pvalue": pvalue,
        "rejected": pvalue <= cfg["dependence_alpha"],
    }


def diagnose_cell(saved, result, cell, cfg):
    """Reconstruct fits and compare with known conditional mean; oracle never enters ANM."""
    data = np.asarray(saved.sample.rows)
    raw_train, raw_eval = data[list(saved.training_indices)], data[list(saved.evaluation_indices)]
    means, scales = raw_train.mean(axis=0), raw_train.std(axis=0)
    training, evaluation = (raw_train - means) / scales, (raw_eval - means) / scales
    seed = np.random.SeedSequence(
        [
            cfg["permutation_seed"],
            cfg["families"].index(cell["family"]),
            cell["replicate"],
            cell["n_eval"],
        ]
    )
    diagnostics, predictions = {}, {}
    for name, x, y in (("A_to_B", 0, 1), ("B_to_A", 1, 0)):
        k = np.exp(-cfg["kernel_gamma"] * (training[:, x, None] - training[:, x]) ** 2)
        coefficients = np.linalg.solve(
            k + cfg["ridge_alpha"] * np.eye(len(training)), training[:, y]
        )
        predicted = (
            np.exp(-cfg["kernel_gamma"] * (evaluation[:, x, None] - training[:, x]) ** 2)
            @ coefficients
        )
        residual = evaluation[:, y] - predicted
        normalized = (residual - residual.mean()) / residual.std()
        check = permutation_check(evaluation[:, x], normalized, cfg, seed)
        expected = result.score_ab if name == "A_to_B" else result.score_ba
        if not math.isclose(check["hsic"], expected, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("Diagnostic fit/score does not match saved production result")
        diagnostics[name] = {**check, "prediction_mse": float(np.mean(residual**2))}
        predictions[name] = predicted
    correct = cell["reference"]
    x, y = (0, 1) if correct == "A_to_B" else (1, 0)
    oracle_prediction = (mechanism(raw_eval[:, x], cell["family"]) - means[y]) / scales[y]
    oracle_residual = evaluation[:, y] - oracle_prediction
    normalized = (oracle_residual - oracle_residual.mean()) / oracle_residual.std()
    oracle = permutation_check(evaluation[:, x], normalized, cfg, seed)
    opposite = "B_to_A" if correct == "A_to_B" else "A_to_B"
    gap = diagnostics[opposite]["hsic"] - oracle["hsic"]
    oracle_preference = (
        correct
        if gap > cfg["direction_threshold"]
        else opposite
        if gap < -cfg["direction_threshold"]
        else None
    )
    return {
        "directions": diagnostics,
        "oracle_forward": oracle,
        "conditional_mean_estimation_mse": float(
            np.mean((predictions[correct] - oracle_prediction) ** 2) * scales[y] ** 2
        ),
        "oracle_assisted_direction": oracle_preference,
        "oracle_assisted_scope": (
            "Known forward mechanism only; not a deployable method or reverse-direction oracle."
        ),
    }


def execute(plan, *, preflight=None):
    plan = Path(plan)
    manifest = validate_plan(plan)
    if manifest["phase"] == "full":
        if preflight is None:
            raise ValueError("Full study requires a passing separate preflight")
        prior = validate_plan(preflight)
        gate = read(Path(preflight) / "completion.json")
        if (
            prior["phase"] != "preflight"
            or prior["source_sha256"] != manifest["source_sha256"]
            or not gate["passed"]
        ):
            raise ValueError("Preflight gate mismatch")
        # Verify completed preflight records instead of trusting its status alone.
        if gate["manifest_digest"] != canonical_digest(prior):
            raise ValueError("Preflight completion/manifest mismatch")
        gate_records = [
            read(Path(preflight) / "diagnostics" / (c["cell_id"] + ".json"))
            for c in prior["schedule"]
        ]
        if gate["diagnostics_digest"] != canonical_digest(gate_records):
            raise ValueError("Preflight diagnostic completion mismatch")
        for cell in prior["schedule"]:
            result = read(Path(preflight) / "attempts" / cell["cell_id"] / "result.json")
            diagnostic = read(Path(preflight) / "diagnostics" / (cell["cell_id"] + ".json"))
            if diagnostic["result_digest"] != canonical_digest(result):
                raise ValueError("Preflight raw/diagnostic binding mismatch")
    if (plan / "execution_started.json").exists():
        raise FileExistsError("Study already started; preserve it and use a new attempt")
    write_json_exclusive(
        plan / "execution_started.json", {"manifest_digest": canonical_digest(manifest)}
    )
    (plan / "diagnostics").mkdir()
    errors = 0
    started = time.perf_counter()
    for cell in manifest["schedule"]:
        directory = plan / "attempts" / cell["cell_id"]
        try:
            result = execute_anm_request(directory)
            if result.status != "ok":
                raise ValueError("ANM execution failure: " + str(result.reason_code))
            saved = load_anm_request(directory)
            diagnostic = diagnose_cell(saved, result, cell, manifest["protocol"])
            record = {
                "cell_id": cell["cell_id"],
                "failure": None,
                "result_digest": canonical_digest(result.model_dump(mode="json")),
                **diagnostic,
            }
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            errors += 1
            record = {"cell_id": cell["cell_id"], "failure": type(exc).__name__ + ": " + str(exc)}
        write(plan / "diagnostics" / (cell["cell_id"] + ".json"), record)
        print(cell["cell_id"], "FAIL" if record["failure"] else "ok", flush=True)
    completed = {
        "passed": errors == 0,
        "scheduled": len(manifest["schedule"]),
        "failures": errors,
        "elapsed_seconds": time.perf_counter() - started,
        "manifest_digest": canonical_digest(manifest),
        "diagnostics_digest": canonical_digest(
            [read(plan / "diagnostics" / (c["cell_id"] + ".json")) for c in manifest["schedule"]]
        ),
    }
    write(plan / "completion.json", completed)
    return completed
