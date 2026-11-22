"""Independent numerical reference and frozen relative-ranking adequacy audit."""

import math
from pathlib import Path

import numpy as np

from causalbridge.discovery.anm_requests import load_anm_request
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_failure_audit import read, sha, verified_archive, write
from causalbridge.evaluation.anm_real_noise import seed_for

CONFIG = Path("configs/anm-decision-audit-v1.json")
PREVIOUS = Path("artifacts/anm-real-noise-20261121")
SYNTHETIC = Path("artifacts/anm-mechanism-study-20261121/case-results.json")


def reference_kernel(values):
    """Explicit H K H centering and independently constructed distance bandwidth."""
    n = len(values)
    distances = np.sqrt(np.subtract.outer(values, values) ** 2)
    positive = sorted(
        float(distances[i, j]) for i in range(n) for j in range(i + 1, n) if distances[i, j] > 0
    )
    bandwidth = float(np.median(positive))
    kernel = np.exp(-(distances**2) / (2 * bandwidth**2))
    h = np.eye(n) - np.ones((n, n)) / n
    return h @ kernel @ h


def reference_fit(training, evaluation, gamma, ridge):
    """Symmetric eigensystem solution, independent of producer's linear solve."""
    kernel = np.exp(-gamma * np.subtract.outer(training[:, 0], training[:, 0]) ** 2)
    eigenvalues, eigenvectors = np.linalg.eigh(kernel)
    coefficient = eigenvectors @ ((eigenvectors.T @ training[:, 1]) / (eigenvalues + ridge))
    prediction = (
        np.exp(-gamma * np.subtract.outer(evaluation[:, 0], training[:, 0]) ** 2) @ coefficient
    )
    residual = evaluation[:, 1] - prediction
    k, residual_kernel = reference_kernel(evaluation[:, 0]), reference_kernel(residual)
    score = float(np.trace(k @ residual_kernel) / len(evaluation) ** 2)
    relative_equation_error = np.linalg.norm(
        (kernel + ridge * np.eye(len(kernel))) @ coefficient - training[:, 1]
    ) / np.linalg.norm(training[:, 1])
    return score, k, residual_kernel, float(relative_equation_error)


def permutation_checks(k, residual_kernel, cfg, key):
    """Nominal IID and heuristic saved-order block randomizations of HSIC."""
    n = len(k)
    observed = float(np.trace(k @ residual_kernel) / n**2)
    blocks = [
        np.arange(i, min(i + cfg["block_length"], n)) for i in range(0, n, cfg["block_length"])
    ]
    checks = {}
    for scheme in ("iid", "saved_order_blocks"):
        rng = np.random.default_rng(seed_for(cfg["seed"], [key, scheme]))
        exceedances = 0
        for _ in range(cfg["permutations"]):
            order = (
                rng.permutation(n)
                if scheme == "iid"
                else np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])
            )
            statistic = float(np.sum(k * residual_kernel[order][:, order]) / n**2)
            exceedances += statistic >= observed - 1e-12
        p = (1 + exceedances) / (1 + cfg["permutations"])
        checks[scheme] = {
            "pvalue_nominal": p,
            "exceedances": int(exceedances),
            "rejected_nominal": p <= cfg["alpha_nominal"],
            "rejected_pair_bonferroni": p <= cfg["alpha_pair_bonferroni"],
        }
    return checks


