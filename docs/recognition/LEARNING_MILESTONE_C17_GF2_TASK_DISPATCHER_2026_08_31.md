# Learning Milestone C17: exact CM/GF(2) task dispatcher

**Date:** 2026-08-31  
**Status:** locally measured and independently replayed; production promotion refused

## What was implemented

C17 adds a strict decomposition-task contract and a frozen, platform-bound dispatcher for the
two exact C15/C16 arms. Admitted identity-order tasks use exhaustive materialization at
`n <= 3` and the screened exact tail at `n > 3`. Platform mismatch abstains to exhaustive,
the global advice-off switch selects exhaustive, and unsupported tasks are refused. Every
returned artifact is reconstructed and checked against the source truth-vector digest.

The dispatcher is deterministic. It contains no trained weights and never predicts truth
values. Its only advice is which exact implementation should compute the same bounded best
artifact.

## Evidence contract

The local engineering run reused the frozen 40-case C16 Yosys-derived corpus. This is useful
post-hoc dispatcher evidence, but it is **not** independent transfer evidence. The policy was
frozen before timing. Four arms were measured for two balanced rounds: direct exhaustive,
direct screened, C17 selected, and C17 advice-off. The functional phase also compared the
exhaustive and screened best identities as the shadow proof.

An independent verifier checked five source and seven artifact fingerprints, replayed all 40
functional cases, checked all 320 timing rows, and recomputed the summary. There were zero
semantic, artifact, policy, or shadow mismatches.

## Local results

| Measure | Result |
|---|---:|
| C17 selected vs direct exhaustive, aggregate whole path | **3.8310x** |
| Direct screened vs direct exhaustive | **3.8634x** |
| Advice-off vs direct exhaustive | **0.9986x** |
| Per-case median C17 speedup | **3.6536x** |
| Per-case 5th-percentile slow tail | **0.7693x** |
| Minimum case (`n=2`) | **0.5973x** |

The aggregate, exactness, and advice-off gates passed. The predeclared 1.20x slow-tail and
0.97x minimum-case gates failed. The analytical `n <= 3` bypass avoided screening, but the
dispatcher wrapper remained too expensive for the very smallest functions. The timeout of
the first three-round harness attempt is retained separately; the completed run changed only
the timing rounds from three to two and retained all cases, methods, functional checks, and
thresholds.

## Decision

Production promotion remains false. C17 proves that exact task selection and conservative
fallback work, and it preserves the large-case aggregate benefit, but the current dispatch
boundary is not a no-regret rule. C18 should freeze independent VTR/LogikBench-derived cones,
measure the same policy without refitting, and test a true direct bypass that avoids wrapper
construction for tiny tasks.

## Evidence

- Run: `docs/recognition/runs/c17-gf2-task-dispatcher-windows-20260831-001`
- Independent verification: `independent_verification.json` in the run directory
- Machine summary: `docs/recognition/learning_milestone_c17_gf2_task_dispatcher_results.json`

