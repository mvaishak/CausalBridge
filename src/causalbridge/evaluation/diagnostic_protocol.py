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


class CueDecisionV2(BaseModel):
    """One generated decision; internal direction/abstention are derived, never repaired."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["A_to_B", "B_to_A", "abstain"]
    diagnostic_direction_cited: Direction | None
    evidence_basis: list[
        Literal["measurements", "variable_names", "diagnostic", "background_knowledge"]
    ] = Field(max_length=4, json_schema_extra={"uniqueItems": True})
    explanation: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def unique_bases(self):
        if len(self.evidence_basis) != len(set(self.evidence_basis)):
            raise ValueError("duplicate evidence bases")
        return self

    def normalized(self):
        fields = self.model_dump(mode="json", exclude={"decision"})
        direction = None if self.decision == "abstain" else self.decision
        return CuePrediction(
            predicted_direction=direction, abstained=direction is None, **fields
        ).model_dump(mode="json")


class EvidenceBasisV3(BaseModel):
    """Required flags avoid an array uniqueness rule unsupported by some decoders."""

    model_config = ConfigDict(extra="forbid")
    measurements: StrictBool
    variable_names: StrictBool
    diagnostic: StrictBool
    background_knowledge: StrictBool


class CueDecisionV3(BaseModel):
    """V2 decision semantics with a strict boolean evidence basis object."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["A_to_B", "B_to_A", "abstain"]
    diagnostic_direction_cited: Direction | None
    evidence_basis: EvidenceBasisV3
    explanation: str = Field(min_length=1, max_length=4000)

    def normalized(self):
        direction = None if self.decision == "abstain" else self.decision
        bases = self.evidence_basis.model_dump()
        return CuePrediction(
            predicted_direction=direction,
            abstained=direction is None,
            diagnostic_direction_cited=self.diagnostic_direction_cited,
            evidence_basis=[name for name in EvidenceBasisV3.model_fields if bases[name]],
            explanation=self.explanation,
        ).model_dump(mode="json")


SYSTEM_V2 = SYSTEM + (
    " Use exactly one decision field: A_to_B means predict A causes B; "
    "B_to_A means predict B causes A; abstain means decline to predict either direction. "
    "If you decline to choose, set decision to abstain. Your explanation must agree "
    "with your decision. Do not output predicted_direction or abstained fields."
)
SYSTEM_V3 = (
    "Assess which causal direction is more plausible between A and B using the supplied "
    "names and measurements. You may abstain. An external directional diagnostic, when "
    "present, is an experimental cue, not a verified ANM artifact or proof of causation. "
    "You may agree or disagree. Return JSON matching the supplied schema. Use exactly one "
    "decision: A_to_B means predict A causes B; B_to_A means predict B causes A; abstain "
    "means decline to predict either direction. Your explanation must agree with your "
    "decision. Do not output predicted_direction or abstained fields. Report the direction "
    "cited by the diagnostic in diagnostic_direction_cited, or null if you do not cite it. "
    "evidence_basis is an object with exactly four required boolean fields: measurements, "
    "variable_names, diagnostic, and background_knowledge. Set each field true if you used "
    "that kind of information, otherwise false. Do not omit fields or add others. These "
    "flags report information used, not proof that it is valid. If diagnostic is true, cite "
    "its supplied direction exactly. Keep explanation concise; do not invent diagnostic "
    "scores or evidence."
)


def config_path(protocol):
    if protocol not in ("v1", "v2", "v3"):
        raise ValueError("Unknown diagnostic protocol")
    return Path(f"configs/diagnostic-investigation-{protocol}.json")


def protocol_for(cfg):
    versions = {f"diagnostic-investigation-v{i}": f"v{i}" for i in (1, 2, 3)}
    try:
        return versions[cfg["protocol_version"]]
    except KeyError as exc:
        raise ValueError("Unknown diagnostic protocol") from exc


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


def diagnostic_cases():
    """Independent software fixtures, outside preflight and research denominators."""
    return [
        {
            "case_id": "DIAGNOSTIC_ABSENT",
            "gold": "A_to_B",
            "source_group": "diagnostic_fixture_absent",
            "weight": 1.0,
            "anm_direction": "A_to_B",
            "evidence": {
                "variable_labels": ["pump setting", "water flow"],
                "units": ["level", "liters per minute"],
                "display_rows": [[1.0, 2.2], [2.0, 3.1], [3.0, 4.2]],
                "summary": {"n_display": 3},
            },
        },
        {
            "case_id": "DIAGNOSTIC_PRESENT",
            "gold": "B_to_A",
            "source_group": "diagnostic_fixture_present",
            "weight": 1.0,
            "anm_direction": "B_to_A",
            "evidence": {
                "variable_labels": ["shade level", "panel output"],
                "units": ["index", "watts"],
                "display_rows": [[1.0, 8.0], [2.0, 7.1], [3.0, 6.0]],
                "summary": {"n_display": 3},
            },
        },
    ]


