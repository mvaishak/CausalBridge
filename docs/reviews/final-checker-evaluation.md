# Final evidence checker evaluation

The deterministic checker validates typed claims and evidence bindings. The 17-pair pilot supplies 68 cached S1 checks, one per pair and E1–E4 package. It makes no new LLM call and cannot determine whether an observational arrow is causally true.

| Process outcome, among answered upstream proposals | Benchmark-correct | Benchmark-wrong |
| --- | ---: | ---: |
| Accepted and released | 6 | 9 |
| Rejected and suppressed | 2 | 3 |

The remaining 48 S1 proposals abstained upstream and supplied zero typed claims. They passed their applicable checks but were not released. Thus the table evaluates 20 answered proposals, not all 68 checks. Five rejections arose outside E4: three E1 proposals cited unavailable rows, summaries and method evidence; two E3 proposals cited displayed row values that did not match. Multiple reason codes can describe one rejected output. The independent saved audit confirms all five. Two benchmark-correct proposals were sacrificed to suppress three benchmark-wrong ones. E4 had zero suppressions: 14 releases, 6 reference-correct and 8 wrong. The simple gate also made no E4 change.

In the observed natural pilot, the checker caught unavailable evidence and numeric row mismatches. The regression suite also exercises invalid identities, citation bindings, method attribution, continuous numeric tolerance and release consistency through injected corruptions. Those tests establish rule behavior under constructed inputs; they do not estimate natural error prevalence. The audit found two strict text/structured-direction mismatches in the 68 S1 outputs, illustrating that free-text semantics remain outside the typed checker. Empty claims are permitted, so `pass` means the submitted typed claims did not violate implemented rules, not that a complete explanation was verified.

The checker improved process validity for the five suppressed citations but did not improve the E4 directional score. The accepted set still includes nine benchmark-wrong answered proposals across E3/E4. Source rows: `artifacts/final-delivery/track-b-diagnostics/checker-audit.json`; aggregate audit: `checker-summary.json`; original prompts and raw responses: the archived pilot ZIP.
