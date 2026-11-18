"""Exploratory cached-baseline diagnosis, not a production ANM replacement.

Fixed permutation HSIC checks assume exchangeable observations. Nonrejection is
not proof of independence or causation. Original artifacts and real validation
cases are never modified or fitted here.
"""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import Field

from causalbridge.discovery.anm import load_anm_artifacts
from causalbridge.discovery.anm_requests import load_anm_request, read_json, write_json_exclusive
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.discovery.study import _destination, _load_development
from causalbridge.schemas import Record


class AdequacyPlan(Record):
    version: Literal["exploratory-hsic-adequacy-v1"]
    permutations: int = Field(strict=True, ge=19, le=9999)
    alpha: Annotated[float, Field(strict=True, gt=0, lt=1)]
    seed: int = Field(strict=True, ge=0)
    rule: Literal["answer_only_when_exactly_one_direction_is_not_rejected"]


def centered_kernel(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Kernel inputs must be finite and nonconstant")
    distances = abs(values[:, None] - values)
    positive = distances[np.triu_indices(len(values), 1)]
    positive = positive[positive > 0]
    if not len(positive):
        raise ValueError("Undefined kernel bandwidth")
    kernel = np.exp(-0.5 * (distances / np.median(positive)) ** 2)
    return kernel - kernel.mean(axis=0) - kernel.mean(axis=1)[:, None] + kernel.mean()


def permutation_check(cause, residual, plan, seed):
    k, residual_kernel = centered_kernel(cause), centered_kernel(residual)
    if k.shape != residual_kernel.shape:
        raise ValueError("Cause and residual counts differ")
    score = float(np.sum(k * residual_kernel) / len(k) ** 2)
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(plan.permutations):
        order = rng.permutation(len(k))
        statistic = float(np.sum(k * residual_kernel[np.ix_(order, order)]) / len(k) ** 2)
        exceed += statistic >= score
    pvalue = (1 + exceed) / (1 + plan.permutations)
    return dict(
        score=score,
        pvalue=pvalue,
        rejected=pvalue <= plan.alpha,
        permutations=plan.permutations,
        seed=seed,
    )


def adequacy_direction(checks):
    passing = [name for name in ("A_to_B", "B_to_A") if not checks[name]["rejected"]]
    if len(passing) == 1:
        return passing[0], "one_direction_not_rejected"
    return None, "both_not_rejected" if passing else "both_rejected"


def diagnose_attempt(directory, plan, key):
    artifacts = load_anm_artifacts(directory)
    saved = load_anm_request(directory)
    if artifacts.result.status != "ok":
        return dict(direction=None, reason="original_method_error", checks=None)
    values = np.asarray(saved.sample.rows, dtype=float)
    training, evaluation = (
        values[list(saved.training_indices)],
        values[list(saved.evaluation_indices)],
    )
    means, scales = training.mean(axis=0), training.std(axis=0)
    train, test = (training - means) / scales, (evaluation - means) / scales
    checks = {}
    for name, x, y, expected in (
        ("A_to_B", 0, 1, artifacts.result.score_ab),
        ("B_to_A", 1, 0, artifacts.result.score_ba),
    ):
        kernel = np.exp(-saved.config.kernel_gamma * (train[:, x, None] - train[:, x]) ** 2)
        coef = np.linalg.solve(kernel + saved.config.ridge_alpha * np.eye(len(train)), train[:, y])
        prediction = (
            np.exp(-saved.config.kernel_gamma * (test[:, x, None] - train[:, x]) ** 2) @ coef
        )
        residual = test[:, y] - prediction
        std = residual.std()
        if not std > 0:
            raise ValueError("Undefined residual variance")
        residual = (residual - residual.mean()) / std
        seed = int(canonical_digest([plan.seed, key, name]).split(":")[1][:16], 16)
        check = permutation_check(test[:, x], residual, plan, seed)
        if not math.isclose(check["score"], expected, abs_tol=1e-12, rel_tol=1e-7):
            raise ValueError("Recalculated dependence score does not match original")
        check["prediction_mse"] = float(np.mean((test[:, y] - prediction) ** 2))
        checks[name] = check
    direction, reason = adequacy_direction(checks)
    counts = []
    for column in values.T:
        counts.append(
            dict(
                unique_values=len(set(column)),
                zero_fraction=float(np.mean(column == 0)),
                largest_tie_fraction=max(Counter(column).values()) / len(column),
            )
        )
    return dict(direction=direction, reason=reason, checks=checks, column_quality=counts)


def _metrics(rows):
    total = math.fsum(r["weight"] for r in rows)
    correct = math.fsum(r["weight"] for r in rows if r["direction"] == r["reference"])
    wrong = math.fsum(
        r["weight"] for r in rows if r["direction"] is not None and r["direction"] != r["reference"]
    )
    answered = correct + wrong
    return dict(
        total_weight=total,
        coverage=answered / total,
        correct_yield=correct / total,
        wrong_yield=wrong / total,
        selective_accuracy=correct / answered if answered else None,
    )


def run(development_run, plan, output):
    root, inputs, summary, completion = _load_development(development_run)
    plan = AdequacyPlan.model_validate(plan)
    output = _destination(output, root)
    records = read_json(root / "evaluations.json")
    controls = read_json(root / "controls.json")
    sources = [r for r in records if r["variant"] == "baseline"] + controls["records"]

    # Hash all existing run bytes before/after, not only selected result files.
    def hashes():
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    before = hashes()
    protocol = dict(
        plan=plan.model_dump(mode="json"),
        development_completion=completion,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_files_sha256=before,
    )
    output.mkdir(parents=True, exist_ok=False)
    write_json_exclusive(output / "protocol.json", protocol)
    real, synthetic = [], []
    baseline = next(v for v in summary["variants"] if v["variant"] == "baseline")
    for record in sources:
        control = "family" in record
        result = diagnose_attempt(
            root / record["directory"], plan, [record["case_id"], record["split_seed"], control]
        )
        result.update(
            case_id=record["case_id"],
            split_seed=record["split_seed"],
            original_direction=record["result"]["predicted_direction"],
        )
        if control:
            result.update(
                family=record["family"],
                interpretation=record["interpretation"],
                correctness=(
                    None
                    if record["interpretation"] != "compatible" or result["direction"] is None
                    else result["direction"] == record["reference_direction"]
                ),
            )
            synthetic.append(result)
        else:
            case = next(c for c in inputs["cases"] if c["case_id"] == record["case_id"])
            detail = next(
                d
                for d in baseline["cases"]
                if d["case_id"] == record["case_id"] and d["split_seed"] == record["split_seed"]
            )
            result.update(
                pair_id=case["pair_id"],
                weight=case["weight"],
                reference=detail["reference"],
                reference_direction_mse=(record["mse"] or {}).get(detail["reference"]),
                opposite_direction_mse=(record["mse"] or {}).get(
                    "B_to_A" if detail["reference"] == "A_to_B" else "A_to_B"
                ),
            )
            real.append(result)
    if hashes() != before:
        raise ValueError("Original study artifacts changed during diagnosis")
    report = dict(
        scope="post-outcome exploratory diagnostic; not production or validation",
        real_cases=len(inputs["cases"]),
        real_split_outcomes=len(real),
        control_outcomes=len(synthetic),
        original_files_unchanged=True,
        primary=_metrics([r for r in real if r["split_seed"] == inputs["plan"]["primary_split"]]),
        splits=[
            dict(split_seed=s, metrics=_metrics([r for r in real if r["split_seed"] == s]))
            for s in inputs["plan"]["split_seeds"]
        ],
        real=real,
        controls=synthetic,
        limitations=[
            "Nonrejection is not independence or causal proof.",
            "Permutations assume exchangeability; real source assumptions are unverified.",
            "Four development pairs and repeated splits do not support general reliability claims.",
            "This exploratory classifier is not a new ANMResult or an S2 release.",
        ],
    )
    write_json_exclusive(output / "report.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("development-run", "plan", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    report = run(a.development_run, read_json(a.plan), a.output)
    print(json.dumps({"real_cases": report["real_cases"], "primary": report["primary"]}))


if __name__ == "__main__":
    main()
