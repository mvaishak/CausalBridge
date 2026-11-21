# ANM mechanism follow-up: what changed and what we learned

## Main finding

**In this controlled synthetic study, an assumption violation can make the fixed
ANM produce many wrong directions even when its mean regression is accurate.**
Improving regression or supplying more evaluation observations does not necessarily
repair that mismatch. This is a project-specific demonstration of a known ANM
limitation, not a novel theorem or proof that a particular real pair is heteroscedastic.

The production ANM code and its gamma, ridge and directional threshold were unchanged.
The protocol, generated data, original requests, source hashes and schedule were
saved before execution. The 16-cell preflight passed; all 192 main cells completed
with zero execution failures. No LLM calls or real-data refits were performed.

## Design in simple terms

We generated data whose true cause is known, using a cubic function and a sine
function. For each of 24 base datasets, we created two paired noise conditions:

- **Independent additive noise:** random error does not depend on the cause.
- **Heteroscedastic noise:** random error has a different spread for different
  cause values. The mean function stays the same. The same exogenous draws are
  reused, and population expected noise variance stays equal across conditions.

The second condition violates the forward independent-additive-noise assumption.
It remains an independent-observation simulation: we did not add serial dependence
or confounding. Training and evaluation pools are separate. We vary training and
evaluation sizes independently, using nested samples. Column orientation alternates.

There are 24 independent base worlds (12 per fixed function), paired across noise
conditions, and 192 repeated factorial cells. These are not 192 independent datasets.
Preflight uses two additional base worlds and is excluded from the scientific table.

## 1. Comparable mean-regression error can accompany very different direction accuracy

At 256 training and 256 evaluation observations:

| Condition | Correct | Wrong | Abstain | Failure | Median mean-function error |
|---|---:|---:|---:|---:|---:|
| Independent additive | 24 | 0 | 0 | 0 | 0.00661 |
| Heteroscedastic | 2 | 17 | 5 | 0 | 0.00664 |

Each row retains all 24 base worlds. The error compares fitted predictions with
the known conditional mean in original effect units; it is not a causal score.
The similar medians do not imply every paired regression fit is identical.

Changing the noise regime increased wrong-answer yield by **17/24 = 70.8 percentage
points**, with an exploratory paired bootstrap interval of **54.2 to 87.5 points**.
The interval resamples complete base worlds within the two fixed families. It is
unadjusted for multiple comparisons and does not quantify uncertainty over new
function families or real datasets.

The controlled difference establishes a large noise-regime effect in this setup.
It does not establish that heteroscedasticity explains the original real-data errors.

## 2. Removing true-direction regression error does not fix this violation

We then used the known generating function to compute true-direction residuals.
This oracle control removes mean-function estimation error in that direction; the
opposite-direction regression remains learned.

At 256/256, the oracle-assisted diagnostic gave:

| Condition | Correct | Wrong | Abstain |
|---|---:|---:|---:|
| Independent additive | 24 | 0 | 0 |
| Heteroscedastic | 2 | 16 | 6 |

Thus, poor estimation of the true mean function is not a sufficient explanation
for the wrong arrows in this simulation. This does **not** remove every possible
reverse-regression error or give a performance upper bound. It uses privileged
truth and is not a deployable ANM improvement.

The known-mean residual dependence check rejected 1/24 independent-additive cases
and 24/24 heteroscedastic cases at evaluation size 256. At size 64, the corresponding
counts were 0/24 and 20/24. A finite test can miss a real violation; a false rejection
under independence is also possible. Nonrejection never proves independence.

## 3. More training data helped prediction, but mainly reduced wrong releases through abstention

With 256 evaluation observations in the heteroscedastic regime:

| Training observations | Correct | Wrong | Abstain | Median mean-function error |
|---|---:|---:|---:|---:|
| 64 | 1 | 23 | 0 | 0.01766 |
| 256 | 2 | 17 | 5 | 0.00664 |

Increasing training size reduced mean-function error and wrong yield, but only one
additional case became correct; five additional cases abstained. The paired wrong-
yield difference was −25.0 points, exploratory interval −41.7 to −8.3 points.
This is a coverage/error trade-off, not reliable recovery under the violation.

## 4. More evaluation data did not repair model mismatch

With 64 training observations and the same fitted functions:

| Evaluation observations | Correct | Wrong | Abstain |
|---|---:|---:|---:|
| 64 | 6 | 17 | 1 |
| 256 | 1 | 23 | 0 |

The wrong-yield increase was +25.0 points, exploratory interval +8.3 to +41.7.
Evaluation size changes dependence-estimation behavior, kernel bandwidth estimates
and the interaction with the fixed .001 threshold. It is not just an abstract
increase in statistical confidence. These observations do not support a general
claim that more data is harmful; they show that more evaluation data did not fix
this misspecified diagnostic in the tested conditions.

## 5. Regression approximation still matters under valid additive noise

At training/evaluation size 64/256 under independent additive noise, the learned
true-direction residual dependence test rejected 9/24 cases. With the known mean,
it rejected only 1/24. At 256/256, those counts were 6/24 and 1/24.

The generator has independent additive noise, so learned residual dependence can
reflect finite-training approximation rather than a violated generating assumption.
In the 256/256 cell, all 24 directions were correct despite six learned-forward
rejections. This cautions against treating a residual test as a perfect assumption
certificate. We did not promote a new rejection gate or tune its alpha.

## What this adds to the earlier saved-data audit

The earlier audit showed associations: split sensitivity, persistent wrong arrows,
and a sample-size/source-family confound. This experiment changes factors directly
and provides a controlled example where assumption mismatch is a major determinant
of direction outcomes, while isolating true-direction fit error with an oracle.

It supports a more precise explanation of our project's negative result boundary:
**numerically consistent ANM evidence can still be unreliable outside its assumptions;
better regression or more data alone need not make its direction correct.**
It does not prove a root cause for soil pairs 91/92, engine pair 108 or the pilot's
eight wrong arrows. Source-level and real-data adequacy investigations would remain
exploratory, and any revised method needs a fresh evaluation cohort.

## Reproduction and limits

The [protocol](../experiments/anm-mechanism-study-v1.md) and
[archived results](../../artifacts/anm-mechanism-study-20261121/README.md) contain
commands, original requests/results, diagnostic vectors and the exact frozen source.
An isolated replay from the archive reproduced all three analysis files byte-for-byte
without regression refits. All saved permutation calculations were recomputed.

There are only two mechanisms, one noise amplitude and one violation strength.
Per-case independence checks use 99 permutations with plus-one p-values and alpha .05.
Bootstrap intervals are exploratory and unadjusted. The regime comparison is paired;
repeated sizes and noise conditions do not increase the number of independent base
worlds. Family-level outcomes and all cells, including any contradictory findings,
are retained in the generated report and JSON.

Independent additive noise is a condition of established ANM identification results;
see [Peters et al. (2014)](https://jmlr.org/papers/v15/peters14a.html).
These simulations illustrate that boundary for this implementation; they do not
refute ANM as a method family or establish a new real-world accuracy improvement.
