# ANM-only development and frozen validation

Latest follow-up: [synthetic panel and transfer check](anm_synthetic_panel.md)
reports a successful predeclared synthetic demonstration at 512 rows: 26 correct,
zero wrong, six abstentions among 32 fresh compatible confirmation datasets.
The larger real-development check has one correct primary pair but fails to
repeat across splits. Earlier results below remain unchanged historical evidence.

Implemented locally on `codex/anish-anm-baseline-reproduction`, with reviewed
PR #14 (`a29dc4b`) as an explicit dependency. The earlier replay changes are
preserved. The user has authorized committing this feature branch; this does not
change PR #14 or merge anything into main. No remote push or new PR is requested.

## Four chunks and their outputs

1. **Handoff connection:** `discovery/study.py` verifies Faizah's pinned manifest
   and roster, then loads only the cases assigned to the requested role. Numerical
   APIs receive numeric A/B samples and opaque IDs; references/groups/weights stay
   in separate evaluator inputs. The same deterministic case and column mapping
   conventions as the existing loader/selection are used. Neutral names identify
   numeric variables; this is not an E1–E4 LLM experiment.
2. **Development baseline:** pair IDs 12, 17, 93 and 99 only. Baseline settings
   match the current producer: 128 selected rows, half training/evaluation split,
   RBF gamma 1, ridge alpha 0.1, threshold 0.001. Configuration identities are new
   study identities; original pilot files are not reused or rewritten.
3. **Controlled comparisons:** `configs/anm-development.json` fixes six variants
   and split seeds 261/1261/2261 before fitting. Each variant changes one setting
   from baseline: 256 rows, alpha 0.01/1, or gamma 0.25/4. Threshold and sampling
   seed remain fixed. This is not a Cartesian grid search. Existing sampling is
   deterministic but different sample sizes are not guaranteed nested subsets.
4. **Candidate freeze and validation:** explicit owner-supplied criteria and a
   named evaluated candidate are required. Digests bind the development inputs,
   original attempts, results, summary, full package source and dependencies.
   Validation runs only the frozen variant on its assigned cases. A start marker
   prevents automatically repeating the same freeze after outcomes are opened.
   Protocol rules also forbid creating new freezes to tune on validation outcomes;
   content hashes are consistency checks, not authenticated external preregistration.

Primary metrics use split 261. Other split outcomes and raw-margin sign stability
are reported separately. Repeated splits are dependent observations, not additional
independent cases. Four pairs in three source groups are too few for a broad
reliability claim or an unrestricted parameter search.

## Run development independently

First prepare/verify the pinned snapshot using [evaluation_handoff.md](evaluation_handoff.md).
Then use a fresh output directory:

```bash
uv run --extra anm python -m causalbridge.discovery.study development \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --roster configs/evaluation-roster.json \
  --plan configs/anm-development.json \
  --output runs/anm-development-new
```

This makes 72 real-data ANM attempts: four development pairs × six variants ×
three splits. It also computes 24 baseline-only control attempts from four fresh
synthetic datasets (cubic, sine, linear Gaussian, heteroscedastic), two column
orientations and three splits. Orientations/splits reuse samples. Only cubic/sine
controls have compatible-direction correctness; the other controls have null
accuracy rather than being counted as wrong unique-direction answers.

All fits use local CPU, with no LLM/server/API calls. Extra diagnostic regression
recalculations report held-out standardized prediction MSE for each direction;
they do not alter production results or certify causal direction. HSIC scores,
margins, actual selected counts and decisions are retained separately. The
existing scorer computes weighted ANM-only metrics without fabricated S0/S1/S2
records. This study does not use the LLM-journal diagnosis interface.

Saved outputs: `inputs.json` before fitting, exclusive original attempts under
`attempts/`, `evaluations.json`, `summary.json`, `controls.json`, and a digest-bound
completion record. Existing output directories are refused. No silent retries or
automatic removal of failed cases. Matching raw data hashes does not certify
causal assumptions or correctness of benchmark references.

