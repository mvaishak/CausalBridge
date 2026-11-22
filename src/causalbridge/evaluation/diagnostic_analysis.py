"""Offline diagnosis and paired, source-clustered analysis; never invokes a model."""

import csv
import json
import random
import statistics
import tarfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from causalbridge.discovery.schemas import DirectionPrediction, canonical_digest
from causalbridge.evaluation.diagnostic_protocol import (
    ABLATION,
    PILOT,
    pilot_source,
    read,
    sha,
    validate_plan,
    write,
)
from causalbridge.evaluation.diagnostic_runtime import decode
from causalbridge.llm.parser import parse_json

KINDS = ("correct", "wrong", "abstention", "execution_failure")


def outcome(prediction, failure, gold):
    if failure or prediction is None:
        return "execution_failure"
    if prediction["predicted_direction"] is None:
        return "abstention"
    return "correct" if prediction["predicted_direction"] == gold else "wrong"


def fraction(n, d):
    return {"numerator": n, "denominator": d, "rate": n / d if d else None}


def summarize(rows):
    """Exclusive upstream outcomes and orthogonal checker rejection, explicit denominators."""
    counts = {k: sum(r["outcome"] == k for r in rows) for k in KINDS}
    n = len(rows)
    rejected = sum(r.get("rejected", False) for r in rows)
    released = [r for r in rows if r.get("released", False)]
    total_weight = sum(r["weight"] for r in rows)
    weighted = {k: sum(r["weight"] for r in rows if r["outcome"] == k) for k in KINDS}
    return {
        "n": n,
        "counts": counts,
        "rates_before_verification": {k: fraction(v, n) for k, v in counts.items()},
        "directional_accuracy_before_verification": fraction(
            counts["correct"], counts["correct"] + counts["wrong"]
        ),
        "coverage_before_verification": fraction(counts["correct"] + counts["wrong"], n),
        "verification_rejection": fraction(rejected, n),
        "rejected_underlying": dict(Counter(r["outcome"] for r in rows if r.get("rejected"))),
        "after_verification": {
            "released": len(released),
            "correct_yield": fraction(sum(r["outcome"] == "correct" for r in released), n),
            "wrong_yield": fraction(sum(r["outcome"] == "wrong" for r in released), n),
            "coverage": fraction(len(released), n),
            "directional_accuracy": fraction(
                sum(r["outcome"] == "correct" for r in released), len(released)
            ),
        },
        "benchmark_weighted_yields_before_verification": {
            k: fraction(v, total_weight) for k, v in weighted.items()
        },
    }


def propagation(e3, e4, gold, anm):
    wrong_anm = anm is not None and anm != gold
    return {
        "wrong_anm": wrong_anm,
        "copied_wrong": wrong_anm and e4["direction"] == anm and not e4["failure"],
        "resisted_correct": wrong_anm and e4["direction"] == gold and not e4["failure"],
        "protective_abstention": wrong_anm and e4["direction"] is None and not e4["failure"],
        "execution_failure": wrong_anm and bool(e4["failure"]),
        "harm_eligible": wrong_anm and e3["direction"] == gold and not e3["failure"],
        "harmful_switch": wrong_anm
        and e3["direction"] == gold
        and not e3["failure"]
        and e4["direction"] == anm
        and not e4["failure"],
        "correct_anm": anm == gold,
        "accepted_correct_anm": anm == gold and e4["direction"] == gold and not e4["failure"],
    }


