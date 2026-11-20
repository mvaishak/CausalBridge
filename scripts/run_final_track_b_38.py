"""Frozen exploratory 38-pair integrated Track B run; never uses labels in prompts.

The ANM artifacts are the archived PR #15 sample_512 attempts. A scripted
one-case integration check is supported before the full live run. Outputs are
exclusive to a new directory, with durable native inference journals.
"""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from causalbridge.discovery.anm_requests import ANMConfig, read_json
from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.discovery.loader import verify_snapshot_hashes
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows, evaluator_mapping
from causalbridge.evaluation.integration import (
    COMPACT_PROTOCOL,
    IntegratedRunner,
    build_native_packages,
)
from causalbridge.evaluation.integration_demo import ScriptedNativeModel
from causalbridge.evaluation.roster import check_roster
from causalbridge.evaluation.scoring import score_pilot
from causalbridge.evaluation.store import atomic_json
from causalbridge.llm.client import Generation, GenerationFailure, ModelConfig, OllamaModel


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def request_key(messages, schema):
    return canonical_digest({"messages": messages, "schema": schema})


def saved_live_generations(root, config):
    """Read only complete raw responses from the previous pinned live attempt."""
    session = read_json(root / "session.json")
    if session["model_config"] != config.model_dump(mode="json") or session["scripted"]:
        raise ValueError("Replay source is not the same pinned live model configuration")
    events = [
        json.loads(line) for line in (root / "experiment/events.jsonl").read_text().splitlines()
    ]
    starts = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_started"}
    generated = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_generated"}
    finished = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_finished"}
    saved = {}
    for key, start in starts.items():
        if key not in generated or key not in finished:
            continue
        if not finished[key]["execution"] or finished[key]["execution"]["failure_stage"]:
            continue
        generation = Generation.model_validate(generated[key]["generation"])
        if generation.status != "complete" or generation.model != config.model:
            continue
        fingerprint = request_key(start["messages"], start["output_schema"])
        if fingerprint in saved:
            raise ValueError("Duplicate saved live request fingerprint")
        saved[fingerprint] = {"generation": generation, "source_attempt_id": start["attempt_id"]}
    return saved


