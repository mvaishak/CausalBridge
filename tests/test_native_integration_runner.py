"""Real ANM and native predictor/checker integration; scripted model transport."""

import json
import random

import pytest

from causalbridge.discovery.anm_requests import ANMConfig
from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.integration import (
    IntegratedRunner,
    NativePackage,
    build_native_packages,
)
from causalbridge.llm.client import Generation


def selected_pair(*, constant=False):
    rng = random.Random(73)
    rows = []
    for _ in range(128):
        x = rng.uniform(-2, 2)
        rows.append((1.0, 2.0) if constant else (x, x * x + rng.gauss(0, 0.2)))
    return select_pair(
        RuntimePair(
            case_id="D0001",
            variables=({"name": "Measurement one"}, {"name": "Measurement two"}),
            rows=rows,
        ),
        SelectionSpec(method_limit=128, display_limit=32),
    )


def configuration(threshold=0.001):
    return ANMConfig(
        threshold=threshold,
        minimum_rows=32,
        maximum_rows=128,
        sampling_seed=262,
        configuration_version="integration-fixture-only",
        threshold_selection_version="not-calibrated-smoke-test",
    )


@pytest.fixture
def packages(tmp_path):
    pytest.importorskip("numpy")
    return build_native_packages(selected_pair(), tmp_path / "anm", configuration())


class NativeModel:
    def __init__(self, behavior="honest"):
        self.calls = 0
        self.behavior = behavior

    def generate(self, messages, schema):
        self.calls += 1
        assert schema["title"] == "DirectionPrediction"
        payload = json.loads(messages[1]["content"])
        evidence = payload["evidence"]
        if self.behavior == "timeout":
            raise TimeoutError("fixture outage")
        if self.behavior == "interrupt":
            raise KeyboardInterrupt()
        if self.behavior == "malformed":
            return Generation(text="not JSON", model="native-fixture")
        abstained = self.behavior == "abstain"
        direction = None if abstained else "A_to_B"
        claims = []
        method = evidence["method_result"]
        if method and method["status"] == "ok" and method["threshold"] is not None:
            cited = method["predicted_direction"]
            if self.behavior == "false_method":
                cited = "B_to_A" if cited != "B_to_A" else "A_to_B"
            claims.append(
                dict(type="method_direction", evidence_ref="method_result", direction=cited)
            )
            if self.behavior == "disagree":
                direction = "B_to_A" if method["predicted_direction"] == "A_to_B" else "A_to_B"
        if self.behavior == "unavailable_row":
            claims.append(
                dict(
                    type="display_row",
                    evidence_ref="display_rows",
                    row_index=9999,
                    values=[1.0, 2.0],
                )
            )
        reply = dict(
            case_id=payload["case_id"],
            package_digest=payload["package_digest"],
            predicted_direction=direction,
            abstained=abstained,
            reason_code="fixture_abstention" if abstained else None,
            claims=claims,
        )
        if self.behavior == "misbound":
            reply["case_id"] = "wrong-case"
        return Generation(
            text=json.dumps(reply), model="native-fixture", input_tokens=20, output_tokens=10
        )


def runner(root):
    return IntegratedRunner(
        root,
        model_identity="immutable-native-fixture-v1",
        identity_verified=True,
        model_mode="scripted_fixture",
    )


