"""Hand-authored integration fixtures. These are NOT LLM experiment results."""

from collections.abc import Iterator

from causalbridge.llm.client import Generation
from causalbridge.pipeline import CausalBridge, RunTrace
from causalbridge.schemas import Assumptions, Proposal, Query, RuntimeCase
from causalbridge.tools.reference import ReferenceBackend


class FixtureModel:
    """Replay explicitly labeled fixture JSON through the real parser/pipeline."""

    def __init__(self, responses: list[str]):
        self.responses = iter(responses)

    def generate(self, messages: list[dict[str, str]], schema: dict) -> Generation:
        return Generation(text=next(self.responses), model="hand_authored_fixture")


def demo_runs() -> Iterator[RunTrace]:
    assumptions = Assumptions(
        correct_dag=True, fully_observed=True, independent_noise=True, positivity=True
    )
    toy = RuntimeCase.model_validate(
        dict(
            case_id="toy_complete",
            graph_group_id="demo_toy",
            graph_nodes=["X", "Y"],
            graph_edges=[["X", "Y"]],
            question="Does increasing X increase Y?",
            assumptions=assumptions,
            visible_cpts=[
                {"node": "X", "p_one": {"": 0.5}},
                {"node": "Y", "parents": ["X"], "p_one": {"0": 0.3, "1": 0.7}},
            ],
        )
    )
    direction = Query(cause="X", outcome="Y", question_type="effect_direction")
    probability = Query(cause="X", outcome="Y", question_type="intervention_probability")
    limited = RuntimeCase.model_validate(
        {**toy.model_dump(), "case_id": "toy_graph_only", "visible_cpts": []}
    )
    disconnected = RuntimeCase.model_validate(
        {**limited.model_dump(), "case_id": "no_path_zero", "graph_edges": []}
    )
    decreasing = Query(
        cause="X", outcome="Y", question_type="effect_direction", from_value=1, to_value=0
    )
    reduced = RuntimeCase.model_validate(
        {
            **toy.model_dump(),
            "case_id": "decreasing_treatment",
            "question": "Does reducing X increase Y?",
        }
    )
    confounded = RuntimeCase.model_validate(
        dict(
            case_id="valid_backdoor",
            graph_group_id="demo_zxy",
            graph_nodes=["Z", "X", "Y"],
            graph_edges=[["Z", "X"], ["Z", "Y"], ["X", "Y"]],
            question="What is P(Y=1|do(X=1))?",
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
    adjusted = Query(
        cause="X", outcome="Y", question_type="intervention_probability", adjustment_set=("Z",)
    )
    marginal = RuntimeCase.model_validate(
        {
            **confounded.model_dump(),
            "case_id": "xy_only_confounded",
            "visible_joint": {
                "variables": ["X", "Y"],
                "probabilities": {"00": 0.41, "01": 0.09, "10": 0.14, "11": 0.36},
            },
        }
    )
    scenarios = [
        (toy, direction, "compute_effect", "compute_effect", "positive"),
        (limited, direction, "compute_effect", "compute_effect", "positive"),
        (
            RuntimeCase.model_validate({**limited.model_dump(), "case_id": "path_sign_mismatch"}),
            direction,
            "compute_effect",
            "has_directed_path",
            "positive",
        ),
        (disconnected, direction, "compute_effect", "has_directed_path", "zero"),
        (reduced, decreasing, "compute_effect", "compute_effect", "negative"),
        (confounded, adjusted, "compute_intervention", "backdoor_adjustment", 0.6),
        (marginal, adjusted, "compute_intervention", "backdoor_adjustment", 0.72),
        (
            RuntimeCase.model_validate(
                {
                    **toy.model_dump(),
                    "case_id": "incorrect_probability",
                    "question": "What is P(Y=1|do(X=1))?",
                }
            ),
            probability,
            "compute_intervention",
            "compute_intervention",
            0.9,
        ),
    ]
    for case, query, required, tool, answer in scenarios:
        plan = Proposal(query=query, requested_operation=required, proposed_tool=tool)
        final = Proposal(
            query=query, requested_operation=required, proposed_tool=tool, proposed_answer=answer
        )
        model = FixtureModel(
            [query.model_dump_json(), plan.model_dump_json(), final.model_dump_json()]
        )
        yield CausalBridge(model, ReferenceBackend(), model_mode="scripted_fixture").run(case)
