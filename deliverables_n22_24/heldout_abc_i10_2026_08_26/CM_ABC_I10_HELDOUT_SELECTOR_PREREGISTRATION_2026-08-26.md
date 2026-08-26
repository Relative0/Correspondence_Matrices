# CM ABC i10 held-out selector preregistration

Preregistered: **2026-08-26**, after freezing source bytes and before parsing,
cone eligibility inspection, or timing.

## Frozen source

- Upstream: `https://github.com/berkeley-abc/abc`
- Branch resolved before download: `master`
- Commit: `c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4`
- Circuit URL: `https://raw.githubusercontent.com/berkeley-abc/abc/c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4/i10.aig`
- Circuit SHA-256: `b551b0932703d7d3c5e3b3cd0fc742b484d0f5d8332b1bf3dd7567679d1559d7`
- Notice URL: `https://raw.githubusercontent.com/berkeley-abc/abc/c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4/copyright.txt`
- Notice SHA-256: `819151b8f059a48f806c75732ef62b1f873b49b6a04fb128aed28bf87d3dcd6c`

Only file size, hashes, upstream documentation, and the license notice were
inspected before this protocol was frozen. No AIGER parse, cone count, support
distribution, truth value, or timing outcome was inspected.

## Screening and immutable corpus construction

Use the already-tested binary AIGER parser and independent bigint truth
evaluator from `cm_gap_epfl_extract_2026_08_03.py`. Reject latches, malformed
files, constants, input roots, constant-literal cones, constant functions,
syntactic support above 16, semantic support outside 8..16, and cones above
5,000 AIG AND nodes. Freeze every admitted cone's structural hash, complete
syntactic-support truth SHA-256, semantic-support mapping, and expression DAG.

Candidate roots are considered without timing: primary outputs in output-index
order, then internal AND nodes in topological order. Deduplicate by
`(structural_hash, truth_sha256)`, primary output first. Within each semantic
support stratum 8..16, select at most 16 roots: evenly spaced primary outputs
first, then enough evenly spaced internal roots to reach 16. This deterministic
cap prevents a large single stratum from dominating.

Screening passes only with at least 32 unique selected cones across at least
three semantic-support strata. Failure is a negative source-suitability result;
do not relax the criteria after observing it.

## Timing protocol

Run the existing deep-audit paired alternating flat-bigint and word-packed
kernels with identical expressions, semantic support, output order, and exact
packed artifacts. Use five preparation repetitions, nine kernel rounds, and a
16 MiB temporary-memory cap. Preserve refusals and raw-arm ineligibility. The
new corpus is `validation_heldout`; it must never be relabelled as tuning.

## Frozen feature selector

Fit separately for raw-expression and CM programs using only the existing BX1
tuning rows from the 2026-08-26 representative audit. The response is
`log(words_time / flat_time)`. Features available before kernel execution are:

1. `live_k`;
2. `log1p(instruction_count)`;
3. `log1p(executed_bigint_ops)`;
4. `log1p(executed_word_ops)`;
5. `log1p(peak_live_word_buffers)` (zero for the raw arm when unavailable);
6. `log1p(structural_dag_nodes_source)`;
7. `log1p(unfolded_tree_nodes)`.

Fit standardized ridge regression. Choose lambda from
`{0.01, 0.1, 1, 10, 100}` by leave-one-`live_k`-stratum-out BX1 cross-validation,
minimizing, in order: catastrophic regret count (`>=2`), routed regret
geometric mean, mean absolute log error, then lambda. Refit on all BX1 rows.
Route to flat below `k=6`; otherwise route to words only when predicted
`log(words/flat) < 0`. The current `k=16` rule remains the production control.
No held-out timing may influence features, lambda, coefficients, or threshold.

## Acceptance and production boundary

For each eligible arm, the held-out feature rule must have:

- zero exact mismatches;
- regret geometric mean at most `1.05`;
- zero catastrophic routes and maximum regret below `2`;
- regret geometric mean no more than 1% worse than the current `k=16` rule.

This single-circuit study cannot by itself authorize production integration.
Integration additionally requires at least a 2% held-out regret improvement in
one arm, no regression in the other, and replication on another independently
frozen circuit family. Report row-bootstrap uncertainty as conditional on this
one circuit; do not call it a circuit-cluster interval.

