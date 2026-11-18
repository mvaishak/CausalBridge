"""Native v2 regression: bounded prompts, truncated response durability, and scope reporting."""

import json
import runpy
import sys
from pathlib import Path

import httpx
import pytest
from test_native_integration_runner import NativeModel, configuration, selected_pair

from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows
from causalbridge.evaluation.integration import (
    COMPACT_PROTOCOL,
    NATIVE_CAUTION,
    IntegratedRunner,
    build_native_packages,
    condition,
)
from causalbridge.llm.client import GenerationFailure, ModelConfig, OllamaModel
from causalbridge.llm.predictor import direction_messages


@pytest.fixture
def native_packages(tmp_path):
    return build_native_packages(selected_pair(), tmp_path / "anm", configuration())


def runner(root, config=None, mode="live_ollama", observations="synthetic"):
    return IntegratedRunner(
        root,
        config=config,
        model_identity="pinned-fixture",
        identity_verified=True,
        protocol=COMPACT_PROTOCOL,
        observation_kind=observations,
        model_mode=mode,
    )


def truncated_response(request):
    # Syntactically valid JSON is deliberately still non-scorable on length termination.
    data = json.loads(request.content)
    user = json.loads(data["messages"][1]["content"])
    return httpx.Response(
        200,
        json={
            "model": "qwen3:8b",
            "done": True,
            "done_reason": "length",
            "prompt_eval_count": 100,
            "eval_count": data.get("options", {}).get("num_predict", 1024),
            "message": {
                "content": json.dumps(
                    dict(
                        case_id=user["case_id"],
                        package_digest=user["package_digest"],
                        predicted_direction="A_to_B",
                        abstained=False,
                    )
                )
            },
        },
    )


def test_compact_prompt_is_versioned_and_condition_isolation(native_packages):
    e = native_packages[0].evidence
    old = direction_messages(e, condition("S0"))[0]["content"]
    a = direction_messages(e, condition("S0", COMPACT_PROTOCOL))[0]["content"]
    b = direction_messages(e, condition("S1", COMPACT_PROTOCOL))[0]["content"]
    assert "at most three" not in old
    assert "at most three relevant claims" in a
    assert "Cite only evidence present in this package" in a
    assert "Use claims=[]" in a and "Abstention remains allowed" in a
    assert b.replace(NATIVE_CAUTION, "") == a
    assert condition("S0").version == "integrated-track-b-v1"


def test_truncated_http_metadata_preserved(native_packages):
    evidence = native_packages[0].evidence
    messages = direction_messages(evidence, condition("S0", COMPACT_PROTOCOL))
    with httpx.Client(transport=httpx.MockTransport(truncated_response)) as client:
        with pytest.raises(GenerationFailure) as caught:
            OllamaModel(client=client).generate(messages, {})
    generation = caught.value.generation
    assert generation.status == "truncated"
    assert generation.failure_reason == "output_token_limit"
    assert generation.model == "qwen3:8b"
    assert generation.input_tokens == 100 and generation.output_tokens == 1024
    assert generation.latency_seconds >= 0
    assert json.loads(generation.raw_response)["done_reason"] == "length"
    assert json.loads(generation.text)["predicted_direction"] == "A_to_B"


