"""Finish the opened pilot's cost/baseline package from original receipts, offline."""

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from causalbridge.discovery.anm_requests import read_json
from causalbridge.discovery.contracts import SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.discovery.loader import prepare_pilot
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.diagnosis import (
    diagnose_pilot,
    load_anm_results,
    load_experiment_receipts,
)
from causalbridge.evaluation.record_costs import generation_costs
from causalbridge.evaluation.scoring import score_pilot
from causalbridge.llm.parser import reject_duplicate_keys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path):
    return [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in path.read_text().splitlines()
    ]


def relocated_audit(pilot, original_root):
    """Explicit read-only lookup relocation; original receipt bytes remain untouched."""
    original_open = Path.open
    relocated = {}

    def read_original(path, mode="r", *args, **kwargs):
        try:
            relative = path.relative_to(original_root)
        except ValueError:
            return original_open(path, mode, *args, **kwargs)
        if ".." in relative.parts or any(flag in mode for flag in "wax+"):
            raise ValueError("Invalid or writable method relocation")
        local = pilot / "anm" / relative
        relocated[str(path)] = str(local)
        return original_open(local, mode, *args, **kwargs)

    with patch.object(Path, "open", read_original):
        result = audit_native(pilot / "experiment")
    result["read_only_method_relocation"] = relocated
    if not result["passed"]:
        raise ValueError("Original native audit failed: " + json.dumps(result["findings"]))
    return result


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def percent(value):
    return "undefined" if value is None else f"{100 * value:.1f}%"


