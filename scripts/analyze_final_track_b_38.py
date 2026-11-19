"""Analyze saved *live* integrated Track B predictions on the opened 38-pair panel."""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def cluster_interval(cases, numerator, denominator):
    groups = defaultdict(list)
    for case in cases:
        groups[case["source_group"]].append(case)
    names = sorted(groups)
    generator = random.Random(261)
    values = []
    for _ in range(10000):
        sampled = [row for name in (generator.choice(names) for _ in names) for row in groups[name]]
        den = sum(row[denominator] for row in sampled)
        if den > 0:
            values.append(sum(row[numerator] for row in sampled) / den)
    if not values:
        return None
    values.sort()
    return {
        "lower": values[int(0.025 * len(values))],
        "upper": values[min(len(values) - 1, int(0.975 * len(values)))],
        "draws": len(values),
        "scope": "exploratory_source_cluster_bootstrap",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    run = args.run
    summary = read(run / "run-summary.json")
    if summary["model_mode"] != "live_ollama" or summary["case_count"] != 38:
        ap.error("Only a completed live 38-pair run may be analyzed here")
    rows = [json.loads(line) for line in (run / "analysis.jsonl").read_text().splitlines()]
    evaluator = {e["case_id"]: e for e in read(run / "evaluator.json")}
    mapping = {m["case_id"]: m for m in read(run / "evaluation_mapping.json")}
    scored = read(run / "scores.json")
    if len(rows) != 38 * 17 or len(evaluator) != len(mapping) != 38:
        ap.error("Incomplete analysis or evaluator")
    records = []
    by_strategy = {}
    for row in rows:
        case = row["case_id"]
        e = evaluator[case]
        order = mapping[case]["original_to_runtime_column_order"]
        cause = 0 if e["reference_direction"] == "first_to_second" else 1
        gold = "A_to_B" if order[0] == cause else "B_to_A"
        direction = row["predicted_direction"]
        record = {
            "case_id": case,
            "pair_id": e["original_pair_id"],
            "source_group": e["source_group"],
            "weight": e["weight"],
            "package": row["package"],
            "condition": row["condition"],
            "reference_ab": gold,
            "predicted_direction": direction,
            "answered": int(direction is not None),
            "correct": int(direction is not None and direction == gold),
            "wrong": int(direction is not None and direction != gold),
            "weighted_answered": e["weight"] * int(direction is not None),
            "weighted_correct": e["weight"] * int(direction is not None and direction == gold),
            "weighted_one": e["weight"],
            "outcome": row["outcome"],
            "prediction_scorable": row["prediction_scorable"],
            "supplied_claim_count": row["supplied_claim_count"],
            "checked_claim_count": row["checked_claim_count"],
        }
        records.append(record)
        by_strategy.setdefault((row["package"], row["condition"]), []).append(record)
    metrics = []
    for score in scored:
        key = score["package"], score["condition"]
        group = by_strategy[key]
        metrics.append(
            {
                **score,
                "correct_count": sum(c["correct"] for c in group),
                "wrong_count": sum(c["wrong"] for c in group),
                "abstain_count": sum(not c["answered"] for c in group),
                "intervals": {
                    "coverage": cluster_interval(group, "weighted_answered", "weighted_one"),
                    "correct_yield": cluster_interval(group, "weighted_correct", "weighted_one"),
                    "answered_accuracy": cluster_interval(
                        group, "weighted_correct", "weighted_answered"
                    ),
                },
            }
        )
    index = {(r["case_id"], r["package"], r["condition"]): r for r in records}
    transitions = Counter()

    def category(record):
        return "correct" if record["correct"] else "wrong" if record["wrong"] else "abstain"

    for case in evaluator:
        e3 = index[(case, "E3", "S0")]
        e4 = index[(case, "E4", "S0")]
        transitions[(category(e3), category(e4))] += 1
    e4_agreement = sum(
        index[(case, "E4", "S0")]["predicted_direction"]
        == index[(case, "E4", "ANM_ONLY")]["predicted_direction"]
        for case in evaluator
    )
    e4_answered_copies_anm = sum(
        index[(case, "E4", "S0")]["predicted_direction"]
        == index[(case, "E4", "ANM_ONLY")]["predicted_direction"]
        for case in evaluator
        if index[(case, "E4", "S0")]["answered"]
    )
    e4_s0_s1_agreement = sum(
        index[(case, "E4", "S0")]["predicted_direction"]
        == index[(case, "E4", "S1")]["predicted_direction"]
        for case in evaluator
    )
    s1 = [r for r in records if r["condition"] == "S1"]
    s2 = [r for r in records if r["condition"] == "S2"]
    checker = {
        "s1_answers": sum(r["answered"] for r in s1),
        "s2_answers": sum(r["answered"] for r in s2),
        "suppressed_correct": sum(
            index[(r["case_id"], r["package"], "S1")]["correct"] for r in s2 if not r["answered"]
        ),
        "suppressed_wrong": sum(
            index[(r["case_id"], r["package"], "S1")]["wrong"] for r in s2 if not r["answered"]
        ),
        "s2_outcomes": dict(Counter(r["outcome"] for r in s2)),
    }
    output = {
        "scope": "exploratory_opened_anm_validation_pairs",
        "cases": 38,
        "source_groups": len({e["source_group"] for e in evaluator.values()}),
        "live_calls": summary["new_model_calls"],
        "model": summary["observed_model"],
        "metrics": metrics,
        "e3_to_e4_s0_transitions": {"→".join(k): v for k, v in sorted(transitions.items())},
        "e4_s0_agrees_with_anm_count": e4_agreement,
        "e4_s0_answered_copies_anm_count": e4_answered_copies_anm,
        "e4_s0_s1_agreement_count": e4_s0_s1_agreement,
        "checker": checker,
        "interval_note": "Exploratory source-cluster bootstrap; opened labels.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "case-results.json").write_text(json.dumps(records, indent=2) + "\n")
    (args.output / "metrics.json").write_text(json.dumps(output, indent=2) + "\n")
    figure_rows = [
        ("E3 / S0", ("E3", "S0")),
        ("E4 / S0", ("E4", "S0")),
        ("E4 / S1", ("E4", "S1")),
        ("E4 / S2", ("E4", "S2")),
        ("ANM only", ("E4", "ANM_ONLY")),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="410" viewBox="0 0 900 410">',
        '<rect width="900" height="410" fill="white"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#20303a}.title{font-size:20px;font-weight:bold}.label{font-size:15px}.small{font-size:13px}</style>",
        '<text x="25" y="34" class="title">Integrated Track B: opened 38-pair panel</text>',
    ]
    colors = ("#237c69", "#bb5145", "#a2a8ad")
    for i, (label, key) in enumerate(figure_rows):
        group = by_strategy[key]
        counts = (sum(r["correct"] for r in group), sum(r["wrong"] for r in group))
        counts += (38 - sum(counts),)
        y = 75 + 58 * i
        svg.append(f'<text x="25" y="{y + 12}" class="label">{label}</text>')
        x = 180.0
        for count, color in zip(counts, colors, strict=True):
            width = 600 * count / 38
            svg.append(
                f'<rect x="{x:.1f}" y="{y - 8}" width="{width:.1f}" height="29" fill="{color}"/>'
            )
            if width > 30:
                svg.append(
                    f'<text x="{x + width / 2:.1f}" y="{y + 12}" text-anchor="middle" '
                    f'fill="white" class="small">{count}</text>'
                )
            x += width
    for i, (label, color) in enumerate(zip(("Correct", "Wrong", "Abstain"), colors, strict=True)):
        x = 25 + 175 * i
        svg.append(f'<rect x="{x}" y="368" width="15" height="15" fill="{color}"/>')
        svg.append(f'<text x="{x + 21}" y="381" class="small">{label}</text>')
    svg.append("</svg>")
    (args.output / "outcomes.svg").write_text("\n".join(svg) + "\n")
    print(
        json.dumps(
            {
                "cases": 38,
                "live_calls": output["live_calls"],
                "e4_agreement": e4_agreement,
                "checker": checker,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