def prepare(plan):
    """Freeze every case, the protocol, source, and complete saved original inputs."""
    plan = Path(plan)
    plan.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    rows = [
        r
        for r in read(PREVIOUS / "real-records.json")
        if r["direction_tested"] == "A_to_B" and r["split_seed"] == cfg["split_seed"]
    ]
    if len(rows) != 55:
        raise ValueError("Expected all 55 primary real pairs")
    files = verified_archive(PREVIOUS / "run-records.tar.gz", PREVIOUS / "manifest.json")
    cases = []
    inputs = {}
    vectors = {}
    for row in read(PREVIOUS / "real-records.json"):
        if row["split_seed"] == cfg["split_seed"]:
            vectors[f"{row['panel']}-{row['pair_id']}-{row['direction_tested']}"] = row["vectors"]
    write(plan / "frozen-vectors.json", vectors)
    inputs["frozen-vectors.json"] = sha(plan / "frozen-vectors.json")
    for row in rows:
        case = {
            k: row[k]
            for k in (
                "panel",
                "pair_id",
                "directory",
                "reference",
                "original_outcome",
                "original_direction",
                "result_digest",
                "request_digest",
            )
        }
        cases.append(case)
        prefix = "plan/" + case["directory"] + "/"
        for name, data in files.items():
            if name.startswith(prefix):
                relative = name.removeprefix("plan/")
                target = plan / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                inputs[relative] = sha(target)
    sources = [CONFIG, SYNTHETIC, Path("uv.lock"), Path("scripts/anm_decision_audit.py")]
    sources += sorted(Path("src/causalbridge").rglob("*.py"))
    for source in sources + [Path("pyproject.toml"), Path("README.md"), Path(".python-version")]:
        target = plan / "frozen-source" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    manifest = {
        "protocol": cfg,
        "cases": cases,
        "inputs_sha256": inputs,
        "source_sha256": {str(p): sha(p) for p in sources},
    }
    write(plan / "manifest.json", manifest)
    return manifest