def test_truncation_durable_non_scorable_usage_audit_cache(native_packages, tmp_path):
    config = ModelConfig()
    r = runner(tmp_path / "run", config)
    with httpx.Client(transport=httpx.MockTransport(truncated_response)) as client:
        model = OllamaModel(config, client=client)
        run = r.run(native_packages, model)
        assert run["new_model_calls"] == 8
        assert run["new_usage"] == {"input_tokens": 800, "output_tokens": 8192}
        for trial in run["trials"]:
            end = trial["outcome"]
            trace = end["execution"]
            assert trace["failure_stage"] == "generate"
            assert trace["generation"]["status"] == "truncated"
            assert trace["prediction"] is None and end["context"] is None
            assert trace["prompt_version"] == "direction-0.2-compact"
        releases = r.replay_s2(run["manifest_id"])
        assert all(x["skip_reason"] == "parent_prediction_failed" for x in releases)
        assert all(x["released_direction"] is None for x in releases)
        rows = analysis_rows(run, releases)
        assert all(not x["prediction_scorable"] for x in rows if x["condition"] != "ANM_ONLY")
        assert next(x for x in rows if x["condition"] == "ANM_ONLY")["prediction_scorable"]
        assert all(x["predicted_direction"] is None for x in rows if x["condition"] != "ANM_ONLY")
        repeated = r.run(native_packages, model)
        assert repeated["new_model_calls"] == 0
        assert repeated["new_usage"] == {"input_tokens": 0, "output_tokens": 0}
        assert repeated["historical_usage"] == run["new_usage"]
    audit = audit_native(tmp_path / "run")
    assert audit["passed"], audit
    assert audit["counts"]["native_generated"] == 8


def test_no_response_is_distinct_from_truncation(native_packages, tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout("no response", request=request)

    config = ModelConfig()
    r = runner(tmp_path / "run", config)
    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        run = r.run(native_packages, OllamaModel(config, client=client))
    assert run["new_usage"] == {"input_tokens": None, "output_tokens": None}
    for trial in run["trials"]:
        trace = trial["outcome"]["execution"]
        assert trace["failure_stage"] == "generate"
        assert trace["generation"] is None and trace["prediction"] is None
        assert "ReadTimeout" in trace["error"]
    r.replay_s2(run["manifest_id"])
    assert audit_native(tmp_path / "run")["passed"]


def test_truncation_recovery_does_not_parse_or_reissue(native_packages, tmp_path, monkeypatch):
    config = ModelConfig()
    r = runner(tmp_path / "run", config)
    original = r._finish
    with httpx.Client(transport=httpx.MockTransport(truncated_response)) as client:
        model = OllamaModel(config, client=client)
        monkeypatch.setattr(
            r, "_finish", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt())
        )
        with pytest.raises(KeyboardInterrupt):
            r.run(native_packages, model)
        monkeypatch.setattr(r, "_finish", original)
        run = r.run(native_packages, model)
    assert run["new_model_calls"] == 7
    recovered = run["trials"][0]["outcome"]
    assert recovered["recovered"]
    assert recovered["execution"]["failure_stage"] == "generate"
    assert recovered["execution"]["prediction"] is None
    assert run["historical_usage"] == {"input_tokens": 100, "output_tokens": 1024}
    r.replay_s2(run["manifest_id"])
    assert audit_native(tmp_path / "run")["passed"]


def test_reporting_empty_claims_does_not_change_release(native_packages, tmp_path):
    r = runner(tmp_path / "run", mode="scripted_fixture")
    run = r.run(native_packages, NativeModel())
    releases = r.replay_s2(run["manifest_id"])
    rows = analysis_rows(run, releases)
    e1 = next(x for x in rows if x["package"] == "E1" and x["condition"] == "S2")
    assert e1["prediction_binding"] == "valid"
    assert e1["supporting_claims_status"] == "no_supporting_claims_supplied"
    assert e1["checked_claim_count"] == 0
    assert e1["released_direction"] == "A_to_B"  # Existing policy explicitly preserved.
    assert e1["causal_correctness"] is None
    e4 = next(x for x in rows if x["package"] == "E4" and x["condition"] == "S2")
    assert e4["supporting_claims_status"] == "checked"
    assert e4["checked_claim_count"] == 1


@pytest.mark.parametrize(
    "mode,observations",
    [
        ("scripted_fixture", "synthetic"),
        ("live_ollama", "synthetic"),
        ("live_ollama", "real_observational"),
        ("live", "unspecified"),
    ],
)
def test_audit_transport_and_data_metadata_separate(native_packages, tmp_path, mode, observations):
    r = runner(tmp_path / "run", mode=mode, observations=observations)
    run = r.run(native_packages, NativeModel())
    r.replay_s2(run["manifest_id"])
    report = audit_native(tmp_path / "run")
    assert report["passed"], report
    assert report["model_modes"] == [mode]
    assert report["observation_kinds"] == [observations]
    assert "scripted model transport" not in " ".join(report["limitations"])


