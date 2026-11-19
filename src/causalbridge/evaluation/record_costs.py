"""Measured generation accounting from unique original journal events, not exports."""

import math
from collections import Counter


def _index(events, kind):
    result = {}
    for event in events:
        if event["kind"] != kind:
            continue
        data = event["data"]
        if data["key"] in result:
            raise ValueError("Duplicate original event: " + kind)
        result[data["key"]] = data
    return result


def _measured(values, *, integer=False):
    for value in values:
        if value is not None and (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
            or (integer and type(value) is not int)
        ):
            raise ValueError("Invalid measured usage/latency")
    known = [v for v in values if v is not None]
    return dict(
        total=(sum(known) if integer else math.fsum(known)) if len(known) == len(values) else None,
        known_total=sum(known) if integer else math.fsum(known),
        missing_count=len(values) - len(known),
    )


def _percentile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    at = probability * (len(ordered) - 1)
    lower = math.floor(at)
    fraction = at - lower
    return ordered[lower] * (1 - fraction) + ordered[math.ceil(at)] * fraction


def generation_costs(events):
    """Native audit and manifest/schedule validation are required before this helper.

    Invocation summaries, resume exports and S2 parent copies are never summed.
    Unknown observations remain unknown instead of becoming zero-cost calls.
    """
    starts = _index(events, "native_started")
    generated = _index(events, "native_generated")
    finished = _index(events, "native_finished")
    if not starts or set(finished) != set(starts) or not set(generated) <= set(starts):
        raise ValueError("Original start/finish/generation identities do not match")
    attempts = [s["attempt_id"] for s in starts.values()]
    if len(attempts) != len(set(attempts)):
        raise ValueError("Duplicate original attempt identity")
    buckets = {}
    for key, start in starts.items():
        package = start["package"]["evidence"]["package"]
        condition = start["condition"]["condition_id"]
        if condition not in ("S0", "S1"):
            raise ValueError("Only primary model generations belong in cost totals")
        execution = finished[key]["execution"]
        generation = generated.get(key, {}).get("generation")
        if execution and generation != execution.get("generation"):
            raise ValueError("Original generation and retained execution disagree")
        if not generation and execution and execution["failure_stage"] is None:
            raise ValueError("Completed prediction has no generation receipt")
        buckets.setdefault((package, condition), []).append((generation, execution, finished[key]))
    rows = []
    for (package, condition), attempts in sorted(buckets.items()):
        generations = [g or {} for g, _, _ in attempts]
        latencies = [g.get("latency_seconds") for g in generations]
        latency = _measured(latencies)
        rows.append(
            dict(
                package=package,
                condition=condition,
                scheduled_attempts=len(attempts),
                observed_generation_records=sum(bool(g) for g, _, _ in attempts),
                input_tokens=_measured([g.get("input_tokens") for g in generations], integer=True),
                output_tokens=_measured(
                    [g.get("output_tokens") for g in generations], integer=True
                ),
                generation_latency_seconds=latency,
                mean_generation_latency_seconds=latency["total"] / len(attempts)
                if latency["total"] is not None
                else None,
                median_generation_latency_seconds=_percentile(
                    [v for v in latencies if v is not None], 0.5
                ),
                p95_generation_latency_seconds=_percentile(
                    [v for v in latencies if v is not None], 0.95
                ),
                latency_quantile_observation_count=sum(v is not None for v in latencies),
                failure_stage_counts=dict(
                    Counter(
                        (execution["failure_stage"] or "success")
                        if execution
                        else (end.get("operational_error") or "execution_unavailable")
                        for _, execution, end in attempts
                    )
                ),
                measured_monetary_cost=None,
            )
        )
    return rows
