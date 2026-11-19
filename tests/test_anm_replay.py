"""Baseline replay must preserve originals and expose corrupt or incomplete inputs."""

import json
from random import Random

import pytest

from causalbridge.discovery import anm
from causalbridge.discovery.anm_requests import ANMConfig, save_anm_request
from causalbridge.discovery.replay import reproduce_attempts

pytest.importorskip("numpy")


def make_attempt(root, *, constant=False):
    rng = Random(73)
    rows = []
    for _ in range(128):
        x = rng.uniform(-2, 2)
        rows.append([1.0, 2.0] if constant else [x, x**3 + rng.gauss(0, 0.2)])
    directory = root / "development" / "attempts" / "case-original-261"
    save_anm_request(
        rows,
        case_id="D0001",
        ab_mapping_id="baseline-map",
        directory=directory,
        config=ANMConfig(threshold=0.001, maximum_rows=128),
    )
    anm.execute_anm_request(directory)
    return directory


def original_bytes(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("constant", [False, True])
def test_replay_preserves_all_originals_and_request_inputs(tmp_path, constant):
    source = tmp_path / "originals"
    attempt = make_attempt(source, constant=constant)
    before = original_bytes(source)
    output = tmp_path / "replayed"
    report = reproduce_attempts(source, output, recompute=True, expected_count=1)
    assert report["passed"] and report["original_files_unchanged"]
    assert report["replay_count"] == 1 and report["expected_count_matches"]
    assert report["schedule_identity_verified"] is False
    entry = report["attempts"][0]
    assert entry["replay_matches"] and entry["differences"] == []
    assert entry["result_status"] == ("error" if constant else "ok")
    for name in ("sample.json", "config.json", "request.json", "inputs.json"):
        assert json.loads((attempt / name).read_text()) == json.loads(
            (output / entry["replay_directory"] / name).read_text()
        )
    assert original_bytes(source) == before
    assert json.loads((output / "report.json").read_text())["passed"] is True


def test_check_only_never_runs_the_numerical_method(tmp_path, monkeypatch):
    source = tmp_path / "originals"
    make_attempt(source)
    # The historical validation run also contains a benchmark/config.json.
    (source / "benchmark").mkdir()
    (source / "benchmark" / "config.json").write_text('{"not_an_anm_attempt":true}')

    def forbidden(*args, **kwargs):
        raise AssertionError("Check-only must not fit regression")

    monkeypatch.setattr("causalbridge.discovery.replay.execute_anm_request", forbidden)
    report = reproduce_attempts(source, tmp_path / "checked")
    assert report["passed"] and report["replay_count"] == 0
    assert report["expected_count_matches"] is None
    assert not (tmp_path / "checked" / "attempts").exists()


@pytest.mark.parametrize("fault", ["missing_request", "incomplete", "sample", "marker", "count"])
def test_bad_originals_fail_before_any_new_fit(tmp_path, monkeypatch, fault):
    source = tmp_path / "originals"
    attempt = make_attempt(source)
    if fault == "missing_request":
        (attempt / "request.json").unlink()
    elif fault == "incomplete":
        (attempt / "result.json").unlink()
    elif fault == "sample":
        sample = json.loads((attempt / "sample.json").read_text())
        sample["rows"][0][0] += 1.0
        (attempt / "sample.json").write_text(json.dumps(sample))
    elif fault == "marker":
        (attempt / "execution_started.json").write_text('{"request_digest":"wrong"}')
    before = original_bytes(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid preflight must stop numerical replay")

    monkeypatch.setattr("causalbridge.discovery.replay.execute_anm_request", forbidden)
    report = reproduce_attempts(
        source, tmp_path / "checked", recompute=True, expected_count=2 if fault == "count" else 1
    )
    assert not report["passed"] and report["replay_count"] == 0
    assert report["discovered_count"] == 1
    assert original_bytes(source) == before


def test_changed_scores_and_arrow_fail_reproduction(tmp_path, monkeypatch):
    source = tmp_path / "originals"
    monkeypatch.setattr(anm, "_calculate", lambda saved, record: (0.1, 0.3))
    make_attempt(source)
    monkeypatch.setattr(anm, "_calculate", lambda saved, record: (0.3, 0.1))
    report = reproduce_attempts(source, tmp_path / "replayed", recompute=True)
    assert not report["passed"]
    assert {"score_ab", "score_ba", "margin", "decision", "predicted_direction"} <= set(
        report["attempts"][0]["differences"]
    )


def test_missing_bundle_is_not_treated_as_a_pass(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        reproduce_attempts(tmp_path / "missing", tmp_path / "out")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "validation.md").write_text("All comparisons passed")
    with pytest.raises(ValueError, match="No original ANM attempts"):
        reproduce_attempts(tmp_path / "reports", tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("destination", ["originals", "originals/nested", "already-exists"])
def test_output_cannot_replace_or_extend_originals(tmp_path, destination):
    source = tmp_path / "originals"
    make_attempt(source)
    output = tmp_path / destination
    if destination == "already-exists":
        output.mkdir()
    before = original_bytes(source)
    with pytest.raises((ValueError, FileExistsError)):
        reproduce_attempts(source, output)
    assert original_bytes(source) == before


def test_symlink_output_inside_originals_is_rejected(tmp_path):
    source = tmp_path / "originals"
    make_attempt(source)
    link = tmp_path / "alias"
    link.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        reproduce_attempts(source, link / "new")


def test_source_changes_during_replay_fail_report(tmp_path, monkeypatch):
    source = tmp_path / "originals"
    attempt = make_attempt(source)
    original = anm.execute_anm_request

    def altered(directory):
        result = original(directory)
        (attempt / "config.json").write_text("{}")
        return result

    monkeypatch.setattr("causalbridge.discovery.replay.execute_anm_request", altered)
    report = reproduce_attempts(source, tmp_path / "replayed", recompute=True)
    assert not report["passed"] and not report["original_files_unchanged"]


def test_cli_records_a_failed_expected_count_and_returns_nonzero(tmp_path, monkeypatch, capsys):
    from causalbridge.discovery.replay import main

    source = tmp_path / "originals"
    make_attempt(source)
    output = tmp_path / "checked"
    monkeypatch.setattr(
        "sys.argv",
        ["replay", "--attempt-root", str(source), "--output", str(output), "--expected-count", "2"],
    )
    assert main() == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False
    assert json.loads((output / "report.json").read_text())["expected_count_matches"] is False
