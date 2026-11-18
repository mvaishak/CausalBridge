"""Post-run weighted pilot summaries. No inference-time labels or inferential claims."""

import math

from causalbridge.discovery.evidence import rng
from causalbridge.discovery.schemas import canonical_digest

PILOT_CONDITIONS = tuple(
    (p, c) for p in ("E1", "E2", "E3", "E4") for c in ("S0", "S1", "S2", "SIMPLE_GATE")
) + (("E4", "ANM_ONLY"),)


def _validate_lineage(indexed):
    """Score one manifest, binding derived conditions to their exact saved S1."""
    manifests, attempts = set(), set()
    for row in indexed.values():
        for field in ("manifest_id", "package_digest"):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError("Analysis row is missing its " + field)
        manifests.add(row["manifest_id"])
        if type(row["prediction_scorable"]) is not bool:
            raise ValueError("Prediction scorability must be boolean")
        if row["condition"] in {"S0", "S1"}:
            attempt = row.get("attempt_id")
            if not isinstance(attempt, str) or not attempt or attempt in attempts:
                raise ValueError("Primary attempt IDs must be present and unique")
            attempts.add(attempt)
            if "run_id" not in row:
                raise ValueError("Primary row is missing its run identity")
    if len(manifests) != 1:
        raise ValueError("Cannot score analysis rows from different manifests together")
    for row in indexed.values():
        if row["condition"] not in {"S2", "SIMPLE_GATE"}:
            continue
        parent = indexed.get((row["case_id"], row["package"], "S1"))
        if parent is None or row.get("parent_attempt_id") != parent["attempt_id"]:
            raise ValueError("Derived row does not join its exact S1 parent")
        for field in ("manifest_id", "package_digest", "run_id", "attempt_id"):
            if field not in row or row[field] != parent[field]:
                raise ValueError("Derived row does not bind its parent's " + field)
        usable = parent["prediction_scorable"] and parent.get("failure_stage") is None
        direction = row["predicted_direction"]
        if direction is not None and (not usable or direction != parent["predicted_direction"]):
            raise ValueError("Derived row cannot invent or reverse its parent answer")
        if row["prediction_scorable"] != parent["prediction_scorable"]:
            raise ValueError("Derived row contradicts its parent's usability")
        if row["condition"] == "S2":
            if "released_direction" not in row or row["released_direction"] != direction:
                raise ValueError("S2 direction must match its recorded release")
            if direction is not None and row.get("outcome") != "pass":
                raise ValueError("Only a passing S2 check may release an answer")
        elif direction is not None and row.get("outcome") != "gate_pass":
            raise ValueError("A rejected simple gate cannot supply an answer")


def score_pilot(rows, evaluator, mappings, *, expected_conditions=PILOT_CONDITIONS):
    """Keep all declared cases in each denominator; reject missing/duplicate rows.

    Reference direction is expressed in original file order. Map it to A/B only
    using the private saved selection receipt, never guessed from pair IDs.
    Validate selection-v1 mapping identity and seeded orientation before scoring.
    This detects inconsistent metadata, not jointly rewritten receipts.
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
        seed = m.get("mapping_seed")
        if (
            type(seed) is not int
            or seed < 0
            or not isinstance(order, (list, tuple))
            or len(order) != 2
            or any(type(column) is not int for column in order)
            or sorted(order) != [0, 1]
        ):
            raise ValueError("Mapping requires an exact column permutation and integer seed")
        expected_id = canonical_digest({"case_id": case, "order": list(order), "seed": seed})
        if m["ab_mapping_id"] != expected_id:
            raise ValueError("Mapping ID does not bind case, column order and seed")
        expected_order = (1, 0) if rng(seed, case, "mapping").getrandbits(1) else (0, 1)
        if tuple(order) != expected_order:
            raise ValueError("Column order differs from deterministic selection")
        if m["source_digest"] != e["source_digest"]:
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
    _validate_lineage(indexed)
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
