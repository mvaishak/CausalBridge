"""ANM-only role isolation, receipts, freeze integrity and validation protocol."""

import hashlib
import json
from copy import deepcopy
from random import Random
from unittest.mock import patch

import pytest

from causalbridge.discovery import study
from causalbridge.evaluation.roster import evaluation_roster

pytest.importorskip("numpy")


@pytest.fixture(scope="module")
def developed(tmp_path_factory):
    root = tmp_path_factory.mktemp("anm-study")
    raw = root / "raw"
    raw.mkdir()
    files = {
        "README": "synthetic test only\n",
        "pairmeta.txt": "1 1 1 2 2 1\n2 1 1 2 2 2\n3 1 1 2 2 1\n",
    }
    for i in (1, 2, 3):
        rng = Random(10 + i)
        rows = []
        for _ in range(140):
            x = rng.uniform(-2, 2)
            rows.append(f"{x} {x**3 + rng.gauss(0, 0.1)}")
        files[f"pair{i:04d}.txt"] = "\n".join(rows) + "\n"
    for name, text in files.items():
        (raw / name).write_text(text)
    manifest = dict(
        version="tuebingen-pilot-v1",
        mapping_seed=261,
        minimum_rows=100,
        files={name: hashlib.sha256((raw / name).read_bytes()).hexdigest() for name in files},
        pairs=[
            dict(pair_id=i, source_group=f"group-{i}", split="test" if i == 3 else "development")
            for i in (1, 2, 3)
        ],
    )
    roster = evaluation_roster(manifest, raw)
    plan = dict(
        version="anm-study-v1",
        threshold=0.0,
        split_seeds=[261, 1261],
        variants=[
            dict(name="baseline", sample_limit=128),
            dict(name="ridge_1", sample_limit=128, ridge_alpha=1.0),
        ],
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No model/network calls")

    with (
        patch("socket.socket", forbidden),
        patch("causalbridge.llm.client.OllamaModel.generate", forbidden),
    ):
        summary = study.run_development(raw, manifest, roster, plan, root / "development")
    return dict(root=root, raw=raw, manifest=manifest, roster=roster, plan=plan, summary=summary)


def criteria():
    # Deliberately permissive synthetic test targets, never real study acceptance.
    return dict(
        decision_owner="unit test",
        rationale="exercise protocol only",
        min_coverage=0.0,
        min_selective_accuracy=0.0,
        max_wrong_yield=1.0,
        min_sign_stability=0.0,
    )


def test_development_uses_only_assigned_cases_and_preserves_inputs(developed):
    d = developed
    root, inputs, summary, completion = study._load_development(d["root"] / "development")
    assert {c["pair_id"] for c in inputs["cases"]} == {1, 2}
    assert summary["case_count"] == 2 and completion["expected_attempts"] == 8
    assert len(list((root / "attempts").glob("*/*/*/request.json"))) == 8
    for p in (root / "attempts").glob("*/*/*/request.json"):
        request = json.loads(p.read_text())
        assert "reference_direction" not in request and "source_group" not in request
    controls = json.loads((root / "controls.json").read_text())
    assert controls["independent_datasets"] == 4 and len(controls["records"]) == 16
    assert all(
        r["correctness"] is None
        for r in controls["records"]
        if r["family"] in {"linear_gaussian", "heteroscedastic"}
    )
    assert len(summary["variants"]) == 2
    assert all(v["primary"]["total_weight"] == 3 for v in summary["variants"])


def test_validation_runs_only_frozen_candidate_once_on_synthetic_fixture(developed, tmp_path):
    d = developed
    frozen = tmp_path / "frozen"
    study.freeze_candidate(d["root"] / "development", "ridge_1", criteria(), frozen)
    verdict = study.run_validation(d["raw"], frozen, tmp_path / "validation")
    assert "passed" in verdict
    inputs = json.loads((tmp_path / "validation" / "inputs.json").read_text())
    assert {c["pair_id"] for c in inputs["cases"]} == {3}
    assert inputs["executed_variants"] == ["ridge_1"]
    assert len(list((tmp_path / "validation" / "attempts").glob("*/*/*/request.json"))) == 2
    assert not (tmp_path / "validation" / "controls.json").exists()
    with pytest.raises(FileExistsError):
        study.run_validation(d["raw"], frozen, tmp_path / "second-validation")


def test_missing_criteria_and_unknown_candidates_cannot_freeze(developed, tmp_path):
    with pytest.raises(ValueError):
        study.freeze_candidate(
            developed["root"] / "development", "baseline", {}, tmp_path / "missing"
        )
    with pytest.raises(ValueError, match="not in"):
        study.freeze_candidate(
            developed["root"] / "development", "unplanned", criteria(), tmp_path / "unknown"
        )
    assert not (tmp_path / "missing").exists() and not (tmp_path / "unknown").exists()


@pytest.mark.parametrize("fault", ["inputs", "evaluations", "summary", "request", "source"])
def test_altered_development_artifacts_cannot_be_frozen(developed, tmp_path, fault):
    import shutil

    copy = tmp_path / "copy"
    shutil.copytree(developed["root"] / "development", copy)
    if fault in {"inputs", "evaluations", "summary"}:
        path = copy / (fault + ".json")
        path.write_text("{}")
    elif fault == "source":
        path = copy / "inputs.json"
        value = json.loads(path.read_text())
        value["source_digest"] = "wrong"
        path.write_text(json.dumps(value))
    else:
        path = next((copy / "attempts").glob("*/*/*/request.json"))
        value = json.loads(path.read_text())
        value["sample_digest"] = "sha256:" + "ab" * 32
        path.write_text(json.dumps(value))
    with pytest.raises((ValueError, KeyError, TypeError)):
        study.freeze_candidate(copy, "baseline", criteria(), tmp_path / "frozen")
    assert not (tmp_path / "frozen").exists()


def test_frozen_candidate_and_dependency_changes_block_validation(developed, tmp_path, monkeypatch):
    frozen = tmp_path / "frozen"
    study.freeze_candidate(developed["root"] / "development", "baseline", criteria(), frozen)
    path = frozen / "freeze.json"
    data = json.loads(path.read_text())
    data["payload"]["variant"] = "ridge_1"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity"):
        study.run_validation(developed["raw"], frozen, tmp_path / "validation")
    assert not (frozen / "validation_started.json").exists()
    monkeypatch.setattr(study, "_environment", lambda: {"numpy": "changed"})
    with pytest.raises(ValueError, match="dependencies"):
        study.freeze_candidate(
            developed["root"] / "development", "baseline", criteria(), tmp_path / "other"
        )


def test_existing_outputs_and_modified_roster_fail_before_fits(developed, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No fitting after failed preflight")

    monkeypatch.setattr(study, "_fit", forbidden)
    d = developed
    with pytest.raises(FileExistsError):
        study.run_development(
            d["raw"], d["manifest"], d["roster"], d["plan"], d["root"] / "development"
        )
    roster = deepcopy(d["roster"])
    roster["pairs"][2]["anm_use"] = "development"
    with pytest.raises(ValueError, match="roster"):
        study.run_development(d["raw"], d["manifest"], roster, d["plan"], tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize(
    "metric", ["coverage", "selective_accuracy", "wrong_yield", "sign_stability"]
)
def test_each_explicit_acceptance_criterion_is_enforced(metric):
    targets = criteria() | dict(
        min_coverage=0.5, min_selective_accuracy=0.5, max_wrong_yield=0.5, min_sign_stability=0.5
    )
    candidate = dict(
        primary=dict(coverage=0.5, selective_accuracy=0.5, wrong_yield=0.5), sign_stability=0.5
    )
    assert study._gate(candidate, study.Criteria.model_validate(targets))["passed"]
    if metric == "sign_stability":
        candidate[metric] = 0.0
    else:
        candidate["primary"][metric] = 1.0 if metric == "wrong_yield" else 0.0
    assert not study._gate(candidate, study.Criteria.model_validate(targets))["passed"]


def test_no_answers_cannot_pass_an_accuracy_gate():
    candidate = dict(
        primary=dict(coverage=0.0, selective_accuracy=None, wrong_yield=0.0), sign_stability=0.0
    )
    assert not study._gate(candidate, study.Criteria.model_validate(criteria()))["passed"]
