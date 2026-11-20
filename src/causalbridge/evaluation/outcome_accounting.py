"""Post-run categories preserve nonrelease reasons and fixed scoring denominators."""

from collections import Counter

from causalbridge.evaluation.saved_checks import validate_panel


def outcome_category(row, parent=None):
    if row["condition"] == "ANM_ONLY":
        if not row["prediction_scorable"] or row.get("failure_stage"):
            return "method_unavailable"
        return "method_abstention" if row["predicted_direction"] is None else "answer"
    if row.get("failure_stage") or not row["prediction_scorable"]:
        return "execution_or_binding_failure"
    if row["condition"] in {"S2", "SIMPLE_GATE"}:
        if parent is None:
            raise ValueError("Derived outcome requires its S1 parent")
        if row["outcome"] == "checker_error":
            return "checker_failure"
        if row["condition"] == "S2" and row["outcome"] == "fail":
            return "checker_rejection"
        if row["outcome"] == "method_unavailable_or_unconfigured":
            return "gate_rejection"
        if row["predicted_direction"] is None and parent["outcome"] == "model_abstention":
            return "upstream_model_abstention"
    if row["predicted_direction"] is not None:
        return "answer"
    if row["outcome"] == "model_abstention":
        return "model_abstention"
    raise ValueError("Unclassified nonrelease outcome: " + row["outcome"])


def account_panel(rows, evaluator, mapping, scores):
    truth, columns = validate_panel(rows, evaluator, mapping, scores, len(evaluator))
    index = {(r["case_id"], r["package"], r["condition"]): r for r in rows}
    details, groups = [], {}
    for row in rows:
        case, package, condition = row["case_id"], row["package"], row["condition"]
        e = truth[case]
        cause = 0 if e["reference_direction"] == "first_to_second" else 1
        gold = (
            "A_to_B" if columns[case]["original_to_runtime_column_order"][0] == cause else "B_to_A"
        )
        parent = index.get((case, package, "S1")) if condition in {"S2", "SIMPLE_GATE"} else None
        category = outcome_category(row, parent)
        if category == "answer":
            category = "correct_answer" if row["predicted_direction"] == gold else "wrong_answer"
        record = {
            "case_id": case,
            "package": package,
            "condition": condition,
            "category": category,
            "weight": e["weight"],
            "failure_stage": row.get("failure_stage"),
            "reason_codes": row["reason_codes"],
            "parent_direction": parent["predicted_direction"] if parent else None,
            "suppressed_parent_correct": (
                parent["predicted_direction"] == gold
                if parent
                and category in {"checker_rejection", "gate_rejection"}
                and parent["predicted_direction"] is not None
                else None
            ),
        }
        details.append(record)
        groups.setdefault((package, condition), []).append(record)
    summaries = []
    for score in scores:
        group = groups[score["package"], score["condition"]]
        counts = dict(Counter(r["category"] for r in group))
        weights = {c: sum(r["weight"] for r in group if r["category"] == c) for c in counts}
        summaries.append(
            {
                **score,
                "categories": counts,
                "category_weights": weights,
                "no_released_direction_count": sum(
                    r["category"] not in {"correct_answer", "wrong_answer"} for r in group
                ),
            }
        )
    contrasts = []
    by_key = {(s["package"], s["condition"]): s for s in scores}
    for condition in ("S0", "S1"):
        e2, e3 = by_key["E2", condition], by_key["E3", condition]
        contrasts.append(
            {
                "contrast": "E3_minus_E2",
                "condition": condition,
                **{key: e3[key] - e2[key] for key in ("coverage", "correct_yield", "wrong_yield")},
            }
        )
    return {
        "scope": "saved_record_accounting_not_new_inference",
        "case_count": len(truth),
        "metrics": summaries,
        "e2_e3_contrasts": contrasts,
        "records": details,
    }
