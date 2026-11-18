import pytest


def fixtures():
    evaluator = [
        dict(
            case_id="D1001",
            reference_direction="first_to_second",
            weight=1.0,
            source_group="g1",
            source_digest="x",
        ),
        dict(
            case_id="D1002",
            reference_direction="second_to_first",
            weight=3.0,
            source_group="g2",
            source_digest="y",
        ),
    ]
    mappings = [
        dict(
            case_id="D1001",
            ab_mapping_id="m1",
            source_digest="x",
            original_to_runtime_column_order=[1, 0],
        ),
        dict(
            case_id="D1002",
            ab_mapping_id="m2",
            source_digest="y",
            original_to_runtime_column_order=[0, 1],
        ),
    ]
    rows = [
        dict(
            case_id=c,
            ab_mapping_id=m,
            package="E4",
            condition="S1",
            predicted_direction=d,
            outcome=o,
            prediction_scorable=valid,
        )
        for c, m, d, o, valid in [
            ("D1001", "m1", "B_to_A", "answer", True),
            ("D1002", "m2", None, "prediction_failure", False),
        ]
    ]
    return rows, evaluator, mappings


def test_weighted_pilot_scores_count_failures_and_reverse_mapping():
    from causalbridge.evaluation.scoring import score_pilot

    rows, evaluator, mappings = fixtures()
    score = score_pilot(rows, evaluator, mappings, expected_conditions=[("E4", "S1")])[0]
    assert score["coverage"] == score["correct_yield"] == 0.25
    assert score["wrong_yield"] == 0.0
    assert score["selective_accuracy"] == 1.0
    assert score["total_weight"] == 4.0
    assert score["failure_count"] == 1
    assert score["source_group_count"] == 2


def test_zero_release_accuracy_is_undefined():
    from causalbridge.evaluation.scoring import score_pilot

    rows, evaluator, mappings = fixtures()
    rows[0].update(predicted_direction=None, outcome="model_abstention")
    score = score_pilot(rows, evaluator, mappings, expected_conditions=[("E4", "S1")])[0]
    assert score["selective_accuracy"] is None
    assert score["coverage"] == 0.0


@pytest.mark.parametrize("fault", ["missing", "duplicate", "mapping", "source", "direction"])
def test_scorer_rejects_incomplete_or_misbound_results(fault):
    from causalbridge.evaluation.scoring import score_pilot

    rows, evaluator, mappings = fixtures()
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows.append(rows[0])
    elif fault == "mapping":
        rows[0]["ab_mapping_id"] = "wrong"
    elif fault == "source":
        mappings[0]["source_digest"] = "wrong"
    else:
        rows[0]["predicted_direction"] = "invalid"
    with pytest.raises(ValueError):
        score_pilot(rows, evaluator, mappings, expected_conditions=[("E4", "S1")])
