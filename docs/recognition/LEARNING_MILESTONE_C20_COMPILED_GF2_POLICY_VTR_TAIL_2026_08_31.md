# Learning Milestone C20: compiled exact policy on the VTR slow tail

**Date:** 2026-08-31  
**Status:** retrospective repeated-tail gate passed; production promotion refused

## Implementation

C20 added a compiler for frozen C19 exact-arm policies. The compiler first validates the policy's
canonical digest and tree contract, converts the tree to an immutable tuple program, and
constant-folds a leaf to a direct exact-arm selector. The frozen C19 policy is a screened leaf, so
its compiled form does not calculate population count, transitions, half-table delta, imbalance,
or any other truth feature.

This is a cost-policy compiler. It does not learn truth values or replace CM/GF(2) analysis. Its
only possible outputs are the two exact arms, and this policy always invokes screened exact CM.

## Retrospective VTR control

The C18 scout contained one `n=3` and ten `n=4` VTR cones. Its single timing round had reported a
0.7156x direct-screened minimum and a 0.6207x wrapped minimum. C20 retained those exact 11 cases,
did not refit the C19 policy, and ran nine balanced randomized rounds across four methods:
direct exhaustive, direct screened, generic C19 evaluation, and compiled C19 evaluation.

| Method | Aggregate vs exhaustive | Median case | Minimum case | Maximum regret vs best direct arm |
|---|---:|---:|---:|---:|
| Direct screened | **1.7798x** | **1.8570x** | **1.4711x** | **1.0000x** |
| Compiled C19 | **1.7600x** | **1.8102x** | **1.4631x** | **1.0360x** |
| Generic C19 | 1.7467x | 1.8095x | 1.4434x | 1.0715x |

The compiled selector added 1.126% aggregate time over a direct screened call; generic feature/tree
evaluation added 1.893%. Constant folding therefore removed measurable policy overhead, although
the exact screened analysis still dominates total time.

Most significantly, the prior slow case was not reproduced. Every direct-screened and compiled
per-case median was faster than exhaustive by at least 1.47x. The earlier one-round outlier should
now be treated as an unstable timing observation, not an established algorithmic regression.

## Verification and decision

The independent verifier checked the frozen C18 dataset and C19 policy fingerprints, required the
C18 source replay, replayed all 11 exact functions, checked all 396 timing rows, and recomputed the
summary. It found zero semantic or artifact mismatches.

The repeated retrospective research gate passed. This improves confidence in the cheap exact arm
and removes the previously reported local small-support blocker, but it is not fresh confirmation:
C18 had already been inspected, the run remains on the same Windows machine, and no production
call site was changed. Production promotion remains false. The strongest next evidence is a
second-machine run with the already frozen policy and a new source-cluster confirmation slice.

## Failed attempt retained

Run `c20-compiled-policy-vtr-tail-windows-20260831-001` stopped before timing because it expected a
LogikBench-style `cluster_id` field that the C18 schema does not contain. The corrected run uses
the frozen C18 `source_file` field and has run ID `-002`; no result is claimed from `-001`.

## Evidence

- Compiler: `cmbench/recognition/gf2_work_policy_compiler.py`
- Frozen C18 dataset: `docs/recognition/c18_independent_cone_dataset.json`
- Frozen C19 policy: `docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json`
- Verified run: `docs/recognition/runs/c20-compiled-policy-vtr-tail-windows-20260831-002`
- Independent verification: `docs/recognition/runs/c20-compiled-policy-vtr-tail-windows-20260831-002/independent_verification.json`
- Machine summary: `docs/recognition/learning_milestone_c20_compiled_gf2_policy_vtr_tail_results.json`

