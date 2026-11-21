"""Single-decision contract, frozen design, and fail-fast preflight regressions."""

import json

import httpx
import pytest

from causalbridge.evaluation import diagnostic_runtime as runtime
from causalbridge.evaluation.diagnostic_analysis import analyze
from causalbridge.evaluation.diagnostic_protocol import (
    CueDecisionV2,
    CuePrediction,
    prepare,
    read,
    request_payload,
    synthetic_cases,
    validate_plan,
)


def payload(think=False):
    return request_payload(
        synthetic_cases()[0],
        "no_diagnostic",
        think,
        read("configs/diagnostic-investigation-v2.json"),
    )


def response(request, fields):
    raw = runtime.fake_response(request)
    body = json.loads(raw["body"])
    body["message"]["content"] = fields if isinstance(fields, str) else json.dumps(fields)
    raw["body"] = json.dumps(body)
    return raw


def fields(decision="abstain"):
    return {
        "decision": decision,
        "diagnostic_direction_cited": None,
        "evidence_basis": [],
        "explanation": "Software contract fixture.",
    }


@pytest.mark.parametrize("think", [False, True])
@pytest.mark.parametrize("decision", ["A_to_B", "B_to_A", "abstain"])
def test_all_decisions_normalize_consistently(think, decision):
    request = payload(think)
    prediction, checker = runtime.decode(response(request, fields(decision)), request, "qwen3:8b")
    assert prediction["predicted_direction"] == (None if decision == "abstain" else decision)
    assert prediction["abstained"] == (decision == "abstain")
    assert checker["release"] == (decision != "abstain")
    schema = request["format"]
    assert schema["properties"]["decision"]["enum"] == ["A_to_B", "B_to_A", "abstain"]
    assert "abstained" not in schema["properties"]
    assert "predicted_direction" not in schema["properties"]
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize(
    "mutation", ["missing", "unknown", "null", "legacy", "both", "duplicates", "empty"]
)
def test_v2_rejects_invalid_or_ambiguous_contracts(mutation):
    f = fields()
    if mutation == "missing":
        f.pop("decision")
    elif mutation == "unknown":
        f["decision"] = "unsure"
    elif mutation == "null":
        f["decision"] = None
    elif mutation == "legacy":
        f.pop("decision")
        f.update(predicted_direction="B_to_A", abstained=True)
    elif mutation == "both":
        f.update(predicted_direction="B_to_A", abstained=True)
    elif mutation == "duplicates":
        f["evidence_basis"] = ["measurements", "measurements"]
    else:
        f["explanation"] = ""
    request = payload()
    with pytest.raises(ValueError):
        runtime.decode(response(request, f), request, "qwen3:8b")


@pytest.mark.parametrize(
    "content", ["not JSON", '{"decision":"abstain"', '{"decision":"A_to_B","decision":"abstain"}']
)
def test_malformed_and_duplicate_key_outputs_are_failures(content):
    request = payload()
    with pytest.raises(ValueError):
        runtime.decode(response(request, content), request, "qwen3:8b")


def test_preserved_v1_failure_is_not_repaired():
    archived = read("artifacts/diagnostic-preflight-failure-audit/validation.json")
    for r in archived["live_responses"]:
        with pytest.raises(ValueError, match="abstained must match null direction"):
            CuePrediction.model_validate(r["prediction"])
        with pytest.raises(ValueError):
            CueDecisionV2.model_validate(r["prediction"])


def test_v2_retains_design_and_budgets():
    v1 = read("configs/diagnostic-investigation-v1.json")
    v2 = read("configs/diagnostic-investigation-v2.json")
    for key, value in v1.items():
        if key != "protocol_version":
            assert v2[key] == value
    case = synthetic_cases()[0]
    for arm in v1["conditions"]:
        for think in v1["thinking_settings"]:
            a = request_payload(case, arm, think, v1)
            b = request_payload(case, arm, think, v2)
            assert a["messages"][1] == b["messages"][1]
            assert a["options"] == b["options"]
            assert a["think"] == b["think"]


