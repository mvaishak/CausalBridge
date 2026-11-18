import hashlib
import json
from pathlib import Path

import pytest

from causalbridge.discovery.data_audit import PILOT_PAIR_IDS
from causalbridge.evaluation.roster import evaluation_roster


def _files(root: Path, contents: dict[str, str]) -> dict[str, str]:
    hashes = {}
    for name, text in contents.items():
        data = text.encode()
        (root / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def test_roster_separates_truth_and_scorability(tmp_path):
    root = tmp_path / "raw"
    root.mkdir()
    rows = "\n".join(f"{i} {i + 1}" for i in range(8)) + "\n"
    hashes = _files(
        root,
        {
            "README": "readme\n",
            "pairmeta.txt": "1 1 1 2 2 1\n2 2 2 1 1 2\n3 1 2 3 4 1\n",
            "pair0001.txt": rows,
            "pair0002.txt": rows,
            "pair0003.txt": rows,
        },
    )
    manifest = {
        "version": "tuebingen-pilot-v1",
        "mapping_seed": 261,
        "minimum_rows": 8,
        "files": hashes,
        "pairs": [
            {"pair_id": 1, "source_group": "dev", "split": "development"},
            {
                "pair_id": 2,
                "source_group": "held",
                "split": "test",
                "exclusion_reason": "insufficient_rows",
            },
            {"pair_id": 3, "source_group": "held", "split": "test"},
        ],
    }
    roster = evaluation_roster(manifest, root)
    by_id = {row["pair_id"]: row for row in roster["pairs"]}
    assert by_id[1]["anm_use"] == "development"
    assert by_id[1]["scorable"] is True
    assert by_id[1]["reference_direction"] == "first_to_second"
    assert by_id[2]["anm_use"] == "not_scorable"
    assert by_id[2]["scorable"] is False
    assert by_id[2]["reference_direction"] == "second_to_first"
    assert by_id[3]["anm_use"] == "not_scorable"
    assert by_id[3]["reference_direction"] is None
    assert roster["pass_criteria"]["numeric_accuracy_bar"] is None
    assert roster["pass_criteria"]["validation_may_select_a_change"] is False


def test_committed_roster_matches_the_local_snapshot_when_present():
    snapshot = Path("runs/pilot-preparation/raw")
    roster_path = Path("configs/evaluation-roster.json")
    if not (snapshot / "pairmeta.txt").exists() or not roster_path.exists():
        pytest.skip("Tübingen snapshot or evaluation roster is not in this checkout")
    manifest = json.loads(Path("configs/pilot-data.json").read_text())
    roster = json.loads(roster_path.read_text())
    fresh = evaluation_roster(manifest, snapshot)
    assert roster == fresh
    by_role = {}
    for row in roster["pairs"]:
        by_role.setdefault(row["anm_use"], set()).add(row["pair_id"])
    assert by_role["frozen_pilot"] == set(PILOT_PAIR_IDS)
    assert by_role["development"].isdisjoint(by_role["validation"])
    assert by_role["development"].isdisjoint(by_role["frozen_pilot"])
    assert all(row["scorable"] for row in roster["pairs"] if row["anm_use"] != "not_scorable")
    assert all(not row["scorable"] for row in roster["pairs"] if row["anm_use"] == "not_scorable")


@pytest.mark.parametrize("fault", ["group_overlap", "constant", "short", "nan", "blank", "unbound"])
def test_roster_rejects_invalid_scorable_data_and_cross_role_groups(tmp_path, fault):
    root = tmp_path / "raw"
    root.mkdir()
    rows = "\n".join(f"{i} {i + 1}" for i in range(8)) + "\n"
    bad = {
        "constant": "1 2\n" * 8,
        "short": "1 2\n3 4\n",
        "nan": "1 nan\n" + rows,
        "blank": "\n" + rows,
    }.get(fault, rows)
    hashes = _files(
        root,
        {
            "README": "readme\n",
            "pairmeta.txt": "1 1 1 2 2 1\n2 1 1 2 2 1\n",
            "pair0001.txt": bad,
            "pair0002.txt": rows,
        },
    )
    if fault == "unbound":
        hashes.pop("pair0001.txt")
    manifest = {
        "version": "tuebingen-pilot-v1",
        "mapping_seed": 261,
        "minimum_rows": 8,
        "files": hashes,
        "pairs": [
            {"pair_id": 1, "source_group": "family", "split": "development"},
            {
                "pair_id": 2,
                "source_group": "family" if fault == "group_overlap" else "held",
                "split": "test",
            },
        ],
    }
    with pytest.raises(ValueError):
        evaluation_roster(manifest, root)
