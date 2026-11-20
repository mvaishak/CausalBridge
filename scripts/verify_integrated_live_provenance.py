"""Verify every resumed Track B generation is either new live or exact saved live."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.saved_checks import journal_trials, unique_index


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def fingerprint(start):
    return canonical_digest({"messages": start["messages"], "schema": start["output_schema"]})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    run, source = args.run, args.source
    session = json.loads((run / "session.json").read_text())
    source_session = json.loads((source / "session.json").read_text())
    frozen = json.loads(Path("configs/final-track-b-integrated-38.json").read_text())
    if (
        session["model_digest"] != frozen["model_digest"]
        or source_session["model_digest"] != frozen["model_digest"]
        or session["model_config"] != source_session["model_config"]
    ):
        raise ValueError("Live sessions do not share the frozen pinned model")
    source_bytes = (source / "experiment/events.jsonl").read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != session["reuse_live_events_sha256"]:
        raise ValueError("Reused source journal changed")
    current_events = events(run / "experiment/events.jsonl")
    prior_events = events(source / "experiment/events.jsonl")
    current_starts, current_raw, current_end = journal_trials(current_events, 304)
    for start in current_starts.values():
        message_text = json.dumps(start["messages"])
        if "reference_direction" in message_text or "original_pair_id" in message_text:
            raise ValueError("Evaluator reference leaked into a model request")
    previous_starts = unique_index(
        [e["data"] for e in prior_events if e["kind"] == "native_started"], "attempt_id"
    )
    unique_index(list(previous_starts.values()), "key")
    previous_raw = {
        key: value["generation"]
        for key, value in unique_index(
            [e["data"] for e in prior_events if e["kind"] == "native_generated"], "key"
        ).items()
    }
    previous_end = unique_index(
        [e["data"] for e in prior_events if e["kind"] == "native_finished"], "key"
    )
    provenance = events(run / "generation-provenance.jsonl")
    by_fingerprint = {fingerprint(start): (key, start) for key, start in current_starts.items()}
    if len(current_starts) != 304 or len(by_fingerprint) != 304 or len(provenance) < 304:
        raise ValueError("Expected 304 unique complete request bindings")
    identities = Counter()
    seen = set()
    for record in provenance:
        kind = record["kind"]
        if kind == "transport_retry":
            continue
        key = record["request_key"]
        if key in seen or key not in by_fingerprint:
            raise ValueError("Duplicate or unplanned provenance entry")
        seen.add(key)
        current_key, current_start = by_fingerprint[key]
        if kind == "saved_live_replay":
            prior = previous_starts[record["source_attempt_id"]]
            source_execution = previous_end[prior["key"]]["execution"]
            if (
                source_execution is None
                or source_execution["failure_stage"] is not None
                or source_execution["generation"] != previous_raw[prior["key"]]
                or prior["messages"] != current_start["messages"]
                or prior["output_schema"] != current_start["output_schema"]
                or previous_raw[prior["key"]] != current_raw[current_key]
            ):
                raise ValueError("Saved live response does not bind to current exact request")
        elif kind not in {"new_live_generation", "new_live_incomplete_generation"}:
            raise ValueError("Unknown generation provenance")
        if current_end[current_key]["execution"] is None:
            raise ValueError("Generation has no completed native trace")
        identities[kind] += 1
    if len(seen) != 304:
        raise ValueError("A planned generation has no provenance entry")
    summary = json.loads((run / "run-summary.json").read_text())
    if identities["saved_live_replay"] != summary["saved_live_replays"] or (
        identities["new_live_generation"] + identities["new_live_incomplete_generation"]
        != summary["actual_new_ollama_calls"]
    ):
        raise ValueError("Run summary disagrees with generation provenance")
    report = {
        "passed": True,
        "scheduled_trials": 304,
        "provenance_counts": dict(identities),
        "transport_retry_events": sum(r["kind"] == "transport_retry" for r in provenance),
        "source_journal_sha256": session["reuse_live_events_sha256"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
