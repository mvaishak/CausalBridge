"""Merged-PR8 native execution through private joins to the scoring oracle."""

import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from test_scoring_acceptance_fixtures import ORACLE, assert_expected

from causalbridge.discovery.anm_requests import ANMConfig
from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.acceptance_demo import AcceptanceModel, run_acceptance
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.integration import build_native_packages

FIXTURES = Path(__file__).parent / "fixtures/track_b_scoring"


def forbidden(*args, **kwargs):
    raise AssertionError("No live/network calls allowed in offline acceptance")


@pytest.fixture(scope="module")
def accepted(tmp_path_factory):
    output = tmp_path_factory.mktemp("phase6") / "accepted"
    with (
        patch("socket.socket", forbidden),
        patch("causalbridge.llm.client.OllamaModel.generate", forbidden),
    ):
        report = run_acceptance(output, FIXTURES)
    return output, report


def test_complete_schedule_audit_and_zero_call_replay(accepted):
    output, report = accepted
    assert report["cases"] == 8 and report["package_count"] == 32
    assert report["new_model_calls"] == report["scripted_calls"] == 64
    assert report["s2_records"] == 32
    assert report["checked_parents"] == 20 and report["skipped_parents"] == 12
    assert report["analysis_rows"] == 136 and report["fixture_projection_matches"]
    assert report["s2_new_model_calls"] == report["resumed_new_model_calls"] == 0
    audit = audit_native(output / "experiment")
    assert audit["passed"] and not audit["findings"]


@pytest.mark.parametrize("key", list(ORACLE["expected"]))
def test_generated_joined_rows_match_hand_calculated_totals(accepted, key):
    output, _ = accepted
    rows = json.loads((output / "joined.json").read_text())
    package, condition = key.split("/")
    assert_expected(
        [r for r in rows if r["package"] == package and r["condition"] == condition],
        ORACLE["expected"][key],
    )


def test_pr8_binding_failure_claims_survive_export(accepted):
    rows = json.loads((accepted[0] / "analysis.json").read_text())
    failed = [r for r in rows if r["case_id"] == "D0208" and r["condition"] in ("S0", "S1")]
    assert len(failed) == 8
    assert all(r["failure_stage"] == "binding" and r["supplied_claim_count"] == 1 for r in failed)
    assert all(not r["prediction_scorable"] and r["predicted_direction"] is None for r in failed)


def test_saved_anm_cache_reused_without_method_execution(accepted, monkeypatch):
    output, _ = accepted
    pair = RuntimePair.model_validate(json.loads((output / "runtime.json").read_text())[0])
    directory = output / "anm" / pair.case_id
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.iterdir()
        if p.is_file()
    }
    monkeypatch.setattr("causalbridge.evaluation.integration.execute_anm_request", forbidden)
    packages = build_native_packages(
        select_pair(pair, SelectionSpec(mapping_seed=0, method_limit=8, display_limit=3)),
        directory,
        ANMConfig(minimum_rows=8, maximum_rows=8, sampling_seed=262),
    )
    assert len(packages) == 4
    assert before == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.iterdir()
        if p.is_file()
    }


def test_existing_output_refused_before_execution(accepted, monkeypatch):
    monkeypatch.setattr(AcceptanceModel, "generate", forbidden)
    with pytest.raises(FileExistsError):
        run_acceptance(accepted[0], FIXTURES)


def test_changed_fixture_is_not_silently_accepted(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    path = fixtures / "joined_rows.json"
    rows = json.loads(path.read_text())
    rows[0]["predicted_direction"] = "B_to_A"
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="Pipeline projection differs"):
        run_acceptance(tmp_path / "changed", fixtures)


def test_independent_audit_rejects_corrupted_s2_export(accepted, tmp_path):
    root = tmp_path / "corrupt"
    shutil.copytree(accepted[0] / "experiment", root)
    path = next((root / "exports").glob("*-s2.json"))
    releases = json.loads(path.read_text())
    releases[0]["released_direction"] = "B_to_A"
    path.write_text(json.dumps(releases))
    audit = audit_native(root)
    assert not audit["passed"]
    assert any(f["code"] == "s2_export" for f in audit["findings"])
