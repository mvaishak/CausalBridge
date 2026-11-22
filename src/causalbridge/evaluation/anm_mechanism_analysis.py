"""Saved-result mechanism analysis: paired units are complete base datasets, not cells."""

from collections import Counter
from pathlib import Path

import numpy as np

from causalbridge.discovery.schemas import ANMResult, canonical_digest
from causalbridge.evaluation.anm_failure_audit import read, summary, verify_attempt, write
from causalbridge.evaluation.anm_mechanism_study import permutation_check, validate_plan


def kind(direction, reference):
    return "abstention" if direction is None else "correct" if direction == reference else "wrong"


def paired(rows, left, right, field, cfg, *, regime=None, n_train=None, n_eval=None):
    selected = [
        r
        for r in rows
        if (regime is None or r["regime"] == regime)
        and (n_train is None or r["n_train"] == n_train)
        and (n_eval is None or r["n_eval"] == n_eval)
    ]
    index = {(r["world_id"], r[field]): r for r in selected}
    worlds = sorted({r["world_id"] for r in selected})
    pairs = [(index[w, left], index[w, right]) for w in worlds]

    def values(p):
        return {
            k: sum((b["outcome"] == k) - (a["outcome"] == k) for a, b in p) / len(p)
            for k in ("correct", "wrong", "abstention", "execution_failure")
        }

    groups = {}
    for family in cfg["families"]:
        groups[family] = [p for p in pairs if p[0]["family"] == family]
    rng = np.random.default_rng(cfg["bootstrap_seed"])
    samples = {k: [] for k in values(pairs)}
    for _ in range(cfg["bootstrap_draws"]):
        draw = [
            group[i] for group in groups.values() for i in rng.integers(len(group), size=len(group))
        ]
        for k, value in values(draw).items():
            samples[k].append(value)
    intervals = {
        k: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] for k, v in samples.items()
    }
    return {
        "field": field,
        "left": left,
        "right": right,
        "regime": regime,
        "n_train": n_train,
        "n_eval": n_eval,
        "base_worlds": len(pairs),
        "difference_right_minus_left": values(pairs),
        "exploratory_paired_intervals": intervals,
    }


