# Windows pytest profile plan

Status: implementation and local validation complete. No benchmark execution, dependency installation, historical evidence rewrite, commit or push occurred.

## Objective

Create a maintained Windows test entry point that produces an actionable active-suite result while preserving explicit custody of optional dependency/platform refusals and immutable historical replay failures.

## Evidence boundaries

- Bind historical replay selectors to `docs/audits/2026-09-14-cm-benchmark-attribution/TEST_COMPARISON.json` and require its LF-canonical SHA-256 so the pre-`.gitattributes` file is stable across LF and CRLF checkouts.
- Bind optional and platform readiness to `docs/audits/2026-09-15-cm-overnight-local-portfolio/TEST_RESULTS.json` and require its exact SHA-256.
- Preserve both evidence files byte for byte. Do not turn expected historical failures into passing tests or install optional dependencies.
- Leave pytest unchanged unless the explicit `--cm-profile=windows-supported` option is selected.
- Fail closed on missing selectors, missing modules, changed hashes, category overlap or an unexpected supported-suite outcome.

## Validation

Run profile unit tests, inventory verification, collection, the complete supported Windows profile, existing focused CI tests affected by the workflow edit, Python compilation, evidence hash checks and Git diff review. Record every result in a successor report without changing either source audit.
