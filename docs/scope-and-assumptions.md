# Scope and assumptions

Vaishak owns the parser, planner, verifier and integration interface. The roadmap's
engineering ownership table is the working split; the proposal defines the causal
scope. Suggestions addressed to another team member inside the roadmap aren't
instructions to reassign Vaishak to benchmark generation.

## What the verifier establishes

It checks that the parsed query binds to known variables, the request preserves
those roles, the selected operation can answer that quantity, the visible evidence
satisfies its preconditions, and the proposed answer agrees with the tool result.

Reachability supports structural answers. An absent directed path supports zero
total intervention effect under the supplied causal assumptions. A present path
alone supports neither a sign nor a magnitude.

Intervention values come from supplied CPTs, or from an observational joint with a
graph-valid backdoor adjustment set. The empty set supports observational
substitution only when it passes the same criterion.

The backdoor check removes outgoing treatment edges, excludes treatment
descendants, then checks d-separation. It implements a sufficient backdoor rule;
it doesn't search all possible identifying formulas.

## Scientific assumptions

The supplied DAG is correct and fully observed. Variables are binary, exogenous
noise is independent, and positivity holds. Runtime cases explicitly assert these
assumptions before numerical causal claims are permitted.

Evidence contains exact population probabilities. Sampling error, estimation,
misspecified graphs and latent confounding are outside this implementation.
The benchmark producer must validate its models, witnesses, DAG compatibility and
evidence consistency independently.

## Conservative choices

The initial exact-CPT contract requires all graph-node tables. Some quantities
could be computed from fewer tables. Extend the evidence contract and tests with
Anish if the benchmark needs that case; don't treat a conservative abstention as
mathematical non-identification.

The default numeric tolerance is 0.001, following the proposal's provisional
choice. Sign has a separate 1e-9 zero threshold so rounding doesn't erase a small
effect. Record and freeze both settings using development data before testing.

## Trust boundaries

The default natural-language parser is an LLM. Comparing its parsed query with its
later plan catches changed roles, but can't independently prove that the parser
understood the original question. Audit parsed queries and report optional public
query-spec experiments separately. Unsupported tasks abstain if the parser exposes
their unsupported type; a silent semantic misparse remains possible.

The numerical backend is trusted to compute correctly from visible evidence.
Contracts check types, permitted ranges, bindings and answer consistency; they
don't independently recompute arbitrary numerical outputs. Cheap structural facts
are checked against the supplied graph. Request/evidence digests detect stale or
misbound results; they aren't cryptographic attestations of computation.

The runtime schema excludes oracle fields, and projection drops extra benchmark
metadata. This boundary can't detect hidden CPTs that a caller deliberately labels
as visible, or secrets embedded in free text. Use separate oracle storage and
review the dataset export. Prompt injection is outside the proposal's scope.

## Research work still belongs to the team

Generate and independently validate the 10-group pilot before scaling. Add the
18 development groups and 72 held-out groups only after feasibility checks and
protocol decisions. Preserve graph groups and paired evidence across splits.

Use the same model and comparable budgets across A–E. Measure D versus C and the
simple evidence gate; report false abstentions alongside unsupported answers.
The fixture demo provides no evidence of research improvement or non-inferiority.

No model weights were downloaded during setup, and live Qwen reliability remains
unmeasured. The locked environment and model settings support a reproducible smoke
run; deterministic generation settings don't guarantee identical hardware outputs.