def test_actual_components_one_case_eight_calls_native_cache_and_s2(
    packages, tmp_path, monkeypatch
):
    root = tmp_path / "run"
    model = NativeModel()
    out = runner(root).run(packages, model)
    assert model.calls == out["new_model_calls"] == 8
    release = runner(root).replay_s2(out["manifest_id"])
    assert len(release) == 4 and all(r["check"]["status"] == "pass" for r in release)
    assert all(r["released_direction"] == "A_to_B" for r in release)
    # Disallow ANM execution and model calls during resume/replay.
    import causalbridge.evaluation.integration as module

    monkeypatch.setattr(module, "execute_anm_request", lambda *a: pytest.fail("Extra ANM call"))

    class Forbidden(NativeModel):
        def generate(self, *a):
            pytest.fail("Extra model call")

    assert runner(root).run(packages, Forbidden())["new_model_calls"] == 0
    assert runner(root).replay_s2(out["manifest_id"]) == release
    for trial in out["trials"]:
        start, end = trial["start"], trial["outcome"]
        trace = end["execution"]
        assert list(trace["request_messages"]) == start["messages"]
        assert trace["output_schema"] == start["output_schema"]
        assert trace["generation"]["text"]
        assert end["context"]["package_digest"] == start["receipt"]["package_digest"]
        assert "method_request" not in start["messages"][1]["content"]
    e2, e3, e4 = (p.evidence for p in packages[1:])
    assert e2.display_rows == e3.display_rows == e4.display_rows
    assert e2.summary == e3.summary == e4.summary
    assert e2.summary.correlation is None  # No extra numeric information introduced.
    assert e4.method_result.provenance.method_version == "anm-krr-hsic-1.0"


@pytest.mark.parametrize(
    "behavior,stage", [("timeout", "generate"), ("malformed", "parse"), ("misbound", "binding")]
)
def test_native_failures_saved_and_s2_skipped(packages, tmp_path, behavior, stage):
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel(behavior))
    assert all(t["outcome"]["execution"]["failure_stage"] == stage for t in out["trials"])
    assert all(t["outcome"]["context"] is None for t in out["trials"])
    assert all(
        x["skip_reason"] == "parent_prediction_failed" for x in r.replay_s2(out["manifest_id"])
    )
    if behavior != "timeout":
        assert out["trials"][0]["outcome"]["execution"]["generation"]["text"]


@pytest.mark.parametrize(
    "behavior,expected", [("false_method", "fail"), ("disagree", "pass"), ("abstain", "pass")]
)
def test_actual_checker_mechanism(packages, tmp_path, behavior, expected):
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel(behavior))
    released = r.replay_s2(out["manifest_id"])
    assert released[3]["check"]["status"] == expected
    if behavior == "false_method":
        assert "method_direction_mismatch" in released[3]["check"]["reason_codes"]
    elif behavior == "abstain":
        assert all(x["released_direction"] is None for x in released)


def test_original_anm_receipt_loaded_and_wrong_sample_config_rejected(packages, tmp_path):
    selected = selected_pair()
    cached = build_native_packages(selected, tmp_path / "anm", configuration())
    assert cached == packages
    with pytest.raises(ValueError, match="different inputs"):
        build_native_packages(selected, tmp_path / "anm", configuration(0.1))
    raw = packages[3].model_dump(mode="json")
    raw["method_request"]["sample_digest"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError, match="request/result mismatch"):
        NativePackage.model_validate(raw)
    # The original request is stored in its own file, not reconstructed from result provenance.
    request = json.loads((tmp_path / "anm" / "request.json").read_text())
    assert request == packages[3].method_request.model_dump(mode="json")


@pytest.mark.parametrize("variant", ["constant", "unconfigured"])
def test_real_anm_error_and_unconfigured_states_preserved(tmp_path, variant):
    pytest.importorskip("numpy")
    selected = selected_pair(constant=variant == "constant")
    packages = build_native_packages(selected, tmp_path / "anm", configuration(None))
    method = packages[3].evidence.method_result
    assert method.status == ("error" if variant == "constant" else "ok")
    assert method.predicted_direction is None
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel())
    # Method uncertainty does not automatically suppress a qualified LLM preference.
    assert r.replay_s2(out["manifest_id"])[3]["check"]["status"] == "pass"


