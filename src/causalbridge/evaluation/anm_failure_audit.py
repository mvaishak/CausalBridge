"""Read-only ANM failure diagnosis from manifest-verified saved attempts; no fitting."""

import csv
import hashlib
import json
import math
import statistics
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import numpy as np

from causalbridge.discovery.anm_requests import load_anm_request
from causalbridge.discovery.evidence import rng
from causalbridge.discovery.schemas import ANMResult, canonical_digest
from causalbridge.llm.parser import reject_duplicate_keys

ARCHIVE = Path("artifacts/anm-experiments-2026-11-18/run-records.tar.gz")
MANIFEST = ARCHIVE.parent / "manifest.json"
CONFIG = Path("configs/anm-failure-audit.json")
VALIDATION = "runs/anish-anm-validation-test-01/execution"
DEVELOPMENT = "runs/anish-anm-development-03"
LARGE = "runs/anish-anm-development-large-01"
SYNTHETIC = "runs/anish-anm-synthetic-panel-01"
ADEQUACY = "runs/anish-anm-adequacy-02/report.json"
KINDS = ("correct", "wrong", "abstention", "execution_failure")


def read(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=reject_duplicate_keys)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def ratio(n, d):
    return {"numerator": n, "denominator": d, "rate": n / d if d else None}


def outcome(direction, reference, status="ok"):
    if status != "ok":
        return "execution_failure"
    if reference is None:
        return "not_identified_control"
    if direction is None:
        return "abstention"
    return "correct" if direction == reference else "wrong"


def summary(rows):
    counts = {k: sum(r["outcome"] == k for r in rows) for k in KINDS}
    weight = sum(r.get("weight", 1) for r in rows)
    directional = counts["correct"] + counts["wrong"]
    return {
        "n": len(rows),
        "source_groups": (
            len({r["source_group"] for r in rows})
            if all("source_group" in r for r in rows)
            else None
        ),
        "counts": counts,
        "coverage": ratio(directional, len(rows)),
        "answered_accuracy": ratio(counts["correct"], directional),
        "correct_yield": ratio(counts["correct"], len(rows)),
        "wrong_yield": ratio(counts["wrong"], len(rows)),
        "weighted_yields": {
            k: ratio(sum(r.get("weight", 1) for r in rows if r["outcome"] == k), weight)
            for k in KINDS
        },
    }


def rank_auc(correct, wrong):
    """P(score of correct > score of wrong), half credit for ties; not calibration."""
    if not correct or not wrong:
        return None
    return sum((a > b) + 0.5 * (a == b) for a in correct for b in wrong) / (
        len(correct) * len(wrong)
    )


def safe_member(name):
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and bool(path.parts)


def verified_archive(archive=ARCHIVE, manifest_path=MANIFEST):
    """Verify every byte before temporary extraction. Reject duplicates, links and extras."""
    manifest = read(manifest_path)
    if sha(archive) != manifest["archive_sha256"]:
        raise ValueError("Archive checksum mismatch")
    entries = manifest["files"]
    expected = {e["path"]: e for e in entries}
    if len(expected) != len(entries) or any(not safe_member(p) for p in expected):
        raise ValueError("Unsafe or duplicate manifest path")
    files = {}
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not safe_member(member.name) or member.issym() or member.islnk():
                raise ValueError("Unsafe archive member")
            if member.isdir():
                continue
            if not member.isfile() or member.name in files or member.name not in expected:
                raise ValueError("Unexpected or duplicate archive member")
            data = tar.extractfile(member).read()
            entry = expected[member.name]
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("Member checksum mismatch")
            files[member.name] = data
    if set(files) != set(expected):
        raise ValueError("Missing archive member")
    return files


def materialize(files, root):
    """Copy verified bytes into a fresh TemporaryDirectory; historical paths are untouched."""
    for name, data in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)