def diagnose(output):
    """Independently join original/thinking archived final contents to frozen evaluator labels."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases, starts = pilot_source()
    truths = {c["case_id"]: c for c in cases}
    observations = []
    with zipfile.ZipFile(PILOT) as z:
        events = [
            json.loads(line)
            for line in z.read("real-pilot-01/experiment/events.jsonl").splitlines()
        ]
    for event in events:
        if event["kind"] != "native_finished":
            continue
        execution = event["data"]["execution"]
        ev = execution["evidence"]
        p = execution["prediction"]
        if p:
            body = json.loads(execution["generation"]["raw_response"])
            if body["message"]["content"] != execution["generation"]["text"]:
                raise ValueError("Original HTTP/final-text mismatch")
            parsed = parse_json(body["message"]["content"], DirectionPrediction)
            if parsed.model_dump(mode="json") != p:
                raise ValueError("Historical prediction/raw mismatch")
        observations.append(
            {
                "experiment": "original_4096_512",
                "style": execution["prompt_condition"]["condition_id"],
                "think": False,
                "case_id": ev["case_id"],
                "package": ev["package"],
                "direction": p["predicted_direction"] if p else None,
                "failure": execution["error"],
                "claims": p["claims"] if p else [],
                "explanation": p["reason_code"] if p else None,
                "thinking": None,
            }
        )
    archive_manifest = read(ABLATION.parent / "manifest.json")
    if sha(ABLATION) != archive_manifest["sha256"]:
        raise ValueError("Thinking archive checksum mismatch")
    with tarfile.open(ABLATION, "r:gz") as tar:
        for member in tar.getmembers():
            parts = member.name.split("/")
            if not member.isfile() or any(p.startswith("._") for p in parts):
                continue
            if (
                "/full/" not in member.name
                or not member.name.endswith(".json")
                or member.name.endswith((".request.json", "manifest.json"))
            ):
                continue
            row = json.load(tar.extractfile(member))
            p = row["prediction"]
            raw = json.loads(row["raw_response"])
            start = starts[row["case_id"], row["package"], row["style"]]
            if (
                row["request"]["messages"] != start["messages"]
                or row["request"]["format"] != start["output_schema"]
            ):
                raise ValueError("Thinking request differs from archived prompt/schema")
            if (
                p
                and parse_json(raw["message"]["content"], DirectionPrediction).model_dump(
                    mode="json"
                )
                != p
            ):
                raise ValueError("Thinking prediction/raw mismatch")
            observations.append(
                {
                    "experiment": "matched_8192_4096",
                    "style": row["style"],
                    "think": row["think"],
                    "case_id": row["case_id"],
                    "package": row["package"],
                    "direction": p["predicted_direction"] if p else None,
                    "failure": row["failure"],
                    "claims": p["claims"] if p else [],
                    "explanation": p["reason_code"] if p else None,
                    "thinking": raw.get("message", {}).get("thinking"),
                }
            )
    if len(observations) != 408:
        raise ValueError("Expected 136 historical + 272 thinking observations")
    index = {}
    for row in observations:
        key = (row["experiment"], row["style"], row["think"], row["case_id"], row["package"])
        if key in index:
            raise ValueError("Duplicate historical observation")
        index[key] = row
    transitions = []
    groups = defaultdict(list)
    for row in observations:
        case = truths[row["case_id"]]
        row["outcome"] = outcome(
            {"predicted_direction": row["direction"]}, row["failure"], case["gold"]
        )
        row["weight"] = case["weight"]
        if row["package"] != "E4":
            continue
        e3 = index[row["experiment"], row["style"], row["think"], row["case_id"], "E3"]
        transition = {
            "experiment": row["experiment"],
            "style": row["style"],
            "think": row["think"],
            "case_id": row["case_id"],
            "gold": case["gold"],
            "anm": case["anm_direction"],
            "e3": e3,
            "e4": row,
            **propagation(e3, row, case["gold"], case["anm_direction"]),
        }
        transitions.append(transition)
        groups[row["experiment"], row["style"], row["think"]].append(transition)
    rates = []
    for (experiment, style, think), rows in groups.items():
        count = Counter(
            {
                k: sum(bool(r[k]) for r in rows)
                for k in (
                    "wrong_anm",
                    "copied_wrong",
                    "resisted_correct",
                    "protective_abstention",
                    "execution_failure",
                    "harm_eligible",
                    "harmful_switch",
                    "correct_anm",
                    "accepted_correct_anm",
                )
            }
        )
        rates.append(
            {
                "experiment": experiment,
                "style": style,
                "think": think,
                "wrong_copy": fraction(count["copied_wrong"], count["wrong_anm"]),
                "resistance": fraction(count["resisted_correct"], count["wrong_anm"]),
                "protective_abstention": fraction(
                    count["protective_abstention"], count["wrong_anm"]
                ),
                "wrong_anm_execution_failure": fraction(
                    count["execution_failure"], count["wrong_anm"]
                ),
                "harmful_switch": fraction(count["harmful_switch"], count["harm_eligible"]),
                "correct_tool_acceptance": fraction(
                    count["accepted_correct_anm"], count["correct_anm"]
                ),
            }
        )
    write(output / "observations.json", observations)
    write(output / "transitions.json", transitions)
    write(
        output / "metrics.json",
        {
            "observations": len(observations),
            "transition_rows": len(transitions),
            "propagation": rates,
            "source_sha256": {str(PILOT): sha(PILOT), str(ABLATION): sha(ABLATION)},
            "scope": (
                "Observed output transitions; not proof of internal reasoning or a"
                " causal effect of historical budget differences."
            ),
        },
    )
    # A structured, unfilled human annotation sheet; no automated inference of cognition.
    with (output / "manual-review.csv").open("w", newline="") as handle:
        fields = [
            "experiment",
            "style",
            "think",
            "case_id",
            "gold",
            "anm",
            "reviewer",
            "mentions_method",
            "mentions_assumptions",
            "identifies_conflict",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in transitions:
            writer.writerow({k: row[k] for k in fields if k in row})
    lines = [
        "# Saved-evidence diagnosis",
        "",
        (
            "Automated joins of preserved raw final outputs. Human explanation"
            " coding remains unfilled in manual-review.csv."
        ),
        "",
        (
            "| Run | Style | Think | Wrong copied | Correct resistance | Prote"
            "ctive abstention | Wrong-ANM failures | Harmful switches | Correc"
            "t-tool acceptance |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rates:
        values = [
            (
                f"{r[k]['numerator']}/{r[k]['denominator']}"
                if r[k]["denominator"]
                else "undefined (0/0)"
            )
            for k in (
                "wrong_copy",
                "resistance",
                "protective_abstention",
                "wrong_anm_execution_failure",
                "harmful_switch",
                "correct_tool_acceptance",
            )
        ]
        lines.append(
            f"| {r['experiment']} | {r['style']} | {r['think']} | " + " | ".join(values) + " |"
        )
    lines += [
        "",
        (
            "Abstention, execution failure and checker rejection are different"
            ". These transition metrics describe upstream predictions. Histori"
            "cal budgets differ; the new controlled-cue protocol changes the p"
            "rompt/schema and is not a historical accuracy replication."
        ),
        "",
        (
            "The ablation's empty typed claims motivate a required diagnostic-"
            "attribution field in the new isolated schema. Attribution consist"
            "ency still cannot certify causal truth."
        ),
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    return {
        "observations": len(observations),
        "transitions": len(transitions),
        "propagation": rates,
    }


def paired_comparison(rows, left, right, think, cfg, *, right_think=None):
    """Source-family bootstrap of matched case differences; all scheduled cases retained."""
    right_think = think if right_think is None else right_think
    index = {(r["case_id"], r["arm"], r["think"]): r for r in rows}
    cases = sorted({r["case_id"] for r in rows})
    groups = defaultdict(list)
    transitions = []
    for cid in cases:
        a, b = index[cid, left, think], index[cid, right, right_think]
        groups[a["source_group"]].append((a, b))
        transitions.append(
            {
                "case_id": cid,
                "left_outcome": a["outcome"],
                "right_outcome": b["outcome"],
                "left_direction": a["prediction"]["predicted_direction"]
                if a["prediction"]
                else None,
                "right_direction": b["prediction"]["predicted_direction"]
                if b["prediction"]
                else None,
            }
        )

    def differences(pairs):
        n = len(pairs)
        return {
            kind: sum((b["outcome"] == kind) - (a["outcome"] == kind) for a, b in pairs) / n
            for kind in KINDS
        }

    pairs = [p for group in groups.values() for p in group]
    observed = differences(pairs)
    samples = {kind: [] for kind in KINDS}
    rng = random.Random(cfg["bootstrap_seed"])
    names = sorted(groups)
    for _ in range(cfg["bootstrap_draws"]):
        draw = [p for name in rng.choices(names, k=len(names)) for p in groups[name]]
        for kind, value in differences(draw).items():
            samples[kind].append(value)
    intervals = {}
    for kind, values in samples.items():
        values.sort()
        intervals[kind] = [
            values[int(0.025 * len(values))],
            values[min(int(0.975 * len(values)), len(values) - 1)],
        ]
    return {
        "left": left,
        "right": right,
        "think": think,
        "right_think": right_think,
        "n_pairs": len(cases),
        "source_groups": len(groups),
        "yield_difference_right_minus_left": observed,
        "exploratory_source_group_intervals": intervals,
        "transitions": transitions,
    }


def analyze(plan, run_dir, output):
    """Replay all raw replies; reject partial/tampered artifacts rather than fill gaps."""
    plan, run_dir, output = Path(plan), Path(run_dir), Path(output)
    manifest, requests = validate_plan(plan)
    run_info = read(run_dir / "run.json")
    if run_info["mode"] not in ("live", "scripted"):
        raise ValueError("Unknown run mode")
    if run_info["plan"] != manifest or read(run_dir / "requests.json") != requests:
        raise ValueError("Run/plan mismatch")
    if run_info["mode"] == "live":
        for name in ("model-before.json", "model-after.json"):
            tags = read(run_dir / name)["tags"]
            if not any(
                m["name"] == manifest["protocol"]["model"]
                and m["digest"] == manifest["protocol"]["model_digest"]
                for m in tags["models"]
            ):
                raise ValueError("Unverified model identity")
    output.mkdir(parents=True, exist_ok=False)
    metadata = read(plan / "evaluator.json")
    rows = []
    expected = {r["trial_id"].split(":")[-1] + ".json" for r in requests}
    if {p.name for p in (run_dir / "records").glob("*.json")} != expected:
        raise ValueError("Missing or unexpected response records")
    for req, meta in zip(requests, metadata, strict=True):
        filename = req["trial_id"].split(":")[-1] + ".json"
        record = read(run_dir / "records" / filename)
        if record["trial_id"] != req["trial_id"] or record["request_digest"] != canonical_digest(
            req["payload"]
        ):
            raise ValueError("Saved request binding mismatch")
        raw_path = run_dir / "raw" / filename
        p = checker = None
        if raw_path.exists():
            raw = read(raw_path)
            if record["raw_digest"] != canonical_digest(raw):
                raise ValueError("Raw digest mismatch")
            try:
                p, checker = decode(raw, req["payload"], manifest["protocol"]["model"])
            except (ValueError, KeyError, TypeError):
                if not record["failure"]:
                    raise ValueError("Invalid raw response recorded as success") from None
        elif not record["failure"] or record["raw_digest"] is not None:
            raise ValueError("Missing raw response without transport failure")
        if (
            p != record["prediction"]
            or checker != record["checker"]
            or (p is not None and record["failure"])
        ):
            raise ValueError("Stored prediction/check does not match raw replay")
        row = {
            **meta,
            "prediction": p,
            "failure": record["failure"],
            "checker": checker,
            "outcome": outcome(p, record["failure"], meta["gold"]),
            "rejected": checker is not None and not checker["passed"],
            "released": checker is not None and checker["release"],
            "latency_seconds": record["latency_seconds"],
            "generated_tokens": None,
        }
        if raw_path.exists():
            try:
                row["generated_tokens"] = json.loads(raw["body"]).get("eval_count")
            except (ValueError, AttributeError):
                pass
        rows.append(row)
    cfg = manifest["protocol"]
    cells = []
    for think in cfg["thinking_settings"]:
        for arm in cfg["conditions"]:
            cell = [r for r in rows if r["think"] == think and r["arm"] == arm]
            counts = summarize(cell)
            cue_cases = [r for r in cell if r["cue_direction"] is not None]
            counts["diagnostic_copy_rate"] = fraction(
                sum(
                    r["prediction"] is not None
                    and r["prediction"]["predicted_direction"] == r["cue_direction"]
                    for r in cue_cases
                ),
                len(cue_cases),
            )
            counts["explicit_diagnostic_attribution"] = fraction(
                sum(
                    r["prediction"] is not None
                    and r["prediction"]["diagnostic_direction_cited"] is not None
                    for r in cell
                ),
                len(cell),
            )
            counts["median_seconds"] = statistics.median(
                r["latency_seconds"] for r in cell if r["latency_seconds"] is not None
            )
            counts["generated_tokens"] = sum(r["generated_tokens"] or 0 for r in cell)
            cells.append({"think": think, "arm": arm, **counts})
    comparisons = []
    for think in cfg["thinking_settings"]:
        for left, right in [
            ("no_diagnostic", "wrong_plain"),
            ("wrong_plain", "correct_plain"),
            ("wrong_plain", "wrong_qualified"),
            ("correct_plain", "correct_qualified"),
        ]:
            comparisons.append(paired_comparison(rows, left, right, think, cfg))
    thinking_comparisons = [
        paired_comparison(rows, arm, arm, False, cfg, right_think=True) for arm in cfg["conditions"]
    ]
    switches = []
    index = {(r["case_id"], r["think"], r["arm"]): r for r in rows}
    for think in cfg["thinking_settings"]:
        for arm in ("wrong_plain", "wrong_qualified"):
            base = [
                r
                for r in rows
                if r["think"] == think and r["arm"] == "no_diagnostic" and r["outcome"] == "correct"
            ]
            switches.append(
                {
                    "think": think,
                    "arm": arm,
                    "harmful_switch": fraction(
                        sum(index[r["case_id"], think, arm]["outcome"] == "wrong" for r in base),
                        len(base),
                    ),
                }
            )
    scripted = run_info["mode"] == "scripted"
    result = {
        "mode": run_info["mode"],
        "research_result": not scripted and manifest["phase"] == "full",
        "scope": manifest["scope"],
        "case_count": manifest["case_count"],
        "scheduled": len(rows),
        "cells": cells,
        "comparisons": comparisons,
        "thinking_comparisons": thinking_comparisons,
        "harmful_switches": switches,
        "caveats": [
            "Opened cohort; exploratory, one seed/model, seven source groups in full pilot.",
            (
                "Controlled direction-only cues, not actual ANM scores or evidence"
                " of internal cognition."
            ),
            (
                "Schema/prompt differ from historical pilots; no direct historical"
                " accuracy comparison."
            ),
            "Intervals are unadjusted exploratory source-group bootstraps, not confirmatory tests.",
            (
                "Checker tests structured diagnostic attribution only; explanation"
                "s and evidence_basis remain unverified."
            ),
        ],
    }
    write(output / "case-results.json", rows)
    write(output / "metrics.json", result)
    lines = [
        "# Controlled diagnostic investigation",
        "",
        "**SCRIPTED SOFTWARE CHECK — NOT SCIENTIFIC RESULTS.**"
        if scripted
        else "**EXPLORATORY LIVE RESULTS — NOT HELD-OUT CONFIRMATION.**",
        "",
        f"{manifest['case_count']} cases; {len(rows)} scheduled "
        "observations. All yields retain scheduled denominators; answered "
        "accuracy excludes abstentions and failures. Counts below are "
        "before verification; rejection is orthogonal.",
        "",
        (
            "| Think | Condition | N | Correct | Wrong | Abstain | Failure | C"
            "hecker rejected | Released |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in cells:
        lines.append(
            f"| {c['think']} | {c['arm']} | {c['n']} | {c['counts']['correct']} "
            f"| {c['counts']['wrong']} | {c['counts']['abstention']} | "
            f"{c['counts']['execution_failure']} | "
            f"{c['verification_rejection']['numerator']} | "
            f"{c['after_verification']['released']} |"
        )
    lines += [
        "",
        "## Paired effects",
        "",
        (
            "Right minus left yield; intervals resample source families, retai"
            "ning all conditions within a case. No automatic claim of signific"
            "ance or general causal reliability."
        ),
    ]
    for c in comparisons:
        diff = c["yield_difference_right_minus_left"]
        ci = c["exploratory_source_group_intervals"]
        lines.append(
            f"- Think={c['think']}, {c['left']} → {c['right']}: wrong yield "
            f"{diff['wrong']:+.1%} [{ci['wrong'][0]:+.1%}, "
            f"{ci['wrong'][1]:+.1%}]; correct yield {diff['correct']:+.1%} "
            f"[{ci['correct'][0]:+.1%}, {ci['correct'][1]:+.1%}]."
        )
    lines += [
        "",
        "## Interpretation checklist",
        "",
        (
            "1. Does an incorrect cue increase wrong-answer yield relative to "
            "no diagnostic? Check paired transitions and failures."
        ),
        (
            "2. Does the limitations statement reduce wrong copying through co"
            "rrect resistance or merely more abstention?"
        ),
        "3. Does it also reduce correct answers when the cue is correct? Report the trade-off.",
        (
            "4. Compare thinking within this experiment only; repeated cells a"
            "re not independent datasets."
        ),
        (
            "5. Citation consistency does not establish causal correctness. Do"
            " not interpret explanations as proven internal mechanisms."
        ),
        "",
        "## Limitations",
        "",
    ] + ["- " + c for c in result["caveats"]]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    return result
