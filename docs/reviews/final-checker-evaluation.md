# Final evidence checker evaluation

The deterministic checker validates typed claims and evidence bindings. The 17-pair pilot supplies 68 cached S1 checks, one per pair and E1–E4 package. It makes no new LLM call and cannot determine whether an observational arrow is causally true.

| Process outcome, among answered upstream proposals | Benchmark-correct | Benchmark-wrong |
| --- | ---: | ---: |
| Accepted and released | 6 | 9 |
| Rejected and suppressed | 2 | 3 |

The remaining 48 S1 proposals abstained upstream and supplied zero typed claims. They passed their applicable checks but were not released. Thus the table evaluates 20 answered proposals, not all 68 checks. Five rejections arose outside E4: three E1 proposals cited unavailable rows, summaries and method evidence; two E3 proposals cited displayed row values that did not match. Multiple reason codes can describe one rejected output. The independent saved audit confirms all five. Two benchmark-correct proposals were sacrificed to suppress three benchmark-wrong ones. E4 had zero suppressions: 14 releases, 6 reference-correct and 8 wrong. The simple gate also made no E4 change.

In the observed natural pilot, the checker caught unavailable evidence and numeric row mismatches. The regression suite also exercises invalid identities, citation bindings, method attribution, continuous numeric tolerance and release consistency through injected corruptions. Those tests establish rule behavior under constructed inputs; they do not estimate natural error prevalence. The audit found two strict text/structured-direction mismatches in the 68 S1 outputs, illustrating that free-text semantics remain outside the typed checker. Empty claims are permitted, so `pass` means the submitted typed claims did not violate implemented rules, not that a complete explanation was verified.

The checker improved process validity for the five suppressed citations but did not improve the E4 directional score. The accepted set still includes nine benchmark-wrong answered proposals across E3/E4. Source rows: `artifacts/final-delivery/track-b-diagnostics/checker-audit.json`; aggregate audit: `checker-summary.json`; original prompts and raw responses: the archived pilot ZIP.

## Post-merge 38-pair integrated panel

The later exploratory panel supplies 152 cached S1→S2 checks. There were 42 answered S1 proposals, 109 upstream abstentions that passed without a direction, and one malformed package-digest proposal that could not be checked as a valid parent. Among answered proposals:

| Process outcome | Benchmark-correct | Benchmark-wrong |
| --- | ---: | ---: |
| Accepted and released | 12 | 16 |
| Rejected and suppressed | 7 | 7 |

Ten E1 suppressions caught citations to unavailable evidence; one E3 citation gave the wrong displayed-row values; three E4 citations failed numeric checks. The E4 rejections were **all benchmark-correct directions**: two summary mismatches and one adjacent-row citation. One summary mismatch was a four-decimal rounding of the supplied standard deviation, rejected under the checker's strict 1e−12 tolerance. The other summary value and the row index were materially wrong. E4/S1 released 13 correct and 13 wrong at 73.4% weighted coverage; S2 released 10 correct and 13 wrong at 65.3% coverage. Thus the checker enforced typed evidence exactness but did not improve and, in this panel, reduced E4 directional accuracy and correct yield. The simple gate still did not alter E4 releases.

The raw resumed journal and case-level analysis are in `artifacts/final-delivery/postmerge-track-b/`. The 38 reference labels had been opened in the numerical ANM study, so these checker rates are exploratory. A `pass` still cannot certify unrestricted prose or the causal direction.
