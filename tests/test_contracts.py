import pytest

from causalbridge.llm.tool_planner import plan_request
from causalbridge.schemas import Proposal, Query, RuntimeCase, ToolResult
from causalbridge.tools.reference import ReferenceBackend
from causalbridge.verifier.contracts import check_preconditions, verify


def proposal(query, tool="compute_effect", answer="positive", requested="compute_effect"):
    return Proposal(
        query=query, requested_operation=requested, proposed_tool=tool, proposed_answer=answer
    )


def check(case, query, candidate, value):
    request = plan_request(query, candidate, case)
    result = ToolResult(request=request, value=value)
    return verify(query, candidate, request, result, case)


def test_correct_effect_verified(toy, query):
    verdict = check(toy, query, proposal(query), 0.4)
    assert (verdict.status, verdict.response_action, verdict.answer) == (
        "verified",
        "answer",
        "positive",
    )


def test_graph_only_effect_abstains(toy, query):
    limited = RuntimeCase.model_validate({**toy.model_dump(), "visible_cpts": []})
    verdict = check(limited, query, proposal(query), 0.4)
    assert verdict.status == "unsupported"
    assert verdict.response_action == "abstain"
    assert verdict.missing_evidence


def test_reachability_true_never_proves_positive_effect(toy, query):
    verdict = check(toy, query, proposal(query, tool="has_directed_path"), True)
    assert verdict.status == "wrong_operation"
    assert verdict.answer is None


def test_no_path_proves_zero_without_tables(toy, query):
    case = RuntimeCase.model_validate({**toy.model_dump(), "graph_edges": [], "visible_cpts": []})
    verdict = check(case, query, proposal(query, "has_directed_path", "zero"), False)
    assert verdict.status == "verified"
    assert verdict.answer == "zero"


def test_no_path_does_not_prove_outcome_probability(toy):
    q = Query(cause="X", outcome="Y", question_type="intervention_probability")
    case = RuntimeCase.model_validate({**toy.model_dump(), "graph_edges": [], "visible_cpts": []})
    verdict = check(case, q, proposal(q, "has_directed_path", 0.0, "compute_intervention"), False)
    assert verdict.status == "wrong_operation"


@pytest.mark.parametrize("answer", ["negative", "zero", True, 0.4, None])
def test_incorrect_answer_type_or_sign_rejected(toy, query, answer):
    verdict = check(toy, query, proposal(query, answer=answer), 0.4)
    assert verdict.status == "unsupported"


def test_magnitude_tolerance_does_not_round_sign_to_zero(toy):
    q = Query(cause="X", outcome="Y", question_type="effect_magnitude")
    assert check(toy, q, proposal(q, answer=0.4009), 0.4).status == "verified"
    assert check(toy, q, proposal(q, answer=0.402), 0.4).status == "unsupported"
    sign = Query(cause="X", outcome="Y", question_type="effect_direction")
    assert check(toy, sign, proposal(sign, answer="positive"), 0.0001).status == "verified"


def test_reversed_contrast_keeps_treatment_roles(toy):
    q = Query(cause="X", outcome="Y", question_type="effect_direction", from_value=1, to_value=0)
    request = plan_request(q, proposal(q, answer="negative"), toy)
    result = ReferenceBackend().execute(request, toy)
    assert result.value == pytest.approx(-0.4)
    assert verify(q, proposal(q, answer="negative"), request, result, toy).status == "verified"


def test_query_substitution_rejected_before_execution(toy, query):
    other = Query(cause="Y", outcome="X", question_type="effect_direction")
    with pytest.raises(ValueError, match="query"):
        plan_request(query, proposal(other), toy)


def test_wrong_requested_operation_rejected(toy, query):
    verdict = check(toy, query, proposal(query, requested="has_directed_path"), 0.4)
    assert verdict.status == "wrong_operation"


def test_stale_result_rejected(toy, query):
    p = proposal(query)
    request = plan_request(query, p, toy)
    stale = request.model_copy(update={"evidence_digest": "another-case"})
    verdict = verify(query, p, request, ToolResult(request=stale, value=0.4), toy)
    assert verdict.status == "execution_error"
    assert verdict.reason_code == "result_binding_mismatch"


def test_boolean_result_cannot_be_interpreted_as_numeric_effect(toy, query):
    assert check(toy, query, proposal(query), True).status == "execution_error"


def test_missing_assumptions_rejected(toy, query):
    case = RuntimeCase.model_validate({**toy.model_dump(), "assumptions": None})
    assert check(case, query, proposal(query), 0.4).reason_code == "missing_evidence"


def test_partial_cpts_are_not_sufficient_for_v1_numeric_tool(toy, query):
    case = RuntimeCase.model_validate({**toy.model_dump(), "visible_cpts": [toy.visible_cpts[1]]})
    request = plan_request(query, proposal(query), case)
    assert check_preconditions(request, case) == ("complete_visible_cpts",)


def test_backend_error_is_execution_failure(toy, query):
    p = proposal(query)
    request = plan_request(query, p, toy)
    verdict = verify(
        query, p, request, ToolResult(request=request, error="engine unavailable"), toy
    )
    assert verdict.status == "execution_error"


def test_model_abstention_has_distinct_reason(toy, query):
    p = Proposal(
        query=query,
        requested_operation="compute_effect",
        proposed_tool="compute_effect",
        response_action="abstain",
    )
    assert check(toy, query, p, 0.4).reason_code == "model_abstention"
