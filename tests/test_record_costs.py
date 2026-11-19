"""Measured resource totals retain unknown values and never double count cached parents."""

from copy import deepcopy

import pytest

from causalbridge.evaluation.record_costs import generation_costs


def events():
    result = []
    for i, latency in enumerate((1.0, 3.0)):
        key = str(i)
        generation = dict(input_tokens=10, output_tokens=5, latency_seconds=latency)
        result.extend(
            [
                {
                    "kind": "native_started",
                    "data": dict(
                        key=key,
                        attempt_id=key,
                        package={"evidence": {"package": "E4"}},
                        condition={"condition_id": "S1"},
                    ),
                },
                {"kind": "native_generated", "data": dict(key=key, generation=generation)},
                {
                    "kind": "native_finished",
                    "data": dict(
                        key=key,
                        execution={
                            "generation": deepcopy(generation),
                            "failure_stage": None,
                        },
                    ),
                },
            ]
        )
    return result


def test_unique_generations_not_resume_or_s2_copies_are_summed():
    source = events()
    expected = generation_costs(source)
    source.extend(
        [
            {"kind": "native_released", "data": {"generation": {"input_tokens": 99999}}},
            {"kind": "invocation_summary", "data": {"historical_usage": {"input_tokens": 20}}},
        ]
    )
    assert generation_costs(source) == expected
    cell = expected[0]
    assert cell["input_tokens"]["total"] == 20
    assert cell["output_tokens"]["total"] == 10
    assert cell["generation_latency_seconds"]["total"] == 4
    assert cell["median_generation_latency_seconds"] == 2
    assert cell["p95_generation_latency_seconds"] == pytest.approx(2.9)
    assert cell["measured_monetary_cost"] is None


def test_unknown_usage_is_not_zero_or_a_complete_total():
    source = events()
    source[1]["data"]["generation"]["input_tokens"] = None
    source[2]["data"]["execution"]["generation"]["input_tokens"] = None
    cell = generation_costs(source)[0]
    assert cell["input_tokens"] == {"total": None, "known_total": 10, "missing_count": 1}


def test_missing_generation_failure_has_unknown_usage_and_recorded_failure():
    source = events()[:3]
    source.pop(1)
    source[-1]["data"]["execution"] = {"generation": None, "failure_stage": "generate"}
    cell = generation_costs(source)[0]
    assert cell["input_tokens"]["total"] is None
    assert cell["observed_generation_records"] == 0
    assert cell["failure_stage_counts"] == {"generate": 1}


@pytest.mark.parametrize(
    "value,field",
    [
        (-1, "input_tokens"),
        (True, "output_tokens"),
        (1.5, "input_tokens"),
        (float("nan"), "latency_seconds"),
    ],
)
def test_invalid_measurement_fails(value, field):
    source = events()
    source[1]["data"]["generation"][field] = value
    source[2]["data"]["execution"]["generation"][field] = value
    with pytest.raises(ValueError):
        generation_costs(source)


@pytest.mark.parametrize("fault", ["duplicate", "missing_finish", "changed_copy", "same_attempt"])
def test_corrupted_receipt_accounting_fails(fault):
    source = events()
    if fault == "duplicate":
        source.append(deepcopy(source[1]))
    elif fault == "missing_finish":
        source.pop()
    elif fault == "changed_copy":
        source[2]["data"]["execution"]["generation"]["input_tokens"] = 40
    else:
        source[3]["data"]["attempt_id"] = source[0]["data"]["attempt_id"]
    with pytest.raises(ValueError):
        generation_costs(source)
