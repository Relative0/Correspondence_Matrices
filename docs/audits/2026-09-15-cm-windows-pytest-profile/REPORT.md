# Maintained Windows pytest profile audit

Date: 2026-09-15  
Base: `main` at `e334de594262059cc18cf37eaab56b0f79e94843`  
Disposition: validated locally; no scientific disposition changed

## Result

The opt-in `windows-supported` profile gives this repository a maintained Windows development gate. Its final collection contained 1,834 active supported tests, deselected the exact 76 historical replay tests from the September 14 comparison, and refused nine whole modules whose optional dependency or platform status was established by the September 15 overnight audit.

The complete supported run passed with 1,826 passed tests, eight in-suite skips, 76 deselections, zero failures, zero errors, and 1,157 passed subtests. Pytest emitted four pre-existing `dd` BDD destructor warnings. The final run took 3,492.45 seconds; two passing tests accounted for 3,035.567 seconds, so the timing is not a benchmark result and supplies no new performance evidence.

## Configuration audit and implementation

The base commit had no root `pytest.ini`, `pyproject.toml` pytest configuration, tox profile, or nox profile. `.github/workflows/research-checks.yml` ran a fixed, focused cross-platform test list with Python 3.13, a minimal pinned dependency file, and a 15-minute job timeout. It did not define a repository-wide supported profile.

The new root `pytest.ini` only registers the two classification markers. Root `conftest.py` loads `cmbench.pytest_profiles`; ordinary pytest behavior remains unchanged unless `--cm-profile=windows-supported` is selected. With that option, the plugin:

- refuses use outside Windows;
- validates both source-audit bindings before collection;
- ignores the nine optional/refusal modules before import;
- deselects only the exact historical test IDs after collection, preserving supported neighbors in mixed modules;
- fails closed on evidence drift, missing modules, missing historical selectors, count drift, or category overlap; and
- prints all three category counts in the terminal summary.

`scripts/cm_windows_pytest_profile.py` provides read-only `verify` and `show` commands. `docs/testing/WINDOWS_PYTEST_PROFILE.md` documents routine use and the successor-audit procedure. The focused CI workflow now runs the four profile contract tests and the inventory verifier on both configured operating systems; it does not run the complete profile under the existing 15-minute/minimal-dependency job.

## Evidence custody

The September 14 comparison predates exact-byte `.gitattributes` coverage and is checked out as CRLF on this machine. Its LF-canonical SHA-256 is `7d9a08e7c72daf650bc62126b89d6d1c8f342887ac806be57f508a8309ec77db`; its local raw SHA-256 remained `ca2c338725d5f0edf29ae9a231abbd12f915da9b184847b9a23a5261c6b08d35`. The September 15 test results retained raw SHA-256 `5913b7ae8538f4abbeae6468441e2aa26be40ad4668f1a81885c604cb1d0e9df`.

The September 14 audit verifier passed 85 manifest entries, 40 claim artifacts, and 47 statistical sources. The September 15 verifier passed all 19 sealed files. Neither predecessor audit was rewritten. The historical failures remain ordinary unprofiled pytest tests and retain their prior scientific meaning.

## Focused CI check

The profile's four contract tests passed, inventory verification passed, Python compilation passed, and full fail-closed collection passed. The existing focused CI list was also exercised locally. Its first exact invocation encountered 25 setup errors because this managed host denies pytest's default `%TEMP%/pytest-of-brian` directory. Repeating it with a workspace temp root removed every setup error: 247 tests passed, one skipped, and the pre-existing generated-chart currentness test failed.

That remaining test hashes six input files as raw bytes. This Windows worktree has CRLF conversions and produces source identity `sha256:c98b0da2d4cf8bd274538ab3fe7898ccf2b1c2d13f84b99aab4799f3ce66b237`; the committed generated file is bound to the LF identity `sha256:a2a188412606f319b395d845fdccf7564d9b90679dcf1f86a2e6a03e388e4abd`. The existing workflow sets `core.autocrlf=false` before checkout, so its CI checkout uses the latter bytes. No chart source, deliverable, or test was changed to mask this separate checkout issue.

## Boundaries

No benchmark campaign, cloud job, dependency installation, evidence rewrite, scientific promotion, commit, or push occurred. The work remains uncommitted for review as requested.
