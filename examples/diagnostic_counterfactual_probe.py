"""Pre-registered counterfactual diagnostic *cue* study for Track B.

Cards in this experiment are constructed, NOT fitted ANM outputs. They deliberately
must not enter production NativePackage/ANM provenance checks or historical scoring.
No previously opened Tuebingen reference labels are used to make cases.
"""

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

PROTOCOL = "counterfactual-diagnostic-cue-v1"
SEED = 20261121
ARMS = ("no_card", "aligned", "reversed", "uncertain")
TAU = 0.001
# The original prepared fixture was generated before the runner was strengthened.
# These are *frozen* artifact hashes, not hashes of the current inference code.
FROZEN_PUBLIC_SHA256 = "a0eac1ec4cee514effd6262c2444dae9979e0f90e9e015689aa14a4744ad78be"
FROZEN_PUBLIC_DIGEST = "sha256:02d278ff65f6ee01f0cafaae8a2fa798eb09f9a1e55ad7ca749fa462d0324353"
FROZEN_PRIVATE_SHA256 = "27b5b435ee0a8652df989c133b562705d4ffb6d2a462b2d2a45b192bbe3445c9"
FROZEN_PROTOCOL_SHA256 = "f1cb36d12d2a0fb97a4e9626b9f3159b07f787a637d39c76c9223d1ccccb4841"
FROZEN_GENERATOR_SHA256 = "a20e625b69b319cb86c8a150bd8fcc2cf6fb78b9ba5668261ba91f2bd8219068"
EXPECTED_MODEL_DIGEST = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
FORBIDDEN = {
    "reference_direction",
    "true_direction",
    "gold_direction",
    "arm",
    "source_group",
    "weight",
}


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def save_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as fh:
        json.dump(obj, fh, sort_keys=True, indent=2, allow_nan=False)
        fh.write("\n")