def test_native_raw_persisted_before_parser_and_recovered(packages, tmp_path, monkeypatch):
    import causalbridge.llm.predictor as module

    original = module.parse_json
    monkeypatch.setattr(module, "parse_json", lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    root = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        runner(root).run(packages[:1], NativeModel())
    monkeypatch.setattr(module, "parse_json", original)
    out = runner(root).run(packages[:1], NativeModel())
    assert out["new_model_calls"] == 1
    assert out["trials"][0]["outcome"]["recovered"] is True
    assert out["trials"][0]["outcome"]["execution"]["failure_stage"] is None


def test_export_baselines_and_failure_denominators(packages, tmp_path):
    from collections import Counter

    from causalbridge.evaluation.export import analysis_rows

    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel("timeout"))
    releases = r.replay_s2(out["manifest_id"])
    rows = analysis_rows(out, releases)
    assert Counter(x["condition"] for x in rows) == {
        "S0": 4,
        "S1": 4,
        "S2": 4,
        "SIMPLE_GATE": 4,
        "ANM_ONLY": 1,
    }
    assert all(x["outcome"] == "prediction_failure" for x in rows if x["condition"] in {"S0", "S1"})
    assert all(x["predicted_direction"] is None for x in rows if x["condition"] != "ANM_ONLY")
    forbidden = {
        "gold_direction",
        "reference_direction",
        "weight",
        "source_group",
        "original_pair_id",
    }
    assert all(not forbidden.intersection(x) for x in rows)
    with pytest.raises(ValueError, match="Missing S2"):
        analysis_rows(out, [])


def test_native_signed_zero_preserved_in_journal_and_exports(tmp_path):
    pytest.importorskip("numpy")
    s = selected_pair()
    # Preserve the mapping/indices by selecting from a fresh original pair containing signed zero.
    source = RuntimePair(
        case_id="D0002",
        variables=({"name": "One"}, {"name": "Two"}),
        rows=[(-0.0, -0.0)] + [(float(i), float(i * i)) for i in range(1, 128)],
    )
    s = select_pair(source, SelectionSpec(method_limit=128, display_limit=128))
    packages = build_native_packages(s, tmp_path / "anm", configuration())
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel())
    saved = json.loads((tmp_path / "run" / "exports" / (out["manifest_id"] + ".json")).read_text())
    import math

    row = saved["trials"][2]["start"]["package"]["evidence"]["display_rows"][0]
    assert math.copysign(1, row[0]) == -1
    assert all(x["check"]["status"] == "pass" for x in r.replay_s2(out["manifest_id"]))


def test_native_audit_clean_and_tampered_receipt(packages, tmp_path):
    from causalbridge.evaluation.audit_native import audit_native
    from causalbridge.evaluation.store import Journal

    root = tmp_path / "run"
    out = runner(root).run(packages, NativeModel())
    runner(root).replay_s2(out["manifest_id"])
    report = audit_native(root)
    assert report["passed"], report
    request_file = tmp_path / "anm" / "request.json"
    data = json.loads(request_file.read_text())
    data["sampling_seed"] += 1
    request_file.write_text(json.dumps(data))
    report = audit_native(root)
    assert not report["passed"]
    assert "original_method_request" in {f["code"] for f in report["findings"]}
    store = Journal(root)
    with store.locked():
        assert len(store.by_key("native_started")) == 8


def test_native_unknown_interruption_never_automatically_retried(packages, tmp_path):
    root = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        runner(root).run(packages[:1], NativeModel("interrupt"))
    out = runner(root).run(packages[:1], NativeModel())
    assert out["new_model_calls"] == 1
    assert out["trials"][0]["outcome"]["operational_error"] == "interrupted_unknown"


def test_native_call_config_cache_invalidation(packages, tmp_path):
    from causalbridge.llm.client import ModelConfig

    root = tmp_path / "run"
    assert runner(root).run(packages[:1], NativeModel())["new_model_calls"] == 2
    assert (
        runner(root).run(packages[:1], NativeModel(), retry_id="explicit-1")["new_model_calls"] == 2
    )
    configured = NativeModel()
    configured.config = ModelConfig(seed=77)
    changed = IntegratedRunner(
        root,
        model_identity="immutable-native-fixture-v1",
        config=configured.config,
        identity_verified=True,
    )
    assert changed.run(packages[:1], configured)["new_model_calls"] == 2
    with pytest.raises(ValueError, match="configurations differ"):
        changed.run(packages[:1], NativeModel())


