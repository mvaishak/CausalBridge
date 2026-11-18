# Roadmap: completed work versus remaining research

Snapshot: main `dbbf8db` (including PR #11) plus all changes from
`pilot-case-diagnosis` at `7a886f1`, on local branch
`codex/faizah-pilot-diagnosis`. Committing this integration branch does not merge
those changes into main. Earlier phase notes retain their historical counts.
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
| D1 data audit/loader/source groups/splits | Faizah | Imported loader, pinned snapshot manifest, eligibility audit and frozen evaluation roster | Reproduce snapshot checks and reconcile authentic original-pilot artifacts |
| D2 E1–E4 evidence packages | Kris | Implemented and tested; matched rows/context, sampling, summaries and bindings | Exercise real loader output; review sanitized labels/units |
| V1 reusable predictor/adapter | Vaishak + Kris | Native predictor integrated; pinned live Qwen3 8B smoke ran on synthetic observations | PR #8 fixes merged; real-data smoke remains |
| V2 process checker | Vaishak + Kris | Actual binding/typed-claim checker integrated; qualified disagreement and false attribution controls tested | Real-output error analysis; separate explanation audit if applicable |
| R1 S0/S1 execution and cached S2 | Kris | Durable attempts/raw replies, failures, resume/retries, model-free S2 and exports implemented/tested | Real-data/model execution under frozen protocol |
| Minimal baselines | Kris + Anish; scoring by Faizah | Simple-gate and ANM-only execution projections implemented | Faizah scorer-consumer acceptance and measured comparisons |
| E1 weighted metrics and group bootstrap | Faizah | Imported weighted scorer and seeded mapping-identity fix; merged consumer acceptance fixtures retained | Actual consumer acceptance, weighted outcomes and paired source-group intervals |
| ALL pilot/held-out/report | Team | Software/synthetic handshake evidence available | Real 15–20-pair pilot if eligible; freeze; held-out execution; figures/error cases; final report/presentation |

## Integration and evaluation handoff

The loader, source manifest, eligibility audit, scorer and diagnosis now exist in
this local working tree. Main's PR #9/#11 handoff/consumer checks are retained.
Code is transferred from the source branch, including its pilot-readiness
prerequisites; it is not restricted to the latest roster commit.

The [evaluation handoff](../evaluation_handoff.md) and
`configs/evaluation-roster.json` specify 17 frozen pilot pairs, four development
pairs (12, 17, 93, 99), 38 validation pairs and 49 entries excluded from scoring.
Source groups stay in their assigned roles. Pilot outcomes and validation cases
must not select a change. The roster sets no numerical accuracy acceptance bar.

The [data audit](../data_audit.md) accounts for all 108 source entries. Twelve
unused entries stay in the seven pilot families with exclusions; other eligible
source groups are assigned to development or test. Held-out pairs have not been
executed. Raw snapshots and prepared outputs remain ignored local artifacts.

## Historical pilot evidence and remaining work

The source branch reports a completed live pilot: 17 pairs/seven groups, 136
live generations, 68 S2 checks, no execution/ANM errors and zero additional calls
on resume. E4 S0/S1/S2 and ANM-only reportedly have identical arrows, 89.0%
weighted coverage and 40.0% weighted selective accuracy. The earlier full-cohort
offline check used real observations/ANM with scripted replies. Transferring code
does not independently reproduce the live results. See [pilot guide](../pilot_run.md).

The scorer checks mapping identity and deterministic column orientation, closing
the earlier altered-order gap. PR #14's review follow-up also restores the full
PR #13 correction (`cf64934`), validates exact saved S1 lineage during scoring,
enforces roster eligibility/source-group isolation, and separates checker errors
from completed suppression. These close the reported integration gaps; they do
not independently certify the original live-pilot bundle or its claimed scores.

Uploaded ANM reports support numerical fidelity but fail the frozen statistical
recovery/stability gate. No statistical repair is introduced by this transfer.
Threshold 0.001 remains exploratory. The checker permits empty claims and
qualified disagreement; passing it establishes neither causal correctness nor
complete evidence support.

Track A retains its 50-question/ten-group synthetic benchmark and exact numerical
checks. Remaining team work includes numerical development, original-run audit,
protocol/metric freeze, untouched validation and held-out execution, paired
source-group bootstrap intervals, error analysis, figures and final reporting.
See [current status](current-status.md) and the original project audit for
historical evidence and ownership. Do not modify old predictions or tune against
the frozen pilot to improve reported scores.

## Local transfer verification

At the initial transfer (`7aec8fd`), all 26 source-code, configuration, schema,
example and test files changed by the source branch matched `7a886f1` byte for
byte. The review follow-up deliberately adds corrections below. Main's handoff, evaluator joins and
actual-consumer acceptance tests are retained. The documentation conflict was
resolved without removing either branch's implemented capabilities.

`bash scripts/check.sh` passes: 904 tests passed, two snapshot-location skips,
89% statement coverage, Ruff lint/format, both Track A demos, computed synthetic
ANM handshake and source/wheel builds. The skipped snapshot and roster checks
were separately run successfully against `/tmp/causalbridge-pr10-snapshot`;
the roster reports 17 pilot, four development, 38 validation and 49 excluded pairs.
Log: ignored `runs/faizah-transfer-check/repository-check.log`.

The user authorized committing/publishing this integration and removing Faizah's
five follow-up commits from `pilot-case-diagnosis` through a normal revert. The
integration merge retains their original authorship/history; the source cleanup
preserves the preceding pilot-readiness work. No model-server calls or PR creation
are part of the transfer. Anish's uncommitted replay worktree stays untouched.

## PR #14 review corrections — 2026-11-18

Full checks now pass **947 tests with no skips**, 91% statement coverage, lint,
formatting, demos, synthetic ANM handshake and source/wheel builds. Both snapshot
tests ran against a local link to the retained pinned files. The roster still
matches 17/4/38/49 exactly. Thirty newly added corruption checks failed before
the fixes; the focused suite and valid native-export metric oracles now pass.
The retained 17-case scripted-pilot artifacts also validate under the stricter
scorer/diagnosis, and alternate-sample result substitution is rejected.

Consolidated merge route: review PR #14 directly against main. It includes the
pilot-readiness implementation from #10, the seeded mapping correction from #12,
the reviewed diagnosis correction from #13, and the evaluation roster. After #14
lands, maintainers should close overlapping #10/#12 as superseded or retarget any
remaining unique changes; do not merge an older implementation over these fixes.
No PR is automatically closed and main is unchanged by updating this branch.
