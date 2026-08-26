# CM Three-Lane Continuation Results

Date: 2026-08-27  
Campaign: `three-lane-20260827-011536`

## Executive result

All three authorized local lanes are complete.

1. A strict, versioned real-workload manifest and validator now make the
   missing external input actionable without inventing a workload. The
   repository still contains no real application/caller trace, so cache,
   family, context, incremental, and selector promotion remain evidence-gated.
2. DP-R2 found that the current dense temporary-memory estimate is not
   conservative. No default was changed. A decision memo recommends estimator
   hardening before Brian considers a versioned 16 MiB benchmark/remote and
   64 MiB direct-API temporary admission profile.
3. DP-R3 consolidated exactly one repeated mechanism: deterministic streaming
   file SHA-256. Compatibility imports, exact-source snapshots, trace
   provenance, and the memo Runpod archive were updated and validated.

No CM preparation, kernel, selector, output ordering, exactness, cache key,
trace schema, output-budget default, cloud resource, dependency, commit, or
push was changed or used.

## Repository preservation

- Branch / HEAD stayed `main` /
  `0f833bc389778f7f915deb7acd4499d207e0ec21`.
- Accepted `cm_ir.py` SHA-256 stayed
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`.
- The pre-existing website, README, audit, Runpod, external, temporary, and
  other uncommitted work was not staged, reverted, deleted, or attributed to
  this campaign.

## Lane 1 — real workload intake

Implemented:

- `cmbench/tracing/workload_manifest.py`;
- `scripts/cm_validate_workload_manifest.py`;
- `WORKLOAD-MANIFEST-TEMPLATE.json`;
- `REAL-WORKLOAD-INTAKE.md`;
- `tests/test_cm_workload_manifest.py`.

The schema has exact keys, strict types and enums, nonnegative budgets,
explicit artifact/output-order contracts, separate data approvals, an initial
one-in-16 sampling rule, bounded trace files, input hashing, and
refuse-overwrite output. Unknown fields are refused.

The retained template validates structurally but reports
`ready_for_metrics_capture=false` with 13 explicit blockers. That distinction
prevents an incomplete template from being cited as a real workload. A fully
declared test fixture becomes metrics-ready while expression, context, and
external-upload approval remain independently false.

The remaining input is external and concrete: an owner must identify the real
application and caller boundary, requested artifact/order, call lifecycle,
budgets, capture duration, and approvals. Until then, available traces remain
synthetic benchmark evidence only.

## Lane 2 — DP-R2 temporary-memory policy

Current policy is split by surface:

- direct materializers: 256 KiB output, no temporary limit;
- benchmark CLI: 64 KiB output, `k <= 16`, no temporary limit;
- remote requests: 64 KiB output, no temporary limit unless supplied;
- an explicit lower-level `output_budget=None` can disable admission limits.

The new bounded diagnostic forced dense NumPy materialization for four
deterministic formulas and ran seven repetitions each. The current dense
temporary estimate is always twice output size and ignores structural
operation count. Median `tracemalloc` peak exceeded it as follows:

| `k` | CM nodes | Estimate | Median traced peak | Multiple |
|---:|---:|---:|---:|---:|
| 8 | 40 | 512 B | 19,830 B | 38.73x |
| 10 | 52 | 2,048 B | 29,466 B | 14.39x |
| 12 | 64 | 8,192 B | 49,646 B | 6.06x |
| 14 | 76 | 32,768 B | 115,170 B | 3.51x |

Typed refusal one byte below the estimate occurred before materialization in
all cases. This validates check placement, not estimator accuracy.
`tracemalloc` is not an RSS/native-allocation upper bound, so these ratios must
not be turned into a universal multiplier.

Decision: reject setting a default against the current estimator. The full
compatibility model, policy alternatives, proposed profiles, approval boundary,
and six-stage validation plan are in
`DP-R2-TEMPORARY-MEMORY-POLICY-DECISION.md`. Brian's later approval would need
to cover the numeric profiles and newly possible typed refusals; neither was
assumed here.

## Lane 3 — DP-R3 provenance consolidation

The pre-change map found three active implementations of the same exact-file
SHA-256 operation: whole-file reading in benchmark provenance and streaming
versions in trace replay and the trace-overhead study.

`cmbench/reporting/provenance.py` is now the single streaming implementation.
`scripts.cm_benchmark_provenance` re-exports it for compatibility. All migrated
audit driver source-snapshot lists include the new transitive module, and the
explicit memo Runpod archive includes it. No result schema, timing boundary,
corpus role, source-copy behavior, overwrite policy, or expression hashing was
consolidated.

The DP-R3 smoke completed in under three seconds overall, produced six exact
paired rows with zero mismatches, two charged events, zero drops, and zero I/O
errors. Its three rounds are intentionally insufficient for overhead inference:
the 1.0402 median ratio and amortized event metric failed the long-study gates.
This is retained as a negative/inconclusive performance result, while the
integration/exactness acceptance passed.

## Validation

| Check | Result |
|---|---|
| Python 3.13 compile checks | pass |
| Python 3.13 manifest/tracing/opportunity unittest | 22 passed in 1.086 s |
| Initial focused pytest | 32 passed in 2.84 s |
| DP-R3 provenance integrity pytest | 10 passed in 0.49 s |
| Expanded focused pytest | 84 passed in 38.26 s |
| Complete repository pytest | 391 passed plus 4 subtests in 96.04 s |
| Memo Runpod archive dependency check | pass; 15 files, complete reporting provenance import surface present |
| Workload template JSON validation | pass; correctly not ready |
| DP-R2 raw JSON and DP-R3 JSON/JSONL audit | parse/validation pass |
| Focused/full JUnit | zero failures, errors, or skips |
| Accepted `cm_ir.py` hash | unchanged |

The repository virtual environment intentionally lacks pytest; dependency-free
tests used Python 3.13.5 there, while the established system Python 3.10 pytest
environment ran the focused and full repository suites.

One diagnostic command initially imported the memo campaign as a package and
failed because the dated script expects its sibling directory on `sys.path`.
Running the same read-only archive check from the campaign's intended working
directory passed. No production or campaign failure resulted.

## Artifacts

- `PREREGISTRATION.md`: frozen gates and preservation state.
- `WORKLOAD-MANIFEST-TEMPLATE-VALIDATION.json`: hashed template validation.
- `DP-R2-OUTPUT-BUDGET-PROBE.json`: raw seven-repetition memory measurements.
- `DP-R2-TEMPORARY-MEMORY-POLICY-DECISION.md`: policy decision memo.
- `DP-R3-DUPLICATE-MAP.md`: pre-change duplicate evidence and scope.
- `dpr3_trace_overhead_smoke_raw.csv`: paired smoke rows.
- `dpr3_trace_overhead_smoke_events.jsonl`: bounded metrics trace.
- `dpr3_trace_overhead_smoke_summary.json` and
  `dpr3_trace_overhead_smoke_trace_audit.json`: summary and trace audit.
- `focused_pytest.xml` and `full_pytest.xml`: machine-readable regression
  results.
- `SOURCE-MANIFEST.json`: exact implementation hashes.
- `RUN-COMMANDS.md`: reproducible commands.

## Ranked next work

1. Supply and validate a real workload manifest, then integrate the existing
   one-in-16 bounded metrics sink at that caller boundary. This is the only
   route to evidence-backed cache/family/context/incremental selection.
2. Independently harden the dense, bigint, and word-packed temporary-memory
   estimators and measure RSS/native allocation on held-out structural cases.
   Do not change defaults during estimator work.
3. After estimator and compatibility evidence, ask Brian whether to approve
   `production-balanced-v1` and its potential new refusals.
4. Leave broader audit-driver consolidation deferred. The measured duplicate
   was removed; more refactoring has no demonstrated performance or reliability
   benefit and risks coupling distinct timing/corpus contracts.
5. Keep CUDD/Numba/SIMD, additional independent circuit families, Runpod, and
   external upload explicitly opt-in and workload-triggered.
