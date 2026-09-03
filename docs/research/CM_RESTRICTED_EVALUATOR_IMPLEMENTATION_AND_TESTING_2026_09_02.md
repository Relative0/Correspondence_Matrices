# CM restricted evaluator implementation and testing note

**Date:** 2026-09-02  
**Scope:** development-only validation of the restricted-evaluator finding in
`CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md` and
`CM_NEXT_OPTIMIZATION_IMPLEMENTATION_PROGRAM.md`.

Follow-up batching, engine, trace-specialization, ANF-rank, complete-screen,
and bounded-rank results are consolidated in
`CM_RECOMMENDED_INTEGRATIONS_IMPLEMENTATION_AND_TESTING_2026_09_02.md`.

## Finding adjudication

The finding was valid in the live working tree. C36's `_eval_ast_restricted`
still followed expression occurrences recursively for every query, while the
complete-truth path used by compiled projection reached the identity-memoized
`eval_expr_bitset` implementation.

The historical C36 helper was not modified. The new development surface keeps
it available as the frozen semantic control and compares:

- **R0:** the same occurrence-recursive gate evaluation, with environment setup
  split out for stage timing;
- **R1:** a query-local identity memo, so each reachable `Expr` object is
  evaluated once per restriction;
- **R2:** direct DAG-v2 topological slot execution with use counts and last-use
  release of packed results.

The experiment also freshly remeasured flattened CSE words, CM-IR words, and
compiled truth projection so the post-repair backend oracle did not reuse old
timings.

## Implementation

- `cmbench/comparative/gf2_restricted_evaluators.py`
  - R0/R1/R2 exact evaluators;
  - direct DAG-v2 arena compilation;
  - exact unique/unfolded node, gate, edge, depth, and liveness counters.
- `cmbench/comparative/gf2_restricted_evaluator_experiment.py`
  - six-arm, 12-block counterbalanced development experiment;
  - decode, representation, restriction setup, evaluation, delivery, cleanup,
    and total timings;
  - per-query raw rows, checkpoints at q1/q4/q16/q64, RSS sampling, and separate
    tracemalloc sessions;
  - fresh fixed/per-case backend oracle and width/family/expansion subgroups;
  - manifest closure over required sources, all loaded project modules, loaded
    native extensions, and the interpreter executable.
- `scripts/cm_comparative_restricted_evaluator_development.py`
  - bounded CLI runner.
- `scripts/crse_restricted_evaluator_development_verify.py`
  - independent trace/oracle/profile/summary replay;
  - source, native-module, interpreter, artifact, and `bitset_backend.py` binding.
- `tests/test_cm_comparative_restricted_evaluators.py`
  - all-gate exactness against the frozen helper;
  - sharing, unique-node, unfolded-work, repeated-child release, liveness,
    schedule/tamper, session-stage, and manifest-tamper tests.

No selector was fitted, no prospective C37 data was consumed, and no production
backend or routing policy was promoted.

## Verified development run

Artifact:
`docs/recognition/runs/restricted-evaluator-development-20260902-002/`

- Results SHA-256:
  `83b7e2b5461990fef925847cd5338c573f8e9499ff3d26680583d327e8154e8d`
- Manifest SHA-256:
  `c90107e1f855da0ea721af0fa449c798ee6eddfe96e6a4eb9510c7fb123caae1`
- Independent verification: `verified`
- Manifest closure checked: 117 local sources, 8 loaded native modules, and the
  interpreter executable.
- Checked: 1,296 performance sessions, 108 separate memory-profile sessions,
  and 82,944 timed query rows.
- Exactness: zero relation, count, SAT, witness, canonical-delivery, profile,
  measurement, or independently recomputed summary mismatches.

An initial `-001` run was invalidated because the Windows RSS probe used the
default `ctypes` return type and truncated the 64-bit process handle. The API
signature was corrected and tested; `-001` was removed rather than retained as
evidence. The verified `-002` run is the only retained result.

## Measured results

The table reports sums of 18 per-case medians from the fresh counterbalanced
run. Speedups are relative to R0.

| Queries | R0 total | R1 total | R2 total | R1 vs R0 | R2 vs R0 | Best fixed |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 17.263 ms | 6.516 ms | 8.292 ms | 2.6492x | 2.0820x | R1 |
| 4 | 56.020 ms | 13.140 ms | 13.906 ms | 4.2631x | 4.0284x | R1 |
| 16 | 212.967 ms | 37.879 ms | 36.217 ms | 5.6222x | 5.8803x | R2 |
| 64 | 827.918 ms | 124.587 ms | 112.434 ms | 6.6453x | 7.3636x | R2 |

At q64 the fresh non-direct totals were:

- flattened CSE words: 166.041 ms;
- compiled truth projection: 161.026 ms;
- CM-IR words: 185.441 ms.

**MEASURED:** R2 was the q64 best fixed backend. It was also the best optimized
backend for the four historical high-`U/N` cases: 31.279 ms versus 35.443 ms for
projection and 52.175 ms for flattened CSE.

**DERIVED:** the aggregate theoretical node-evaluation reduction from R0
unfolding to R1 unique-node evaluation was 40.8023x. R1 evaluated no more than
the reachable unique-node count; R2 evaluated exactly that count and its peak
live result slots never exceeded it.

**DERIVED:** after repair, the optimized per-case oracle retained only 1.0041x
headroom over the best optimized fixed backend at q64. The old `U/N > 10`
routing premise therefore did not survive this development adjudication as a
material production candidate. One multiply-low-cone case still selected
projection post hoc, but the aggregate available headroom was about 0.41%, well
below the proposed 1.05x prospective gate.

Memory sessions were excluded from performance aggregation. Their maximum
stage-sampled RSS deltas / tracemalloc peaks were approximately:

- R1: 1.86 MB / 1.47 MB;
- R2: 0.35 MB / 0.76 MB;
- projection: 0.52 MB / 1.25 MB.

RSS deltas are stage-boundary samples, not isolated process maxima; the run also
records the process-wide OS high-water mark.

## Testing performed

Focused exact suite:

```text
42 passed in 7.36s
```

This included the existing bitset, decomposition, C34, C35, and C36 tests plus
the seven new restricted-evaluator tests.

Broad non-neural suite:

```text
1200 passed, 4 warnings, 1127 subtests passed in 209.52s
```

The four warnings are the existing `dd.bdd.BDD.__del__` referenced-node shutdown
warnings in persistence tests; no correctness test failed. The documented
Torch-dependent neural files and stale generated-public-chart revision test were
excluded, matching the dossier's reproducible default-environment procedure.

The independent artifact verifier also passed after recomputing traces, exact
outputs, structural profiles, schedules/counts, stage arithmetic, complexity
invariants, memory-profile presence, and every reported summary value.

## Decision

The implementation asymmetry was real and materially affected C36's backend
landscape. R1 is preferable at q1/q4 in this development cohort; R2 is preferable
at q16/q64 and has substantially lower observed allocation/RSS tails than R1.

Do not formalize the old structural router unchanged. The next engineering
decision should start from R1/R2 as the repaired direct controls. Because the
q64 fixed-backend result already captures 99.59% of the optimized primitive
oracle on this exposed cohort, a formal routing confirmation is not presently
justified by these data alone.
