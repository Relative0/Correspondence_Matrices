# CM learning benchmark handoff contract

**Date:** 2026-09-04  
**Status:** implemented; current evidence abstains; no training or benchmark run.

## Purpose

The Benchmark task and learning task now have an explicit machine-readable
boundary. The Benchmark task may produce exact evidence independently; the learning
task accepts only a normalized `crse-learning-benchmark-handoff/v1` document and
recomputes its economics. It never calls the benchmark runner.

Passing this contract permits only consideration of a development learning
experiment. It does not itself train a model, open prospective data, enable routing,
or authorize production advice.

## Required handoff

The contract requires:

- a frozen task, source tree, case set, and exact-baseline closure;
- confirmation that all relevant task-identical exact arms and unfavorable/refused
  rows were retained;
- a source-blind development protocol frozen before labels;
- at least 16 fit, 8 validation, and 8 audit source groups;
- at least two backend labels with at least eight source groups per label;
- zero source-group overlap and zero prospective cases consumed;
- at least two independently verified runs on distinct physical machines;
- identical case-set and label-table hashes across both machines;
- zero schedule, semantic, and source/artifact mismatches;
- sum-based best-fixed and per-case-oracle totals, not a geometric-mean proxy;
- p95 feature/control, inference, exact-verification, and expected-fallback costs
  measured on each exact-timing host; and
- at least `1.10x` gross and fully charged speedup on every replication.

The handoff must explicitly permit development-training eligibility while keeping
prospective consumption and production routing prohibited. Economic totals and
speedups are recomputed; altered derived values are rejected.

## Current result

The current verified evidence fails with eight explicit blockers:

1. insufficient development groups by split;
2. insufficient source groups per label;
3. the protocol postdates the current labels;
4. the query ladder lacks sum-based charged headroom;
5. cross-machine replication is missing;
6. the query-ladder claim boundary forbids learning claims;
7. the complete charged-cost vector is missing; and
8. recognition timing and exact timing use different hosts.

The two positive diagnostics remain visible but do not bypass these blockers:

- version-history gross sum-based headroom is `1.137580420x` on three exposed
  cases; and
- q64 best-fixed geometric-mean oracle regret is `1.107862216x` on the one-host
  query ladder.

Current output is complete abstention with the unchanged exact fallback.

## Implementation

- `cmbench/recognition/learning_benchmark_handoff.py`
- `scripts/cm_learning_benchmark_handoff.py`
- `tests/test_learning_benchmark_handoff.py`

Current readiness can be checked without running benchmarks:

```powershell
.\.venv\Scripts\python.exe scripts\cm_learning_benchmark_handoff.py
```

Exit code `2` means fail-closed abstention. A later in-project handoff can be
checked with `--handoff <path>`; malformed, incomplete, drifted, economically
insufficient, or over-broad handoffs also abstain.
