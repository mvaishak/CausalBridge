"""Bind model-selected operations without silently repairing wrong selections."""

from causalbridge.schemas import Proposal, Query, RuntimeCase, ToolRequest

CANONICAL_OPERATION = {
    "reachability": "has_directed_path",
    "effect_direction": "compute_effect",
    "effect_magnitude": "compute_effect",
    "intervention_probability": "compute_intervention",
    "adjustment_validity": "is_valid_adjustment_set",
}


def plan_request(query: Query, proposal: Proposal, case: RuntimeCase) -> ToolRequest:
    query.bind(case)
    if proposal.query != query:
        raise ValueError("Candidate query does not match parsed query")
    return ToolRequest(
        operation=proposal.proposed_tool, query=query, evidence_digest=case.evidence_digest()
    )
