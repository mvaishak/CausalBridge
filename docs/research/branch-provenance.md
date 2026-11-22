# Branch and evidence provenance

The fetched `origin/main` base is `fb81b96a92c8cc78360276e54bd3d9be0a974e56`. The complete [branch inventory](../reviews/branch-lineage-and-provenance-audit.md) was made before integration. Its claim that v3 had no live study is corrected by the [local artifact reconciliation](../reviews/branch-lineage-provenance-reconciliation.md). The [integration manifest](../reviews/scientific-integration-manifest.md) gives file-level choices.

| Research | Original branch and tip | Relationship to main and other work |
| --- | --- | --- |
| Submitted Track A/B, ANM and final deliverables | `main` `fb81b96`; final delivery `d266004`; postmerge Track B `d773118` | Already incorporated. Frozen report/slides and archives retained. |
| Thinking ablation | `codex/qwen3-thinking-ablation-20261121` `ecd1b3054bb290830f9a9dfa0b1b6763fe2030d1` | Descends from main; uses archived 17-pair pilot inputs. |
| Diagnostic v1/v2/v3 | `codex/diagnostic-investigation-v3-20261121` `7d4a408cc8fcb0b1238971c04141c0fd579a5a20` | Git descendants of thinking, then v1 `b8b5b44`, Anish v2 `4f600b4`, v3. V3 consumes original pilot and thinking archives. The 170-call live archive was external to Git before consolidation. |
| Alternate prompt-only v2 | `71ff36ae0dfc528b831b8206afb8103bb11bf01a` | Branches after v1. Design/plan retained, alternate runtime/config excluded because it conflicts with the implemented single-decision contract. |
| ANM failure studies | `codex/anm-failure-diagnosis-20261121` `d3be02c76d7e20fa5395301e5e9c2922baa25133` | Independently branches from main; analyzes saved pilot/validation ANM results and synthetic worlds. It is a scientific explanation/follow-up, not a Git or runtime prerequisite of the earlier v3 live experiment. |
| Synthetic cue study | `experiment/counterfactual-anm-cue-v1-20261121` `368d6486261452ff7e5fee85f75e1a113e48509b` | Independently branches from main; frozen preparation only. PR #21 remains historically separate. |
| Historical pilot review | `codex/pilot-output-review-tools` `1d59c848637c09b32bbcdf97acf30b2446421467` | Additive review tooling retained. Other older branches are incorporated ancestors or carry conflicting old scorer/relocation patches excluded from runtime. |

Git ancestry does not establish which saved outputs a study consumed. Input dependencies are pinned by frozen plans and source manifests. Scientific follow-up does not imply inherited code or a comparable outcome definition. No historical branch was changed or deleted.

## Team contributions

The [historical roadmap](../knowledge/roadmap-status.md) records Arunima's graph and witness work, Anish's numerical engine and ANM, Faizah's data audit/roster and scoring, Kris's evidence packages and runner, and Vaishak's predictor/checker integration. Joint ownership is explicit there. Later commits add Vaishak's thinking/v3 studies, Anish's ANM failure investigations and v2 diagnostic contract, and Arunima's prepared synthetic cue study. These are contribution records, not claims that every branch descends from another teammate's research branch.