def test_v2_entrypoint_wire_and_cache_and_8192_preflight(native_packages, tmp_path, monkeypatch):
    # Build a saved baseline using the real native runner, no dependency on runs/ artifacts.
    baseline = tmp_path / "baseline"
    r = runner(baseline / "experiment", mode="scripted_fixture")
    run = r.run(native_packages, NativeModel())
    r.replay_s2(run["manifest_id"])
    original_client = httpx.Client
    calls = []
    digest = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"

    def respond(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:8b", "digest": digest}]})
        if request.url.path == "/api/ps":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "digest": digest,
                            "context_length": 4096,
                            "size_vram": 6000000000,
                        }
                    ]
                },
            )
        data = json.loads(request.read())
        calls.append(data)
        assert data["think"] is False
        assert data["options"]["num_predict"] == 512
        assert data["options"]["num_ctx"] == 4096
        return truncated_response(request)

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original_client(
            transport=httpx.MockTransport(respond),
            **kw,
        ),
    )
    script = Path("examples/live_track_b_smoke_v2.py")
    output = tmp_path / "live"
    args = [str(script), "--baseline", str(baseline), "--output", str(output)]
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(str(script), run_name="__main__")
    assert len(calls) == 8
    report = json.loads((output / "report.json").read_text())
    assert report["audit_passed"] and report["repeated_new_model_calls"] == 0
    assert report["session"]["effective_settings"]["display_limit"] == 16
    runpy.run_path(str(script), run_name="__main__")
    assert len(calls) == 8
    fresh = tmp_path / "unsupported8192"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script),
            "--baseline",
            str(baseline),
            "--output",
            str(fresh),
            "--context-tokens",
            "8192",
        ],
    )
    with pytest.raises(ValueError, match="capacity unverified"):
        runpy.run_path(str(script), run_name="__main__")
    assert len(calls) == 8 and not (fresh / "experiment").exists()


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("usage", "usage_accounting"),
        ("truncation_status", "http_truncation_status"),
    ],
)
def test_independent_audit_detects_semantic_corruption(native_packages, tmp_path, fault, expected):
    from causalbridge.evaluation.audit import _hash

    config = ModelConfig()
    root = tmp_path / "run"
    r = runner(root, config)
    with httpx.Client(transport=httpx.MockTransport(truncated_response)) as client:
        run = r.run(native_packages, OllamaModel(config, client=client))
    r.replay_s2(run["manifest_id"])
    path = root / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    for event in events:
        data = event["data"]
        if fault == "usage" and event["kind"] == "native_invocation":
            data["new_usage"]["output_tokens"] = 0
        elif fault == "truncation_status":
            if event["kind"] == "native_generated":
                data["generation"]["status"] = "complete"
            elif event["kind"] == "native_finished":
                data["execution"]["generation"]["status"] = "complete"
    previous = None
    for event in events:
        event["previous"] = previous
        event["digest"] = _hash({k: event[k] for k in ("seq", "previous", "kind", "data")})
        previous = event["digest"]
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    # Synchronize the export too: rejection must not depend on stale journal hashes/exports.
    ends = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_finished"}
    export_path = root / "exports" / (run["manifest_id"] + ".json")
    export = json.loads(export_path.read_text())
    for trial in export["trials"]:
        trial["outcome"] = ends[trial["start"]["key"]]
    if fault == "usage":
        export["new_usage"]["output_tokens"] = 0
    export_path.write_text(json.dumps(export))
    report = audit_native(root)
    assert not report["passed"]
    codes = {f["code"] for f in report["findings"]}
    assert expected in codes
    assert "journal_integrity" not in codes and "trial_export" not in codes
