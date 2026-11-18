"""Exploratory adequacy checks: exact permutation accounting and saved artifacts."""

import importlib.util
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

spec = importlib.util.spec_from_file_location(
    "anm_adequacy", Path(__file__).parents[1] / "examples/anm_adequacy.py"
)
adequacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adequacy)


def plan():
    return adequacy.AdequacyPlan(
        version="exploratory-hsic-adequacy-v1",
        permutations=19,
        alpha=0.05,
        seed=1,
        rule="answer_only_when_exactly_one_direction_is_not_rejected",
    )


@pytest.mark.parametrize(
    "rejected,expected",
    [
        ((False, True), "A_to_B"),
        ((True, False), "B_to_A"),
        ((True, True), None),
        ((False, False), None),
    ],
)
def test_unique_nonrejected_direction_only(rejected, expected):
    checks = dict(zip(("A_to_B", "B_to_A"), ({"rejected": x} for x in rejected), strict=True))
    assert adequacy.adequacy_direction(checks)[0] == expected


def test_permutations_are_reproducible_and_use_plus_one_accounting():
    x = np.linspace(-2, 2, 30)
    result = adequacy.permutation_check(x, x, plan(), 71)
    assert result == adequacy.permutation_check(x, x, plan(), 71)
    assert result["pvalue"] == 1 / 20 and result["rejected"]
    assert 1 / 20 <= result["pvalue"] <= 1


def test_product_distribution_hsic_is_zero():
    x = np.array([-1.0, -1.0, 1.0, 1.0])
    y = np.array([-1.0, 1.0, -1.0, 1.0])
    r = adequacy.permutation_check(x, y, plan(), 11)
    assert abs(r["score"]) < 1e-14
    assert not r["rejected"]


@pytest.mark.parametrize("values", [[1.0, 1.0], [1.0, float("nan")]])
def test_undefined_inputs_fail_explicitly(values):
    with pytest.raises(ValueError):
        adequacy.centered_kernel(values)


def test_typed_original_method_errors_are_not_independence_passes(tmp_path):
    from causalbridge.discovery.anm import execute_anm_request
    from causalbridge.discovery.anm_requests import save_anm_request

    path = tmp_path / "constant"
    save_anm_request([[1.0, 2.0]] * 100, case_id="D0001", ab_mapping_id="map", directory=path)
    execute_anm_request(path)
    result = adequacy.diagnose_attempt(path, plan(), "constant")
    assert result == dict(direction=None, reason="original_method_error", checks=None)
