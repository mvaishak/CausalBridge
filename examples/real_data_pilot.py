"""Bounded real-data pilot using the existing native runner. Labels are joined separately."""

import argparse
import hashlib
import json
from pathlib import Path

import httpx

from causalbridge.discovery.anm_requests import ANMConfig, read_json
from causalbridge.discovery.contracts import RuntimePair, SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows, evaluator_mapping
from causalbridge.evaluation.integration import (
    COMPACT_PROTOCOL,
    IntegratedRunner,
    build_native_packages,
)
from causalbridge.evaluation.integration_demo import ScriptedNativeModel
from causalbridge.evaluation.store import atomic_json
from causalbridge.llm.client import ModelConfig, OllamaModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scripted", action="store_true", help="Offline pipeline validation only")
    parser.add_argument("--config", type=Path, default=Path("configs/pilot-model.json"))
    parser.add_argument("--model-digest", help="Required immutable Ollama digest for a live pilot")
    parser.add_argument("--max-calls", type=int, default=160)
    args = parser.parse_args()
    source = args.prepared / "runtime" / "pairs.jsonl"
    pairs = [
        RuntimePair.model_validate(read_json_line(line)) for line in source.read_text().splitlines()
    ]
    if not pairs or len({p.case_id for p in pairs}) != len(pairs) or len(pairs) > 20:
        parser.error("Pilot requires 1–20 distinct cases")
    if len(pairs) * 8 > args.max_calls:
        parser.error("Pilot exceeds requested call budget before scheduling")
    config = None if args.scripted else ModelConfig.model_validate(read_json(args.config))
    metadata = None
    if not args.scripted:
        if not args.model_digest:
            parser.error("Pin --model-digest before live generation")
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.get(config.base_url.rstrip("/") + "/api/tags")
            response.raise_for_status()
            models = [m for m in response.json()["models"] if m["name"] == config.model]
            if len(models) != 1 or models[0]["digest"] != args.model_digest:
                parser.error("Installed model differs from the pinned name/digest")
            metadata = models[0]
    session = dict(
        protocol=COMPACT_PROTOCOL,
        runtime_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        config=config.model_dump(mode="json") if config else None,
        model_digest=args.model_digest if config else None,
        model_mode="scripted_fixture" if args.scripted else "live_ollama",
        source_files_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), *sorted(Path("src/causalbridge").rglob("*.py"))]
        },
        selection=dict(
            method_limit=128, display_limit=16, mapping_seed=261, sample_seed=262, display_seed=263
        ),
        anm_threshold=0.001,
        threshold_scope="exploratory_pilot_not_calibrated",
    )
    root = args.output
    if (root / "session.json").exists():
        if read_json(root / "session.json") != session:
            parser.error("Inputs, settings or code changed; use a new output directory")
    else:
        root.mkdir(parents=True, exist_ok=False)
        atomic_json(root / "session.json", session)
    packages = []
    for pair in pairs:
        selected = select_pair(pair, SelectionSpec(**session["selection"]))
        packages.extend(
            build_native_packages(
                selected,
                root / "anm" / pair.case_id,
                ANMConfig(
                    sampling_seed=262,
                    threshold=0.001,
                    maximum_rows=128,
                    configuration_version="real-pilot-exploratory-v1",
                    threshold_selection_version="uncalibrated_pilot_0.001",
                ),
            )
        )
    runner = IntegratedRunner(
        root / "experiment",
        model_identity=json.dumps(session, sort_keys=True),
        identity_verified=True,
        config=config,
        model_mode=session["model_mode"],
        protocol=COMPACT_PROTOCOL,
        observation_kind="real_observational",
        source_version="pilot-readiness-v1",
    )
    if args.scripted:
        run = runner.run(packages, ScriptedNativeModel())
    else:
        with httpx.Client(timeout=config.timeout_seconds, trust_env=False) as client:
            run = runner.run(packages, OllamaModel(config, client=client))
    releases = runner.replay_s2(run["manifest_id"])
    report = audit_native(root / "experiment")
    atomic_json(root / "audit.json", report)
    atomic_json(root / "evaluation_mapping.json", evaluator_mapping(packages))
    rows = analysis_rows(run, releases)
    (root / "analysis.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in rows)
    )
    atomic_json(
        root / "pilot-run.json",
        dict(
            notice="Real data with scripted replies: pipeline validation only"
            if args.scripted
            else "Exploratory real-data pilot; no held-out claims",
            case_count=len(pairs),
            manifest_id=run["manifest_id"],
            new_model_calls=run["new_model_calls"],
            s2_count=len(releases),
            audit_passed=report["passed"],
            new_usage=run["new_usage"],
            historical_usage=run["historical_usage"],
            observed_model=metadata,
            method_errors=sum(
                p.evidence.package == "E4" and p.evidence.method_result.status == "error"
                for p in packages
            ),
        ),
    )
    print(json.dumps(read_json(root / "pilot-run.json"), indent=2))
    return 0 if report["passed"] else 1


def read_json_line(line):
    from causalbridge.llm.parser import reject_duplicate_keys

    return json.loads(line, object_pairs_hook=reject_duplicate_keys)


if __name__ == "__main__":
    raise SystemExit(main())
