"""Descriptive real-test wrapper must refuse configuration changes before fitting."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "validation_test", Path(__file__).parents[1] / "examples/anm_validation_test.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def plan():
    return module.read_json(Path(__file__).parents[1] / "configs/anm-development-large-sample.json")


@pytest.mark.parametrize("fault", ["threshold", "gamma", "size", "splits", "sampling_seed"])
def test_configuration_is_fixed_before_any_data_is_opened(tmp_path, monkeypatch, fault):
    p = plan()
    if fault == "threshold":
        p["threshold"] = 0.01
    elif fault == "gamma":
        p["variants"][1]["kernel_gamma"] = 4.0
    elif fault == "size":
        p["variants"][1]["sample_limit"] = 256
    elif fault == "sampling_seed":
        p["sampling_seed"] = 999
    else:
        p["split_seeds"] = [261, 1261]

    def forbidden(*args, **kwargs):
        pytest.fail("Configuration must fail before data access or numerical execution")

    monkeypatch.setattr(module, "check_roster", forbidden)
    monkeypatch.setattr(module, "_execute", forbidden)
    with pytest.raises(ValueError, match="fixed|predeclared"):
        module.run(tmp_path / "missing", {}, {}, p, tmp_path / "out")
    assert not (tmp_path / "out").exists()
