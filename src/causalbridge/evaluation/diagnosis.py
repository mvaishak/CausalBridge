"""Case-level diagnosis of a finished pilot. No model calls and no new threshold.

Reads the saved analysis export, evaluator records and A/B mapping. Optional
ANM result.json files add margins. This does not read free-text generations,
fit a threshold, or compute confidence intervals.
"""

import json
import math
from pathlib import Path

from pydantic import ValidationError

from causalbridge.discovery.schemas import ANMResult, canonical_digest
from causalbridge.evaluation.scoring import PILOT_CONDITIONS, score_pilot

MODEL_CONDITIONS = ("S0", "S1", "S2")
PACKAGES = ("E1", "E2", "E3", "E4")


def diagnose_pilot(rows, evaluator, mappings, anm_results=None, *, experiment_receipts=None):
    """Join labels after inference and summarize the saved pilot.

    anm_results maps case_id to a saved ANM result. When omitted, directions
    still come from the ANM_ONLY export and margins stay null. Saved margins
    require independently retained experiment_receipts bound to the E4 export.
    """
    weighted = score_pilot(rows, evaluator, mappings)
    unweighted = score_pilot(rows, [_unit_weight(row) for row in evaluator], mappings)
    conditions = [
        left | _unweighted_fields(right) for left, right in zip(weighted, unweighted, strict=True)
    ]
    bound = _bind(evaluator, mappings)
    indexed = _index(rows, bound)
    anm = _anm_by_case(anm_results, bound, indexed, experiment_receipts)
    cases = [_case_row(case, bound, indexed, anm) for case in sorted(bound)]
    return {
        "scope": "exploratory_pilot_diagnosis_no_confidence_intervals",
        "case_count": len(cases),
        "source_group_count": len({row["source_group"] for row in cases}),
        "total_weight": conditions[0]["total_weight"],
        "cases": cases,
        "conditions": conditions,
        "contrasts": _contrasts(conditions),
        "checker": _checker(cases),
        "anm_agreement": _agreement(cases),
        "source_groups": _groups(cases),
        "threshold_curve": _threshold_curve(cases),
        "notes": (
            "Selective accuracy is null when nothing is released. "
            "Threshold rows reuse saved margins and do not replace the pilot threshold. "
            "Written explanations are not in the analysis export."
        ),
    }


def _unit_weight(row):
    return dict(row) | {"weight": 1.0}


def _unweighted_fields(row):
    return {
        "unweighted_coverage": row["coverage"],
        "unweighted_correct_yield": row["correct_yield"],
        "unweighted_wrong_yield": row["wrong_yield"],
        "unweighted_selective_accuracy": row["selective_accuracy"],
    }


def _bind(evaluator, mappings):
    gold = {row["case_id"]: row for row in evaluator}
    mapping = {row["case_id"]: row for row in mappings}
    bound = {}
    for case, row in gold.items():
        order = mapping[case]["original_to_runtime_column_order"]
        cause = 0 if row["reference_direction"] == "first_to_second" else 1
        if "source_group" not in row:
            raise ValueError("Evaluator records require a source group")
        bound[case] = {
            "case_id": case,
            "original_pair_id": row.get("original_pair_id"),
            "source_group": row["source_group"],
            "weight": row["weight"],
            "ab_mapping_id": mapping[case]["ab_mapping_id"],
            "reference_direction": "A_to_B" if order[0] == cause else "B_to_A",
        }
    return bound


def _index(rows, bound):
    indexed = {}
    for row in rows:
        indexed[(row["case_id"], row["package"], row["condition"])] = row
    expected = {(case, *pair) for case in bound for pair in PILOT_CONDITIONS}
    if set(indexed) != expected:
        raise ValueError("Diagnosis requires the complete pilot schedule")
    return indexed


