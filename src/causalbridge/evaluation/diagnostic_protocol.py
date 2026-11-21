"""Isolated controlled-cue protocol. Never fabricates an ANM result or receipt."""

import hashlib
import json
import random
import subprocess
import zipfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from causalbridge.discovery.schemas import Direction, canonical_digest

PILOT = Path("artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip")
ABLATION = Path("artifacts/qwen3-thinking-ablation-8192-4096-01/run-records.tar.gz")
CONFIG = Path("configs/diagnostic-investigation-v1.json")
SYSTEM = (
    "Assess which causal direction is more plausible between A and B using the supplied "
    "names and measurements. You may abstain. An external directional diagnostic, when "
    "present, is an experimental cue, not a verified ANM artifact or proof of causation. "
    "You may agree or disagree. Return JSON matching the supplied schema. Report the "
    "direction cited by the diagnostic in diagnostic_direction_cited, or null if you do "
    "not cite it. evidence_basis lists the information used, not proof that it is valid. "
    "If you list diagnostic as a basis, cite its supplied direction exactly. "
    "Keep explanation concise; do not invent diagnostic scores or evidence."
)


class CuePrediction(BaseModel):
    """Same required fields in every arm; identity is bound in code, not copied by the model."""

    model_config = ConfigDict(extra="forbid")
    predicted_direction: Direction | None
    abstained: StrictBool
    diagnostic_direction_cited: Direction | None
    evidence_basis: list[
        Literal["measurements", "variable_names", "diagnostic", "background_knowledge"]
    ] = Field(max_length=4)
    explanation: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def consistent(self):
        if self.abstained != (self.predicted_direction is None):
            raise ValueError("abstained must match null direction")
        if len(self.evidence_basis) != len(set(self.evidence_basis)):
            raise ValueError("duplicate evidence bases")
        return self


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    """Atomic write inside a separately created attempt directory."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def opposite(direction):
    return "B_to_A" if direction == "A_to_B" else "A_to_B"


def pilot_source():
    """Read archived messages and evaluator-only mapping; never rewrite archives."""
    if sha(PILOT) != "b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a":
        raise ValueError("Original pilot checksum mismatch")
    with zipfile.ZipFile(PILOT) as z:
        events = [
            json.loads(line)
            for line in z.read("real-pilot-01/experiment/events.jsonl").splitlines()
        ]
        mappings = {
            r["case_id"]: r for r in json.loads(z.read("real-pilot-01/evaluation_mapping.json"))
        }
    starts = {
        (
            e["data"]["package"]["evidence"]["case_id"],
            e["data"]["package"]["evidence"]["package"],
            e["data"]["condition"]["condition_id"],
        ): e["data"]
        for e in events
        if e["kind"] == "native_started"
    }
    truth = read("artifacts/final-delivery/track-b-pilot/evaluator-records.json")
    cases = []
    for record in sorted(truth, key=lambda r: r["case_id"]):
        cid = record["case_id"]
        cause = 0 if record["reference_direction"] == "first_to_second" else 1
        gold = (
            "A_to_B" if mappings[cid]["original_to_runtime_column_order"][0] == cause else "B_to_A"
        )
        e3 = starts[cid, "E3", "S0"]["package"]["evidence"]
        e4 = starts[cid, "E4", "S0"]["package"]["evidence"]
        cases.append(
            {
                "case_id": cid,
                "gold": gold,
                "source_group": record["source_group"],
                "weight": record["weight"],
                "anm_direction": e4["method_result"]["predicted_direction"],
                "evidence": {
                    k: e3[k] for k in ("variable_labels", "units", "display_rows", "summary")
                },
            }
        )
    if len(cases) != 17 or len(starts) != 136:
        raise ValueError("Unexpected frozen pilot size")
    return cases, starts


def synthetic_cases():
    """Two fixed software/preflight fixtures, never part of research denominators."""
    return [
        {
            "case_id": f"PREFLIGHT_{i}",
            "gold": direction,
            "source_group": f"fixture_{i}",
            "weight": 1.0,
            "anm_direction": direction,
            "evidence": {
                "variable_labels": ["A", "B"],
                "units": [None, None],
                "display_rows": [[0.0, 0.2], [1.0, 1.3], [2.0, 3.8]],
                "summary": {"n_display": 3},
            },
        }
        for i, direction in enumerate(("A_to_B", "B_to_A"))
    ]


def source_hashes():
    paths = [
        CONFIG,
        PILOT,
        ABLATION,
        Path("configs/evaluation-roster.json"),
        Path("artifacts/final-delivery/track-b-pilot/evaluator-records.json"),
        Path("scripts/diagnostic_investigation.py"),
    ]
    paths += sorted(Path("src/causalbridge").rglob("*.py"))
    return {str(p): sha(p) for p in paths}


def request_payload(case, arm, think, cfg):
    """Build only model-visible fields; no correctness/source-group metadata."""
    cue = (
        None
        if arm == "no_diagnostic"
        else (opposite(case["gold"]) if arm.startswith("wrong") else case["gold"])
    )
    diagnostic = (
        None
        if cue is None
        else {
            "kind": "experimental_directional_cue",
            "direction": cue,
            "limitations": cfg["warning"] if arm.endswith("qualified") else None,
        }
    )
    user = {
        "question": "Which direction is more plausible, A to B or B to A? You may abstain.",
        "evidence": case["evidence"],
        "external_diagnostic": diagnostic,
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(user, sort_keys=True, allow_nan=False)},
        ],
        "format": CuePrediction.model_json_schema(),
        "stream": False,
        "think": think,
        "options": {
            "temperature": cfg["temperature"],
            "seed": cfg["seed"],
            "num_ctx": cfg["num_ctx"],
            "num_predict": cfg["num_predict"],
        },
    }
    return payload


def prepare(output, *, preflight=False):
    """Freeze requests separately from evaluator labels and experimental arm metadata."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(CONFIG)
    cases = synthetic_cases() if preflight else pilot_source()[0]
    rng = random.Random(cfg["order_seed"])
    requests, evaluator = [], []
    for case in cases:
        cells = [(arm, think) for arm in cfg["conditions"] for think in cfg["thinking_settings"]]
        rng.shuffle(cells)
        for arm, think in cells:
            cue = (
                None
                if arm == "no_diagnostic"
                else (opposite(case["gold"]) if arm.startswith("wrong") else case["gold"])
            )
            payload = request_payload(case, arm, think, cfg)
            identity = canonical_digest({"case_id": case["case_id"], "payload": payload})
            requests.append({"trial_id": identity, "payload": payload})
            evaluator.append(
                {
                    "trial_id": identity,
                    "case_id": case["case_id"],
                    "arm": arm,
                    "think": think,
                    "gold": case["gold"],
                    "weight": case["weight"],
                    "source_group": case["source_group"],
                    "cue_direction": cue,
                }
            )
    hashes = source_hashes()
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    roster = read("configs/evaluation-roster.json")
    manifest = {
        "protocol": cfg,
        "phase": "preflight" if preflight else "full",
        "scope": "synthetic software fixtures" if preflight else cfg["inference_scope"],
        "scheduled": len(requests),
        "case_count": len(cases),
        "source_commit": revision,
        "runtime_versions": {
            "python": __import__("platform").python_version(),
            "pydantic": __import__("pydantic").__version__,
            "httpx": __import__("httpx").__version__,
        },
        "source_sha256": hashes,
        "requests_digest": canonical_digest(requests),
        "evaluator_digest": canonical_digest(evaluator),
        "eligibility": {
            "roster_counts": roster["counts"],
            "documented_untouched_pool": 0,
            "confirmatory": False,
            "reason": (
                "Pilot and validation outcomes opened; development is not holdout;"
                " 49 excluded pairs are unscorable."
            ),
        },
    }
    write(output / "requests.json", requests)
    write(output / "evaluator.json", evaluator)
    write(output / "manifest.json", manifest)
    return manifest