def analyze(plan, output, *, verify_permutations=True):
    plan, output = Path(plan), Path(output)
    manifest = validate_plan(plan)
    cfg = manifest["protocol"]
    completion = read(plan / "completion.json")
    if completion["manifest_digest"] != canonical_digest(manifest):
        raise ValueError("Completion/plan binding mismatch")
    records = [read(plan / "diagnostics" / (c["cell_id"] + ".json")) for c in manifest["schedule"]]
    if completion["diagnostics_digest"] != canonical_digest(records):
        raise ValueError("Saved diagnostic digest mismatch")
    rows = []
    for cell, diagnostic in zip(manifest["schedule"], records, strict=True):
        if diagnostic["cell_id"] != cell["cell_id"]:
            raise ValueError("Diagnostic cell identity mismatch")
        row = {**cell, "failure": diagnostic["failure"], "outcome": "execution_failure"}
        if diagnostic["failure"] is None:
            directory = plan / "attempts" / cell["cell_id"]
            result = ANMResult.model_validate(read(directory / "result.json"))
            if canonical_digest(result.model_dump(mode="json")) != diagnostic["result_digest"]:
                raise ValueError("Production result/diagnostic mismatch")
            verify_attempt(
                directory, {"numeric_relative_tolerance": 1e-9, "numeric_absolute_tolerance": 1e-12}
            )
            if verify_permutations:
                seed = np.random.SeedSequence(
                    [
                        cfg["permutation_seed"],
                        cfg["families"].index(cell["family"]),
                        cell["replicate"],
                        cell["n_eval"],
                    ]
                )
                for check in [*diagnostic["directions"].values(), diagnostic["oracle_forward"]]:
                    replay = permutation_check(
                        np.asarray(check["cause_vector"]),
                        np.asarray(check["residual_vector"]),
                        cfg,
                        seed,
                    )
                    for k in ("hsic", "exceedances", "pvalue", "rejected"):
                        if replay[k] != check[k]:
                            raise ValueError("Saved permutation calculation mismatch")
            forward = diagnostic["directions"][cell["reference"]]
            reverse = diagnostic["directions"][
                "B_to_A" if cell["reference"] == "A_to_B" else "A_to_B"
            ]
            row.update(
                direction=result.predicted_direction,
                outcome=kind(result.predicted_direction, cell["reference"]),
                margin=result.margin,
                forward_hsic=forward["hsic"],
                reverse_hsic=reverse["hsic"],
                learned_forward_rejected=forward["rejected"],
                learned_reverse_rejected=reverse["rejected"],
                oracle_forward_rejected=diagnostic["oracle_forward"]["rejected"],
                oracle_forward_hsic=diagnostic["oracle_forward"]["hsic"],
                conditional_mean_estimation_mse=diagnostic["conditional_mean_estimation_mse"],
                oracle_assisted_outcome=kind(
                    diagnostic["oracle_assisted_direction"], cell["reference"]
                ),
            )
        rows.append(row)
    output.mkdir(parents=True, exist_ok=False)
    cells = []
    for regime in cfg["regimes"]:
        for nt in cfg["train_sizes"]:
            for ne in cfg["evaluation_sizes"]:
                selected = [
                    r
                    for r in rows
                    if r["regime"] == regime and r["n_train"] == nt and r["n_eval"] == ne
                ]
                valid = [r for r in selected if r["failure"] is None]
                cell = {"regime": regime, "n_train": nt, "n_eval": ne, **summary(selected)}
                cell["learned_forward_rejections"] = sum(
                    r["learned_forward_rejected"] for r in valid
                )
                cell["oracle_forward_rejections"] = sum(r["oracle_forward_rejected"] for r in valid)
                cell["both_learned_directions_rejected"] = sum(
                    r["learned_forward_rejected"] and r["learned_reverse_rejected"] for r in valid
                )
                cell["median_conditional_mean_estimation_mse"] = (
                    float(np.median([r["conditional_mean_estimation_mse"] for r in valid]))
                    if valid
                    else None
                )
                cell["oracle_assisted_counts"] = dict(
                    Counter(r["oracle_assisted_outcome"] for r in valid)
                )
                cells.append(cell)
    effects = []
    for regime in cfg["regimes"]:
        for ne in cfg["evaluation_sizes"]:
            effects.append(paired(rows, 64, 256, "n_train", cfg, regime=regime, n_eval=ne))
        for nt in cfg["train_sizes"]:
            effects.append(paired(rows, 64, 256, "n_eval", cfg, regime=regime, n_train=nt))
    for nt in cfg["train_sizes"]:
        for ne in cfg["evaluation_sizes"]:
            effects.append(
                paired(
                    rows,
                    "independent_additive",
                    "heteroscedastic",
                    "regime",
                    cfg,
                    n_train=nt,
                    n_eval=ne,
                )
            )
    family_cells = [
        {
            "family": family,
            "regime": cell["regime"],
            "n_train": cell["n_train"],
            "n_eval": cell["n_eval"],
            **summary(
                [
                    r
                    for r in rows
                    if r["family"] == family
                    and r["regime"] == cell["regime"]
                    and r["n_train"] == cell["n_train"]
                    and r["n_eval"] == cell["n_eval"]
                ]
            ),
        }
        for family in cfg["families"]
        for cell in cells
    ]
    result = {
        "family_cells": family_cells,
        "version": cfg["version"],
        "phase": manifest["phase"],
        "scope": cfg["scope"],
        "scheduled_cells": len(rows),
        "base_worlds": len({r["world_id"] for r in rows}),
        "failures": sum(r["outcome"] == "execution_failure" for r in rows),
        "permutations_replayed_without_refitting": verify_permutations,
        "cells": cells,
        "paired_effects": effects,
        "runtime": manifest["runtime"],
        "source_sha256": manifest["source_sha256"],
        "manifest_digest": canonical_digest(manifest),
        "completion": completion,
    }
    write(output / "case-results.json", rows)
    write(output / "metrics.json", result)
    write_report(result, output / "report.md")
    return result


