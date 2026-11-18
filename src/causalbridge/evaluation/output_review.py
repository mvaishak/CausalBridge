"""Read-only pilot intake and evidence tables for human output review. No inference."""

import argparse
import hashlib
import json
from pathlib import Path

from causalbridge.discovery.anm_requests import read_json, write_json_exclusive
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows
from causalbridge.llm.parser import reject_duplicate_keys


def _lines(path):
    return [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]


def _inventory(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _identity(row):
    return row["case_id"], row["package"], row["condition"]


def _verify_analysis(saved, generated):
    def indexed(rows):
        result = {_identity(row): row for row in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate scheduled analysis row")
        return result

    if indexed(saved) != indexed(generated):
        raise ValueError("Analysis export differs from original experiment outcomes")


def _tables(run, releases):
    proposals, decisions = [], []
    by_parent = {row["source_key"]: row for row in releases}
    for trial in run["trials"]:
        start, end = trial["start"], trial["outcome"]
        execution = end.get("execution") or {}
        prediction = execution.get("prediction") or {}
        generation = execution.get("generation") or {}
        evidence = start["package"]["evidence"]
        locator = f"experiment/exports/{run['manifest_id']}.json"
        item = dict(
            review_id=start["attempt_id"],
            case_id=evidence["case_id"],
            package=evidence["package"],
            condition=start["condition"]["condition_id"],
            package_digest=start["receipt"]["package_digest"],
            artifact_locator=locator,
            source_key=start["key"],
            failure_stage=execution.get("failure_stage") or end.get("operational_error"),
            structured_direction=prediction.get("predicted_direction"),
            abstained=prediction.get("abstained"),
            visible_reason=prediction.get("reason_code"),
            raw_response_text=generation.get("text"),
            claims=prediction.get("claims", []),
            supplied_evidence=evidence,
            consistency_label="pending",
            decisive_excerpt="",
            review_rationale="",
            reviewer="",
        )
        proposals.append(item)
        if item["condition"] == "S1":
            release = by_parent[start["key"]]
            check = release.get("check")
            decisions.append(
                dict(
                    review_id=start["attempt_id"],
                    case_id=item["case_id"],
                    package=item["package"],
                    parent_attempt_id=start["attempt_id"],
                    parent_source_key=start["key"],
                    s1_direction=item["structured_direction"],
                    released_direction=release["released_direction"],
                    skip_reason=release.get("skip_reason"),
                    checker_status=check.get("status") if check else None,
                    reason_codes=check.get("reason_codes", []) if check else [],
                    claim_findings=check.get("claim_findings", []) if check else [],
                    claims=item["claims"],
                    supplied_evidence=evidence,
                    artifact_locator=f"experiment/exports/{run['manifest_id']}-s2.json",
                    process_review_label="pending",
                    review_rationale="",
                    reviewer="",
                )
            )
    return proposals, decisions


def prepare_review(bundle, output, *, expected_cases=17):
    """Verify a complete single-manifest pilot; write separate, unlabelled review tables.

    A failing intake writes only intake.json. Existing absolute ANM references
    must resolve; relocation is never implemented by rewriting originals.
    Labels and reference directions are intentionally absent during first review.
    """
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if not bundle.is_dir():
        raise ValueError("Pilot bundle directory is missing")
    if output.exists():
        raise FileExistsError("Review output must be a fresh directory")
    if bundle == output or bundle in output.parents:
        raise ValueError("Review output must be outside the original bundle")
    if type(expected_cases) is not int or expected_cases < 1:
        raise ValueError("Expected cases must be a positive integer")
    before = _inventory(bundle)
    required = (
        "session.json",
        "analysis.jsonl",
        "evaluation_mapping.json",
        "experiment/events.jsonl",
    )
    missing = [name for name in required if not (bundle / name).is_file()]
    report = dict(
        version="pilot-output-review-v1",
        passed=False,
        source_bundle=str(bundle),
        expected_case_count=expected_cases,
        source_files_sha256=before,
        missing_files=missing,
        findings=[],
        notes=[
            "Human review labels remain pending; no contradiction detector or new model calls.",
            "Intake does not certify source eligibility, label joins or causal correctness.",
            "Unresolved original ANM paths block audit; do not rewrite historical receipts.",
        ],
    )
    proposals = decisions = None
    if not missing:
        try:
            read_json(bundle / "session.json")
            saved = _lines(bundle / "analysis.jsonl")
            manifests = {row["manifest_id"] for row in saved}
            if len(manifests) != 1:
                raise ValueError("Review requires exactly one analysis manifest")
            manifest = manifests.pop()
            # Digest identifiers are local basenames, never arbitrary paths.
            if (
                not isinstance(manifest, str)
                or Path(manifest).name != manifest
                or manifest in {".", ".."}
            ):
                raise ValueError("Invalid manifest identifier")
            run = read_json(bundle / "experiment/exports" / (manifest + ".json"))
            releases = read_json(bundle / "experiment/exports" / (manifest + "-s2.json"))
            audit = audit_native(bundle / "experiment")
            report["native_audit"] = audit
            if not audit["passed"]:
                raise ValueError("Native artifact audit failed; inspect native_audit findings")
            _verify_analysis(saved, analysis_rows(run, releases))
            proposals, decisions = _tables(run, releases)
            cases = {p["case_id"] for p in proposals}
            expected = {
                (case, package, condition)
                for case in cases
                for package in ("E1", "E2", "E3", "E4")
                for condition in ("S0", "S1")
            }
            actual = [_identity(p) for p in proposals]
            if (
                len(cases) != expected_cases
                or len(actual) != len(set(actual))
                or set(actual) != expected
            ):
                raise ValueError(
                    "Original trials do not match the expected complete E1–E4/S0–S1 schedule"
                )
            mappings = read_json(bundle / "evaluation_mapping.json")
            mapping_cases = [m["case_id"] for m in mappings]
            if len(mapping_cases) != len(set(mapping_cases)) or set(mapping_cases) != cases:
                raise ValueError("Mapping cases differ from original trial cases")
            by_case = {m["case_id"]: m for m in mappings}
            for trial in run["trials"]:
                start = trial["start"]
                selected = start["package"]["selected"]["selection"]
                mapping = by_case[start["receipt"]["case_id"]]
                order = mapping["original_to_runtime_column_order"]
                if (
                    type(mapping["mapping_seed"]) is not int
                    or not isinstance(order, list)
                    or len(order) != 2
                    or any(type(column) is not int for column in order)
                    or sorted(order) != [0, 1]
                ):
                    raise ValueError("Mapping requires exact integer seed and columns")
                if (
                    mapping["ab_mapping_id"] != start["receipt"]["ab_mapping_id"]
                    or mapping["mapping_seed"] != selected["spec"]["mapping_seed"]
                    or mapping["original_to_runtime_column_order"] != selected["column_order"]
                    or mapping["source_digest"] != selected["source_digest"]
                ):
                    raise ValueError("Mapping differs from original selection receipt")
            report.update(
                passed=True,
                manifest_id=manifest,
                case_count=len(cases),
                proposal_count=len(proposals),
                checker_decision_count=len(decisions),
                checker_rejection_count=sum(d["checker_status"] == "fail" for d in decisions),
                checker_error_count=sum(d["skip_reason"] == "checker_error" for d in decisions),
                review_status="pending_human_annotations",
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            report["findings"].append(f"{type(exc).__name__}: {exc}")
    report["original_files_unchanged"] = before == _inventory(bundle)
    if not report["original_files_unchanged"]:
        report["passed"] = False
        report["findings"].append("Original bundle changed during intake")
    output.mkdir(parents=True, exist_ok=False)
    if report["passed"]:
        for filename, rows in (
            ("proposals.jsonl", proposals),
            ("checker-decisions.jsonl", decisions),
        ):
            with (output / filename).open("x") as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    write_json_exclusive(output / "intake.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-cases", type=int, default=17)
    args = parser.parse_args()
    report = prepare_review(args.bundle, args.output, expected_cases=args.expected_cases)
    print(json.dumps({key: report[key] for key in ("passed", "missing_files", "findings")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
