# H2/H3 current-source profile-first gate

Date: 2026-09-08  
Scope: exact, non-neural CM construction and dense materialization only  
Status: preregistered before decision-bearing execution

## Binding boundary

This phase is subordinate to
`CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md` and
`CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md`. H9 remains
deferred. This phase does not select replacement hardware repositories, run Yosys,
extend incremental compilation, request or use cloud compute, change production
defaults, or revise public claims.

The source checkpoint is the locally recorded `origin/main` commit
`c9af2a3c80388e467944bd706036996db9eed9b8`. A fetch was attempted before the
freeze but GitHub was unreachable; the local checkout and local `origin/main` ref were
byte-identical at that commit. Production files are hashed individually in `FREEZE.json`.

## Frozen workload

Every input was admitted by the verified architecture-comparison freeze
`f00c688efd2d939936d78814794e5638e21bb2352f65863adf5c612b92c99148`.
Selection uses only lane, cohort, width, family, shape, replicate, and existing case
identity—never method output or timing.

- Complete relation: all fresh replicate-zero tree and high-sharing cases at widths 8
  and 14 (three operator families), plus the observed nominal-n20 controlled-live 8,
  12, and 16 regression cases.
- Repeated restriction: all 18 observed C36 cases plus the same 12 fresh cases. The
  exact q1 and q64 boundaries are retained.
- Related multi-root: all six observed C37 and six fresh workloads, for both the current
  Python sharing-union and separate-root controls at q64.
- Smaller queries: every runnable width-at-most-8 admitted case, all six scalar
  sublanes, both fresh/resident CM lifecycles, and CM structural reload.

Tree-shaped fresh cases and the three observed complete-relation cases are explicit
low-sharing/regression controls. No case may be removed after execution begins.

## Frozen measurement boundary

Each operation receives two warmups followed by seven measured repetitions. Reported
time is the median of raw `perf_counter_ns` stage records; every raw repetition is
retained. Cache clearing and pre-measurement garbage collection occur outside the timed
span. Cold spans start at DAG-v2 deserialization and include canonical CM construction,
binding/layout, exact evaluation/materialization, conversion/delivery, and canonical
serialization. Reused spans retain the parsed/compiled representation but rebuild the
required output; output caching is forbidden.

Attribution is a separate one-shot `cProfile` pass and uses mutually exclusive internal
self-time categories, not cumulative call time. The frozen categories are:

- canonical key creation/order preparation;
- hashing;
- interning;
- canonical serialization;
- dense lifting/alignment;
- allocation;
- packed/dense conversion; and
- temporary copies/pointwise temporaries.

Generic low-level allocation/copy categories are conservative upper bounds. The raw
profile remainder is retained, and category time is never subtracted from end-to-end
time. Existing optional CM diagnostics are collected only in the attribution pass;
production return values and routing remain unchanged.

Memory is a third, separate pass. After warmup and garbage collection it records current
RSS at the boundary, samples current RSS every 1 ms through the operation, records RSS
with the required artifact retained and after release/collection, and records the
corresponding `tracemalloc` baseline/current/peak values. Signed retained deltas are
preserved; only incremental peak is nonnegative by definition. The sampler lifecycle is
reported. This avoids reusing the process-lifetime high-water mark as an incremental
memory estimate.

## Frozen materiality and continuation gate

H2 applies only to cold complete-relation and cold repeated-restriction rows. H3 applies
only to dense complete-relation rows, cold and reused. A component is material only if
all of the following hold in its applicable scope:

1. at least six exact, non-refused cells exist;
2. aggregate exclusive profile share is at least 15%;
3. median per-cell share is at least 10%;
4. median exclusive component time is at least 50 microseconds;
5. at least half the cells individually reach 10%;
6. both observed and fresh cohorts pass the aggregate 10% cohort floor when both are
   present; and
7. allocation or temporary-copy candidates additionally have median sampled/traced
   peak above required output bytes by at least 25%.

If no component passes, H2 and H3 remain deferred and no candidate or RunPod request is
permitted. If multiple components pass, only the one with the largest aggregate share
may proceed. One small reversible candidate may then be tested against an unchanged
current-source control. It must preserve every oracle, order, canonical SHA-256, and
structural signature; improve its targeted applicable end-to-end geomean by at least
3% and its targeted component by at least 5%; regress no individual applicable case by
more than 5%, no low-sharing control by more than 3%, and neither peak nor retained
memory by more than 5%. It must also pass the focused, exhaustive small-function,
sharing-metamorphic, and maintained non-neural checks.

Only if source identity, complete coverage, exactness, stability, memory validity,
independent summary replay, candidate benefit, all regression limits, and all tests pass
may an exact RunPod authorization request be prepared. Preparation is not authorization
to create a Pod.

## Instrumentation-only retry note

Attempt 001 retained all 237 rows but failed closed because the 64-bit Windows process
pseudo-handle was truncated by ctypes' default return type, leaving sampled RSS
unavailable. Its `tracemalloc` observations and nonmaterial component shares are not
promoted. Retry 002 changes only the ctypes signature and strengthens the summary check
to require `rss_available`; it preserves every workload, repetition, timing boundary,
threshold, continuation rule, and unfavorable row from this protocol.
