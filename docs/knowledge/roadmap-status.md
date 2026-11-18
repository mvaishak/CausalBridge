# Roadmap status: pilot scope

Snapshot: main `1dd84b4` (PRs #1–#8), plus local `codex/pilot-readiness` changes.
Current user scope is preparation through the pilot, not held-out evaluation or
the final report. [Pilot commands and limitations](../pilot_run.md) are current;
older phase notes retain their historical validation counts.

**Live pilot update, 14 November 2026:** `runs/real-pilot-01/` completed 136 live
generations and 68 S2 checks over 17 pairs/seven source groups. No execution or ANM
errors; audit passed; resume made zero new calls. E4 S1/S2/ANM-only have identical
arrows, 89.0% weighted coverage and 40.0% weighted selective accuracy. The
before/during-pilot entries below describe the preparation checklist; the first
run is now complete. No held-out run or final report has been produced.

| Package | Current evidence | Before/during pilot |
| --- | --- | --- |
| G1/G2/G3 and N1 | Graph tools, independent exact witnesses, production numerical engine; 50 cases over ten groups | Live Track A execution if included in this pilot |
| N2 | Real KRR/HSIC with durable original requests; all 17 selected real pairs compute successfully offline | Inspect diagnostic behavior; 0.001 threshold is exploratory, not calibrated |
| D1 | Frozen official snapshot; 17 selected pairs in seven source groups; strict loader, hashes, exclusions, separate evaluator records | Review cohort caveats while interpreting pilot; reserved pairs are not eligibility-audited |
| D2 | Matched E1–E4; runner now rejects changed context/source before calls; independent audit checks matching | Inspect actual live prompt lengths and failures |
| V1/V2 | Native predictor/checker and compact prompts; earlier live synthetic smoke documented | Live real-data calls; inspect typed-claim and empty-claim outcomes |
| R1 | Durable S0/S1, cached zero-call S2, resume, model pin and bounded pilot entry point | Run 136 live generations; inspect raw outputs and usage |
| Baselines/scoring | ANM-only and simple-gate exports; weighted pilot coverage/yields/accuracy with complete denominators | Explicit post-run label join; inspect failures and incorrect/correct releases removed |
| Intervals/held-out/report | Deferred by user | No pilot significance claims or final report |

The official data are prepared locally under ignored `runs/pilot-preparation/`.
All 108 metadata entries are accounted for: 17 included and 91 explicitly
reserved/excluded from this pilot. All related source-family entries remain in
the pilot partition even when only a subset is selected. No development/test
allocation or held-out eligibility is asserted.

The full-cohort offline check uses real observations and real ANM, but scripted
model replies. Its 136 fixture calls and 68 S2 checks establish integration only.
The subsequent live real-data pilot is recorded in the update above and pilot guide.

## Deferred work

- Development-calibrated ANM threshold and final held-out protocol freeze.
- Source-group paired bootstrap intervals and inferential comparisons.
- Auditing eligibility of reserved data and choosing development/test splits.
- Full research error analysis, publication figures, report and presentation.
- Optional robustness work or a new minimum-citation checker policy.

The current checker validates supplied typed claims and bindings; it permits
empty claims and qualified disagreement with ANM. A process pass does not prove
causal correctness or completeness of evidence support.
