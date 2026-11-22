"""Recount raw model responses independently of stored prediction/metric fields."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from causalbridge.discovery.schemas import DirectionPrediction, canonical_digest
from causalbridge.llm.parser import parse_json

ROOT = Path("runs/qwen3-thinking-ablation-8192-4096-01")
NAME = "qwen3-thinking-ablation-8192-4096-01"


def main():
    manifest = json.loads((ROOT / "full/manifest.json").read_text())
    assert (
        hashlib.sha256(Path("scripts/qwen3_thinking_ablation.py").read_bytes()).hexdigest()
        == manifest["runner_sha256"]
    )
    assert (
        hashlib.sha256(
            Path("artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip").read_bytes()
        ).hexdigest()
        == manifest["archive_sha256"]
    )
    for name, digest in manifest["source_sha256"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    rows = json.loads((ROOT / "full-case-results.json").read_text())
    metrics = json.loads((ROOT / "full-analysis.json").read_text())
    ids = set()
    pairs = defaultdict(list)
    counts = defaultdict(Counter)
    for r in rows:
        assert r["observation_id"] not in ids
        ids.add(r["observation_id"])
        assert r["model_digest"] == manifest["model_digest"]
        body = json.loads(r["raw_response"])
        assert body["model"] == "qwen3:8b"
        assert body["eval_count"] == r["generated_tokens"]
        assert body["prompt_eval_count"] == r["prompt_tokens"]
        assert body["message"].get("thinking") == r["thinking"]
        assert (body["done_reason"] == "length") == r["truncated"]
        req = r["request"]
        assert req["options"] == {
            "temperature": 0,
            "seed": 261,
            "num_ctx": 8192,
            "num_predict": 4096,
        }
        assert canonical_digest(req).split(":")[-1] == r["observation_id"]
        p = None
        if body["done"] and not r["truncated"]:
            p = parse_json(body["message"]["content"], DirectionPrediction)
            assert p.case_id == r["case_id"] and p.package_digest == r["package_digest"]
        category = (
            "failures"
            if p is None
            else "abstain"
            if p.abstained
            else "correct"
            if p.predicted_direction == r["gold"]
            else "wrong"
        )
        for package in ("ALL", r["package"]):
            counts[r["style"], r["think"], package][category] += 1
        key = r["case_id"], r["package"], r["style"]
        pairs[key].append(r)
    for m in metrics["summary"]:
        c = counts[m["style"], m["think"], m["package"]]
        for category in ("correct", "wrong", "abstain", "failures"):
            assert c[category] == m[category]
    for pair in pairs.values():
        assert len(pair) == 2 and {r["think"] for r in pair} == {False, True}
        a, b = [dict(r["request"]) for r in pair]
        a.pop("think")
        b.pop("think")
        assert a == b
    assert len(ids) == 272 and len(pairs) == 136
    path = Path("docs/reviews/" + NAME + ".validation.json")
    validation = json.loads(path.read_text())
    validation.update(
        independent_raw_recount_passed=True,
        frozen_source_hashes_passed=True,
        unique_observations=272,
        matched_input_identities=136,
        thinking_on_with_reasoning=sum(bool(r["thinking"]) for r in rows if r["think"]),
        thinking_off_with_reasoning=sum(bool(r["thinking"]) for r in rows if not r["think"]),
        nonempty_claim_proposals=sum(
            bool(r["prediction"] and r["prediction"]["claims"]) for r in rows
        ),
        separate_thinking_token_counts_exposed=False,
    )
    path.write_text(json.dumps(validation, indent=2) + "\n")
    print("Raw recount, identities, budgets, source hashes and request matches passed")


if __name__ == "__main__":
    main()
