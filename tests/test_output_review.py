"""Saved-output review must reject corruption and never rerun inference."""

import json

import pytest
from test_native_integration_runner import NativeModel, configuration, runner, selected_pair

from causalbridge.evaluation.export import analysis_rows, evaluator_mapping
from causalbridge.evaluation.output_review import prepare_review


@pytest.fixture
def bundle(tmp_path):
    pytest.importorskip("numpy")
    from causalbridge.evaluation.integration import build_native_packages

    root = tmp_path / "bundle"
    root.mkdir()
    packages = build_native_packages(selected_pair(), root / "anm", configuration())
    model = NativeModel("unavailable_row")
    run = runner(root / "experiment").run(packages, model)
    releases = runner(root / "experiment").replay_s2(run["manifest_id"])
    (root / "session.json").write_text(json.dumps({"model_mode": "scripted_fixture"}))
    (root / "evaluation_mapping.json").write_text(json.dumps(evaluator_mapping(packages)))
    (root / "analysis.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in analysis_rows(run, releases))
    )
    return root


def hashes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_review_exports_original_evidence_without_inference_or_input_edits(
    bundle, tmp_path, monkeypatch
):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Review must never execute inference or network calls")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(NativeModel, "generate", forbidden)
    monkeypatch.setattr("causalbridge.discovery.anm.execute_anm_request", forbidden)
    before = hashes(bundle)
    out = tmp_path / "review"
    report = prepare_review(bundle, out, expected_cases=1)
    assert report["passed"], report
    assert report["proposal_count"] == 8
    assert report["checker_decision_count"] == report["checker_rejection_count"] == 4
    assert hashes(bundle) == before
    proposals = [json.loads(line) for line in (out / "proposals.jsonl").read_text().splitlines()]
    decisions = [
        json.loads(line) for line in (out / "checker-decisions.jsonl").read_text().splitlines()
    ]
    assert all(p["consistency_label"] == "pending" for p in proposals)
    assert all(p["raw_response_text"] and p["supplied_evidence"] for p in proposals)
    assert all(d["process_review_label"] == "pending" and d["claim_findings"] for d in decisions)
    assert len({p["review_id"] for p in proposals}) == 8
    assert all("reference_direction" not in p for p in proposals)
    assert {d["review_id"] for d in decisions} == {
        p["review_id"] for p in proposals if p["condition"] == "S1"
    }


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "analysis",
        "mapping",
        "parent",
        "journal",
        "count",
        "relocated_anm",
        "boolean_mapping",
    ],
)
def test_corrupted_or_incomplete_bundles_produce_only_failure_report(bundle, tmp_path, fault):
    if fault == "missing":
        (bundle / "analysis.jsonl").unlink()
    elif fault == "analysis":
        path = bundle / "analysis.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["predicted_direction"] = "B_to_A"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    elif fault == "mapping":
        path = bundle / "evaluation_mapping.json"
        rows = json.loads(path.read_text())
        rows[0]["original_to_runtime_column_order"].reverse()
        path.write_text(json.dumps(rows))
    elif fault == "boolean_mapping":
        path = bundle / "evaluation_mapping.json"
        rows = json.loads(path.read_text())
        rows[0]["original_to_runtime_column_order"] = [
            bool(v) for v in rows[0]["original_to_runtime_column_order"]
        ]
        path.write_text(json.dumps(rows))
    elif fault == "parent":
        path = next((bundle / "experiment/exports").glob("*-s2.json"))
        rows = json.loads(path.read_text())
        rows[0]["source_key"] = "nonexistent-parent"
        path.write_text(json.dumps(rows))
    elif fault == "journal":
        with (bundle / "experiment/events.jsonl").open("a") as stream:
            stream.write('{"partial":')
    elif fault == "relocated_anm":
        (bundle / "anm").rename(bundle / "relocated")
    before = hashes(bundle)
    out = tmp_path / "review"
    report = prepare_review(bundle, out, expected_cases=2 if fault == "count" else 1)
    assert not report["passed"]
    assert report["missing_files"] or report["findings"]
    assert {p.name for p in out.iterdir()} == {"intake.json"}
    assert hashes(bundle) == before


def test_output_must_be_new_and_separate(bundle, tmp_path):
    with pytest.raises(ValueError, match="outside"):
        prepare_review(bundle, bundle / "review", expected_cases=1)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        prepare_review(bundle, existing, expected_cases=1)
