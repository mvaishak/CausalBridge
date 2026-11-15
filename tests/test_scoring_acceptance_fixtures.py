"""Exact arithmetic checks on an external scorer's hand-calculated oracle.

No production scorer or bootstrap estimator is implemented here. These checks
validate the fixture handed to the scorer owner, including paired resample data.
"""

import json
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).parent / "fixtures/track_b_scoring"
ROWS = json.loads((ROOT / "joined_rows.json").read_text())
ORACLE = json.loads((ROOT / "expected.json").read_text())
RATES = ("coverage", "correct_yield", "wrong_yield", "selective_accuracy")


def cell(rows, package, condition):
    return [r for r in rows if r["package"] == package and r["condition"] == condition]


def exact_totals(rows):
    # Test-only arithmetic, independent of any eventual scorer implementation.
    total = sum(Fraction(r["weight"]) for r in rows)
    correct = sum(Fraction(r["weight"]) for r in rows if r["reference_agreement"] is True)
    wrong = sum(Fraction(r["weight"]) for r in rows if r["reference_agreement"] is False)
    answered = correct + wrong
    return dict(
        eligible_weight=total,
        answer_weight=answered,
        correct_weight=correct,
        wrong_weight=wrong,
        coverage=answered / total,
        correct_yield=correct / total,
        wrong_yield=wrong / total,
        selective_accuracy=correct / answered if answered else None,
    )


def assert_expected(rows, expected):
    actual = exact_totals(rows)
    for name, value in expected.items():
        assert actual[name] == (Fraction(value) if value is not None else None), name


def validate_fixture(rows):
    cases = {r["case_id"]: r for r in ORACLE["cases"]}
    planned = {
        (c, p, k)
        for c in cases
        for p in ("E1", "E2", "E3", "E4")
        for k in ("S0", "S1", "S2", "SIMPLE_GATE")
    }
    planned |= {(c, "E4", "ANM_ONLY") for c in cases}
    slots = [(r["case_id"], r["package"], r["condition"]) for r in rows]
    assert len(slots) == len(set(slots)) and set(slots) == planned
    for row in rows:
        case = cases[row["case_id"]]
        assert all(
            row[k] == case[k] for k in ("weight", "source_group", "split", "reference_direction")
        )
        arrow = row["predicted_direction"]
        assert row["reference_agreement"] is (
            None if arrow is None else arrow == row["reference_direction"]
        )
    return rows


def test_complete_fixture_with_fixed_eligible_denominator():
    validate_fixture(ROWS)
    assert len(ROWS) == 136
    assert sum(c["weight"] for c in ORACLE["cases"]) == 16
    assert len({c["source_group"] for c in ORACLE["cases"]}) == 4


@pytest.mark.parametrize("key", list(ORACLE["expected"]))
def test_hand_calculated_weighted_results(key):
    package, condition = key.split("/")
    assert_expected(cell(ROWS, package, condition), ORACLE["expected"][key])


@pytest.mark.parametrize("package", ["E1", "E2", "E3", "E4"])
def test_parent_failure_and_abstention_accounting(package):
    s1 = cell(ROWS, package, "S1")
    for stage, weight in ORACLE["expected_failure_weights"].items():
        assert sum(r["weight"] for r in s1 if r["failure_stage"] == stage) == weight
    assert sum(r["weight"] for r in s1 if r["outcome"] == "model_abstention") == 1
    s2 = cell(ROWS, package, "S2")
    assert sum(r["weight"] for r in s2 if r["outcome"] == "parent_prediction_failed") == 7
    assert sum(r["weight"] for r in s2 if r["outcome"] == "fail") == 4
    for row in s2:
        if row["outcome"] in ("parent_prediction_failed", "fail"):
            assert row["predicted_direction"] is None and row["reference_agreement"] is None


def test_wrong_removed_and_correct_suppressed_are_separate():
    s1 = {r["case_id"]: r for r in cell(ROWS, "E4", "S1")}
    removed = [
        r
        for r in cell(ROWS, "E4", "S2")
        if s1[r["case_id"]]["predicted_direction"] is not None and r["predicted_direction"] is None
    ]
    assert sum(r["weight"] for r in removed if s1[r["case_id"]]["reference_agreement"]) == 3
    assert sum(r["weight"] for r in removed if not s1[r["case_id"]]["reference_agreement"]) == 1
    before, after = [exact_totals(cell(ROWS, "E4", c)) for c in ("S1", "S2")]
    assert after["coverage"] <= before["coverage"]
    assert after["correct_yield"] <= before["correct_yield"]
    assert after["wrong_yield"] <= before["wrong_yield"]
    assert after["selective_accuracy"] < before["selective_accuracy"]


