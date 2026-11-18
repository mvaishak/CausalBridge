"""Frozen evaluation roster. No model calls and no threshold selection.

Development rows may be used to choose a later ANM change. Validation rows may
not. The 17 pilot rows stay frozen. Truth is the benchmark cause column, read
after the snapshot hashes match.
"""

import json
import math
from pathlib import Path

from causalbridge.discovery.data_audit import data_exclusion, file_stats
from causalbridge.discovery.loader import (
    PairReview,
    read_pair_metadata,
    validate_source_groups,
    verify_snapshot_hashes,
)

SCALAR_RANGES = {(1, 1, 2, 2), (2, 2, 1, 1)}
ROLES = ("frozen_pilot", "development", "validation", "not_scorable")


def evaluation_roster(manifest: dict, snapshot: Path) -> dict:
    """Return one row per metadata pair, with role, truth and scorability."""
    snapshot = Path(snapshot)
    verify_snapshot_hashes(snapshot, manifest["files"])
    metadata = read_pair_metadata(snapshot / "pairmeta.txt")
    reviews = {pair["pair_id"]: pair for pair in manifest["pairs"]}
    if set(metadata) != set(reviews) or len(reviews) != len(manifest["pairs"]):
        raise ValueError("Metadata pair ids differ from the manifest")
    validate_source_groups(tuple(PairReview.model_validate(r) for r in manifest["pairs"]))
    minimum_rows = manifest.get("minimum_rows", 100)
    if type(minimum_rows) is not int or minimum_rows < 8:
        raise ValueError("Minimum row count must be an integer of at least eight")
    pairs = [_row(reviews[pair_id], metadata[pair_id]) for pair_id in sorted(reviews)]
    for row in pairs:
        if not row["scorable"]:
            continue
        pair_id = row["pair_id"]
        filename = f"pair{pair_id:04d}.txt"
        if filename not in manifest["files"]:
            raise ValueError("Scorable numeric file is not pinned: " + filename)
        *columns, weight = metadata[pair_id]
        reason = data_exclusion(
            pair_id, tuple(columns), weight, file_stats(snapshot / filename), minimum_rows
        )
        if reason is not None:
            raise ValueError(f"Scorable pair {pair_id} fails audited eligibility: {reason}")
    counts = {role: sum(row["anm_use"] == role for row in pairs) for role in ROLES}
    return {
        "version": "evaluation-handoff-v1",
        "manifest_version": manifest["version"],
        "mapping_seed": manifest["mapping_seed"],
        "metrics": {
            "weighted_coverage": "released weight / total weight",
            "correct_yield": "correct released weight / total weight",
            "wrong_yield": "wrong released weight / total weight",
            "selective_accuracy": "correct released weight / released weight, or null",
        },
        "pass_criteria": {
            "numeric_accuracy_bar": None,
            "pilot_threshold": 0.001,
            "pilot_threshold_status": "exploratory_not_a_pass_bar",
            "development_may_select_a_change": True,
            "validation_may_select_a_change": False,
            "pilot_may_select_a_change": False,
            "denominator": "every scorable pair in the named split",
        },
        "counts": counts,
        "pairs": pairs,
    }


def _row(review: dict, metadata: tuple) -> dict:
    first_start, first_end, second_start, second_end, weight = metadata
    columns = (first_start, first_end, second_start, second_end)
    if columns == (1, 1, 2, 2):
        direction = "first_to_second"
    elif columns == (2, 2, 1, 1):
        direction = "second_to_first"
    else:
        direction = None
    reason = review.get("exclusion_reason")
    scorable = (
        reason is None
        and review["split"] in {"pilot", "development", "test"}
        and direction is not None
        and type(weight) in (int, float)
        and math.isfinite(weight)
        and weight > 0
    )
    if scorable and review["split"] == "pilot":
        role = "frozen_pilot"
    elif scorable and review["split"] == "development":
        role = "development"
    elif scorable and review["split"] == "test":
        role = "validation"
    else:
        role = "not_scorable"
    row = {
        "pair_id": review["pair_id"],
        "source_group": review["source_group"],
        "split": review["split"],
        "anm_use": role,
        "scorable": scorable,
        "weight": weight,
        "reference_direction": direction,
    }
    if reason is not None:
        row["exclusion_reason"] = reason
    return row


def check_roster(manifest: dict, snapshot: Path, roster: dict) -> None:
    fresh = evaluation_roster(manifest, snapshot)
    if roster != fresh:
        raise ValueError("Evaluation roster does not match the snapshot")


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    roster = evaluation_roster(manifest, args.snapshot)
    if args.write:
        args.roster.write_text(json.dumps(roster, indent=2) + "\n")
    else:
        check_roster(manifest, args.snapshot, json.loads(args.roster.read_text()))
    print(json.dumps(roster["counts"], indent=2))


if __name__ == "__main__":
    main()
