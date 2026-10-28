import pytest

from causalbridge.schemas import Assumptions, Query, RuntimeCase


@pytest.fixture
def assumptions():
    return Assumptions(
        correct_dag=True, fully_observed=True, independent_noise=True, positivity=True
    )


@pytest.fixture
def toy(assumptions):
    return RuntimeCase.model_validate(
        dict(
            case_id="toy",
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


@pytest.fixture
def query():
    return Query(cause="X", outcome="Y", question_type="effect_direction")
