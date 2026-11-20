"""Independent archive integrity and saved-result recount, without numerical refitting."""

import argparse
import hashlib
import json
import math
import tarfile
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.archive_root.resolve()):
        parser.error("Write a fresh review outside the retained archive")
    manifest = json.loads((args.archive_root / "manifest.json").read_text())
    path = args.archive_root / manifest["archive"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive hash mismatch")
    expected = {r["path"]: r for r in manifest["files"]}
    saved = {}
    prefix = "runs/anish-anm-validation-test-01/"
    seen = set()
    with tarfile.open(path) as archive:
        for member in archive:
            if not member.isfile():
                continue
            if member.name in seen or member.name not in expected:
                raise ValueError("Unexpected or duplicate archive member")
            seen.add(member.name)
            content = archive.extractfile(member).read()
            record = expected[member.name]
            if (
                len(content) != record["bytes"]
                or hashlib.sha256(content).hexdigest() != record["sha256"]
            ):
                raise ValueError("Saved member differs: " + member.name)
            if member.name.startswith(prefix) and member.name.endswith(".json"):
                saved[member.name] = json.loads(content)
    if seen != set(expected):
        raise ValueError("Missing archive member")
    summary = saved[prefix + "execution/summary.json"]
    protocol = saved[prefix + "protocol.json"]
    report = saved[prefix + "report.json"]
    if len(summary["variants"]) != 1:
        raise ValueError("Unexpected validation variant count")
    rows = summary["variants"][0]["cases"]
    primary_split = protocol["plan"]["primary_split"]
    outcomes, checked, cases = Counter(), 0, set()
    variant = protocol["chosen_variant"]["name"]
    for row in rows:
        result = saved[
            prefix
            + f"execution/attempts/{variant}/{row['case_id']}/{row['split_seed']}/result.json"
        ]
        margin = result["score_ba"] - result["score_ab"]
        threshold = result["threshold"]
        direction = "A_to_B" if margin > threshold else "B_to_A" if margin < -threshold else None
        if (
            result["status"] != "ok"
            or not math.isclose(margin, result["margin"], abs_tol=1e-12)
            or result["predicted_direction"] != direction
            or row["decision"] != direction
        ):
            raise ValueError("Saved-score direction or summary mismatch")
        checked += 1
        if row["split_seed"] == primary_split:
            if row["case_id"] in cases:
                raise ValueError("Repeated primary case")
            cases.add(row["case_id"])
            outcomes[
                "abstain"
                if direction is None
                else "correct"
                if direction == row["reference"]
                else "wrong"
            ] += 1
    if len(cases) != report["case_count"] or len(cases) != len(protocol["case_ids"]):
        raise ValueError("Primary denominator differs")
    output = dict(
        scope="independent_saved_artifact_integrity_and_accounting_review_not_a_second_numerical_estimator",
        archive_sha256=manifest["archive_sha256"],
        archived_files_verified=len(seen),
        saved_validation_directions_checked=checked,
        primary_split=primary_split,
        primary_cases=len(cases),
        primary_counts=dict(outcomes),
        reported_primary_weighted_accuracy=report["metrics"]["selective_accuracy"],
        note=(
            "Counts use retained reference labels. This recount does not independently "
            "establish causal labels, re-fit ANM or reproduce "
            "the full original numerical calculation."
        ),
        model_calls=0,
        numerical_refits=0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2)
        stream.write("\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