def features(rows, training, evaluation):
    """Descriptive sample/split features; these do not modify ANM preprocessing."""
    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or data.shape[1] != 2 or not np.isfinite(data).all():
        raise ValueError("Expected finite numeric pairs")
    columns = []
    for column in data.T:
        counts = Counter(column.tolist())
        sd = float(column.std())
        columns.append(
            {
                "unique_values": len(counts),
                "unique_fraction": len(counts) / len(data),
                "largest_tie_fraction": max(counts.values()) / len(data),
                "zero_fraction": float(np.mean(column == 0)),
                "max_absolute_z": float(np.max(np.abs(column - column.mean())) / sd)
                if sd
                else None,
            }
        )
    train, test = data[list(training)], data[list(evaluation)]
    scales = train.std(axis=0)
    if not np.all(scales > 0):
        raise ValueError("Constant training column")
    return {
        "selected_rows": len(data),
        "columns": columns,
        "max_tie_fraction": max(c["largest_tie_fraction"] for c in columns),
        "duplicate_row_fraction": 1 - len(set(map(tuple, data.tolist()))) / len(data),
        "adjacent_selected_row_correlation": [
            float(np.corrcoef(data[:-1, i], data[1:, i])[0, 1])
            if data[:-1, i].std() > 0 and data[1:, i].std() > 0
            else None
            for i in range(2)
        ],
        "evaluation_exact_row_in_training_fraction": sum(
            tuple(row) in set(map(tuple, train.tolist())) for row in test
        )
        / len(test),
        "train_test_mean_shift_max_sd": float(
            np.max(np.abs(test.mean(axis=0) - train.mean(axis=0)) / scales)
        ),
        "evaluation_outside_training_range": [
            float(np.mean((test[:, i] < train[:, i].min()) | (test[:, i] > train[:, i].max())))
            for i in range(2)
        ],
    }


def verify_attempt(directory, cfg, expected=None):
    """Existing input validator + result/receipt/preprocessing arithmetic, without refitting."""
    saved = load_anm_request(directory)
    raw = read(directory / "result.json")
    result = ANMResult.model_validate(raw)
    repro = read(directory / "reproducibility.json")
    request = saved.request.model_dump(mode="json")
    request_digest = canonical_digest(request)
    if result.threshold != saved.config.threshold:
        raise ValueError("Result threshold mismatch")
    for key, value in request.items():
        if key in ("case_id", "threshold"):
            continue
        if getattr(result.provenance, key) != value:
            raise ValueError("Returned result is not bound to original request")
    if result.provenance.reproducibility_ref != canonical_digest(repro):
        raise ValueError("Reproducibility digest mismatch")
    if repro["request_digest"] != request_digest or repro["config"] != saved.config.model_dump(
        mode="json"
    ):
        raise ValueError("Reproducibility request/config mismatch")
    if (
        list(saved.training_indices) != repro["training_indices"]
        or list(saved.evaluation_indices) != repro["evaluation_indices"]
    ):
        raise ValueError("Saved split mismatch")
    if expected is not None:
        for field in ("margin", "score_ab", "score_ba", "status"):
            if field in expected and expected[field] != getattr(result, field):
                raise ValueError("Summary differs from independently saved result")
        if expected["request_digest"] != request_digest or expected[
            "result_digest"
        ] != canonical_digest(raw):
            raise ValueError("Evaluation receipt digest mismatch")
        if "result" in expected and expected["result"] != raw:
            raise ValueError("Evaluation result does not match original")
    if result.status != "ok":
        return saved, result, repro
    training = np.asarray(saved.sample.rows)[list(saved.training_indices)]
    preprocessing = repro["preprocessing"]
    for actual, recorded in (
        (training.mean(axis=0), preprocessing["training_means"]),
        (training.std(axis=0), preprocessing["training_population_stds"]),
    ):
        if not np.allclose(
            actual,
            recorded,
            rtol=cfg["numeric_relative_tolerance"],
            atol=cfg["numeric_absolute_tolerance"],
        ):
            raise ValueError("Training-only standardization mismatch")
    if expected is not None and "mse" in expected:
        for direction, value in expected["mse"].items():
            info = preprocessing["directions"][direction]
            calculated = (
                info["evaluation_residual_mean"] ** 2
                + info["evaluation_residual_population_std"] ** 2
            )
            if not math.isclose(
                calculated,
                value,
                rel_tol=cfg["numeric_relative_tolerance"],
                abs_tol=cfg["numeric_absolute_tolerance"],
            ):
                raise ValueError("Cached MSE and residual moments disagree")
    return saved, result, repro


