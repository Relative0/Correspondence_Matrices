# Learning milestone C32: prepared-policy shadow boundary

**Date:** 2026-09-01
**Status:** local shadow-boundary implementation and independent verification complete
**Training or policy refit:** none
**Production writes:** none
**Shadow/production promotion:** false / false

## Purpose

C31 prospectively reproduced the unchanged C30 prepared-policy result on Windows and a
physical Linux machine, making the candidate eligible for a separate shadow review. C32
implements the boundary required for that review without promoting the candidate. The
exact screened baseline remains the only result that can be served. The prepared-policy
candidate is opt-in, observational, and structurally unable to replace the baseline.

## Boundary contract

Each request executes and verifies the exact screened baseline first. With shadow disabled,
no candidate session or candidate query runs. With shadow enabled, the frozen C30 prepared
context executes after the baseline and the boundary records its artifact identity, selected
arm, timing, refusal, or error. The returned artifact always comes from the baseline.

The boundary records zero candidate results served, zero production writes, zero shadow
promotions, and zero production promotions. It validates the prepared-context digest at
construction and checks the bound policy-source hashes again at lifecycle close.

## Fail-closed controls

Six independently checked controls passed:

1. shadow-disabled execution performed no candidate work and served the exact baseline;
2. an injected candidate exception was contained while the exact baseline was served;
3. an injected candidate refusal was contained while the exact baseline was served;
4. an exact but nonbest candidate artifact was detected as a divergence and was not served;
5. an incorrect prepared-context binding was refused; and
6. a policy source changed after preparation was refused by the lifecycle audit.

These controls distinguish semantic exactness from required best-artifact identity. Even an
alternate artifact that reconstructs the same truth table is treated as a shadow divergence
when it does not match the baseline artifact contract.

## Balanced measurement

The local run used the unchanged 48-case C27 corpus and frozen C27/C22 policies. Sixteen
counterbalanced blocks covered n=3/4/5/6 and alternated shadow-disabled and shadow-enabled
order. The independent verifier recomputed the schedule, source and input hashes, exhaustive
oracles, compact request records, controls, and summary.

| Measurement | Result |
|---|---:|
| Batches | 128 |
| Paired batches | 64 |
| Exact baseline requests served | 1,024 |
| Shadow candidate observations | 512 |
| Candidate divergences | 0 |
| Candidate results served | 0 |
| Production writes | 0 |

The enabled boundary's synchronous total time was **2.045x** the disabled boundary. The
baseline computation itself was stable: enabled/disabled aggregate baseline latency was
**1.003x**. The extra time is therefore the expected candidate work rather than measurable
damage to the baseline algorithm. This timing is observational and is not a promotion gate.
It shows that any later shadow rollout should move candidate work off the response-critical
path or use bounded sampling rather than synchronously doubling request work.

## Decision

The local C32 shadow-review gate passes: the baseline remained exact, all valid candidate
observations matched, injected failures and divergence were contained, and no candidate
result or production write escaped the boundary. This validates the local implementation;
it does not authorize a live shadow deployment or production promotion.

## Evidence

- Run: `runs/c32-prepared-shadow-windows-20260901-001/`
- Results: `runs/c32-prepared-shadow-windows-20260901-001/results.json`
- Independent verification:
  `runs/c32-prepared-shadow-windows-20260901-001/independent_verification.json`
- Functional controls:
  `runs/c32-prepared-shadow-windows-20260901-001/functional_controls.json`
- Boundary implementation: `../../cmbench/recognition/gf2_prepared_shadow_boundary.py`
- Experiment: `../../cmbench/comparative/gf2_prepared_shadow_experiment.py`
