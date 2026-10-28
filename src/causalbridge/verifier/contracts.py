"""General operation requirements, with no benchmark IDs or gold labels."""

import math

from causalbridge.llm.tool_planner import CANONICAL_OPERATION
from causalbridge.schemas import Proposal, Query, RuntimeCase, ToolRequest, ToolResult, Verdict
from causalbridge.tools.graph import has_path, valid_adjustment


def check_preconditions(request: ToolRequest, case: RuntimeCase) -> tuple[str, ...]:
    query = request.query
    query.bind(case)
    missing = []
    if request.operation in {"compute_effect", "compute_intervention", "backdoor_adjustment"}:
        if case.assumptions is None or not case.assumptions.satisfied():
            missing.append("causal_assumptions")
    if request.operation in {"compute_effect", "compute_intervention"}:
        structural_zero = request.operation == "compute_effect" and not has_path(case, query)
        if not structural_zero and {c.node for c in case.visible_cpts} != set(case.graph_nodes):
            missing.append("complete_visible_cpts")
    if request.operation == "backdoor_adjustment":
        if not valid_adjustment(case, query):
            missing.append("valid_backdoor_adjustment_set")
        required = {query.cause, query.outcome, *query.adjustment_set}
        if case.visible_joint is None or not required <= set(case.visible_joint.variables):
            missing.append("visible_joint_over_cause_outcome_adjustment")
    return tuple(missing)


def abstention(status: str, code: str, explanation: str, missing=()) -> Verdict:
    return Verdict(
        status=status,
        response_action="abstain",
        reason_code=code,
        explanation=explanation,
        missing_evidence=missing,
    )


def check_operation(query: Query, proposal: Proposal, request: ToolRequest) -> Verdict | None:
    """Classify semantic operation mismatches before checking numerical evidence."""
    expected = CANONICAL_OPERATION[query.question_type]
    requested_ok = proposal.requested_operation == expected or (
        query.question_type == "intervention_probability"
        and proposal.requested_operation == "backdoor_adjustment"
    )
    if not requested_ok:
        return abstention(
            "wrong_operation",
            "requested_quantity_mismatch",
            "The requested operation does not compute the question's quantity.",
        )
    effect_query = query.question_type in {"effect_direction", "effect_magnitude"}
    compatible = (
        request.operation == expected
        or (effect_query and request.operation == "has_directed_path")
        or (
            query.question_type == "intervention_probability"
            and request.operation == "backdoor_adjustment"
        )
    )
    if not compatible:
        return abstention(
            "wrong_operation",
            "tool_capability_mismatch",
            "The selected tool cannot establish the requested quantity.",
        )
    return None


def verify(
    query: Query,
    proposal: Proposal,
    request: ToolRequest,
    result: ToolResult,
    case: RuntimeCase,
    *,
    numeric_tolerance: float = 1e-3,
    sign_tolerance: float = 1e-9,
) -> Verdict:
    """Check a trusted tool result; this is not an independent numeric oracle.

    Query binding is checked against the parsed/public query spec. Correct natural
    language parsing and backend computation are explicit trust boundaries.
    """
    if not (
        math.isfinite(numeric_tolerance)
        and numeric_tolerance >= 0
        and math.isfinite(sign_tolerance)
        and sign_tolerance >= 0
    ):
        raise ValueError("Tolerances must be finite and nonnegative")
    try:
        query.bind(case)
    except ValueError:
        return abstention("execution_error", "query_binding_error", "Unknown graph variable.")
    if (
        request.query != query
        or proposal.query != query
        or request.operation != proposal.proposed_tool
        or request.evidence_digest != case.evidence_digest()
    ):
        return abstention(
            "execution_error",
            "request_binding_mismatch",
            "The plan, query, or evidence changed before verification.",
        )
    if result.request != request:
        return abstention(
            "execution_error",
            "result_binding_mismatch",
            "The tool result belongs to a different request or evidence context.",
        )
    operation_error = check_operation(query, proposal, request)
    if operation_error is not None:
        return operation_error
    operation = request.operation
    effect_query = query.question_type in {"effect_direction", "effect_magnitude"}
    missing = check_preconditions(request, case)
    if effect_query and operation == "has_directed_path":
        if case.assumptions is None or not case.assumptions.satisfied():
            missing += ("causal_assumptions",)
    if missing:
        return abstention(
            "unsupported",
            "missing_evidence",
            "The selected operation's evidence requirements are not satisfied.",
            missing,
        )
    if result.error is not None:
        return abstention(
            "execution_error", "tool_execution_error", "The tool failed: " + result.error
        )
    value = result.value
    structural = operation in {"has_directed_path", "is_valid_adjustment_set"}
    if structural:
        if type(value) is not bool:
            return abstention(
                "execution_error", "invalid_tool_result", "Expected a boolean tool result."
            )
        # Independently recheck cheap graph facts; numeric backend remains trusted.
        expected_fact = (
            has_path(case, query)
            if operation == "has_directed_path"
            else valid_adjustment(case, query)
        )
        if value != expected_fact:
            return abstention(
                "execution_error",
                "invalid_tool_result",
                "Tool result contradicts the supplied graph.",
            )
    elif type(value) is not float or not math.isfinite(value):
        return abstention(
            "execution_error", "invalid_tool_result", "Expected a finite numeric tool result."
        )
    elif not (-1 <= value <= 1) or (operation != "compute_effect" and value < 0):
        return abstention(
            "execution_error",
            "invalid_tool_result",
            "Numeric result is outside its permitted range.",
        )
    if effect_query and operation == "has_directed_path":
        if value:
            return abstention(
                "wrong_operation",
                "reachability_does_not_establish_effect",
                "A directed path does not determine an effect's sign or magnitude.",
            )
        value = 0.0
    if proposal.response_action == "abstain":
        return abstention(
            "unsupported",
            "model_abstention",
            "The model abstained; this does not establish that evidence is insufficient.",
        )
    if query.question_type == "effect_direction":
        checked = (
            "zero" if abs(value) <= sign_tolerance else ("positive" if value > 0 else "negative")
        )
        consistent = type(proposal.proposed_answer) is str and proposal.proposed_answer == checked
    elif query.question_type in {"reachability", "adjustment_validity"}:
        checked = value
        consistent = type(proposal.proposed_answer) is bool and proposal.proposed_answer == checked
    else:
        checked = value
        consistent = (
            type(proposal.proposed_answer) is float
            and abs(proposal.proposed_answer - checked) <= numeric_tolerance
        )
    if not consistent:
        return abstention(
            "unsupported",
            "answer_inconsistent_with_result",
            "The proposed answer does not follow from the checked tool result.",
        )
    return Verdict(
        status="verified",
        response_action="answer",
        reason_code="contract_satisfied",
        answer=checked,
        explanation=f"The {operation} result supports {checked} for the bound query.",
    )
