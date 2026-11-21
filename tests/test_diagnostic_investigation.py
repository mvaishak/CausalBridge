"""Regression and end-to-end checks without a model, GPU or external network."""

import json

import httpx
import pytest

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation import diagnostic_runtime as runtime
from causalbridge.evaluation.diagnostic_analysis import (
    analyze,
    diagnose,
    fraction,
    outcome,
    paired_comparison,
    summarize,
)
from causalbridge.evaluation.diagnostic_protocol import (
    CuePrediction,
    prepare,
    read,
    validate_plan,
    write,
)


@pytest.fixture
def plan(tmp_path):
    path = tmp_path / "plan"
    prepare(path)
    return path


def test_factorial_plan_and_no_label_metadata_in_requests(plan):
    manifest, requests = validate_plan(plan)
    assert manifest["scheduled"] == 170 and manifest["case_count"] == 17
    assert manifest["eligibility"]["confirmatory"] is False
    metadata = read(plan / "evaluator.json")
    assert len({r["trial_id"] for r in requests}) == 170
    for req, meta in zip(requests, metadata, strict=True):
        user = json.loads(req["payload"]["messages"][1]["content"])
        assert set(user) == {"question", "evidence", "external_diagnostic"}
        assert "gold" not in user and "arm" not in user
        assert "method_result" not in user["evidence"]
        assert "case_id" not in user
        assert meta["think"] is req["payload"]["think"]
    # Within each case, only the declared direction, warning and think fields vary.
    by_case = {}
    for req, meta in zip(requests, metadata, strict=True):
        payload = json.loads(json.dumps(req["payload"]))
        user = json.loads(payload["messages"][1]["content"])
        user.pop("external_diagnostic")
        payload["messages"][1]["content"] = json.dumps(user, sort_keys=True)
        payload.pop("think")
        if meta["case_id"] in by_case:
            assert payload == by_case[meta["case_id"]]
        by_case[meta["case_id"]] = payload


@pytest.mark.parametrize("mutation", ["budget", "gold_leak", "group", "duplicate", "direction"])
def test_plan_rejects_rehashed_mutations(plan, mutation):
    requests, evaluator = read(plan / "requests.json"), read(plan / "evaluator.json")
    if mutation == "budget":
        requests[0]["payload"]["options"]["num_predict"] = 8000
    elif mutation == "gold_leak":
        requests[0]["payload"]["messages"][0]["content"] += " Gold direction is A_to_B."
    elif mutation == "group":
        evaluator[0]["source_group"] = "independent"
    elif mutation == "duplicate":
        requests[1] = requests[0]
        evaluator[1] = evaluator[0]
    else:
        evaluator[0]["gold"] = "B_to_A" if evaluator[0]["gold"] == "A_to_B" else "A_to_B"
    write(plan / "requests.json", requests)
    write(plan / "evaluator.json", evaluator)
    manifest = read(plan / "manifest.json")
    manifest["requests_digest"] = canonical_digest(requests)
    manifest["evaluator_digest"] = canonical_digest(evaluator)
    write(plan / "manifest.json", manifest)
    with pytest.raises(ValueError):
        validate_plan(plan)


def test_required_attribution_and_abstention_consistency():
    valid = {
        "predicted_direction": None,
        "abstained": True,
        "diagnostic_direction_cited": None,
        "evidence_basis": [],
        "explanation": "uncertain",
    }
    CuePrediction.model_validate(valid)
    for key, value in [("abstained", False), ("evidence_basis", ["diagnostic", "diagnostic"])]:
        with pytest.raises(ValueError):
            CuePrediction.model_validate({**valid, key: value})
    valid.pop("diagnostic_direction_cited")
    with pytest.raises(ValueError):
        CuePrediction.model_validate(valid)


def modified_response(payload, **updates):
    raw = runtime.fake_response(payload)
    body = json.loads(raw["body"])
    prediction = json.loads(body["message"]["content"])
    prediction.update(updates)
    body["message"]["content"] = json.dumps(prediction)
    raw["body"] = json.dumps(body)
    return raw


def test_checker_allows_accurately_attributed_disagreement(plan):
    _, requests = validate_plan(plan)
    req = next(
        r
        for r in requests
        if json.loads(r["payload"]["messages"][1]["content"])["external_diagnostic"]
    )
    raw = runtime.fake_response(req["payload"])
    body = json.loads(raw["body"])
    p = json.loads(body["message"]["content"])
    other = "B_to_A" if p["predicted_direction"] == "A_to_B" else "A_to_B"
    raw = modified_response(req["payload"], predicted_direction=other)
    prediction, check = runtime.decode(raw, req["payload"], "qwen3:8b")
    assert prediction["predicted_direction"] == other and check["release"]


