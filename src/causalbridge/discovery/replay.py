"""Verify saved ANM attempts and optionally repeat the unchanged producer locally.

This is production replay, not an independent reference or a causal-accuracy study.
Historical inputs are read only; replay artifacts go to a fresh directory.
"""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from causalbridge.discovery.anm import execute_anm_request, load_anm_artifacts
from causalbridge.discovery.anm_requests import (
    load_anm_request,
    read_json,
    save_anm_request,
    write_json_exclusive,
)
from causalbridge.discovery.schemas import canonical_digest

ARTIFACTS = (
    "sample.json",
    "config.json",
    "request.json",
    "inputs.json",
    "execution_started.json",
    "reproducibility.json",
    "result.json",
)
EXACT_FIELDS = (
    "status",
    "threshold",
    "decision",
    "predicted_direction",
    "reason_code",
    "error_category",
)
SCORE_FIELDS = ("score_ab", "score_ba", "margin")


def _inventory(root):
    # Include incomplete attempts: finding only result.json would hide failures.
    directories = sorted(
        {p.parent for name in ARTIFACTS if name != "config.json" for p in root.rglob(name)}
    )
    return {
        str(directory.relative_to(root)): {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            if (directory / name).is_file()
            else None
            for name in ARTIFACTS
        }
        for directory in directories
    }


def _differences(original, replayed):
    differences = [
        field for field in EXACT_FIELDS if getattr(original, field) != getattr(replayed, field)
    ]
    for field in SCORE_FIELDS:
        expected, actual = getattr(original, field), getattr(replayed, field)
        if expected is None or actual is None:
            equal = expected is actual
        else:
            equal = abs(actual - expected) <= 1e-10 + 1e-7 * abs(expected)
        if not equal:
            differences.append(field)
    return differences


def reproduce_attempts(attempt_root, output, *, recompute=False, expected_count=None):
    """Check all discovered attempts; recompute only after all originals validate.

    expected_count checks only a count, not the identities of a frozen schedule.
    No benchmark labels, model calls, threshold tuning or accuracy scoring occur.
    """
    root, output = Path(attempt_root).resolve(), Path(output).resolve()
    if not root.is_dir():
        raise ValueError("Original attempt root is missing or is not a directory")
    if output == root or root in output.parents:
        raise ValueError("Output must be outside the original attempt root")
    if output.exists():
        raise FileExistsError("Use a fresh output directory")
    if expected_count is not None and (type(expected_count) is not int or expected_count < 1):
        raise ValueError("Expected attempt count must be a positive integer")
    before = _inventory(root)
    if not before:
        raise ValueError("No original ANM attempts found; Markdown reports are not run artifacts")
    checked, originals = [], []
    for relative, files in before.items():
        entry = {"source": relative, "artifact_valid": False}
        try:
            if any(value is None for value in files.values()):
                raise ValueError("Incomplete original ANM attempt")
            saved = load_anm_request(root / relative)
            artifacts = load_anm_artifacts(root / relative)
            if read_json(root / relative / "execution_started.json") != {
                "request_digest": canonical_digest(saved.request.model_dump(mode="json"))
            }:
                raise ValueError("Execution marker does not bind the original request")
            entry.update(
                artifact_valid=True,
                case_id=saved.request.case_id,
                request_digest=canonical_digest(saved.request.model_dump(mode="json")),
                sample_digest=saved.request.sample_digest,
                config_digest=saved.request.config_digest,
                result_status=artifacts.result.status,
                original_dependencies=artifacts.reproducibility["dependencies"],
            )
            originals.append((saved, artifacts.result, entry))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
        checked.append(entry)
    count_matches = expected_count is None or len(checked) == expected_count
    valid = all(entry["artifact_valid"] for entry in checked) and count_matches
    output.mkdir(parents=True, exist_ok=False)
    if recompute and valid:
        for index, (saved, original, entry) in enumerate(originals):
            destination = output / "attempts" / f"{index:04d}"
            try:
                request = save_anm_request(
                    saved.sample.rows,
                    case_id=saved.request.case_id,
                    ab_mapping_id=saved.sample.ab_mapping_id,
                    config=saved.config,
                    directory=destination,
                )
                if request != saved.request:
                    raise ValueError("Replay changed the original request")
                replayed = execute_anm_request(destination)
                load_anm_artifacts(destination)
                entry["differences"] = _differences(original, replayed)
                entry["replay_matches"] = not entry["differences"]
            except (ValueError, OSError, ArithmeticError) as exc:
                entry.update(replay_matches=False, replay_error=f"{type(exc).__name__}: {exc}")
            entry["replay_directory"] = str(destination.relative_to(output))
    unchanged = _inventory(root) == before
    passed = (
        valid
        and unchanged
        and (not recompute or all(entry.get("replay_matches") is True for entry in checked))
    )
    try:
        numpy_version = importlib.metadata.version("numpy")
    except importlib.metadata.PackageNotFoundError:
        numpy_version = None
    report = dict(
        report_version="anm-production-replay-1",
        scope="saved_artifact_consistency_and_optional_production_replay",
        passed=passed,
        recompute_requested=recompute,
        replay_count=sum("replay_matches" in entry for entry in checked),
        original_attempt_root=str(root),
        original_files_sha256=before,
        original_files_unchanged=unchanged,
        discovered_count=len(checked),
        expected_count=expected_count,
        expected_count_matches=None if expected_count is None else count_matches,
        schedule_identity_verified=False,
        current_dependencies={"python": platform.python_version(), "numpy": numpy_version},
        producer_source_sha256={
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("anm.py", "anm_requests.py")
        },
        score_tolerance={"absolute": 1e-10, "relative_to_original": 1e-7},
        attempts=checked,
        limitations=[
            "Reuses the production implementation; not an independent numerical reference.",
            "No causal labels, accuracy, stability or scientific progression gate evaluated.",
            "Matching hashes establish consistency, not authenticity of the originals.",
            "A matching replay of a typed method error is not successful direction recovery.",
        ],
    )
    write_json_exclusive(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--recompute", action="store_true", help="Repeat local CPU-only ANM fits")
    args = parser.parse_args()
    try:
        report = reproduce_attempts(
            args.attempt_root,
            args.output,
            recompute=args.recompute,
            expected_count=args.expected_count,
        )
    except (ValueError, OSError) as exc:
        parser.exit(2, f"ANM replay: {exc}\n")
    print(json.dumps({key: report[key] for key in ("passed", "discovered_count", "replay_count")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