def _anm_by_case(anm_results, bound, indexed, experiment_receipts):
    if anm_results is None:
        return {
            case: {"margin": None, "score_ab": None, "score_ba": None, "threshold": None}
            for case in bound
        }
    if set(anm_results) != set(bound):
        raise ValueError("ANM results must match the evaluator cases")
    if experiment_receipts is None:
        raise ValueError("Saved margins require original experiment receipts")
    parsed = {}
    for case, result in anm_results.items():
        saved = _validated_anm(case, result, bound[case]["ab_mapping_id"])
        exported = indexed[(case, "E4", "ANM_ONLY")]
        if saved.predicted_direction != exported["predicted_direction"]:
            raise ValueError("Saved ANM direction disagrees with the ANM_ONLY export")
        if saved.provenance.config_digest != exported.get("method_config_digest"):
            raise ValueError("ANM result is not bound to the saved configuration")
        exported_package = exported.get("package_digest")
        matching = [
            receipt
            for receipt in experiment_receipts
            if receipt.get("case_id") == case
            and exported_package is not None
            and receipt.get("package_digest") == exported_package
            and receipt.get("ab_mapping_id") == bound[case]["ab_mapping_id"]
        ]
        if not matching or any(
            receipt.get("method_result_digest") != canonical_digest(saved.model_dump(mode="json"))
            for receipt in matching
        ):
            raise ValueError("ANM result is not bound to the original experiment receipt")
        parsed[case] = {
            "margin": saved.margin,
            "score_ab": saved.score_ab,
            "score_ba": saved.score_ba,
            "threshold": saved.threshold,
        }
    return parsed


def _validated_anm(case, result, mapping_id) -> ANMResult:
    """Reject a margin, direction, or request binding that the saved scores do not support."""
    try:
        saved = ANMResult.model_validate(result)
    except ValidationError as exc:
        raise ValueError(f"Saved ANM result for {case} is inconsistent") from exc
    if saved.provenance.ab_mapping_id != mapping_id:
        raise ValueError("ANM result is not bound to the saved A/B mapping")
    return saved


def _case_row(case, bound, indexed, anm):
    meta = bound[case]
    reference = meta["reference_direction"]
    record = {key: value for key, value in meta.items() if key != "ab_mapping_id"}
    record.update(anm[case])
    record["anm_direction"] = indexed[(case, "E4", "ANM_ONLY")]["predicted_direction"]
    record["anm_correct"] = _correct(record["anm_direction"], reference)
    for package, condition in PILOT_CONDITIONS:
        row = indexed[(case, package, condition)]
        prefix = f"{package}_{condition}".lower()
        direction = row["predicted_direction"]
        record[f"{prefix}_direction"] = direction
        record[f"{prefix}_outcome"] = row.get("outcome")
        record[f"{prefix}_state"] = _state(row)
        record[f"{prefix}_reason_codes"] = list(row.get("reason_codes") or [])
        record[f"{prefix}_correct"] = _correct(direction, reference)
    return record


def _correct(direction, reference):
    if direction is None:
        return None
    return direction == reference


def _find(conditions, package, condition):
    return next(
        row for row in conditions if row["package"] == package and row["condition"] == condition
    )


def _difference(left, right, field):
    if left[field] is None or right[field] is None:
        return None
    return left[field] - right[field]


def _contrasts(conditions):
    named = {
        "H1_S0_E3_minus_E2": ("E3", "S0", "E2", "S0"),
        "H1_S1_E3_minus_E2": ("E3", "S1", "E2", "S1"),
        "H2_S1_E4_minus_E3": ("E4", "S1", "E3", "S1"),
        "H2_S1_E4_minus_ANM": ("E4", "S1", "E4", "ANM_ONLY"),
        "H3_E4_S2_minus_S1": ("E4", "S2", "E4", "S1"),
    }
    contrasts = []
    for name, (lp, lc, rp, rc) in named.items():
        left, right = _find(conditions, lp, lc), _find(conditions, rp, rc)
        contrasts.append(
            {
                "name": name,
                "coverage": _difference(left, right, "coverage"),
                "correct_yield": _difference(left, right, "correct_yield"),
                "wrong_yield": _difference(left, right, "wrong_yield"),
                "selective_accuracy": _difference(left, right, "selective_accuracy"),
                "unweighted_coverage": _difference(left, right, "unweighted_coverage"),
                "unweighted_selective_accuracy": _difference(
                    left, right, "unweighted_selective_accuracy"
                ),
            }
        )
    return contrasts


