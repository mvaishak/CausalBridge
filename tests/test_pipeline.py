import json
import subprocess

import pytest

from causalbridge.llm.client import Generation
from causalbridge.pipeline import CausalBridge
from causalbridge.schemas import Proposal, RuntimeCase
from causalbridge.tools.reference import ReferenceBackend


class ScriptedModel:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.messages = []

    def generate(self, messages, schema):
        self.messages.append(messages)
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return Generation(text=output, model="test-fixture", input_tokens=3, output_tokens=2)


def candidate(query, **changes):
    return Proposal(
        query=query, requested_operation="compute_effect", proposed_tool="compute_effect", **changes
    ).model_dump_json()


def test_full_lifecycle_uses_tool_result_then_verifies(toy, query):
    model = ScriptedModel(
        query.model_dump_json(), candidate(query), candidate(query, proposed_answer="positive")
    )
    trace = CausalBridge(model, ReferenceBackend()).run(toy)
    assert trace.verdict.answer == "positive"
    assert trace.verdict.status == "verified"
    assert trace.tool_result.value == pytest.approx(0.4)
    assert trace.input_tokens == 9
    assert trace.output_tokens == 6
    assert [c.stage for c in trace.calls] == ["parse", "plan", "interpret"]
    assert "tool_result" in model.messages[-1][-1]["content"]
    assert trace.query_source == "llm_parser"


def test_model_never_receives_oracle_metadata(toy, query):
    raw = {
        **toy.model_dump(),
        "gold_response": "SECRET",
        "target_value": "SECRET",
        "hidden_cpts": {"SECRET": "SECRET"},
        "answerable": True,
    }
    model = ScriptedModel(
        query.model_dump_json(), candidate(query), candidate(query, proposed_answer="positive")
    )
    trace = CausalBridge(model, ReferenceBackend()).run(RuntimeCase.from_benchmark(raw))
    assert "SECRET" not in json.dumps(model.messages)
    assert "SECRET" not in trace.model_dump_json()


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "```json\n{}\n```",
        "{}",
        "[]",
        '{"cause":"X","outcome":"Y","question_type":"counterfactual"}',
        '{"cause":"X","cause":"Y","outcome":"Y","question_type":"reachability"}',
    ],
)
def test_invalid_parse_is_logged_as_execution_failure(toy, output):
    trace = CausalBridge(ScriptedModel(output), ReferenceBackend()).run(toy)
    assert trace.verdict.status == "execution_error"
    assert trace.verdict.response_action == "abstain"
    assert trace.failure_stage == "parse"
    assert len(trace.calls) == 1


def test_model_outage_returns_trace(toy):
    trace = CausalBridge(ScriptedModel(TimeoutError("timed out")), ReferenceBackend()).run(toy)
    assert trace.verdict.reason_code == "model_error"
    assert trace.failure_stage == "parse"


def test_final_model_cannot_swap_query_or_tool(toy, query):
    changed = Proposal(
        query=query,
        requested_operation="compute_effect",
        proposed_tool="has_directed_path",
        proposed_answer="positive",
    )
    model = ScriptedModel(candidate(query), changed.model_dump_json())
    trace = CausalBridge(model, ReferenceBackend()).run(toy, query=query)
    assert trace.verdict.status == "execution_error"
    assert trace.verdict.reason_code == "final_plan_changed"


def test_missing_evidence_does_not_execute_numeric_backend(toy, query):
    class MustNotExecute:
        def execute(self, request, case):
            raise AssertionError("Numeric call must be gated")

    limited = RuntimeCase.model_validate({**toy.model_dump(), "visible_cpts": []})
    model = ScriptedModel(candidate(query))
    trace = CausalBridge(model, MustNotExecute()).run(limited, query=query)
    assert trace.verdict.reason_code == "missing_evidence"
    assert len(trace.calls) == 1
    assert trace.verdict.response_action == "abstain"


def test_wrong_operation_is_classified_before_missing_evidence(toy):
    from causalbridge.schemas import Query

    q = Query(cause="X", outcome="Y", question_type="reachability")
    wrong = Proposal(
        query=q, requested_operation="has_directed_path", proposed_tool="compute_effect"
    )
    limited = RuntimeCase.model_validate({**toy.model_dump(), "visible_cpts": []})
    trace = CausalBridge(ScriptedModel(wrong.model_dump_json()), ReferenceBackend()).run(
        limited, query=q
    )
    assert trace.verdict.status == "wrong_operation"
    assert trace.verdict.reason_code == "tool_capability_mismatch"
    assert trace.tool_executed is False


def test_backend_outage_is_separate_from_model_failure(toy, query):
    class Broken:
        def execute(self, request, case):
            raise RuntimeError("engine unavailable")

    trace = CausalBridge(ScriptedModel(candidate(query)), Broken()).run(toy, query=query)
    assert trace.verdict.status == "execution_error"
    assert trace.verdict.reason_code == "tool_execution_error"
    assert trace.failure_stage == "execute"


def test_cli_demo_and_schema_export(tmp_path):
    output = tmp_path / "demo.jsonl"
    proc = subprocess.run(
        ["causalbridge", "demo", "--output", str(output)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert {r["verdict"]["status"] for r in records} >= {
        "verified",
        "unsupported",
        "wrong_operation",
    }
    assert all(r["model_mode"] == "scripted_fixture" for r in records)
    folder = tmp_path / "schemas"
    proc = subprocess.run(
        ["causalbridge", "schemas", "--output", str(folder)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert (
        json.loads((folder / "runtime_case.schema.json").read_text())["additionalProperties"]
        is False
    )


def test_cli_run_reports_model_unavailability_as_jsonl(toy, tmp_path):
    source, output, config = [tmp_path / n for n in ("case.jsonl", "out.jsonl", "model.json")]
    source.write_text(toy.model_dump_json() + "\n")
    config.write_text(json.dumps({"base_url": "http://127.0.0.1:1", "timeout_seconds": 0.1}))
    proc = subprocess.run(
        [
            "causalbridge",
            "run",
            "--input",
            str(source),
            "--output",
            str(output),
            "--config",
            str(config),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert json.loads(output.read_text())["verdict"]["reason_code"] == "model_error"
