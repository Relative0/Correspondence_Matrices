# Next-Agent Handoff — Remaining-Work Campaign

Date: 2026-08-26

## Repository state

- Root: `C:\Users\brian\Documents\CM_Computation`
- Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`
- Worktree is intentionally dirty. Do not revert, stage, delete, or attribute
  unrelated website/audit-rerun work, `.claude/`, `external/`, `tmp/`, or
  `The Broken Silence.*`.
- Do not read `.env*`, credentials, tokens, or private configuration.
- Do not commit or push unless Brian explicitly asks.
- Retained `cm_ir.py` SHA-256:
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`.

## Completed here

- Implemented `cm-workload-trace/v1`, bounded/fail-contained JSONL tracing,
  strict metrics allow-list, validation, deterministic logical replay, and
  single/family/context benchmark-boundary integration.
- Tracing remains off by default. When enabled, default sampling is 1/16.
- Continuous capture was measured twice and rejected. Sampled capture median
  whole-call ratio was 1.0052 with zero exact mismatches, drops, or I/O errors.
- Passed 12 focused unit tests, 59 integration tests, and the final full suite:
  380 tests plus 4 subtests in 93.46 seconds.
- Ran guarded RP-D0 after exact approval. It failed closed because the
  `astutils>=0.0.5` dependency of `dd` has no binary wheel. The pod terminated,
  cost `$0.000765`, and the independent postflight reported zero pods.
- Ran separately authorized RP-D0 Run 2. It stopped before downloading or
  executing astutils because the offline wheel 0.48.0 installation lacked its
  `packaging>=24.0` wheel. This is a tooling defect. Run 2 terminated, cost
  `$0.000537`, cumulative cost is `$0.001302`, and postflight reported zero
  pods.
- Ran the explicitly authorized third-and-final RP-D0 Run 3. The corrected
  build-tool wheelhouse installed; the pinned astutils source was verified and
  built into a pure-Python wheel. Clean target resolution then failed because
  `dd==0.6.0` requires PLY 3.10 or earlier and PyPI provides PLY 3.10 only as a
  source distribution. Run 3 terminated, cost `$0.000646`, cumulative RP-D0
  cost is `$0.001948`, and its independent postflight reported zero pods.

## Pending approval boundary

All three pod authorizations have been consumed, and Brian identified Run 3 as
the final pod. Do not rerun or modify any failed output and do not create
another pod. Preserve all three audits.

The remaining standard-install blocker is PLY: `dd==0.6.0` constrains it to
`<=3.10`, while PLY 3.10 is source-only. Any future attempt requires a wholly
new authorization that explicitly covers the pinned PLY source build, or an
explicitly accepted `--no-deps`/dependency-metadata exception. Neither is
recommended until a named real workload establishes value for the native lane.

## Next evidence, not automatic implementation

1. Treat Run 1 as a binary-only dependency negative, Run 2 as a tooling
   negative, and Run 3 as the final standard-install feasibility negative under
   its source-build contract. No imports or exact smokes ran, so do not infer
   either success or failure for Numba/CUDD.
2. Identify a real workload owner and collect default sampled metrics to test
   whether cache/family/context/selector/native entry gates are populated.
3. For exact cache replay, preregister a short named workload and use a bounded
   explicit full trace. Do not treat sampled observations as a request stream.
4. Authorize only the downstream lane whose real opportunity clears its gate.

## Claims that must not be resurrected

- Do not optimize the statistically null CM/CSE-flat residual.
- Do not claim CM beats flattened sharing-aware CSE.
- Do not restore the old support-only word-engine rule; current retained k16
  dispatch remains authoritative.
- Do not treat BDD construction/restriction as exhaustive truth-table output.
- Do not treat quotient/structural operator artifacts as semantic XOR timing.
- Do not claim formal global CM canonical equivalence.
- Do not infer cache/family/context/native benefit from synthetic mechanics,
  dependency imports, or sampled traces.
