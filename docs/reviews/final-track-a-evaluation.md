# Final Track A live evaluation

The established ten-group synthetic pilot was regenerated without changing its visible cases or oracle. The frozen visible input has 50 questions: 29 answerable and 21 unanswerable. A one-case smoke at the configured local Ollama endpoint saved real raw responses. The full run then used the same `qwen3:8b` installation at `http://127.0.0.1:11435`, model digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`, temperature 0, seed 261, thinking off, 8192 context tokens, 1024 output tokens, and the production numerical engine. This is the actual model reported by `/api/tags`, not an assumed default.

The raw 50-trace JSONL is preserved as `artifacts/final-delivery/track-a-live/traces.jsonl.gz` with SHA-256 `f7637886005c2c3f56d7b60c8f3e6d4c856262434cdbec7474b38f6f60545813`. The separate oracle, endpoint model metadata and console log are beside it. Each trace contains the visible case, exact model messages and output schema, raw Ollama responses, model name, stage outcomes, tool records, verdict, latency, token usage and generation settings. The oracle was joined only after inference. The original uncompressed run is ignored at `runs/final-track-a-live-20261119.jsonl`; the tracked archive is the portable evidence.

## Predefined task outcomes

| Gold and outcome | Cases |
| --- | ---: |
| Correct answer on answerable case | 1 |
| Wrong released answer | 1 |
| False abstention on answerable case | 27 |
| Correct abstention on unanswerable case | 21 |

Coverage is **2/50 = 4.0%**. Answered accuracy is **1/2 = 50%**, which is not informative at this coverage. Correct-answer yield is **1/50 = 2.0%**; overall correct answer-or-abstain decisions are **22/50 = 44%**. All 21 unanswerable cases were abstained on, while 27/29 answerable cases were missed. The case-level scorer uses the hidden oracle's intended answer, not merely the pipeline's `verified` status; numeric answers are compared at the frozen 0.001 tolerance. There were 102 actual model stages, 35,069 input tokens and 6,432 output tokens. Summed trace latency was 567.8 seconds. No request was replayed or mocked in this run.

The verifier status counts were 39 `unsupported`, 6 `wrong_operation`, 3 `execution_error` and 2 `verified`. The three execution errors are structured-output errors at the planning stage for `G001_path`, `G003_path` and `G005_path`; the full run still saved all 50 cases. The CLI returned exit code 1 because of failed case statuses, while its console confirms 50 saved traces. The exact cases and counts are in `artifacts/final-delivery/analysis/track-a-case-results.json` and `metrics.json`.

## Failure mechanism

Only 9/50 model-parsed query types match the oracle's intended query type. In `G006_sign_complete`, the question asks whether changing X from 0 to 1 **increases** Y. The model parsed it as `intervention_probability`, requested `compute_intervention`, and returned `0.3124944283345406`. The verifier marked that numeric answer `verified` for the parsed intervention-probability query. The oracle answer to the asked direction question is `negative`. This is a verified binding to the model's changed query, not a correct answer to the original question. The one correct released answer was `G006_path`, a directed-path question.

The run was frozen before inspecting these answers. Changing the prompt or adding a post-outcome semantic rule now would be test-set tuning; any repaired pipeline needs a new independently generated graph-group evaluation. The present result supports a narrow finding: structural tools can check the operation they receive, but they do not by themselves ensure that the model has mapped the natural-language question to the right operation. The exact witness and deterministic generator tests remain valid, independently of the live model failure.

The 50 cases share ten graphs, so case-level Bernoulli intervals would overstate independent information. An exploratory ten-group percentile bootstrap (10,000 resamples, seed 261) gives coverage 0–12% and correct-answer yield 0–6%. An answered-accuracy interval is omitted because both answers are in one graph group. These intervals describe this constructed set only.
