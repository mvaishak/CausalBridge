"""Reproduce saved final results without network access, generation, or ANM fits.

Run from any directory with --output pointing to a fresh directory. All source
archives stay unchanged; extracted files and regenerated results stay in output.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/final-delivery"


def run(script, *args):
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def compare(actual, expected):
    if actual.read_bytes() != expected.read_bytes():
        raise ValueError(f"Reproduced output differs: {actual.name}")


def unpack_tar(archive, destination):
    with tarfile.open(archive) as handle:
        handle.extractall(destination, filter="data")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = [
        ART / "track-a-live/traces.jsonl.gz",
        ART / "track-a-live/oracle.jsonl",
        ART / "track-b-pilot/original-real-pilot-01.zip",
        ART / "track-b-pilot/evaluator-records.json",
        ART / "postmerge-track-b/integrated-38-resumed-live.tar.gz",
        ART / "postmerge-track-b/integrated-38-interrupted-live.tar.gz",
    ]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    pilot_zip = sources[2]
    if hashes[str(pilot_zip.relative_to(ROOT))] != (
        "b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a"
    ):
        raise ValueError("Original pilot archive hash mismatch")
    with zipfile.ZipFile(pilot_zip) as handle:
        for item in handle.infolist():
            if not item.filename.startswith("real-pilot-01/") or item.is_dir():
                continue
            target = (output / item.filename).resolve()
            if not target.is_relative_to(output):
                raise ValueError("Unsafe pilot archive path")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(handle.read(item))
    pilot = output / "real-pilot-01"
    from causalbridge.evaluation.scoring import score_pilot

    rows = [json.loads(line) for line in (pilot / "analysis.jsonl").read_text().splitlines()]
    evaluator = json.loads(sources[3].read_text())
    mapping = json.loads((pilot / "evaluation_mapping.json").read_text())
    scores = score_pilot(rows, evaluator, mapping)
    if scores != json.loads((pilot / "pilot-scores.json").read_text()):
        raise ValueError("Original pilot scores differ")
    run(
        "account_saved_outcomes.py",
        "--run",
        pilot,
        "--evaluator",
        sources[3],
        "--scores",
        pilot / "pilot-scores.json",
        "--output",
        output / "pilot-accounting.json",
    )
    for archive in sources[4:]:
        unpack_tar(archive, output)
    resumed = output / "postmerge-track-b-38-resumed-live"
    interrupted = output / "postmerge-track-b-38-live"
    run(
        "verify_integrated_live_provenance.py",
        "--run",
        resumed,
        "--source",
        interrupted,
        "--output",
        output / "provenance.json",
    )
    compare(
        output / "provenance.json", ART / "postmerge-track-b/integrated-38-provenance-audit.json"
    )
    run("analyze_final_track_b_38.py", "--run", resumed, "--output", output / "integrated-analysis")
    for name in ("metrics.json", "case-results.json", "outcomes.svg"):
        compare(
            output / "integrated-analysis" / name,
            ART / "postmerge-track-b/integrated-38-analysis" / name,
        )
    run(
        "account_saved_outcomes.py",
        "--run",
        resumed,
        "--output",
        output / "integrated-accounting.json",
    )
    run("final_analysis.py", "--output", output / "final-analysis")
    for name in (
        "metrics.json",
        "track-a-case-results.json",
        "anm-real-case-results.json",
        "outcomes.svg",
    ):
        compare(output / "final-analysis" / name, ART / "analysis" / name)
    traces = [
        json.loads(line) for line in gzip.decompress(sources[0].read_bytes()).decode().splitlines()
    ]
    track_a = []
    for trace in traces:
        track_a.append(
            {
                "case_id": trace["runtime_case"]["case_id"],
                "response_action": trace["verdict"]["response_action"],
                "verdict_status": trace["verdict"]["status"],
                "failure_stage": trace["failure_stage"],
                "operational_failure": trace["failure_stage"] is not None,
            }
        )
    (output / "track-a-operational-accounting.json").write_text(
        json.dumps(track_a, indent=2) + "\n"
    )
    interrupted_events = [
        json.loads(line)
        for line in (interrupted / "experiment/events.jsonl").read_text().splitlines()
    ]
    interrupted_counts = Counter(e["kind"] for e in interrupted_events)
    result = {
        "passed": True,
        "source_revision": "d773118951986a2bd25d57a98adb4c9d0881a6b9",
        "source_revision_notice": "Archived study baseline; reproduction code may be newer.",
        "input_sha256": hashes,
        "original_pilot_scores_equal": True,
        "integrated_analysis_bytes_equal": True,
        "final_analysis_bytes_equal": True,
        "interrupted_attempt_events": dict(interrupted_counts),
        "interrupted_attempt_notice": "Not included in completed-panel scientific denominators.",
        "new_scientific_generations": 0,
        "new_scientific_anm_fits": 0,
    }
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
