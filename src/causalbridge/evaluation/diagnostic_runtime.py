"""Durable live or explicitly scripted execution of the frozen cue experiment."""

import json
import random
import time
from pathlib import Path

import httpx

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.diagnostic_protocol import (
    CueDecisionV2,
    CueDecisionV3,
    CuePrediction,
    read,
    request_payload,
    synthetic_cases,
    validate_plan,
    write,
)
from causalbridge.llm.parser import reject_duplicate_keys


def decode(raw, payload, model):
    """Classify execution before checking the citation; never rescue truncated output."""
    if raw["http_status"] != 200:
        raise ValueError("http_failure")
    body = json.loads(raw["body"])
    if body.get("model") != model:
        raise ValueError("response_model_mismatch")
    if body.get("done") is not True or body.get("done_reason") == "length":
        raise ValueError("incomplete_or_truncated")
    message = body["message"]
    if payload["think"] and not message.get("thinking"):
        raise ValueError("thinking_not_activated")
    if not payload["think"] and message.get("thinking"):
        raise ValueError("unexpected_thinking")
    if payload["format"] == CueDecisionV3.model_json_schema():
        fields = json.loads(message["content"], object_pairs_hook=reject_duplicate_keys)
        prediction = CueDecisionV3.model_validate(fields).normalized()
    elif payload["format"] == CueDecisionV2.model_json_schema():
        fields = json.loads(message["content"], object_pairs_hook=reject_duplicate_keys)
        prediction = CueDecisionV2.model_validate(fields).normalized()
    elif payload["format"] == CuePrediction.model_json_schema():
        prediction = CuePrediction.model_validate_json(message["content"]).model_dump(mode="json")
    else:
        raise ValueError("unknown_output_contract")
    user = json.loads(payload["messages"][1]["content"])
    diagnostic = user["external_diagnostic"]
    cited = prediction["diagnostic_direction_cited"]
    expected = diagnostic["direction"] if diagnostic else None
    reasons = []
    if cited is not None and cited != expected:
        reasons.append("incorrect_diagnostic_citation")
    if "diagnostic" in prediction["evidence_basis"] and (expected is None or cited is None):
        reasons.append("missing_or_unavailable_diagnostic_citation")
    return prediction, {
        "passed": not reasons,
        "reason_codes": reasons,
        "release": not reasons and not prediction["abstained"],
        "scope": (
            "structured diagnostic attribution only; not causal truth, numeric"
            " citations or unrestricted prose"
        ),
    }


def fake_response(payload):
    """Deterministic plumbing fixture, not a simulated scientific performance result."""
    user = json.loads(payload["messages"][1]["content"])
    cue = user["external_diagnostic"]
    direction = cue["direction"] if cue else None
    prediction = {
        "predicted_direction": direction,
        "abstained": direction is None,
        "diagnostic_direction_cited": direction,
        "evidence_basis": ["diagnostic"] if cue else [],
        "explanation": "SCRIPTED SOFTWARE FIXTURE: copies cue or abstains.",
    }
    if payload["format"] == CueDecisionV3.model_json_schema():
        prediction.pop("predicted_direction")
        prediction.pop("abstained")
        prediction["decision"] = direction if direction is not None else "abstain"
        prediction["evidence_basis"] = {
            name: name in prediction["evidence_basis"]
            for name in ("measurements", "variable_names", "diagnostic", "background_knowledge")
        }
    elif payload["format"] == CueDecisionV2.model_json_schema():
        prediction.pop("predicted_direction")
        prediction.pop("abstained")
        prediction["decision"] = direction if direction is not None else "abstain"
    body = {
        "model": payload["model"],
        "done": True,
        "done_reason": "stop",
        "message": {
            "content": json.dumps(prediction),
            "thinking": "SCRIPTED FIXTURE" if payload["think"] else "",
        },
        "eval_count": 0,
        "prompt_eval_count": 0,
    }
    return {"http_status": 200, "body": json.dumps(body)}


