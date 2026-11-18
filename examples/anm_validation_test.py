"""Explicitly authorized descriptive test of one fixed ANM on the real holdout.

No tuning or invented acceptance gate. Opening these results consumes this
holdout for future method selection. Originals and previous runs stay unchanged.
"""

import argparse
import hashlib
import json
from pathlib import Path

from causalbridge.discovery.anm_requests import read_json, write_json_exclusive
from causalbridge.discovery.schemas import canonical_digest
from causalbridge.discovery.study import Plan, _destination, _execute, _source_digest
from causalbridge.evaluation.roster import check_roster


def run(snapshot, manifest, roster, plan, output):
    plan = Plan.model_validate(plan)
    chosen = next((v for v in plan.variants if v.name == "sample_512"), None)
    if (
        chosen is None
        or chosen.sample_limit != 512
        or chosen.kernel_gamma != 1.0
        or chosen.ridge_alpha != 0.1
        or plan.threshold != 0.001
    ):
        raise ValueError("This test is fixed at 512 rows, gamma=1, alpha=0.1, threshold=0.001")
    if plan.split_seeds != (261, 1261, 2261) or plan.primary_split != 261:
        raise ValueError("This test uses the three predeclared splits, primary 261")
    snapshot = Path(snapshot).resolve()
    check_roster(manifest, snapshot, roster)
    selected = [c for c in roster["pairs"] if c["anm_use"] == "validation" and c["scorable"]]
    if not selected:
        raise ValueError("No assigned validation cases")
    output = _destination(output, snapshot)
    output.mkdir(parents=True, exist_ok=False)
    protocol = dict(
        scope="user-authorized descriptive held-out test; no acceptance gate",
        chosen_variant=chosen.model_dump(mode="json"),
        plan=plan.model_dump(mode="json"),
        case_ids=[c["pair_id"] for c in selected],
        manifest_digest=canonical_digest(manifest),
        roster_digest=canonical_digest(roster),
        package_source_digest=_source_digest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        warning="These outcomes must not select a later method while retaining a held-out claim.",
    )
    write_json_exclusive(output / "protocol.json", protocol)
    summary = _execute(
        snapshot, manifest, roster, plan, output / "execution", "validation", chosen.name
    )
    records = read_json(output / "execution/evaluations.json")
    if {r["variant"] for r in records} != {chosen.name}:
        raise ValueError("An unplanned configuration was evaluated")
    primary = [r for r in records if r["split_seed"] == plan.primary_split]
    report = dict(
        scope=protocol["scope"],
        holdout_opened=True,
        case_count=len(selected),
        source_group_count=len({c["source_group"] for c in selected}),
        primary_split=plan.primary_split,
        metrics=summary["variants"][0]["primary"],
        splits=summary["variants"][0]["splits"],
        sign_stability=summary["variants"][0]["sign_stability"],
        selected_rows=dict(
            minimum=min(r["result"]["provenance"]["selected_row_count"] for r in primary),
            maximum=max(r["result"]["provenance"]["selected_row_count"] for r in primary),
            fewer_than_512=sum(
                r["result"]["provenance"]["selected_row_count"] < 512 for r in primary
            ),
        ),
        decision="No performance pass/fail threshold was supplied; report observations only.",
    )
    write_json_exclusive(output / "report.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "manifest", "roster", "plan", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    print(
        json.dumps(
            run(
                a.snapshot, read_json(a.manifest), read_json(a.roster), read_json(a.plan), a.output
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