def validate_plan(plan):
    """Reconstruct frozen cells, catching leaked evaluator fields or modified requests."""
    plan = Path(plan)
    manifest = read(plan / "manifest.json")
    cfg = manifest["protocol"]
    if cfg != read(CONFIG) or manifest["source_sha256"] != source_hashes():
        raise ValueError("Protocol/source bytes changed; create a new protocol/plan")
    requests, evaluator = read(plan / "requests.json"), read(plan / "evaluator.json")
    if (
        canonical_digest(requests) != manifest["requests_digest"]
        or canonical_digest(evaluator) != manifest["evaluator_digest"]
    ):
        raise ValueError("Plan binding mismatch")
    if manifest["phase"] not in ("preflight", "full"):
        raise ValueError("Unknown phase")
    cases = synthetic_cases() if manifest["phase"] == "preflight" else pilot_source()[0]
    by_case = {c["case_id"]: c for c in cases}
    if len(requests) != manifest["scheduled"] or len(requests) != len(evaluator):
        raise ValueError("Scheduled trial mismatch")
    if len({r["trial_id"] for r in requests}) != len(requests):
        raise ValueError("Duplicate trials")
    cells = set()
    for req, meta in zip(requests, evaluator, strict=True):
        cid, arm, think = meta["case_id"], meta["arm"], meta["think"]
        case = by_case[cid]
        if arm not in cfg["conditions"] or type(think) is not bool:
            raise ValueError("Invalid factorial cell")
        if req["payload"] != request_payload(case, arm, think, cfg):
            raise ValueError("Payload differs from frozen protocol")
        if meta["source_group"] != case["source_group"] or meta["weight"] != case["weight"]:
            raise ValueError("Evaluator group/weight mismatch")
        cue = (
            None
            if arm == "no_diagnostic"
            else (opposite(case["gold"]) if arm.startswith("wrong") else case["gold"])
        )
        if meta["gold"] != case["gold"] or meta["cue_direction"] != cue:
            raise ValueError("Evaluator direction mismatch")
        if req["trial_id"] != meta["trial_id"] or req["trial_id"] != canonical_digest(
            {"case_id": cid, "payload": req["payload"]}
        ):
            raise ValueError("Request identity mismatch")
        user = json.loads(req["payload"]["messages"][1]["content"])
        if (
            set(user) != {"question", "evidence", "external_diagnostic"}
            or user["evidence"] != case["evidence"]
        ):
            raise ValueError("Evidence changed or evaluator metadata leaked")
        expected_diag = (
            None
            if cue is None
            else {
                "kind": "experimental_directional_cue",
                "direction": cue,
                "limitations": cfg["warning"] if arm.endswith("qualified") else None,
            }
        )
        if user["external_diagnostic"] != expected_diag or req["payload"]["think"] != think:
            raise ValueError("Wrong controlled cue")
        cells.add((cid, arm, think))
    if cells != {
        (c, arm, think)
        for c in by_case
        for arm in cfg["conditions"]
        for think in cfg["thinking_settings"]
    }:
        raise ValueError("Incomplete factorial design")
    return manifest, requests
