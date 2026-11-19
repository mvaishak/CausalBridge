"""Compare archived live pilot requests with a current offline replay, case by case."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def starts(path):
    return [
        event["data"]
        for line in path.read_text().splitlines()
        if (event := json.loads(line))["kind"] == "native_started"
    ]


def source_comparison(session):
    original = session.get("source_files_sha256", {})
    tracked = (
        "discovery/anm.py",
        "discovery/evidence.py",
        "discovery/loader.py",
        "evaluation/integration.py",
        "evaluation/scoring.py",
        "llm/predictor.py",
    )
    result = {}
    for suffix in tracked:
        previous = [value for path, value in original.items() if path.endswith(suffix)]
        current_path = Path("src/causalbridge") / suffix
        current = hashlib.sha256(current_path.read_bytes()).hexdigest()
        result[suffix] = {
            "archived_sha256": previous[0] if len(previous) == 1 else None,
            "current_sha256": current,
            "same": len(previous) == 1 and previous[0] == current,
        }
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--current", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    with zipfile.ZipFile(args.archive) as z:
        original = [
            json.loads(line)["data"]
            for line in z.read("real-pilot-01/experiment/events.jsonl").decode().splitlines()
            if json.loads(line)["kind"] == "native_started"
        ]
        archived_session = json.loads(z.read("real-pilot-01/session.json"))
    current = starts(args.current / "experiment" / "events.jsonl")

    def key(row):
        return (
            row["package"]["evidence"]["case_id"],
            row["package"]["evidence"]["package"],
            row["condition"]["condition_id"],
        )

    a, b = {key(r): r for r in original}, {key(r): r for r in current}
    fields = ("messages", "output_schema", "condition", "prompt_version", "protocol", "receipt")
    differing = {
        field: [list(k) for k in sorted(a.keys() & b.keys()) if a[k][field] != b[k][field]]
        for field in fields
    }
    package_fields = ("evidence", "method_request", "selected")
    differing.update(
        {
            "package." + field: [
                list(k)
                for k in sorted(a.keys() & b.keys())
                if a[k]["package"][field] != b[k]["package"][field]
            ]
            for field in package_fields
        }
    )
    report = {
        "original_live_attempts": len(original),
        "current_scripted_attempts": len(current),
        "case_count": len({k[0] for k in a}),
        "keys_identical": a.keys() == b.keys(),
        "model_visible_and_method_fields_compared": list(fields)
        + ["package." + x for x in package_fields],
        "excluded_nonvisible_field": "package.method_directory is an absolute artifact path",
        "differences": differing,
        "original_model_config": archived_session.get("config"),
        "source_comparison": source_comparison(archived_session),
        "interpretation": "Scripted request comparison; no new live inference.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["keys_identical"] and not any(differing.values()) and len(a) == 136 else 1


if __name__ == "__main__":
    raise SystemExit(main())
