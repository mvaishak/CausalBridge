"""Offline post-pilot diagnostics. Never calls a model client or executes ANM."""

import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import statistics
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from causalbridge.discovery.loader import prepare_pilot
from causalbridge.evaluation.audit_native import audit_native
from causalbridge.evaluation.export import analysis_rows
from causalbridge.evaluation.scoring import score_pilot

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs/real-pilot-01"
PREP = ROOT / "runs/pilot-preparation/prepared"


def read(path):
    return json.loads(path.read_text())


def dump(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def table(out, name, rows):
    dump(out / (name + ".json"), rows)
    if rows:
        with (out / (name + ".csv")).open("x", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False)
                        if isinstance(v, (list, dict))
                        else "NA"
                        if v is None
                        else v
                        for k, v in row.items()
                    }
                )


def metric(rows, field="final_prediction", weighted=False):
    weights = [r["weight"] if weighted else 1 for r in rows]
    total = math.fsum(weights)
    answered = math.fsum(w for r, w in zip(rows, weights, strict=True) if r[field] is not None)
    correct = math.fsum(
        w for r, w in zip(rows, weights, strict=True) if r[field] == r["ground_truth"]
    )
    wrong = answered - correct
    return dict(
        n=len(rows),
        total_weight=total,
        answered=answered,
        correct=correct,
        incorrect=wrong,
        coverage=answered / total,
        accuracy=correct / answered if answered else None,
        correct_answer_rate=correct / total,
        incorrect_answer_rate=wrong / total,
        abstention_rate=(total - answered) / total,
    )


def equal_numeric(actual, expected):
    if isinstance(actual, (list, tuple)) or isinstance(expected, (list, tuple)):
        return (
            isinstance(actual, (list, tuple))
            and isinstance(expected, (list, tuple))
            and len(actual) == len(expected)
            and all(equal_numeric(a, b) for a, b in zip(actual, expected, strict=True))
        )
    return (
        type(actual) in (float, int)
        and type(expected) in (float, int)
        and math.isfinite(actual)
        and math.isfinite(expected)
        and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
    )


