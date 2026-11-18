# Roadmap: completed work versus remaining research

Snapshot: merged upstream main `7085d2f` (through PR #9), plus open PRs #10/#11.
See [current status](current-status.md) for the current audit, open branches and remaining acceptance gates.
Sources: [detailed roadmap](../planning/Detailed_Implementation_Roadmap.pdf),
[working plan](../kris-track-b-plan.md), and the evidence-linked knowledge bank.
This is a capability/status map, not a percentage-complete claim. Passing synthetic
integration is distinct from completing the planned real-data experiment.

| Roadmap package | Owner | Evidence-backed status | Remaining |
| --- | --- | --- | --- |
| G1/G2 structural DAG utilities and backdoor checks | Arunima | Implemented and tested; used in the ten-group pilot | Live-case review / report |
| G3 exact insufficiency witness | Arunima + Anish | Same observed joint, opposite effects implemented; independent rational/engine confirmation extended to the ten-group pilot | Human review of new cases; live Track A run / report |
| N1 numerical intervention engine | Anish | Production engine merged; hand cases, reference comparisons and pilot confirmation tested | Use in final benchmark execution |
| N2 ANM diagnostic | Anish | Actual KRR/HSIC, pre-saved requests and error/ambiguity controls implemented; our native integration tested | Development threshold choice/freeze; real-data evaluation |
| D1 data audit/loader/source groups/splits | Faizah | Pilot loader exists on open PR #10; actual snapshot audit not reproduced here | Audited snapshot, eligibility/exclusions, approved names, source-group splits, runtime/evaluator mapping |
| D2 E1–E4 evidence packages | Kris | Implemented and tested; matched rows/context, sampling, summaries and bindings | Exercise real loader output; review sanitized labels/units |
| V1 reusable predictor/adapter | Vaishak + Kris | Native predictor integrated; pinned live Qwen3 8B smoke ran on synthetic observations | PR #8 fixes merged; real-data smoke remains |
| V2 process checker | Vaishak + Kris | Actual binding/typed-claim checker integrated; qualified disagreement and false attribution controls tested | Real-output error analysis; separate explanation audit if applicable |
| R1 S0/S1 execution and cached S2 | Kris | Durable attempts/raw replies, failures, resume/retries, model-free S2 and exports implemented/tested | Real-data/model execution under frozen protocol |
| Minimal baselines | Kris + Anish; scoring by Faizah | Simple-gate and ANM-only execution projections implemented | Faizah scorer-consumer acceptance and measured comparisons |
| E1 weighted metrics and group bootstrap | Faizah | Actual weighted pilot scorer on PR #10; fixture arithmetic passes; mapping integrity gap confirmed | Actual consumer acceptance, weighted outcomes and paired source-group intervals |
| ALL pilot/held-out/report | Team | Software/synthetic handshake evidence available | Real 15–20-pair pilot if eligible; freeze; held-out execution; figures/error cases; final report/presentation |

## Integration and research status

PR #9 is merged. PR #10 adds the real pilot loader/scorer; PR #11 supplies our
compatibility fix and actual-consumer tests. Both remain open. PR #11 passes 830
tests with one explicit unmerged-API skip; its CI is green. The combined tree
passes 870 tests. Earlier phase counts are historical, not the current tree.

The [project audit](../reviews/project-audit-2026-11-15.md) found that the pilot
scorer accepts a flipped external column order with an unchanged mapping ID.
Our strict private joins reject that inconsistency, but the pilot scoring path
must validate it too. Treat actual scorer acceptance as open until repaired.

The real pilot is reported completed (17 pairs/seven groups), but original bundles
are absent here and scores have not been independently reconciled. E4 shows no
reported incremental benefit over ANM. Uploaded ANM reports support numerical
fidelity while the frozen statistical recovery/stability gate fails. Neither is
a reason to alter past predictions or treat thresholds as calibrated confidence.

Track A retains its 50-question/ten-group synthetic benchmark and exact numerical
validation; live evaluation/human review remain. Final source-separated splits,
development decisions, ANM/preprocessing validation, protocol/metric/CI freeze,
held-out evaluation and report/presentation remain team work.

Readiness fixtures and software acceptance are substantial completed work. They
are not real-data causal-performance evidence or a substitute for frozen research
evaluation. See current-status.md for ownership and the precise critical path.
