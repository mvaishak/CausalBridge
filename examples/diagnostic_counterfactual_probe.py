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


def run_live(public, *, model_config, output):
    import httpx

    from causalbridge.discovery.schemas import DirectionEvidence
    from causalbridge.llm.client import ModelConfig, OllamaModel
    from causalbridge.llm.predictor import predict_direction

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    config = ModelConfig.model_validate_json(Path(model_config).read_text())
    save_new(
        output / "run-identity.json",
        {
            "protocol": PROTOCOL,
            "public_sha256": digest(public),
            "config": config.model_dump(mode="json"),
            "status": "live_attempt_expected",
            "note": "Experimental counterfactuals: do not score as real ANM performance",
        },
    )
    condition = make_condition()
    with httpx.Client(timeout=config.timeout_seconds, trust_env=False) as client:
        model = OllamaModel(config, client=client)
        with (output / "responses.jsonl").open("x", encoding="utf8") as fh:
            for item in public:
                ev = DirectionEvidence.model_validate(item["evidence"])
                trace = predict_direction(ev, condition, model)
                result = {
                    "case_id": item["case_id"],
                    "arm": item["arm"],
                    "trace": trace.model_dump(mode="json"),
                    "mode": "live_ollama",
                }
                fh.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
                fh.flush()
    return output / "responses.jsonl"


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
    p = sub.add_parser("analyze")
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--responses", type=Path, required=True)
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
        public = load_jsonl(args.prepared / "public.jsonl")
        identity = json.loads((args.prepared / "protocol.json").read_text())
        if digest(public) != identity["public_digest"]:
            raise ValueError("Frozen public manifest mismatch")
        if (
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            != identity["preparation_script_sha256"]
        ):
            raise ValueError("Preparation script changed after protocol freeze")
        run_live(public, model_config=args.model_config, output=args.output)
    else:
        public = load_jsonl(args.prepared / "public.jsonl")
        frozen = json.loads((args.prepared / "protocol.json").read_text())
        if digest(public) != frozen["public_digest"]:
            raise ValueError("Frozen public manifest mismatch")
        if (
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            != frozen["preparation_script_sha256"]
        ):
            raise ValueError("Preparation script changed after protocol freeze")
        private = json.loads((args.prepared / "private-oracle.json").read_text())
        responses = load_jsonl(args.responses)
        save_new(args.output, analyze(public, private, responses))


if __name__ == "__main__":
    main()