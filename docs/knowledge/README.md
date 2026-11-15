# CausalBridge knowledge bank

**Start with [current-status.md](current-status.md)** for the latest GitHub merge,
live-smoke evidence, uncommitted work and next actions. Phase records below retain
historical validation snapshots and must not be read as current status.

Start here when resuming work. This is an evidence-linked progress record, not a
claim that roadmap assignments have been completed. Update it alongside each
implementation milestone; fetch remote progress before marking teammates' work.

## Research and system context

Two tracks: Track A checks support for causal effects with a supplied DAG and exact
population evidence. Track B studies direction predictions from names, observations
and an optional ANM diagnostic. They share transport where useful, but have separate
schemas and correctness claims. A process-check pass does not verify a causal arrow.

Planning sources:
- [Shared planning folder](https://drive.google.com/drive/folders/1vx2vCUmMF_OcG24JXdpUQDmIBlh72ShG)
- [Collaboration questions](https://docs.google.com/document/d/1uTciRJR_YQT-UvEk8qh7B7cDMQttPMidOhNkzDm8Hq8/edit)
- [Kris implementation plan](../kris-track-b-plan.md), especially “Base version v1”.
- [Kris defined answers](../kris-collaboration-answers.md).

Status vocabulary: **planned** = specified only; **implemented** = code exists;
**tested** = named checks pass; **integrated** = actual consumer/producer exercised;
**evaluated** = real experiment with scored outcomes. Local unmerged work is marked
explicitly. Do not infer a teammate's status from assigned responsibility.

## Overall project inventory

Last fetched remote main: `1dd84b4`, including PR #7
([Track A pilot](../track_a_pilot.md)) and PR #8 smoke/checker fixes.
Integration-readiness work is committed in open [PR #9](https://github.com/mvaishak/CausalBridge/pull/9)
at `bcad4a3`: **818 tests passed**, with green Python 3.12/3.13 CI.
See current-status.md for the current acceptance gates; PR #8 fixes are merged.

| Workstream | Owner | Evidence-backed status | Evidence / next dependency |
| --- | --- | --- | --- |
| Known-DAG parsing, pipeline, contracts | Vaishak | Tested on audited main | Original Track A suite retained; see current verification record below |
| Exact graph/numeric backend | Anish | Production engine merged and tested | `tools/inference.py`, `tools/engine.py`; reference adapter retained separately |
| Benchmark generation / exact witnesses | Arunima + Anish | Ten-group synthetic pilot implemented and checked; live run pending | `benchmark/generator.py`, `witness.py`, `pilot.py`; 50 runtime cases in `data/pilot/track_a_10_groups.jsonl`, exact witness joint and rational/engine confirmation tests |
| Tübingen ingestion and split audit | Faizah | Planned / handoff pending | No real-data loader in audited main |
| ANM | Anish | Merged and exercised through our native runner | Real KRR/HSIC and durable pre-execution requests; synthetic observations only |
| Track B predictor / process checker | Vaishak | Implemented/tested merged | `llm/predictor.py`, `verifier/checks.py`, `verifier/bindings.py`; native runner integration tested |
| Evidence, prompts and execution | Kris | Phases 1–3 tested; native component integration tested, real-data/scorer handoff pending | See phase tracker below |
| Scoring / intervals | Faizah | Planned / handoff pending | No scorer in audited main |
| Live model / pilot / held-out | Team | Two live Qwen3 8B smokes on synthetic observations; real-data pilot/held-out not complete | PR #8 fixes merged; saved checker-0.3 replays verified; no real-pair performance claims |

## Original roadmap: plan versus actual work

These numbers are the original roadmap phases. The recent readiness phases
1–7 have a separate tracker in [current status](current-status.md).

| Phase | Current status | Actual deliverables | Remaining exit work |
| --- | --- | --- | --- |
| 0 Scope/design | Defined | Scope, architecture, research contrasts, phases and audit procedure; simplified shared questions | Maintain decisions as external handoffs arrive |
| 1 Contracts/evidence | Merged/tested; native adapter exercised | `discovery/contracts.py`, `evidence.py`, `prompts.py`, `example.py`; tests and contract example | Real loader/scorer boundary remains pending |
| 2 Runner/persistence | Merged/tested; live synthetic smoke exercised | `evaluation/runner.py`, `store.py`, `demo.py`, tests and `docs/kris-phase2.md` | Failed-generation metadata follow-up merged in PR #8 |
| 3 Independent artifact audit | Merged/tested; corruption review fix included | `evaluation/audit.py`, frozen `audit_policy.py`, 31 cases and `phase3-audit.json` | Real adapter and live research audit remain later gates |
| 4 Integration | Partially complete: available components integrated/tested | `integration.py`, native audit, baseline/export projection and demo | Real loader and Faizah scorer-consumer acceptance still pending |
| 5 Pilot/freeze | Infrastructure smoke started; real-data pilot not complete | Eight live Qwen3 calls on one synthetic case; see current-status.md | Two infrastructure smokes and replay complete; audited real groups and protocol freeze remain |
| 6 Held-out/handoff | Planned | None | Frozen runs, independent audit and scoring reconciliation |

## Recent readiness handoffs

- [Current status and next actions](current-status.md)
- [Saved live-smoke replay](../kris-phase2-replay.md)
- [Loader/export boundaries](../kris-phase3-handoff.md)
- [A/B orientation and evaluator joins](../kris-phase4-evaluator-joins.md)
- [Scorer acceptance fixtures](../kris-phase5-scoring-fixtures.md)
- [Offline pipeline acceptance](../kris-phase6-offline-acceptance.md)

The detailed implementation sections below preserve historical milestone evidence.

## Phase 1 behavior and files

- [Contracts](../../src/causalbridge/discovery/contracts.py): no evaluator fields;
  strict finite rows; separate direction proposal; method consistency; attempt and
  process release shapes. These are our v1 boundary, adaptable to teammates.
- [Evidence](../../src/causalbridge/discovery/evidence.py): independent seeded
  orientation/method/display selection, local row IDs, population summaries,
  signed-zero-normalized canonical hashes, method binding, matched packages.
- [Prompts](../../src/causalbridge/discovery/prompts.py): exact common task plus
  S1-only caution paragraph, identical output schema, only public payload serialized.
- [Contract generator](../../src/causalbridge/discovery/example.py) and
  [generated example](../../examples/track_b_contract.json): four-row illustration,
  four packages, eight prompts, answer/abstention/failure and illustrative release.
  Not a valid ANM study: the method and release are explicitly scripted.
- [Tests](../../tests/test_discovery_phase1.py): hand calculations, sampling,
  mapping, visibility, invalid inputs, hashes, method errors and proposal records.

Reproduce from repo root:

```bash
uv sync --frozen --dev
uv run python -m causalbridge.discovery.example --output examples/track_b_contract.json
bash scripts/check.sh
```

This host intermittently loses editable-package import resolution across command
calls. Verified fallback sets `PYTHONPATH=src` and uses
`UV_CACHE_DIR=/tmp/causalbridge-uv-cache` for both commands. No production source
change was made for that environment issue.

## Decisions and limitations

| Decision | Reason / consequence |
| --- | --- |
| Separate Track B package | Track A direction is effect sign; Track B direction is A/B orientation |
| One seeded orientation across packages | Avoid introducing a label-oriented order bias |
| Up to 64 display / 256 method rows | Roadmap default, pilot-dependent; E4 adds information as well as a diagnostic |
| Canonical hash convention v1 | Ordered A/B float rows and normalized signed zero; cross-language agreement needs golden vectors |
| Names supplied as reviewed input | Structural validators cannot detect direction clues or secrets embedded in approved free text |
| Error card retained in E4 | Failed/ambiguous method cases must not disappear from evaluation |
| `causal_proof` representable in proposal | Allows production checker to detect explicit overclaims rather than hiding them as parser failures |
| No citation correctness claim yet | Registry validates availability; faithful attribution and release require Vaishak's checker |
| No automatic template repair | Malformed predictions remain observable failures |

External questions live in the shared document. Blocking points for integration:
Faizah's source-to-runtime mapping and export consumer; Anish's exact sample/hash
API; Vaishak's prediction/checker signatures and output fields. None blocks mocked
Phase 2 progress.

## Maintenance checklist

After each phase: update status and exact commands/results; link artifacts; record
changed assumptions; list remaining dependencies; distinguish local branch from
merged main. After an external handoff: record the revision and actual adapter
fixture run before changing “planned” to “integrated”. Keep research observations,
scripted fixtures and mathematical examples separately labeled.

## Historical Phase 1 verification record

12 November 2026, local branch `codex/kris-track-b-plan`, Python 3.12.13:

- `PYTHONPATH=src UV_CACHE_DIR=/tmp/causalbridge-uv-cache bash scripts/check.sh`: PASS.
- 90 tests passed: 67 pre-existing plus 23 Phase 1 cases; overall coverage 90%.
- Ruff lint and formatting passed; original eight-case demo retained its expected
  four verified / three unsupported / one wrong-operation results.
- Source archive and wheel built successfully.
- Contract example generated with `python -m causalbridge.discovery.example`.
- No model calls, real ANM calculation or production checker execution occurred.
- Standalone independent artifact auditing remains Phase 3, not claimed complete.

Phase 1 was subsequently committed locally at `e8e0f90`, then remote main merged
at `1163edf`. Our work has not been pushed or merged to remote main. This record
describes local work, not remote main. Test counts are descriptive; acceptance depends on
invariants exercised and the documented limits, not counts or coverage alone.

## Historical Phase 2 update — 14 November 2026

Reviewed remote main `48d6cda`: Arunima's small synthetic benchmark and exact witness
joint export, plus Vaishak's Track B schemas/predictor/checker and integration smoke,
are merged. Repository code is authoritative where the collaboration document's
older examples differ (e.g. directional_scores is not a current prediction field).
Anish's real ANM/independent numerical confirmation and Faizah's real loader/scorer
have not been observed here; this is not a claim they have done no work elsewhere.

Our Phase 2 implementation and reproducible demo are documented in
[kris-phase2.md](../kris-phase2.md). The runner stores all raw/parsed/failure outcomes,
process-locked journal events, manifests, per-invocation usage, retry lineage,
S2 parent links and cache identities. Fixture replay is complete; real Vaishak
adapter and ANM-request provenance remain Phase 4. Phase 3 independent artifact
auditing is next. No live experiment has been run.

### Phase 2 verification

- Full combined `PYTHONPATH=src UV_CACHE_DIR=/tmp/causalbridge-uv-cache bash scripts/check.sh`: 303 tests pass, lint/format pass, unchanged eight-case Track A demo, wheel/sdist build pass.
- 13 Phase 2 runner/storage test cases pass; 23 Phase 1 cases remain passing alongside the merged upstream suite.
- Final reproduction directory: `runs/kris-phase2-final` (ignored runtime artifacts).
  Manifest `8b4d098795aef586b37d9b1c1d23da249d1987784a089a1cb23a1496ecfe826b`:
  first invocation 24 calls / 12 S1 replay records; second invocation 0 new calls / 24 reused trials.
- Saved usage unknown for demo fixtures; counting tests use explicitly synthetic token values.
- Shared document now contains implemented answers beneath Kris's three original
  questions. Connector readback confirmed all three answers and unchanged other text.
- Phase 2 source/docs are committed locally with this update. No push/remote PR or
  real model/ANM/scoring run was performed. Phase 3 independent audit remains pending.

## Historical Phase 3 completion

[Phase 3 specification and evidence](../kris-phase3.md) records the separate
artifact reader and adversarial tests. [Default-scope audit report](phase3-audit.json)
records zero findings for the three-case fixture bundle: 24 trials, 12 S2 records,
86 journal events. Input artifacts, frozen policy and auditor source are hashed.
All 334 combined tests, lint/format, Track A demo and package builds pass.

Audit-discovered instrumentation gaps were closed: Runner v1.1 links each new
call to its invocation and persists new trial keys; the demo stores a private
label-free source/selection sidecar before prediction. Legacy bundles missing
these receipts are not retroactively treated as fully auditable.

Phase 3 independence is a separate implementation/read path, not an independent
human reviewer. It uses hand expectations, malformed/corrupted artifacts and
positive/negative mechanism controls. No causal accuracy or ANM computation is
claimed. Scripted, merged-production and live-scientific statuses remain distinct.

Current next phase: Phase 4 adapters and boundary tests. Outstanding owned work
also includes simple-gate/method-only baseline integration and final scoring-export
consumer agreement. Anish/Faizah handoffs and real model runs remain pending.

## Historical Phase 4 progress — available components integrated

See [Phase 4 handoff](../kris-phase4.md) and [native audit](phase4-audit.json).
Merged Anish PR #5 at main `b1718e7`; our local merge is `d990af8`.
Real ANM computation, durable original requests, Vaishak's actual predictor and
checker now run through the native integration path. Synthetic data/scripted model
transport remain clearly labeled. The older fixture runner is unchanged in meaning.

Verification: 495 combined tests pass, plus lint/format, reference and engine demos,
real synthetic ANM handshake and package builds. 18 native integration cases cover
failure/binding/control paths and signed-zero persistence. Three-case native demo:
24 initial generations, 12 S2 checks, 0 new calls on resume, 51 analysis rows;
recorded native audit has zero findings and input-file hashes.

Implemented simple-gate and ANM-only baseline projections; exporter retains all
scheduled failures and provides opaque A/B mapping IDs. Separate private evaluator
mapping enables correct post-run reference orientation, without labels in runtime.
Full original/typed claims and raw model replies are preserved; no lossy proposal
conversion claims compatibility between different schema versions.

**Phase 4 remains open** for Faizah's real loader, audited snapshot/source-group
manifest, approved labels/units and scorer-consumer fixture. Latest collaboration
read still has no Faizah answers. No real-world benchmark, live LLM call, threshold
tuning or pilot freeze has occurred. Do not advance the knowledge-bank status to
real-data integrated or evaluated based on this synthetic handshake.

## Historical PR publication snapshot

[Roadmap status](roadmap-status.md) maps each original work package to implemented
capabilities and remaining research, including the open Phase 4 data/scorer gate.
The completed work is submitted as [draft PR #6](https://github.com/mvaishak/CausalBridge/pull/6); no merge is assumed.

### PR publication

Draft [PR #6](https://github.com/mvaishak/CausalBridge/pull/6) targets team `main`
from `KrisDcosta:codex/kris-track-b-plan`. Direct push to the team repository was
rejected because the authenticated account has pull-only access. A fork under
KrisDcosta was created/verified and the branch pushed there. Team origin remains
unchanged. GitHub readback confirms OPEN, draft and mergeable; CI was not yet
reported at creation. Local 495-test validation remains distinct from GitHub CI.

## Historical PR #6 review correction

The review of `e1c68b1` correctly found that the native auditor permitted a non-null
S2 direction on failed-parent and checker-error records when `check` was null.
The runner generated these records correctly; detection of corrupted saved records
and downstream export validation were incomplete.

Reproduced before the fix with four red cases: generation, parsing, binding and
checker errors. Each case starts from a passing clean run, injects a direction,
rebuilds the journal hash chain and updates the S2 export. The auditor now requires
null direction on both no-check branches; `analysis_rows` rejects contradictory
S2 states rather than exporting a false answer. Clean failure/control records remain
valid. The runner and production checker/release policy are unchanged.

Validation after correction: 499 tests pass, lint/format, both Track A demos,
real synthetic ANM handshake and package builds pass. Fresh native demo under
`runs/kris-pr6-review-fix`: 24 initial calls, 12 S1 checks, zero new calls on resume;
updated native audit report passes with zero findings. PR #6 is updated with this
fix; merge is not assumed. Our earlier 495-test pass did not cover these corruptions.

## Historical PR #6 merge and first-smoke snapshot

Superseded for current status by PR #8 and open PR #9; retained as a dated evidence trail.

PR #6 is merged at `1638d67`, with 499-test validation and both GitHub CI jobs
passing on its final head. A first live Qwen3 8B smoke completed on synthetic
observations: 8 calls, 3 S2 rejections/1 release, audit pass, and zero extra model
calls for S2/resume. Two S0 generations exhausted the output budget. Native failed-
generation metadata needs correction; original wire responses remain available.

Uncommitted compact-protocol/metadata/provenance changes and two local launchers
exist. Their presence is recorded without declaring them tested or merged. No
completed v2 report was found. See [current status](current-status.md) for exact
artifact paths, model identity, limitations and ordered next steps. This update
does not touch or commit the in-progress source changes.
