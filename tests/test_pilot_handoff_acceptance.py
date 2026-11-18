"""Actual pilot APIs against PR9 acceptance targets; no live inference.

Skipped when the unmerged pilot API is absent. Enable by combining PR10 with main.
"""

import json
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest

from causalbridge.discovery.anm_requests import ANMConfig
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.acceptance_demo import run_acceptance
from causalbridge.evaluation.export import evaluator_mapping
from causalbridge.evaluation.handoff import validate_loader_handoff
from causalbridge.evaluation.integration import build_native_packages, condition
from causalbridge.llm.predictor import direction_messages

scoring = pytest.importorskip(
    "causalbridge.evaluation.scoring", reason="Requires pilot-readiness API"
)
prepare_pilot = pytest.importorskip("causalbridge.discovery.loader").prepare_pilot
snapshot = pytest.importorskip("test_pilot_data").snapshot

FIXTURES = Path(__file__).parent / "fixtures/track_b_scoring"
ORACLE = json.loads((FIXTURES / "expected.json").read_text())


def private_adapter(records):
    return [
        dict(
            case_id=e["case_id"],
            source_group=e["source_group"],
            weight=e["weight"],
            split=e["split"],
            cause_column={"first_to_second": 0, "second_to_first": 1}[e["reference_direction"]],
        )
        for e in records
    ]


def test_actual_loader_to_evidence_and_private_join(tmp_path):
    prepared = prepare_pilot(tmp_path, snapshot(tmp_path))
    runtime, private = validate_loader_handoff(prepared.pairs, private_adapter(prepared.evaluator))
    assert runtime[0].rows[0] == (1.0, 3.0)
    assert private[0].cause_column == 1 and private[0].weight == 0.5
    packages = build_native_packages(
        select_pair(runtime[0]), tmp_path / "anm", ANMConfig(sampling_seed=262)
    )
    mappings = evaluator_mapping(packages)
    assert mappings[0]["source_digest"] == prepared.evaluator[0]["source_digest"]
    for p in packages:
        for c in ("S0", "S1"):
            text = json.dumps(direction_messages(p.evidence, condition(c)))
            assert "PRIVATE_GOLD_SENTINEL" not in text
            assert "second_to_first" not in text and "source_group" not in text


@pytest.fixture(scope="module")
def consumer(tmp_path_factory):
    output = tmp_path_factory.mktemp("actual-consumer") / "run"
    report = run_acceptance(output, FIXTURES)
    rows = json.loads((output / "analysis.json").read_text())
    private = json.loads((output / "evaluator.json").read_text())
    mappings = json.loads((output / "mappings.json").read_text())
    by_case = {m["case_id"]: m for m in mappings}
    evaluator = [
        dict(
            case_id=e["case_id"],
            source_group=e["source_group"],
            weight=e["weight"],
            reference_direction="first_to_second" if e["cause_column"] == 0 else "second_to_first",
            source_digest=by_case[e["case_id"]]["source_digest"],
        )
        for e in private
    ]
    return rows, evaluator, mappings, report


def test_actual_scorer_reproduces_all_metric_oracles(consumer):
    rows, evaluator, mappings, report = consumer
    scores = scoring.score_pilot(rows, evaluator, mappings)
    assert len(scores) == 17 and report["audit_passed"]
    for s in scores:
        expected = ORACLE["expected"][s["package"] + "/" + s["condition"]]
        assert s["total_weight"] == expected["eligible_weight"] == 16
        assert s["case_count"] == 8 and s["source_group_count"] == 4
        for metric in ("coverage", "correct_yield", "wrong_yield", "selective_accuracy"):
            target = expected[metric]
            if target is None:
                assert s[metric] is None
            else:
                assert s[metric] == pytest.approx(float(Fraction(target)))


@pytest.mark.parametrize("draw", ORACLE["source_group_resamples"])
def test_actual_scorer_fixed_paired_group_resamples(consumer, draw):
    rows, evaluator, mappings, _ = consumer
    counts = Counter(draw["draw"])
    evaluator = [
        e | {"weight": e["weight"] * counts[e["source_group"]]}
        for e in evaluator
        if counts[e["source_group"]]
    ]
    ids = {e["case_id"] for e in evaluator}
    subset = [
        r
        for r in rows
        if r["case_id"] in ids and r["package"] == "E4" and r["condition"] in ("S1", "S2")
    ]
    scores = scoring.score_pilot(
        subset,
        evaluator,
        [m for m in mappings if m["case_id"] in ids],
        expected_conditions=[("E4", "S1"), ("E4", "S2")],
    )
    for s in scores:
        expected = draw[s["condition"]]
        assert s["total_weight"] == expected["eligible_weight"]
        for metric in ("coverage", "correct_yield", "wrong_yield", "selective_accuracy"):
            target = expected[metric]
            if target is None:
                assert s[metric] is None
            else:
                assert s[metric] == pytest.approx(float(Fraction(target)))


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "wrong_mapping", "wrong_source", "wrong_reference"]
)
def test_actual_scorer_rejects_broken_handoffs(consumer, fault):
    rows, evaluator, mappings, _ = deepcopy(consumer)
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif fault == "wrong_mapping":
        rows[0]["ab_mapping_id"] = "wrong"
    elif fault == "wrong_source":
        evaluator[0]["source_digest"] = "wrong"
    else:
        evaluator[0]["reference_direction"] = "invalid"
    with pytest.raises(ValueError):
        scoring.score_pilot(rows, evaluator, mappings)
