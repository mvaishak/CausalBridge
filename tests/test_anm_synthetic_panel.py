"""Fixed synthetic schedule and full reporting, including controls and abstentions."""

import importlib.util
from collections import Counter
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
spec = importlib.util.spec_from_file_location(
    "synthetic_panel", Path(__file__).parents[1] / "examples/anm_synthetic_panel.py"
)
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


def plan():
    return panel.Plan.model_validate(
        panel.read_json(Path(__file__).parents[1] / "configs/anm-synthetic-panel.json")
    )


def test_schedule_is_balanced_and_has_independent_seeds():
    rows = panel.cases(plan())
    assert len(rows) == 88
    assert len({c["seed"] for c in rows}) == 88
    assert Counter(c["partition"] for c in rows) == {"development": 44, "confirmation": 44}
    assert Counter(c["construction_direction"] for c in rows) == {"A_to_B": 44, "B_to_A": 44}
    assert sum(c["compatible"] for c in rows) == 64
    assert {c["seed"] for c in rows if c["partition"] == "development"}.isdisjoint(
        c["seed"] for c in rows if c["partition"] == "confirmation"
    )


def test_generators_are_deterministic_and_swap_columns_without_reordering_rows():
    for case in panel.cases(plan()):
        rows = np.array(panel.generate(case, 512))
        assert rows.shape == (512, 2) and np.isfinite(rows).all()
        assert np.array_equal(rows, np.array(panel.generate(case, 512)))
        reverse = case | {
            "construction_direction": "B_to_A"
            if case["construction_direction"] == "A_to_B"
            else "A_to_B"
        }
        assert np.array_equal(rows[:, ::-1], panel.generate(reverse, 512))


def test_no_answer_accuracy_and_errors_remain_in_denominators():
    rows = [
        dict(direction=None, reference="A_to_B", status="ok"),
        dict(direction=None, reference="B_to_A", status="error"),
    ]
    m = panel.metrics(rows)
    assert m["cases"] == 2 and m["errors"] == 1 and m["abstained"] == 1
    assert m["answer_accuracy"] is None and m["correct_yield"] == m["wrong_yield"] == 0


def test_confirmation_gate_does_not_hide_bad_families_or_score_controls():
    p = plan()
    records = []
    for case in panel.cases(p):
        for n in p.sample_sizes:
            for split in p.split_seeds:
                reference = case["construction_direction"] if case["compatible"] else None
                direction = case["construction_direction"]
                if case["family"] == "sine":
                    direction = "B_to_A" if direction == "A_to_B" else "A_to_B"
                records.append(
                    case
                    | dict(
                        n=n,
                        split=split,
                        reference=reference,
                        direction=direction,
                        status="ok",
                        swap_passed=True,
                    )
                )
    report = panel.summarize(records, p)
    assert report["demonstration_gate"]["checks"]["accuracy"]
    assert not report["demonstration_gate"]["checks"]["family_accuracy"]
    assert not report["demonstration_gate"]["passed"]
    assert all(
        c["causal_accuracy"] is None for cell in report["cells"] for c in cell["controls"].values()
    )


def test_overwriting_an_existing_run_is_refused(tmp_path):
    with pytest.raises(FileExistsError):
        panel.run(plan(), tmp_path)
