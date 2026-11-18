import hashlib

import pytest


def snapshot(tmp_path):
    files = {
        "README": "Overview with private label descriptions",
        "pairmeta.txt": "0001 2 2 1 1 0.5\n0002 1 1 2 2 1\n",
        "pair0001.txt": "1 3\n2 5\n3 7\n4 9\n5 11\n6 13\n7 15\n8 17\n",
        "pair0001_des.txt": "PRIVATE_GOLD_SENTINEL second column causes first",
        "pair0002.txt": "2 4\n3 9\n",
        "pair0002_des.txt": "Reserved family",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    return {
        "version": "tuebingen-pilot-v1",
        "source_url": "https://example.org/snapshot",
        "mapping_seed": 261,
        "minimum_rows": 8,
        "files": {
            name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()
        },
        "pairs": [
            {
                "pair_id": 1,
                "source_group": "family1",
                "split": "pilot",
                "variables": [{"name": "Measurement one"}, {"name": "Measurement two"}],
                "notes": ["description reviewed"],
            },
            {
                "pair_id": 2,
                "source_group": "family2",
                "split": "reserved",
                "exclusion_reason": "not_selected_for_pilot",
            },
        ],
    }


def test_loader_preserves_original_order_but_reads_reversed_reference(tmp_path):
    from causalbridge.discovery.loader import prepare_pilot

    prepared = prepare_pilot(tmp_path, snapshot(tmp_path))
    assert len(prepared.pairs) == len(prepared.evaluator) == 1
    assert prepared.pairs[0].rows[0] == (1.0, 3.0)
    assert prepared.evaluator[0]["reference_direction"] == "second_to_first"
    assert prepared.evaluator[0]["weight"] == 0.5
    assert "PRIVATE_GOLD_SENTINEL" not in prepared.pairs[0].model_dump_json()
    assert prepared.audit["included_count"] == 1
    assert prepared.audit["excluded"][0]["reason"] == "not_selected_for_pilot"


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "missing",
        "overlap",
        "nonfinite",
        "constant",
        "unreviewed",
        "metadata",
        "zero_weight",
    ],
)
def test_loader_fails_closed_on_unusable_or_unreviewed_inputs(tmp_path, fault):
    from causalbridge.discovery.loader import prepare_pilot

    manifest = snapshot(tmp_path)
    if fault == "hash":
        (tmp_path / "pair0001.txt").write_text("changed")
    elif fault == "missing":
        (tmp_path / "pair0001_des.txt").unlink()
    elif fault == "overlap":
        manifest["pairs"][1]["source_group"] = "family1"
    elif fault == "unreviewed":
        manifest["pairs"][0].pop("variables")
    else:
        filename = "pairmeta.txt" if fault in {"metadata", "zero_weight"} else "pair0001.txt"
        content = {
            "nonfinite": "1 nan\n" * 8,
            "constant": "1 2\n" * 8,
            "metadata": "0001 1 2 3 3 0.5\n0002 1 1 2 2 1\n",
            "zero_weight": "0001 2 2 1 1 0\n0002 1 1 2 2 1\n",
        }[fault]
        (tmp_path / filename).write_text(content)
        manifest["files"][filename] = hashlib.sha256(content.encode()).hexdigest()
    with pytest.raises((ValueError, OSError)):
        prepare_pilot(tmp_path, manifest)


def test_prepared_pilot_runs_existing_matrix_offline_and_scores_afterward(tmp_path):
    import json
    import subprocess

    source = tmp_path / "source"
    source.mkdir()
    manifest = snapshot(source)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    prepared = tmp_path / "prepared"
    proc = subprocess.run(
        [
            "python",
            "-m",
            "causalbridge.discovery.loader",
            "--snapshot",
            str(source),
            "--manifest",
            str(path),
            "--output",
            str(prepared),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    output = tmp_path / "run"
    command = [
        "python",
        "examples/real_data_pilot.py",
        "--prepared",
        str(prepared),
        "--output",
        str(output),
        "--scripted",
    ]
    proc = subprocess.run(command, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((output / "pilot-run.json").read_text())
    assert report["new_model_calls"] == 8
    assert report["audit_passed"] and report["s2_count"] == 4
    proc = subprocess.run(command, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads((output / "pilot-run.json").read_text())["new_model_calls"] == 0
    assert not (output / "scores.json").exists()
    proc = subprocess.run(
        [
            "python",
            "-m",
            "causalbridge.evaluation.scoring",
            "--analysis",
            str(output / "analysis.jsonl"),
            "--evaluator",
            str(prepared / "evaluator/records.json"),
            "--mapping",
            str(output / "evaluation_mapping.json"),
            "--output",
            str(output / "scores.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert len(json.loads((output / "scores.json").read_text())) == 17