@pytest.mark.parametrize("citation", [None, "A_to_B", "B_to_A"])
def test_unavailable_diagnostic_is_not_an_abstention_or_causal_check(plan, citation):
    _, requests = validate_plan(plan)
    req = next(
        r
        for r in requests
        if json.loads(r["payload"]["messages"][1]["content"])["external_diagnostic"] is None
    )
    raw = modified_response(
        req["payload"], diagnostic_direction_cited=citation, evidence_basis=["diagnostic"]
    )
    p, check = runtime.decode(raw, req["payload"], "qwen3:8b")
    assert p["abstained"] and not check["passed"]


@pytest.mark.parametrize("fault", ["truncated", "malformed", "model", "thinking", "http"])
def test_execution_failures_are_rejected_before_scoring(plan, fault):
    _, requests = validate_plan(plan)
    req = next(r for r in requests if r["payload"]["think"])
    raw = runtime.fake_response(req["payload"])
    body = json.loads(raw["body"])
    if fault == "truncated":
        body["done_reason"] = "length"
    elif fault == "malformed":
        body["message"]["content"] = "not json"
    elif fault == "model":
        body["model"] = "another:model"
    elif fault == "thinking":
        body["message"]["thinking"] = ""
    else:
        raw["http_status"] = 500
    raw["body"] = json.dumps(body)
    with pytest.raises(ValueError):
        runtime.decode(raw, req["payload"], "qwen3:8b")
    assert outcome(None, fault, "A_to_B") == "execution_failure"


def test_metrics_partition_and_explicit_denominators():
    rows = [
        {"outcome": k, "weight": 1, "rejected": k == "correct", "released": k == "wrong"}
        for k in ("correct", "wrong", "abstention", "execution_failure")
    ]
    metrics = summarize(rows)
    assert sum(metrics["counts"].values()) == 4
    assert metrics["directional_accuracy_before_verification"] == fraction(1, 2)
    assert metrics["verification_rejection"] == fraction(1, 4)
    assert metrics["rejected_underlying"] == {"correct": 1}
    assert metrics["after_verification"]["correct_yield"] == fraction(0, 4)
    assert fraction(0, 0)["rate"] is None


def test_saved_diagnosis_recounts_both_archives(tmp_path):
    result = diagnose(tmp_path / "diagnosis")
    assert result["observations"] == 408 and result["transitions"] == 102
    original = next(
        r
        for r in result["propagation"]
        if r["experiment"].startswith("original") and r["style"] == "S0"
    )
    assert original["wrong_copy"] == fraction(8, 8)
    assert original["harmful_switch"] == fraction(4, 4)
    on = [r for r in result["propagation"] if r["experiment"].startswith("matched") and r["think"]]
    assert len(on) == 2 and all(r["resistance"] == fraction(0, 8) for r in on)


def test_full_scripted_end_to_end_and_replay_tampering(plan, tmp_path):
    run_dir = tmp_path / "run"
    runtime.run(plan, run_dir, scripted=True)
    result = analyze(plan, run_dir, tmp_path / "analysis")
    assert result["scheduled"] == 170 and not result["research_result"]
    assert len(result["comparisons"]) == 8
    for cell in result["cells"]:
        expected = (
            "abstention"
            if cell["arm"] == "no_diagnostic"
            else ("wrong" if cell["arm"].startswith("wrong") else "correct")
        )
        assert cell["counts"][expected] == 17
    path = next((run_dir / "raw").glob("*.json"))
    raw = read(path)
    raw["body"] += " "
    write(path, raw)
    with pytest.raises(ValueError, match="Raw digest"):
        analyze(plan, run_dir, tmp_path / "tampered-analysis")


def test_existing_outputs_are_not_overwritten(plan, tmp_path):
    with pytest.raises(FileExistsError):
        prepare(plan)
    runtime.run(plan, tmp_path / "run", scripted=True)
    with pytest.raises(FileExistsError):
        runtime.run(plan, tmp_path / "run", scripted=True)


def test_live_requires_explicit_endpoint_and_real_preflight(plan, tmp_path):
    with pytest.raises(ValueError, match="base-url"):
        runtime.run(plan, tmp_path / "no-endpoint")
    with pytest.raises(ValueError, match="preflight"):
        runtime.run(plan, tmp_path / "no-gate", base_url="http://127.0.0.1:1")