def _checker(cases):
    effects = []
    for package in PACKAGES:
        removed_correct = removed_wrong = 0.0
        removed_correct_n = removed_wrong_n = 0
        rejected = []
        for case in cases:
            before = case[f"{package.lower()}_s1_direction"]
            after = case[f"{package.lower()}_s2_direction"]
            if before is None or after is not None:
                continue
            correct = case[f"{package.lower()}_s1_correct"]
            if correct:
                removed_correct += case["weight"]
                removed_correct_n += 1
            else:
                removed_wrong += case["weight"]
                removed_wrong_n += 1
            rejected.append(
                {
                    "case_id": case["case_id"],
                    "original_pair_id": case["original_pair_id"],
                    "source_group": case["source_group"],
                    "weight": case["weight"],
                    "s1_direction": before,
                    "s1_correct": correct,
                    "s2_outcome": case[f"{package.lower()}_s2_outcome"],
                    "s2_reason_codes": case[f"{package.lower()}_s2_reason_codes"],
                }
            )
        effects.append(
            {
                "package": package,
                "removed_correct_weight": removed_correct,
                "removed_wrong_weight": removed_wrong,
                "removed_correct_count": removed_correct_n,
                "removed_wrong_count": removed_wrong_n,
                "rejections": rejected,
            }
        )
    return effects


def _state(row):
    outcome = row.get("outcome")
    if row.get("condition") == "ANM_ONLY":
        if row.get("failure_stage") or outcome in {"error", "method_unavailable_or_unconfigured"}:
            return "method_unavailable"
        if row["predicted_direction"] is not None:
            return "answer"
        if outcome in {"ambiguous_margin", "abstain"}:
            return "abstain"
        return "method_unavailable"
    if (
        not row.get("prediction_scorable")
        or row.get("failure_stage")
        or outcome
        in {"prediction_failure", "parent_prediction_failed", "parent_failure", "checker_error"}
    ):
        return "prediction_failure"
    if row.get("condition") == "S2" and outcome == "fail":
        return "checker_suppressed"
    if row["predicted_direction"] is not None:
        return "answer"
    if outcome in {"model_abstention", "pass"}:
        return "abstain"
    return "outcome_unavailable"


def _relation(model, method):
    if model == method:
        return "agree_abstain" if model is None else "agree_answer"
    if model is None:
        return "model_abstain"
    if method is None:
        return "anm_abstain"
    return "disagree"


def _agreement(cases):
    rows = []
    for package in PACKAGES:
        for condition in MODEL_CONDITIONS:
            counts = dict.fromkeys(
                ("agree_answer", "agree_abstain", "model_abstain", "anm_abstain", "disagree"), 0
            )
            states = []
            for case in cases:
                prefix = f"{package.lower()}_{condition.lower()}"
                model_state = case[f"{prefix}_state"]
                method_state = case["e4_anm_only_state"]
                states.append((model_state, method_state))
                if model_state not in {"answer", "abstain"} or method_state not in {
                    "answer",
                    "abstain",
                }:
                    continue
                counts[_relation(case[f"{prefix}_direction"], case["anm_direction"])] += 1
            rows.append(
                {
                    "package": package,
                    "condition": condition,
                    **counts,
                    "total_case_count": len(cases),
                    "comparable_case_count": sum(counts.values()),
                    "prediction_failure_count": sum(m == "prediction_failure" for m, _ in states),
                    "method_unavailable_count": sum(a == "method_unavailable" for _, a in states),
                    "checker_suppressed_count": sum(m == "checker_suppressed" for m, _ in states),
                    "outcome_unavailable_count": sum(m == "outcome_unavailable" for m, _ in states),
                    "excluded_case_count": len(cases) - sum(counts.values()),
                }
            )
    return rows


def _groups(cases):
    groups = []
    names = sorted({case["source_group"] for case in cases})
    for name in names:
        members = [case for case in cases if case["source_group"] == name]
        groups.append(
            {
                "source_group": name,
                "case_count": len(members),
                "weight": math.fsum(case["weight"] for case in members),
                "e4_s1_correct": sum(case["e4_s1_correct"] is True for case in members),
                "e4_s1_wrong": sum(case["e4_s1_correct"] is False for case in members),
                "e4_s1_abstain": sum(case["e4_s1_state"] == "abstain" for case in members),
                "e4_s1_failure": sum(
                    case["e4_s1_state"] == "prediction_failure" for case in members
                ),
                "e4_anm_unavailable": sum(
                    case["e4_anm_only_state"] == "method_unavailable" for case in members
                ),
                "e4_anm_correct": sum(case["anm_correct"] is True for case in members),
                "e4_anm_wrong": sum(case["anm_correct"] is False for case in members),
                "e4_anm_abstain": sum(case["e4_anm_only_state"] == "abstain" for case in members),
            }
        )
    return groups