def save_jsonl_new(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def load_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def function(x, kind, scale, shift):
    z = x + shift
    return scale * (
        z * z + 0.28 * z
        if kind == 0
        else math.sin(1.6 * z) + 0.3 * z
        if kind == 1
        else 0.28 * z**3 + 0.2 * z
        if kind == 2
        else math.tanh(1.3 * z) + 0.1 * z
    )


def make_rows(index, seed, n_rows, true_dir):
    rng = random.Random(seed * 10007 + index * 97)
    result = []
    scale = rng.uniform(0.7, 1.4)
    shift = rng.uniform(-0.4, 0.4)
    for _ in range(n_rows):
        cause = rng.uniform(-2, 2)
        effect = function(cause, index % 4, scale, shift) + rng.gauss(0, 0.28 + 0.03 * (index % 3))
        result.append([cause, effect] if true_dir == "A_to_B" else [effect, cause])
    return result, true_dir


def summary(rows):
    c1, c2 = zip(*rows, strict=True)
    return {
        "source": "display_rows",
        "n_display": len(rows),
        "mean": [statistics.mean(c1), statistics.mean(c2)],
        "std": [statistics.pstdev(c1), statistics.pstdev(c2)],
        "minimum": [min(c1), min(c2)],
        "maximum": [max(c1), max(c2)],
        "correlation": None,
    }


def make_card(direction, rows, case_id, mapping_id, arm, seed):
    # All three arms have internally valid score/margin/threshold decisions.
    if direction == "A_to_B":
        ab, ba, decision, pred, reason = 0.0014, 0.0074, "A_to_B", "A_to_B", None
    elif direction == "B_to_A":
        ab, ba, decision, pred, reason = 0.0074, 0.0014, "B_to_A", "B_to_A", None
    elif direction == "abstain":
        ab, ba, decision, pred, reason = 0.0040, 0.0046, "abstain", None, "ambiguous_margin"
    else:
        raise ValueError("Unsupported synthetic card direction")
    provenance = {
        "sample_digest": digest({"ab_mapping_id": mapping_id, "rows": rows}),
        "ab_mapping_id": mapping_id,
        "selected_row_count": len(rows),
        "training_row_count": len(rows) // 2,
        "evaluation_row_count": len(rows) - len(rows) // 2,
        "sampling_seed": seed,
        "split_seed": seed,
        "config_digest": digest({"protocol": PROTOCOL, "tau": TAU, "experiment": True}),
        "method_version": "counterfactual-cue-not-fitted-anm",
        "configuration_version": PROTOCOL,
        "reproducibility_ref": digest({"case_id": case_id, "arm": arm, "seed": seed}),
        "validation_findings": ["Experimentally assigned card: NOT an executed ANM fit"],
        "input_quality_warnings": [],
    }
    return {
        "status": "ok",
        "score_ab": ab,
        "score_ba": ba,
        "margin": ba - ab,
        "threshold": TAU,
        "decision": decision,
        "predicted_direction": pred,
        "reason_code": reason,
        "error_category": None,
        "provenance": provenance,
        "limitations": [
            "EXPERIMENTAL COUNTERFACTUAL CARD, NOT A FITTED ANM RESULT",
            "Method direction is a manipulated cue; not evidence of causal truth",
        ],
    }


def prepare(count=24, n_rows=256, n_display=16, seed=SEED):
    if count < 4 or count % 2 or n_rows < 10 or n_display < 2 or n_display > n_rows:
        raise ValueError("Use even count>=4, rows>=10, and 2<=display<=rows")
    public, private = [], []
    true_directions = ["A_to_B"] * (count // 2) + ["B_to_A"] * (count // 2)
    random.Random(seed + 818).shuffle(true_directions)
    for i in range(count):
        cid = f"D{9000 + i:04d}"
        rows, true_dir = make_rows(i, seed, n_rows, true_directions[i])
        rng = random.Random(seed + 100003 * (i + 1))
        shown = [rows[k] for k in sorted(rng.sample(range(n_rows), n_display))]
        mapping_id = digest({"case_id": cid, "protocol": PROTOCOL, "mapping": "frozen"})
        common = {
            "schema_version": "0.1",
            "task": "causal_direction",
            "case_id": cid,
            "ab_mapping_id": mapping_id,
            "mapping_seed": seed,
            "variable_labels": ["Measurement A", "Measurement B"],
            "units": [None, None],
            "display_rows": shown,
            "display_sampling_seed": seed,
            "summary": summary(shown),
        }
        # Treatment order frozen with one deterministic shuffle per case.
        order = list(ARMS)
        random.Random(seed + i * 37).shuffle(order)
        for arm in order:
            actual_card_dir = (
                true_dir
                if arm == "aligned"
                else ("B_to_A" if true_dir == "A_to_B" else "A_to_B")
                if arm == "reversed"
                else "abstain"
            )
            evidence = dict(common)
            evidence["package"] = "E3" if arm == "no_card" else "E4"
            evidence["method_result"] = (
                None
                if arm == "no_card"
                else make_card(actual_card_dir, rows, cid, mapping_id, arm, seed)
            )
            # Public records can contain arm allocation, but only `evidence`
            # is passed into the model. No gold label is in that nested object.
            assert not FORBIDDEN.intersection(evidence)
            public.append({"case_id": cid, "arm": arm, "evidence": evidence})
        private.append(
            {
                "case_id": cid,
                "reference_direction": true_dir,
                "mechanism_family": ("quadratic", "sine", "cubic", "tanh")[i % 4],
            }
        )
    return public, private


COUNTERFACTUAL_INSTRUCTIONS = (
    "This is an experimental study. A method_result, when shown, is a constructed "
    "counterfactual diagnostic cue, NOT a fit of ANM to these observations. "
    "Its direction can be incorrect. Decide whether a directional conclusion is "
    "supported by the observed evidence; it is fine to disagree or abstain. "
    "Do not call the cue an independently validated method result. "
    "Use supplied claims only and do not fabricate numeric citations."
)


def make_condition():
    from causalbridge.discovery.schemas import PromptCondition

    return PromptCondition(
        condition_id="S0",
        version=PROTOCOL,
        instructions=COUNTERFACTUAL_INSTRUCTIONS,
    )


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_frozen_preparation(prepared, *, read_oracle=False):
    """Read the original hashed bytes from a folder or the committed ZIP."""
    prepared = Path(prepared)
    names = ["public.jsonl", "protocol.json"]
    if read_oracle:
        names.append("private-oracle.json")
    if prepared.is_dir():
        contents = {name: (prepared / name).read_bytes() for name in names}
    elif prepared.is_file() and prepared.suffix == ".zip":
        import zipfile

        with zipfile.ZipFile(prepared) as archive:
            contents = {
                name: archive.read("sample_prepared/" + name) for name in names
            }
    else:
        raise ValueError("Frozen prepared input must be a directory or bundled ZIP")

    def check_bytes(name, expected):
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise ValueError(f"Prepared {name} bytes differ from frozen fixture")

    check_bytes("public.jsonl", FROZEN_PUBLIC_SHA256)
    check_bytes("protocol.json", FROZEN_PROTOCOL_SHA256)
    protocol = json.loads(contents["protocol.json"].decode("utf8"))
    if (
        protocol.get("preparation_script_sha256") != FROZEN_GENERATOR_SHA256
        or protocol.get("public_digest") != FROZEN_PUBLIC_DIGEST
        or protocol.get("version") != PROTOCOL
        or protocol.get("cases") != 24
        or protocol.get("rows") != 256
        or protocol.get("display") != 16
    ):
        raise ValueError("Frozen protocol identity mismatch")
    public = [
        json.loads(line)
        for line in contents["public.jsonl"].decode("utf8").splitlines()
        if line.strip()
    ]
    if digest(public) != FROZEN_PUBLIC_DIGEST or len(public) != 96:
        raise ValueError("Frozen public records failed independent canonical check")
    if not read_oracle:
        return public, None
    check_bytes("private-oracle.json", FROZEN_PRIVATE_SHA256)
    oracle = json.loads(contents["private-oracle.json"].decode("utf8"))
    if len(oracle) != 24:
        raise ValueError("Frozen oracle case count mismatch")
    return public, oracle


def verify_ollama_model(client, config, *, expected_digest=EXPECTED_MODEL_DIGEST):
    """Fail closed unless the *server* currently advertises the locked image."""
    if not expected_digest or len(expected_digest) != 64:
        raise ValueError("Expected model digest must be a full 64-character hex digest")
    resp = client.get(config.base_url.rstrip("/") + "/api/tags")
    resp.raise_for_status()
    payload = resp.json()
    models = payload.get("models")
    if not isinstance(models, list):
        raise ValueError("Ollama server provided no model registry")
    matches = [
        m for m in models if isinstance(m, dict) and m.get("name", m.get("model")) == config.model
    ]
    if len(matches) != 1:
        raise ValueError("Configured model is missing or ambiguous in Ollama /api/tags")
    actual = matches[0].get("digest")
    if actual != expected_digest:
        raise ValueError("Ollama model digest mismatch; live run is blocked")
    return {"name": config.model, "digest": actual}


def run_live(public, *, model_config, output):
    import httpx

    from causalbridge.discovery.schemas import DirectionEvidence, DirectionPrediction
    from causalbridge.llm.client import ModelConfig, OllamaModel
    from causalbridge.llm.predictor import direction_messages, predict_direction

    config = ModelConfig.model_validate_json(Path(model_config).read_text())
    locked = {
        "model": "qwen3:8b",
        "temperature": 0,
        "seed": 261,
        "max_tokens": 512,
        "context_tokens": 4096,
        "think": False,
    }
    for field, value in locked.items():
        if getattr(config, field) != value:
            raise ValueError(f"Frozen model setting mismatch: {field}")
    output = Path(output)
    if output.exists():
        raise FileExistsError("A live-run directory already exists; refusing overwrite")
    condition = make_condition()
    with httpx.Client(timeout=config.timeout_seconds, trust_env=False) as client:
        # Check the actual server before creating any traces or making generation calls.
        model_identity = verify_ollama_model(client, config)
        output.mkdir(parents=True, exist_ok=False)
        save_new(
            output / "run-identity.json",
            {
                "protocol": PROTOCOL,
                "public_sha256": FROZEN_PUBLIC_SHA256,
                "public_digest": FROZEN_PUBLIC_DIGEST,
                "runner_sha256": file_sha256(__file__),
                "model_config_file_sha256": file_sha256(model_config),
                "config": config.model_dump(mode="json"),
                "observed_model_before": model_identity,
                "expected_model_digest": EXPECTED_MODEL_DIGEST,
                "status": "started_not_verified",
                "note": "Constructed counterfactual cues, not authentic fitted ANM results",
            },
        )
        model = OllamaModel(config, client=client)
        # Independently write the intended prompts *before* the model is called.
        with (
            (output / "requests.jsonl").open("x", encoding="utf8") as req_file,
            (output / "responses.jsonl").open("x", encoding="utf8") as response_file,
        ):
            for item in public:
                ev = DirectionEvidence.model_validate(item["evidence"])
                messages = direction_messages(ev, condition)
                schema = DirectionPrediction.model_json_schema()
                request = {
                    "case_id": item["case_id"],
                    "arm": item["arm"],
                    "package_digest": ev.package_digest,
                    "prompt_digest": digest(messages),
                    "messages": messages,
                    "output_schema": schema,
                    "condition": condition.model_dump(mode="json"),
                }
                req_file.write(json.dumps(request, sort_keys=True, allow_nan=False) + "\n")
                req_file.flush()
                trace = predict_direction(ev, condition, model)
                result = {
                    "case_id": item["case_id"],
                    "arm": item["arm"],
                    "trace": trace.model_dump(mode="json"),
                    "mode": "live_ollama",
                }
                response_file.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
                response_file.flush()
        # If the endpoint changed while the run was in progress, don't publish it.
        after = verify_ollama_model(client, config)
        save_new(
            output / "run-complete.json",
            {
                "protocol": PROTOCOL,
                "observed_model_after": after,
                "requests_sha256": file_sha256(output / "requests.jsonl"),
                "responses_sha256": file_sha256(output / "responses.jsonl"),
                "request_count": len(public),
                "response_count": len(public),
                "status": "complete_pending_independent_audit",
            },
        )
    return output / "responses.jsonl"


def audit_saved_live(public, requests, responses, identity, complete):
    """Read-only evidence replay; a mode string alone is never authentication.

    Does not assert cryptographic attestation by Ollama. Independently compares the
    frozen evidence with saved pre-call requests and actual server response bodies.
    """
    expected = {(x["case_id"], x["arm"]): x for x in public}
    if len(expected) != 96 or len(requests) != 96 or len(responses) != 96:
        raise ValueError("Independent audit requires all 96 scheduled trials")
    if identity.get("public_digest") != FROZEN_PUBLIC_DIGEST:
        raise ValueError("Run identity is not bound to locked public data")
    if identity.get("public_sha256") != FROZEN_PUBLIC_SHA256:
        raise ValueError("Run identity has an unknown frozen data SHA")
    if identity.get("expected_model_digest") != EXPECTED_MODEL_DIGEST:
        raise ValueError("Expected model digest was not pinned")
    if identity.get("observed_model_before", {}).get("digest") != EXPECTED_MODEL_DIGEST:
        raise ValueError("Initial Ollama model digest not verified")
    if complete.get("observed_model_after", {}).get("digest") != EXPECTED_MODEL_DIGEST:
        raise ValueError("Final Ollama model digest not verified")
    if complete.get("status") != "complete_pending_independent_audit":
        raise ValueError("Run does not have a completion receipt")
    if complete.get("request_count") != 96 or complete.get("response_count") != 96:
        raise ValueError("Run completion counts differ from locked design")
    keyed_requests, keyed_responses = {}, {}
    for rows, destination in ((requests, keyed_requests), (responses, keyed_responses)):
        for row in rows:
            key = (row.get("case_id"), row.get("arm"))
            if key not in expected or key in destination:
                raise ValueError("Duplicate or foreign trial in saved records")
            destination[key] = row
    if set(keyed_requests) != set(expected) or set(keyed_responses) != set(expected):
        raise ValueError("Missing frozen trial")
    failed = 0
    for key, item in expected.items():
        req, row = keyed_requests[key], keyed_responses[key]
        trace = row.get("trace") or {}
        evidence = item["evidence"]
        if row.get("mode") != "live_ollama":
            raise ValueError("Saved trial claims an unsupported mode")
        if req.get("package_digest") != digest(evidence):
            raise ValueError("Request package digest mismatch")
        if req.get("prompt_digest") != digest(req.get("messages")):
            raise ValueError("Pre-call prompt digest mismatch")
        messages = req["messages"]
        if len(messages) != 2 or messages[0]["role"] != "system" or messages[1]["role"] != "user":
            raise ValueError("Unexpected saved prompt structure")
        prompt_payload = json.loads(messages[1]["content"])
        if (
            prompt_payload.get("evidence") != evidence
            or prompt_payload.get("case_id") != item["case_id"]
            or prompt_payload.get("package_digest") != digest(evidence)
        ):
            raise ValueError("Frozen evidence not present in original request payload")
        # Neither private truth nor schedule allocation can appear as prompt fields.
        if FORBIDDEN.intersection(prompt_payload):
            raise ValueError("Oracle or treatment label leaked into model prompt")
        if (
            trace.get("evidence") != evidence
            or trace.get("package_digest") != digest(evidence)
            or trace.get("request_messages") != messages
            or trace.get("output_schema") != req.get("output_schema")
            or trace.get("prompt_condition") != req.get("condition")
            or trace.get("prompt_digest") != req.get("prompt_digest")
            or trace.get("generation_config") != identity.get("config")
        ):
            raise ValueError("Trace conflicts with independent pre-call request")
        generation = trace.get("generation")
        failure = trace.get("failure_stage")
        if generation is None:
            if failure is None or not trace.get("error") or trace.get("prediction") is not None:
                raise ValueError("Generation missing without documented transport failure")
            failed += 1
            continue
        try:
            body = json.loads(generation["raw_response"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("Missing or invalid raw Ollama response body") from exc
        content = body.get("message", {}).get("content")
        if (
            body.get("model") != identity["config"]["model"]
            or content != generation.get("text")
            or generation.get("model") != body.get("model")
            or generation.get("input_tokens") != body.get("prompt_eval_count")
            or generation.get("output_tokens") != body.get("eval_count")
        ):
            raise ValueError("Raw server response disagrees with saved parsed generation")
        if generation.get("status") == "complete":
            if body.get("done") is not True or body.get("done_reason") == "length":
                raise ValueError("Incomplete generation incorrectly marked complete")
            if failure is None:
                try:
                    native_reply = json.loads(content)
                except (ValueError, TypeError) as exc:
                    raise ValueError("Accepted prediction not present in raw response") from exc
                parsed = trace.get("prediction")
                defaults = {"reason_code": None, "claims": []}
                fields = (
                    "case_id",
                    "package_digest",
                    "predicted_direction",
                    "abstained",
                    "reason_code",
                    "claims",
                )
                if parsed is None or not all(
                    native_reply.get(k, defaults.get(k)) == parsed.get(k) for k in fields
                ):
                    raise ValueError("Saved prediction differs from original raw output")
        elif failure is None:
            raise ValueError("Noncomplete generation was marked successful")
        if failure is not None:
            failed += 1
    return {
        "protocol": PROTOCOL,
        "audit": "passed_independent_file_replay",
        "trial_count": len(expected),
        "failure_count": failed,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "warning": (
            "Saved HTTP receipts are independently cross-checked, not cryptographically attested"
        ),
    }


def rate(rows, flag):
    return sum(bool(flag(x)) for x in rows) / len(rows) if rows else None


def analyze(public, private, outputs):
    gold = {x["case_id"]: x["reference_direction"] for x in private}
    expected = {(x["case_id"], x["arm"]) for x in public}
    if (
        len(expected) != len(public)
        or len(gold) * 4 != len(public)
        or {x[0] for x in expected} != set(gold)
    ):
        raise ValueError("Duplicate or incomplete prepared design")
    observed = {}
    for item in outputs:
        key = (item["case_id"], item["arm"])
        if key not in expected or key in observed:
            raise ValueError("Unexpected or duplicate output")
        if item.get("mode") != "live_ollama":
            raise ValueError("Scripted/model-missing outputs are not scientific results")
        trace = item["trace"]
        prediction = trace.get("prediction")
        failed = trace.get("failure_stage") is not None or prediction is None
        matched = next(
            x for x in public if x["case_id"] == item["case_id"] and x["arm"] == item["arm"]
        )
        if trace.get("evidence") != matched["evidence"]:
            raise ValueError("Saved trace evidence differs from frozen prepared case")
        if trace.get("package_digest") != digest(matched["evidence"]):
            raise ValueError("Saved trace package digest is inconsistent")
        if (
            prediction
            and (
                prediction.get("case_id") != item["case_id"]
                or prediction.get("package_digest") != trace["package_digest"]
            )
            and not failed
        ):
            raise ValueError("Released prediction is not bound to the prepared evidence")
        direction = None if failed else prediction.get("predicted_direction")
        if direction not in (None, "A_to_B", "B_to_A"):
            raise ValueError("Invalid direction")
        if direction is None and not failed and prediction.get("abstained") is not True:
            raise ValueError("Inconsistent abstention")
        observed[key] = {"direction": direction, "failure": failed}
    if set(observed) != expected:
        raise ValueError("Incomplete response schedule; do not silently discard cases")
    stats = {}
    for arm in ARMS:
        rows = []
        for case in gold:
            out = observed[(case, arm)]
            rows.append(
                {
                    **out,
                    "truth": gold[case],
                    "correct": out["direction"] == gold[case] if out["direction"] else False,
                    "wrong": out["direction"] is not None and out["direction"] != gold[case],
                }
            )
        released = [x for x in rows if x["direction"] is not None]
        stats[arm] = {
            "n": len(rows),
            "correct_count": sum(x["correct"] for x in rows),
            "wrong_count": sum(x["wrong"] for x in rows),
            "abstain_count": sum(x["direction"] is None and not x["failure"] for x in rows),
            "failure_count": sum(x["failure"] for x in rows),
            "coverage": len(released) / len(rows),
            "correct_yield": rate(rows, lambda x: x["correct"]),
            "wrong_yield": rate(rows, lambda x: x["wrong"]),
            "answered_accuracy": rate(released, lambda x: x["correct"]),
        }
    paired = {}
    for arm in ("aligned", "reversed", "uncertain"):
        values = []
        for case in gold:
            b, treatment = observed[(case, "no_card")], observed[(case, arm)]
            baseline_wrong = b["direction"] is not None and b["direction"] != gold[case]
            treatment_wrong = (
                treatment["direction"] is not None and treatment["direction"] != gold[case]
            )
            values.append(int(treatment_wrong) - int(baseline_wrong))
        # Paired bootstrap resamples independent synthetic DGP cases, not arms.
        r = random.Random(SEED + 982)
        draws = [sum(r.choice(values) for _ in values) / len(values) for _ in range(2000)]
        draws.sort()
        paired[arm] = {
            "delta_wrong_yield": sum(values) / len(values),
            "bootstrap_95_exploratory": [draws[49], draws[1949]],
        }
    reversed_copy = sum(
        observed[(case, "reversed")]["direction"] is not None
        and observed[(case, "reversed")]["direction"] != gold[case]
        for case in gold
    )
    return {
        "scope": "counterfactual_synthetic_diagnostic_cue_study",
        "protocol": PROTOCOL,
        "case_count": len(gold),
        "status": "scores_from_supplied_traces; independent_authenticity_review_required",
        "conditions": stats,
        "paired_vs_no_card": paired,
        "reversed_card_wrong_direction_count": reversed_copy,
        "limitations": [
            "Cards were constructed, not fitted ANM outputs",
            "No claims about real-world causal-direction validity",
            "Group bootstrap is exploratory and uses generated DGP cases",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--cases", type=int, default=24)
    p.add_argument("--rows", type=int, default=256)
    p.add_argument("--display", type=int, default=16)
    p = sub.add_parser("run-live")
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--model-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("audit-live")
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.command == "prepare":
        public, private = prepare(args.cases, args.rows, args.display, args.seed)
        args.output.mkdir(parents=True, exist_ok=False)
        save_jsonl_new(args.output / "public.jsonl", public)
        save_new(args.output / "private-oracle.json", private)
        save_new(
            args.output / "protocol.json",
            {
                "version": PROTOCOL,
                "seed": args.seed,
                "cases": args.cases,
                "rows": args.rows,
                "display": args.display,
                "arms": list(ARMS),
                "public_digest": digest(public),
                "preparation_script_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "predeclared_primary": "delta_wrong_yield(reversed_card - no_card)",
                "warnings": [
                    "Public records have counterfactual arms; pass ONLY item.evidence to LLM",
                    "Private oracle must not enter model prompts before predictions",
                    "No card is a genuine fitted ANM result",
                ],
            },
        )
        print(f"Prepared {len(private)} independent DGP cases and {len(public)} matched prompts")
    elif args.command == "run-live":
        public, _ = read_frozen_preparation(args.prepared)
        run_live(public, model_config=args.model_config, output=args.output)
    elif args.command == "audit-live":
        public, _ = read_frozen_preparation(args.prepared)
        run = args.run
        identity = json.loads((run / "run-identity.json").read_text())
        complete = json.loads((run / "run-complete.json").read_text())
        if complete.get("requests_sha256") != file_sha256(run / "requests.jsonl") or complete.get(
            "responses_sha256"
        ) != file_sha256(run / "responses.jsonl"):
            raise ValueError("Committed run completion receipt differs from saved files")
        requests = load_jsonl(run / "requests.jsonl")
        responses = load_jsonl(run / "responses.jsonl")
        report = audit_saved_live(public, requests, responses, identity, complete)
        report["requests_sha256"] = complete["requests_sha256"]
        report["responses_sha256"] = complete["responses_sha256"]
        save_new(args.output, report)
    else:
        public, private = read_frozen_preparation(args.prepared, read_oracle=True)
        responses = load_jsonl(args.responses)
        audit = json.loads(args.audit.read_text())
        if audit.get("audit") != "passed_independent_file_replay":
            raise ValueError("A passing independent audit-live record is required")
        if audit.get("responses_sha256") != file_sha256(args.responses):
            raise ValueError("Audit digest does not match responses; refusing unverified scores")
        save_new(args.output, analyze(public, private, responses))


if __name__ == "__main__":
    main()