def test_http_preflight_and_full_protocol_without_network(plan, tmp_path, monkeypatch):
    """MockTransport exercises real HTTP request/response and model checks, not real inference."""
    pre = tmp_path / "pre-plan"
    prepare(pre, preflight=True)
    original_client = httpx.Client
    observed = []
    cfg = read(plan / "manifest.json")["protocol"]

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": cfg["model"], "digest": cfg["model_digest"]}]}
            )
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "mock-fixture"})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        payload = json.loads(request.content)
        observed.append(payload)
        return httpx.Response(200, text=runtime.fake_response(payload)["body"])

    monkeypatch.setattr(
        runtime.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    gate = tmp_path / "pre-run"
    assert runtime.run(pre, gate, base_url="http://fixture")["preflight_passed"]
    result = runtime.run(plan, tmp_path / "full-run", base_url="http://fixture", gate=gate)
    assert result["completed"] == 170 and len(observed) == 190
    # These mock-only artifacts remain inside pytest's temp directory.
    report = analyze(plan, tmp_path / "full-run", tmp_path / "analysis")
    assert report["scheduled"] == 170


def test_cluster_interval_retains_all_cases_and_scheduled_failures():
    rows = []
    for cid, group in [("a", "shared"), ("b", "shared"), ("c", "other")]:
        for arm, kind in [("left", "correct"), ("right", "execution_failure")]:
            rows.append(
                {
                    "case_id": cid,
                    "source_group": group,
                    "arm": arm,
                    "think": True,
                    "outcome": kind,
                    "prediction": None,
                }
            )
    result = paired_comparison(
        rows, "left", "right", True, {"bootstrap_seed": 261, "bootstrap_draws": 100}
    )
    assert result["n_pairs"] == 3 and result["source_groups"] == 2
    assert result["yield_difference_right_minus_left"]["correct"] == -1
    assert result["yield_difference_right_minus_left"]["execution_failure"] == 1


def test_failures_and_checker_rejections_survive_raw_replay(plan, tmp_path, monkeypatch):
    original = runtime.fake_response
    calls = 0

    def faulty(payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("fixture transport failure")
        raw = original(payload)
        body = json.loads(raw["body"])
        if calls == 2:
            body["done_reason"] = "length"
        elif calls == 3:
            p = json.loads(body["message"]["content"])
            user = json.loads(payload["messages"][1]["content"])
            cue = user["external_diagnostic"]
            p["diagnostic_direction_cited"] = (
                "B_to_A" if cue and cue["direction"] == "A_to_B" else "A_to_B"
            )
            body["message"]["content"] = json.dumps(p)
        raw["body"] = json.dumps(body)
        return raw

    monkeypatch.setattr(runtime, "fake_response", faulty)
    result = runtime.run(plan, tmp_path / "run", scripted=True)
    assert result["failures"] == 2 and result["verification_rejections"] == 1
    report = analyze(plan, tmp_path / "run", tmp_path / "analysis")
    assert sum(c["counts"]["execution_failure"] for c in report["cells"]) == 2
    assert sum(c["verification_rejection"]["numerator"] for c in report["cells"]) == 1
    assert sum(sum(c["counts"].values()) for c in report["cells"]) == 170
    before = {p.name: p.read_bytes() for p in (tmp_path / "run" / "records").glob("*.json")}
    runtime.run(plan, tmp_path / "run", scripted=True, resume=True)
    assert calls == 170  # Failed observations are retained; they are not retried.
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "run" / "records").glob("*.json")}


def test_resume_recovers_saved_raw_without_another_call(plan, tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    runtime.run(plan, run_dir, scripted=True)
    record = next((run_dir / "records").glob("*.json"))
    record.unlink()  # Simulate interruption after durable raw save, before derived record.

    def no_calls(payload):
        raise AssertionError("Saved raw must be replayed without inference")

    monkeypatch.setattr(runtime, "fake_response", no_calls)
    result = runtime.run(plan, run_dir, scripted=True, resume=True)
    assert result["completed"] == 170 and result["failures"] == 0
    analyze(plan, run_dir, tmp_path / "analysis")


def test_scripted_preflight_cannot_authorize_live_calls(plan, tmp_path):
    pre = tmp_path / "pre-plan"
    prepare(pre, preflight=True)
    gate = tmp_path / "pre-run"
    runtime.run(pre, gate, scripted=True)
    with pytest.raises(ValueError, match="passing live"):
        runtime.run(plan, tmp_path / "full", base_url="http://fixture", gate=gate)