def run(plan):
    """Compute references, fail on any mismatch, and retain both-direction adequacy."""
    plan = Path(plan)
    manifest = read(plan / "manifest.json")
    for path, digest in manifest["source_sha256"].items():
        if sha(path) != digest:
            raise ValueError("Source changed after freeze")
    for path, digest in manifest["inputs_sha256"].items():
        if sha(plan / path) != digest:
            raise ValueError("Input changed after freeze")
    if (plan / "started.json").exists():
        raise FileExistsError("Preserve original execution")
    write(plan / "started.json", {"manifest_digest": canonical_digest(manifest)})
    cfg = manifest["protocol"]
    records = []
    vectors = read(plan / "frozen-vectors.json")
    for case in manifest["cases"]:
        directory = plan / case["directory"]
        saved = load_anm_request(directory)
        result = read(directory / "result.json")
        if canonical_digest(result) != case["result_digest"]:
            raise ValueError("Original result mismatch")
        if canonical_digest(saved.request.model_dump(mode="json")) != case["request_digest"]:
            raise ValueError("Original request mismatch")
        data = np.asarray(saved.sample.rows)
        train = data[list(saved.training_indices)]
        test = data[list(saved.evaluation_indices)]
        means, scales = train.mean(axis=0), train.std(axis=0)
        train, test = (train - means) / scales, (test - means) / scales
        directions = {}
        for direction, columns in (("A_to_B", [0, 1]), ("B_to_A", [1, 0])):
            score, k, residual_kernel, error = reference_fit(
                train[:, columns],
                test[:, columns],
                saved.config.kernel_gamma,
                saved.config.ridge_alpha,
            )
            original = result["score_ab" if direction == "A_to_B" else "score_ba"]
            matched = math.isclose(
                score,
                original,
                rel_tol=cfg["numeric_relative_tolerance"],
                abs_tol=cfg["numeric_absolute_tolerance"],
            )
            frozen = vectors[f"{case['panel']}-{case['pair_id']}-{direction}"]
            k = reference_kernel(np.asarray(frozen["cause"]))
            residual_kernel = reference_kernel(np.asarray(frozen["residual"]))
            saved_residual_score = float(np.trace(k @ residual_kernel) / len(k) ** 2)
            if not math.isclose(saved_residual_score, original, rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("Independent HSIC formula differs on fixed original residuals")
            directions[direction] = {
                "reference_hsic": score,
                "reference_score_matches": matched,
                "saved_residual_reference_hsic": saved_residual_score,
                "original_hsic": original,
                "absolute_difference": abs(score - original),
                "relative_normal_equation_error": error,
                **permutation_checks(
                    k, residual_kernel, cfg, [case["panel"], case["pair_id"], direction]
                ),
            }
        margin = directions["B_to_A"]["reference_hsic"] - directions["A_to_B"]["reference_hsic"]
        threshold = result["threshold"]
        decision = (
            None
            if threshold is None
            else "A_to_B"
            if margin > threshold
            else "B_to_A"
            if margin < -threshold
            else "abstain"
        )
        records.append(
            {
                **case,
                "decision": decision,
                "original_decision": result["decision"],
                "reference_decision_matches": decision == result["decision"],
                "reference_margin": margin,
                "directions": directions,
            }
        )
        print(case["panel"], case["pair_id"], "numerically matched", flush=True)
    write(plan / "records.json", records)
    write(
        plan / "completion.json",
        {
            "records_digest": canonical_digest(records),
            "real_cases": len(records),
            "directional_checks": 2 * len(records),
        },
    )
    return records


def report(plan, output):
    """Deterministic saved-results summary; no fits or permutation reruns."""
    plan, output = Path(plan), Path(output)
    rows = read(plan / "records.json")
    if canonical_digest(rows) != read(plan / "completion.json")["records_digest"]:
        raise ValueError("Record digest mismatch")
    lines = [
        "# Independent ANM numerical and decision audit",
        "",
        "All cases use original fixed settings and splits. No new release policy is deployed. "
        "Adequacy rejections are nominal; nonrejection does not verify independence.",
        "",
        "| Panel | Outcome | N | Both rejected IID .05 | Both rejected IID .025 | "
        "Both rejected blocks .025 | Selected direction rejected IID .025 |",
        "|---|---|---|---|---|---|---|",
    ]
    for panel in ("pilot17", "validation38"):
        for outcome in ("correct", "wrong", "abstention"):
            selected = [r for r in rows if r["panel"] == panel and r["original_outcome"] == outcome]

            def both(scheme, flag, selected=selected):
                return sum(all(d[scheme][flag] for d in r["directions"].values()) for r in selected)

            picked = sum(
                r["original_direction"] is not None
                and r["directions"][r["original_direction"]]["iid"]["rejected_pair_bonferroni"]
                for r in selected
            )
            lines.append(
                f"| {panel} | {outcome} | {len(selected)} | "
                f"{both('iid', 'rejected_nominal')} | "
                f"{both('iid', 'rejected_pair_bonferroni')} | "
                f"{both('saved_order_blocks', 'rejected_pair_bonferroni')} | {picked} |"
            )
    synthetic = read(SYNTHETIC)
    lines += [
        "",
        "## Existing synthetic evidence (no new synthetic fits)",
        "",
        "Previous 99-permutation nominal .05 checks; fixed train/evaluation sizes 256/256. "
        "Do not directly equate these with the new 1,999-permutation real checks.",
        "",
        "| Regime | Outcome | N | Both directions rejected |",
        "|---|---|---|---|",
    ]
    for regime in ("independent_additive", "heteroscedastic"):
        for outcome in ("correct", "wrong", "abstention"):
            selected = [
                r
                for r in synthetic
                if r["regime"] == regime
                and r["n_train"] == 256
                and r["n_eval"] == 256
                and r["outcome"] == outcome
            ]
            both = sum(
                r["learned_forward_rejected"] and r["learned_reverse_rejected"] for r in selected
            )
            lines.append(f"| {regime} | {outcome} | {len(selected)} | {both} |")
    lines += [
        "",
        "## Per-case diagnostics",
        "",
        "| Panel | Pair | Original outcome | IID p A→B | IID p B→A | Block p A→B | Block p B→A |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        a, b = r["directions"]["A_to_B"], r["directions"]["B_to_A"]
        lines.append(
            f"| {r['panel']} | {r['pair_id']} | {r['original_outcome']} | "
            f"{a['iid']['pvalue_nominal']} | {b['iid']['pvalue_nominal']} | "
            f"{a['saved_order_blocks']['pvalue_nominal']} | "
            f"{b['saved_order_blocks']['pvalue_nominal']} |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
    return {
        "matched_directions": 2 * len(rows),
        "maximum_absolute_score_difference": max(
            d["absolute_difference"] for r in rows for d in r["directions"].values()
        ),
    }
