"""Frozen paired thinking experiment using exact archived pilot requests."""

import argparse
import hashlib
import json
import time
import zipfile
from pathlib import Path

import httpx

from causalbridge.discovery.schemas import DirectionEvidence, DirectionPrediction, canonical_digest
from causalbridge.llm.parser import parse_json
from causalbridge.verifier.bindings import VerificationContext
from causalbridge.verifier.checks import check_prediction

ROOT = Path("runs/qwen3-thinking-ablation-8192-4096-01")
DIGEST = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
URL = "http://127.0.0.1:11435"


def save(path, obj):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def source():
    archive = Path("artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip")
    with zipfile.ZipFile(archive) as z:
        events = [
            json.loads(x) for x in z.read("real-pilot-01/experiment/events.jsonl").splitlines()
        ]
    starts = [e["data"] for e in events if e["kind"] == "native_started"]
    ends = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_finished"}
    return starts, ends, hashlib.sha256(archive.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["activation", "preflight", "full"], required=True)
    args = ap.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    starts, ends, archive_hash = source()
    starts.sort(
        key=lambda s: (
            s["package"]["evidence"]["case_id"],
            s["package"]["evidence"]["package"],
            s["condition"]["condition_id"],
        )
    )
    with httpx.Client(timeout=900, trust_env=False) as client:
        tags = client.get(URL + "/api/tags").json()
        assert next(m for m in tags["models"] if m["name"] == "qwen3:8b")["digest"] == DIGEST
        save(
            ROOT / ("infrastructure-" + args.phase + ".json"),
            {
                "tags": tags,
                "version": client.get(URL + "/api/version").json(),
                "ps": client.get(URL + "/api/ps").json(),
            },
        )
        if args.phase == "full":
            gate = json.loads((ROOT / "preflight-gate.json").read_text())
            assert gate["passed"], "Preflight must pass before full experiment"
        cases = sorted({s["package"]["evidence"]["case_id"] for s in starts})[:2]
        selected = (
            starts
            if args.phase == "full"
            else [
                s
                for s in starts
                if s["package"]["evidence"]["case_id"] in cases
                and s["package"]["evidence"]["package"] in ("E1", "E4")
            ]
        )
        if args.phase == "activation":
            selected = selected[:1]
        folder = ROOT / args.phase
        folder.mkdir(exist_ok=True)
        manifest = {
            "phase": args.phase,
            "archive_sha256": archive_hash,
            "model_digest": DIGEST,
            "context": 8192,
            "output": 4096,
            "temperature": 0,
            "seed": 261,
            "pairs": [s["key"] for s in selected],
            "order": "sorted inputs; alternate off-first/on-first by input index",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_sha256": {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path("src/causalbridge").rglob("*.py"))
            },
        }
        if (folder / "manifest.json").exists():
            assert json.loads((folder / "manifest.json").read_text()) == manifest
        else:
            save(folder / "manifest.json", manifest)
        records = []
        for i, start in enumerate(selected):
            for think in [False, True] if i % 2 == 0 else [True, False]:
                payload = {
                    "model": "qwen3:8b",
                    "messages": start["messages"],
                    "format": start["output_schema"],
                    "stream": False,
                    "think": think,
                    "options": {
                        "temperature": 0,
                        "seed": 261,
                        "num_ctx": 8192,
                        "num_predict": 4096,
                    },
                }
                identity = canonical_digest(payload).split(":")[-1]
                path = folder / (identity + ".json")
                if path.exists():
                    records.append(json.loads(path.read_text()))
                    continue
                rec = {
                    "observation_id": identity,
                    "case_id": start["package"]["evidence"]["case_id"],
                    "package": start["package"]["evidence"]["package"],
                    "style": start["condition"]["condition_id"],
                    "think": think,
                    "model_digest": DIGEST,
                    "request": payload,
                    "prompt_digest": canonical_digest(start["messages"]),
                    "package_digest": start["receipt"]["package_digest"],
                    "prediction": None,
                    "checker": None,
                    "failure": None,
                    "thinking_token_count": None,
                }
                save(folder / (identity + ".request.json"), rec)
                begin = time.perf_counter()
                try:
                    response = client.post(URL + "/api/chat", json=payload)
                    rec["http_status"] = response.status_code
                    rec["raw_response"] = response.text
                    response.raise_for_status()
                    body = response.json()
                    if body.get("model") != "qwen3:8b":
                        raise ValueError("response_model_mismatch")
                    rec["thinking"] = body.get("message", {}).get("thinking")
                    rec["final_content"] = body.get("message", {}).get("content")
                    rec["truncated"] = body.get("done_reason") == "length"
                    rec["prompt_tokens"] = body.get("prompt_eval_count")
                    rec["generated_tokens"] = body.get("eval_count")
                    if body.get("done") is not True or rec["truncated"]:
                        raise ValueError("incomplete_or_truncated")
                    prediction = parse_json(rec["final_content"], DirectionPrediction)
                    evidence = DirectionEvidence.model_validate(start["package"]["evidence"])
                    if (
                        prediction.case_id != evidence.case_id
                        or prediction.package_digest != evidence.package_digest
                    ):
                        raise ValueError("prediction_binding_failure")
                    rec["prediction"] = prediction.model_dump(mode="json")
                    ctx = VerificationContext.model_validate(
                        ends[start["key"]]["context"]
                    ).model_copy(update={"proposal_digest": prediction.proposal_digest})
                    rec["checker"] = check_prediction(evidence, prediction, context=ctx).model_dump(
                        mode="json"
                    )
                except Exception as exc:
                    rec["failure"] = type(exc).__name__ + ": " + str(exc)
                rec["latency_seconds"] = time.perf_counter() - begin
                save(path, rec)
                records.append(rec)
                print(
                    args.phase,
                    rec["case_id"],
                    rec["package"],
                    rec["style"],
                    think,
                    rec["failure"],
                    bool(rec.get("thinking")),
                    rec.get("generated_tokens"),
                    flush=True,
                )
        if args.phase in ("activation", "preflight"):
            on = [r for r in records if r["think"]]
            gate = {
                "passed": all(not r["failure"] for r in records)
                and all(bool(r.get("thinking")) for r in on),
                "observations": len(records),
                "matched_inputs": len(selected),
                "failures": sum(bool(r["failure"]) for r in records),
                "thinking_on_with_separate_reasoning": sum(bool(r.get("thinking")) for r in on),
                "thinking_on_count": len(on),
                "truncated": sum(bool(r.get("truncated")) for r in records),
            }
            save(ROOT / (args.phase + "-gate.json"), gate)
            print(json.dumps(gate), flush=True)


if __name__ == "__main__":
    main()
