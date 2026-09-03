# Architecture-aware comparison corpus and schedule freeze

Date: 2026-09-03
Status: **verified frozen; no timing or cloud authorization**

The current-source four-lane comparison campaign now has a deterministic,
source-blind corpus and schedule freeze. The independent verifier rebuilt the
entire artifact byte-for-byte, rehashed the 21-file implementation closure and
four observed-regression sources, and found no alpha-structural overlap between
the new single-root cases and the observed comparison inputs.

## Frozen corpus

- 49 public complete-relation regression cases are bound from the existing
  public audit corpus.
- 18 repeated-restriction regression cases are bound from C36.
- 6 related-root regression workloads are bound from C37.
- The verified smaller-task functional control is retained as an observed
  regression case.
- 36 fresh single-root expressions cover widths 8, 11, and 14; `andor`,
  `xor_eqv`, and `mixed` operator families; tree-like and high-sharing shapes;
  and two independent replicates per cell.
- 6 fresh related-root workloads and 6 fresh version-history pairs are frozen.

Fresh selection used only the predeclared seed, width/family/shape grid,
identity-DAG structure, depth, sharing fraction, and prior structural
identities. It did not compute or inspect fresh truth outputs, method outputs,
or method timings.

## Frozen schedules and contracts

All arm orders use complete forward/reverse counterbalance cycles. The frozen
plans contain 10,880 Lane A cells, 6,912 Lane B cells, 384 Lane C cells, and
1,470 Lane D cells. Lane B keeps the q1/q4/q16/q64 ladder. Each lane retains the
task-specific artifact defined by the functional admission rather than ranking
methods that return different answers.

The measurement schema includes parsing/normalization, representation
construction, compilation, binding, evaluation, delivery, serialization where
applicable, cleanup, accounted total, output bytes, peak RSS, retained bytes,
source/runtime identity, and failure/refusal status.

Publication remains gated on exact source and artifact identity, zero semantic
mismatches, retention of every unfavorable cell, task-matched artifacts, and
separate cross-machine replication. The historical `1.472x` result remains a
Windows-only result and cannot be silently replaced. New tasks receive new
sections; no universal-winner headline is allowed.

## Decision boundary

The freeze permits only source-identity preservation and local functional
replay. It does **not** authorize fresh truth-oracle generation, timed local or
cloud execution, a RunPod authorization request, selector fitting, neural
training, production routing, or website publication. Those are separate
steps. In particular, the q64 portfolio's 1.0000x selector-oracle headroom still
blocks selector and neural work, but does not block these non-neural,
task-matched comparisons.

Evidence:

- `docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json`
- `docs/recognition/architecture_comparison_freeze_20260903/VERIFICATION.json`
- freeze SHA-256:
  `f00c688efd2d939936d78814794e5638e21bb2352f65863adf5c612b92c99148`
- verification status: `verified_frozen_not_authorized`
- source checkpoint:
  `4c88b8269836c8568d0ff7a8d18ad2a7827c2471`
