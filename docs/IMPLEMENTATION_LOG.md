# Implementation record

Plan: `docs/superpowers/plans/2026-10-27-vaishak-implementation.md`.

- User authorized assumptions and end-to-end execution; use ordinary project practices
  while RTK.md and PROCESS.md are absent (confirmed in chat).
- Empty Git repository has no baseline code or commits. Work in the supplied
  checkout on `codex/vaishak-verifier`; a second worktree needs an initial commit
  and adds no useful isolation here. Preserve both original PDFs.
- No local Ollama executable or server detected. Exercise the live adapter with
  HTTP transport tests; do not describe scripted outputs as model results.
- Preflight: schemas feed tools/contracts; request and result carry the same query,
  operation and evidence digest. Pipeline uses those exact interfaces.
- Task 1: complete. Visible-only schemas, projection, causal assumptions and
  validation; initial 15 schema tests passed after missing-module RED.
- Task 2: complete. General capability/evidence/conclusion contracts, replaceable
  backend protocol and development reference calculations; 42 tests passed.
- Task 3: complete. Strict JSON lifecycle, Ollama transport, CLI, 8 fixture cases,
  exported schemas, lockfile, CI and integration documentation; 60 tests passed.
- Serena's active project has no language servers. Its editing calls failed with
  that explicit error; continued using normal file editing tools.
- Independent read-only review found 2 Important issues: malformed benchmark root
  types crashed ingestion, and Pydantic error strings exposed rejected nested
  values. Six regression tests failed first, then passed after explicit root-type
  validation and `hide_input_in_errors=True` at the shared model boundary.
- Final integration check found operation mismatch was classified after missing
  evidence in the pipeline. A regression test failed first; shared
  `check_operation` now runs before evidence requirements. Full suite: 67 passed.
- Build configuration excludes the supplied source PDFs from package archives;
  the originals remain untouched in the project folder.
- Review scope decisions: live model behavior requires the user's chosen runtime;
  benchmark results require the team's generated data; natural-language parsing
  and numerical backend correctness remain explicit trust boundaries. These match
  the design. No research-results claim is made. No deferred minor findings.
- Local completion keeps the feature branch and supplied checkout for the user.
  No remote repository is configured, so nothing is pushed or published.
- Final checks: locked sync, lockfile consistency, Ruff lint and formatting,
  67 tests, 8 demo cases, JSON schema export, source/wheel build and an isolated
  wheel-install smoke run passed. See `docs/verification.md` for evidence and limits.
