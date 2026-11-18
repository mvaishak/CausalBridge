"""Frozen Tübingen pilot ingestion. No labels or source descriptions enter runtime pairs."""

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field

from causalbridge.discovery.anm_requests import read_json, write_json_exclusive
from causalbridge.discovery.contracts import Digest, RuntimePair, Variable
from causalbridge.discovery.evidence import digest
from causalbridge.schemas import Record


def verify_snapshot_hashes(snapshot: Path, files: dict[str, str]) -> None:
    """Reject a missing or rewritten file before any pair value is interpreted."""
    if not isinstance(files, dict) or not files:
        raise ValueError("Manifest has no snapshot hashes")
    if not {"README", "pairmeta.txt"} <= files.keys():
        raise ValueError("Snapshot must pin README and metadata")
    snapshot = Path(snapshot)
    for name, expected in files.items():
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("Snapshot file names must be local basenames")
        path = snapshot / name
        if not path.is_file():
            raise ValueError("Snapshot file missing: " + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Snapshot hash mismatch: " + name)


def read_pair_metadata(path: Path) -> dict[int, tuple[int, int, int, int, float]]:
    """Read pairmeta.txt. Duplicate ids and nonfinite or negative weights fail."""
    metadata: dict[int, tuple[int, int, int, int, float]] = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 6:
            raise ValueError("Metadata requires six fields")
        pair_id, first_start, first_end, second_start, second_end = map(int, fields[:5])
        weight = float(fields[5])
        if pair_id in metadata or not math.isfinite(weight) or weight < 0:
            raise ValueError("Duplicate pair or invalid metadata weight")
        metadata[pair_id] = (first_start, first_end, second_start, second_end, weight)
    if not metadata:
        raise ValueError("Metadata is empty")
    return metadata


class PairReview(Record):
    pair_id: int = Field(strict=True, ge=1)
    source_group: str = Field(min_length=1)
    split: Literal["pilot", "development", "test", "ineligible", "reserved"]
    variables: tuple[Variable, Variable] | None = None
    exclusion_reason: str | None = Field(default=None, min_length=1)
    notes: tuple[str, ...] = ()


class PilotManifest(Record):
    version: Literal["tuebingen-pilot-v1"]
    source_url: str
    mapping_seed: int = Field(strict=True, ge=0)
    minimum_rows: int = Field(default=100, strict=True, ge=8)
    files: dict[str, Digest]
    pairs: tuple[PairReview, ...]


@dataclass(frozen=True)
class PreparedPilot:
    pairs: tuple[RuntimePair, ...]
    evaluator: tuple[dict, ...]
    audit: dict


def validate_source_groups(reviews: tuple[PairReview, ...]) -> None:
    """Keep each source family in one split, including its excluded members."""
    grouped: dict[str, list[PairReview]] = {}
    for review in reviews:
        grouped.setdefault(review.source_group, []).append(review)
    for group, members in grouped.items():
        splits = {member.split for member in members}
        if len(splits) != 1:
            raise ValueError("Source group has more than one split: " + group)
        split = next(iter(splits))
        eligible = [member for member in members if member.exclusion_reason is None]
        if split == "pilot" and not eligible:
            raise ValueError("Pilot source group has no included pair: " + group)
        if split in {"development", "test"} and not eligible:
            raise ValueError("Held-out source group has no eligible pair: " + group)
        if split in {"ineligible", "reserved"} and eligible:
            raise ValueError("Excluded source group contains an eligible pair: " + group)


def prepare_pilot(snapshot: Path, manifest: dict) -> PreparedPilot:
    """Verify exact files, source isolation and explicit reviews before projection.

    Fail an included unusable pair rather than changing the declared cohort. Never
    impute/drop rows or reorder columns toward the reference cause. Exclusions and
    reservations are recorded for every metadata entry.
    """
    spec = PilotManifest.model_validate(manifest)
    snapshot = Path(snapshot).resolve()
    verify_snapshot_hashes(snapshot, spec.files)
    metadata = read_pair_metadata(snapshot / "pairmeta.txt")
    reviews = {r.pair_id: r for r in spec.pairs}
    if len(reviews) != len(spec.pairs) or set(reviews) != set(metadata):
        raise ValueError("Review must account for every metadata pair exactly once")
    validate_source_groups(spec.pairs)
    # Opaque IDs are randomized independently of reference labels, before reading them.
    ids = list(range(1000, 1000 + len(reviews)))
    random.Random(spec.mapping_seed).shuffle(ids)
    case_ids = {pair: f"D{opaque:04d}" for pair, opaque in zip(sorted(reviews), ids, strict=True)}
    pairs, evaluator, excluded = [], [], []
    for pair_id, review in sorted(reviews.items()):
        a, b, c, d, weight = metadata[pair_id]
        if review.split != "pilot" or review.exclusion_reason:
            excluded.append(
                dict(
                    pair_id=pair_id,
                    source_group=review.source_group,
                    split=review.split,
                    reason=review.exclusion_reason,
                )
            )
            continue
        if weight <= 0 or (a, b, c, d) not in {(1, 1, 2, 2), (2, 2, 1, 1)}:
            raise ValueError("Included pair must be positive-weight scalar/scalar")
        if review.variables is None or not review.notes:
            raise ValueError("Included names, units and source require description review")
        name, description = f"pair{pair_id:04d}.txt", f"pair{pair_id:04d}_des.txt"
        if not {name, description} <= spec.files.keys():
            raise ValueError("Included data and description must be pinned")
        rows = []
        for line in (snapshot / name).read_text().splitlines():
            if not line.strip():
                raise ValueError("Blank numeric row requires an explicit exclusion decision")
            values = line.split()
            if len(values) != 2:
                raise ValueError("Included data must have exactly two columns")
            rows.append(tuple(map(float, values)))
        pair = RuntimePair(case_id=case_ids[pair_id], variables=review.variables, rows=rows)
        if len(rows) < spec.minimum_rows or any(
            len(set(col)) < 3 for col in zip(*pair.rows, strict=True)
        ):
            raise ValueError("Included pair has insufficient rows or variation")
        pairs.append(pair)
        evaluator.append(
            dict(
                case_id=pair.case_id,
                original_pair_id=pair_id,
                source_group=review.source_group,
                split="pilot",
                weight=weight,
                reference_direction="first_to_second" if a == 1 else "second_to_first",
                source_digest=digest(pair.model_dump()),
                data_sha256=spec.files[name],
                description_sha256=spec.files[description],
                row_count=len(rows),
                notes=list(review.notes),
            )
        )
    if not pairs:
        raise ValueError("No included pilot pairs")
    return PreparedPilot(
        tuple(pairs),
        tuple(evaluator),
        dict(
            version=spec.version,
            manifest_digest=digest(spec.model_dump(mode="json")),
            source_url=spec.source_url,
            included_count=len(pairs),
            source_group_count=len({e["source_group"] for e in evaluator}),
            excluded=excluded,
            warning=(
                "Exploratory pilot; reference labels, independent sampling "
                "and ANM assumptions are not certified."
            ),
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    prepared = prepare_pilot(args.snapshot, manifest)
    args.output.mkdir(parents=True, exist_ok=False)
    runtime, private = args.output / "runtime", args.output / "evaluator"
    runtime.mkdir()
    private.mkdir()
    (runtime / "pairs.jsonl").write_text(
        "".join(p.model_dump_json() + "\n" for p in prepared.pairs)
    )
    write_json_exclusive(private / "records.json", prepared.evaluator)
    write_json_exclusive(private / "audit.json", prepared.audit)
    write_json_exclusive(private / "manifest.json", manifest)
    print(json.dumps(prepared.audit))


if __name__ == "__main__":
    main()