## Executed development results — 2026-11-18

Authoritative final-source run: `runs/anish-anm-development-03/`. All 72 real-data
attempts have status `ok`; all 24 controls compute. No real validation or pilot
pair was fitted. The eligible weight is 3 in every real-data metric cell.

| Configuration | Primary weighted coverage | Primary selective accuracy | Primary wrong yield | Raw-sign stability across three splits |
| --- | ---: | ---: | ---: | ---: |
| Baseline, n=128 | 100% | 0% | 100% | 75% |
| n=256 | 66.7% | 0% | 66.7% | 75% |
| alpha=0.01 | 66.7% | 0% | 66.7% | 25% |
| alpha=1 | 66.7% | 0% | 66.7% | 100% |
| gamma=0.25 | 66.7% | 0% | 66.7% | 75% |
| gamma=4 | 66.7% | 0% | 66.7% | 50% |

All primary correct yields are zero. Reduced wrong yield comes from abstaining,
not from producing correct primary answers. Stable wrong answers are not an
improvement. Secondary split 2261 has 25% answered accuracy for alpha=0.01 and
20% for gamma=4; the other secondary cells have zero. These are small dependent
development observations, not evidence to select a reliable method.

The cubic and sine controls produce 12 correct answered outcomes across two
independent generated datasets. Linear Gaussian and heteroscedastic controls
each produce six answers, with correctness deliberately undefined. This is a
sanity/assumption diagnostic, not reproduction of the missing 48-dataset study.

Post-outcome diagnostics independently decoded predictions back to original-file
cause columns for all four baseline pairs. Four additional baseline swap fits
exchanged scores and negated margins within 1e-12; they do not reverse the
reported historical predictions. Results: `runs/anish-anm-orientation-01/report.json`.
Preliminary runs 01/02 used the same numerical plan before final source-attestation
annotations were finished. The final 72 numerical result records match run 01
exactly. These repetitions do not increase the independent dataset count.

## Freeze and validation commands

No real candidate has been selected or frozen because this comparison does not
support progression. No real acceptance targets are invented. Supply a JSON
criteria file only after deciding meaningful standards; required fields are:

| Field | Meaning |
| --- | --- |
| decision_owner, rationale | Who specified the criteria and why |
| min_coverage | Minimum released weight / eligible weight |
| min_selective_accuracy | Minimum correct / answered weight; undefined accuracy fails |
| max_wrong_yield | Maximum wrong / eligible weight |
| min_sign_stability | Minimum fraction of cases with the same nonzero raw sign across splits |

Rate fields must be numeric values in [0,1]. No defaults are supplied. Targets
are engineering decisions, not substitutes for uncertainty estimates or proof.
Freeze rejects candidates missing from the completed study or failing its
development criteria. Source/dependency changes require a fresh development run.

```bash
uv run --extra anm python -m causalbridge.discovery.study freeze \
  --development-run runs/anish-anm-development-03 \
  --variant CANDIDATE_NAME --criteria /path/to/explicit-criteria.json \
  --output runs/anm-freeze-new
uv run --extra anm python -m causalbridge.discovery.study validation \
  --snapshot runs/pilot-preparation/raw --frozen runs/anm-freeze-new \
  --output runs/anm-validation-new
```

Validation fits only the chosen configuration on the 38 assigned cases, retains
all cases in denominators, and emits a criterion-by-criterion decision. It does
not run the other development candidates or synthetic controls. Its gate/path
has been tested on synthetic fixture partitions, not the real validation panel.

## Next work

Inspect assumptions and dependence/regression diagnostics for these four pairs.
Do not reverse arrows or widen the parameter search until the metrics improve.
Develop a separately specified method investigation with fresh synthetic cases
to separate regression approximation, independence estimation and split/sample
effects. Obtain the original synthetic validation bundle if exact reproduction
of its reported failure is required. Leave the 38 validation pairs unused until
a defensible candidate and evaluation criteria are frozen. Integrate with the
LLM runner only after numerical validation supports the intended claim.

