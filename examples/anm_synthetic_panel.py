"""Fixed synthetic panel: retain every mechanism, seed, error and abstention.

No tuning, real validation data or LLM calls. A narrow demonstration gate is
specified before fitting; it is not certification of real-world reliability.
"""

import argparse
import hashlib
import importlib.metadata
import itertools
import json
import math
import platform
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from causalbridge.discovery.anm import execute_anm_request, load_anm_artifacts
from causalbridge.discovery.anm_requests import (
    ANMConfig,
    read_json,
    save_anm_request,
    write_json_exclusive,
)
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.schemas import Record

COMPATIBLE = ("cubic", "quadratic", "sine", "tanh")
CONTROLS = ("linear_gaussian", "confounded_gaussian", "heteroscedastic")
Rate = Annotated[float, Field(strict=True, ge=0, le=1)]


class Gate(Record):
    min_coverage: Rate
    min_answer_accuracy: Rate
    min_family_coverage: Rate
    min_family_answer_accuracy: Rate


class Plan(Record):
    version: Literal["anm-synthetic-panel-v1"]
    master_seed: int = Field(strict=True, ge=0)
    replicates_per_partition: int = Field(strict=True, ge=1, le=10)
    sample_sizes: tuple[int, ...]
    split_seeds: tuple[int, ...]
    primary_size: int
    primary_split: int
    noise_scales: tuple[float, ...]
    threshold: Annotated[float, Field(strict=True, ge=0)]
    kernel_gamma: Annotated[float, Field(strict=True, gt=0)]
    ridge_alpha: Annotated[float, Field(strict=True, gt=0)]
    demonstration_gate: Gate

    @model_validator(mode="after")
    def schedule(self):
        if (
            not self.sample_sizes
            or any(n < 100 or n > 2048 for n in self.sample_sizes)
            or len(set(self.sample_sizes)) != len(self.sample_sizes)
            or self.primary_size not in self.sample_sizes
        ):
            raise ValueError("Invalid sample-size schedule")
        if (
            not self.split_seeds
            or any(s < 0 for s in self.split_seeds)
            or len(set(self.split_seeds)) != len(self.split_seeds)
            or self.primary_split not in self.split_seeds
        ):
            raise ValueError("Invalid split schedule")
        if not self.noise_scales or any(s <= 0 for s in self.noise_scales):
            raise ValueError("Positive noise scales required")
        return self


def cases(plan):
    """Each partition gets independent draws of every fixed mechanism setting."""
    result = []
    for partition, family, scale, direction, rep in itertools.product(
        ("development", "confirmation"),
        COMPATIBLE + CONTROLS,
        plan.noise_scales,
        ("A_to_B", "B_to_A"),
        range(plan.replicates_per_partition),
    ):
        for noise in ("gaussian", "laplace") if family in COMPATIBLE else ("gaussian",):
            result.append(
                dict(
                    case_id=f"D{5000 + len(result):04d}",
                    partition=partition,
                    family=family,
                    scale=scale,
                    construction_direction=direction,
                    replicate=rep,
                    noise=noise,
                    seed=plan.master_seed + 100 * len(result),
                    compatible=family in COMPATIBLE,
                )
            )
    return result


def generate(case, n):
    rng = np.random.default_rng(case["seed"])
    x = (
        rng.uniform(-math.sqrt(3), math.sqrt(3), n)
        if case["family"] in {"quadratic", "sine", "heteroscedastic"}
        else rng.normal(size=n)
    )
    noise = (
        rng.laplace(scale=1 / math.sqrt(2), size=n)
        if case["noise"] == "laplace"
        else rng.normal(size=n)
    )
    sigma = case["scale"]
    family = case["family"]
    if family == "cubic":
        y = 0.5 * x**3 + sigma * noise
    elif family == "quadratic":
        y = 0.8 * x**2 + sigma * noise
    elif family == "sine":
        y = 2 * np.sin(1.5 * x) + sigma * noise
    elif family == "tanh":
        y = 2 * np.tanh(1.5 * x) + sigma * noise
    elif family == "linear_gaussian":
        y = x + sigma * noise
    elif family == "heteroscedastic":
        y = 2 * np.tanh(1.5 * x) + (0.2 + sigma * abs(x)) * noise
    else:
        latent = x
        x = latent + 0.5 * rng.normal(size=n)
        y = 0.8 * x + latent + sigma * noise
    rows = np.column_stack((x, y))
    if case["construction_direction"] == "B_to_A":
        rows = rows[:, ::-1]
    return rows.tolist()


def metrics(rows):
    answers = [r for r in rows if r["direction"] is not None]
    correct = sum(r["direction"] == r["reference"] for r in answers)
    return dict(
        cases=len(rows),
        answered=len(answers),
        correct=correct,
        wrong=len(answers) - correct,
        abstained=sum(r["status"] == "ok" and r["direction"] is None for r in rows),
        errors=sum(r["status"] != "ok" for r in rows),
        coverage=len(answers) / len(rows),
        answer_accuracy=correct / len(answers) if answers else None,
        correct_yield=correct / len(rows),
        wrong_yield=(len(answers) - correct) / len(rows),
    )