def finish(pilot, snapshot, manifest, original_root, output):
    if output.exists() or any(
        output.resolve().is_relative_to(p.resolve()) for p in (pilot, snapshot)
    ):
        raise ValueError("Use a fresh output directory outside the original inputs")
    before = {str(p.relative_to(pilot)): sha(p) for p in sorted(pilot.rglob("*")) if p.is_file()}
    prepared = prepare_pilot(snapshot, read_json(manifest))
    journal = pilot / "experiment/events.jsonl"
    receipts = load_experiment_receipts(journal)
    audit = relocated_audit(pilot, original_root)
    events = lines(journal)
    starts = [e["data"] for e in events if e["kind"] == "native_started"]
    session = read_json(pilot / "session.json")
    selected = {
        p.case_id: select_pair(p, SelectionSpec(**session["selection"])).model_dump(mode="json")
        for p in prepared.pairs
    }
    expected = {(c, p, s) for c in selected for p in ("E1", "E2", "E3", "E4") for s in ("S0", "S1")}
    slots = []
    for start in starts:
        package = start["package"]
        evidence = package["evidence"]
        slots.append((evidence["case_id"], evidence["package"], start["condition"]["condition_id"]))
        if package["selected"] != selected[evidence["case_id"]]:
            raise ValueError("Saved sample differs from pinned source")
        if start["replicate_id"] != "0" or start["retry_id"] is not None:
            raise ValueError("Unexpected replicate/retry; declare an explicit accounting policy")
    if len(slots) != len(set(slots)) or set(slots) != expected:
        raise ValueError("Original schedule mismatch")
    rows, mappings = lines(pilot / "analysis.jsonl"), read_json(pilot / "evaluation_mapping.json")
    scores = score_pilot(rows, prepared.evaluator, mappings)
    if scores != read_json(pilot / "pilot-scores.json"):
        raise ValueError("Scores do not reproduce exactly")
    diagnosis = diagnose_pilot(
        rows,
        prepared.evaluator,
        mappings,
        load_anm_results(pilot / "anm"),
        experiment_receipts=receipts,
    )
    costs = generation_costs(events)
    total_input = sum(c["input_tokens"]["known_total"] for c in costs)
    total_output = sum(c["output_tokens"]["known_total"] for c in costs)
    first = read_json(pilot / "first-run-summary.json")
    if (total_input, total_output) != (
        first["new_usage"]["input_tokens"],
        first["new_usage"]["output_tokens"],
    ):
        raise ValueError("Unique journal usage differs from original first-run receipt")
    invocations = [read_json(p) for p in sorted((pilot / "experiment/invocations").glob("*.json"))]
    if sum(i["new_model_calls"] for i in invocations) != len(starts):
        raise ValueError("Invocation new-call counts differ from journal")
    by_cost = {(c["package"], c["condition"]): c for c in costs}
    baselines = []
    for score in scores:
        parent = by_cost.get((score["package"], score["condition"]))
        baselines.append(
            dict(
                **score,
                new_generation_records=parent["observed_generation_records"] if parent else 0,
                reused_s1_generation_records=by_cost[(score["package"], "S1")][
                    "observed_generation_records"
                ]
                if score["condition"] in ("S2", "SIMPLE_GATE")
                else 0,
            )
        )
    summary = dict(
        scope="opened_pilot_record_results_not_a_new_or_held_out_experiment",
        cases=len(selected),
        source_groups=len({r["source_group"] for r in prepared.evaluator}),
        scheduled_primary_generations=len(starts),
        unique_input_tokens=total_input,
        unique_output_tokens=total_output,
        token_observation_missing_count=sum(
            c[k]["missing_count"] for c in costs for k in ("input_tokens", "output_tokens")
        ),
        summed_client_generation_seconds=math.fsum(
            c["generation_latency_seconds"]["known_total"] for c in costs
        ),
        generation_latency_missing_count=sum(
            c["generation_latency_seconds"]["missing_count"] for c in costs
        ),
        invocation_new_call_counts=[i["new_model_calls"] for i in invocations],
        failures=dict(
            Counter(
                stage
                for c in costs
                for stage, count in c["failure_stage_counts"].items()
                for _ in range(count)
            )
        ),
        checker_latency_seconds=None,
        anm_fit_latency_seconds=None,
        monetary_cost=None,
        unmeasured_notice=(
            "Checker and ANM wall times were not recorded; local dollar cost is unknown. "
            "Zero additional generation is not zero end-to-end compute."
        ),
        new_scientific_model_calls=0,
        new_scientific_anm_fits=0,
        independent_human_annotation_complete=False,
    )
    if any(sha(pilot / name) != value for name, value in before.items()):
        raise ValueError("Original input changed")
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (
        ("audit.json", audit),
        ("session.json", session),
        ("summary.json", summary),
        ("generation-costs.json", costs),
        ("baseline-comparisons.json", baselines),
        ("diagnosis.json", diagnosis),
        ("evaluator.json", prepared.evaluator),
    ):
        write(output / name, value)
    with (output / "generation-costs.csv").open("w") as stream:
        fields = [
            "package",
            "condition",
            "scheduled_attempts",
            "input_tokens",
            "output_tokens",
            "generation_seconds",
            "mean_seconds",
            "median_seconds",
            "p95_seconds",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for c in costs:
            writer.writerow(
                dict(
                    package=c["package"],
                    condition=c["condition"],
                    scheduled_attempts=c["scheduled_attempts"],
                    input_tokens=c["input_tokens"]["total"],
                    output_tokens=c["output_tokens"]["total"],
                    generation_seconds=c["generation_latency_seconds"]["total"],
                    mean_seconds=c["mean_generation_latency_seconds"],
                    median_seconds=c["median_generation_latency_seconds"],
                    p95_seconds=c["p95_generation_latency_seconds"],
                )
            )
    with (output / "baseline-comparisons.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(baselines[0]))
        writer.writeheader()
        writer.writerows(baselines)
    text = [
        "# Saved pilot: measured resources and baseline comparisons",
        "",
        "Opened 17-pair, seven-source-group exploratory pilot. Original source, samples, "
        "journal/method bindings, score lineage and scores were reverified on current main. "
        "No new predictions or numerical fits. Independent human annotation is deferred.",
        "",
        "## Measured generation resources",
        "",
        f"Unique original generations: {len(starts)}. Input tokens: {total_input:,}; "
        f"output tokens: {total_output:,}. Summed client generation latency: "
        f"{summary['summed_client_generation_seconds']:.2f} seconds "
        f"({summary['summed_client_generation_seconds'] / 60:.2f} minutes). "
        "This is a sum of client "
        "request latencies, not a measured full-pipeline wall time. Original invocation "
        "and resume summaries are not added to journal receipts.",
        "",
        "| Package | Prompt | Calls | Input tokens | Output tokens | "
        "Total seconds | Median seconds | P95 seconds |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for c in costs:
        text.append(
            f"| {c['package']} | {c['condition']} | {c['observed_generation_records']} | "
            f"{c['input_tokens']['total']:,} | {c['output_tokens']['total']:,} | "
            f"{c['generation_latency_seconds']['total']:.2f} | "
            f"{c['median_generation_latency_seconds']:.2f} | "
            f"{c['p95_generation_latency_seconds']:.2f} |"
        )
    text += [
        "",
        "Generation/parsing/binding failures: zero in this saved pilot. "
        "Checker/ANM wall times and local monetary cost are unmeasured, not zero. "
        "S2 and SIMPLE_GATE reuse S1 generations; ANM-only reuses the cached method result. "
        "Their additional generation count is zero. Existing parent generation/method costs "
        "still matter when comparing end-to-end systems.",
        "",
        "## Explicit baseline comparisons",
        "",
        "All percentages are benchmark-weighted with all 17 cases retained. Answered "
        "accuracy is undefined with no releases. Gate means SIMPLE_GATE.",
        "",
        "| Package | Condition | Coverage | Correct yield | Wrong yield | "
        "Answered accuracy | New generations | Reused S1 generations |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for b in baselines:
        text.append(
            f"| {b['package']} | {b['condition']} | "
            + " | ".join(
                percent(b[k])
                for k in ("coverage", "correct_yield", "wrong_yield", "selective_accuracy")
            )
            + f" | {b['new_generation_records']} | {b['reused_s1_generation_records']} |"
        )
    text += [
        "",
        "E1–E4 SIMPLE_GATE retains S1's directions on this pilot. E4 S0/S1/S2/"
        "SIMPLE_GATE/ANM-only are directionally identical: 14 answers, six correct, eight wrong, "
        "three abstentions. The checker removes one wrong and two correct E1 answers, and "
        "two wrong E3 answers. It changes no E4 direction. These are completed findings, "
        "not a reason to tune the opened cohort until a positive result appears.",
        "",
        "## Before the midterm rerun",
        "",
        "1. Treat a same-cohort rerun as repeatability/sensitivity, not a fresh final test. "
        "Preserve the original pilot and use a new output directory.",
        "2. Freeze exact code/model artifact, prompts/schema, source hashes, selections, "
        "ANM configuration, threshold, primary seed and call budget before generation. "
        "Log any changed condition order or prompt as a protocol change; do not overwrite history.",
        "3. Inspect existing templates for zero-based row-reference clarity and explicit "
        "method caveats. Any wording change is a new version, not an unreported correction.",
        "4. Produce a compact controlled-checker perturbation table from existing fixtures, "
        "separate from natural error prevalence; close the Track A live-model gap if feasible.",
        "5. Report ANM as a bounded diagnostic with weak observed real-data performance. "
        "Anish's synthetic checks support numerical fidelity; parameter tuning has not "
        "established robust transfer. A new method/preprocessing idea needs a specific "
        "mechanistic rationale and clean evaluation, not an unbounded pre-midterm search.",
        "",
    ]
    (output / "report.md").write_text("\n".join(text))
    root = Path(__file__).resolve().parents[1]
    write(
        output / "provenance.json",
        dict(
            original_pilot_files_sha256=before,
            raw_manifest_sha256=sha(manifest),
            source_sha256={
                str(p.relative_to(root)): sha(p)
                for p in (Path(__file__), root / "src/causalbridge/evaluation/record_costs.py")
            },
            output_sha256={p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
            preparation_code_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            preparation_worktree_status=subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root, text=True
            ),
        ),
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pilot", "snapshot", "manifest", "original-method-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            finish(
                args.pilot, args.snapshot, args.manifest, args.original_method_root, args.output
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