def real_panel(root, prefix, cfg):
    inputs = read(root / prefix / "inputs.json")
    evaluations = read(root / prefix / "evaluations.json")
    cases = {r["case_id"]: r for r in inputs["cases"]}
    rows, seen = [], set()
    roster = {r["pair_id"]: r for r in read("configs/evaluation-roster.json")["pairs"]}
    for ev in evaluations:
        case = cases[ev["case_id"]]
        identity = (case["case_id"], ev["variant"], ev["split_seed"])
        if identity in seen:
            raise ValueError("Duplicate evaluated attempt")
        seen.add(identity)
        # References/group labels are evaluator-only, never used for fitting here.
        entry = roster[case["pair_id"]]
        if any(case[k] != entry[k] for k in ("source_group", "reference_direction", "weight")):
            raise ValueError("Frozen roster/evaluator mismatch")
        saved, result, repro = verify_attempt(root / prefix / ev["directory"], cfg, ev)
        if saved.request.case_id != case["case_id"] or saved.config.split_seed != ev["split_seed"]:
            raise ValueError("Case/split identity mismatch")
        order = ev["selection"]["column_order"]
        if sorted(order) != [0, 1]:
            raise ValueError("Invalid column mapping")
        mapping_seed = ev["selection"]["spec"]["mapping_seed"]
        expected_order = (
            [1, 0] if rng(mapping_seed, case["case_id"], "mapping").getrandbits(1) else [0, 1]
        )
        if order != expected_order or saved.request.ab_mapping_id != canonical_digest(
            {"case_id": case["case_id"], "order": order, "seed": mapping_seed}
        ):
            raise ValueError("Deterministic column mapping/binding mismatch")
        indices = ev["selection"]["method_indices"]
        if len(indices) != len(saved.sample.rows) or len(indices) != len(set(indices)):
            raise ValueError("Selected index count/uniqueness mismatch")
        cause = 0 if case["reference_direction"] == "first_to_second" else 1
        reference = "A_to_B" if order[0] == cause else "B_to_A"
        quality = features(saved.sample.rows, saved.training_indices, saved.evaluation_indices)
        other = "B_to_A" if reference == "A_to_B" else "A_to_B"
        rows.append(
            {
                "panel": prefix,
                "case_id": case["case_id"],
                "pair_id": case["pair_id"],
                "source_group": case["source_group"],
                "weight": case["weight"],
                "variant": ev["variant"],
                "split_seed": ev["split_seed"],
                "column_order": order,
                "reference": reference,
                "direction": result.predicted_direction,
                "status": result.status,
                "outcome": outcome(result.predicted_direction, reference, result.status),
                "margin": result.margin,
                "absolute_margin": abs(result.margin) if result.margin is not None else None,
                "score_ab": result.score_ab,
                "score_ba": result.score_ba,
                "threshold": result.threshold,
                "request_digest": ev["request_digest"],
                "sample_digest": result.provenance.sample_digest,
                "config_digest": result.provenance.config_digest,
                "method_indices": ev["selection"]["method_indices"],
                "reference_mse": ev["mse"][reference],
                "opposite_mse": ev["mse"][other],
                "reference_fit_lower_mse": ev["mse"][reference] < ev["mse"][other],
                "quality": quality,
            }
        )
    expected = {
        (c, v, s)
        for c in cases
        for v in inputs["executed_variants"]
        for s in inputs["plan"]["split_seeds"]
    }
    if seen != expected:
        raise ValueError("Incomplete saved experiment; do not infer missing observations")
    return rows