def summarize(records, plan):
    cells = []
    for partition, n, split in itertools.product(
        ("development", "confirmation"), plan.sample_sizes, plan.split_seeds
    ):
        group = [
            r
            for r in records
            if r["partition"] == partition and r["n"] == n and r["split"] == split
        ]
        compatible = [r for r in group if r["compatible"]]
        cells.append(
            dict(
                partition=partition,
                n=n,
                split=split,
                compatible=metrics(compatible),
                families={
                    f: metrics([r for r in compatible if r["family"] == f]) for f in COMPATIBLE
                },
                controls={
                    f: dict(
                        cases=sum(r["family"] == f for r in group),
                        answers=sum(r["family"] == f and r["direction"] is not None for r in group),
                        causal_accuracy=None,
                    )
                    for f in CONTROLS
                },
            )
        )
    primary = next(
        c
        for c in cells
        if c["partition"] == "confirmation"
        and c["n"] == plan.primary_size
        and c["split"] == plan.primary_split
    )
    gate = plan.demonstration_gate
    m = primary["compatible"]
    checks = dict(
        coverage=m["coverage"] >= gate.min_coverage,
        accuracy=m["answer_accuracy"] is not None
        and m["answer_accuracy"] >= gate.min_answer_accuracy,
        family_coverage=all(
            f["coverage"] >= gate.min_family_coverage for f in primary["families"].values()
        ),
        family_accuracy=all(
            f["answer_accuracy"] is not None
            and f["answer_accuracy"] >= gate.min_family_answer_accuracy
            for f in primary["families"].values()
        ),
        no_errors=all(r["status"] == "ok" for r in records),
        column_swaps=all(r.get("swap_passed", True) for r in records),
    )
    return dict(
        cells=cells,
        demonstration_gate=dict(passed=all(checks.values()), checks=checks),
        limitations=[
            "Synthetic fixed mechanisms; not real-data recovery or a production repair.",
            "Confirmation has fresh draws, not new function/noise settings.",
            "Sample sizes, splits and swaps reuse datasets; do not pool as independent cases.",
            "Independent additive noise is generated; exact identification is not proved.",
            "Controls have undefined causal accuracy; operational releases remain reported.",
        ],
    )


def run(plan, output):
    plan = Plan.model_validate(plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    schedule = cases(plan)
    source = Path(__file__).read_bytes()
    package = Path(__file__).resolve().parents[1] / "src/causalbridge"
    protocol = dict(
        plan=plan.model_dump(mode="json"),
        schedule=schedule,
        source_sha256=hashlib.sha256(source).hexdigest(),
        producer_sha256={
            name: hashlib.sha256((package / "discovery" / name).read_bytes()).hexdigest()
            for name in ("anm.py", "anm_requests.py")
        },
        environment=dict(
            python=platform.python_version(), numpy=importlib.metadata.version("numpy")
        ),
    )
    write_json_exclusive(output / "protocol.json", protocol)
    records = []
    for case in schedule:
        full_rows = generate(case, max(plan.sample_sizes))
        datafile = output / (case["case_id"] + ".json")
        write_json_exclusive(datafile, dict(case=case, rows=full_rows))
        for n, split in itertools.product(plan.sample_sizes, plan.split_seeds):
            config = ANMConfig(
                threshold=plan.threshold,
                maximum_rows=n,
                split_seed=split,
                sampling_seed=case["seed"],
                kernel_gamma=plan.kernel_gamma,
                ridge_alpha=plan.ridge_alpha,
                configuration_version=plan.version,
                threshold_selection_version="fixed_exploratory_0.001",
            )
            path = output / "attempts" / case["case_id"] / str(n) / str(split)
            request = save_anm_request(
                full_rows[:n],
                case_id=case["case_id"],
                ab_mapping_id=canonical_digest([case["case_id"], "original"]),
                directory=path,
                config=config,
            )
            result = execute_anm_request(path)
            load_anm_artifacts(path)
            record = case | dict(
                n=n,
                split=split,
                status=result.status,
                direction=result.predicted_direction,
                reference=case["construction_direction"] if case["compatible"] else None,
                score_ab=result.score_ab,
                score_ba=result.score_ba,
                margin=result.margin,
                directory=str(path.relative_to(output)),
                data_sha256=hashlib.sha256(datafile.read_bytes()).hexdigest(),
                request_digest=canonical_digest(request.model_dump(mode="json")),
                result_digest=canonical_digest(result.model_dump(mode="json")),
            )
            if split == plan.primary_split:
                swapped = output / "swaps" / case["case_id"] / str(n)
                save_anm_request(
                    [row[::-1] for row in full_rows[:n]],
                    case_id=case["case_id"],
                    ab_mapping_id=canonical_digest([case["case_id"], "swapped"]),
                    directory=swapped,
                    config=config,
                )
                other = execute_anm_request(swapped)
                record["swap_passed"] = other.status == result.status and (
                    result.status != "ok"
                    or all(
                        math.isclose(a, b, abs_tol=1e-10, rel_tol=1e-7)
                        for a, b in (
                            (result.score_ab, other.score_ba),
                            (result.score_ba, other.score_ab),
                            (result.margin, -other.margin),
                        )
                    )
                )
            records.append(record)
    summary = summarize(records, plan)
    write_json_exclusive(output / "results.json", records)
    write_json_exclusive(output / "summary.json", summary)
    write_json_exclusive(
        output / "completion.json",
        dict(
            protocol_digest=canonical_digest(protocol),
            results_digest=canonical_digest(records),
            summary_digest=canonical_digest(summary),
            independent_datasets=len(schedule),
            original_attempts=len(records),
            swap_attempts=sum("swap_passed" in r for r in records),
        ),
    )
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(read_json(a.plan), a.output)["demonstration_gate"]))


if __name__ == "__main__":
    main()
