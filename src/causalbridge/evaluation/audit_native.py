"""Read-only native Phase 4 handshake audit; no execution or checker imports.

Uses independent JSON/hash helpers from Phase 3, but native digest convention.
This validates the recorded handshake, not causal accuracy or raw source eligibility.
"""

import argparse
import hashlib
import json
from pathlib import Path

from causalbridge.discovery.schemas import DirectionEvidence, DirectionPrediction
from causalbridge.evaluation.audit import _hash, _json
from causalbridge.evaluation.audit_policy import CAUTION

NATIVE_BASE = (
    "Assess which direction is more plausible between A and B using the supplied evidence."
)
NATIVE_SUFFIX = (
    "\nReturn JSON only matching the supplied schema. "
    "Use A_to_B, B_to_A or null with abstained=true and a reason. Copy the supplied "
    "case_id and package_digest. Scores and margins are diagnostics, not calibrated causal "
    "probabilities. Observations and ANM preferences are not proof of causation. "
    "Claims may cite only supplied evidence. Qualified disagreement with ANM is permitted."
)


COMPACT_OUTPUT = (
    "\nKeep the structured response concise. Supply at most three relevant claims; "
    "never enumerate or copy all displayed rows. Use a short reason_code. "
    "Cite only evidence present in this package: display_row claims require display_rows, "
    "summary claims require the cited supplied statistic, and method_direction claims "
    "require a non-null method_result with an available direction. "
    "Do not invent values or citations. Use claims=[] when no relevant citations are available. "
    "Abstention remains allowed: predicted_direction=null, abstained=true, and a short reason."
)


def _native_hash(value):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
            ).encode()
        ).hexdigest()
    )