def real_diagnosis(rows, cfg):
    primary = [r for r in rows if r["split_seed"] == cfg["primary_split"]]
    if len(primary) != 38 or len(rows) != 114:
        raise ValueError("Expected exactly 38 cases and 114 dependent split outcomes")
    repeated = defaultdict(list)
    for row in rows:
        repeated[row["case_id"]].append(row)
    case_results = []
    for row in primary:
        siblings = sorted(repeated[row["case_id"]], key=lambda r: r["split_seed"])
        if len({r["sample_digest"] for r in siblings}) != 1:
            raise ValueError("Split sensitivity must keep selected sample fixed")
        signs = [(r["margin"] > 0) - (r["margin"] < 0) for r in siblings]
        case_results.append(
            {
                **row,
                "raw_sign_stable": len(set(signs)) == 1 and signs[0] != 0,
                "decision_stable": len({r["direction"] for r in siblings}) == 1,
                "wrong_all_splits": all(r["outcome"] == "wrong" for r in siblings),
                "correct_any_split": any(r["outcome"] == "correct" for r in siblings),
                "split_outcomes": {str(r["split_seed"]): r["outcome"] for r in siblings},
                "split_margins": {str(r["split_seed"]): r["margin"] for r in siblings},
            }
        )
    strata = {}
    strata["full_512"] = summary(
        [r for r in primary if r["quality"]["selected_rows"] == cfg["large_sample_size"]]
    )
    strata["fewer_than_512"] = summary(
        [r for r in primary if r["quality"]["selected_rows"] < cfg["large_sample_size"]]
    )
    for label, predicate in (
        (
            "tie_at_least_10pct",
            lambda r: r["quality"]["max_tie_fraction"] >= cfg["descriptive_tie_fraction_cutoff"],
        ),
        (
            "tie_below_10pct",
            lambda r: r["quality"]["max_tie_fraction"] < cfg["descriptive_tie_fraction_cutoff"],
        ),
    ):
        strata[label] = summary([r for r in primary if predicate(r)])
    groups = {}
    for name in sorted({r["source_group"] for r in primary}):
        selected = [r for r in primary if r["source_group"] == name]
        groups[name] = {
            **summary(selected),
            "selected_sizes": sorted({r["quality"]["selected_rows"] for r in selected}),
            "max_tie_fraction_range": [
                min(r["quality"]["max_tie_fraction"] for r in selected),
                max(r["quality"]["max_tie_fraction"] for r in selected),
            ],
        }
    margin_correct = [r["absolute_margin"] for r in primary if r["outcome"] == "correct"]
    margin_wrong = [r["absolute_margin"] for r in primary if r["outcome"] == "wrong"]
    margin_sensitivity = {}
    for group in groups:
        subset = [r for r in primary if r["source_group"] != group]
        margin_sensitivity[group] = rank_auc(
            [r["absolute_margin"] for r in subset if r["outcome"] == "correct"],
            [r["absolute_margin"] for r in subset if r["outcome"] == "wrong"],
        )
    outcome_diagnostics = {}
    for kind in KINDS:
        selected = [r for r in case_results if r["outcome"] == kind]
        outcome_diagnostics[kind] = {
            "n": len(selected),
            "raw_sign_stable": ratio(sum(r["raw_sign_stable"] for r in selected), len(selected)),
            "decision_stable": ratio(sum(r["decision_stable"] for r in selected), len(selected)),
            "wrong_all_splits": ratio(sum(r["wrong_all_splits"] for r in selected), len(selected)),
            "correct_any_split": ratio(
                sum(r["correct_any_split"] for r in selected), len(selected)
            ),
            "reference_fit_lower_mse": ratio(
                sum(r["reference_fit_lower_mse"] for r in selected), len(selected)
            ),
        }
    return {
        "primary": summary(primary),
        "splits": {
            str(s): summary([r for r in rows if r["split_seed"] == s]) for s in cfg["real_splits"]
        },
        "strata": strata,
        "source_groups": groups,
        "outcome_diagnostics": outcome_diagnostics,
        "sample_size_overlap_source_groups": [
            g
            for g in groups
            if any(n < 512 for n in groups[g]["selected_sizes"])
            and 512 in groups[g]["selected_sizes"]
        ],
        "margin": {
            "median_correct": statistics.median(margin_correct),
            "median_wrong": statistics.median(margin_wrong),
            "rank_auc": rank_auc(margin_correct, margin_wrong),
            "leave_one_source_out_auc": margin_sensitivity,
        },
        "case_results": case_results,
    }