def write_report(result, output):
    lines = [
        "# ANM component mechanism study",
        "",
        "**Controlled synthetic pilot. These results do not identify "
        "the cause of errors on real pairs.**",
        "",
        f"Phase: {result['phase']}. {result['base_worlds']} base datasets, "
        f"{result['scheduled_cells']} paired factorial cells; "
        f"{result['failures']} execution failures. "
        "Changing train size preserves evaluation rows; changing evaluation size "
        "preserves training rows. "
        "Noise regimes share exogenous draws. Results below retain all scheduled worlds.",
        "",
        "| Regime | Train | Eval | C | W | A | F | Learned forward rejected | "
        "Oracle forward rejected | Median mean-function error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in result["cells"]:
        k = c["counts"]
        error = c["median_conditional_mean_estimation_mse"]
        error_text = "undefined" if error is None else f"{error:.5f}"
        lines.append(
            f"| {c['regime']} | {c['n_train']} | {c['n_eval']} | {k['correct']} | "
            f"{k['wrong']} | {k['abstention']} | {k['execution_failure']} | "
            f"{c['learned_forward_rejections']}/{c['n']} | "
            f"{c['oracle_forward_rejections']}/{c['n']} | "
            f"{error_text} |"
        )
    lines += [
        "",
        "## Oracle-assisted diagnostic (not a deployable method)",
        "",
        "Only the known true-direction regression is replaced. The reverse model stays learned.",
        "",
        "| Regime | Train | Eval | Oracle-assisted C | W | A |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cell in result["cells"]:
        counts = cell["oracle_assisted_counts"]
        lines.append(
            f"| {cell['regime']} | {cell['n_train']} | {cell['n_eval']} | "
            f"{counts.get('correct', 0)} | {counts.get('wrong', 0)} | "
            f"{counts.get('abstention', 0)} |"
        )
    lines += [
        "",
        "## Mechanism families",
        "",
        "| Family | Regime | Train | Eval | N | C | W | A | F |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in result["family_cells"]:
        counts = cell["counts"]
        lines.append(
            f"| {cell['family']} | {cell['regime']} | {cell['n_train']} | "
            f"{cell['n_eval']} | {cell['n']} | {counts['correct']} | "
            f"{counts['wrong']} | {counts['abstention']} | {counts['execution_failure']} |"
        )
    lines += [
        "",
        "## Matched effects",
        "",
        "Right minus left yield. Intervals resample whole base datasets within each of the "
        "two fixed mechanism families, preserving paired conditions. They are exploratory, "
        "unadjusted for multiple comparisons and do not represent uncertainty over new families.",
    ]
    for e in result["paired_effects"]:
        d, ci = e["difference_right_minus_left"], e["exploratory_paired_intervals"]
        lines.append(
            f"- {e['field']} {e['left']} → {e['right']}; regime={e['regime']}, "
            f"train={e['n_train']}, eval={e['n_eval']}: wrong yield {d['wrong']:+.1%} "
            f"[{ci['wrong'][0]:+.1%}, {ci['wrong'][1]:+.1%}]; correct yield {d['correct']:+.1%}."
        )
    lines += [
        "",
        "## Interpretation boundaries",
        "",
        "- Mean-function error is in original effect units, comparing learned predictions "
        "with the known conditional mean. "
        "Its change isolates prediction approximation here; it is not a causal-direction metric.",
        "- Oracle-forward residuals remove mean-regression approximation. Their dependence test "
        "can still reject under finite-sample randomness in the additive condition; nonrejection "
        "does not prove independence. Heteroscedasticity violates forward independent additive "
        "noise by construction, even when a finite test does not detect it.",
        "- Oracle-assisted directions replace only the true-direction score with an oracle score. "
        "They use privileged generating-function knowledge and are not a deployable method, "
        "upper bound, new benchmark or proposed production replacement.",
        "- Dependence tests use 99 residual permutations, a plus-one p-value, alpha .05 and "
        "a frozen 1e-12 numerical tie tolerance. They diagnose dependence, not causal truth. "
        "No threshold, kernel, model or sample exclusion was chosen from these outcomes.",
        "- This study uses two fixed functions, one noise amplitude and one heteroscedastic "
        "strength. It tests one assumption violation, not confounding, temporal dependence, "
        "all ANM mechanisms, or the specific soil/engine datasets.",
        "- Inspect failures and family-level outcomes before interpreting aggregate rates. "
        "A zero-error cell or interval is not proof of general reliability.",
    ]
    Path(output).write_text("\n".join(lines) + "\n")
