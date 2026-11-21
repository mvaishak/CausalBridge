# Saved-evidence diagnosis

Automated joins of preserved raw final outputs. Human explanation coding remains unfilled in manual-review.csv.

| Run | Style | Think | Wrong copied | Correct resistance | Protective abstention | Wrong-ANM failures | Harmful switches | Correct-tool acceptance |
|---|---|---|---|---|---|---|---|---|
| original_4096_512 | S0 | False | 8/8 | 0/8 | 0/8 | 0/8 | 4/4 | 6/6 |
| original_4096_512 | S1 | False | 8/8 | 0/8 | 0/8 | 0/8 | undefined (0/0) | 6/6 |
| matched_8192_4096 | S0 | True | 8/8 | 0/8 | 0/8 | 0/8 | 2/2 | 6/6 |
| matched_8192_4096 | S1 | False | 7/8 | 0/8 | 0/8 | 1/8 | undefined (0/0) | 6/6 |
| matched_8192_4096 | S0 | False | 8/8 | 0/8 | 0/8 | 0/8 | undefined (0/0) | 6/6 |
| matched_8192_4096 | S1 | True | 8/8 | 0/8 | 0/8 | 0/8 | 2/2 | 6/6 |

Abstention, execution failure and checker rejection are different. These transition metrics describe upstream predictions. Historical budgets differ; the new controlled-cue protocol changes the prompt/schema and is not a historical accuracy replication.

The ablation's empty typed claims motivate a required diagnostic-attribution field in the new isolated schema. Attribution consistency still cannot certify causal truth.