class ResumableLiveModel:
    """Reuse exact live responses and log bounded retries on transport disconnects."""

    def __init__(self, config, client, saved, log_path):
        self.config = config
        self.model = OllamaModel(config, client=client)
        self.saved = saved
        self.log_path = log_path
        self.replayed = 0
        self.actual = 0

    def _log(self, event):
        with self.log_path.open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def generate(self, messages, schema):
        fingerprint = request_key(messages, schema)
        if fingerprint in self.saved:
            item = self.saved.pop(fingerprint)
            self.replayed += 1
            self._log(
                {
                    "kind": "saved_live_replay",
                    "request_key": fingerprint,
                    "source_attempt_id": item["source_attempt_id"],
                }
            )
            return item["generation"]
        for retry in range(181):
            try:
                generation = self.model.generate(messages, schema)
                self.actual += 1
                self._log({"kind": "new_live_generation", "request_key": fingerprint})
                return generation
            except GenerationFailure:
                self.actual += 1
                self._log({"kind": "new_live_incomplete_generation", "request_key": fingerprint})
                raise
            except httpx.TransportError as exc:
                self._log(
                    {
                        "kind": "transport_retry",
                        "request_key": fingerprint,
                        "retry": retry,
                        "error": type(exc).__name__,
                        "time_utc": datetime.now(UTC).isoformat(),
                    }
                )
                if retry == 180:
                    raise SystemExit("Model transport unavailable for 30 minutes") from exc
                time.sleep(10)
        raise AssertionError("Unreachable retry loop")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--cache",
        type=Path,
        default=Path(
            "runs/postmerge-anm-cache/runs/anish-anm-validation-test-01/execution/attempts/sample_512"
        ),
    )
    ap.add_argument("--scripted", action="store_true")
    ap.add_argument(
        "--smoke", action="store_true", help="Run one pair only; a separate output is required"
    )
    ap.add_argument(
        "--reuse-live-from",
        type=Path,
        help="Reuse exact successful live responses from an interrupted run",
    )
    args = ap.parse_args()
    spec_path = Path("configs/final-track-b-integrated-38.json")
    names_path = Path("configs/final-track-b-validation-names.json")
    manifest_path = Path("configs/pilot-data.json")
    roster_path = Path("configs/evaluation-roster.json")
    archive_inputs = Path("artifacts/final-delivery/anm-real-validation/inputs.json")
    spec = read_json(spec_path)
    if spec["protocol"] != COMPACT_PROTOCOL or spec["pair_count"] != 38:
        ap.error("Frozen protocol mismatch")
    names = read_json(names_path)
    manifest = read_json(manifest_path)
    roster = read_json(roster_path)
    verify_snapshot_hashes(args.snapshot, manifest["files"])
    check_roster(manifest, args.snapshot, roster)
    archived = read_json(archive_inputs)
    cases = [
        dict(case_id=c["case_id"], pair_id=c["pair_id"], source_group=c["source_group"])
        for c in archived["cases"]
    ]
    if (
        len(cases) != 38
        or {c["pair_id"] for c in cases}
        != {r["pair_id"] for r in roster["pairs"] if r["anm_use"] == "validation"}
        or set(names) != {str(c["pair_id"]) for c in cases}
    ):
        ap.error("Archived cases, roster and reviewed variable names differ")
    cases.sort(key=lambda c: c["pair_id"])
    if len({c["source_group"] for c in cases}) != spec["source_group_count"]:
        ap.error("Source-group count differs from frozen protocol")
    config = (
        None if args.scripted else ModelConfig.model_validate(read_json(Path(spec["model_config"])))
    )
    observed_model = None
    if config is not None:
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.get(config.base_url.rstrip("/") + "/api/tags")
            response.raise_for_status()
            matches = [m for m in response.json()["models"] if m["name"] == config.model]
            if len(matches) != 1 or matches[0]["digest"] != spec["model_digest"]:
                ap.error("Installed model name/digest differs from frozen protocol")
            observed_model = matches[0]
    selected_cases = cases[:1] if args.smoke else cases
    if not args.smoke and len(selected_cases) * 8 > spec["maximum_live_calls"]:
        ap.error("Call budget exceeded")
    if args.reuse_live_from and (args.scripted or args.smoke):
        ap.error("Saved-live reuse is only for the full live panel")
    saved = saved_live_generations(args.reuse_live_from, config) if args.reuse_live_from else {}
    anm_config = ANMConfig.model_validate(spec["anm_config"])
    selection = SelectionSpec.model_validate(spec["selection"])
    session = {
        "scope": spec["scope"],
        "protocol": COMPACT_PROTOCOL,
        "cases": selected_cases,
        "scripted": args.scripted,
        "model_config": config.model_dump(mode="json") if config else None,
        "model_digest": spec["model_digest"] if config else None,
        "snapshot_hashes": digest(manifest_path),
        "roster_sha256": digest(roster_path),
        "archive_inputs_sha256": digest(archive_inputs),
        "protocol_sha256": digest(spec_path),
        "names_sha256": digest(names_path),
        "script_sha256": digest(__file__),
        "reuse_live_events_sha256": digest(args.reuse_live_from / "experiment/events.jsonl")
        if args.reuse_live_from
        else None,
        "reused_live_generation_count": len(saved),
        "source_sha256": {
            str(p): digest(p) for p in sorted(Path("src/causalbridge").rglob("*.py"))
        },
    }
    root = args.output
    if (root / "session.json").exists():
        if read_json(root / "session.json") != session:
            ap.error("Session inputs changed; choose a new output directory")
    else:
        root.mkdir(parents=True, exist_ok=False)
        atomic_json(root / "session.json", session)
    packages = []
    for case in selected_cases:
        rows = [
            tuple(map(float, line.split()))
            for line in (args.snapshot / f"pair{case['pair_id']:04d}.txt").read_text().splitlines()
        ]
        pair = RuntimePair(
            case_id=case["case_id"],
            variables=tuple({"name": name} for name in names[str(case["pair_id"])]),
            rows=rows,
        )
        selected = select_pair(pair, selection)
        packages.extend(
            build_native_packages(selected, args.cache / case["case_id"] / "261", anm_config)
        )
    runner = IntegratedRunner(
        root / "experiment",
        model_identity=json.dumps(session, sort_keys=True),
        identity_verified=True,
        config=config,
        model_mode="scripted_fixture" if args.scripted else "live_ollama",
        protocol=COMPACT_PROTOCOL,
        observation_kind="real_observational",
        source_version=spec["version"],
    )
    if args.scripted:
        run = runner.run(packages, ScriptedNativeModel())
        model = None
    else:
        with httpx.Client(timeout=config.timeout_seconds, trust_env=False) as client:
            model = ResumableLiveModel(config, client, saved, root / "generation-provenance.jsonl")
            run = runner.run(packages, model)
        if model.replayed != session["reused_live_generation_count"]:
            raise ValueError("A saved live generation did not match the frozen request")
        if model.actual + model.replayed != len(selected_cases) * 8:
            raise ValueError("Not every planned trial has a real model response")
    releases = runner.replay_s2(run["manifest_id"])
    audit = audit_native(root / "experiment")
    rows = analysis_rows(run, releases)
    atomic_json(root / "audit.json", audit)
    atomic_json(root / "evaluation_mapping.json", evaluator_mapping(packages))
    (root / "analysis.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows)
    )
    atomic_json(
        root / "run-summary.json",
        {
            "case_count": len(selected_cases),
            "new_model_calls": run["new_model_calls"],
            "manifest_id": run["manifest_id"],
            "audit_passed": audit["passed"],
            "observed_model": observed_model,
            "model_mode": "scripted_fixture"
            if args.scripted
            else "saved_live_plus_new_live"
            if args.reuse_live_from
            else "live_ollama",
            "saved_live_replays": model.replayed if model else 0,
            "actual_new_ollama_calls": model.actual if model else 0,
            "new_usage": run["new_usage"],
            "historical_usage": run["historical_usage"],
        },
    )
    if not args.smoke:
        truth = {r["pair_id"]: r for r in roster["pairs"] if r["anm_use"] == "validation"}
        evaluator = [
            dict(
                case_id=c["case_id"],
                original_pair_id=c["pair_id"],
                source_group=c["source_group"],
                weight=truth[c["pair_id"]]["weight"],
                reference_direction=truth[c["pair_id"]]["reference_direction"],
                source_digest=next(
                    m["source_digest"]
                    for m in evaluator_mapping(packages)
                    if m["case_id"] == c["case_id"]
                ),
            )
            for c in cases
        ]
        atomic_json(root / "evaluator.json", evaluator)
        atomic_json(root / "scores.json", score_pilot(rows, evaluator, evaluator_mapping(packages)))
    print(json.dumps(read_json(root / "run-summary.json"), indent=2))
    return 0 if audit["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
