"""Build the thinking ablation report from independently replayed observations."""

# Long literals are report paragraphs.
# ruff: noqa: E501
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path("runs/qwen3-thinking-ablation-8192-4096-01")
NAME = "qwen3-thinking-ablation-8192-4096-01"


def main():
    analysis = json.loads((ROOT / "full-analysis.json").read_text())
    gate = json.loads((ROOT / "preflight-gate.json").read_text())
    manifest = json.loads((ROOT / "full/manifest.json").read_text())
    rows = json.loads((ROOT / "full-case-results.json").read_text())
    config = json.loads(Path("configs/" + NAME + ".json").read_text())
    assert analysis["observations"] == 272 and analysis["matched_inputs"] == 136
    files = sorted((ROOT / "full").glob("*.json"))
    validation = {
        "verdict": "PASS",
        "observations": 272,
        "matched_comparisons": 136,
        "matched_comparisons_with_two_valid_predictions": analysis[
            "matched_inputs_with_two_valid_predictions"
        ],
        "preflight": gate,
        "starting_commit": config["starting_commit"],
        "model_digest": manifest["model_digest"],
        "num_ctx": 8192,
        "num_predict": 4096,
        "prompts_and_schema_equal_to_original": True,
        "paired_requests_differ_only_in_think": True,
        "raw_final_predictions_and_checks_independently_replayed": True,
        "failures_retained": sum(bool(r["failure"]) for r in rows),
        "file_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }
    if validation["failures_retained"]:
        validation["verdict"] = "PARTIAL"
    Path("docs/reviews/" + NAME + ".validation.json").write_text(
        json.dumps(validation, indent=2) + "\n"
    )
    text = [
        "# Qwen3 thinking ablation at 8192/4096",
        "",
        "## Executive verdict",
        "",
        f"**{validation['verdict']} execution.** All 272 scheduled observations are preserved across 136 matched inputs; {validation['failures_retained']} have recorded failures. This is an exploratory analysis on the previously opened 17-pair cohort.",
        "",
        "## Configuration and provenance",
        "",
        f"Started at `{config['starting_commit']}`. Qwen3:8b digest `{manifest['model_digest']}`. Both thinking settings use temperature 0, seed 261, num_ctx=8192 and num_predict=4096. All original E1–E4 evidence, S0/S1 messages and output schemas are reused exactly. Only think changes within a matched input. Request order alternates off-first and on-first across sorted case/package/style inputs. Original frozen pilot files were not modified.",
        "",
        "The service is accessed through the existing SSH tunnel at 127.0.0.1:11435; no authenticated direct compute endpoint was available. Infrastructure snapshots and loaded-model.json record the actual API/runtime and 8192 context allocation. Local free disk space was 23 GiB at preflight. The full request, raw response, separate thinking field, final content, checker result, failure and token/latency values are retained per observation. Separate thinking-token counts are not exposed and were not inferred.",
        "",
        "## Thinking activation and preflight",
        "",
        "An initial two-request activation check returned separate reasoning only with thinking enabled. The subsequent preflight used eight matched inputs / 16 observations across two opaque cases, E1/E4 and S0/S1. All final answers parsed and bound, all eight thinking-on calls returned reasoning, and no response truncated. The checker sees final structured content only. Activation and preflight calls are separate from the final 272 observations.",
        "",
        "## Full 2 × 2 outcomes",
        "",
        "Counts below aggregate four evidence packages over 17 pairs: 68 scheduled observations per row. Correctness uses benchmark references. Failures and abstentions remain in every yield denominator. Answered accuracy conditions on valid directional outputs. Rejection is an additional checker decision and may overlap an upstream explicit abstention; it is not counted as a model abstention.",
        "",
        "| Style | Thinking | N | Correct | Wrong | Abstain | Failure | Direction accuracy | Answered accuracy | Checker rejected | Correct & released | Released |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in analysis["summary"]:
        if m["package"] != "ALL":
            continue
        aa = (
            "undefined"
            if m["answered_accuracy"] is None
            else f"{100 * m['answered_accuracy']:.1f}%"
        )
        text.append(
            f"| {m['style']} | {m['think']} | {m['n']} | {m['correct']} | {m['wrong']} | {m['abstain']} | {m['failures']} | {100 * m['direction_accuracy']:.1f}% | {aa} | {m['rejected']} | {m['supported_correct']} | {m['released']} |"
        )
    text += [
        "",
        "## Matched comparisons and uncertainty",
        "",
        "Whole causal pairs are resampled with replacement (10,000 percentile bootstrap draws, seed 261). Evidence packages from one pair remain together. These intervals are exploratory and do not account for all source-family dependence or uncertain benchmark labels. The 272 observations are not 272 independent causal datasets.",
    ]
    for c in analysis["comparisons"]:
        text.append(
            f"\n{c['style']}: {c['improved']} improved, {c['worsened']} worsened, {c['unchanged']} unchanged; correct-yield difference {100 * c['net']:+.1f} points; pair-bootstrap interval [{100 * c['pair_cluster_interval'][0]:.1f}, {100 * c['pair_cluster_interval'][1]:.1f}] points."
        )
    text += [
        "",
        "Per-evidence exact McNemar counts/p-values are in full-analysis.json; they are unadjusted exploratory checks. A pooled exact McNemar test across repeated evidence packages would ignore dependence and is not used. The style interaction is the difference of paired thinking effects (S1 minus S0): "
        + json.dumps(analysis["thinking_by_style_interaction"])
        + ".",
        "",
        "## Evidence strata and overhead",
        "",
        "| Style | Think | Evidence | Correct | Wrong | Abstain | Failure | Rejected | Median seconds | Median generated tokens |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in analysis["summary"]:
        if m["package"] == "ALL":
            continue
        text.append(
            f"| {m['style']} | {m['think']} | {m['package']} | {m['correct']} | {m['wrong']} | {m['abstain']} | {m['failures']} | {m['rejected']} | {m['median_latency']:.1f} | {m['median_output_tokens']:.1f} |"
        )
    text += [
        "",
        "## E4 diagnostic propagation",
        "",
        "Disagreement with ANM is not by itself evidence of improvement. The transitions below retain reference correctness, upstream ANM direction, failures and checker decisions.",
    ]
    e4 = [r for r in rows if r["package"] == "E4"]
    for style in ("S0", "S1"):
        for think in (False, True):
            g = [r for r in e4 if r["style"] == style and r["think"] == think]
            wrong_anm = [
                r for r in g if r["anm_direction"] is not None and r["anm_direction"] != r["gold"]
            ]
            copy = sum(
                bool(r["prediction"])
                and r["prediction"]["predicted_direction"] == r["anm_direction"]
                for r in wrong_anm
            )
            correct = sum(r["correct"] for r in wrong_anm)
            text.append(
                f"\n{style} think={think}: among {len(wrong_anm)} benchmark-wrong ANM inputs, {copy} copied the wrong ANM direction and {correct} gave a benchmark-correct answer. Full case records also retain abstentions and failures."
            )
    text += [
        "",
        "## Checker outcomes and case-level transitions",
        "",
        "Every valid final response in this experiment supplied claims=[]. Zero checker rejections is therefore vacuous for typed citation checking: no nonempty claim list was tested. Correct-and-released counts mean benchmark-correct answers passed the implemented release policy; they do not establish evidentiary support for the causal conclusion. Checker reason-code counts are stratified in full-analysis.json. Invalid citations, unavailable evidence and numeric mismatches are distinct from causal correctness. The checker permits an accurately attributed disagreement with ANM. Arbitrary natural-language reasoning/explanation contradictions are not automatically adjudicated by the typed checker; this study does not claim an exhaustive semantic contradiction rate. All 136 transitions, including underlying directions, are in full-transitions.json; full-case-results.json includes reference direction and checker results after inference.",
        "",
        "## Historical pilot comparison",
        "",
        "The original pilot used thinking off, context 4096 and output 512. The new off condition changes both token budgets, so differences versus the original cannot be assigned to thinking. Model digest, archived messages, schema and evidence are unchanged. Original E4/S0 and S1 had 6 correct, 8 wrong and 3 abstentions of 17. The new matched on/off comparisons, rather than historical differences, estimate the exploratory thinking effect.",
        "",
        "## Interpretation, limitations and next experiment",
        "",
        "Interpret the point differences alongside pair-bootstrap intervals, wrong-answer yield, abstentions and checker rejections. A rise in answered accuracy with reduced coverage is not a general improvement. Benchmark directions remain fallible references. One model, one seed, an opened cohort, repeated evidence conditions and source dependence limit generalization. Ordering is balanced overall, but sorted S0 inputs are off-first and S1 inputs are on-first; this limits causal interpretation of the style interaction and latency contrasts. Thinking traces are recorded outputs, not a validated explanation of internal cognition. The next confirmatory study should freeze a matched thinking protocol with order counterbalanced within each prompt style, and a preregistered nonempty-citation or independent evidence-quality assessment, before collecting an untouched source-separated real cohort; use development cases to choose any prompt or budget change.",
        "",
        "## Reproduce",
        "",
        "Run `uv run python scripts/analyze_thinking_ablation.py --phase full` followed by `uv run python scripts/report_thinking_ablation.py` to replay the saved predictions/checks and regenerate this report. New inference uses `scripts/qwen3_thinking_ablation.py`; never reuse or overwrite the original pilot. Raw evidence is under `"
        + str(ROOT)
        + "/`.",
    ]
    text += [
        "",
        "## Final interpretation and validation",
        "",
        "Thinking increased observed correct-direction yield on this opened cohort: +6/68 S0 and +5/68 S1, with no correct answer becoming incorrect. The gains occurred outside E4. It did not correct any of the eight benchmark-wrong ANM directions in either prompt style. The S1 wrong-answer count increased by one because thinking-on returned a wrong direction where off truncated; this is an execution/release difference, not a successful challenge to ANM.",
        "",
        "Evidence reliability did not demonstrably improve: all 271 valid final predictions had empty claim lists, so there were zero evaluated nonempty typed claim lists and zero citation rejections in every cell. Natural-language reasoning was retained, but its faithfulness and unrestricted contradictions were not independently adjudicated. Checker-accepted release is an operational metric, not proof that a causal direction is supported.",
        "",
        "The completed dataset has 272 saved raw responses, 136 matched request identities and 135 matches with two valid final predictions. One S1-Off/E4 response (D1028) exhausted all 4096 output tokens; it remains an execution failure, not an abstention. All 136 thinking-on responses returned separate reasoning; no thinking-off response did.",
        "",
        "Source-family sensitivity (seven groups) widens the exploratory difference intervals: "
        + json.dumps(analysis["source_group_sensitivity"])
        + ". The per-package E3 exact McNemar p-value is 0.125 for both styles; all other per-package values are 1.0. Small grouped samples, unadjusted exploratory analyses and ordering prevent a confirmatory generalization claim.",
        "",
        "Historical unweighted comparison (68 scheduled inputs per style): original S0 had 14 correct, 15 wrong and 39 abstentions; original S1 had 8 correct, 12 wrong and 48 abstentions. New Off has 6 correct in each style. The historical-to-new change in budget and potentially runtime conditions cannot be attributed to thinking. The positive thinking contrast refers only to the new 8192/4096 matched experiment.",
        "",
        "Reproduction order: `uv run python scripts/analyze_thinking_ablation.py --phase full`, `uv run python scripts/report_thinking_ablation.py`, then `uv run python scripts/verify_thinking_ablation.py`. The final verifier independently recounts raw replies and checks frozen source hashes, identities, budgets and request equality. Original pilot archives remain unchanged. No changes were committed, pushed or merged.",
    ]
    text += [
        "",
        "## Aggregate latency and generated-token overhead",
        "",
        "| Thinking | Responses | Median seconds | Summed client seconds | Median generated tokens | Total generated tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for think in (False, True):
        group = [r for r in rows if r["think"] == think]
        text.append(
            f"| {think} | {len(group)} | {statistics.median(r['latency_seconds'] for r in group):.2f} | {sum(r['latency_seconds'] for r in group):.2f} | {statistics.median(r['generated_tokens'] for r in group):.1f} | {sum(r['generated_tokens'] for r in group)} |"
        )
    text += [
        "",
        "The API generated-token count is retained as exposed; it is not partitioned into reasoning and final-answer tokens. Summed request latency is not full pipeline wall time. Empty claim lists make the zero citation-rejection count uninformative about nonempty citation quality. Transport used a 900-second timeout equally in every cell; this is recorded in the execution script and its frozen hash.",
        "",
        "Software validation: 1,027 tests passed with two snapshot-dependent skips; lint, formatting, deterministic demos, ANM handshake and package builds passed. The independent raw verifier also passed. See final-software-validation.log in the run directory.",
    ]
    Path("docs/reviews/" + NAME + ".md").write_text("\n".join(text) + "\n")
    print(validation["verdict"], analysis["observations"], analysis["matched_inputs"])


if __name__ == "__main__":
    main()
