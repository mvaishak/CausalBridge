"""Strict saved-record completeness checks; no inference or method execution."""

import json

from causalbridge.evaluation.scoring import PILOT_CONDITIONS, score_pilot


def unique_index(rows, field):
    indexed = {}
    for row in rows:
        key = row[field]
        if key in indexed:
            raise ValueError(f"Duplicate {field}: {key}")
        indexed[key] = row
    return indexed


def validate_panel(rows, evaluator, mapping, scores, case_count):
    truth = unique_index(evaluator, "case_id")
    columns = unique_index(mapping, "case_id")
    if len(truth) != case_count or len(columns) != case_count or truth.keys() != columns.keys():
        raise ValueError("Incomplete or mismatched evaluator/mapping cases")
    keys = [(r["case_id"], r["package"], r["condition"]) for r in rows]
    expected = {(case, p, c) for case in truth for p, c in PILOT_CONDITIONS}
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Duplicate, missing or unplanned analysis trial")
    calculated = score_pilot(rows, evaluator, mapping)
    if calculated != scores:
        raise ValueError("Saved scores do not reproduce from bound analysis")
    return truth, columns


def journal_trials(events, expected_count=None):
    stages = {}
    for kind in ("native_started", "native_generated", "native_finished"):
        stages[kind] = unique_index([e["data"] for e in events if e["kind"] == kind], "key")
    starts, generated, finished = stages.values()
    if starts.keys() != generated.keys() or starts.keys() != finished.keys():
        raise ValueError("Started, generated and finished trial identities differ")
    if expected_count is not None and len(starts) != expected_count:
        raise ValueError("Unexpected journal trial count")
    unique_index(list(starts.values()), "attempt_id")
    for key, start in starts.items():
        execution = finished[key]["execution"]
        generation = generated[key]["generation"]
        if execution is None or execution["generation"] != generation:
            raise ValueError("Finished execution differs from durable generation")
        if (
            execution["request_messages"] != start["messages"]
            or execution["output_schema"] != start["output_schema"]
            or execution["generation_config"] != start["config"]
        ):
            raise ValueError("Finished execution differs from original request")
        raw = json.loads(generation["raw_response"])
        if raw.get("model") != generation["model"] or (
            raw.get("message", {}).get("content") != generation["text"]
        ):
            raise ValueError("Parsed generation differs from raw model response")
        if (
            generation["status"] != "complete"
            or raw.get("done") is not True
            or raw.get("done_reason") == "length"
        ):
            raise ValueError("Incomplete raw generation in completed panel")
    return starts, {k: v["generation"] for k, v in generated.items()}, finished
