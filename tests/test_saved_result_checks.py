"""Regression checks for malformed records previously hidden by chained comparisons."""

import copy
import json
import tarfile
from pathlib import Path

import pytest

from causalbridge.evaluation.outcome_accounting import account_panel, outcome_category
from causalbridge.evaluation.saved_checks import journal_trials, validate_panel


@pytest.fixture
def journal():
    result = []
    for key in ("a", "b"):
        gen = {
            "model": "test",
            "text": "reply",
            "status": "complete",
            "raw_response": json.dumps(
                {
                    "done": True,
                    "done_reason": "stop",
                    "model": "test",
                    "message": {"content": "reply"},
                }
            ),
        }
        start = {
            "key": key,
            "attempt_id": key,
            "messages": [key],
            "output_schema": {},
            "config": {},
        }
        execution = {
            "generation": gen,
            "request_messages": [key],
            "output_schema": {},
            "generation_config": {},
        }
        result.extend(
            [
                {"kind": "native_started", "data": start},
                {"kind": "native_generated", "data": {"key": key, "generation": gen}},
                {"kind": "native_finished", "data": {"key": key, "execution": execution}},
            ]
        )
    return result


def test_complete_journal(journal):
    assert len(journal_trials(journal, 2)[0]) == 2


def test_two_equal_short_stages_are_rejected(journal):
    # Previously 2 != 1 != 1 evaluated False.
    journal = [
        e
        for e in journal
        if not (e["data"]["key"] == "b" and e["kind"] in {"native_generated", "native_finished"})
    ]
    with pytest.raises(ValueError, match="identities differ"):
        journal_trials(journal, 2)


@pytest.mark.parametrize("stage", ["native_started", "native_generated", "native_finished"])
def test_duplicate_journal_events_are_not_silently_overwritten(journal, stage):
    journal.append(copy.deepcopy(next(e for e in journal if e["kind"] == stage)))
    with pytest.raises(ValueError, match="Duplicate"):
        journal_trials(journal, 2)


def test_equal_counts_with_different_keys_rejected(journal):
    journal[-1]["data"]["key"] = "unplanned"
    with pytest.raises(ValueError, match="identities differ"):
        journal_trials(journal, 2)


def test_changed_finish_response_rejected(journal):
    journal[-1] = copy.deepcopy(journal[-1])
    journal[-1]["data"]["execution"]["generation"]["status"] = "changed"
    with pytest.raises(ValueError, match="durable generation"):
        journal_trials(journal, 2)


@pytest.mark.parametrize("raw", [{"done": False}, {"done": True, "done_reason": "length"}])
def test_raw_completion_is_checked(journal, raw):
    journal[1]["data"]["generation"]["raw_response"] = json.dumps(
        {"model": "test", "message": {"content": "reply"}, **raw}
    )
    with pytest.raises(ValueError, match="Incomplete raw"):
        journal_trials(journal, 2)


@pytest.fixture(scope="module")
def panel():
    archive = Path(__file__).resolve().parents[1] / (
        "artifacts/final-delivery/postmerge-track-b/integrated-38-resumed-live.tar.gz"
    )
    with tarfile.open(archive) as handle:
        prefix = "postmerge-track-b-38-resumed-live/"

        def read(name):
            return handle.extractfile(prefix + name).read().decode()

        return (
            [json.loads(line) for line in read("analysis.jsonl").splitlines()],
            json.loads(read("evaluator.json")),
            json.loads(read("evaluation_mapping.json")),
            json.loads(read("scores.json")),
        )


def test_saved_panel_reproduces_and_accounting_reconciles(panel):
    rows, truth, mapping, scores = panel
    result = account_panel(rows, truth, mapping, scores)
    assert all(sum(s["categories"].values()) == 38 for s in result["metrics"])
    e4 = next(s for s in result["metrics"] if (s["package"], s["condition"]) == ("E4", "S2"))
    assert e4["categories"] == {
        "correct_answer": 10,
        "wrong_answer": 13,
        "upstream_model_abstention": 11,
        "checker_rejection": 3,
        "execution_or_binding_failure": 1,
    }
    s1 = next(s for s in result["metrics"] if (s["package"], s["condition"]) == ("E4", "S1"))
    assert s1["categories"]["model_abstention"] == 11  # twelfth non-answer was a binding error
    assert s1["coverage"] - e4["coverage"] == pytest.approx(0.08025)


def test_equal_undersized_metadata_rejected(panel):
    rows, truth, mapping, scores = panel
    with pytest.raises(ValueError, match="Incomplete"):
        validate_panel(rows, truth[:-1], mapping[:-1], scores, 38)


def test_duplicate_case_metadata_rejected(panel):
    rows, truth, mapping, scores = panel
    with pytest.raises(ValueError, match="Duplicate"):
        validate_panel(rows, truth + truth[:1], mapping, scores, 38)


def test_duplicate_trial_cannot_replace_missing_trial(panel):
    rows, truth, mapping, scores = panel
    with pytest.raises(ValueError, match="analysis trial"):
        validate_panel(rows[:-1] + rows[:1], truth, mapping, scores, 38)


def test_changed_saved_scores_are_rejected(panel):
    rows, truth, mapping, scores = copy.deepcopy(panel)
    scores[0]["coverage"] += 0.1
    with pytest.raises(ValueError, match="Saved scores"):
        validate_panel(rows, truth, mapping, scores, 38)


def test_rejection_is_not_upstream_abstention():
    row = {
        "condition": "S2",
        "outcome": "fail",
        "prediction_scorable": True,
        "predicted_direction": None,
    }
    parent = {"predicted_direction": "A_to_B", "outcome": "answer"}
    assert outcome_category(row, parent) == "checker_rejection"
    row["outcome"] = "checker_error"
    assert outcome_category(row, parent) == "checker_failure"


def test_unknown_nonrelease_fails_closed():
    with pytest.raises(ValueError, match="Unclassified"):
        outcome_category(
            {
                "condition": "S0",
                "outcome": "unknown",
                "prediction_scorable": True,
                "predicted_direction": None,
            }
        )


def test_raw_text_disagrees_with_execution(journal):
    journal[1]["data"]["generation"]["text"] = "altered"
    with pytest.raises(ValueError, match="raw model response"):
        journal_trials(journal, 2)


def test_changed_generation_configuration(journal):
    journal[-1]["data"]["execution"]["generation_config"] = {"seed": 999}
    with pytest.raises(ValueError, match="original request"):
        journal_trials(journal, 2)
