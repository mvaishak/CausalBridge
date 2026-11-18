"""Label-free analysis rows and prespecified execution baselines, not scoring."""

from causalbridge.llm.predictor import PredictionExecution

EXPORT_VERSION = "native-analysis-v2"


def analysis_rows(run: dict, releases: list[dict]) -> list[dict]:
    by_parent = {r["source_key"]: r for r in releases}
    rows = []
    for trial in run["trials"]:
        start, end = trial["start"], trial["outcome"]
        evidence = start["package"]["evidence"]
        trace = PredictionExecution.model_validate(end["execution"]) if end["execution"] else None
        usable = trace is not None and trace.failure_stage is None
        direction = trace.prediction.predicted_direction if usable else None
        base = dict(
            export_version=EXPORT_VERSION,
            manifest_id=run["manifest_id"],
            case_id=evidence["case_id"],
            package=evidence["package"],
            ab_mapping_id=evidence["ab_mapping_id"],
            package_digest=start["receipt"]["package_digest"],
            attempt_id=start["attempt_id"],
            run_id=trace.run_id if trace else None,
            model_identity=start["model_identity"],
            model_mode=start["model_mode"],
            observation_kind=start.get("observation_kind", "unspecified"),
            prediction_binding="valid" if usable else "invalid_or_unavailable",
            prediction_scorable=usable,
            generation_status=trace.generation.status
            if trace and trace.generation
            else "unavailable",
            generation_failure_reason=trace.generation.failure_reason
            if trace and trace.generation
            else None,
            supplied_claim_count=len(trace.prediction.claims)
            if trace and trace.prediction is not None
            else None,
            supporting_claims_status="not_checked",
            checked_claim_count=0,
            released_direction=None,
            causal_correctness=None,
            causal_correctness_status="requires_separate_evaluator_labels",
            protocol=start["protocol"],
            failure_stage=trace.failure_stage if trace else end["operational_error"],
            input_tokens=trace.generation.input_tokens if trace and trace.generation else None,
            output_tokens=trace.generation.output_tokens if trace and trace.generation else None,
        )
        rows.append(
            base
            | dict(
                condition=start["condition"]["condition_id"],
                predicted_direction=direction,
                outcome="prediction_failure"
                if not usable
                else "model_abstention"
                if direction is None
                else "answer",
                reason_codes=[trace.prediction.reason_code]
                if usable and trace.prediction.reason_code
                else [],
                parent_attempt_id=None,
            )
        )
        if start["condition"]["condition_id"] != "S1":
            continue
        release = by_parent.get(start["key"])
        if release is None:
            raise ValueError("Missing S2 outcome for scheduled S1")
        check = release["check"]
        released = release["released_direction"]
        if not usable:
            valid = (
                check is None
                and release["skip_reason"] == "parent_prediction_failed"
                and released is None
            )
        elif check is None:
            valid = release["skip_reason"] == "checker_error" and released is None
        else:
            valid = (
                release["skip_reason"] is None
                and (not check["release"] or check["status"] == "pass")
                and released == (direction if check["release"] else None)
            )
        if not valid:
            raise ValueError("Contradictory S2 outcome for saved parent")
        rows.append(
            base
            | dict(
                condition="S2",
                predicted_direction=release["released_direction"],
                parent_attempt_id=start["attempt_id"],
                outcome=release["skip_reason"] or check["status"],
                reason_codes=check["reason_codes"] if check else [],
                checker_version=check["checker_version"] if check else None,
                released_direction=released,
                supporting_claims_status="not_checked"
                if check is None
                else "no_supporting_claims_supplied"
                if not trace.prediction.claims
                else "checked",
                checked_claim_count=len(check["claim_findings"]) if check else 0,
                input_tokens=0,
                output_tokens=0,
            )
        )
        method = evidence["method_result"]
        gate = evidence["package"] != "E4" or (
            method["status"] == "ok" and method["threshold"] is not None
        )
        rows.append(
            base
            | dict(
                condition="SIMPLE_GATE",
                parent_attempt_id=start["attempt_id"],
                predicted_direction=direction if usable and gate else None,
                outcome="parent_failure"
                if not usable
                else "gate_pass"
                if gate
                else "method_unavailable_or_unconfigured",
                reason_codes=[],
                input_tokens=0,
                output_tokens=0,
            )
        )
        if evidence["package"] == "E4":
            rows.append(
                base
                | dict(
                    condition="ANM_ONLY",
                    prediction_scorable=method["status"] == "ok"
                    and method["threshold"] is not None,
                    prediction_binding="valid",
                    generation_status="not_applicable",
                    generation_failure_reason=None,
                    supplied_claim_count=None,
                    model_identity=None,
                    attempt_id=None,
                    run_id=None,
                    parent_attempt_id=None,
                    predicted_direction=method["predicted_direction"]
                    if method["status"] == "ok"
                    else None,
                    outcome=method["reason_code"] or method["decision"],
                    reason_codes=[method["reason_code"]] if method["reason_code"] else [],
                    failure_stage=method["error_category"],
                    input_tokens=0,
                    output_tokens=0,
                    method_config_digest=method["provenance"]["config_digest"],
                )
            )
    return rows


def evaluator_mapping(packages):
    """Private mapping handoff for post-run label joins. Never send to predictor."""
    mappings = {}
    for package in packages:
        e = package.evidence
        selected = package.selected.selection
        value = dict(
            case_id=e.case_id,
            ab_mapping_id=e.ab_mapping_id,
            original_to_runtime_column_order=list(selected.column_order),
            mapping_seed=selected.spec.mapping_seed,
            source_digest=selected.source_digest,
        )
        if e.case_id in mappings and mappings[e.case_id] != value:
            raise ValueError("Conflicting evaluator mappings for one case")
        mappings[e.case_id] = value
    return list(mappings.values())