def synthetic_diagnosis(root, cfg):
    rows = read(root / SYNTHETIC / "results.json")
    seen, checked = set(), []
    for row in rows:
        key = (row["case_id"], row["n"], row["split"])
        if key in seen:
            raise ValueError("Duplicate synthetic observation")
        seen.add(key)
        saved, result, _ = verify_attempt(root / SYNTHETIC / row["directory"], cfg, row)
        construction = read(root / SYNTHETIC / (row["case_id"] + ".json"))
        if saved.request.case_id != row["case_id"] or saved.config.split_seed != row["split"]:
            raise ValueError("Synthetic case/split identity mismatch")
        if row["compatible"] and row["reference"] != row["construction_direction"]:
            raise ValueError("Synthetic reference/construction mismatch")
        if not row["compatible"] and row["reference"] is not None:
            raise ValueError("Nonidentified control must not have direction accuracy")
        if Counter(map(tuple, saved.sample.rows)) - Counter(map(tuple, construction["rows"])):
            raise ValueError("Synthetic selected sample is not from saved construction")
        if sha(root / SYNTHETIC / (row["case_id"] + ".json")) != row["data_sha256"]:
            raise ValueError("Synthetic dataset identity mismatch")
        for field in ("case_id", "family", "partition", "compatible", "construction_direction"):
            if construction["case"][field] != row[field]:
                raise ValueError("Synthetic construction metadata mismatch")
        if (
            result.predicted_direction != row["direction"]
            or saved.request.selected_row_count != row["n"]
        ):
            raise ValueError("Synthetic original/result mismatch")
        checked.append(
            {
                **row,
                "outcome": outcome(result.predicted_direction, row["reference"], result.status)
                if row["compatible"]
                else "not_identified_control",
            }
        )
    panels, paired = [], []
    for partition in ("development", "confirmation"):
        for n in (128, 512):
            for seed in (261, 1261):
                selected = [
                    r
                    for r in checked
                    if r["partition"] == partition
                    and r["n"] == n
                    and r["split"] == seed
                    and r["compatible"]
                ]
                panels.append(
                    {"partition": partition, "n_rows": n, "split_seed": seed, **summary(selected)}
                )
        index = {
            (r["case_id"], r["n"]): r
            for r in checked
            if r["partition"] == partition and r["compatible"] and r["split"] == 261
        }
        ids = sorted({k[0] for k in index})
        transitions = Counter()
        nested = 0
        for cid in ids:
            left, right = index[cid, 128], index[cid, 512]
            transitions[left["outcome"] + "_to_" + right["outcome"]] += 1
            small = read(root / SYNTHETIC / left["directory"] / "sample.json")["rows"]
            large = read(root / SYNTHETIC / right["directory"] / "sample.json")["rows"]
            nested += not bool(Counter(map(tuple, small)) - Counter(map(tuple, large)))
        paired.append(
            {
                "partition": partition,
                "n_datasets": len(ids),
                "selected_samples_nested": nested,
                "transitions_128_to_512": dict(transitions),
            }
        )
    controls = Counter(
        (r["partition"], r["n"], r["family"], r["direction"] is not None)
        for r in checked
        if not r["compatible"] and r["split"] == 261
    )
    return {
        "verified_attempts": len(checked),
        "compatible_panels": panels,
        "paired_sample_size": paired,
        "control_counts": [
            {
                "partition": p,
                "n_rows": n,
                "family": f,
                "answered": a,
                "count": v,
                "causal_accuracy": None,
            }
            for (p, n, f, a), v in sorted(controls.items())
        ],
    }


