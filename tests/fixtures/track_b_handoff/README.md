# External handoff fixture

`loader.json` is synthetic: two runtime pairs and separate evaluator records.
It exercises the local provisional adapter target, not Faizah's finalized API.
Its three-row samples are deliberately too small for a valid ANM study.

Only each runtime record may be passed to RuntimePair, selection and evidence
construction. Evaluator cause_column refers to original column order, before
A/B randomization. Family sentinel strings must never reach predictor messages
or ANM requests. See docs/kris-phase3-handoff.md for acceptance boundaries.
