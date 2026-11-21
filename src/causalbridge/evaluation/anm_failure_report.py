"""Generate evidence-bounded interpretation from the saved ANM audit's exact counts."""

from pathlib import Path


def triplet(cell):
    c = cell["counts"]
    return f"{c['correct']} / {c['wrong']} / {c['abstention']} / {c['execution_failure']}"


def fraction(value):
    return (
        f"{value['numerator']}/{value['denominator']}"
        if value["denominator"]
        else "undefined (0/0)"
    )


def report(metrics, output):
    real = metrics["real"]
    wrong = real["outcome_diagnostics"]["wrong"]
    correct = real["outcome_diagnostics"]["correct"]
    groups = real["source_groups"]
    lines = [
        "# ANM failure diagnosis: saved-data investigation",
        "",
        "## Verdict",
        "",
        "The saved evidence supports multiple failure modes, not one established root cause. "
        "Some wrong arrows are split-sensitive; others remain wrong. Sample size is associated "
        "with outcomes but mostly confounded with source family. Ties alone do not explain "
        "the errors. Neither split stability nor residual-dependence ranking "
        "establishes causal truth.",
        "",
        f"Verified {metrics['archive_files_verified']:,} archived files, "
        f"{metrics['real_attempts_verified']} saved real attempts and "
        f"{metrics['synthetic']['verified_attempts']} saved synthetic attempts. "
        "No new ANM fits, permutations, LLM calls or threshold selection. "
        "Repeated attempts are not independent datasets.",
        "",
        "## 1. The real-data result is reproduced",
        "",
        "Counts are correct / wrong / abstention / execution failure. Every seed retains "
        "the same 38 pairs in 12 source groups; only the training/evaluation split changes.",
        "",
        "| Split | C / W / A / F | Directional accuracy | Coverage |",
        "|---|---|---|---|",
    ]
    for seed, cell in real["splits"].items():
        lines.append(
            f"| {seed} | {triplet(cell)} | {fraction(cell['answered_accuracy'])} | "
            f"{fraction(cell['coverage'])} |"
        )
    lines += [
        "",
        "Primary seed 261: 50% unweighted answered accuracy; weighted correct and wrong "
        "yields are 35.3% and 38.1% of total weight 10.8, giving weighted answered "
        "accuracy 48.1%. These agree with the frozen ANM-only result. Model execution "
        "failures from the separate LLM pipeline must not be inserted into ANM counts.",
        "",
        "## 2. Some wrong directions are unstable; others persist",
        "",
        f"Among 13 primary wrong cases, {fraction(wrong['raw_sign_stable'])} keep the same "
        f"nonzero raw-margin sign across all three splits. In contrast, "
        f"{fraction(correct['raw_sign_stable'])} primary correct cases do so. "
        "Raw sign stability differs from decision stability because the fixed threshold "
        "can turn a small signed margin into abstention.",
        "",
        f"Only {fraction(wrong['correct_any_split'])} primary wrong cases become correct "
        f"on at least one saved split. {fraction(wrong['wrong_all_splits'])} remain wrong "
        "on every split. Therefore, changing a random seed sometimes changes the result, "
        "but repeated agreement can preserve an incorrect direction. No favorable seed "
        "is substituted for the primary seed.",
        "",
        "## 3. Sample size matters in compatible simulations; the real association is confounded",
        "",
        "| Real primary stratum | N | C / W / A / F | Answered accuracy |",
        "|---|---:|---|---|",
    ]
    for label in ("full_512", "fewer_than_512"):
        cell = real["strata"][label]
        lines.append(
            f"| {label} | {cell['n']} | {triplet(cell)} | {fraction(cell['answered_accuracy'])} |"
        )
    overlap = ", ".join(real["sample_size_overlap_source_groups"]) or "none"
    lines += [
        "",
        f"Only these source groups contain both full and shorter samples: **{overlap}**. "
        "Most of the size comparison also changes source/mechanism. It does not show "
        "that collecting more observations would fix the real wrong cases.",
        "",
        "The cached synthetic comparison uses the same generated dataset IDs at both "
        "sizes. Selected 128-row samples are nested in the 512-row samples for all 32 "
        "compatible datasets in each partition. Both training and evaluation sample "
        "sizes change, so regression learning and HSIC finite-sample effects are not separated.",
        "",
        "| Synthetic partition, primary split | Rows | C / W / A / F |",
        "|---|---:|---|",
    ]
    for cell in metrics["synthetic"]["compatible_panels"]:
        if cell["split_seed"] == 261:
            lines.append(f"| {cell['partition']} | {cell['n_rows']} | {triplet(cell)} |")
    lines.append("")
    for pair in metrics["synthetic"]["paired_sample_size"]:
        transitions = pair["transitions_128_to_512"]
        lines.append(
            f"- {pair['partition']}: {transitions.get('wrong_to_correct', 0)} wrong → correct, "
            f"{transitions.get('wrong_to_abstention', 0)} wrong → abstention, "
            f"{transitions.get('correct_to_abstention', 0)} correct → abstention. "
            "Larger samples removed wrong releases here but did not retain every correct answer."
        )
    lines += [
        "",
        "This is evidence of finite-sample sensitivity under the tested synthetic "
        "construction. It does not identify the source of real-data failure. Known "
        "nonidentified/assumption-violation controls have null causal accuracy, not "
        "manufactured correct/wrong labels.",
        "",
        "## 4. Repeated values are not a sufficient explanation",
        "",
        "The descriptive cutoff is a largest tied value occupying at least 10% of "
        "either selected column. It is a post-outcome audit bin, not a tuned exclusion rule.",
        "",
        "| Tie stratum | N | C / W / A / F |",
        "|---|---:|---|",
    ]
    for label in ("tie_at_least_10pct", "tie_below_10pct"):
        cell = real["strata"][label]
        lines.append(f"| {label} | {cell['n']} | {triplet(cell)} |")
    lines += [
        "",
        "Both strata contain correct and wrong answers. These counts do not support "
        "a blanket claim that ties caused the failure. Exact-row overlap across a split "
        "is reported descriptively; without original unit IDs it cannot establish leakage "
        "or that repeated values came from the same physical observation.",
        "",
        "## 5. Margin and fit quality do not certify a direction",
        "",
        f"On the 38-pair panel, median absolute margin is {real['margin']['median_correct']:.6f} "
        f"for correct releases and {real['margin']['median_wrong']:.6f} for wrong releases. "
        f"The descriptive correct-versus-wrong rank AUC is {real['margin']['rank_auc']:.3f}. "
        "This suggests some ranking information here, not a calibrated confidence measure. "
        "It must not be conflated with the original 17-pair pilot's different margin result. "
        "No margin cutoff is selected. Leave-one-source-out AUC values are in metrics.json; "
        "they are sensitivity checks, not independent replications.",
        "",
        f"In {fraction(wrong['reference_fit_lower_mse'])} wrong primary cases, the "
        "reference direction has lower held-out standardized prediction MSE than the "
        "opposite direction, yet ANM chooses the wrong direction. Production chooses "
        "lower residual dependence, not lower prediction error. This pinpoints a ranking "
        "disagreement; MSE itself is not a causal-direction oracle.",
        "",
        "The separate cached four-pair development adequacy study gives more detail:",
        "",
        "| Pair | Reference MSE | Opposite MSE | Cached permutation-test outcome |",
        "|---|---:|---:|---|",
    ]
    for row in metrics["development"]["adequacy_primary"]:
        lines.append(
            f"| {row['pair_id']} | {row['reference_direction_mse']:.3f} | "
            f"{row['opposite_direction_mse']:.3f} | {row['reason']} |"
        )
    lines += [
        "",
        "Pairs 12 and 17: only the benchmark-wrong direction was not rejected. "
        "Pair 93: both directions rejected. Pair 99: neither direction rejected. "
        "Nonrejection is not proof of independence, and permutations assume exchangeability. "
        "These tests cover only four development pairs; their results cannot be assigned "
        "to all 38 validation cases. The existing parameter comparisons and adequacy "
        "gate did not establish a reliable real-data method; they are not newly tuned here.",
        "",
        "## 6. Source families and every primary wrong case",
        "",
        "Small groups and different sample sizes prevent a general domain-ranking claim.",
        "",
        "| Source | N | C / W / A / F | Selected sizes |",
        "|---|---:|---|---|",
    ]
    for name, cell in groups.items():
        lines.append(
            f"| {name} | {cell['n']} | {triplet(cell)} | "
            f"{', '.join(map(str, cell['selected_sizes']))} |"
        )
    lines += [
        "",
        "| Pair | Source | N | Absolute margin | Outcomes 261 / 1261 / 2261 |",
        "|---|---|---:|---:|---|",
    ]
    for row in sorted(real["case_results"], key=lambda r: r["absolute_margin"], reverse=True):
        if row["outcome"] == "wrong":
            outcomes = " / ".join(row["split_outcomes"][str(s)] for s in (261, 1261, 2261))
            lines.append(
                f"| {row['pair_id']} | {row['source_group']} | "
                f"{row['quality']['selected_rows']} | "
                f"{row['absolute_margin']:.6f} | {outcomes} |"
            )
    lines += [
        "",
        "## 7. Source context for the three persistently wrong cases",
        "",
        "The two soil pairs share a source family; these are three cases from two "
        "families, not three independent source replications. The following are manual "
        "paraphrases of source descriptions checked against the pinned file hashes. "
        "Full description digests and unresolved questions are in metrics.json.",
        "",
    ]
    for case in metrics["source_metadata_review"]["cases"]:
        row = next(r for r in real["case_results"] if r["pair_id"] == case["pair_id"])
        lag = row["quality"]["adjacent_selected_row_correlation"]
        values = ", ".join("undefined" if v is None else f"{v:.3f}" for v in lag)
        lines.append(
            f"- Pair {case['pair_id']} ({case['source_member']}): "
            + " ".join(case["observations"])
            + f" Adjacent selected-row correlations for runtime A/B: {values}. "
            + " ".join(case["unresolved"])
        )
    lines += [
        "",
        "Adjacent-row correlations describe the saved source-row order, which can "
        "have unequal spacing. Values are rounded to three decimals. Without unit/time "
        "IDs, correlation does not establish "
        "serial dependence, leakage or its causal role in the error. These metadata "
        "observations motivate targeted tests; they are not diagnosed assumption violations.",
    ]
    lines += [
        "",
        "## 8. What is verified, suggested and unresolved",
        "",
        "**Verified:** archive integrity, request/sample/configuration and column mapping "
        "bindings, threshold arithmetic, split indices, training-only means/scales, "
        "reproducibility digests, and cached residual-moment/MSE consistency. All scheduled "
        "attempts are retained. This found no such preparation/accounting defect in the "
        "audited records; it is not a fresh independent KRR/HSIC reconstruction. "
        "Mapping is checked against its seed and saved binding; the complete upstream "
        "snapshot is not reread to reconstruct every original selected observation.",
        "",
        "**Supported interpretation:** finite samples and split sensitivity contribute "
        "to fragility in the saved simulations; real split sensitivity and persistently "
        "wrong preferences are both observed. Lower residual "
        "dependence can favor the benchmark-wrong direction. Neither a large margin, "
        "a stable sign nor a nonrejected independence test guarantees correct identification.",
        "",
        "**Unresolved:** which real cases violate additive-noise assumptions, whether "
        "confounding/selection/cluster dependence is decisive, which reference labels "
        "are imperfect, and whether the fixed regression/bandwidth settings contribute. "
        "Tied values and sample-size associations do not establish these causes.",
        "",
        "## 9. Recommended next work",
        "",
        "1. Keep this audit separate from Vaishak's LLM cue experiment. The LLM study "
        "tests downstream propagation; this audit characterizes upstream fragility.",
        "2. If more ANM work is justified, freeze a known-truth synthetic factorial "
        "experiment separating training size from evaluation size and additive noise "
        "from one specific violation at a time. Use multiple fresh dataset seeds, "
        "report all conditions, and retain a fixed baseline. This is proposed, not executed.",
        "3. Obtain source-level metadata for the persistently wrong real cases before "
        "claiming a case-specific assumption violation. Existing source descriptions "
        "raise concerns but do not identify the decisive cause.",
        "4. Do not tune thresholds, reverse arrows, select a favorable split, or exclude "
        "difficult pairs after seeing labels. A revised accuracy claim needs a new "
        "source-separated evaluation cohort.",
        "",
        "## Theory and external context",
        "",
        "ANM identification depends on additive-noise structure and additional conditions; "
        "a theorem is not a guarantee for a finite-sample fixed implementation. See "
        "[Peters et al. (2014)](https://jmlr.org/papers/v15/peters14a.html). "
        "The broader CauseEffectPairs study reports useful ANM performance with other "
        "evaluation details, so this audit does not refute ANM as a whole: "
        "[Mooij et al. (2016)](https://jmlr.org/papers/v17/14-518.html). "
        "Neither publication validates our particular 38 outputs.",
        "",
        "Generated from metrics.json; see the shared experiment guide for reproduction. "
        "No significance, causal root-cause or improvement claim is made.",
    ]
    Path(output).write_text("\n".join(lines) + "\n")
