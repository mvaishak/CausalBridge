# Data

Visible runtime cases belong in `pilot/`, `dev/` and `test/`. These folders are empty
until the benchmark is generated and validated. The fixtures in `examples/` are
for development; they aren't a verified pilot benchmark.

Store cases as JSONL using `RuntimeCase` from `src/causalbridge/schemas.py`.
Include `case_id`, `graph_group_id`, explicit graph nodes and edges, question text,
visible probabilities and assumption flags. See [the integration guide](../docs/integration.md)
for the full format.

Complete models, reference answers and witness models belong in `oracle/`, which
is ignored except for its README. Export visible cases explicitly. Never pass
oracle records to a runtime model or tool. Join labels by case ID after execution.

Keep evidence pairs, paraphrases and isomorphic graph copies together. The proposed
split is 10 pilot, 18 development and 72 test graph groups, subject to pilot feasibility.
Freeze prompts, verifier rules and tolerances before generating the held-out test set.
