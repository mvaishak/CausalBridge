"""Recompute final descriptive metrics and a vector figure from saved artifacts."""

from __future__ import annotations

import argparse
import gzip
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/final-delivery"
OUT = ART / "analysis"


def read_json(path: Path):
    return json.loads(path.read_text())


def interval(rows: list[dict], group_key: str, numerator: str, denominator: str) -> dict:
    """Exploratory percentile interval, resampling whole source/graph groups."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row[group_key]].append(row)
    names = sorted(groups)
    rng = random.Random(261)
    values = []
    for _ in range(10000):
        sampled = [row for _name in (rng.choice(names) for _ in names) for row in groups[_name]]
        den = sum(row[denominator] for row in sampled)
        if den:
            values.append(sum(row[numerator] for row in sampled) / den)
    values.sort()
    return {
        "lower": values[int(0.025 * len(values))],
        "upper": values[min(len(values) - 1, int(0.975 * len(values)))],
        "draws": len(values),
        "method": "source_or_graph_cluster_percentile_bootstrap_seed261_exploratory",
    }


def track_a() -> dict:
    traces_path = ART / "track-a-live/traces.jsonl.gz"
    oracle_path = ART / "track-a-live/oracle.jsonl"
    traces = [
        json.loads(line) for line in gzip.decompress(traces_path.read_bytes()).decode().splitlines()
    ]
    oracle = {z["case_id"]: z for z in map(json.loads, oracle_path.read_text().splitlines())}
    assert len(traces) == len(oracle) == 50
    assert len({z["runtime_case"]["case_id"] for z in traces}) == 50
    rows = []
    for trace in traces:
        case = trace["runtime_case"]
        gold = oracle[case["case_id"]]
        verdict = trace["verdict"]
        answered = verdict["response_action"] == "answer"
        answer = verdict["answer"]
        target = gold["gold_answer"]
        if answered and gold["answerable"]:
            if isinstance(target, (int, float)) and not isinstance(target, bool):
                correct = isinstance(answer, (int, float)) and abs(answer - target) <= 0.001
            else:
                correct = answer == target
        else:
            correct = False
        rows.append(
            {
                "case_id": case["case_id"],
                "graph_group_id": case["graph_group_id"],
                "evidence_level": case["evidence_level"],
                "gold_answerable": gold["answerable"],
                "gold_answer": target,
                "query_type_expected": gold["query"]["question_type"],
                "query_type_observed": trace["query"]["question_type"] if trace["query"] else None,
                "status": verdict["status"],
                "response_action": verdict["response_action"],
                "answer": answer,
                "correct_answer": correct,
                "correct_abstention": not answered and not gold["answerable"],
                "wrong_answer": answered and not correct,
                "false_abstention": not answered and gold["answerable"],
                "parse_calls": sum(c["stage"] == "parse" for c in trace["calls"]),
                "model_calls": len(trace["calls"]),
                "input_tokens": trace["input_tokens"],
                "output_tokens": trace["output_tokens"],
                "latency_seconds": trace["latency_seconds"],
                "one": 1,
                "answered": int(answered),
                "correct": int(correct),
            }
        )
    counts = Counter()
    for row in rows:
        for key in ("correct_answer", "correct_abstention", "wrong_answer", "false_abstention"):
            counts[key] += row[key]
    result = {
        "cases": 50,
        "graph_groups": 10,
        "answerable": sum(z["gold_answerable"] for z in rows),
        "unanswerable": sum(not z["gold_answerable"] for z in rows),
        "counts": dict(counts),
        "coverage": sum(z["answered"] for z in rows) / 50,
        "answered_accuracy": sum(z["correct"] for z in rows)
        / max(1, sum(z["answered"] for z in rows)),
        "overall_correct_decision": (counts["correct_answer"] + counts["correct_abstention"]) / 50,
        "query_type_matches": sum(
            z["query_type_expected"] == z["query_type_observed"] for z in rows
        ),
        "actual_model_calls": sum(z["model_calls"] for z in rows),
        "input_tokens": sum(z["input_tokens"] for z in rows),
        "output_tokens": sum(z["output_tokens"] for z in rows),
        "latency_seconds_sum": sum(z["latency_seconds"] for z in rows),
        "status_counts": dict(Counter(z["status"] for z in rows)),
        "by_evidence": {},
        "intervals": {
            "coverage": interval(rows, "graph_group_id", "answered", "one"),
            "correct_yield": interval(rows, "graph_group_id", "correct", "one"),
            "answered_accuracy": None,
            "answered_accuracy_reason": (
                "Only two answers, both in one graph group; no useful cluster interval"
            ),
        },
    }
    for level in sorted({z["evidence_level"] for z in rows}):
        subset = [z for z in rows if z["evidence_level"] == level]
        result["by_evidence"][level] = {
            "n": len(subset),
            "correct_answer": sum(z["correct_answer"] for z in subset),
            "correct_abstention": sum(z["correct_abstention"] for z in subset),
            "wrong_answer": sum(z["wrong_answer"] for z in subset),
            "false_abstention": sum(z["false_abstention"] for z in subset),
        }
    (OUT / "track-a-case-results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return result


def anm_real() -> dict:
    base = ROOT / "artifacts/anm-experiments-2026-11-18/summaries/anish-anm-validation-test-01"
    summary = read_json(base / "execution/summary.json")
    case_map = {
        z["case_id"]: z for z in read_json(ART / "anm-real-validation/inputs.json")["cases"]
    }
    cases = [z for z in summary["variants"][0]["cases"] if z["split_seed"] == 261]
    assert len(cases) == 38
    rows = []
    for case in cases:
        metadata = case_map[case["case_id"]]
        rows.append(
            {
                "case_id": case["case_id"],
                "source_group": metadata["source_group"],
                "weight": metadata["weight"],
                "decision": case["decision"],
                "reference": case["reference"],
                "selected_rows": case["selected_rows"],
                "margin": case["margin"],
                "answered": int(case["decision"] is not None),
                "correct": int(
                    case["decision"] is not None and case["decision"] == case["reference"]
                ),
                "wrong": int(
                    case["decision"] is not None and case["decision"] != case["reference"]
                ),
                "one": 1,
            }
        )
    assert sum(z["correct"] for z in rows) == 13
    assert sum(z["wrong"] for z in rows) == 13
    (OUT / "anm-real-case-results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return {
        "cases": 38,
        "source_groups": len({z["source_group"] for z in rows}),
        "correct": 13,
        "wrong": 13,
        "abstain": 12,
        "coverage": 26 / 38,
        "answered_accuracy": 13 / 26,
        "intervals": {
            "coverage": interval(rows, "source_group", "answered", "one"),
            "correct_yield": interval(rows, "source_group", "correct", "one"),
            "answered_accuracy": interval(rows, "source_group", "correct", "answered"),
        },
    }


def figure(metrics: dict) -> None:
    # An intentionally simple publication-ready vector chart: case fractions, not mixed weights.
    panels = [
        ("Track A, synthetic", metrics["track_a"]["counts"], 50),
        ("Track B E4, real", {"correct_answer": 6, "wrong_answer": 8, "abstain": 3}, 17),
        ("ANM validation, real", {"correct_answer": 13, "wrong_answer": 13, "abstain": 12}, 38),
    ]
    colors = {"correct_answer": "#237c69", "wrong_answer": "#bb5145", "abstain": "#a2a8ad"}
    labels = {
        "correct_answer": "Correct answer",
        "wrong_answer": "Wrong answer",
        "abstain": "Abstain",
    }
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="360" viewBox="0 0 900 360">',
        '<rect width="900" height="360" fill="white"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#20303a}.title{font-size:20px;font-weight:bold}.label{font-size:15px}.small{font-size:13px}</style>",
        '<text x="30" y="33" class="title">CausalBridge outcomes by evaluation panel</text>',
    ]
    for i, (title, counts, total) in enumerate(panels):
        y = 80 + 85 * i
        svg.append(f'<text x="30" y="{y}" class="label">{title} (n={total})</text>')
        x = 255
        if i == 0:
            counts = {
                "correct_answer": counts.get("correct_answer", 0),
                "wrong_answer": counts.get("wrong_answer", 0),
                "abstain": counts.get("correct_abstention", 0) + counts.get("false_abstention", 0),
            }
        for key in ("correct_answer", "wrong_answer", "abstain"):
            count = counts.get(key, 0)
            width = 590 * count / total
            svg.append(
                f'<rect x="{x:.2f}" y="{y - 20}" width="{width:.2f}" '
                f'height="30" fill="{colors[key]}"/>'
            )
            if width > 35:
                svg.append(
                    f'<text x="{x + width / 2:.2f}" y="{y + 1}" '
                    f'text-anchor="middle" class="small" fill="white">{count}</text>'
                )
            x += width
    for i, key in enumerate(("correct_answer", "wrong_answer", "abstain")):
        x = 30 + i * 180
        svg.append(f'<rect x="{x}" y="323" width="14" height="14" fill="{colors[key]}"/>')
        svg.append(f'<text x="{x + 21}" y="335" class="small">{labels[key]}</text>')
    svg.append("</svg>")
    (OUT / "outcomes.svg").write_text("\n".join(svg) + "\n")


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.output is not None:
        OUT = args.output
    OUT.mkdir(parents=True, exist_ok=args.output is None)
    result = {"track_a": track_a(), "anm_real": anm_real()}
    (OUT / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    figure(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
