# Roadmap: completed work versus remaining research

Snapshot: merged upstream main `1dd84b4` (through PR #8).
See [current status](current-status.md) for open PR #9, live artifacts and remaining acceptance gates.
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
| D1 data audit/loader/source groups/splits | Faizah | No completed handoff observed in this repository snapshot | Audited snapshot, eligibility/exclusions, approved names, source-group splits, runtime/evaluator mapping |
| D2 E1–E4 evidence packages | Kris | Implemented and tested; matched rows/context, sampling, summaries and bindings | Exercise real loader output; review sanitized labels/units |
| V1 reusable predictor/adapter | Vaishak + Kris | Native predictor integrated; pinned live Qwen3 8B smoke ran on synthetic observations | PR #8 fixes merged; real-data smoke remains |
| V2 process checker | Vaishak + Kris | Actual binding/typed-claim checker integrated; qualified disagreement and false attribution controls tested | Real-output error analysis; separate explanation audit if applicable |
| R1 S0/S1 execution and cached S2 | Kris | Durable attempts/raw replies, failures, resume/retries, model-free S2 and exports implemented/tested | Real-data/model execution under frozen protocol |
| Minimal baselines | Kris + Anish; scoring by Faizah | Simple-gate and ANM-only execution projections implemented | Faizah scorer-consumer acceptance and measured comparisons |
| E1 weighted metrics and group bootstrap | Faizah | PR #9 adds metric/fixed-resample acceptance fixtures; actual scorer handoff pending | Actual consumer acceptance, weighted outcomes and paired source-group intervals |
| ALL pilot/held-out/report | Team | Software/synthetic handshake evidence available | Real 15–20-pair pilot if eligible; freeze; held-out execution; figures/error cases; final report/presentation |

## Roadmap versus readiness phases

The original roadmap's contracts/runner/audit/native-integration capabilities are
implemented. Its real-data pilot, protocol freeze, held-out evaluation and final
report remain incomplete. Do not confuse these with the recent readiness phases.

Readiness phases 1–2 (live infrastructure fixes and saved-run replay) are complete;
PR #8 is merged. Phases 3–6 (boundary validation, evaluator joins, scorer fixtures
and offline pipeline acceptance) are committed in open [PR #9](https://github.com/mvaishak/CausalBridge/pull/9),
implementation head `bcad4a3`. Review/publication and knowledge-bank cleanup are
complete; team acceptance/merge remains pending.

## Current validation and scientific scope

The reviewed PR #9 implementation passes **818 tests**, Ruff lint/format, both
Track A demos, synthetic ANM handshake and builds; GitHub CI passed Python 3.12
and 3.13. Historical milestone counts remain in the phase documents.

Track A has 50 synthetic questions across ten graph groups, with human review and
live execution pending. Track B has two saved live-model smokes on synthetic
observations and verified checker-0.3 replays, not a real-data research pilot.

The offline acceptance demo reproduces 136 scorer-input rows for eight synthetic
cases using 64 scripted attempts and 32 cached S2 outcomes, with a passing audit
and zero extra S2/resume calls. Tiny method inputs intentionally test the typed
ANM failure path. H1/H2/H3 fixtures and fixed paired group resamples are acceptance
oracles, not measured research results or confidence intervals.

## Remaining critical path

Accept audited loader/reference/group/split records and the actual weighted scorer;
validate one real pilot pair end to end; run pilot/development work; freeze all
protocol/metric/CI choices; execute held-out evaluation without tuning; produce
comparisons, figures, errors and final reproducibility/report/presentation outputs.
See [current status](current-status.md) for exact ownership and parallel work.
