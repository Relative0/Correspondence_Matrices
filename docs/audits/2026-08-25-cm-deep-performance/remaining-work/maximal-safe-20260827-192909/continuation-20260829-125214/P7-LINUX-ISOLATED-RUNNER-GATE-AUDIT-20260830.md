# P7 Linux isolated-cell runner gate audit

## Implemented locally

The runner now freezes exact P7 order-ledger subsets and executes each retained cell
through a fresh Linux owned process group. It binds worker requests to the freeze,
plan, cell, case, arm and outside-span scalar oracle; pins the worker to one admitted
CPU; records task-total wall time and sampled whole-process-group peak RSS; bounds
input, output, deadline and process count; and requires cleanup and stream closure.

Evidence uses immutable plan/oracle/environment/source records and append-only ledger
segments. A resumed invocation preserves an interrupted attempt as an explicit error
before a new attempt; partial tails remain preserved in their original segment.
Reconciliation refuses unexpected cells, changed requests, missing primary metrics,
semantic mismatch, incomplete cleanup, changed source identity or a forged success.

## Local verification

- 32 focused tests pass across P7 bindings, the new runner, corpus freeze, BLIF
  recognition and Linux supervision.
- Fake success, refusal, timeout, semantic mismatch and cleanup-failure paths are
  fail-closed.
- Interrupted-attempt recovery preserves the old attempt and requires the identical
  request digest for the retry.
- A real Windows subprocess exercised the worker CLI for a frozen complete-relation
  cell and matched the independent scalar oracle. This is a CLI functional check,
  not Linux supervision evidence.
- Offline-gate V4 reproduces all 58 prepared cases, both policy bindings, checksums,
  source manifest and the two-case nine-arm dry run. It contains no timings.

## Remaining gate

The runner has not yet executed end-to-end under Linux `/proc` supervision. The
next bounded step is the proposed 36-cell RunPod functional scout. Only after that
passes should a minimum-block development timing shard be proposed. Confirmation
data remains untouched, and no performance claim is currently permitted.

