import pytest

from causalbridge.discovery.schemas import canonical_digest


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
            ab_mapping_id=canonical_digest({"case_id": "D1001", "order": [1, 0], "seed": 0}),
            mapping_seed=0,
            source_digest="x",
            original_to_runtime_column_order=[1, 0],
        ),
        dict(
            case_id="D1002",
            ab_mapping_id=canonical_digest({"case_id": "D1002", "order": [0, 1], "seed": 3}),
            mapping_seed=3,
            source_digest="y",
            original_to_runtime_column_order=[0, 1],
        ),
    ]
    rows = [
        dict(
            case_id=c,
            ab_mapping_id=next(
                record["ab_mapping_id"] for record in mappings if record["case_id"] == c
            ),
            package="E4",
            condition="S1",
            predicted_direction=d,
            outcome=o,
            prediction_scorable=valid,
        )
        for c, d, o, valid in [
            ("D1001", "B_to_A", "answer", True),
            ("D1002", None, "prediction_failure", False),
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


@pytest.mark.parametrize(
    "fault",
    [
        "flipped_order",
        "rewritten_id",
        "boolean_order",
        "float_order",
        "duplicate_order",
        "missing_seed",
        "boolean_seed",
        "float_seed",
        "negative_seed",
        "changed_seed",
        "wrong_id",
        "wrong_case",
    ],
)
def test_scorer_rejects_inconsistent_mapping_identity(fault):
    from causalbridge.evaluation.scoring import score_pilot

    rows, evaluator, mappings = fixtures()
    record = mappings[0]
    if fault in {"flipped_order", "rewritten_id"}:
        record["original_to_runtime_column_order"] = [0, 1]
        if fault == "rewritten_id":
            record["ab_mapping_id"] = canonical_digest(
                {"case_id": record["case_id"], "order": [0, 1], "seed": record["mapping_seed"]}
            )
            rows[0]["ab_mapping_id"] = record["ab_mapping_id"]
    elif fault == "boolean_order":
        record["original_to_runtime_column_order"] = [True, False]
    elif fault == "float_order":
        record["original_to_runtime_column_order"] = [1.0, 0.0]
    elif fault == "duplicate_order":
        record["original_to_runtime_column_order"] = [1, 1]
    elif fault == "missing_seed":
        record.pop("mapping_seed")
    elif fault == "boolean_seed":
        record["mapping_seed"] = False
    elif fault == "float_seed":
        record["mapping_seed"] = 0.0
    elif fault == "negative_seed":
        record["mapping_seed"] = -1
    elif fault == "changed_seed":
        record["mapping_seed"] = 99
    elif fault == "wrong_id":
        record["ab_mapping_id"] = "sha256:" + "f" * 64
        rows[0]["ab_mapping_id"] = record["ab_mapping_id"]
    else:
        record["case_id"] = "D9999"
    with pytest.raises(ValueError):
        score_pilot(rows, evaluator, mappings, expected_conditions=[("E4", "S1")])


def test_mapping_integrity_fix_preserves_original_weighted_results():
    from causalbridge.evaluation.scoring import score_pilot

    rows, evaluator, mappings = fixtures()
    original = score_pilot(rows, evaluator, mappings, expected_conditions=[("E4", "S1")])[0]
    assert original["selective_accuracy"] == 1.0
    assert original["coverage"] == 0.25
