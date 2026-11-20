# Post-merge Track B evidence archive

This directory separates model evidence from software checks and interrupted attempts.

| Artifact | Evidence type | Interpretation |
| --- | --- | --- |
| `pilot-request-comparison.json` | Deterministic current-pipeline replay against archived live trial starts | All 136 original model-visible requests and method bindings matched |
| `dataset-inventory.json` | Deterministic roster audit | 17 pilot, four development, 38 validation, 49 unscorable; no pilot/validation group overlap |
| `integrated-38-scripted.tar.gz` | First scripted software check | Historical fixture run before formatter changes; no live model calls |
| `integrated-38-scripted-formatted.tar.gz` | Current scripted software check | 304 fixture calls, all 38 bindings and scores; no live model calls |
| `integrated-live-smoke.tar.gz` | One-pair live integration check | Eight actual `qwen3:8b` responses |
| `integrated-38-interrupted-live.tar.gz` | Interrupted full-panel attempt | 51 actual responses and 253 transport failures; **not** a scorable 38-pair result |
| `integrated-38-resumed-live.tar.gz` | Completed real-model panel | 304 bound model responses: 51 saved-live replays, 253 newly generated; three transport retries recorded separately |
| `integrated-38-provenance-audit.json` | Independent deterministic verification | All 304 request/response origins bind exactly; no reference labels in prompts |
| `integrated-38-analysis/` | Scored exploratory analysis | Case-level metrics, grouped intervals and publication-ready SVG figure |
| `model-identity-after-run.json` | Post-run endpoint query | Same pinned Qwen3 model digest after the transport retries |

The 38 labels were previously opened for numerical ANM validation, so the completed panel remains exploratory. The interrupted attempt's transport failures are not abstentions and are excluded from the completed-panel scores.
