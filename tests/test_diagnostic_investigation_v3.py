"""V3 boolean evidence contract and independently frozen diagnostic gate."""

import itertools
import json

import pytest

from causalbridge.evaluation import diagnostic_runtime as runtime
from causalbridge.evaluation.diagnostic_protocol import (
    prepare,
    read,
    request_payload,
    synthetic_cases,
    validate_plan,
)

BASES = ("measurements", "variable_names", "diagnostic", "background_knowledge")


def payload(arm="no_diagnostic", think=False):
    return request_payload(
        synthetic_cases()[0], arm, think, read("configs/diagnostic-investigation-v3.json")
    )


def response(request, fields):
    raw = runtime.fake_response(request)
    body = json.loads(raw["body"])
    body["message"]["content"] = fields if isinstance(fields, str) else json.dumps(fields)
    raw["body"] = json.dumps(body)
    return raw


@pytest.mark.parametrize("decision", ["A_to_B", "B_to_A", "abstain"])
@pytest.mark.parametrize("flags", list(itertools.product((False, True), repeat=4)))
def test_all_decisions_and_boolean_combinations(decision, flags):
    request = payload()
    basis = dict(zip(BASES, flags, strict=True))
    fields = dict(
        decision=decision,
        diagnostic_direction_cited=None,
        evidence_basis=basis,
        explanation="Fixture.",
    )
    prediction, checker = runtime.decode(response(request, fields), request, "qwen3:8b")
    assert prediction["predicted_direction"] == (None if decision == "abstain" else decision)
    assert prediction["abstained"] == (decision == "abstain")
    assert prediction["evidence_basis"] == [name for name in BASES if basis[name]]
    assert checker["passed"] == (not basis["diagnostic"])


@pytest.mark.parametrize(
    "mutation",
    ["missing", "extra", "nonboolean", "null", "array", "missing_decision", "extra_outer"],
)
def test_rejects_invalid_contract(mutation):
    request = payload()
    fields = dict(
        decision="abstain",
        diagnostic_direction_cited=None,
        evidence_basis=dict.fromkeys(BASES, False),
        explanation="Fixture.",
    )
    if mutation == "missing":
        fields["evidence_basis"].pop("measurements")
    elif mutation == "extra":
        fields["evidence_basis"]["other"] = False
    elif mutation == "nonboolean":
        fields["evidence_basis"]["measurements"] = 0
    elif mutation == "null":
        fields["evidence_basis"]["measurements"] = None
    elif mutation == "array":
        fields["evidence_basis"] = []
    elif mutation == "missing_decision":
        fields.pop("decision")
    else:
        fields["unknown"] = 1
    with pytest.raises(ValueError):
        runtime.decode(response(request, fields), request, "qwen3:8b")


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        '{"decision":"abstain"',
        '{"decision":"A_to_B","decision":"abstain"}',
        '{"decision":"abstain","diagnostic_direction_cited":null,"evidence_basis":'
        '{"measurements":false,"measurements":true,"variable_names":false,'
        '"diagnostic":false,"background_knowledge":false},"explanation":"Fixture."}',
    ],
)
def test_invalid_json_and_duplicate_keys(content):
    request = payload()
    with pytest.raises(ValueError):
        runtime.decode(response(request, content), request, "qwen3:8b")


def test_four_cell_probe_and_scientific_plan_parity(tmp_path):
    probe = tmp_path / "probe"
    pre = tmp_path / "pre"
    full = tmp_path / "full"
    v2pre = tmp_path / "v2pre"
    v2full = tmp_path / "v2full"
    prepare(probe, diagnostic=True, protocol="v3")
    prepare(pre, preflight=True, protocol="v3")
    prepare(full, protocol="v3")
    prepare(v2pre, preflight=True, protocol="v2")
    prepare(v2full, protocol="v2")
    assert validate_plan(probe)[0]["scheduled"] == 4
    assert validate_plan(pre)[0]["scheduled"] == 20
    assert validate_plan(full)[0]["scheduled"] == 170
    for left, right in ((pre, v2pre), (full, v2full)):
        a = read(left / "evaluator.json")
        b = read(right / "evaluator.json")
        assert [(x["case_id"], x["arm"], x["think"]) for x in a] == [
            (x["case_id"], x["arm"], x["think"]) for x in b
        ]
        assert [x["gold"] for x in a] == [x["gold"] for x in b]


def test_probe_scripted_replay_and_resume(tmp_path):
    plan = tmp_path / "plan"
    output = tmp_path / "run"
    prepare(plan, diagnostic=True, protocol="v3")
    result = runtime.run(plan, output, scripted=True)
    assert result["diagnostic_passed"] and result["completed"] == 4
    raw = {p.name: p.read_bytes() for p in (output / "raw").glob("*.json")}
    assert runtime.run(plan, output, scripted=True, resume=True) == result
    assert raw == {p.name: p.read_bytes() for p in (output / "raw").glob("*.json")}


def test_probe_failure_stops_and_resume_never_retries_saved_failure(tmp_path, monkeypatch):
    import httpx

    plan = tmp_path / "plan"
    output = tmp_path / "run"
    prepare(plan, diagnostic=True, protocol="v3")
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
        calls.append(request)
        fields = {
            "decision": "abstain",
            "diagnostic_direction_cited": None,
            "evidence_basis": {name: False for name in BASES},
            "explanation": "Fixture.",
        }
        fields["evidence_basis"].pop("measurements")
        return httpx.Response(200, text=response(json.loads(request.content), fields)["body"])

    monkeypatch.setattr(
        runtime.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    result = runtime.run(plan, output, base_url="http://fixture")
    assert result["completed"] == 1 and result["failures"] == 1
    assert not result["diagnostic_passed"] and len(calls) == 1
    saved = {p.name: p.read_bytes() for p in (output / "raw").glob("*.json")}
    assert runtime.run(plan, output, base_url="http://fixture", resume=True) == result
    assert len(calls) == 1
    assert saved == {p.name: p.read_bytes() for p in (output / "raw").glob("*.json")}


def test_v3_plan_rejects_reordering_even_with_recomputed_digests(tmp_path):
    from causalbridge.discovery.schemas import canonical_digest
    from causalbridge.evaluation.diagnostic_protocol import write

    plan = tmp_path / "plan"
    prepare(plan, preflight=True, protocol="v3")
    requests = read(plan / "requests.json")
    evaluator = read(plan / "evaluator.json")
    manifest = read(plan / "manifest.json")
    requests[0], requests[1] = requests[1], requests[0]
    evaluator[0], evaluator[1] = evaluator[1], evaluator[0]
    manifest["requests_digest"] = canonical_digest(requests)
    manifest["evaluator_digest"] = canonical_digest(evaluator)
    write(plan / "requests.json", requests)
    write(plan / "evaluator.json", evaluator)
    write(plan / "manifest.json", manifest)
    with pytest.raises(ValueError, match="order"):
        validate_plan(plan)
