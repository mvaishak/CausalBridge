"""Offline loader/package/execution/export/join acceptance; no live model or scorer."""

import argparse
import hashlib
import json
from pathlib import Path

from causalbridge.discovery.anm_requests import ANMConfig
from causalbridge.discovery.contracts import SelectionSpec
from causalbridge.discovery.evidence import select_pair
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows, evaluator_mapping
from causalbridge.evaluation.handoff import validate_loader_handoff
from causalbridge.evaluation.integration import (
    COMPACT_PROTOCOL,
    NATIVE_CAUTION,
    IntegratedRunner,
    build_native_packages,
)
from causalbridge.evaluation.joins import join_evaluator_records
from causalbridge.llm.client import Generation

CAUSE_COLUMNS = dict(
    zip((f"D{i:04d}" for i in range(201, 209)), (1, 1, 1, 0, 1, 1, 1, 1), strict=True)
)
PROJECTION_FIELDS = (
    "case_id",
    "source_group",
    "weight",
    "split",
    "reference_direction",
    "package",
    "condition",
    "predicted_direction",
    "reference_agreement",
    "failure_stage",
    "outcome",
    "reason_codes",
)


class AcceptanceModel:
    """Fixed scripted replies keyed only by runtime case/package/condition.

    Never reads evaluator labels or expected metric files. Deliberate bad
    citations test mechanism behavior, not natural model-error prevalence.
    """

    def __init__(self):
        self.calls = 0

    def generate(self, messages, schema):
        self.calls += 1
        user = json.loads(messages[1]["content"])
        case, evidence = user["case_id"], user["evidence"]
        if case == "D0206":
            raise TimeoutError("synthetic acceptance timeout")
        if case == "D0207":
            return Generation(text="not JSON", model="scripted-scorer-acceptance")
        # S1's existing caution paragraph identifies the condition, not an oracle.
        s1 = NATIVE_CAUTION in messages[0]["content"]
        direction = "B_to_A" if case in {"D0202", "D0204"} else "A_to_B"
        if case == "D0205":
            direction = None
        if not s1 and evidence["package"] in {"E3", "E4"}:
            if case == "D0202":
                direction = "A_to_B"
            if case == "D0205":
                direction = "B_to_A"
        claims = []
        if (s1 and case in {"D0202", "D0203"}) or case == "D0208":
            claims.append(
                dict(
                    type="display_row",
                    evidence_ref="display_rows",
                    row_index=9999,
                    values=[0.0, 0.0],
                )
            )
        reply = dict(
            case_id="D9999" if case == "D0208" else case,
            package_digest=user["package_digest"],
            predicted_direction=direction,
            abstained=direction is None,
            reason_code="fixture_abstention" if direction is None else None,
            claims=claims,
        )
        return Generation(text=json.dumps(reply), model="scripted-scorer-acceptance")


def run_acceptance(output: Path, fixtures: Path):
    """Fresh output only; verify resume inside the same frozen execution session."""
    output, fixtures = Path(output), Path(fixtures)
    oracle = json.loads((fixtures / "expected.json").read_text())
    expected = json.loads((fixtures / "joined_rows.json").read_text())
    runtime, evaluator = validate_loader_handoff(
        [
            dict(
                case_id=c["case_id"],
                variables=[dict(name="Measurement one"), dict(name="Measurement two")],
                rows=[[1.0, 2.0], [2.0, 5.0], [3.0, 9.0]],
            )
            for c in oracle["cases"]
        ],
        [
            dict(
                case_id=c["case_id"],
                source_group=c["source_group"],
                weight=c["weight"],
                split=c["split"],
                cause_column=CAUSE_COLUMNS[c["case_id"]],
            )
            for c in oracle["cases"]
        ],
    )
    output.mkdir(parents=True, exist_ok=False)
    packages = tuple(
        p
        for pair in runtime
        for p in build_native_packages(
            select_pair(pair, SelectionSpec(mapping_seed=0, method_limit=8, display_limit=3)),
            output / "anm" / pair.case_id,
            ANMConfig(minimum_rows=8, maximum_rows=8, sampling_seed=262),
        )
    )
    runner = IntegratedRunner(
        output / "experiment",
        model_identity="scripted-scorer-acceptance-v1",
        model_mode="scripted_fixture",
        observation_kind="synthetic",
        identity_verified=True,
        protocol=COMPACT_PROTOCOL,
    )
    model = AcceptanceModel()
    run = runner.run(packages, model)
    before_s2 = model.calls
    releases = runner.replay_s2(run["manifest_id"])
    if model.calls != before_s2:
        raise ValueError("S2 issued model calls")
    resumed = runner.run(packages, model)
    journal = runner.store.path.read_bytes()
    repeated = runner.replay_s2(run["manifest_id"])
    if model.calls != before_s2 or resumed["new_model_calls"] != 0:
        raise ValueError("Resume issued model calls")
    if repeated != releases or runner.store.path.read_bytes() != journal:
        raise ValueError("Repeated S2 changed saved outcomes")
    schedule = {
        (run["manifest_id"], pair.case_id, p, c)
        for pair in runtime
        for p in ("E1", "E2", "E3", "E4")
        for c in ("S0", "S1", "S2", "SIMPLE_GATE")
    }
    schedule |= {(run["manifest_id"], pair.case_id, "E4", "ANM_ONLY") for pair in runtime}
    exports = analysis_rows(run, releases)
    mappings = evaluator_mapping(packages)
    joined = join_evaluator_records(exports, mappings, runtime, evaluator, expected_slots=schedule)

    def project(rows):
        return [{k: row[k] for k in PROJECTION_FIELDS} for row in rows]

    if project(joined) != project(expected):
        raise ValueError("Pipeline projection differs from hand-calculated fixture input")
    audit = audit_native(output / "experiment")
    if not audit["passed"]:
        raise ValueError(f"Independent audit failed: {audit['findings']}")
    report = dict(
        acceptance_version="track-b-offline-acceptance-v1",
        manifest_id=run["manifest_id"],
        new_model_calls=run["new_model_calls"],
        scripted_calls=model.calls,
        s2_new_model_calls=0,
        resumed_new_model_calls=resumed["new_model_calls"],
        cases=len(runtime),
        package_count=len(packages),
        s2_records=len(releases),
        checked_parents=sum(r["check"] is not None for r in releases),
        skipped_parents=sum(r["check"] is None for r in releases),
        analysis_rows=len(joined),
        fixture_projection_matches=True,
        audit_passed=audit["passed"],
        fixtures_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(fixtures.glob("*.json"))
        },
        limitations=[
            "Synthetic scripted mechanism fixture, not real data or accuracy.",
            "Three-row ANM inputs intentionally yield insufficient_rows.",
            "Matches scorer input oracle; Faizah's actual scorer is not exercised.",
        ],
    )
    for name, value in dict(
        report=report,
        audit=audit,
        analysis=exports,
        mappings=mappings,
        joined=list(joined),
        runtime=[r.model_dump(mode="json") for r in runtime],
        evaluator=[r.model_dump(mode="json") for r in evaluator],
    ).items():
        (output / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_acceptance(args.output, args.fixtures), indent=2))


if __name__ == "__main__":
    main()