@pytest.mark.parametrize("key", ["E4/ANM_ONLY", "E4/SIMPLE_GATE"])
def test_zero_answer_accuracy_is_undefined(key):
    package, condition = key.split("/")
    result = exact_totals(cell(ROWS, package, condition))
    assert result["selective_accuracy"] is None
    assert result["coverage"] == result["correct_yield"] == result["wrong_yield"] == 0
    assert result["eligible_weight"] == 16


@pytest.mark.parametrize(
    "name,left,right",
    [
        ("H1_S0_E3_minus_E2", ("E3", "S0"), ("E2", "S0")),
        ("H1_S1_E3_minus_E2", ("E3", "S1"), ("E2", "S1")),
        ("H2_S0_E4_minus_E3", ("E4", "S0"), ("E3", "S0")),
        ("H2_S1_E4_minus_E3", ("E4", "S1"), ("E3", "S1")),
        ("H3_E4_S2_minus_S1", ("E4", "S2"), ("E4", "S1")),
    ],
)
def test_matched_comparison_oracles(name, left, right):
    a, b = [cell(ROWS, *key) for key in (left, right)]
    assert {(r["case_id"], r["source_group"], r["weight"]) for r in a} == {
        (r["case_id"], r["source_group"], r["weight"]) for r in b
    }
    x, y = exact_totals(a), exact_totals(b)
    for metric, value in ORACLE["comparisons"][name].items():
        assert x[metric] - y[metric] == Fraction(value)


@pytest.mark.parametrize("replicate", ORACLE["source_group_resamples"])
def test_fixed_source_group_resamples_are_paired(replicate):
    multiplicities = Counter(replicate["draw"])
    by_condition = {}
    for condition in ("S1", "S2"):
        source = cell(ROWS, "E4", condition)
        expanded = [
            deepcopy(r) for group in replicate["draw"] for r in source if r["source_group"] == group
        ]
        assert_expected(expanded, replicate[condition])
        assert Counter(r["case_id"] for r in expanded) == Counter(
            {
                r["case_id"]: multiplicities[r["source_group"]]
                for r in source
                if multiplicities[r["source_group"]]
            }
        )
        by_condition[condition] = expanded
    assert Counter(r["case_id"] for r in by_condition["S1"]) == Counter(
        r["case_id"] for r in by_condition["S2"]
    )


def test_process_injections_not_merged_with_runtime_failures():
    expected = ORACLE["injected_process_errors"]
    rejected = [
        r
        for r in cell(ROWS, "E4", "S2")
        if any(code in r["reason_codes"] for code in ("rows_unavailable", "row_unavailable"))
    ]
    assert sum(r["weight"] for r in rejected) == expected["weight"] == 4
    assert Fraction(expected["weight"], expected["eligible_denominator"]) == Fraction(
        expected["rate"]
    )
    assert Fraction(expected["weight"], expected["successful_parent_denominator"]) == Fraction(
        expected["conditional_rate"]
    )
    assert all(r["failure_stage"] is None for r in rejected)


@pytest.mark.parametrize(
    "fault", ["drop_failure", "duplicate", "change_weight", "change_group", "flip_agreement"]
)
def test_corrupted_acceptance_input_is_detected(fault):
    rows = deepcopy(ROWS)
    if fault == "drop_failure":
        rows.remove(next(r for r in rows if r["failure_stage"] == "generate"))
    elif fault == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif fault == "change_weight":
        rows[0]["weight"] = 100
    elif fault == "change_group":
        rows[0]["source_group"] = "different-family"
    else:
        rows[0]["reference_agreement"] = False
    with pytest.raises(AssertionError):
        validate_fixture(rows)


def test_missing_trust_checker_error_and_original_abstention_stay_distinct():
    fixture = json.loads((ROOT / "checker_edge_cases.json").read_text())
    for condition in ("S1", "S2"):
        assert_expected(cell(fixture["rows"], "E4", condition), fixture["expected"][condition])
    outcomes = Counter()
    for row in cell(fixture["rows"], "E4", "S2"):
        category = "pass_without_answer" if row["outcome"] == "pass" else row["outcome"]
        outcomes[category] += row["weight"]
        assert row["predicted_direction"] is None
    assert outcomes == fixture["expected_outcome_weights"]
