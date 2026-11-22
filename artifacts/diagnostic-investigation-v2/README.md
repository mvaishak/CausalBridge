# Diagnostic investigation v2: offline validation

This bundle validates software behavior only. **No live v2 preflight or research inference was run.** See the v2 experiment guide and runner handoff in the shared docs directories.

- `validation.json`: exact validation scope and remaining live checks.
- `software-validation.log`: 1,082 passed tests and two existing optional-snapshot skips.
- `scripted-smoke.log`: all 20 preflight and 170 full scripted cells completed, with no model calls.
- `scripted-smoke.tar.gz` / `smoke-manifest.json`: complete scripted plans, raw fixtures, records, analysis and every member's size/SHA-256. These scripted replies are not LLM findings.
- `schema-parity-fixtures.json`: exact v2 generated schema and eight valid/invalid objects; all matched expected application and independent Draft 2020-12 JSON Schema acceptance. This external validation used the available local jsonschema installation and adds no runtime dependency.
- `other-checks.log`: demos, synthetic ANM handshake and source/wheel package build.
- `lint-format.log`: Ruff checks.
- `source-manifest.json`: inventory of this working-tree correction and audit documentation; excludes itself.

The smoke's `source_commit` is the pre-existing HEAD, b8b5b44, while source hashes bind the modified local code. These are uncommitted software-validation artifacts. Freeze new live plans after the correction is committed/published; record that actual revision. Do not use the old v1 or scripted preflight to authorize the live v2 full experiment.

Preserved v1 failure archive inspection lives in `artifacts/diagnostic-preflight-failure-audit/validation.json` and `docs/reviews/diagnostic-preflight-failure-audit.md`. Its historical failures remain failures. The correction removes redundant generated fields; it does not guarantee accurate directions or semantic agreement of unrestricted explanations.