def test_simple_gate_blocks_method_error_and_preserves_parent(tmp_path):
    from causalbridge.evaluation.export import analysis_rows

    pytest.importorskip("numpy")
    packages = build_native_packages(
        selected_pair(constant=True), tmp_path / "anm", configuration()
    )
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel())
    s2 = r.replay_s2(out["manifest_id"])
    rows = analysis_rows(out, s2)
    e4 = {row["condition"]: row for row in rows if row["package"] == "E4"}
    assert e4["S1"]["predicted_direction"] == "A_to_B"
    assert e4["S2"]["predicted_direction"] == "A_to_B"
    assert e4["SIMPLE_GATE"]["predicted_direction"] is None
    assert e4["ANM_ONLY"]["predicted_direction"] is None


def test_evaluator_mapping_is_private_and_matches_runtime_columns(packages, tmp_path):
    from causalbridge.evaluation.export import analysis_rows, evaluator_mapping

    mapping = evaluator_mapping(packages)
    assert len(mapping) == 1
    assert mapping[0]["original_to_runtime_column_order"] == list(
        packages[0].selected.selection.column_order
    )
    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel())
    rows = analysis_rows(out, r.replay_s2(out["manifest_id"]))
    assert all(row["ab_mapping_id"] == mapping[0]["ab_mapping_id"] for row in rows)
    for trial in out["trials"]:
        assert "original_to_runtime_column_order" not in trial["start"]["messages"][1]["content"]
        assert "column_order" not in trial["start"]["messages"][1]["content"]


def test_runner_rejects_context_changed_between_e3_and_e4_before_generation(packages, tmp_path):
    raw = packages[3].model_dump(mode="json")
    raw["selected"]["variables"][0]["name"] = "Wrong variable"
    raw["evidence"]["variable_labels"][0] = "Wrong variable"
    changed = (*packages[:3], NativePackage.model_validate(raw))
    with pytest.raises(ValueError, match="Matched package"):
        runner(tmp_path / "run").run(changed, NativeModel())
    assert not (tmp_path / "run" / "events.jsonl").exists()


def test_anm_export_stays_scorable_when_model_times_out(packages, tmp_path):
    from causalbridge.evaluation.export import analysis_rows

    r = runner(tmp_path / "run")
    out = r.run(packages, NativeModel("timeout"))
    row = next(
        x
        for x in analysis_rows(out, r.replay_s2(out["manifest_id"]))
        if x["condition"] == "ANM_ONLY"
    )
    assert row["prediction_scorable"] is True
    assert row["prediction_binding"] == "valid"
    assert row["generation_status"] == "not_applicable"
    assert row["supplied_claim_count"] is None


def test_native_audit_independently_checks_matched_context(packages, tmp_path, monkeypatch):
    from causalbridge.evaluation.audit_native import audit_native
    from causalbridge.evaluation.integration import NativePackage

    raw = packages[3].model_dump(mode="json")
    raw["selected"]["variables"][0]["name"] = "Wrong variable"
    raw["evidence"]["variable_labels"][0] = "Wrong variable"
    changed = (*packages[:3], NativePackage.model_validate(raw))
    # Bypass only scheduling's newly added group guard: reconstruct an old-format
    # coherent bundle, retaining actual predictor, journal, checker and exports.
    original = NativePackage.model_validate_json

    def old_handoff(data):
        package = original(data)
        if package.evidence.package == "E4":
            selected = packages[0].selected
            return package.model_copy(update={"selected": selected})
        return package

    monkeypatch.setattr(NativePackage, "model_validate_json", old_handoff)
    r = runner(tmp_path / "run")
    out = r.run(changed, NativeModel())
    r.replay_s2(out["manifest_id"])
    report = audit_native(tmp_path / "run")
    assert "matched_context" in {f["code"] for f in report["findings"]}
