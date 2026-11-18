import hashlib
import json
from pathlib import Path

import pytest

from causalbridge.discovery.data_audit import (
    PILOT_PAIR_IDS,
    assign_reviews,
    check_manifest,
    data_exclusion,
)


def test_data_exclusions_follow_the_declared_order():
    stats = {"rows": 200, "blank": 0, "bad_width": 0, "nonfinite": 0, "unique": [10, 10]}
    assert data_exclusion(1, (1, 1, 2, 2), 0, stats, 100) == "zero_weight"
    assert data_exclusion(1, (1, 2, 3, 3), 1, stats, 100) == "multicolumn"
    assert data_exclusion(1, (1, 1, 2, 2), 1, stats | {"blank": 1}, 100) == "invalid_rows"
    assert data_exclusion(1, (1, 1, 2, 2), 1, stats | {"rows": 90}, 100) == "insufficient_rows"
    assert (
        data_exclusion(1, (1, 1, 2, 2), 1, stats | {"unique": [10, 2]}, 100)
        == "insufficient_variation"
    )
    assert data_exclusion(19, (1, 1, 2, 2), 1, stats, 100) == "time_dependence"
    assert data_exclusion(5, (1, 1, 2, 2), 1, stats, 100) is None


def test_committed_manifest_keeps_the_pilot_pairs_and_assigns_every_group():
    manifest = json.loads(Path("configs/pilot-data.json").read_text())
    included = {
        pair["pair_id"]
        for pair in manifest["pairs"]
        if pair["split"] == "pilot" and "exclusion_reason" not in pair
    }
    assert included == set(PILOT_PAIR_IDS)
    groups: dict[str, set[str]] = {}
    eligible: dict[str, int] = {}
    for pair in manifest["pairs"]:
        groups.setdefault(pair["source_group"], set()).add(pair["split"])
        if "exclusion_reason" not in pair:
            eligible[pair["source_group"]] = eligible.get(pair["source_group"], 0) + 1
        else:
            assert pair["exclusion_reason"] != "reserved_not_eligibility_audited"
    assert all(len(splits) == 1 for splits in groups.values())
    for group, splits in groups.items():
        split = next(iter(splits))
        if split in {"pilot", "development", "test"}:
            assert eligible.get(group, 0) >= 1
        else:
            assert split == "ineligible"
            assert group not in eligible
    pilot_groups = {
        pair["source_group"] for pair in manifest["pairs"] if pair["pair_id"] in included
    }
    held_out = {
        pair["source_group"]
        for pair in manifest["pairs"]
        if pair["split"] in {"development", "test"}
    }
    assert pilot_groups.isdisjoint(held_out)


def test_manifest_matches_the_local_snapshot_when_present():
    snapshot = Path("runs/pilot-preparation/raw")
    if not (snapshot / "pairmeta.txt").exists():
        pytest.skip("Tübingen snapshot is not in this checkout")
    manifest = json.loads(Path("configs/pilot-data.json").read_text())
    check_manifest(manifest, snapshot)


def _snapshot(tmp_path, metadata):
    root = tmp_path / "raw"
    root.mkdir()
    files = {
        "README": b"readme\n",
        "pairmeta.txt": metadata.encode(),
        "pair0001.txt": b"1 2\n3 4\n",
    }
    for name, content in files.items():
        (root / name).write_bytes(content)
    manifest = {
        "minimum_rows": 100,
        "mapping_seed": 261,
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
        "pairs": [{"pair_id": 1, "source_group": "g", "split": "pilot", "variables": ["A", "B"]}],
    }
    return root, manifest


def test_changed_snapshot_bytes_are_rejected_before_eligibility(tmp_path):
    root, manifest = _snapshot(tmp_path, "1 1 1 2 2 1\n")
    (root / "pair0001.txt").write_text("9 8\n3 4\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        assign_reviews(manifest, root)
    with pytest.raises(ValueError, match="hash mismatch"):
        check_manifest(manifest, root)


def test_missing_snapshot_file_is_rejected(tmp_path):
    root, manifest = _snapshot(tmp_path, "1 1 1 2 2 1\n")
    (root / "pair0001.txt").unlink()
    with pytest.raises(ValueError, match="Snapshot file missing"):
        assign_reviews(manifest, root)


@pytest.mark.parametrize(
    "metadata",
    ["1 1 1 2 2 1\n1 1 1 2 2 1\n", "1 1 1 2 2 nan\n", "1 1 1 2 2 -1\n"],
)
def test_duplicate_or_invalid_metadata_is_rejected(tmp_path, metadata):
    root, manifest = _snapshot(tmp_path, metadata)
    with pytest.raises(ValueError, match="Duplicate pair or invalid metadata weight"):
        assign_reviews(manifest, root)
