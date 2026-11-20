"""Bounded artificial checker controls on cached directional E4/S1 proposals.

These are mechanism checks, never estimates of natural error prevalence or
independent human validation. All changes stay in memory; originals are untouched.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from causalbridge.discovery.schemas import (
    DirectionEvidence,
    DirectionPrediction,
    DisplayRowClaim,
    canonical_digest,
)
from causalbridge.evaluation.diagnosis import load_experiment_receipts
from causalbridge.llm.parser import reject_duplicate_keys
from causalbridge.verifier.bindings import VerificationContext
from causalbridge.verifier.checks import check_prediction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.pilot.resolve()):
        parser.error("Write a new report outside the original pilot")
    journal = args.pilot / "experiment/events.jsonl"
    before = hashlib.sha256(journal.read_bytes()).hexdigest()
    load_experiment_receipts(journal)
    events = [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in journal.read_text().splitlines()
    ]
    starts = {e["data"]["key"]: e["data"] for e in events if e["kind"] == "native_started"}
    expected = {
        "removed_E4_method": "invalid_evidence",
        "stale_request_sample_digest": "method_sample_mismatch",
        "reversed_method_citation": "method_direction_mismatch",
        "unavailable_display_row": "row_unavailable",
    }
    trials, controls, abstentions = [], 0, 0
    for event in events:
        if event["kind"] != "native_finished":
            continue
        end = event["data"]
        start = starts[end["key"]]
        if (
            start["condition"]["condition_id"] != "S1"
            or start["package"]["evidence"]["package"] != "E4"
        ):
            continue
        execution = end["execution"]
        evidence = DirectionEvidence.model_validate(execution["evidence"])
        proposal = DirectionPrediction.model_validate(execution["prediction"])
        context = VerificationContext.model_validate(end["context"])
        if proposal.abstained:
            abstentions += 1
            continue
        control = check_prediction(evidence, proposal, context=context)
        if control.status != "pass" or not control.release:
            raise ValueError("Original directional control does not pass")
        controls += 1
        claims = list(proposal.claims)
        method_index = next(i for i, claim in enumerate(claims) if claim.type == "method_direction")
        old = claims[method_index]
        claims[method_index] = old.model_copy(
            update={"direction": "A_to_B" if old.direction == "B_to_A" else "B_to_A"}
        )
        reversed_proposal = proposal.model_copy(update={"claims": tuple(claims)})
        bad_row = DisplayRowClaim(
            type="display_row",
            evidence_ref="display_rows",
            row_index=len(evidence.display_rows),
            values=(0.0, 0.0),
        )
        row_proposal = proposal.model_copy(update={"claims": (*proposal.claims, bad_row)})

        def bind(new_proposal, original_context=context):
            # Explicit synthetic receipt for the altered proposal, so detection
            # must inspect the citation rather than merely reject an old hash.
            return original_context.model_copy(
                update={"proposal_digest": canonical_digest(new_proposal.model_dump(mode="json"))}
            )

        variants = [
            (
                "removed_E4_method",
                evidence.model_copy(update={"method_result": None}),
                proposal,
                context,
            ),
            (
                "stale_request_sample_digest",
                evidence,
                proposal,
                context.model_copy(
                    update={
                        "method_request": context.method_request.model_copy(
                            update={"sample_digest": "sha256:" + "a" * 64}
                        )
                    }
                ),
            ),
            ("reversed_method_citation", evidence, reversed_proposal, bind(reversed_proposal)),
            ("unavailable_display_row", evidence, row_proposal, bind(row_proposal)),
        ]
        for name, supplied, prediction, receipt in variants:
            checked = check_prediction(supplied, prediction, context=receipt)
            if (
                checked.status != "fail"
                or checked.release
                or expected[name] not in checked.reason_codes
            ):
                raise ValueError("Unexpected mechanism outcome: " + name)
            trials.append(
                dict(
                    case_id=evidence.case_id,
                    source_attempt_id=start["attempt_id"],
                    perturbation=name,
                    status=checked.status,
                    release=checked.release,
                    reason_codes=list(checked.reason_codes),
                    expected_code=expected[name],
                )
            )
    if controls == 0 or hashlib.sha256(journal.read_bytes()).hexdigest() != before:
        raise ValueError("No eligible controls or changed original journal")
    result = dict(
        scope="artificial_process_mechanism_controls_not_natural_error_rate",
        unchanged_directional_controls_passed=controls,
        excluded_original_abstentions=abstentions,
        artificial_trials=len(trials),
        rejection_counts=dict(Counter(t["perturbation"] for t in trials)),
        expected_codes=expected,
        trials=trials,
        source_journal_sha256=before,
        model_calls=0,
        anm_fits=0,
        note=(
            "Removed E4 method is rejected at schema validation. Only directional parents "
            "are eligible. Rebinding altered proposals is synthetic, "
            "not an edit to original cache receipts."
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "trials"}, indent=2))


if __name__ == "__main__":
    main()
