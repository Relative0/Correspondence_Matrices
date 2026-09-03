# C37 frozen prospective native exact confirmation protocol — v3

Date frozen: 2026-09-03  
Scope: exact, non-neural repeated restriction and sibling-output execution

V1 aborted before dataset creation or timing because an inherited portfolio admission
cap rejected a predeclared expression. V2 removed that irrelevant cap, then aborted
before dataset creation or timing because three nominal parameter identities reduced
to C36 truth identities: high operand bits cannot affect a low arithmetic output.

V3 corrects those three rows by structural effective-width rules, not timing or backend
performance. At width 12 it uses multiply `(b_width=3, output_bit=8)` and multiply-add
`(b_width=2, output_bit=4)`; at width 14 it uses multiply
`(b_width=5, output_bit=8)`. The other 15 single-root rows and all six multi-root rows
are unchanged. Schedules, methods, contracts, compiler flags, and all ten gates remain
unchanged from v1. Dataset construction must still abort wholesale on any C36 truth
overlap, duplicate truth, support omission, or scalar/expression disagreement.

## Frozen candidates and controls

Single-root candidate: ABI-v1 C11 fused slot executor. Controls: the exact Python R2
topological restricted evaluator and exact `uint16` tuple projection.

Multi-root candidate: one union arena evaluated once for three sibling roots. Control:
three separately compiled/evaluated native arenas. Both sides deliver the same explicit
residual relations, counts, SAT flags, witnesses, and digests.

## Prospective data and lifecycle

There are three single-root cases per support width 11–16: adder-tree,
multiply-low-cone, and multiply-add-low-cone. The six multi-root workloads are two
multiply groups, add-7, popcount-15, 3x5 adder-tree, and 4x4 multiply plus a seven-bit
addend. No truth statistic beyond mandatory freshness/correctness checks, timing, or
backend output may select or remove a row.

Each identity receives 64 output-blind deterministic restrictions with residual widths
6, 8, and 10. All setup, compilation, restriction setup, evaluation, semantic delivery,
and cleanup are charged. Oracle construction is outside timing. Process-global bitset
environment caches are cleared before every complete session.

Single-root timing uses 12 complete balanced blocks; multi-root uses 20. One untimed
warm-up per method precedes measurement. Memory sessions are separate.

## Unchanged fixed gates

1. zero relation, count, SAT, witness, canonical-delivery, ABI, hash, and replay mismatch;
2. single-root aggregate case-median speedup over Python R2 at least `1.10x`;
3. single-root minimum case-median speedup at least `0.95x`;
4. single-root minimum width-aggregate speedup at least `1.00x`;
5. single-root p95 session speedup at least `0.95x`;
6. native single-root maximum declared workspace at most 64 MiB;
7. multi-root aggregate workload-median speedup at least `1.10x`;
8. multi-root minimum workload-median speedup at least `1.00x`;
9. multi-root p95 session speedup at least `0.95x`;
10. every multi-root workload reduces node count and union workspace is no larger than
    its three-root control.

No result-dependent gate, case, method, schedule, or implementation change is allowed.
Failure refuses integration. Passing makes ABI-v1 eligible only for guarded opt-in
integration with deterministic Python fallback, not automatic public promotion.
