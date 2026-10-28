import pytest
from pydantic import ValidationError

from causalbridge.schemas import Query, RuntimeCase


def visible(**updates):
    return dict(
        case_id="toy",
        graph_nodes=["X", "Y"],
        graph_edges=[["X", "Y"]],
        question="Does increasing X increase Y?",
        **updates,
    )


def test_benchmark_projection_excludes_all_oracle_fields():
    case = RuntimeCase.from_benchmark(
        {
            **visible(),
            "answerable": False,
            "gold_response": "positive",
            "hidden_cpts": {"secret": 1},
            "target_value": 0.4,
            "witness_pair_id": "W001",
            "query_type": "effect_direction",
        }
    )
    assert "gold" not in case.model_dump_json()
    assert "secret" not in case.model_dump_json()
    assert "answerable" not in case.model_dump_json()


def test_runtime_boundary_rejects_oracle_fields():
    with pytest.raises(ValidationError):
        RuntimeCase.model_validate({**visible(), "answerable": False})


@pytest.mark.parametrize(
    "updates",
    [
        {"graph_edges": [["X", "Y"], ["Y", "X"]]},
        {"graph_edges": [["X", "Z"]]},
        {"graph_nodes": ["X", "X"]},
        {"visible_cpts": [{"node": "Y", "parents": ["X"], "p_one": {"0": 0.3}}]},
        {"visible_cpts": [{"node": "Y", "parents": [], "p_one": {"": 0.3}}]},
        {"visible_cpts": [{"node": "X", "parents": [], "p_one": {"": float("nan")}}]},
    ],
)
def test_invalid_evidence_rejected(updates):
    with pytest.raises(ValidationError):
        RuntimeCase.model_validate({**visible(), **updates})


def test_isolated_nodes_and_partial_tables_are_representable():
    case = RuntimeCase.model_validate(
        visible(visible_cpts=[{"node": "Y", "parents": ["X"], "p_one": {"0": 0.3, "1": 0.7}}])
    )
    assert case.visible_cpts[0].node == "Y"
    isolated = RuntimeCase.model_validate({**visible(), "graph_edges": []})
    assert isolated.graph_nodes == ("X", "Y")


@pytest.mark.parametrize(
    "updates",
    [
        {"cause": "Y"},
        {"from_value": True},
        {"to_value": 2},
        {"to_value": 0},
        {"conditioning": {"Z": 1}},
    ],
)
def test_invalid_or_unsupported_query_rejected(updates):
    payload = dict(cause="X", outcome="Y", question_type="effect_direction")
    with pytest.raises(ValidationError):
        Query.model_validate({**payload, **updates})


def test_digest_tracks_evidence_and_is_stable():
    case = RuntimeCase.model_validate(visible())
    assert case.evidence_digest() == RuntimeCase.model_validate(visible()).evidence_digest()
    assert (
        case.evidence_digest()
        != RuntimeCase.model_validate({**visible(), "graph_edges": []}).evidence_digest()
    )
