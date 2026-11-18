"""Post-run weighted pilot summaries. No inference-time labels or inferential claims."""

import math

PILOT_CONDITIONS = tuple(
    (p, c) for p in ("E1", "E2", "E3", "E4") for c in ("S0", "S1", "S2", "SIMPLE_GATE")
) + (("E4", "ANM_ONLY"),)


def score_pilot(rows, evaluator, mappings, *, expected_conditions=PILOT_CONDITIONS):
    """Keep all declared cases in each denominator; reject missing/duplicate rows.

    Reference direction is expressed in original file order. Map it to A/B only
    using the private saved selection receipt, never guessed from pair IDs.
    """
    gold = {e["case_id"]: e for e in evaluator}
    mapping = {m["case_id"]: m for m in mappings}
    if (
        not gold
        or len(gold) != len(evaluator)
        or len(mapping) != len(mappings)
        or set(gold) != set(mapping)
    ):
        raise ValueError("Evaluator/mapping cases must match exactly without duplicates")
    expected = set(expected_conditions)
    if len(expected) != len(expected_conditions) or not expected:
        raise ValueError("Conditions must be unique and nonempty")
    directions, weights = {}, {}
    for case, e in gold.items():
        m = mapping[case]
        order = m["original_to_runtime_column_order"]
        if order not in ([0, 1], [1, 0]) or m["source_digest"] != e["source_digest"]:
            raise ValueError("Evaluator source/mapping mismatch")
        if e["reference_direction"] not in {"first_to_second", "second_to_first"}:
            raise ValueError("Invalid reference direction")
        cause = 0 if e["reference_direction"] == "first_to_second" else 1
        directions[case] = "A_to_B" if order[0] == cause else "B_to_A"
        w = e["weight"]
        if type(w) not in (float, int) or not math.isfinite(w) or w <= 0:
            raise ValueError("Scoring weights must be finite and positive")
        weights[case] = w
    indexed = {}
    for row in rows:
        case = row["case_id"]
        pair = (row["package"], row["condition"])
        key = (case, *pair)
        if case not in gold or pair not in expected or key in indexed:
            raise ValueError("Unexpected or duplicate analysis row")
        if row["ab_mapping_id"] != mapping[case]["ab_mapping_id"]:
            raise ValueError("Analysis mapping mismatch")
        if row["predicted_direction"] not in {None, "A_to_B", "B_to_A"}:
            raise ValueError("Invalid predicted direction")
        if row["predicted_direction"] is not None and not row["prediction_scorable"]:
            raise ValueError("Unscorable prediction cannot be released")
        indexed[key] = row
    if set(indexed) != {(case, *condition) for case in gold for condition in expected}:
        raise ValueError("Missing scheduled analysis rows")
    denominator = math.fsum(weights.values())
    results = []
    for package, condition in expected_conditions:
        released, correct, wrong, failures = [], [], [], 0
        for case in gold:
            row = indexed[(case, package, condition)]
            direction = row["predicted_direction"]
            if direction is not None:
                released.append(weights[case])
                (correct if direction == directions[case] else wrong).append(weights[case])
            if not row["prediction_scorable"] or row.get("outcome") in {
                "checker_error",
                "parent_prediction_failed",
                "parent_failure",
            }:
                failures += 1
        released_weight, correct_weight = math.fsum(released), math.fsum(correct)
        results.append(
            dict(
                package=package,
                condition=condition,
                case_count=len(gold),
                total_weight=denominator,
                source_group_count=len({e["source_group"] for e in evaluator}),
                coverage=released_weight / denominator,
                correct_yield=correct_weight / denominator,
                wrong_yield=math.fsum(wrong) / denominator,
                selective_accuracy=correct_weight / released_weight if released_weight else None,
                failure_count=failures,
                scope="exploratory_pilot_no_confidence_intervals",
            )
        )
    return results


def main():
    import argparse
    import json
    from pathlib import Path

    from causalbridge.discovery.anm_requests import read_json, write_json_exclusive

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("analysis", "evaluator", "mapping", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    from causalbridge.llm.parser import reject_duplicate_keys

    rows = [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in args.analysis.read_text().splitlines()
    ]
    result = score_pilot(rows, read_json(args.evaluator), read_json(args.mapping))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
