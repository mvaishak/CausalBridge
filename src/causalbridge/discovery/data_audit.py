"""Eligibility audit for the frozen Tübingen snapshot.

The 17 pilot pairs stay included. Their names and units are not rewritten.
Every other pair gets one data exclusion, or its whole source group is assigned
to development or test. Assignment shuffles source-group names with seed 261
and does not read reference directions or model output.
"""

import json
import math
import random
from pathlib import Path

from causalbridge.discovery.loader import read_pair_metadata, verify_snapshot_hashes

PILOT_PAIR_IDS = frozenset({1, 2, 3, 4, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 56, 86, 88})
# Descriptions state a time index, a successive-day lag, a repeated measure of
# the same units, or an explicit time series. Pair 24 and 86 match loose words
# ("minute", "monthly rent") and are not in this set. Pair 93 says mm/day for a
# multi-year catchment average and is not in this set.
TIME_DEPENDENT_PAIR_IDS = frozenset(
    {
        19,
        42,
        43,
        44,
        45,
        46,
        48,
        49,
        50,
        51,
        65,
        66,
        67,
        68,
        69,
        72,
        73,
        76,
        77,
        85,
        87,
        89,
        90,
        94,
        95,
        96,
    }
)
SCALAR_RANGES = {(1, 1, 2, 2), (2, 2, 1, 1)}
VERIFICATION_NOTE = (
    "Cause column and description names checked on 16 November 2026. "
    "Runtime names and units were left unchanged."
)


def file_stats(path: Path) -> dict:
    rows = []
    blank = bad_width = nonfinite = 0
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            blank += 1
            continue
        parts = line.split()
        if len(parts) != 2:
            bad_width += 1
            continue
        try:
            values = tuple(float(part) for part in parts)
        except ValueError:
            nonfinite += 1
            continue
        if not all(math.isfinite(value) for value in values):
            nonfinite += 1
            continue
        rows.append(values)
    unique = [len(set(column)) for column in zip(*rows, strict=True)] if rows else []
    return {
        "rows": len(rows),
        "blank": blank,
        "bad_width": bad_width,
        "nonfinite": nonfinite,
        "unique": unique,
    }


def data_exclusion(pair_id, columns, weight, stats, minimum_rows) -> str | None:
    """Return the first data reason to keep a pair out, before family rules."""
    if weight <= 0:
        return "zero_weight"
    if columns not in SCALAR_RANGES:
        return "multicolumn"
    if stats["blank"] or stats["bad_width"] or stats["nonfinite"]:
        return "invalid_rows"
    if stats["rows"] < minimum_rows:
        return "insufficient_rows"
    if any(count < 3 for count in stats["unique"]):
        return "insufficient_variation"
    if pair_id in TIME_DEPENDENT_PAIR_IDS:
        return "time_dependence"
    return None


def assign_reviews(manifest: dict, snapshot: Path) -> list[dict]:
    """Return pair reviews with audited exclusions and source-group splits."""
    snapshot = Path(snapshot)
    verify_snapshot_hashes(snapshot, manifest["files"])
    reviews = {pair["pair_id"]: pair for pair in manifest["pairs"]}
    metadata = read_pair_metadata(snapshot / "pairmeta.txt")
    if set(metadata) != set(reviews):
        raise ValueError("Metadata pair ids differ from the manifest")
    minimum_rows = manifest["minimum_rows"]
    exclusions = {}
    for pair_id, (a, b, c, d, weight) in metadata.items():
        stats = file_stats(snapshot / f"pair{pair_id:04d}.txt")
        reason = data_exclusion(pair_id, (a, b, c, d), weight, stats, minimum_rows)
        if pair_id in PILOT_PAIR_IDS and reason is not None:
            raise ValueError(f"Frozen pilot pair {pair_id} is no longer eligible: {reason}")
        exclusions[pair_id] = reason
    pilot_groups = {reviews[pair_id]["source_group"] for pair_id in PILOT_PAIR_IDS}
    eligible_groups = sorted(
        {
            reviews[pair_id]["source_group"]
            for pair_id, reason in exclusions.items()
            if reason is None and reviews[pair_id]["source_group"] not in pilot_groups
        }
    )
    development = _development_groups(eligible_groups, manifest["mapping_seed"])
    updated = []
    for pair_id in sorted(reviews):
        current = reviews[pair_id]
        group = current["source_group"]
        reason = exclusions[pair_id]
        if pair_id in PILOT_PAIR_IDS:
            split, reason = "pilot", None
        elif group in pilot_groups:
            split = "pilot"
            reason = reason or "not_selected_within_pilot_source_group"
        elif group in development:
            split = "development"
        elif group in set(eligible_groups):
            split = "test"
        else:
            split = "ineligible"
            if reason is None:
                raise ValueError(f"Pair {pair_id} has no exclusion in an ineligible group")
        pair = {
            "pair_id": pair_id,
            "source_group": group,
            "split": split,
        }
        if current.get("variables") is not None:
            pair["variables"] = current["variables"]
        if reason is not None:
            pair["exclusion_reason"] = reason
        notes = list(current.get("notes") or [])
        if pair_id in PILOT_PAIR_IDS and VERIFICATION_NOTE not in notes:
            notes.append(VERIFICATION_NOTE)
        if notes:
            pair["notes"] = notes
        updated.append(pair)
    return updated


def _development_groups(groups: list[str], seed: int) -> set[str]:
    """Give 20 percent of remaining eligible groups to development, at least one."""
    order = list(groups)
    random.Random(seed).shuffle(order)
    if len(order) <= 1:
        return set(order)
    count = max(1, round(0.2 * len(order)))
    if count >= len(order):
        count = len(order) - 1
    return set(order[:count])


def check_manifest(manifest: dict, snapshot: Path) -> None:
    expected = assign_reviews(manifest, snapshot)
    if manifest["pairs"] != expected:
        raise ValueError("Manifest pair reviews do not match the snapshot audit")


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    reviews = assign_reviews(manifest, args.snapshot)
    if args.write:
        manifest["pairs"] = reviews
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    else:
        check_manifest(manifest, args.snapshot)
    counts: dict[str, int] = {}
    for pair in reviews:
        counts[pair["split"]] = counts.get(pair["split"], 0) + 1
    print(json.dumps({"pairs": counts, "pilot_included": len(PILOT_PAIR_IDS)}, indent=2))


if __name__ == "__main__":
    main()
