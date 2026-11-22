"""Independently validate and summarize saved thinking observations, with pair bootstrap."""

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from causalbridge.discovery.schemas import DirectionEvidence, DirectionPrediction, canonical_digest
from causalbridge.llm.parser import parse_json
from causalbridge.verifier.bindings import VerificationContext
from causalbridge.verifier.checks import check_prediction

ROOT = Path("runs/qwen3-thinking-ablation-8192-4096-01")


def load(phase):
    return [
        json.loads(p.read_text())
        for p in sorted((ROOT / phase).glob("*.json"))
        if not p.name.endswith(".request.json") and p.name != "manifest.json"
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["preflight", "full"], required=True)
    a = ap.parse_args()
    rows = load(a.phase)
    truth = {
        r["case_id"]: r
        for r in json.loads(
            Path("artifacts/final-delivery/track-b-pilot/evaluator-records.json").read_text()
        )
    }
    import zipfile

    with zipfile.ZipFile("artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip") as z:
        mappings = {
            r["case_id"]: r for r in json.loads(z.read("real-pilot-01/evaluation_mapping.json"))
        }
        events = [
            json.loads(line)
            for line in z.read("real-pilot-01/experiment/events.jsonl").splitlines()
        ]
    original = {
        (
            e["data"]["package"]["evidence"]["case_id"],
            e["data"]["package"]["evidence"]["package"],
            e["data"]["condition"]["condition_id"],
        ): e["data"]
        for e in events
        if e["kind"] == "native_started"
    }
    ends = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_finished"}
    buckets = defaultdict(list)
    matched = defaultdict(dict)
    for r in rows:
        start = original[r["case_id"], r["package"], r["style"]]
        assert r["request"]["messages"] == start["messages"]
        assert r["request"]["format"] == start["output_schema"]
        assert r["package_digest"] == start["receipt"]["package_digest"]
        if r["prediction"]:
            raw = json.loads(r["raw_response"])
            prediction = parse_json(raw["message"]["content"], DirectionPrediction)
            assert prediction.model_dump(mode="json") == r["prediction"]
            context = VerificationContext.model_validate(ends[start["key"]]["context"])
            context = context.model_copy(update={"proposal_digest": prediction.proposal_digest})
            evidence = DirectionEvidence.model_validate(start["package"]["evidence"])
            assert prediction.package_digest == evidence.package_digest
            assert (
                check_prediction(evidence, prediction, context=context).model_dump(mode="json")
                == r["checker"]
            )
        e = truth[r["case_id"]]
        cause = 0 if e["reference_direction"] == "first_to_second" else 1
        gold = (
            "A_to_B"
            if mappings[r["case_id"]]["original_to_runtime_column_order"][0] == cause
            else "B_to_A"
        )
        p = r["prediction"]
        direction = p["predicted_direction"] if p else None
        r["gold"] = gold
        r["correct"] = int(bool(p) and direction == gold)
        r["wrong"] = int(bool(p) and direction is not None and direction != gold)
        r["abstain"] = int(bool(p) and direction is None)
        r["released"] = int(bool(p) and r["checker"]["release"])
        r["rejected"] = int(bool(p) and r["checker"]["status"] == "fail")
        r["supported_correct"] = r["correct"] * r["released"]
        r["checker_reasons"] = r["checker"]["reason_codes"] if r["checker"] else []
        r["weight"] = e["weight"]
        r["anm_direction"] = (
            start["package"]["evidence"]["method_result"]["predicted_direction"]
            if r["package"] == "E4"
            else None
        )
        r["source_group"] = e["source_group"]
        payload = r["request"]
        assert payload["options"]["num_ctx"] == 8192 and payload["options"]["num_predict"] == 4096
        assert payload["options"]["temperature"] == 0 and payload["options"]["seed"] == 261
        assert payload["think"] == r["think"]
        assert canonical_digest(payload).split(":")[-1] == r["observation_id"]
        assert canonical_digest(payload["messages"]) == r["prompt_digest"]
        buckets[r["style"], r["think"], r["package"]].append(r)
        matched[r["case_id"], r["package"], r["style"]][r["think"]] = r
    summaries = []
    for style in ("S0", "S1"):
        for thinking in (False, True):
            for package in ("ALL", "E1", "E2", "E3", "E4"):
                group = [
                    r
                    for r in rows
                    if r["style"] == style
                    and r["think"] == thinking
                    and (package == "ALL" or r["package"] == package)
                ]
                if not group:
                    continue
                counts = {
                    k: sum(r[k] for r in group)
                    for k in (
                        "correct",
                        "wrong",
                        "abstain",
                        "released",
                        "rejected",
                        "supported_correct",
                    )
                }
                counts["failures"] = sum(bool(r["failure"]) for r in group)
                counts["truncated"] = sum(bool(r.get("truncated")) for r in group)
                summaries.append(
                    {
                        "style": style,
                        "think": thinking,
                        "package": package,
                        "n": len(group),
                        **counts,
                        "direction_accuracy": counts["correct"] / len(group),
                        "answered_accuracy": counts["correct"]
                        / (counts["correct"] + counts["wrong"])
                        if counts["correct"] + counts["wrong"]
                        else None,
                        "median_latency": statistics.median(r["latency_seconds"] for r in group),
                        "median_output_tokens": statistics.median(
                            r.get("generated_tokens") or 0 for r in group
                        ),
                        "total_latency_seconds": sum(r["latency_seconds"] for r in group),
                        "total_output_tokens": sum(r.get("generated_tokens") or 0 for r in group),
                        "thinking_activated": sum(bool(r.get("thinking")) for r in group),
                        "nonempty_claim_proposals": sum(
                            bool(r["prediction"] and r["prediction"]["claims"]) for r in group
                        ),
                        "checker_reasons": dict(
                            __import__("collections").Counter(
                                code for r in group for code in r["checker_reasons"]
                            )
                        ),
                        "weighted_correct_yield": sum(r["weight"] * r["correct"] for r in group)
                        / sum(r["weight"] for r in group),
                        "weighted_coverage": sum(
                            r["weight"] * int(bool(r["prediction"]) and not r["abstain"])
                            for r in group
                        )
                        / sum(r["weight"] for r in group),
                    }
                )
                summaries[-1]["rates_over_scheduled_observations"] = {
                    key: counts[key] / len(group)
                    for key in (
                        "correct",
                        "wrong",
                        "abstain",
                        "failures",
                        "released",
                        "rejected",
                        "supported_correct",
                        "truncated",
                    )
                }
    transitions = []
    for key, pair in matched.items():
        assert set(pair) == {False, True}
        off, on = pair[False], pair[True]
        left, right = dict(off["request"]), dict(on["request"])
        left.pop("think")
        right.pop("think")
        assert left == right and off["model_digest"] == on["model_digest"]
        transitions.append(
            {
                "case_id": key[0],
                "package": key[1],
                "style": key[2],
                "off_correct": off["correct"],
                "on_correct": on["correct"],
                "delta": on["correct"] - off["correct"],
                "off_direction": off["prediction"]["predicted_direction"]
                if off["prediction"]
                else None,
                "on_direction": on["prediction"]["predicted_direction"]
                if on["prediction"]
                else None,
                "gold": on["gold"],
                "anm_direction": on["anm_direction"],
                "off_failure": off["failure"],
                "on_failure": on["failure"],
                "off_rejected": off["rejected"],
                "on_rejected": on["rejected"],
                "off_latency": off["latency_seconds"],
                "on_latency": on["latency_seconds"],
                "off_tokens": off.get("generated_tokens"),
                "on_tokens": on.get("generated_tokens"),
            }
        )
    comparisons = []
    for style in ("S0", "S1"):
        t = [r for r in transitions if r["style"] == style]
        if not t:
            continue
        groups = defaultdict(list)
        for r in t:
            groups[r["case_id"]].append(r["delta"])
        rng = random.Random(261)
        names = sorted(groups)
        samples = []
        for _ in range(10000):
            vals = [v for name in rng.choices(names, k=len(names)) for v in groups[name]]
            samples.append(sum(vals) / len(vals))
        samples.sort()
        improved = sum(r["delta"] == 1 for r in t)
        worsened = sum(r["delta"] == -1 for r in t)
        comparisons.append(
            {
                "style": style,
                "improved": improved,
                "worsened": worsened,
                "unchanged": len(t) - improved - worsened,
                "net": sum(r["delta"] for r in t) / len(t),
                "pair_cluster_interval": [samples[250], samples[9749]],
                "mcnemar_note": "Pooled McNemar is inappropriate for dependent evidence packages.",
            }
        )
    result = {
        "phase": a.phase,
        "observations": len(rows),
        "matched_inputs": len(matched),
        "summary": summaries,
        "comparisons": comparisons,
    }
    exact = []
    for style in ("S0", "S1"):
        for package in ("E1", "E2", "E3", "E4"):
            t = [r for r in transitions if r["style"] == style and r["package"] == package]
            b, c = sum(r["delta"] == 1 for r in t), sum(r["delta"] == -1 for r in t)
            n = b + c
            exact.append(
                {
                    "style": style,
                    "package": package,
                    "n": len(t),
                    "improved": b,
                    "worsened": c,
                    "exact_mcnemar_two_sided": min(
                        1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n
                    )
                    if n
                    else 1.0,
                    "scope": "exploratory; unadjusted; source groups may remain dependent",
                }
            )
    result["per_package_mcnemar"] = exact
    result["case_count"] = len({r["case_id"] for r in rows})
    result["matched_inputs_with_two_valid_predictions"] = sum(
        not pair[False]["failure"] and not pair[True]["failure"] for pair in matched.values()
    )
    result["thinking_tokens"] = "not separately exposed by API"
    source_sensitivity = {}
    for style in ("S0", "S1"):
        groups = defaultdict(list)
        casegroup = {r["case_id"]: r["source_group"] for r in rows}
        for t in transitions:
            if t["style"] == style:
                groups[casegroup[t["case_id"]]].append(t["delta"])
        names = sorted(groups)
        rng = random.Random(261)
        draws = []
        for _ in range(10000):
            vals = [v for name in rng.choices(names, k=len(names)) for v in groups[name]]
            draws.append(sum(vals) / len(vals))
        draws.sort()
        source_sensitivity[style] = {"groups": len(groups), "interval": [draws[250], draws[9749]]}
    result["source_group_sensitivity"] = source_sensitivity
    pair_effects = defaultdict(dict)
    for style in ("S0", "S1"):
        for case in {r["case_id"] for r in transitions}:
            values = [
                r["delta"] for r in transitions if r["style"] == style and r["case_id"] == case
            ]
            if values:
                pair_effects[case][style] = sum(values) / len(values)
    interaction = [v["S1"] - v["S0"] for v in pair_effects.values() if set(v) == {"S0", "S1"}]
    rng = random.Random(261)
    draws = sorted(
        statistics.mean(rng.choices(interaction, k=len(interaction))) for _ in range(10000)
    )
    result["thinking_by_style_interaction"] = {
        "difference_of_differences": statistics.mean(interaction),
        "pair_bootstrap_interval": [draws[250], draws[9749]],
    }
    if a.phase == "full":
        assert len(rows) == 272 and len(matched) == 136 and result["case_count"] == 17
    (ROOT / (a.phase + "-case-results.json")).write_text(json.dumps(rows, indent=2) + "\n")
    (ROOT / (a.phase + "-analysis.json")).write_text(json.dumps(result, indent=2) + "\n")
    (ROOT / (a.phase + "-transitions.json")).write_text(json.dumps(transitions, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