## Executed targeted diagnosis — 2026-11-18

The follow-up used only cached baseline requests from development run 03 and its
baseline controls. `configs/anm-adequacy.json` fixed 199 permutations, seed 180731
and alpha 0.05 before the new adequacy outcomes were inspected. This is an
explicitly post-outcome exploratory study, not a preregistered reliability test.

`examples/anm_adequacy.py` reconstructs both held-out regressions and requires its
HSIC calculations to match the original scores. For each direction, it compares
the observed centered-kernel statistic with 199 residual permutations, using the
plus-one p-value `(1 + exceedances) / 200`. The exploratory rule answers only
when exactly one direction is not rejected; otherwise it abstains. Nonrejection
does not establish independence, identification or causation. Real observation
exchangeability is not verified, so the p-values are not certified for these data.

```bash
uv run --extra anm python examples/anm_adequacy.py \
  --development-run runs/anish-anm-development-03 \
  --plan configs/anm-adequacy.json \
  --output runs/anm-adequacy-new
```

There are 12 real baseline split outcomes and 24 control outcomes: 72 directional
tests and 14,328 permutation statistics. Regression diagnostics are recalculated
locally; original numerical requests/results are not overwritten. The original
study's complete file hashes are checked before/after. Final artifact:
`runs/anish-anm-adequacy-02/report.json`; run 01 and the final source have identical
reports after an error-handling correction. No validation cases are used.

Primary results:

| Development pair | Reference-direction MSE / opposite MSE | Adequacy outcome | Conclusion |
| --- | --- | --- | --- |
| 12 | 0.909 / 1.351 | Only the wrong direction is not rejected | Better reference-direction MSE does not ensure better HSIC ranking |
| 17 | 3.064 / 1.152 | Only the wrong direction is not rejected | Fit/dependence asymmetry persists; no correct recovery |
| 93 | 0.509 / 0.315 | Both directions rejected | No adequate directional model established by this check |
| 99 | 0.610 / 1.091 | Neither direction rejected | The test does not distinguish directions; nonrejection is not identification |

Weighted coverage is 33.3%, correct yield 0%, wrong yield 33.3%, answered accuracy
0%. Split 1261 has 50% coverage and 0% answered accuracy; split 2261 has 33.3%
coverage and 0% accuracy. The rule reduces answers but does not recover correct
real-development directions. It is not promoted to production or registered as a
freezable candidate. It is not an S2 release and is not stored as an ANMResult.

Controls: cubic retains six correct outcomes; sine retains three correct outcomes
and abstains on three. Linear Gaussian still receives two directional answers;
heteroscedastic receives five. Both control classes keep undefined accuracy. The
gate therefore does not certify the method's assumptions or eliminate over-release.

The pinned development descriptions also limit interpretation. Census pairs
12/17 omit upstream population survey instance weights; benchmark pair weights
are not those missing row weights. Pair 93 averages precipitation/runoff over
catchments with acknowledged confounders. Pair 99 contains pupils in clustered
classes/schools and notes possible selection bias. The sample has repeated values
(pair 99's largest mapped-column tie occupies 19.5% of its 128 observations).
Numeric eligibility and a benchmark reference do not certify independent additive
noise. These observations do not prove a single explanation or justify changing
references/exclusions after inspecting outcomes.

The justified next decision is to review the intended claim and design fresh,
known-truth development experiments that separately vary assumption violations,
regression approximation and dependence estimation. Do not reverse real arrows,
retune alpha on these four pairs, or spend the validation set to seek a positive
result. Neither the parameter comparison nor this adequacy gate supplies a
defensible candidate for the current reliable-evidence claim.