def audit_claim(c, e):
    """Independent comparisons against the saved public evidence, no checker import."""
    if c["type"] == "method_direction":
        m = e["method_result"]
        code = (
            "method_unavailable"
            if m is None
            else "method_execution_error"
            if m["status"] != "ok"
            else "method_threshold_unconfigured"
            if m["threshold"] is None
            else "method_direction_mismatch"
            if c["direction"] != m["predicted_direction"]
            else "method_claim_consistent"
        )
        expected = None if m is None else m["predicted_direction"]
    elif c["type"] == "display_row":
        rows = e["display_rows"]
        expected = rows[c["row_index"]] if rows is not None and c["row_index"] < len(rows) else None
        code = (
            "rows_unavailable"
            if rows is None
            else "row_unavailable"
            if expected is None
            else "row_claim_consistent"
            if equal_numeric(c["values"], expected)
            else "row_value_mismatch"
        )
    else:
        summary = e["summary"]
        expected = None if summary is None else summary.get(c["statistic"])
        code = (
            "summary_unavailable"
            if summary is None
            else "statistic_unavailable"
            if expected is None
            else "summary_claim_consistent"
            if (
                c["value"] == expected
                if c["statistic"] == "n_display"
                else equal_numeric(c["value"], expected)
            )
            else "summary_value_mismatch"
        )
    return code.endswith("_consistent"), code, expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    # All original run bytes, plus actual source/evaluator inputs. Never include diagnostics.
    inputs = sorted(
        set(
            [
                p
                for p in RUN.rglob("*")
                if p.is_file() and "diagnostics" not in p.relative_to(RUN).parts
            ]
            + list((ROOT / "runs/pilot-preparation/raw").glob("*"))
            + list((ROOT / "src").rglob("*.py"))
            + list(PREP.rglob("*.json"))
            + list(PREP.rglob("*.jsonl"))
            + [
                ROOT / "configs/pilot-data.json",
                ROOT / "configs/pilot-model.json",
                ROOT / "examples/real_data_pilot.py",
            ]
        )
    )
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    exports = RUN / "experiment/exports"
    runfile = next(p for p in exports.glob("*.json") if not p.name.endswith("-s2.json"))
    run = read(runfile)
    releases = read(runfile.with_name(runfile.stem + "-s2.json"))
    release_by = {r["source_attempt_id"]: r for r in releases}
    gold_list = read(PREP / "evaluator/records.json")
    gold = {e["case_id"]: e for e in gold_list}
    prepared = prepare_pilot(
        ROOT / "runs/pilot-preparation/raw", read(ROOT / "configs/pilot-data.json")
    )
    assert list(prepared.evaluator) == gold_list
    runtime = [json.loads(line) for line in (PREP / "runtime/pairs.jsonl").read_text().splitlines()]
    assert [p.model_dump(mode="json") for p in prepared.pairs] == runtime
    runtime_by = {p["case_id"]: p for p in runtime}
    mappings_list = read(RUN / "evaluation_mapping.json")
    mappings = {m["case_id"]: m for m in mappings_list}
    raw_analysis = [json.loads(line) for line in (RUN / "analysis.jsonl").read_text().splitlines()]
    assert analysis_rows(run, releases) == raw_analysis
    rescored = score_pilot(raw_analysis, gold_list, mappings_list)
    assert rescored == read(RUN / "pilot-scores.json")
    fresh_audit = audit_native(RUN / "experiment")
    assert fresh_audit["passed"], fresh_audit
    dump(out / "fresh-native-audit.json", fresh_audit)
    annotations = read(Path(__file__).with_name("explanation-annotations.json"))
    anno = {a["attempt_id"]: a for a in annotations}
    trials = run["trials"]
    assert len(anno) == len(trials) == 136
    records, checks, claims, pairs = [], [], [], {}
    trial_by = {}
    for t in trials:
        s, execution = t["start"], t["outcome"]["execution"]
        e, p = s["package"]["evidence"], execution["prediction"]
        selected = s["package"]["selected"]
        selection = selected["selection"]
        order = selection["column_order"]
        original_rows = runtime_by[e["case_id"]]["rows"]
        expected_method = [
            [original_rows[i][j] for j in order] for i in selection["method_indices"]
        ]
        expected_display = [
            [original_rows[i][j] for j in order] for i in selection["display_indices"]
        ]
        assert (
            selected["method_rows"] == expected_method
            and selected["display_rows"] == expected_display
        )
        case, package, strategy = e["case_id"], e["package"], s["condition"]["condition_id"]
        assert execution["failure_stage"] is None
        trial_by[(case, package, strategy)] = t
        ev, mp = gold[case], mappings[case]
        cause = 0 if ev["reference_direction"] == "first_to_second" else 1
        truth = "A_to_B" if mp["original_to_runtime_column_order"][0] == cause else "B_to_A"
        method_path = RUN / "anm" / case
        m = read(method_path / "result.json")
        assert m["margin"] == m["score_ba"] - m["score_ab"]
        calculated = (
            "A_to_B"
            if m["margin"] > m["threshold"]
            else "B_to_A"
            if m["margin"] < -m["threshold"]
            else None
        )
        assert calculated == m["predicted_direction"]
        a = anno[s["attempt_id"]]
        assert (
            a["case_id"] == case
            and a["package"] == package
            and a["strategy"] == strategy
            and a["text"] == p["reason_code"]
        )
        release = release_by.get(s["attempt_id"])
        checked = release["check"] if release else None
        independent = [audit_claim(c, e) for c in p["claims"]]
        for i, (c, (ok, code, expected)) in enumerate(zip(p["claims"], independent, strict=True)):
            claims.append(
                dict(
                    attempt_id=s["attempt_id"],
                    case_id=case,
                    package=package,
                    strategy=strategy,
                    claim_index=i,
                    claim=c,
                    expected=expected,
                    matching_display_row_indices=(
                        [
                            j
                            for j, row in enumerate(e["display_rows"] or [])
                            if equal_numeric(c["values"], row)
                        ]
                        if c["type"] == "display_row"
                        else None
                    ),
                    independently_consistent=ok,
                    reason_code=code,
                    actual_checker_evaluation=strategy == "S1",
                )
            )
        if checked:
            assert len(checked["claim_findings"]) == len(independent)
            for finding, (ok, code, _) in zip(checked["claim_findings"], independent, strict=True):
                assert finding["reason_code"] == code
                assert (finding["status"] == "pass") == ok
            expected_pass = all(audit[0] for audit in independent)
            assert (checked["status"] == "pass") == expected_pass
            assert checked["release"] == (expected_pass and not p["abstained"])
            assert release["released_direction"] == (
                p["predicted_direction"] if checked["release"] else None
            )
            checks.append(
                dict(
                    case_id=case,
                    pair_id=ev["original_pair_id"],
                    source_group=ev["source_group"],
                    package=package,
                    attempt_id=s["attempt_id"],
                    status=checked["status"],
                    release=checked["release"],
                    upstream_prediction=p["predicted_direction"],
                    ground_truth=truth,
                    final_prediction=release["released_direction"],
                    reason_codes=checked["reason_codes"],
                    claim_findings=checked["claim_findings"],
                    supplied_claim_count=len(p["claims"]),
                    independent_audit="confirmed_consistent"
                    if expected_pass
                    else "confirmed_rejection",
                    text_mismatch=a["strict_direction_conflict"],
                    text_categories=a["categories"],
                    context_path=str(runfile.relative_to(ROOT)) + "#trials/" + s["attempt_id"],
                )
            )
        if case not in pairs:
            sample = read(method_path / "sample.json")["rows"]
            arr = np.asarray(sample)
            pairs[case] = dict(
                case_id=case,
                pair_id=ev["original_pair_id"],
                source_group=ev["source_group"],
                weight=ev["weight"],
                ground_truth=truth,
                reference_direction=ev["reference_direction"],
                column_order=mp["original_to_runtime_column_order"],
                labels=[v["name"] for v in s["package"]["selected"]["variables"]],
                anm_score_ab=m["score_ab"],
                anm_score_ba=m["score_ba"],
                anm_margin=m["margin"],
                absolute_margin=abs(m["margin"]),
                threshold=m["threshold"],
                anm_prediction=m["predicted_direction"],
                anm_correct=m["predicted_direction"] == truth if m["predicted_direction"] else None,
                forced_sign_correct=("A_to_B" if m["margin"] > 0 else "B_to_A") == truth,
                original_row_count=ev["row_count"],
                method_n=len(sample),
                train_n=m["provenance"]["training_row_count"],
                eval_n=m["provenance"]["evaluation_row_count"],
                unique_a=len(set(arr[:, 0])),
                unique_b=len(set(arr[:, 1])),
                duplicate_row_fraction=1 - len(set(map(tuple, sample))) / len(sample),
                pearson_r=float(np.corrcoef(arr.T)[0, 1]),
                notes=ev["notes"],
                anm_artifact=str((method_path / "result.json").relative_to(ROOT)),
            )
        base = dict(
            case_id=case,
            pair_id=ev["original_pair_id"],
            source_group=ev["source_group"],
            weight=ev["weight"],
            ground_truth=truth,
            original_reference_direction=ev["reference_direction"],
            column_order=mp["original_to_runtime_column_order"],
            labels=e["variable_labels"],
            package=package,
            strategy=strategy,
            upstream_strategy=strategy,
            replicate_id=s["replicate_id"],
            retry_id=s["retry_id"],
            attempt_id=s["attempt_id"],
            run_id=execution["run_id"],
            model_config=s["config"],
            prompt_version=s["prompt_version"],
            package_digest=p["package_digest"],
            anm_score_ab=m["score_ab"],
            anm_score_ba=m["score_ba"],
            anm_margin=m["margin"],
            anm_threshold=m["threshold"],
            anm_prediction=m["predicted_direction"],
            anm_supplied=package == "E4",
            model_prediction=p["predicted_direction"],
            explanation=p["reason_code"],
            model_claims=p["claims"],
            model_correct=p["predicted_direction"] == truth if p["predicted_direction"] else None,
            anm_correct=m["predicted_direction"] == truth if m["predicted_direction"] else None,
            model_agrees_anm=p["predicted_direction"] == m["predicted_direction"],
            strict_text_conflict=a["strict_direction_conflict"],
            explanation_agrees_model=(a["direction_support"] == p["predicted_direction"])
            if a["direction_support"] in ("A_to_B", "B_to_A")
            else True
            if a["direction_support"] == "abstention"
            else None,
            text_categories=a["categories"],
            explanation_support=a["direction_support"],
            annotation_note=a["note"],
            checker_status=None,
            checker_reasons=None,
            checker_release=None,
            final_prediction=p["predicted_direction"],
            final_correct=p["predicted_direction"] == truth if p["predicted_direction"] else None,
            input_tokens=execution["generation"]["input_tokens"],
            output_tokens=execution["generation"]["output_tokens"],
            raw_artifact=str(runfile.relative_to(ROOT)),
            raw_trial_index=trials.index(t),
            missing_fields=[
                "checker_not_applicable_to_generation",
                "independent_long_form_explanation_not_collected",
            ],
        )
        records.append(base)
        if checked:
            records.append(
                base
                | dict(
                    strategy="S2",
                    upstream_strategy="S1",
                    checker_status=checked["status"],
                    checker_reasons=checked["reason_codes"],
                    checker_release=checked["release"],
                    final_prediction=release["released_direction"],
                    final_correct=release["released_direction"] == truth
                    if release["released_direction"]
                    else None,
                    input_tokens=0,
                    output_tokens=0,
                    missing_fields=[
                        "independent_S2_generation_not_applicable",
                        "independent_long_form_explanation_not_collected",
                    ],
                )
            )
    # Keep prespecified auxiliary baselines too, without fabricating independent model outputs.
    s1_by = {(r["case_id"], r["package"]): r for r in records if r["strategy"] == "S1"}
    for row in raw_analysis:
        if row["condition"] not in ("ANM_ONLY", "SIMPLE_GATE"):
            continue
        base = s1_by[(row["case_id"], row["package"])].copy()
        base.update(
            strategy=row["condition"],
            upstream_strategy="S1" if row["condition"] == "SIMPLE_GATE" else None,
            final_prediction=row["predicted_direction"],
            final_correct=row["predicted_direction"] == base["ground_truth"]
            if row["predicted_direction"]
            else None,
            input_tokens=0,
            output_tokens=0,
            missing_fields=["independent_baseline_generation_not_applicable"],
        )
        if row["condition"] == "ANM_ONLY":
            for key in [
                "model_prediction",
                "model_correct",
                "explanation",
                "model_claims",
                "strict_text_conflict",
                "explanation_support",
                "annotation_note",
                "attempt_id",
                "run_id",
                "model_config",
                "prompt_version",
                "model_agrees_anm",
                "explanation_agrees_model",
            ]:
                base[key] = None
            base["text_categories"] = []
        records.append(base)
    assert len(records) == len(raw_analysis) == 289
    for row in raw_analysis:
        found = [
            r
            for r in records
            if (r["case_id"], r["package"], r["strategy"])
            == (row["case_id"], row["package"], row["condition"])
        ]
        assert len(found) == 1 and found[0]["final_prediction"] == row["predicted_direction"]
    table(out, "case-level", records)
    table(out, "anm-pairs", list(pairs.values()))
    table(out, "checker-audit", checks)
    table(out, "claim-audit", claims)
    summary, agreements, confusions, mismatch = [], [], [], []
    groups = sorted({p["source_group"] for p in pairs.values()})
    source_metrics = []
    for (package, strategy), rs in itertools.groupby(
        sorted(records, key=lambda r: (r["package"], r["strategy"])),
        key=lambda r: (r["package"], r["strategy"]),
    ):
        rs = list(rs)
        for weighted in (False, True):
            summary.append(
                dict(
                    package=package,
                    strategy=strategy,
                    weighting="benchmark_weighted" if weighted else "unweighted",
                    stage="released",
                    **metric(rs, weighted=weighted),
                )
            )
            if strategy == "S2":
                summary.append(
                    dict(
                        package=package,
                        strategy=strategy,
                        weighting="benchmark_weighted" if weighted else "unweighted",
                        stage="upstream_S1",
                        **metric(rs, field="model_prediction", weighted=weighted),
                    )
                )
        for g in groups:
            subset = [r for r in rs if r["source_group"] == g]
            source_metrics.append(
                dict(package=package, strategy=strategy, source_group=g, **metric(subset))
            )
        for truth in ("A_to_B", "B_to_A"):
            for predicted in ("A_to_B", "B_to_A", None):
                subset = [
                    r
                    for r in rs
                    if r["ground_truth"] == truth and r["final_prediction"] == predicted
                ]
                confusions.append(
                    dict(
                        package=package,
                        strategy=strategy,
                        truth=truth,
                        prediction=predicted,
                        n=len(subset),
                        benchmark_weight=math.fsum(r["weight"] for r in subset),
                    )
                )
        both = [
            r for r in rs if r["final_prediction"] is not None and r["anm_prediction"] is not None
        ]
        answered = [r for r in rs if r["final_prediction"] is not None]
        agreements.append(
            dict(
                package=package,
                strategy=strategy,
                n=len(rs),
                agree_including_joint_abstention=sum(
                    r["final_prediction"] == r["anm_prediction"] for r in rs
                ),
                both_answer_n=len(both),
                both_answer_agreement=sum(
                    r["final_prediction"] == r["anm_prediction"] for r in both
                )
                / len(both)
                if both
                else None,
                model_answer_n=len(answered),
                agreement_on_model_answers=sum(
                    r["final_prediction"] == r["anm_prediction"] for r in answered
                )
                / len(answered)
                if answered
                else None,
                benchmark_weighted_agreement=sum(
                    r["weight"] for r in rs if r["final_prediction"] == r["anm_prediction"]
                )
                / sum(r["weight"] for r in rs),
                anm_visible=package == "E4",
            )
        )
        if strategy in ("S0", "S1"):
            mismatch.append(
                dict(
                    package=package,
                    strategy=strategy,
                    generations=len(rs),
                    answered=sum(r["model_prediction"] is not None for r in rs),
                    strict_conflicts=sum(r["strict_text_conflict"] for r in rs),
                    strict_conflict_rate=sum(r["strict_text_conflict"] for r in rs) / len(rs),
                    category_counts=dict(Counter(c for r in rs for c in r["text_categories"])),
                    informative_natural_language=sum(
                        r["explanation_support"] in ("A_to_B", "B_to_A", "internally_inconsistent")
                        for r in rs
                    ),
                )
            )
    table(out, "metrics", summary)
    table(out, "source-metrics", source_metrics)
    table(out, "anm-agreement", agreements)
    table(out, "confusion-matrices", confusions)
    table(out, "explanation-mismatches", mismatch)
    # Matched transitions: each of the 6 condition comparisons per strategy, no pooling.
    transitions, transition_summaries = [], []
    indexed = {(r["case_id"], r["package"], r["strategy"]): r for r in records}

    def state(r):
        return (
            "abstain"
            if r["final_prediction"] is None
            else "correct"
            if r["final_correct"]
            else "incorrect"
        )

    contrasts = (
        [
            (s, a, s, b)
            for s in ("S0", "S1", "S2")
            for a, b in itertools.combinations(("E1", "E2", "E3", "E4"), 2)
        ]
        + [("S1", e, "S2", e) for e in ("E1", "E2", "E3", "E4")]
        + [("S0", e, "S1", e) for e in ("E1", "E2", "E3", "E4")]
    )
    for s, a, t, b in contrasts:
        label = f"{a}/{s} -> {b}/{t}"
        matched = []
        for case in gold:
            x, y = indexed[(case, a, s)], indexed[(case, b, t)]
            item = dict(
                contrast=label,
                case_id=case,
                source_group=x["source_group"],
                weight=x["weight"],
                from_prediction=x["final_prediction"],
                to_prediction=y["final_prediction"],
                from_state=state(x),
                to_state=state(y),
                changed=x["final_prediction"] != y["final_prediction"],
                correct_rate_difference=int(bool(y["final_correct"]))
                - int(bool(x["final_correct"])),
                answered_difference=int(y["final_prediction"] is not None)
                - int(x["final_prediction"] is not None),
            )
            transitions.append(item)
            matched.append(item)
        transition_summaries.append(
            dict(
                contrast=label,
                n=17,
                changed=sum(r["changed"] for r in matched),
                state_transitions=dict(
                    Counter(r["from_state"] + "->" + r["to_state"] for r in matched)
                ),
                delta_correct_rate=statistics.mean(r["correct_rate_difference"] for r in matched),
                delta_coverage=statistics.mean(r["answered_difference"] for r in matched),
                weighted_delta_correct_rate=sum(
                    r["weight"] * r["correct_rate_difference"] for r in matched
                )
                / sum(r["weight"] for r in matched),
            )
        )
    table(out, "matched-transitions", transitions)
    table(out, "matched-summary", transition_summaries)
    threshold_rows = []
    thresholds = sorted(
        {0, 0.0005, 0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.015}
        | {p["absolute_margin"] for p in pairs.values()}
    )
    for tau in thresholds:
        rs = [
            p
            | dict(
                final_prediction=(
                    "A_to_B"
                    if p["anm_margin"] > tau
                    else "B_to_A"
                    if p["anm_margin"] < -tau
                    else None
                )
            )
            for p in pairs.values()
        ]
        for weighted in (False, True):
            threshold_rows.append(
                dict(
                    threshold=tau,
                    weighting="benchmark_weighted" if weighted else "unweighted",
                    **metric(rs, weighted=weighted),
                )
            )
    table(out, "threshold-sensitivity", threshold_rows)
    reject_counts = []
    for package in ("E1", "E2", "E3", "E4"):
        rs = [r for r in checks if r["package"] == package]
        reject_counts.append(
            dict(
                package=package,
                checked=len(rs),
                passed=sum(r["status"] == "pass" for r in rs),
                failed=sum(r["status"] == "fail" for r in rs),
                released=sum(r["release"] for r in rs),
                passed_abstentions=sum(r["status"] == "pass" and not r["release"] for r in rs),
                reason_counts=dict(
                    Counter(c for r in rs if r["status"] == "fail" for c in r["reason_codes"])
                ),
                zero_claim_outputs=sum(r["supplied_claim_count"] == 0 for r in rs),
            )
        )
    table(out, "checker-summary", reject_counts)
    # Exploratory source-cluster percentile bootstrap: common sampled groups across contrasts.
    rng = np.random.default_rng(261)
    group_draws = rng.integers(0, len(groups), size=(20000, len(groups)))
    counts = np.stack([(group_draws == i).sum(axis=1) for i in range(len(groups))], axis=1)
    intervals = []
    boot_cache = {}
    for e, s in [
        ("E4", "ANM_ONLY"),
        ("E3", "S0"),
        ("E3", "S1"),
        ("E3", "S2"),
        ("E1", "S0"),
        ("E1", "S1"),
        ("E1", "S2"),
    ]:
        rs = [indexed[(case, e, s)] for case in gold]
        for weighted in (False, True):
            totals = np.array(
                [
                    [
                        sum(
                            (r["weight"] if weighted else 1) * v
                            for r in rs
                            if r["source_group"] == g
                        )
                        for v in (1,)
                    ]
                    for g in groups
                ]
            ).ravel()
            answered = np.array(
                [
                    sum(
                        (r["weight"] if weighted else 1)
                        for r in rs
                        if r["source_group"] == g and r["final_prediction"] is not None
                    )
                    for g in groups
                ]
            )
            correct = np.array(
                [
                    sum(
                        (r["weight"] if weighted else 1)
                        for r in rs
                        if r["source_group"] == g and r["final_correct"]
                    )
                    for g in groups
                ]
            )
            den = counts @ totals
            ans = counts @ answered
            cor = counts @ correct
            vals = {
                "coverage": ans / den,
                "correct_answer_rate": cor / den,
                "accuracy": np.divide(cor, ans, out=np.full(cor.shape, np.nan), where=ans > 0),
            }
            boot_cache[(e, s, weighted)] = vals
            for name, v in vals.items():
                good = v[np.isfinite(v)]
                intervals.append(
                    dict(
                        contrast=f"{e}/{s}",
                        weighting="benchmark_weighted" if weighted else "unweighted",
                        metric=name,
                        estimate=metric(rs, weighted=weighted)[name],
                        lower=float(np.quantile(good, 0.025)) if len(good) else None,
                        upper=float(np.quantile(good, 0.975)) if len(good) else None,
                        defined_bootstraps=len(good),
                        draws=20000,
                        method="source_cluster_percentile_bootstrap_seed261",
                    )
                )
    for a, s, b, t in [
        ("E3", "S0", "E4", "ANM_ONLY"),
        ("E3", "S1", "E4", "ANM_ONLY"),
        ("E1", "S1", "E1", "S2"),
        ("E3", "S1", "E3", "S2"),
    ]:
        for weighted in (False, True):
            for name in ("coverage", "correct_answer_rate"):
                v = boot_cache[(b, t, weighted)][name] - boot_cache[(a, s, weighted)][name]
                ra = [indexed[(c, a, s)] for c in gold]
                rb = [indexed[(c, b, t)] for c in gold]
                intervals.append(
                    dict(
                        contrast=f"{a}/{s} -> {b}/{t}",
                        weighting="benchmark_weighted" if weighted else "unweighted",
                        metric="delta_" + name,
                        estimate=metric(rb, weighted=weighted)[name]
                        - metric(ra, weighted=weighted)[name],
                        lower=float(np.quantile(v, 0.025)),
                        upper=float(np.quantile(v, 0.975)),
                        defined_bootstraps=20000,
                        draws=20000,
                        method="paired_source_cluster_percentile_bootstrap_seed261",
                    )
                )
    table(out, "uncertainty", intervals)
    margins = {
        k: [p["absolute_margin"] for p in pairs.values() if p["anm_correct"] is k]
        for k in (True, False, None)
    }
    correct = margins[True]
    wrong = margins[False]
    margin_summary = {
        str(k): dict(n=len(v), minimum=min(v), median=statistics.median(v), maximum=max(v))
        for k, v in margins.items()
    }
    margin_summary["rank_auc_correct_vs_wrong_answered"] = sum(
        (c > w) + 0.5 * (c == w) for c in correct for w in wrong
    ) / (len(correct) * len(wrong))
    margin_summary["prediction_counts"] = dict(
        Counter(str(p["anm_prediction"]) for p in pairs.values())
    )
    margin_summary["ground_truth_counts"] = dict(Counter(p["ground_truth"] for p in pairs.values()))
    dump(out / "margin-summary.json", margin_summary)
    # Figures use matplotlib only; each also exported as SVG for inspectable vector text.
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150}
    )

    def save(fig, name):
        fig.tight_layout()
        for suffix in ("png", "svg"):
            target = out / (name + "." + suffix)
            if target.exists():
                raise FileExistsError(target)
            fig.savefig(target)
        plt.close(fig)

    colors = {"S0": "#2166ac", "S1": "#b35806", "S2": "#5e3c99", "ANM_ONLY": "#00875a"}
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for ax, weighting in zip(axs, ["unweighted", "benchmark_weighted"], strict=True):
        for r in summary:
            if (
                r["stage"] != "released"
                or r["weighting"] != weighting
                or r["strategy"] not in colors
            ):
                continue
            if r["accuracy"] is not None:
                ax.scatter(
                    r["coverage"],
                    r["accuracy"],
                    color=colors[r["strategy"]],
                    marker={"S0": "o", "S1": "s", "S2": "^", "ANM_ONLY": "x"}[r["strategy"]],
                    s=55,
                )
                ax.annotate(
                    r["package"] + "/" + r["strategy"],
                    (r["coverage"], r["accuracy"]),
                    xytext=(4, 4 + 8 * list(colors).index(r["strategy"])),
                    textcoords="offset points",
                    fontsize=7,
                )
        ax.set(
            xlim=(-0.03, 1.05),
            ylim=(-0.05, 1.2),
            xlabel="Coverage",
            ylabel="Accuracy among answers",
            title=weighting.replace("_", " "),
        )
        ax.text(0.03, 1.1, "Zero-answer conditions have undefined accuracy", fontsize=8)
    save(fig, "01-accuracy-coverage")
    fig, ax = plt.subplots(figsize=(10, 4))
    for i, p in enumerate(sorted(pairs.values(), key=lambda p: p["absolute_margin"])):
        ax.scatter(
            p["absolute_margin"],
            i,
            color="#00875a"
            if p["anm_correct"] is True
            else "#bf3030"
            if p["anm_correct"] is False
            else "#777777",
        )
        ax.text(
            p["absolute_margin"] + 0.0001, i, p["case_id"] + " / " + str(p["pair_id"]), fontsize=8
        )
    ax.axvline(0.001, color="black", linestyle="--", label="Deployed tau = .001")
    ax.set(
        xlabel="Absolute HSIC score difference (uncalibrated)",
        ylabel="Pairs sorted by margin",
        title="ANM: green correct, red incorrect, gray abstention",
        yticks=[],
        xlim=(0, 0.016),
    )
    ax.legend()
    save(fig, "02-anm-margin")
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for ax, weighting in zip(axs, ["unweighted", "benchmark_weighted"], strict=True):
        rs = [r for r in threshold_rows if r["weighting"] == weighting]
        ax.step(
            [r["threshold"] for r in rs],
            [r["coverage"] for r in rs],
            where="post",
            label="Coverage",
        )
        ax.step(
            [r["threshold"] for r in rs],
            [r["accuracy"] if r["accuracy"] is not None else np.nan for r in rs],
            where="post",
            label="Answer accuracy",
        )
        ax.axvline(0.001, color="gray", linestyle="--")
        ax.set(
            xlabel="Hypothetical threshold",
            ylabel="Rate",
            title=weighting.replace("_", " "),
            ylim=(-0.03, 1.03),
        )
        ax.legend()
    save(fig, "03-threshold-sensitivity")
    fig, ax = plt.subplots(figsize=(8, 4))
    codes = sorted({c for r in reject_counts for c in r["reason_counts"]})
    bottom = np.zeros(4)
    for code in codes:
        vals = np.array([r["reason_counts"].get(code, 0) for r in reject_counts])
        ax.bar(["E1", "E2", "E3", "E4"], vals, bottom=bottom, label=code)
        bottom += vals
    ax.set(
        ylabel="Rejected outputs with reason (overlapping counts)",
        title="68 cached checker evaluations; 5 distinct failures",
    )
    ax.legend(fontsize=8)
    save(fig, "04-checker-reasons")
    fig, ax = plt.subplots(figsize=(9, 4))
    for s in ("S0", "S1", "S2"):
        rs = [
            next(r for r in agreements if r["package"] == e and r["strategy"] == s)
            for e in ("E1", "E2", "E3", "E4")
        ]
        ax.plot(
            range(4),
            [r["agree_including_joint_abstention"] / 17 for r in rs],
            marker="o",
            label=s + " incl. abstentions",
            color=colors[s],
        )
        ax.plot(
            range(4),
            [
                r["both_answer_agreement"] if r["both_answer_agreement"] is not None else np.nan
                for r in rs
            ],
            linestyle=":",
            color=colors[s],
            label=s + " both answer",
        )
    ax.set(
        xticks=range(4),
        xticklabels=["E1", "E2", "E3", "E4"],
        ylabel="Unweighted agreement",
        ylim=(-0.03, 1.03),
        title="ANM is supplied only in E4",
    )
    ax.legend(fontsize=8, ncol=2)
    save(fig, "05-anm-agreement")
    fig, ax = plt.subplots(figsize=(8, 4))
    for offset, s in [(-0.17, "S0"), (0.17, "S1")]:
        rs = [
            next(r for r in mismatch if r["package"] == e and r["strategy"] == s)
            for e in ("E1", "E2", "E3", "E4")
        ]
        bars = ax.bar(
            np.arange(4) + offset,
            [r["strict_conflict_rate"] for r in rs],
            width=0.32,
            label=s,
            color=colors[s],
        )
        for bar, r in zip(bars, rs, strict=True):
            ax.text(
                bar.get_x() + 0.06,
                bar.get_height() + 0.005,
                f"{r['strict_conflicts']}/17",
                fontsize=8,
            )
    ax.set(
        xticks=range(4),
        xticklabels=["E1", "E2", "E3", "E4"],
        ylabel="Strict conflict / all generations",
        ylim=(0, 0.24),
        title="Manual text audit; short codes may be uninformative",
    )
    ax.legend()
    save(fig, "06-explanation-conflicts")
    session = read(RUN / "session.json")
    drift = []
    for name, expected in session["source_files_sha256"].items():
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            drift.append(name)
    assert not drift, drift
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    assert hashes == after
    dump(out / "input-sha256.json", hashes)
    validation = dict(
        original_inputs_unchanged=True,
        frozen_raw_data_and_metadata_revalidated=True,
        original_preparation_reproduced_in_memory=True,
        source_to_runtime_selection_verified=True,
        original_files_hashed=len(hashes),
        analysis_rows_reconstructed_exactly=True,
        original_weighted_scores_reproduced_exactly=True,
        session_source_hashes_match=True,
        native_audit_passed=True,
        checker_outputs_independently_adjudicated=len(checks),
        rejected_outputs_confirmed=sum(r["status"] == "fail" for r in checks),
        model_calls=0,
        anm_fits=0,
        n_pairs=len(pairs),
        n_generations=len(trials),
        n_case_rows=len(records),
        replicate_ids=sorted({r["replicate_id"] for r in records}),
        python=platform.python_version(),
        numpy=np.__version__,
        matplotlib=matplotlib.__version__,
        bootstrap_draws=20000,
        bootstrap_seed=261,
        original_token_usage=run["historical_usage"],
        max_input_tokens=max(
            t["outcome"]["execution"]["generation"]["input_tokens"] for t in trials
        ),
        max_output_tokens=max(
            t["outcome"]["execution"]["generation"]["output_tokens"] for t in trials
        ),
        terminal_reasons=sorted(
            {
                json.loads(t["outcome"]["execution"]["generation"]["raw_response"])["done_reason"]
                for t in trials
            }
        ),
        original_generation_latency_seconds=sum(
            t["outcome"]["execution"]["generation"]["latency_seconds"] for t in trials
        ),
    )
    dump(out / "validation.json", validation)
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
