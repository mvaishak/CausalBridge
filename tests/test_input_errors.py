import json

import pytest
from pydantic import ValidationError

from causalbridge.cli import main
from causalbridge.schemas import RuntimeCase


@pytest.mark.parametrize("raw", [[], None, "row", 42])
def test_benchmark_projection_requires_object_root(raw):
    with pytest.raises(ValueError, match="JSON object"):
        RuntimeCase.from_benchmark(raw)


def test_rejected_nested_oracle_values_never_appear_in_validation_errors(toy):
    raw = toy.model_dump(mode="json")
    raw["visible_cpts"][0]["hidden_cpts"] = {"target_value": "HIDDEN-SECRET"}
    with pytest.raises(ValidationError) as error:
        RuntimeCase.from_benchmark(raw)
    assert "HIDDEN-SECRET" not in str(error.value)
    assert "hidden_cpts" in str(error.value)


def test_cli_keeps_processing_bad_benchmark_rows_without_logging_rejected_values(toy, tmp_path):
    source, output = tmp_path / "bad.jsonl", tmp_path / "out.jsonl"
    raw = toy.model_dump(mode="json")
    raw["visible_cpts"][0]["hidden_cpts"] = {"target_value": "HIDDEN-SECRET"}
    source.write_text("[]\nnull\n" + json.dumps(raw) + "\n")
    assert main(["run", "--input", str(source), "--output", str(output), "--benchmark-rows"]) == 1
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == 3
    assert all(r["verdict"]["reason_code"] == "invalid_input" for r in records)
    assert "HIDDEN-SECRET" not in output.read_text()
