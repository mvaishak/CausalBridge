# Final results analysis

## Answer to the research question

Structured evidence and deterministic checking made model outputs more auditable in the tested system. They did **not** establish an improvement in causal direction reliability. Track A's live local model answered only 2/50 synthetic questions and misinterpreted the query type in 41/50 cases. Track B's E4 model decisions copied ANM exactly on all 17 real pilot pairs, including eight benchmark-wrong answers; the checker made no E4 release change. These are two distinct tasks and are not pooled into a single accuracy claim.

## Direction, abstention and matched comparisons

Track A: 29 answerable and 21 unanswerable cases yielded one correct answer, one wrong answer, 27 false abstentions and 21 correct abstentions. Coverage was 4%, answered accuracy 50% on only two answers, correct-answer yield 2%, and correct answer-or-abstain rate 44%. The model issued 102 live stages. The graph-only/partial/full evidence conditions are described in `final-track-a-evaluation.md`; no matched independent prompt strategy was predeclared for this run.

Track B: E4 S0, S1, S2, simple gate and ANM-only all answered 14/17, with 6 reference-correct, 8 wrong and 3 abstentions. Benchmark-weighted coverage was 89.0%, answered accuracy 40.0%, correct yield 35.6%, wrong yield 53.4%. E3/S0 answered 8/17 (4 correct, 4 wrong), with 67.1% weighted coverage and 59.2% weighted answered accuracy. The matched E3→E4 S0 transition changed 13 decisions, including 4 correct→wrong and 1 wrong→correct. The unweighted correct yield rose 11.8 percentage points, while benchmark-weighted correct yield fell 4.1 points. This is a small, source-dependent exploratory contrast, not proof of a general directional effect.

The seven-group Track B cluster bootstrap in `artifacts/final-delivery/track-b-diagnostics/uncertainty.json` reports an exploratory 95% interval of 76.2–100% for E4 weighted coverage and 12.3–70.6% for weighted answered accuracy. A 12-group exploratory bootstrap on the real ANM validation yields 53.1–88.2% unweighted coverage and 27.3–72.7% answered accuracy. These intervals are broad, and reference labels and group definitions add uncertainty that bootstrap sampling does not capture. Track A's ten-group interval gives 0–12% coverage. No significance test is asserted.

## Diagnostics and evidence checking

The frozen ANM at 128 rows failed its recovery and stability gate; a fresh 512-row synthetic panel had 26/32 correct and 6 abstentions. On 38 real benchmark pairs under the fixed up-to-512-row setting, it had 13 correct, 13 wrong and 12 abstentions, with 73.4% weighted coverage and 48.1% weighted answered accuracy. The 38 outcomes have been opened. Their source groups do not overlap the 17-pair pilot, but no LLM run exists for that real panel. The synthetic and real sample regimes and assumptions differ. The observed gap is real; a single causal explanation for it is not established.

The checker suppressed five invalidly supported Track B answers outside E4: three benchmark-wrong and two benchmark-correct. Among answered upstream proposals across packages, it accepted six correct and nine wrong, and rejected two correct and three wrong. Forty-eight upstream abstentions had zero typed claims. The checker catches the observed unavailable evidence and row-value mismatches, but free-text contradictions can pass and passing citations do not certify a causal arrow. Track A exposes another boundary: its verifier marked an answer to a misparsed query `verified` even though the answer contradicted the original sign question.

## Calibration, failures and limitations

The ANM margin is an HSIC score difference, not a probability. The pilot has too few independent source groups and too few E4 decision differences to fit a useful calibration curve. The 38 real validation split signs agree across all three splits on only 23/38 pairs, a sensitivity warning. The selected Track A failure `G006_sign_complete` and Track B's eight E4 wrong answers are traceable to raw records. The benchmark labels are scoring references, not guaranteed interventions. The one-model, small-cohort evidence does not support a general performance benefit. A future revised method must be frozen and tested on new source-separated data.

Recompute the saved metrics, case joins, intervals and vector outcome plot with `uv run --extra anm python scripts/final_analysis.py`. Source data are in `artifacts/final-delivery/analysis/`; the plot is `outcomes.svg`.