@pytest.mark.parametrize("fault", ["contract", "citation", "transport"])
def test_live_preflight_stops_before_next_call_and_never_retries(tmp_path, monkeypatch, fault):
    plan = tmp_path / "plan"
    prepare(plan, preflight=True, protocol="v2")
    cfg = read(plan / "manifest.json")["protocol"]
    original = httpx.Client
    calls = []

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": cfg["model"], "digest": cfg["model_digest"]}]}
            )
        if request.url.path in ("/api/version", "/api/ps"):
            return httpx.Response(200, json={"models": [], "version": "mock"})
        p = json.loads(request.content)
        calls.append(p)
        if fault == "transport":
            raise httpx.ReadTimeout("fixture")
        f = fields()
        if fault == "contract":
            f["abstained"] = True
        else:
            f.update(diagnostic_direction_cited="A_to_B", evidence_basis=["diagnostic"])
        return httpx.Response(200, text=response(p, f)["body"])

    monkeypatch.setattr(
        runtime.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    output = tmp_path / "run"
    result = runtime.run(plan, output, base_url="http://fixture")
    assert result["completed"] == 1 and result["scheduled"] == 20
    assert not result["preflight_passed"] and len(calls) == 1
    assert result["verification_rejections"] == (1 if fault == "citation" else 0)
    assert result["failures"] == (0 if fault == "citation" else 1)
    before = {p.name: p.read_bytes() for p in (output / "records").glob("*.json")}
    again = runtime.run(plan, output, base_url="http://fixture", resume=True)
    assert again == result and len(calls) == 1
    assert before == {p.name: p.read_bytes() for p in (output / "records").glob("*.json")}


def test_v2_full_end_to_end_and_v1_gate_cannot_authorize_it(tmp_path):
    full = tmp_path / "full"
    prepare(full, protocol="v2")
    assert validate_plan(full)[0]["scheduled"] == 170
    run = tmp_path / "run"
    runtime.run(full, run, scripted=True)
    result = analyze(full, run, tmp_path / "analysis")
    assert result["scheduled"] == 170 and not result["research_result"]
    assert all(c["counts"]["execution_failure"] == 0 for c in result["cells"])
    pre = tmp_path / "v1-pre"
    prepare(pre, preflight=True)
    gate = tmp_path / "v1-gate"
    runtime.run(pre, gate, scripted=True)
    # A forged PASS flag cannot bypass mode/source/protocol and raw replay checks.
    from causalbridge.evaluation.diagnostic_protocol import write

    run_info = read(gate / "run.json")
    run_info["mode"] = "live"
    write(gate / "run.json", run_info)
    with pytest.raises(ValueError, match="another source, protocol"):
        runtime.run(full, tmp_path / "blocked", base_url=None or "http://fixture", gate=gate)


@pytest.mark.parametrize(
    "fault", ["truncated", "unfinished", "model", "missing_thinking", "unexpected_thinking", "http"]
)
def test_v2_execution_guards_still_reject_invalid_responses(fault):
    request = payload(think=fault != "unexpected_thinking")
    raw = runtime.fake_response(request)
    body = json.loads(raw["body"])
    if fault == "truncated":
        body["done_reason"] = "length"
    elif fault == "unfinished":
        body["done"] = False
    elif fault == "model":
        body["model"] = "other:model"
    elif fault == "missing_thinking":
        body["message"]["thinking"] = ""
    elif fault == "unexpected_thinking":
        body["message"]["thinking"] = "unexpected"
    else:
        raw["http_status"] = 500
    raw["body"] = json.dumps(body)
    with pytest.raises(ValueError):
        runtime.decode(raw, request, "qwen3:8b")


def test_v2_successful_mock_http_preflight_full_and_replay(tmp_path, monkeypatch):
    pre = tmp_path / "pre"
    full = tmp_path / "full"
    prepare(pre, preflight=True, protocol="v2")
    prepare(full, protocol="v2")
    cfg = read(pre / "manifest.json")["protocol"]
    original = httpx.Client
    calls = []

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": cfg["model"], "digest": cfg["model_digest"]}]}
            )
        if request.url.path in ("/api/version", "/api/ps"):
            return httpx.Response(200, json={"models": [], "version": "mock"})
        p = json.loads(request.content)
        calls.append(p)
        return httpx.Response(200, text=runtime.fake_response(p)["body"])

    monkeypatch.setattr(
        runtime.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    gate = tmp_path / "gate"
    output = tmp_path / "output"
    assert runtime.run(pre, gate, base_url="http://fixture")["preflight_passed"]
    result = runtime.run(full, output, base_url="http://fixture", gate=gate)
    assert result["completed"] == 170 and len(calls) == 190
    assert set(p["think"] for p in calls) == {False, True}
    report = analyze(full, output, tmp_path / "analysis")
    assert report["scheduled"] == 170 and all(
        c["counts"]["execution_failure"] == 0 for c in report["cells"]
    )