def _decide(margin, threshold):
    if margin > threshold:
        return "A_to_B"
    if margin < -threshold:
        return "B_to_A"
    return None


def _threshold_curve(cases, thresholds=(0.0, 0.001, 0.01, 0.1)):
    if any(case["margin"] is None for case in cases):
        return {
            "status": "margins_unavailable",
            "rows": [],
            "note": "Pass saved ANM result.json files to score other thresholds.",
        }
    rows = []
    total = math.fsum(case["weight"] for case in cases)
    for threshold in thresholds:
        released, correct = [], []
        for case in cases:
            direction = _decide(case["margin"], threshold)
            if direction is None:
                continue
            released.append(case["weight"])
            if direction == case["reference_direction"]:
                correct.append(case["weight"])
        released_weight = math.fsum(released)
        correct_weight = math.fsum(correct)
        rows.append(
            {
                "threshold": threshold,
                "coverage": released_weight / total,
                "selective_accuracy": correct_weight / released_weight if released_weight else None,
                "correct_yield": correct_weight / total,
                "pilot_threshold": threshold == 0.001,
            }
        )
    return {
        "status": "saved_margins_only",
        "rows": rows,
        "note": "Exploratory curve. Do not adopt a new threshold from this pilot.",
    }


def load_anm_results(root: Path):
    """Read completed ANM directories and verify each original request before use."""
    results = {}
    root = Path(root)
    if not root.is_dir():
        raise ValueError("ANM root is not a directory")
    for path in sorted(item for item in root.iterdir() if item.is_dir()):
        if not (path / "result.json").is_file():
            continue
        if not (path / "request.json").is_file():
            raise ValueError("ANM result is missing its original request: " + path.name)
        from causalbridge.discovery.anm import load_anm_artifacts

        artifacts = load_anm_artifacts(path)
        if artifacts.request.case_id != path.name:
            raise ValueError("ANM request case does not match its directory")
        saved = _validated_anm(
            path.name, artifacts.result.model_dump(mode="json"), artifacts.request.ab_mapping_id
        )
        results[path.name] = saved.model_dump(mode="json")
    if not results:
        raise ValueError("ANM root contains no result.json files")
    return results


def load_experiment_receipts(path):
    """Read original journal receipts without rewriting or recovering historical files.

    Hashes detect corruption; the caller must supply the retained experiment
    journal, not a journal reconstructed from replacement ANM artifacts.
    """
    from causalbridge.discovery.evidence import digest
    from causalbridge.llm.parser import reject_duplicate_keys

    receipts = []
    previous = None
    for seq, line in enumerate(Path(path).read_text().splitlines()):
        event = json.loads(line, object_pairs_hook=reject_duplicate_keys)
        payload = {key: event[key] for key in ("seq", "previous", "kind", "data")}
        if (
            event["seq"] != seq
            or event["previous"] != previous
            or event["digest"] != digest(payload)
        ):
            raise ValueError("Corrupt original experiment journal")
        previous = event["digest"]
        if event["kind"] == "native_started":
            receipt = event["data"]["receipt"]
            if receipt.get("method_result_digest") is not None:
                receipts.append(receipt)
    if not receipts:
        raise ValueError("Original experiment journal contains no ANM receipts")
    return receipts


def main():
    import argparse

    from causalbridge.discovery.anm_requests import read_json, write_json_exclusive
    from causalbridge.llm.parser import reject_duplicate_keys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--anm-root", type=Path)
    parser.add_argument("--experiment-journal", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in args.analysis.read_text().splitlines()
        if line.strip()
    ]
    anm = load_anm_results(args.anm_root) if args.anm_root else None
    receipts = (
        load_experiment_receipts(args.experiment_journal) if args.experiment_journal else None
    )
    result = diagnose_pilot(
        rows,
        read_json(args.evaluator),
        read_json(args.mapping),
        anm,
        experiment_receipts=receipts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(args.output, result)
    print(
        json.dumps(
            {
                "case_count": result["case_count"],
                "source_group_count": result["source_group_count"],
                "contrasts": result["contrasts"],
                "checker": [
                    {key: value for key, value in row.items() if key != "rejections"}
                    for row in result["checker"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
