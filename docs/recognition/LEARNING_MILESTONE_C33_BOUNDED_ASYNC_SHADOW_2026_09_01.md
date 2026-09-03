# Learning milestone C33: bounded asynchronous prepared-policy shadowing

**Date:** 2026-09-01
**Status:** local implementation, measurement, and independent verification complete
**Training or policy refit:** none
**Production writes:** none
**Shadow/production promotion:** false / false

## Purpose

C32 proved that the frozen C30 prepared policy could be observed without changing the
exact response, but synchronous observation cost 2.045x the shadow-disabled total time.
C33 moves that observational work behind a bounded queue and makes the response boundary
machine-checkable: candidate work cannot begin until the caller explicitly acknowledges
that the exact baseline has been delivered.

This is local engineering evidence for an asynchronous boundary. It is not a live service,
deployment, or promotion decision.

## Enforced boundary

`PreparedPolicyAsyncShadowBoundary.execute()` evaluates and verifies the exact screened
baseline. A sampled request produces an immutable envelope containing only the four fields
needed for semantic replay: case identity, variable count, expression, and frozen truth
bits. The envelope, exact baseline artifact, verified context, and prepared policy are bound
by SHA-256 identities.

The envelope remains staged after `execute()` returns. The worker cannot receive it until
`acknowledge_delivery()` is called. Queue capacity is reserved before staging, and a full
queue drops only shadow work with a recorded `queue_full` disposition. The exact baseline
continues to be served without waiting for queue availability.

The boundary records zero candidate results served, zero production writes, zero shadow
promotions, and zero production promotions. Candidate exceptions, refusals, source changes,
and exact-but-nonbest artifacts are contained in observation records.

## Fail-closed controls

Ten independently replayed control groups passed:

1. no candidate observation was possible before delivery acknowledgement;
2. caller mutation after `execute()` could not change the frozen queued request;
3. bounded queue saturation dropped shadow work without blocking or changing the response;
4. deterministic sampling selected exactly the intended request indices;
5. an injected candidate exception was contained off path;
6. an injected candidate refusal was contained off path;
7. an exact but nonbest candidate was recorded as a divergence and never served;
8. an incorrect prepared-context binding was refused;
9. a policy source changed after preparation produced a contained worker error and a
   refused lifecycle audit; and
10. bounded close drained staged work, stopped the worker, and refused late requests.

## Counterbalanced measurement

The run retained the unchanged 48-case C27 natural Yosys corpus, C27/C22 prepared policies,
and C31/C32 evidence. Sixteen blocks counterbalanced four widths and four methods:

- exact baseline with shadow disabled;
- C32 synchronous full shadow;
- C33 asynchronous full shadow with deferred delivery acknowledgement; and
- C33 asynchronous quarter sampling with deferred delivery acknowledgement.

| Measurement | Result |
|---|---:|
| Batches | 256 |
| Counterbalanced four-method groups | 64 |
| Exact baseline requests served | 2,048 |
| Synchronous observations | 512 |
| Asynchronous full observations | 512 |
| Asynchronous quarter-sampled observations | 128 |
| Candidate observations before acknowledgement | 0 |
| Candidate divergences | 0 |
| Candidate results served | 0 |
| Production writes | 0 |

Aggregate serving-path ratios relative to shadow disabled were:

| Method | Serving ratio | Observation coverage |
|---|---:|---:|
| C32 synchronous full shadow | 2.040x | 100% |
| C33 asynchronous full shadow | 1.038x | 100% |
| C33 asynchronous quarter sampling | 0.996x | 25% |

The full asynchronous envelope-copy plus staging overhead had a 40.7 microsecond median,
80.3 microsecond p95, and 461.4 microsecond maximum. Its worst per-width serving ratio was
1.1335x at n=4, below the preregistered 1.20x width ceiling. The aggregate 1.0382x ratio
passed the 1.10x ceiling and was substantially below synchronous shadowing.

The aggregate full-shadow baseline-only ratio was 1.0227x. Since the observer was released
only after the timed responses, candidate computation itself was outside the serving path;
the remaining cost is request copying, hashing, bounded staging, and measurement noise.

## Decision and next work

The local C33 exact-containment and timing gates pass. The result establishes a usable local
shadow boundary and removes synchronous candidate work as the immediate bottleneck. It does
not authorize production deployment or candidate serving, and the timing result has not yet
been repeated on a second machine.

The strongest next research phase is C34: use larger natural workloads to locate genuine
end-to-end headroom before adding more policy or serving machinery. Compare exact CM/GF(2)
paths with task-matched plain/flattened CSE, packed operations, ABC/AIG, CUDD/BDD, and SAT
controls. Separate construction, equivalence, decomposition, and repeated-query contracts;
do not compare methods that return different outputs. Resume learned ranking only where an
exact candidate first demonstrates enough end-to-end savings to pay for recognition.

## Evidence

- Run: `runs/c33-async-shadow-windows-20260901-001/`
- Results: `runs/c33-async-shadow-windows-20260901-001/results.json`
- Independent verification:
  `runs/c33-async-shadow-windows-20260901-001/independent_verification.json`
- Functional controls:
  `runs/c33-async-shadow-windows-20260901-001/functional_controls.json`
- Boundary: `../../cmbench/recognition/gf2_async_shadow_boundary.py`
- Experiment: `../../cmbench/comparative/gf2_async_shadow_experiment.py`
