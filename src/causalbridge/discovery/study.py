"""ANM-only development, explicit candidate freeze, and one frozen validation run.

No model calls. Numerical inputs never contain evaluator references. All outputs
are new; the published roster and historical attempts are never rewritten.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import random
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from causalbridge.discovery.anm import execute_anm_request, load_anm_artifacts
from causalbridge.discovery.anm_requests import (
    ANMConfig,
    load_anm_request,
    read_json,
    save_anm_request,
    write_json_exclusive,
)
from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.roster import check_roster
from causalbridge.evaluation.scoring import score_pilot
from causalbridge.schemas import Record

Rate = Annotated[float, Field(strict=True, ge=0, le=1)]
Positive = Annotated[float, Field(strict=True, gt=0)]
Seed = Annotated[int, Field(strict=True, ge=0)]


class Variant(Record):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    sample_limit: int = Field(strict=True, ge=100, le=2048)
    kernel_gamma: Positive = 1.0
    ridge_alpha: Positive = 0.1


class Plan(Record):
    version: Literal["anm-study-v1"] = "anm-study-v1"
    threshold: Annotated[float, Field(strict=True, ge=0)] = 0.001
    mapping_seed: Seed = 261
    sampling_seed: Seed = 262
    split_seeds: tuple[Seed, ...] = Field(min_length=2)
    primary_split: Seed = 261
    control_seed: Seed = 731
    variants: tuple[Variant, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def identities(self):
        if len(set(self.split_seeds)) != len(self.split_seeds):
            raise ValueError("Split seeds must be unique")
        if self.primary_split not in self.split_seeds:
            raise ValueError("Primary split must be scheduled")
        names = [v.name for v in self.variants]
        if len(names) != len(set(names)) or "baseline" not in names:
            raise ValueError("Unique variants and an explicit baseline are required")
        baseline = next(v for v in self.variants if v.name == "baseline")
        if baseline != Variant(name="baseline", sample_limit=128):
            raise ValueError("Baseline must retain the 128-row, gamma=1, alpha=0.1 settings")
        return self


class Criteria(Record):
    """Owner-specified targets; no defaults pretending that reliability is agreed."""

    decision_owner: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    min_coverage: Rate
    min_selective_accuracy: Rate
    max_wrong_yield: Rate
    min_sign_stability: Rate


def _source_digest():
    root = Path(__file__).resolve().parents[1]
    return canonical_digest(
        {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*.py"))
        }
    )


def _save(path, value):
    write_json_exclusive(Path(path), value)


def _environment():
    return {"python": platform.python_version(), "numpy": importlib.metadata.version("numpy")}


def _destination(output, *protected):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("Use a fresh output directory")
    if any(output == Path(p).resolve() or Path(p).resolve() in output.parents for p in protected):
        raise ValueError("Output must be outside protected original artifacts")
    return output


def _diagnostics(directory):
    """Recalculate held-out prediction MSE; do not change production fitting."""
    import numpy as np

    saved = load_anm_request(directory)
    data = np.asarray(saved.sample.rows)
    training, evaluation = data[list(saved.training_indices)], data[list(saved.evaluation_indices)]
    means, scales = training.mean(axis=0), training.std(axis=0)
    train, test = (training - means) / scales, (evaluation - means) / scales
    values = {}
    for name, x, y in (("A_to_B", 0, 1), ("B_to_A", 1, 0)):
        kernel = np.exp(-saved.config.kernel_gamma * (train[:, x, None] - train[:, x]) ** 2)
        coefficients = np.linalg.solve(
            kernel + saved.config.ridge_alpha * np.eye(len(train)), train[:, y]
        )
        prediction = (
            np.exp(-saved.config.kernel_gamma * (test[:, x, None] - train[:, x]) ** 2)
            @ coefficients
        )
        values[name] = float(np.mean((test[:, y] - prediction) ** 2))
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("Nonfinite diagnostic MSE")
    return values


def _fit(pair, variant, seed, plan, root):
    selected = select_pair(
        pair,
        SelectionSpec(
            method_limit=variant.sample_limit,
            display_limit=16,
            mapping_seed=plan.mapping_seed,
            sample_seed=plan.sampling_seed,
        ),
    )
    mapping = canonical_digest(
        {
            "case_id": pair.case_id,
            "order": selected.selection.column_order,
            "seed": plan.mapping_seed,
        }
    )
    directory = root / "attempts" / variant.name / pair.case_id / str(seed)
    config = ANMConfig(
        threshold=plan.threshold,
        maximum_rows=variant.sample_limit,
        sampling_seed=plan.sampling_seed,
        split_seed=seed,
        kernel_gamma=variant.kernel_gamma,
        ridge_alpha=variant.ridge_alpha,
        configuration_version="anm-study-v1-" + variant.name,
        threshold_selection_version="exploratory_fixed_not_calibrated",
    )
    request = save_anm_request(
        selected.method_rows,
        case_id=pair.case_id,
        ab_mapping_id=mapping,
        directory=directory,
        config=config,
    )
    result = execute_anm_request(directory)
    load_anm_artifacts(directory)
    entry = dict(
        case_id=pair.case_id,
        variant=variant.name,
        split_seed=seed,
        directory=str(directory.relative_to(root)),
        request_digest=canonical_digest(request.model_dump(mode="json")),
        result_digest=canonical_digest(result.model_dump(mode="json")),
        selection=selected.selection.model_dump(mode="json"),
        mse=_diagnostics(directory) if result.status == "ok" else None,
    )
    return entry, result


def _pair(snapshot, pair_id, case_id):
    rows = [
        tuple(map(float, line.split()))
        for line in (snapshot / f"pair{pair_id:04d}.txt").read_text().splitlines()
    ]
    return RuntimePair(
        case_id=case_id,
        variables=({"name": "Measurement one"}, {"name": "Measurement two"}),
        rows=rows,
    )


def _summary(records, inputs, role):
    """Join evaluator references only after completed numerical execution."""
    plan = Plan.model_validate(inputs["plan"])
    cases = inputs["cases"]
    results = []
    for variant in plan.variants:
        if variant.name not in inputs["executed_variants"]:
            continue
        by_seed = []
        details = []
        for seed in plan.split_seeds:
            group = [r for r in records if r["variant"] == variant.name and r["split_seed"] == seed]
            rows, mappings, evaluator = [], [], []
            manifest = canonical_digest(
                [
                    inputs["source_digest"],
                    role,
                    variant.name,
                    seed,
                    inputs["roster"],
                    inputs["plan"],
                ]
            )
            for r in group:
                case = next(c for c in cases if c["case_id"] == r["case_id"])
                result = r["result"]
                order = r["selection"]["column_order"]
                cause = 0 if case["reference_direction"] == "first_to_second" else 1
                reference = "A_to_B" if order[0] == cause else "B_to_A"
                rows.append(
                    dict(
                        manifest_id=manifest,
                        case_id=case["case_id"],
                        package="E4",
                        condition="ANM_ONLY",
                        ab_mapping_id=result["provenance"]["ab_mapping_id"],
                        package_digest=canonical_digest([r["request_digest"], r["result_digest"]]),
                        predicted_direction=result["predicted_direction"],
                        prediction_scorable=result["status"] == "ok",
                        outcome=result["reason_code"] or result["decision"],
                    )
                )
                mappings.append(
                    dict(
                        case_id=case["case_id"],
                        ab_mapping_id=result["provenance"]["ab_mapping_id"],
                        original_to_runtime_column_order=order,
                        mapping_seed=plan.mapping_seed,
                        source_digest=r["selection"]["source_digest"],
                    )
                )
                evaluator.append(case | {"source_digest": r["selection"]["source_digest"]})
                details.append(
                    dict(
                        case_id=case["case_id"],
                        split_seed=seed,
                        reference=reference,
                        margin=result["margin"],
                        score_ab=result["score_ab"],
                        score_ba=result["score_ba"],
                        selected_rows=result["provenance"]["selected_row_count"],
                        decision=result["predicted_direction"],
                        mse=r["mse"],
                        status=result["status"],
                    )
                )
            score = score_pilot(
                rows, evaluator, mappings, expected_conditions=[("E4", "ANM_ONLY")]
            )[0]
            by_seed.append(dict(split_seed=seed, metrics=score))
        stable = []
        for case in cases:
            margins = [d["margin"] for d in details if d["case_id"] == case["case_id"]]
            signs = [None if m is None or m == 0 else (1 if m > 0 else -1) for m in margins]
            stable.append(all(s is not None and s == signs[0] for s in signs))
        results.append(
            dict(
                variant=variant.name,
                primary=next(
                    s["metrics"] for s in by_seed if s["split_seed"] == plan.primary_split
                ),
                splits=by_seed,
                sign_stability=sum(stable) / len(stable),
                cases=details,
            )
        )
    return dict(
        role=role,
        case_count=len(cases),
        source_group_count=len({c["source_group"] for c in cases}),
        split_outcomes_per_case=len(plan.split_seeds),
        variants=results,
        note=f"{role.capitalize()} results describe only the assigned cases. "
        "Development is exploratory. Splits are dependent; no intervals or automatic winner.",
    )


def _controls(plan, output):
    """Four fresh datasets; swaps and split repetitions are not independent cases."""
    import numpy as np

    baseline = next(v for v in plan.variants if v.name == "baseline")
    records = []
    for index, name in enumerate(("cubic", "sine", "linear_gaussian", "heteroscedastic")):
        rng = np.random.default_rng(plan.control_seed + index)
        x = rng.normal(size=128) if name == "linear_gaussian" else rng.uniform(-2, 2, 128)
        noise = rng.normal(size=128)
        if name == "cubic":
            y = 0.5 * x**3 + 0.2 * noise
        elif name == "sine":
            y = 2 * np.sin(1.5 * x) + 0.2 * noise
        elif name == "linear_gaussian":
            y = x + noise
        else:
            y = 2 * np.tanh(x) + (0.2 + abs(x)) * noise
        for swapped in (False, True):
            pair = RuntimePair(
                case_id=f"D{9000 + 2 * index + int(swapped):04d}",
                variables=({"name": "Measurement one"}, {"name": "Measurement two"}),
                rows=list(zip(y, x, strict=True)) if swapped else list(zip(x, y, strict=True)),
            )
            for seed in plan.split_seeds:
                entry, result = _fit(pair, baseline, seed, plan, output / "controls")
                cause = 1 if swapped else 0
                reference = "A_to_B" if entry["selection"]["column_order"][0] == cause else "B_to_A"
                records.append(
                    entry
                    | dict(
                        family=name,
                        swapped=swapped,
                        directory="controls/" + entry["directory"],
                        result=result.model_dump(mode="json"),
                        reference_direction=reference,
                        correctness=(
                            None
                            if name in {"linear_gaussian", "heteroscedastic"}
                            or result.predicted_direction is None
                            else result.predicted_direction == reference
                        ),
                        interpretation="compatible"
                        if name in {"cubic", "sine"}
                        else "not_in_compatible_accuracy",
                    )
                )
    return dict(
        independent_datasets=4,
        records=records,
        note="Fresh baseline-only diagnostics; not the missing 48-dataset validation study. "
        "Swaps/splits reuse datasets. Nonidentified/violation controls have null accuracy.",
    )


def _execute(snapshot, manifest, roster, plan, output, role, chosen=None):
    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    _destination(output, snapshot)
    check_roster(manifest, snapshot, roster)
    if plan.mapping_seed != manifest["mapping_seed"]:
        raise ValueError("Plan mapping seed must match the frozen handoff")
    assigned = [r for r in roster["pairs"] if r["anm_use"] == role and r["scorable"]]
    if not assigned:
        raise ValueError("No scorable cases assigned to this role")
    ids = list(range(1000, 1000 + len(roster["pairs"])))
    random.Random(manifest["mapping_seed"]).shuffle(ids)
    case_ids = dict(zip(sorted(r["pair_id"] for r in roster["pairs"]), ids, strict=True))
    cases = [r | {"case_id": f"D{case_ids[r['pair_id']]:04d}"} for r in assigned]
    inputs = dict(
        manifest=manifest,
        roster=roster,
        plan=plan.model_dump(mode="json"),
        role=role,
        cases=cases,
        source_digest=_source_digest(),
        dependencies=_environment(),
        executed_variants=[v.name for v in plan.variants if chosen is None or v.name == chosen],
    )
    output.mkdir(parents=True, exist_ok=False)
    _save(output / "inputs.json", inputs)
    records = []
    for case in cases:
        pair = _pair(snapshot, case["pair_id"], case["case_id"])
        for variant in plan.variants:
            if variant.name not in inputs["executed_variants"]:
                continue
            for seed in plan.split_seeds:
                entry, result = _fit(pair, variant, seed, plan, output)
                records.append(entry | {"result": result.model_dump(mode="json")})
    _save(output / "evaluations.json", records)
    summary = _summary(records, inputs, role)
    _save(output / "summary.json", summary)
    controls = _controls(plan, output) if role == "development" else None
    if controls is not None:
        _save(output / "controls.json", controls)
    _save(
        output / "completion.json",
        {
            "inputs_digest": canonical_digest(inputs),
            "evaluations_digest": canonical_digest(records),
            "summary_digest": canonical_digest(summary),
            "controls_digest": canonical_digest(controls),
            "expected_attempts": len(cases)
            * len(inputs["executed_variants"])
            * len(plan.split_seeds),
        },
    )
    return summary


def run_development(snapshot, manifest, roster, plan, output):
    return _execute(snapshot, manifest, roster, Plan.model_validate(plan), output, "development")


def _load_development(root):
    root = Path(root).resolve()
    inputs, records, summary, completion = (
        read_json(root / name)
        for name in ("inputs.json", "evaluations.json", "summary.json", "completion.json")
    )
    if inputs["role"] != "development" or inputs["source_digest"] != _source_digest():
        raise ValueError("Development role or source identity changed")
    if inputs["dependencies"] != _environment():
        raise ValueError("Numerical dependencies changed")
    for name, value in (("inputs", inputs), ("evaluations", records), ("summary", summary)):
        if canonical_digest(value) != completion[name + "_digest"]:
            raise ValueError("Development artifact digest mismatch")
    plan = Plan.model_validate(inputs["plan"])
    if inputs["executed_variants"] != [v.name for v in plan.variants]:
        raise ValueError("Development variants changed")
    expected = {
        (c["case_id"], v.name, s)
        for c in inputs["cases"]
        for v in plan.variants
        for s in plan.split_seeds
    }
    actual = [(r["case_id"], r["variant"], r["split_seed"]) for r in records]
    if (
        len(actual) != len(set(actual))
        or set(actual) != expected
        or len(actual) != completion["expected_attempts"]
    ):
        raise ValueError("Development schedule is incomplete")
    for r in records:
        directory = (root / r["directory"]).resolve()
        if root not in directory.parents:
            raise ValueError("Attempt path escapes the development run")
        a = load_anm_artifacts(directory)
        if (
            canonical_digest(a.request.model_dump(mode="json")) != r["request_digest"]
            or canonical_digest(a.result.model_dump(mode="json")) != r["result_digest"]
            or a.result.model_dump(mode="json") != r["result"]
        ):
            raise ValueError("Development attempt does not match saved records")
    if _summary(records, inputs, "development") != summary:
        raise ValueError("Development summary cannot be reproduced")
    controls = read_json(root / "controls.json")
    if canonical_digest(controls) != completion["controls_digest"]:
        raise ValueError("Control artifact changed")
    for r in controls["records"]:
        directory = (root / r["directory"]).resolve()
        if root not in directory.parents:
            raise ValueError("Control path escapes the development run")
        a = load_anm_artifacts(directory)
        if canonical_digest(a.result.model_dump(mode="json")) != r["result_digest"]:
            raise ValueError("Control attempt changed")
    return root, inputs, summary, completion


def _gate(candidate, criteria):
    p = candidate["primary"]
    checks = dict(
        coverage=p["coverage"] >= criteria.min_coverage,
        selective_accuracy=p["selective_accuracy"] is not None
        and p["selective_accuracy"] >= criteria.min_selective_accuracy,
        wrong_yield=p["wrong_yield"] <= criteria.max_wrong_yield,
        sign_stability=candidate["sign_stability"] >= criteria.min_sign_stability,
    )
    return dict(passed=all(checks.values()), checks=checks)


def freeze_candidate(development_run, variant, criteria, output):
    root, inputs, summary, completion = _load_development(development_run)
    criteria = Criteria.model_validate(criteria)
    candidate = next((v for v in summary["variants"] if v["variant"] == variant), None)
    if candidate is None:
        raise ValueError("Candidate was not in the completed development plan")
    if not _gate(candidate, criteria)["passed"]:
        raise ValueError("Candidate does not meet the supplied development criteria")
    payload = dict(
        development_run=str(root),
        completion_digest=canonical_digest(completion),
        variant=variant,
        criteria=criteria.model_dump(mode="json"),
        source_digest=inputs["source_digest"],
    )
    output = _destination(output, root)
    output.mkdir(parents=True, exist_ok=False)
    _save(output / "freeze.json", dict(payload=payload, digest=canonical_digest(payload)))
    return payload


def run_validation(snapshot, frozen, output):
    frozen = Path(frozen).resolve()
    envelope = read_json(frozen / "freeze.json")
    payload = envelope["payload"]
    if (
        canonical_digest(payload) != envelope["digest"]
        or payload["source_digest"] != _source_digest()
    ):
        raise ValueError("Frozen candidate identity changed")
    _, inputs, _, completion = _load_development(payload["development_run"])
    if canonical_digest(completion) != payload["completion_digest"]:
        raise ValueError("Development run changed after candidate freeze")
    plan = Plan.model_validate(inputs["plan"])
    # Keep baseline in the immutable plan for identity; execute only the chosen variant.
    chosen = next(v for v in plan.variants if v.name == payload["variant"])
    criteria = Criteria.model_validate(payload["criteria"])
    check_roster(inputs["manifest"], Path(snapshot), inputs["roster"])
    if not any(c["anm_use"] == "validation" and c["scorable"] for c in inputs["roster"]["pairs"]):
        raise ValueError("No scorable validation cases")
    _destination(output, snapshot, frozen, payload["development_run"])
    _save(
        frozen / "validation_started.json",
        dict(output=str(Path(output).resolve()), freeze_digest=envelope["digest"]),
    )
    summary = _execute(
        snapshot, inputs["manifest"], inputs["roster"], plan, output, "validation", chosen.name
    )
    candidate = next(v for v in summary["variants"] if v["variant"] == chosen.name)
    verdict = _gate(candidate, criteria)
    _save(Path(output) / "decision.json", verdict)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dev = sub.add_parser("development")
    for key in ("snapshot", "manifest", "roster", "plan", "output"):
        dev.add_argument("--" + key, type=Path, required=True)
    freeze = sub.add_parser("freeze")
    for key in ("development-run", "criteria", "output"):
        freeze.add_argument("--" + key, type=Path, required=True)
    freeze.add_argument("--variant", required=True)
    validation = sub.add_parser("validation")
    for key in ("snapshot", "frozen", "output"):
        validation.add_argument("--" + key, type=Path, required=True)
    a = parser.parse_args()
    if a.command == "development":
        r = run_development(
            a.snapshot, read_json(a.manifest), read_json(a.roster), read_json(a.plan), a.output
        )
        print(json.dumps({k: r[k] for k in ("role", "case_count", "source_group_count")}))
    elif a.command == "freeze":
        r = freeze_candidate(a.development_run, a.variant, read_json(a.criteria), a.output)
        print(json.dumps({"frozen_variant": r["variant"]}))
    else:
        print(json.dumps(run_validation(a.snapshot, a.frozen, a.output)))


if __name__ == "__main__":
    main()
