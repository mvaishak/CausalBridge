import pytest

from causalbridge.schemas import Query, RuntimeCase, ToolRequest
from causalbridge.tools.reference import ReferenceBackend, valid_adjustment
from causalbridge.verifier.contracts import check_preconditions


def run(case, q, op):
    request = ToolRequest(query=q, operation=op, evidence_digest=case.evidence_digest())
    return ReferenceBackend().execute(request, case)


def test_intervention_and_effect_hand_calculations(toy):
    q = Query(cause="X", outcome="Y", question_type="intervention_probability")
    assert run(toy, q, "compute_intervention").value == pytest.approx(0.7)
    assert run(toy, q, "compute_effect").value == pytest.approx(0.4)


def test_mediation_enumeration(assumptions):
    case = RuntimeCase.model_validate(
        dict(
            case_id="chain",
            graph_nodes=["X", "M", "Y"],
            graph_edges=[["X", "M"], ["M", "Y"]],
            question="Effect?",
            assumptions=assumptions,
            visible_cpts=[
                {"node": "X", "p_one": {"": 0.5}},
                {"node": "M", "parents": ["X"], "p_one": {"0": 0.2, "1": 0.8}},
                {"node": "Y", "parents": ["M"], "p_one": {"0": 0.1, "1": 0.9}},
            ],
        )
    )
    q = Query(cause="X", outcome="Y", question_type="effect_magnitude")
    assert run(case, q, "compute_effect").value == pytest.approx(0.48)
    assert not valid_adjustment(case, q.model_copy(update={"adjustment_set": ("M",)}))


@pytest.fixture
def confounded(assumptions):
    # Z~.5; X|Z=(.2,.8); Y|X,Z=(.1,.5,.4,.8), parent order X,Z.
    # do(X=1): .5*.4+.5*.8=.6; P(Y=1|X=1)=.72.
    return RuntimeCase.model_validate(
        dict(
            case_id="confounded",
            graph_nodes=["Z", "X", "Y"],
            graph_edges=[["Z", "X"], ["Z", "Y"], ["X", "Y"]],
            question="P(Y=1|do(X=1))?",
            assumptions=assumptions,
            visible_joint={
                "variables": ["Z", "X", "Y"],
                "probabilities": {
                    "000": 0.36,
                    "001": 0.04,
                    "010": 0.06,
                    "011": 0.04,
                    "100": 0.05,
                    "101": 0.05,
                    "110": 0.08,
                    "111": 0.32,
                },
            },
        )
    )


def test_backdoor_adjustment_uses_joint_not_observational_conditional(confounded):
    q = Query(
        cause="X", outcome="Y", question_type="intervention_probability", adjustment_set=("Z",)
    )
    assert valid_adjustment(confounded, q)
    assert run(confounded, q, "backdoor_adjustment").value == pytest.approx(0.6)
    empty = q.model_copy(update={"adjustment_set": ()})
    request = ToolRequest(
        query=empty, operation="backdoor_adjustment", evidence_digest=confounded.evidence_digest()
    )
    assert "valid_backdoor_adjustment_set" in check_preconditions(request, confounded)


def test_confounded_xy_marginal_cannot_answer_intervention(confounded):
    case = RuntimeCase.model_validate(
        {
            **confounded.model_dump(),
            "visible_joint": {
                "variables": ["X", "Y"],
                "probabilities": {"00": 0.41, "01": 0.09, "10": 0.14, "11": 0.36},
            },
        }
    )
    q = Query(
        cause="X", outcome="Y", question_type="intervention_probability", adjustment_set=("Z",)
    )
    result = run(case, q, "backdoor_adjustment")
    assert result.error is not None
    assert result.value is None


def test_unconfounded_observation_substitution(toy):
    case = RuntimeCase.model_validate(
        {
            **toy.model_dump(),
            "visible_cpts": [],
            "visible_joint": {
                "variables": ["X", "Y"],
                "probabilities": {"00": 0.35, "01": 0.15, "10": 0.15, "11": 0.35},
            },
        }
    )
    q = Query(cause="X", outcome="Y", question_type="intervention_probability")
    assert run(case, q, "backdoor_adjustment").value == pytest.approx(0.7)


def test_collider_adjustment_is_invalid(assumptions):
    case = RuntimeCase.model_validate(
        dict(
            case_id="collider",
            graph_nodes=["X", "Y", "Z"],
            graph_edges=[["X", "Z"], ["Y", "Z"]],
            question="Adjustment?",
            assumptions=assumptions,
        )
    )
    q = Query(cause="X", outcome="Y", question_type="adjustment_validity", adjustment_set=("Z",))
    assert not valid_adjustment(case, q)
    assert run(case, q, "is_valid_adjustment_set").value is False


def test_reference_refuses_wrong_evidence_digest(toy):
    q = Query(cause="X", outcome="Y", question_type="effect_magnitude")
    request = ToolRequest(query=q, operation="compute_effect", evidence_digest="stale")
    assert run(toy, q, "compute_effect").value == pytest.approx(0.4)
    assert ReferenceBackend().execute(request, toy).error is not None
