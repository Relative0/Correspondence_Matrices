# Learning Milestone C19: cheap exact CM/GF(2) work policy

**Date:** 2026-08-31  
**Status:** phase-separated exact policy confirmation passed; production promotion refused

## Frozen LogikBench corpus

C19 reused the previously audited LogikBench RTL-to-BLIF conversion. It did not rerun synthesis
or incur new cloud cost. The corpus freezer admitted 96 small combinational cones from 51 converted
BLIF files, excluded seven truth vectors already present in earlier recognition corpora and 16
within-C19 duplicates, and assigned complete source clusters to development, validation, or
confirmation before timing.

| Split | Cases | Source clusters |
|---|---:|---:|
| Development | 48 | 29 |
| Validation | 24 | 13 |
| Confirmation | 24 | 9 |

An independent source verifier replayed all 96 cones from the frozen BLIF files. It reproduced the
support metadata and truth vectors, found no prior-corpus overlap, and confirmed that no source
cluster crossed a split. The confirmation policy could not be refit.

## What was fitted

Both available arms are exact CM/GF(2) computations: exhaustive decomposition and screened exact
decomposition. C19 learned only which exact arm to call. It did not learn truth values, approximate
a CM, or train a neural network.

The development phase measured both direct arms. A deterministic cost-tree fitter considered five
cheap integer features: live-variable count, truth-table population count, adjacent transitions,
half-table delta, and edge imbalance. Validation compared always-exhaustive, fixed `n<=3` and
`n<=4` rules, and learned depth-one and depth-two candidates. The predeclared eligibility gate was
at least 1.0x aggregate speedup and at least 0.97x on every validation case.

The selected candidate was named `learned_stump`, but the fitted tree collapsed to a single leaf:
always call screened exact CM. That distinction matters: the result is a learned cost decision,
not a learned mathematical answer, and the final policy contains no split or pattern recognizer.
The serialized policy was frozen before any confirmation measurement existed.

## Sealed confirmation

The 24 confirmation cases contain four `n=3`, eight `n=4`, four `n=5`, and eight `n=6` cones.
Five balanced rounds produced 720 confirmation rows across six methods.

| Method | Aggregate vs exhaustive | Median case | Minimum case | Maximum regret vs best direct arm |
|---|---:|---:|---:|---:|
| Direct screened | **2.7931x** | **1.9029x** | **1.1065x** | **1.0000x** |
| C19 selected | **2.7686x** | **1.8219x** | **0.9717x** | **1.1386x** |
| C17 wrapper | 2.7346x | 1.8088x | 0.9199x | 1.7846x |
| Fixed `n<=3` exhaustive | 2.7462x | 1.8945x | 0.9663x | 1.6330x |
| Fixed `n<=4` exhaustive | 2.6749x | 1.4665x | 0.9387x | 1.9439x |

All arms and policies returned the same best exact artifact as exhaustive CM, and every artifact
reconstructed its source truth vector. C19 passed its confirmation gate: 2.7686x aggregate and
0.9717x minimum per-case speedup.

The selected leaf still pays generic feature extraction and tree-evaluation overhead, which is why
it trails a direct screened call and has one case close to the no-regret floor. A policy compiler can
constant-fold this leaf into a direct screened call. Such a change must be measured on a new or
clearly retrospective evaluation slice rather than relabeling this sealed confirmation.

## Independent verification and decision

The independent verifier checked nine artifact and three source fingerprints, replayed all 96
functions, checked 480 development, 840 validation, and 720 confirmation timing rows, rebuilt the
trees and frozen policy from pre-confirmation data, and recomputed both timing summaries. It found
zero semantic or artifact mismatches.

C19 closes the immediate fresh-source small-case profitability question on this one Windows
machine, but it does not establish production readiness. The selected rule is structurally trivial,
the confirmation covers one source family and one machine, C18/VTR previously contained a slower
screened tail, and no production integration has been enabled. Production promotion remains false.

## Evidence

- Frozen dataset: `docs/recognition/c19_logikbench_small_cone_dataset.json`
- Source inventory: `docs/recognition/c19_logikbench_small_cone_inventory.json`
- Source replay: `docs/recognition/c19_logikbench_small_cone_verification.json`
- Run: `docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001`
- Frozen policy: `docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json`
- Independent verification: `docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/independent_verification.json`
- Machine summary: `docs/recognition/learning_milestone_c19_cheap_gf2_work_policy_results.json`

