# Fixed adequacy-policy replay

Exploratory opened cases, unchanged original preferences. No refits, permutation reruns, or deployed policy. IID checks are nominal; blocks are a saved-order heuristic. Nonrejection is not proof of independence. Warning-only is an annotation and deliberately has the same outcomes as original.

| Panel | Scheme | Policy | N | Correct | Wrong | Abstained | Execution failures | Coverage | Directional accuracy | Wrong removed | Correct lost | Added abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pilot17 | iid | original | 17 | 6 | 8 | 3 | 0 | 14/17 (82.4%) | 6/14 (42.9%) | 0 | 0 | 0 |
| pilot17 | iid | warning_only | 17 | 6 | 8 | 3 | 0 | 14/17 (82.4%) | 6/14 (42.9%) | 0 | 0 | 0 |
| pilot17 | iid | withhold_if_both_rejected | 17 | 6 | 6 | 5 | 0 | 12/17 (70.6%) | 6/12 (50.0%) | 2 | 0 | 2 |
| pilot17 | iid | withhold_if_selected_rejected | 17 | 6 | 6 | 5 | 0 | 12/17 (70.6%) | 6/12 (50.0%) | 2 | 0 | 2 |
| pilot17 | iid | require_unique_nonrejected | 17 | 4 | 5 | 8 | 0 | 9/17 (52.9%) | 4/9 (44.4%) | 3 | 2 | 5 |
| pilot17 | saved_order_blocks | original | 17 | 6 | 8 | 3 | 0 | 14/17 (82.4%) | 6/14 (42.9%) | 0 | 0 | 0 |
| pilot17 | saved_order_blocks | warning_only | 17 | 6 | 8 | 3 | 0 | 14/17 (82.4%) | 6/14 (42.9%) | 0 | 0 | 0 |
| pilot17 | saved_order_blocks | withhold_if_both_rejected | 17 | 5 | 7 | 5 | 0 | 12/17 (70.6%) | 5/12 (41.7%) | 1 | 1 | 2 |
| pilot17 | saved_order_blocks | withhold_if_selected_rejected | 17 | 5 | 7 | 5 | 0 | 12/17 (70.6%) | 5/12 (41.7%) | 1 | 1 | 2 |
| pilot17 | saved_order_blocks | require_unique_nonrejected | 17 | 2 | 5 | 10 | 0 | 7/17 (41.2%) | 2/7 (28.6%) | 3 | 4 | 7 |
| validation38 | iid | original | 38 | 13 | 13 | 12 | 0 | 26/38 (68.4%) | 13/26 (50.0%) | 0 | 0 | 0 |
| validation38 | iid | warning_only | 38 | 13 | 13 | 12 | 0 | 26/38 (68.4%) | 13/26 (50.0%) | 0 | 0 | 0 |
| validation38 | iid | withhold_if_both_rejected | 38 | 6 | 8 | 24 | 0 | 14/38 (36.8%) | 6/14 (42.9%) | 5 | 7 | 12 |
| validation38 | iid | withhold_if_selected_rejected | 38 | 6 | 8 | 24 | 0 | 14/38 (36.8%) | 6/14 (42.9%) | 5 | 7 | 12 |
| validation38 | iid | require_unique_nonrejected | 38 | 6 | 4 | 28 | 0 | 10/38 (26.3%) | 6/10 (60.0%) | 9 | 7 | 16 |
| validation38 | saved_order_blocks | original | 38 | 13 | 13 | 12 | 0 | 26/38 (68.4%) | 13/26 (50.0%) | 0 | 0 | 0 |
| validation38 | saved_order_blocks | warning_only | 38 | 13 | 13 | 12 | 0 | 26/38 (68.4%) | 13/26 (50.0%) | 0 | 0 | 0 |
| validation38 | saved_order_blocks | withhold_if_both_rejected | 38 | 10 | 9 | 19 | 0 | 19/38 (50.0%) | 10/19 (52.6%) | 4 | 3 | 7 |
| validation38 | saved_order_blocks | withhold_if_selected_rejected | 38 | 10 | 9 | 19 | 0 | 19/38 (50.0%) | 10/19 (52.6%) | 4 | 3 | 7 |
| validation38 | saved_order_blocks | require_unique_nonrejected | 38 | 9 | 1 | 28 | 0 | 10/38 (26.3%) | 9/10 (90.0%) | 12 | 4 | 16 |

All yields use all scheduled cases in that panel (17 or 38). Accuracy uses directional answers only. Original abstention and added policy withholding are separate in JSON. No answer is flipped; a rule can retain a direction or withhold it, so it cannot increase correct-answer yield.

Complete case-level transitions, source-group breakdowns and source-weighted descriptive metrics are in JSON. No policy is selected as a winner; new held-out evaluation is outside this replay.
