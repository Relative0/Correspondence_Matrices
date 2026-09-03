# CM recommended integrations: implementation and testing note

**Date:** 2026-09-02  
**Scope:** development-only adjudication of the immediate recommendations in
`CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md` and
`CM_NEXT_OPTIMIZATION_IMPLEMENTATION_PROGRAM.md`.

## Answer about C37

No C37 confirmation data, policy, threshold, result, or production route was
changed. The work covered multiple recommended implementations, but all new
measurements used exposed C36 or C16 development data. A method was left out of
the live default whenever its complete-task gate failed.

## Recommendation matrix

| Recommendation | Implemented/tested | Result | Integration decision |
|---|---|---|---|
| R0/R1/R2 restricted evaluation | Frozen occurrence control, identity memo, direct DAG-v2 topological/liveness arena | R2 was 7.3636x faster than R0 at q64; repaired oracle headroom fell to 1.0041x | Keep exact development backends; abandon old `U/N > 10` production premise; no C37 promotion |
| Stage/RSS/manifest closure | Decode, representation, setup, evaluation, delivery, cleanup, RSS, tracemalloc, source/native/interpreter hashes | Verified with zero mismatch | Integrated into each new development harness/verifier |
| Bigint versus NumPy words | CSE and CM-IR bigint/words at widths 11–16 and q1/q4/q16/q64 | At q64 bigint was 1.755x faster for CSE and 1.636x faster for CM-IR; bigint won every width | Existing automatic selector already keeps 6–10 live-variable residuals on bigint; no selector change needed |
| Concatenated and union-care batching | Arbitrary assignment lanes, exact gather, duplicate handling, memory/timing experiment | Best q64 batch achieved 0.0447x of best nonbatch, about 22.38x slower | Exact implementation retained for research; continuation gate failed; not routed |
| Trace-specialized cofactor/multi-root arena | Relevant-fixed-signature cache, structural interning, residual-order grouping, multi-root liveness execution | q64 achieved 0.4427x of best control, about 2.26x slower | Exact implementation retained; continuation gate failed; not routed |
| ANF-basis GF(2) rank | Packed ANF matrix rank plus exact factor conversion back to truth basis | 458,752 exhaustive four-variable function/partition checks, zero mismatch; rank-only C16 screen was 17.7896x faster including ANF construction and 20.0611x with precomputed ANF | Algebra/kernel validated for rank-specific future use |
| ANF rank in complete C16 screen | ANF rank pre-screen with old truth-basis payload materialization, unchanged cofactor/Kronecker screens | Candidate documents and best artifacts byte-identical; complete task was 0.9763x from truth and 0.9794x with precomputed ANF | Complete-task gate failed; live C16 analyzer unchanged |
| Sound partial-rank lower bound | Stop elimination once partial rank cannot yield a compressing rank artifact | Candidate documents byte-identical; pruned 3.2051% of rank rows versus 30% gate and ran at 0.9793x | Pruning and speed gates failed; live analyzer unchanged |

## Main implementation surfaces

- Restricted evaluators and first experiment:
  `cmbench/comparative/gf2_restricted_evaluators.py` and
  `cmbench/comparative/gf2_restricted_evaluator_experiment.py`.
- Arbitrary-lane batching:
  `cmbench/comparative/gf2_multi_query_batches.py` and
  `cmbench/comparative/gf2_multi_query_batch_experiment.py`.
- Trace specialization:
  `cmbench/comparative/gf2_trace_specialized.py` and
  `cmbench/comparative/gf2_trace_specialized_experiment.py`.
- ANF rank and exact factor transform:
  `cmbench/recognition/gf2_anf_rank.py` and
  `cmbench/comparative/gf2_anf_rank_experiment.py`.
- Complete-screen ANF candidate:
  `cmbench/recognition/gf2_anf_screened.py` and
  `cmbench/comparative/gf2_anf_full_screen_experiment.py`.
- Bounded rank candidate:
  `cmbench/recognition/gf2_bounded_rank.py` and
  `cmbench/comparative/gf2_bounded_rank_experiment.py`.
- Each experiment has a bounded CLI runner and an independent artifact
  verifier under `scripts/`.

These are explicit development surfaces. Historical C36 implementations were
not silently rewritten, and negative candidates were not inserted into the
production selector or C16 global-best default.

## Verified artifacts

| Run | Independent status | Checked work |
|---|---|---|
| `restricted-evaluator-development-20260902-002` | verified | 1,296 performance sessions, 108 memory sessions, 82,944 query rows |
| `multi-query-batch-development-20260902-001` | verified | 4,608 performance sessions, 144 memory sessions, 1,152 oracle queries |
| `trace-specialized-development-20260902-001` | verified | 1,152 performance sessions, 72 memory sessions |
| `anf-rank-development-20260902-003` | verified | 458,752 exhaustive checks, 640 performance sessions, 160 memory sessions |
| `anf-rank-full-screen-development-20260902-002` | verified | 360 performance sessions, 27 memory sessions |
| `bounded-rank-development-20260902-001` | verified | 160 performance sessions, 18 memory sessions |

All verifiers reported zero semantic, artifact, timing-stage, schedule,
measurement, summary, and manifest mismatch in the fields applicable to their
run. Invalid, unverified ANF attempts `-001`/`-002` and full-screen `-001` were
removed after verified replacements were generated; they are not evidence.

## Regression testing

Focused exact/recommendation suite:

```text
82 passed in 33.97s
```

Broad non-neural suite using the dossier's documented exclusions:

```text
1219 passed, 4 warnings, 1127 subtests passed in 217.14s
```

The four warnings are the existing `dd.bdd.BDD.__del__` referenced-node
shutdown warnings in persistence tests. No correctness test failed.

## Final decision

The recommended work changed more than one or two items: it added and verified
the repaired restricted evaluator, two arbitrary-lane batch modes, a
trace-specialized multi-root evaluator, ANF-basis rank/factor conversion, a
complete-screen ANF candidate, a sound bounded-rank candidate, their runners,
verifiers, raw artifacts, and regression tests.

The evidence does **not** support writing any of the new batch, trace, ANF
full-screen, or bounded-rank candidates into C37 or a production default. The
strong positive results are the repaired R2 evaluator and the ANF rank
subroutine in a rank-specific lifecycle. The old structural router remains
unjustified after repair, and the conservative bigint engine policy is already
consistent with the new measurements.
