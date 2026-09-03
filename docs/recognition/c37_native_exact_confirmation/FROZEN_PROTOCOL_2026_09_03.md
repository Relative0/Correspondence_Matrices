# C37 frozen prospective native exact confirmation protocol

Date frozen: 2026-09-03  
Scope: exact, non-neural repeated restriction and sibling-output execution  
Development evidence used to justify this confirmation: C36 plus the 2026-09-02 native development runs  
Training, learned routing, threshold fitting, and output-based case selection: forbidden

## Frozen candidates and controls

Single-root candidate: ABI-v1 C11 fused slot executor, compiled from
`native/cm_fused_slots/fused_slot_executor.c` with the checked-in build wrapper.

Single-root controls:

- identity-memoized/topological Python restricted evaluator R2;
- the exact `uint16` tuple projection control.

Multi-root candidate: one ABI-v1 union arena evaluated once for three sibling roots.
Control: three separately compiled and evaluated native arenas. Both deliver the same
three explicit residual relations, counts, SAT flags, witnesses, and digests.

## Prospective data selection

The source repository and generator semantics may be reused, but every exact parameter
identity and truth identity must be disjoint from C36.

Single-root selection is fixed as three generator parameter rows per support width
11 through 16: adder-tree, multiply-low-cone, and multiply-add-low-cone. The exact
parameter table lives in `prospective_candidates()` and is hashed into the freeze.
No truth statistic, timing, or backend output may select or remove a row. A row may
only abort the whole confirmation if its independent scalar and expression oracles
disagree or it lacks its declared support.

The six multi-root workloads are fixed in
`prospective_sibling_output_workloads()`: two new multiply groups, add-7, popcount-15,
3x5 adder-tree, and 4x4 multiply plus a seven-bit addend. Their workload identities
must be disjoint from the development workloads. Structural sharing is reported but
does not select a workload.

Each case/workload receives 64 output-blind deterministic restrictions with residual
widths 6, 8, and 10. All setup, compilation, restriction setup, evaluation, semantic
delivery, and cleanup are charged. Independent oracle construction is outside timing.
The process-global bitset environment cache is cleared before every complete session.

## Schedule and fixed gates

Single-root timing uses 12 complete balanced blocks (two repetitions of every
three-method order). Multi-root timing uses 20 complete balanced blocks. One untimed
warm-up per method precedes measurement. Memory sessions are separate and excluded
from timing summaries.

All of the following gates were fixed before loading the prospective dataset:

1. zero relation, count, SAT, witness, canonical-delivery, ABI, hash, and replay mismatch;
2. single-root aggregate case-median speedup over Python R2 at least `1.10x`;
3. single-root minimum case-median speedup at least `0.95x`;
4. single-root minimum width-aggregate speedup at least `1.00x`;
5. single-root p95 session speedup at least `0.95x`;
6. native single-root maximum declared workspace at most 64 MiB;
7. multi-root aggregate workload-median speedup at least `1.10x`;
8. multi-root minimum workload-median speedup at least `1.00x`;
9. multi-root p95 session speedup at least `0.95x`;
10. every multi-root workload reduces compiled node count and union workspace is no
    larger than the corresponding three-root control.

No gate, case, method, compiler flag, schedule, or implementation may be changed after
prospective results are inspected. Failure retains the Python/native-separate controls
and refuses integration. Passing makes the ABI-v1 path eligible only for guarded,
opt-in integration with deterministic Python fallback; it does not make the native
binary portable to another compiler, operating system, or CPU and does not authorize
a public benchmark claim without a separately identified benchmark refresh.

