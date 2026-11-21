"""Freeze request identity and prevent hidden budget/prompt differences."""

import importlib.util
from pathlib import Path

from causalbridge.discovery.schemas import canonical_digest

spec = importlib.util.spec_from_file_location(
    "ablation", Path("scripts/qwen3_thinking_ablation.py")
)
ablation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ablation)


def test_original_schedule_complete_and_distinct():
    starts, ends, digest = ablation.source()
    assert len(starts) == 136
    keys = [
        (
            s["package"]["evidence"]["case_id"],
            s["package"]["evidence"]["package"],
            s["condition"]["condition_id"],
        )
        for s in starts
    ]
    assert len(set(keys)) == 136
    assert len({k[0] for k in keys}) == 17
    assert all(s["key"] in ends for s in starts)
    assert len(digest) == 64


def test_original_requests_match_evidence_digest():
    starts, _, _ = ablation.source()
    for s in starts:
        assert canonical_digest(s["package"]["evidence"]) == s["receipt"]["package_digest"]
        assert s["config"]["think"] is False
        assert s["config"]["context_tokens"] == 4096
        assert s["config"]["max_tokens"] == 512
