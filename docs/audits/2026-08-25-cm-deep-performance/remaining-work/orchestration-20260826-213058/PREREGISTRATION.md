# CM Remaining-Test Orchestration Preregistration

Registered: 2026-08-26T14:30:58Z

## Repository preservation

- Root: `C:\Users\brian\Documents\CM_Computation`
- Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`
- Accepted `cm_ir.py` SHA-256:
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`
- The pre-existing dirty worktree, website work, audit outputs, `.claude/`,
  `external/`, `tmp/`, and `The Broken Silence.*` are preserved.
- No `.env*`, credentials, tokens, or private configuration may be read.
- No commit, push, dependency installation, Runpod pod, or external write is
  authorized by this campaign.

## Purpose

1. Re-run focused and full local correctness checks after the consolidated
   trace changes.
2. Exercise the accepted one-in-16 trace policy across single-expression,
   expression-family, and partial-context benchmark boundaries.
3. Validate every trace and produce deterministic logical summaries.
4. Inspect entry gates for cache, family, context, selector, Numba/CUDD, and
   SIMD work without upgrading synthetic mechanics into workload evidence.

## Timing and evidence rules

- The trace smoke is synthetic mechanics evidence only.
- It cannot establish cache hit rates, family-edit locality, context-stream
  locality, selector traffic, or native-kernel economics.
- Exact output correctness must remain true for all benchmark rows.
- New paths must refuse overwrite.
- Run failures, skips, and unavailable optional dependencies are retained.
- Hardware timing from this smoke is descriptive and is not a unit-test
  assertion or production claim.

## Preregistered local checks

- Focused trace/integration pytest set matching the accepted campaign.
- Complete repository pytest suite.
- Three small CLI trace runs using deterministic seed `20260826`, sampling
  every 16 workload calls, and no optional native/BDD dependency.
- Validator and replay-summary tools applied to each emitted trace.

## Stop rules

- Stop on any correctness mismatch or full-suite regression and diagnose
  before running performance-related work.
- Do not launch a fourth RP-D0 attempt.
- Do not run cache/family/context policy experiments without an ordered real
  workload trace.
- Do not run another selector fit without a new independently frozen family
  and demonstrated `k=13..15` traffic.
- Do not run Numba, CUDD, or SIMD studies without their workload gates and new
  dependency/cloud authorization.