def development_diagnosis(root, rows, large, cfg):
    cells = []
    for panel, entries in (("development", rows), ("large_sample_followup", large)):
        for variant in sorted({r["variant"] for r in entries}):
            for seed in cfg["real_splits"]:
                selected = [
                    r for r in entries if r["variant"] == variant and r["split_seed"] == seed
                ]
                cells.append(
                    {"panel": panel, "variant": variant, "split_seed": seed, **summary(selected)}
                )
    adequacy = read(root / ADEQUACY)
    selected = [r for r in adequacy["real"] if r["split_seed"] == cfg["primary_split"]]
    bindings = {(r["case_id"], r["split_seed"]): r for r in rows if r["variant"] == "baseline"}
    for row in adequacy["real"]:
        original = bindings[row["case_id"], row["split_seed"]]
        for direction, field in (("A_to_B", "score_ab"), ("B_to_A", "score_ba")):
            if not math.isclose(
                row["checks"][direction]["score"], original[field], rel_tol=1e-9, abs_tol=1e-12
            ):
                raise ValueError("Adequacy and original score disagree")
    return {
        "cells": cells,
        "adequacy_primary": selected,
        "adequacy_scope": (
            "Cached permutation outcomes only; no new permutations; "
            "nonrejection is not independence."
        ),
        "repeated_development_runs_are_not_new_datasets": True,
    }


def run_audit(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    before = {
        str(p): sha(p) for p in (ARCHIVE, MANIFEST, CONFIG, Path("configs/evaluation-roster.json"))
    }
    if before[str(ARCHIVE)] != cfg["archive_sha256"]:
        raise ValueError("Not the pinned historical archive")
    files = verified_archive()
    with tempfile.TemporaryDirectory(prefix="causalbridge-anm-diagnosis-") as directory:
        root = Path(directory)
        materialize(files, root)
        validation = real_panel(root, VALIDATION, cfg)
        dev = real_panel(root, DEVELOPMENT, cfg)
        large = real_panel(root, LARGE, cfg)
        real = real_diagnosis(validation, cfg)
        synthetic = synthetic_diagnosis(root, cfg)
        development = development_diagnosis(root, dev, large, cfg)
    after = {p: sha(p) for p in before}
    if before != after:
        raise ValueError("Original inputs changed during audit")
    metadata = read("configs/anm-failure-case-metadata.json")
    data_manifest = read("configs/pilot-data.json")
    if {c["pair_id"] for c in metadata["cases"]} != {
        r["pair_id"] for r in real["case_results"] if r["wrong_all_splits"]
    }:
        raise ValueError("Metadata review does not cover the persistent-wrong cases")
    for case in metadata["cases"]:
        if case["source_member"] != f"pair{case['pair_id']:04d}_des.txt":
            raise ValueError("Metadata source/case mismatch")
        if case["description_sha256"] != data_manifest["files"][case["source_member"]]:
            raise ValueError("Source metadata is not bound to pinned description")
    result = {
        "source_metadata_review": metadata,
        "source_sha256": {
            str(p): sha(p)
            for p in (
                Path("src/causalbridge/evaluation/anm_failure_audit.py"),
                Path("src/causalbridge/evaluation/anm_failure_report.py"),
                Path("scripts/diagnose_anm_failures.py"),
                Path("uv.lock"),
                Path("configs/anm-failure-case-metadata.json"),
                Path("configs/pilot-data.json"),
            )
        },
        "runtime": {"numpy": np.__version__, "python": __import__("platform").python_version()},
        "audit_version": cfg["version"],
        "scope": cfg["scope"],
        "archive_files_verified": len(files),
        "real_attempts_verified": len(validation) + len(dev) + len(large),
        "new_anm_fits": 0,
        "new_permutations": 0,
        "live_model_calls": 0,
        "preserved_inputs_sha256": before,
        "real": real,
        "synthetic": synthetic,
        "development": development,
    }
    write(output / "metrics.json", result)
    write(output / "real-attempts.json", validation)
    write(output / "case-results.json", real["case_results"])
    with (output / "case-results.csv").open("w", newline="") as handle:
        fields = [
            "pair_id",
            "case_id",
            "source_group",
            "outcome",
            "selected_rows",
            "max_tie_fraction",
            "absolute_margin",
            "raw_sign_stable",
            "decision_stable",
            "wrong_all_splits",
            "reference_mse",
            "opposite_mse",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in real["case_results"]:
            writer.writerow({k: row[k] if k in row else row["quality"][k] for k in fields})
    return result