def audit_native(root):
    root = Path(root)
    findings, events = [], []

    def check(ok, code, key):
        if not ok:
            findings.append({"code": code, "location": key})

    maps = {
        k: {} for k in ("native_started", "native_generated", "native_finished", "native_released")
    }
    try:
        raw = (root / "events.jsonl").read_bytes()
        check(not raw or raw.endswith(b"\n"), "partial_tail", "events.jsonl")
        previous = None
        for i, line in enumerate(raw.splitlines()):
            event = _json(line)
            payload = {k: event[k] for k in ("seq", "previous", "kind", "data")}
            check(
                event["seq"] == i
                and event["previous"] == previous
                and event["digest"] == _hash(payload),
                "journal_integrity",
                str(i),
            )
            events.append(event)
            previous = event["digest"]
            kind, data = event["kind"], event["data"]
            if kind in maps:
                check(data["key"] not in maps[kind], "duplicate_event", kind)
                if kind in {"native_generated", "native_finished"}:
                    check(data["key"] in maps["native_started"], "event_order", kind)
                maps[kind][data["key"]] = data
            else:
                check(kind in {"native_invocation", "recovery"}, "event_kind", kind)
        starts, raws, ends, releases = (maps[k] for k in maps)
        for key, start in starts.items():
            identity = {
                k: v
                for k, v in start.items()
                if k not in {"key", "attempt_id", "invocation_id", "parent_attempt_id"}
            }
            check(_native_hash(identity) == key, "cache_key", key)
            e = DirectionEvidence.model_validate(start["package"]["evidence"])
            receipt = start["receipt"]
            check(
                receipt["package_digest"] == e.package_digest
                and receipt["display_sample_digest"] == e.display_sample_digest,
                "original_evidence_binding",
                key,
            )
            name = start["condition"]["condition_id"]
            protocol = start["protocol"]
            check(
                protocol in {"integrated-track-b-v1", "integrated-track-b-v2-compact"},
                "protocol_policy",
                key,
            )
            compact = protocol == "integrated-track-b-v2-compact"
            expected_system = (
                NATIVE_BASE
                + (COMPACT_OUTPUT if compact else "")
                + (CAUTION if name == "S1" else "")
                + NATIVE_SUFFIX
            )
            check(start["condition"]["version"] == protocol, "condition_version", key)
            check(
                start["prompt_version"]
                == ("direction-0.2-compact" if compact else "direction-0.1"),
                "prompt_version",
                key,
            )
            check(
                name in {"S0", "S1"} and start["messages"][0]["content"] == expected_system,
                "prompt_policy",
                key,
            )
            check(
                start["output_schema"] == DirectionPrediction.model_json_schema(),
                "schema_policy",
                key,
            )
            user = _json(start["messages"][1]["content"])
            check(
                user
                == dict(
                    question="Which direction is more plausible, A → B or B → A? You may abstain.",
                    evidence=e.model_dump(mode="json"),
                    case_id=e.case_id,
                    package_digest=e.package_digest,
                    display_sample_digest=e.display_sample_digest,
                ),
                "public_payload",
                key,
            )
            selected = start["package"]["selected"]
            if e.package != "E1":
                check(
                    [list(r) for r in e.display_rows] == selected["display_rows"],
                    "selected_display_binding",
                    key,
                )
                columns = list(zip(*e.display_rows, strict=True))
                for i, column in enumerate(columns):
                    import math

                    mean = math.fsum(column) / len(column)
                    std = math.sqrt(math.fsum((v - mean) ** 2 for v in column) / len(column))
                    check(
                        math.isclose(e.summary.mean[i], mean, rel_tol=1e-12, abs_tol=1e-12)
                        and math.isclose(e.summary.std[i], std, rel_tol=1e-12, abs_tol=1e-12),
                        "display_summary",
                        key,
                    )
            if e.package == "E4":
                request = start["package"]["method_request"]
                method_dir = Path(start["package"]["method_directory"])
                original = _json((method_dir / "request.json").read_text())
                sample = _json((method_dir / "sample.json").read_text())
                config = _json((method_dir / "config.json").read_text())
                result = _json((method_dir / "result.json").read_text())
                reproducibility = _json((method_dir / "reproducibility.json").read_text())
                check(
                    original == request == receipt["method_request"], "original_method_request", key
                )
                check(
                    sample["rows"] == selected["method_rows"]
                    and sample["ab_mapping_id"] == e.ab_mapping_id
                    and _native_hash(sample) == request["sample_digest"]
                    and _native_hash(config) == request["config_digest"],
                    "method_input_binding",
                    key,
                )
                check(
                    result == e.method_result.model_dump(mode="json")
                    and receipt["method_result_digest"] == _native_hash(result)
                    and result["provenance"]["reproducibility_ref"]
                    == _native_hash(reproducibility),
                    "method_result_binding",
                    key,
                )
            end = ends[key]
            trace = end["execution"]
            if trace is None:
                check(end["operational_error"] == "interrupted_unknown", "unknown_state", key)
                continue
            check(
                trace["request_messages"] == start["messages"]
                and trace["output_schema"] == start["output_schema"]
                and trace["evidence"] == start["package"]["evidence"],
                "execution_binding",
                key,
            )
            if key in raws:
                check(trace["generation"] == raws[key]["generation"], "raw_generation_binding", key)
            else:
                check(
                    trace["failure_stage"] == "generate" and trace["generation"] is None,
                    "missing_generation",
                    key,
                )
            generation = trace["generation"]
            http_incomplete = False
            if generation and generation.get("raw_response") is not None:
                body = _json(generation["raw_response"])
                content = body.get("message", {}).get("content")
                check(
                    generation["text"] == (content if isinstance(content, str) else "")
                    and generation["input_tokens"] == body.get("prompt_eval_count")
                    and generation["output_tokens"] == body.get("eval_count")
                    and generation["model"]
                    == body.get("model", (start.get("config") or {}).get("model")),
                    "http_generation_binding",
                    key,
                )
                # Derive every HTTP completion state independently of the stored status.
                expected_status, expected_reason = "complete", None
                if body.get("done_reason") == "length":
                    expected_status, expected_reason = "truncated", "output_token_limit"
                elif body.get("done") is not True:
                    expected_status, expected_reason = "incomplete", "response_not_done"
                elif not isinstance(content, str) or not content.strip():
                    expected_status, expected_reason = "incomplete", "missing_text_content"
                http_incomplete = expected_status != "complete"
                check(
                    generation.get("status") == expected_status
                    and generation.get("failure_reason") == expected_reason,
                    "http_truncation_status"
                    if expected_status == "truncated"
                    else "http_completion_status",
                    key,
                )
            if generation and (
                http_incomplete or generation.get("status", "complete") != "complete"
            ):
                check(
                    trace["failure_stage"] == "generate"
                    and trace["prediction"] is None
                    and end["context"] is None
                    and bool(generation.get("failure_reason")),
                    "incomplete_generation_not_scorable",
                    key,
                )
            if trace["failure_stage"] is None:
                parsed = DirectionPrediction.model_validate(_json(trace["generation"]["text"]))
                check(
                    parsed.model_dump(mode="json") == trace["prediction"]
                    and parsed.case_id == e.case_id
                    and parsed.package_digest == e.package_digest,
                    "prediction_binding",
                    key,
                )
                expected = dict(receipt, proposal_digest=parsed.proposal_digest)
                check(end["context"] == expected, "saved_context", key)
            else:
                check(end["context"] is None, "failed_context", key)
        for release in releases.values():
            key = release["source_key"]
            trace = ends[key]["execution"]
            check(
                starts[key]["condition"]["condition_id"] == "S1"
                and release["source_attempt_id"] == starts[key]["attempt_id"]
                and release["parent_outcome_digest"] == _native_hash(ends[key]),
                "s2_parent",
                key,
            )
            if trace is None or trace["failure_stage"] is not None:
                check(
                    release["check"] is None
                    and release["skip_reason"] == "parent_prediction_failed"
                    and release["released_direction"] is None,
                    "s2_failed_parent",
                    key,
                )
                continue
            checked, prediction = release["check"], trace["prediction"]
            if checked is None:
                check(
                    release["skip_reason"] == "checker_error"
                    and release["released_direction"] is None,
                    "s2_missing_check",
                    key,
                )
                continue
            check(
                checked["case_id"] == trace["evidence"]["case_id"]
                and checked["package_digest"] == _native_hash(trace["evidence"])
                and checked["proposal_digest"] == _native_hash(prediction),
                "check_binding",
                key,
            )
            expected_direction = prediction["predicted_direction"] if checked["release"] else None
            check(
                release["released_direction"] == expected_direction
                and (not checked["release"] or checked["status"] == "pass"),
                "s2_release",
                key,
            )
        manifests = list((root / "manifests").glob("*.json"))
        check(bool(manifests), "no_manifests", "manifests")
        for path in manifests:
            m = _json(path.read_text())
            keys = m["expected_keys"]
            check(
                _native_hash(keys).removeprefix("sha256:") == path.stem
                and len(keys) == len(set(keys)),
                "manifest_identity",
                path.name,
            )
            export = _json((root / "exports" / (path.stem + ".json")).read_text())
            check(
                export["trials"] == [dict(start=starts[k], outcome=ends[k]) for k in keys],
                "trial_export",
                path.name,
            )
            s2 = _json((root / "exports" / (path.stem + "-s2.json")).read_text())
            expected = {k for k in keys if starts[k]["condition"]["condition_id"] == "S1"}
            check(
                {r["source_key"] for r in s2} == expected and len(s2) == len(expected),
                "s2_completeness",
                path.name,
            )
            check(all(releases[r["key"]] == r for r in s2), "s2_export", path.name)
        for event in events:
            if event["kind"] != "native_invocation":
                continue
            invocation = event["data"]
            new = {
                k for k, s in starts.items() if s["invocation_id"] == invocation["invocation_id"]
            }
            check(
                new == set(invocation["new_trial_keys"])
                and invocation["new_model_calls"] == len(new),
                "call_accounting",
                invocation["invocation_id"],
            )
            manifest = _json(
                (root / "manifests" / (invocation["manifest_id"] + ".json")).read_text()
            )
            for field in ("input_tokens", "output_tokens"):
                for group, usage_keys in (
                    ("new_usage", new),
                    ("historical_usage", set(manifest["expected_keys"]) - new),
                ):
                    values = [
                        ends[k]["execution"]["generation"][field]
                        if ends[k]["execution"] and ends[k]["execution"]["generation"]
                        else None
                        for k in usage_keys
                    ]
                    expected = sum(values) if all(v is not None for v in values) else None
                    check(
                        invocation[group][field] == expected,
                        "usage_accounting",
                        invocation["invocation_id"],
                    )
        for path in manifests:
            m = _json(path.read_text())
            grouped = {}
            for key in m["expected_keys"]:
                start = starts[key]
                e = start["package"]["evidence"]
                grouped.setdefault(e["case_id"], {})[
                    (e["package"], start["condition"]["condition_id"])
                ] = start
            for case, group in grouped.items():
                check(
                    set(group) == {(p, c) for p in ("E1", "E2", "E3", "E4") for c in ("S0", "S1")},
                    "complete_matrix",
                    case,
                )
                for p in ("E1", "E2", "E3", "E4"):
                    a, b = group[(p, "S0")], group[(p, "S1")]
                    check(
                        a["package"] == b["package"]
                        and a["config"] == b["config"]
                        and a["model_identity"] == b["model_identity"]
                        and a["output_schema"] == b["output_schema"],
                        "condition_isolation",
                        case,
                    )
                numeric = [group[(p, "S0")]["package"]["evidence"] for p in ("E2", "E3", "E4")]
                named = [group[(p, "S0")]["package"]["evidence"] for p in ("E1", "E3", "E4")]
                check(
                    all(
                        e["variable_labels"] == named[0]["variable_labels"]
                        and e["units"] == named[0]["units"]
                        for e in named
                    ),
                    "matched_context",
                    case,
                )
                selections = [
                    group[(p, "S0")]["package"]["selected"] for p in ("E1", "E2", "E3", "E4")
                ]
                check(all(s == selections[0] for s in selections), "matched_selection", case)
                evidence = [
                    group[(p, "S0")]["package"]["evidence"] for p in ("E1", "E2", "E3", "E4")
                ]
                check(
                    all(
                        e["ab_mapping_id"] == evidence[0]["ab_mapping_id"]
                        and e["mapping_seed"] == evidence[0]["mapping_seed"]
                        for e in evidence
                    ),
                    "matched_mapping",
                    case,
                )
                check(
                    all(
                        e["display_rows"] == numeric[0]["display_rows"]
                        and e["summary"] == numeric[0]["summary"]
                        for e in numeric
                    ),
                    "matched_numeric",
                    case,
                )
    except (ValueError, KeyError, TypeError, OSError, IndexError, AttributeError) as exc:
        findings.append({"code": "unreadable_or_invalid_artifact", "detail": type(exc).__name__})
    return dict(
        audit_version="native-handshake-audit-v2",
        model_modes=sorted({s["model_mode"] for s in maps["native_started"].values()}),
        observation_kinds=sorted(
            {s.get("observation_kind", "unspecified") for s in maps["native_started"].values()}
        ),
        auditor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_files_sha256={
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.name != "writer.lock"
        },
        passed=not findings,
        findings=findings,
        counts={k: len(v) for k, v in maps.items()},
        limitations=[
            "Transport mode and observation provenance are separate; "
            "legacy undeclared provenance stays unspecified.",
            "Checks durable method request/result binding, not statistical validity.",
            "Real source-family eligibility and scorer consumption are pending.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() in args.output.resolve().parents:
        parser.error("Report must be outside the input experiment")
    report = audit_native(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
