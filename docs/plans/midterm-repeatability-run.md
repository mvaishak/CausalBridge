# Midterm repeatability run plan

Prepared 19 November 2026. Planning only: no smoke generation or full rerun has
started. The saved-results package is already complete. PR #12 was closed with
user authorization at 2026-11-19T20:37:30Z after confirming its fix is superseded
in main. It was not merged and its branch was not deleted.

## Scientific purpose

Present a bounded study of how evidence and checking affect model outputs,
including the negative ANM/direction findings. The new run tests repeatability
of the opened 17-pair pilot under a pinned configuration. It is not a fresh
holdout, a method-improvement study or completion of the deferred human-annotation
endpoint. Keep original and repeated results side by side; never choose the more
favorable run as the only reported result.

The independent recorded-result review confirms Anish's 13 correct/13 wrong/12
abstention validation count. Numerical correctness and useful real-data recovery
remain different questions. No extra parameter grid, new discovery algorithm or
outcome-driven exclusions are part of this midterm plan.

## Sequence and acceptance gates

| Step | Concrete output | Proceed when |
| --- | --- | --- |
| 1. Freeze the candidate | Versioned execution manifest with code/model/input/prompt/method hashes and declared budget | Every required identity is explicit; no unknown field is presented as frozen |
| 2. Verify service | API version, installed model metadata and exact artifact digest | Endpoint is callable and the digest matches the manifest; no silent model substitution |
| 3. One-pair smoke | D1006, matched E1–E4, eight S0/S1 calls, four cached S2 outcomes, audit and zero-call resume | Complete raw traces, valid parsing/binding, correct schedule, stable sample identities and passing audit; no extra S2/resume generation or ANM calls |
| 4. Full repetition | Same 17 cases, 136 primary calls, 68 cached S2 outcomes, fresh output directory | Smoke passes operational gates; all scheduled attempts remain in accounting |
| 5. Compare and report | Original-versus-repeat tables, resources, failures, case disagreements and midterm figures | Both runs retained, baselines explicit, unknown costs left unknown, limitations stated |

Accuracy is not an admission criterion for the smoke test. Correctly recorded
abstentions and checker rejections are legitimate scientific outcomes. This
particular smoke case's ANM should execute successfully and round-trip its
original request/result. Failures in generation, schema parsing, binding, artifact
audit or schedule accounting stop scaling. Preserve those failed traces. Do not
automatically retry them until a predeclared fix/new attempt policy is recorded.

## Proposed fixed configuration

Keep the original pilot settings to isolate repeatability:

| Item | Candidate value |
| --- | --- |
| Inference revision | Current audited main: 7c7198d29f4f2e224963a2e24be778db1d81e4d7; recheck before final freeze |
| Analysis code | Pin reviewed results code separately; record source hashes and worktree state |
| Cohort | All original 17 pairs / 7 groups; same exclusions and benchmark weights |
| Model | qwen3:8b, original Q4_K_M artifact |
| Artifact digest | 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41 |
| Generation | temperature 0, seed 261, think=false, context 4096, max output 512, timeout 300 s |
| Prompt protocol | integrated-track-b-v2-compact; exact S0/S1 messages and output schema hashes retained |
| Method/display sample limits | At most 128 method rows / 16 displayed rows, matching the original selection |
| Seeds | mapping 261, method sampling 262, display 263, ANM split 261 |
| ANM | Original KRR/HSIC configuration: gamma 1, ridge alpha 0.1, half training/evaluation split, threshold 0.001 |
| Checker | direction-checker-0.3; same numeric tolerance and citation/binding rules |
| Replicates/retries | One replicate; no automatic retries; original deterministic condition order retained |

Do not substitute the newer 512-row ANM validation configuration into this
128-row pilot repetition and call it unchanged. Current main's anm.py has the
same SHA-256 as the original session record:
c755bdc8617b9486a9cfadb856390687dbeef5040afab48b73b9617bc500899b.
Other inference/prompt source files and runtime versions must still be compared
and pinned. Current source identity does not prove server/runtime identity.

The endpoint is a pending field. The original localhost:11435 endpoint did not
respond from this environment. Confirm whether inference runs here or on the
teammate's machine, then record the actual URL and runtime/API version. Changing
the transport endpoint must be logged even if model and generation settings stay
the same. Do not silently fall back to another model or download an alternative.

## Smoke choice and budget

D1006 is the lexicographically smallest eligible opaque case ID. It was chosen
by that deterministic rule, not by correctness. Its outputs are already opened;
the smoke is an operational test and is not scored as a new independent dataset.

Prepare a separate one-case runtime-only input and keep its evaluator record
private. The smoke and full run use separate manifests/output roots. Do not copy
cache receipts across manifests to pretend the smoke is already part of the
full run. Preserve any independent original attempts.

Maximum planned fresh budget:

- Smoke: 8 model calls, 1 ANM case evaluation, 4 cached S2 checks.
- Full repetition: 136 model calls, 17 ANM case evaluations, 68 cached S2 checks.
- Total: **144 model calls, 18 ANM case evaluations, 72 cached S2 checks**.
- S2 and resume add zero model calls and reuse existing method results.

At the original model-call speed, this is roughly 27 minutes of summed generation
time, plus preparation, method execution and other overhead. It is not a wall-time
guarantee. Local dollar cost and original checker/ANM wall time were unmeasured.
Log fresh generation and method/checker timings where the existing runner records
them; do not invent unavailable historical observations.

If no code/configuration has changed and time/service access is tight, the
audited original pilot is already a valid midterm result. A full repetition is
not necessary merely to label a file final. Report that choice explicitly rather
than fabricate a fresh test or launch an unbounded run.

## Midterm result package

Use the existing exact tables and figures, adding the repetition as another run:

1. E1–E4 × S0/S1/S2, plus SIMPLE_GATE and ANM-only: coverage, correct/wrong yield,
   answered accuracy and raw counts with fixed denominators.
2. Original-versus-repeat arrow, abstention and checker-decision agreement, with
   every disagreement linked to exact attempts. Repeated pairs are not independent
   causal examples and must not be used to inflate the sample size.
3. Measured tokens, latency, failures and actual retries; do not double count
   cached parents or resume exports. Keep no-answer accuracy undefined.
4. Representative natural citation failures and the separate 14-control/56-
   perturbation mechanism table. Do not equate artificial detection with natural
   error prevalence or independent human validation.
5. Clear negative findings: E4 followed ANM and checking did not improve its
   arrows; the original five rejections removed three wrong and two correct
   answers. The repeat may differ; preserve and explain rather than select.

Human annotation remains deferred until after the midterm if feasible. Track A's
live benchmark is a separate bounded experiment if time permits; do not silently
add it to the 144-call Track B budget.

## Immediate actions

First finalize the inference host/endpoint and review the candidate manifest.
Then seal exact code, configuration and input identities and run the one-pair
smoke. No performance threshold needs to be met to report the negative study.
No new generation is authorized or executed merely by saving this plan.
