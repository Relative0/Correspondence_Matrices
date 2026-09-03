# CM recommendations implementation audit

> September 3 closure: `CM_NATIVE_PORTFOLIO_BASELINE_CLOSURE_2026_09_03.md`
> compares native slots with the omitted CSE/CM bigint and word controls in one
> cache-isolated run. Native is the fixed winner on all 18 exposed cases; selector
> headroom is exactly `1.0000x`, so prospective routing and neural work remain stopped.

> Post-audit continuation: projection cleanup, fused native slots, and native
> multi-root sharing are implemented and tested in
> `CM_NEXT_ITEMS_PROJECTION_NATIVE_MULTI_ROOT_2026_09_02.md`. That continuation
> also corrects complete-task cache isolation for backend timing.

**Date:** 2026-09-02  
**Scope:** exact CM/Boolean backend optimization; no neural training or C37 confirmation.

## Workstream boundary

The recommendations in `CM_NEXT_OPTIMIZATION_IMPLEMENTATION_PROGRAM.md` belong
to the straightforward exact-computation portfolio used by the current
benchmarks: direct packed evaluation, CSE, CM IR, projection, packed ANF, and
exact GF(2) decomposition. They do not train a neural network with CMs.

The public expert page at
`https://relative0.github.io/Correspondence_Matrices/expert.html` is also an
exact benchmark/evidence surface. It compares task-matched CM, BitSet, CSE,
ROBDD/CUDD, SymPy, and Espresso behavior and explicitly scopes conclusions by
artifact and lifecycle. It is not a neural-training result page.

Neural research remains a separate advisory workstream. Its models may later
select among exact methods only if optimized exact methods leave enough
prospective headroom to pay for prediction and verification. The repaired C36
development cohort does not currently leave that headroom.

## Existing recommendation work audited

The shared working tree already contained development-only implementations and
verified artifacts for:

- R0 occurrence-recursive, R1 identity-memoized, and R2 topological/liveness
  restricted evaluation;
- bigint-versus-word comparisons;
- concatenated-lane and union-care-set batching;
- trace-specialized multi-root restriction;
- ANF-basis GF(2) rank and factor conversion;
- ANF rank inside the complete C16 screen;
- sound bounded-rank pruning.

The retained results support R2 and the rank-specific ANF kernel. They do not
support production integration of the batch, trace-specialized, ANF
full-screen, or bounded-rank candidates. Historical C36 behavior was preserved
as a control.

Primary consolidated evidence:

- `CM_RESTRICTED_EVALUATOR_IMPLEMENTATION_AND_TESTING_2026_09_02.md`
- `CM_RECOMMENDED_INTEGRATIONS_IMPLEMENTATION_AND_TESTING_2026_09_02.md`

## Defects found and fixed

Two memo tables used `memo.get(key)` with `None` as the miss sentinel even
though zero is a valid packed Boolean result.

1. `cmbench/comparative/gf2_restricted_evaluators.py`, R1:
   a shared node whose restricted packed result was zero could be recomputed.
2. `bitset_backend.py`, `eval_cm_node_bitset`:
   a shared CM node whose packed result was zero could likewise be recomputed.

Both paths now distinguish key absence from a cached zero by indexed lookup
with `KeyError` handling. Exact output is unchanged; the stated one-evaluation-
per-identity invariant now holds for false as well as true/nonzero results.

Regression coverage was added to:

- `tests/test_cm_comparative_restricted_evaluators.py`
- `tests/test_bitset_backend.py`

The tests construct shared zero-valued nodes and count actual leaf evaluation,
not a theoretical counter.

## Replacement development run

Because the retained `-002` artifact hashes the older source bytes, it remains
historical evidence. A source-hash-closed replacement was created:

`docs/recognition/runs/restricted-evaluator-development-20260902-003/`

Independent verification:

- status: `verified`;
- 18 exposed C36 cases and 1,152 independent query replays;
- 1,296 performance sessions;
- 108 memory-profile sessions;
- 82,944 timed query rows;
- 117 local source hashes, 8 native-module hashes, and interpreter binding;
- zero relation, count, SAT, witness, canonical-delivery, trace, profile,
  measurement, schedule, or summary mismatch;
- no prospective data, training, production write, or production promotion.

Results SHA-256:
`a61cd63899538e8c0b6d33456a1a621247b0e4246388a9c1d7bc572852d5d0ef`

Manifest SHA-256:
`d732589e42b2b1d1cf2d08d12d7fec9cfa26f9f353a0ba8ceabdd01b7cf0a40b`

### Q64 result

Values are sums of 18 per-case medians from the counterbalanced development
run.

| Method | Q64 total |
|---|---:|
| R0 occurrence-recursive | 820.203 ms |
| R1 identity memo | 133.408 ms |
| **R2 topological/liveness** | **108.557 ms** |
| flattened CSE words | 163.448 ms |
| compiled truth projection | 158.359 ms |
| CM IR words | 179.124 ms |

- R1 versus R0: 6.1481x.
- R2 versus R0: 7.5555x.
- R2 versus R1: 1.2289x.
- Optimized primitive oracle: 108.512 ms.
- Oracle headroom over R2: 1.000416x, approximately 0.04%.

R2 won 17 of 18 optimized per-case choices; compiled projection won one. The
available selector headroom is far below the proposed 1.05x prospective gate.

## Test results

Focused exact/recommendation compatibility suite:

```text
63 passed in 31.34s
```

Broad non-neural suite:

```text
1221 passed, 4 warnings, 1127 subtests passed in 204.67s
```

The warnings are the existing `dd.bdd.BDD.__del__` referenced-node shutdown
warnings in persistence tests. No correctness test failed. Torch-dependent
neural tests and the stale generated-chart revision test remained excluded for
the same documented environment/revision reasons as the dossier.

## Integration decision

- Keep the zero-safe memo fixes and regressions.
- Keep R0 as a historical control and R1/R2 as exact development backends.
- Treat R2 as the strongest repaired direct method on exposed C36 development
  data, not as a prospectively confirmed production default.
- Do not formalize the old `U/N > 10` router; its headroom collapsed after
  primitive-backend repair.
- Do not add a neural selector on this cohort: approximately 0.04% oracle
  headroom cannot pay for a model, selection, and exact verification.
- Keep the neural-CM training thread separate unless it is explicitly studying
  a different task where prediction can avoid material exact work.