def run(plan, output, *, base_url=None, scripted=False, gate=None, resume=False):
    """One attempt per request, raw saved before parsing. Failures are never retried silently."""
    plan, output = Path(plan), Path(output)
    manifest, requests = validate_plan(plan)
    if not scripted and not base_url:
        raise ValueError("Live execution requires explicit --base-url")
    if not scripted and manifest["phase"] == "full":
        if gate is None:
            raise ValueError("Live full run requires --preflight-run")
        gate = Path(gate)
        prior = read(gate / "run.json")
        if (
            prior["mode"] != "live"
            or prior["plan"]["phase"] != "preflight"
            or not read(gate / "summary.json")["preflight_passed"]
        ):
            raise ValueError("A passing live synthetic preflight is required")
        if (
            prior["plan"]["source_sha256"] != manifest["source_sha256"]
            or prior["plan"]["protocol"] != manifest["protocol"]
            or prior["base_url"] != base_url
        ):
            raise ValueError("Preflight used another source, protocol or endpoint")
        # Recount every raw preflight reply rather than trusting a saved PASS flag.
        gate_requests = read(gate / "requests.json")
        if (
            canonical_digest(gate_requests) != prior["plan"]["requests_digest"]
            or len(gate_requests) != 20
        ):
            raise ValueError("Preflight request binding mismatch")
        if cfg_is_v3(manifest["protocol"]):
            expected = []
            rng = random.Random(manifest["protocol"]["order_seed"])
            for case in synthetic_cases():
                cells = [
                    (arm, think)
                    for arm in manifest["protocol"]["conditions"]
                    for think in manifest["protocol"]["thinking_settings"]
                ]
                rng.shuffle(cells)
                for arm, think in cells:
                    payload = request_payload(case, arm, think, manifest["protocol"])
                    expected.append(
                        {
                            "trial_id": canonical_digest(
                                {"case_id": case["case_id"], "payload": payload}
                            ),
                            "payload": payload,
                        }
                    )
            if gate_requests != expected:
                raise ValueError("Preflight request order differs from frozen protocol")
        for req in gate_requests:
            record = read(gate / "records" / (req["trial_id"].split(":")[-1] + ".json"))
            raw = read(gate / "raw" / (req["trial_id"].split(":")[-1] + ".json"))
            if record["failure"] or record["raw_digest"] != canonical_digest(raw):
                raise ValueError("Preflight failure or raw binding mismatch")
            _, gate_check = decode(raw, req["payload"], manifest["protocol"]["model"])
            if not gate_check["passed"]:
                raise ValueError("Preflight citation inconsistency")
    if not resume:
        output.mkdir(parents=True, exist_ok=False)
        (output / "raw").mkdir()
        (output / "records").mkdir()
    elif not output.is_dir():
        raise ValueError("Resume requires an existing attempt directory")
    cfg = manifest["protocol"]
    run_info = {
        "mode": "scripted" if scripted else "live",
        "base_url": base_url,
        "plan": manifest,
        "gate_run_digest": canonical_digest(read(gate / "run.json")) if gate else None,
    }
    if resume:
        if read(output / "run.json") != run_info or read(output / "requests.json") != requests:
            raise ValueError("Resume source/protocol/request binding mismatch")
    else:
        write(output / "run.json", run_info)
        write(output / "requests.json", requests)
    failures = 0
    rejections = 0
    fail_fast = manifest["phase"] in ("preflight", "diagnostic") and cfg.get(
        "preflight_fail_fast", False
    )
    with httpx.Client(timeout=cfg["timeout_seconds"], trust_env=False) as client:

        def snapshot(name):
            tags = client.get(base_url.rstrip("/") + "/api/tags")
            tags.raise_for_status()
            tags = tags.json()
            if not any(
                m["name"] == cfg["model"] and m["digest"] == cfg["model_digest"]
                for m in tags["models"]
            ):
                raise ValueError("Pinned model digest unavailable")
            details = {"tags": tags}
            for endpoint in ("version", "ps"):
                response = client.get(base_url.rstrip("/") + "/api/" + endpoint)
                response.raise_for_status()
                details[endpoint] = response.json()
            write(output / name, details)

        if not scripted:
            if resume:
                snapshot("model-resume.json")
            else:
                snapshot("model-before.json")
        for req in requests:
            identity = req["trial_id"].split(":")[-1]
            record = {
                "trial_id": req["trial_id"],
                "request_digest": canonical_digest(req["payload"]),
                "prediction": None,
                "checker": None,
                "failure": None,
                "raw_digest": None,
            }
            raw_path = output / "raw" / (identity + ".json")
            record_path = output / "records" / (identity + ".json")
            if resume and record_path.exists():
                saved = read(record_path)
                if (
                    saved["trial_id"] != req["trial_id"]
                    or saved["request_digest"] != record["request_digest"]
                ):
                    raise ValueError("Resume record/request mismatch")
                if raw_path.exists():
                    raw = read(raw_path)
                    if saved["raw_digest"] != canonical_digest(raw):
                        raise ValueError("Resume raw digest mismatch")
                    try:
                        prediction, checker = decode(raw, req["payload"], cfg["model"])
                    except (ValueError, KeyError, TypeError):
                        if not saved["failure"]:
                            raise ValueError("Invalid saved success") from None
                    else:
                        if (
                            prediction != saved["prediction"]
                            or checker != saved["checker"]
                            or saved["failure"]
                        ):
                            raise ValueError("Resume prediction/raw mismatch")
                elif not saved["failure"] or saved["raw_digest"] is not None:
                    raise ValueError("Missing durable raw response")
                failures += bool(saved["failure"])
                rejections += bool(saved["checker"] and not saved["checker"]["passed"])
                if fail_fast and (failures or rejections):
                    break
                continue
            started = time.perf_counter()
            try:
                if resume and raw_path.exists():
                    raw = read(raw_path)
                elif scripted:
                    raw = fake_response(req["payload"])
                else:
                    response = client.post(base_url.rstrip("/") + "/api/chat", json=req["payload"])
                    raw = {"http_status": response.status_code, "body": response.text}
                if not raw_path.exists():
                    raw["client_latency_seconds"] = time.perf_counter() - started
                    write(raw_path, raw)
                record["raw_digest"] = canonical_digest(raw)
                record["prediction"], record["checker"] = decode(raw, req["payload"], cfg["model"])
                rejections += not record["checker"]["passed"]
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                record["failure"] = type(exc).__name__ + ": " + str(exc)
                failures += 1
            record["latency_seconds"] = time.perf_counter() - started
            if record["raw_digest"] is not None:
                record["latency_seconds"] = raw.get("client_latency_seconds")
            write(record_path, record)
            print(f"completed {identity[:12]} failure={bool(record['failure'])}", flush=True)
            if fail_fast and (failures or rejections):
                break
        if not scripted:
            snapshot("model-after.json")
    completed = sum(
        (output / "records" / (r["trial_id"].split(":")[-1] + ".json")).exists() for r in requests
    )
    result = {
        "completed": completed,
        "scheduled": len(requests),
        "failures": failures,
        "preflight_passed": manifest["phase"] == "preflight"
        and completed == len(requests)
        and failures == 0
        and rejections == 0,
        **(
            {"diagnostic_passed": completed == len(requests) and failures == 0 and rejections == 0}
            if manifest["phase"] == "diagnostic"
            else {}
        ),
        "verification_rejections": rejections,
        "mode": run_info["mode"],
        "research_result": not scripted and manifest["phase"] == "full",
    }
    write(output / "summary.json", result)
    return result


def cfg_is_v3(cfg):
    return cfg["protocol_version"] == "diagnostic-investigation-v3"
