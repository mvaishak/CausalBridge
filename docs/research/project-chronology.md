# Project chronology

| Period | Work and dependency |
| --- | --- |
| Oct 27–Nov 15 | Verifier/orchestration, graph witnesses, numerical engine, ANM, data audit, evidence packages, predictor, checker and pilot runner developed in team branches and merged through PRs 1–9. See [lineage audit](../reviews/branch-lineage-and-provenance-audit.md). |
| Nov 14–18 | Frozen 17-pair Track B pilot, 128-row ANM validation, later 512-row synthetic and 38-pair real ANM validation. The 38 reference labels became opened. |
| Nov 19–20 | Final Track A live run, final report/slides, then integrated live Track B run on the opened 38-pair panel and failure-accounting corrections. `main` reached `fb81b96`. |
| Nov 21 | Thinking ablation `ecd1b30` used the opened 17-pair cohort. Diagnostic v1 `b8b5b44` failed preflights; Anish's v2 `4f600b4` changed the output contract; v3 `7d4a408` changed evidence-basis flags and completed a 4/20/170 gate/full run. The last run lived outside Git until this integration. |
| Nov 21 | Anish's independent ANM diagnosis `d3be02c` investigated saved results and synthetic mechanisms; it is a scientific follow-up, not a Git ancestor of the v3 run. Arunima's independent counterfactual cue branch `368d648` prepared 24 synthetic worlds and 96 calls but has no verified live results. |
| Nov 22 | This branch consolidated distinct research streams without changing the submitted report, slides or frozen protocols. |

Git ancestry, input consumption and scientific follow-up are different relations. See [provenance](branch-provenance.md).