def source_hashes(protocol="v1"):
    paths = [
        config_path(protocol),
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
    protocol = protocol_for(cfg)
    contract = {"v1": CuePrediction, "v2": CueDecisionV2, "v3": CueDecisionV3}[protocol]
    prompt = {"v1": SYSTEM, "v2": SYSTEM_V2, "v3": SYSTEM_V3}[protocol]
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user, sort_keys=True, allow_nan=False)},
        ],
        "format": contract.model_json_schema(),
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


def prepare(output, *, preflight=False, diagnostic=False, protocol="v1"):
    """Freeze requests separately from evaluator labels and experimental arm metadata."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(config_path(protocol))
    if diagnostic and (preflight or protocol != "v3"):
        raise ValueError("Diagnostic probe is v3 only and separate from preflight")
    cases = (
        diagnostic_cases() if diagnostic else synthetic_cases() if preflight else pilot_source()[0]
    )
    rng = random.Random(cfg["order_seed"])
    requests, evaluator = [], []
    for case in cases:
        if diagnostic:
            arm = "no_diagnostic" if case["case_id"] == "DIAGNOSTIC_ABSENT" else "correct_plain"
            cells = [(arm, think) for think in cfg["thinking_settings"]]
        else:
            cells = [
                (arm, think) for arm in cfg["conditions"] for think in cfg["thinking_settings"]
            ]
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
    hashes = source_hashes(protocol)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    roster = read("configs/evaluation-roster.json")
    manifest = {
        "protocol": cfg,
        "phase": "diagnostic" if diagnostic else "preflight" if preflight else "full",
        "scope": "independent diagnostic software fixtures"
        if diagnostic
        else "synthetic software fixtures"
        if preflight
        else cfg["inference_scope"],
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
    protocol = protocol_for(cfg)
    if cfg != read(config_path(protocol)) or manifest["source_sha256"] != source_hashes(protocol):
        raise ValueError("Protocol/source bytes changed; create a new protocol/plan")
    requests, evaluator = read(plan / "requests.json"), read(plan / "evaluator.json")
    if (
        canonical_digest(requests) != manifest["requests_digest"]
        or canonical_digest(evaluator) != manifest["evaluator_digest"]
    ):
        raise ValueError("Plan binding mismatch")
    if manifest["phase"] not in (
        ("preflight", "full", "diagnostic") if protocol == "v3" else ("preflight", "full")
    ):
        raise ValueError("Unknown phase")
    cases = (
        diagnostic_cases()
        if manifest["phase"] == "diagnostic"
        else synthetic_cases()
        if manifest["phase"] == "preflight"
        else pilot_source()[0]
    )
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
    expected = (
        {
            (
                c["case_id"],
                "no_diagnostic" if c["case_id"] == "DIAGNOSTIC_ABSENT" else "correct_plain",
                think,
            )
            for c in cases
            for think in cfg["thinking_settings"]
        }
        if manifest["phase"] == "diagnostic"
        else {
            (c, arm, think)
            for c in by_case
            for arm in cfg["conditions"]
            for think in cfg["thinking_settings"]
        }
    )
    if cells != expected:
        raise ValueError("Incomplete factorial design")
    if protocol == "v3":
        rng = random.Random(cfg["order_seed"])
        order = []
        for case in cases:
            if manifest["phase"] == "diagnostic":
                choices = [
                    (
                        "no_diagnostic"
                        if case["case_id"] == "DIAGNOSTIC_ABSENT"
                        else "correct_plain",
                        think,
                    )
                    for think in cfg["thinking_settings"]
                ]
            else:
                choices = [
                    (arm, think) for arm in cfg["conditions"] for think in cfg["thinking_settings"]
                ]
                rng.shuffle(choices)
            order.extend((case["case_id"], arm, think) for arm, think in choices)
        if [(m["case_id"], m["arm"], m["think"]) for m in evaluator] != order:
            raise ValueError("Frozen request order changed")
    return manifest, requests
