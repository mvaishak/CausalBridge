"""Audit and numerical-accounting tests: no ANM regression fits or live calls."""

import hashlib
import io
import json
import tarfile

import numpy as np
import pytest

from causalbridge.evaluation.anm_failure_audit import (
    ARCHIVE,
    CONFIG,
    DEVELOPMENT,
    MANIFEST,
    VALIDATION,
    features,
    materialize,
    outcome,
    rank_auc,
    read,
    real_diagnosis,
    real_panel,
    run_audit,
    summary,
    verified_archive,
    verify_attempt,
    write,
)
from causalbridge.evaluation.anm_failure_report import report


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    root = tmp_path_factory.mktemp("saved-anm")
    files = verified_archive()
    assert len(files) == 7125
    materialize(files, root)
    return root


@pytest.fixture(scope="module")
def real_rows(originals):
    return real_panel(originals, VALIDATION, read(CONFIG))


def tiny_archive(tmp_path, *, fault=None):
    path = tmp_path / "records.tar.gz"
    entries = []
    with tarfile.open(path, "w:gz") as tar:
        for name in ["a.json", "a.json"] if fault == "duplicate" else ["a.json"]:
            info = tarfile.TarInfo("../escape.json" if fault == "path" else name)
            data = b'{"value":1}'
            if fault == "link":
                info.type = tarfile.SYMTYPE
                info.linkname = "/tmp/escape"
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            entries.append(
                {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            )
    # Duplicated members should fail even when the manifest lists a single path.
    entries = entries[:1]
    if fault == "member_hash":
        entries[0]["sha256"] = "0" * 64
    if fault == "missing":
        entries.append({"path": "missing.json", "bytes": 1, "sha256": "0" * 64})
    manifest = tmp_path / "manifest.json"
    write(
        manifest,
        {
            "archive_sha256": "0" * 64
            if fault == "archive_hash"
            else hashlib.sha256(path.read_bytes()).hexdigest(),
            "files": entries,
        },
    )
    return path, manifest


def test_tiny_archive_integrity(tmp_path):
    path, manifest = tiny_archive(tmp_path)
    assert verified_archive(path, manifest) == {"a.json": b'{"value":1}'}


@pytest.mark.parametrize(
    "fault", ["duplicate", "path", "link", "member_hash", "archive_hash", "missing"]
)
def test_archive_rejects_unsafe_or_unbound_inputs(tmp_path, fault):
    path, manifest = tiny_archive(tmp_path, fault=fault)
    with pytest.raises(ValueError):
        verified_archive(path, manifest)
    assert not (tmp_path.parent / "escape.json").exists()


def test_features_count_ties_and_split_overlap_without_altering_rows():
    rows = [[0, 0], [1, 1], [0, 0], [2, 3]]
    copy = json.loads(json.dumps(rows))
    f = features(rows, [0, 1], [2, 3])
    assert f["selected_rows"] == 4
    assert f["max_tie_fraction"] == 0.5
    assert f["duplicate_row_fraction"] == 0.25
    assert f["evaluation_exact_row_in_training_fraction"] == 0.5
    assert f["evaluation_outside_training_range"] == [0.5, 0.5]
    assert rows == copy


def test_metrics_do_not_turn_failures_or_controls_into_wrong_answers():
    assert outcome(None, "A_to_B", "error") == "execution_failure"
    assert outcome(None, "A_to_B") == "abstention"
    assert outcome("B_to_A", "A_to_B") == "wrong"
    assert outcome("A_to_B", None) == "not_identified_control"
    rows = [
        {"outcome": k, "weight": 1, "source_group": "shared"}
        for k in ("correct", "wrong", "abstention", "execution_failure")
    ]
    s = summary(rows)
    assert s["n"] == 4 and s["source_groups"] == 1
    assert s["answered_accuracy"]["rate"] == 0.5
    assert s["coverage"]["denominator"] == 4
    assert summary([])["answered_accuracy"]["rate"] is None


def test_rank_auc_ties_and_undefined_cases():
    assert rank_auc([2], [1]) == 1
    assert rank_auc([1], [2]) == 0
    assert rank_auc([1], [1]) == 0.5
    assert rank_auc([], [1]) is None


def test_primary_and_split_stability_golden_counts(real_rows):
    result = real_diagnosis(real_rows, read(CONFIG))
    assert result["primary"]["counts"] == {
        "correct": 13,
        "wrong": 13,
        "abstention": 12,
        "execution_failure": 0,
    }
    assert result["splits"]["1261"]["counts"]["correct"] == 20
    assert result["splits"]["2261"]["counts"]["correct"] == 14
    assert result["strata"]["full_512"]["counts"] == {
        "correct": 9,
        "wrong": 3,
        "abstention": 10,
        "execution_failure": 0,
    }
    assert result["strata"]["fewer_than_512"]["counts"]["wrong"] == 10
    assert result["outcome_diagnostics"]["wrong"]["raw_sign_stable"]["numerator"] == 4
    assert result["outcome_diagnostics"]["wrong"]["wrong_all_splits"]["numerator"] == 3
    assert result["outcome_diagnostics"]["correct"]["raw_sign_stable"]["numerator"] == 12
    assert result["sample_size_overlap_source_groups"] == ["pima_diabetes"]
    assert result["margin"]["rank_auc"] == pytest.approx(0.6686390532544378)


def test_missing_and_duplicate_attempts_fail(originals, tmp_path):
    evaluations = read(originals / VALIDATION / "evaluations.json")
    for mode in ("missing", "duplicate"):
        target = tmp_path / mode
        target.mkdir()
        # Links are only test fixtures inside pytest's temporary tree, not archive extraction.
        (target / "runs").symlink_to(originals / "runs", target_is_directory=True)
        changed = list(evaluations[:-1] if mode == "missing" else evaluations + evaluations[:1])
        # Isolated copied execution metadata with original attempts; originals are untouched.
        panel = tmp_path / (mode + "-panel")
        panel.mkdir()
        write(panel / "evaluations.json", changed)
        write(panel / "inputs.json", read(originals / VALIDATION / "inputs.json"))
        (panel / "attempts").symlink_to(
            originals / VALIDATION / "attempts", target_is_directory=True
        )
        with pytest.raises(ValueError):
            real_panel(tmp_path, panel.name, read(CONFIG))


@pytest.mark.parametrize("fault", ["sample", "request", "threshold", "repro", "preprocessing"])
def test_original_request_and_numeric_binding_reject_corruption(originals, tmp_path, fault):
    ev = read(originals / DEVELOPMENT / "evaluations.json")[0]
    original = originals / DEVELOPMENT / ev["directory"]
    directory = tmp_path / "attempt"
    directory.mkdir()
    for p in original.iterdir():
        (directory / p.name).write_bytes(p.read_bytes())
    if fault == "sample":
        p = directory / "sample.json"
        r = read(p)
        r["rows"][0][0] += 1
        write(p, r)
    elif fault == "request":
        p = directory / "request.json"
        r = read(p)
        r["split_seed"] += 1
        write(p, r)
    elif fault == "threshold":
        p = directory / "result.json"
        r = read(p)
        r["threshold"] = 0
        write(p, r)
    else:
        p = directory / "reproducibility.json"
        r = read(p)
        if fault == "repro":
            r["request_digest"] = "sha256:" + "0" * 64
        else:
            r["preprocessing"]["training_means"][0] += 1
        write(p, r)
    with pytest.raises(ValueError):
        verify_attempt(directory, read(CONFIG), ev)


def test_end_to_end_no_refits_and_frozen_bytes_preserved(tmp_path, monkeypatch):
    before = (ARCHIVE.read_bytes(), MANIFEST.read_bytes())

    def forbidden(*args, **kwargs):
        raise AssertionError("No numerical refit is authorized in the saved-data audit")

    monkeypatch.setattr(np.linalg, "solve", forbidden)
    result = run_audit(tmp_path / "audit")
    assert result["archive_files_verified"] == 7125
    assert result["real_attempts_verified"] == 210
    assert result["synthetic"]["verified_attempts"] == 352
    assert result["new_anm_fits"] == result["new_permutations"] == result["live_model_calls"] == 0
    assert {c["pair_id"] for c in result["source_metadata_review"]["cases"]} == {91, 92, 108}
    for partition in result["synthetic"]["paired_sample_size"]:
        assert partition["n_datasets"] == partition["selected_samples_nested"] == 32
    confirmation = next(
        r
        for r in result["synthetic"]["compatible_panels"]
        if r["partition"] == "confirmation" and r["n_rows"] == 512 and r["split_seed"] == 261
    )
    assert confirmation["counts"] == {
        "correct": 26,
        "wrong": 0,
        "abstention": 6,
        "execution_failure": 0,
    }
    assert all(r["causal_accuracy"] is None for r in result["synthetic"]["control_counts"])
    report(result, tmp_path / "audit" / "report.md")
    text = (tmp_path / "audit" / "report.md").read_text()
    assert "4/13" in text and "12/13" in text and "not a fresh independent" in text
    assert (ARCHIVE.read_bytes(), MANIFEST.read_bytes()) == before
    with pytest.raises(FileExistsError):
        run_audit(tmp_path / "audit")


@pytest.mark.parametrize("difference,allowed", [(1e-13, True), (0.01, False)])
def test_standardization_precision_policy_with_consistent_receipts(
    originals, tmp_path, difference, allowed
):
    from causalbridge.discovery.schemas import canonical_digest

    ev = read(originals / DEVELOPMENT / "evaluations.json")[0]
    directory = tmp_path / "attempt"
    directory.mkdir()
    for p in (originals / DEVELOPMENT / ev["directory"]).iterdir():
        (directory / p.name).write_bytes(p.read_bytes())
    repro = read(directory / "reproducibility.json")
    repro["preprocessing"]["training_means"][0] += difference
    write(directory / "reproducibility.json", repro)
    result = read(directory / "result.json")
    result["provenance"]["reproducibility_ref"] = canonical_digest(repro)
    write(directory / "result.json", result)
    ev["result"] = result
    ev["result_digest"] = canonical_digest(result)
    if allowed:
        verify_attempt(directory, read(CONFIG), ev)
    else:
        with pytest.raises(ValueError, match="standardization"):
            verify_attempt(directory, read(CONFIG), ev)


def test_cached_mse_requires_residual_moment_agreement(originals):
    ev = read(originals / DEVELOPMENT / "evaluations.json")[0]
    ev["mse"]["A_to_B"] += 0.1
    with pytest.raises(ValueError, match="MSE"):
        verify_attempt(originals / DEVELOPMENT / ev["directory"], read(CONFIG), ev)
