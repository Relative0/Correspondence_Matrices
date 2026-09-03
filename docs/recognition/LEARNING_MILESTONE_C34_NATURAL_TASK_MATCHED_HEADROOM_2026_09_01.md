# Learning milestone C34: natural task-matched exact headroom adjudication

**Date:** 2026-09-01
**Status:** local implementation, measurement, and independent verification complete; both headroom gates fail
**Training or policy refit:** none
**RunPod:** not used
**Production write or promotion:** none

## Purpose and evidence boundary

C30-C33 made prepared exact-policy observation safe and reduced full asynchronous shadow
overhead to 1.038x the disabled serving path. C34 asks the prior scientific question:
does any exact method surface have enough task-matched advantage to pay for recognition,
verification, dispatch, and observation?

C34 uses the full-width C23-v1 Yosys dataset: 48 natural generated-circuit expressions
from eight pinned generator families spanning 3-10 live variables. This source had already
been inspected during C23 and its first 64-partition decomposition run was correctly marked
incomplete. C34 therefore labels it **reused natural width-extension evidence**, not fresh
confirmation. A new role manifest was frozen before C34 timing. All 48 cases enter the
complete-relation table; a deterministic source-identity rule selects 15 cases, one at
width 3 and two at every width 4-10, for complete decomposition. Selection uses no timing
or method result, and none of these cases is training or policy-selection data.

Independent corpus replay reconstructed all 48 expressions and truth vectors with zero
semantic or selection mismatches.

## Task contracts

### Complete relation

Every method starts from the same frozen expression-DAG document and delivers the same
canonical packed truth vector over the full declared variable order. Timed work includes
method-specific input decoding, representation construction, compilation/binding,
execution, canonical delivery, and cleanup. The external semantic oracle is outside the
comparative span.

The six exact methods are:

1. direct recursive AST bitset evaluation;
2. structural CSE without associative flattening;
3. sharing-aware flattened structural CSE;
4. CM-IR compilation and flattened bigint evaluation;
5. packed source-ANF construction and truth evaluation; and
6. expression-to-CNF plus a fresh CaDiCaL solver enumerating every original assignment.

CaDiCaL is included only because complete assignment enumeration delivers the same full
truth vector. SAT status or one witness would not satisfy this contract.

### Complete exact CM/GF(2) decomposition

Every method again starts from the frozen expression DAG, constructs the exact complete
truth vector, and returns the deterministic globally best exact CM/GF(2) artifact. C34
removes C23's earlier support-width ambiguity by enumerating the complete canonical A|B
partition universe: `2^(n-1)-1` partitions, from 3 at width 3 through 511 at width 10.

The three fixed input paths are flattened CSE, CM IR, and packed source ANF. Each then runs
the same screened exact completion over every partition, charges exact reconstruction and
artifact delivery, and is checked against an independently materialized exhaustive oracle.

## Backend eligibility

The installed pure-Python `dd.autoref` backend passed one exact functional truth-vector
probe at each width 3-10. Those diagnostic times are not ranked: C21/C23 had already shown
fresh single-query BDD cleanup to be dominated, so C34 predeclared exact width probes only.
The local CUDD binding and ABC/Yosys executables are unavailable. ABC/AIG also lacks a
frozen adapter delivering the complete packed-vector contract. SAT, BDD, or AIG proposals
alone are ineligible for the globally best decomposition table because a proposal is not
the requested exact artifact.

## Complete-relation results

The counterbalanced table contains 3,456 exact timed executions: 48 cases, six methods,
and twelve blocks. Direct AST bitset evaluation won every case and every width aggregate.

| Method | Sum of per-case median times | Relative to best fixed | Per-case wins |
|---|---:|---:|---:|
| Direct AST bitset | **6.687 ms** | **1.0000x** | **48** |
| Flattened CSE bigint | 11.472 ms | 0.5829x | 0 |
| Plain CSE bigint | 11.598 ms | 0.5765x | 0 |
| CM IR bigint | 29.399 ms | 0.2274x | 0 |
| Packed source ANF | 45.726 ms | 0.1462x | 0 |
| CaDiCaL assignment enumeration | 150.819 ms | 0.0443x | 0 |

For this bounded one-shot full-vector task, CM IR is about 4.40x slower than the direct
exact baseline; flattened CSE is about 1.72x slower. The per-case timing oracle simply
chooses direct AST on all 48 cases, so it has zero raw headroom. Charging the frozen C30
prepared-dispatch median (43.1 microseconds) plus the C33 full-shadow enqueue p95
(80.3 microseconds) makes the budget-adjusted oracle ratio 0.5303x. No recognition or
learning opportunity exists on this surface.

## Complete-decomposition results

The decomposition table contains 270 exact timed executions: 15 cases, three methods, and
six blocks. All methods reconstruct the source truth vector and deliver the independently
computed global best artifact.

| Method | Sum of per-case median times | Relative to best fixed | Per-case wins |
|---|---:|---:|---:|
| Flattened CSE + complete screened GF(2) | **9.130 s** | **1.0000x** | **7** |
| CM IR + complete screened GF(2) | 9.479 s | 0.9631x | 4 |
| Packed source ANF + complete screened GF(2) | 10.148 s | 0.8996x | 4 |

The apparent case winners do not provide useful routing margin. The unattainable per-case
oracle is only **1.00350x** faster than the best fixed method. Its median per-case absolute
headroom is 12.4 microseconds, below the 123.4-microsecond charged budget; only one third
of cases cover that budget. The budget-adjusted oracle speedup is **1.00329x**, far below
the frozen 1.05 gate.

A post-hoc width rule is even weaker: 1.00227x raw and 1.00206x after the charged budget.
It is retrospective and is not a trained or promotable policy. Both C34 headroom gates
fail.

## Independent verification

The independent verifier:

- replayed all 48 expression/truth identities;
- recomputed all 15 global exhaustive decomposition oracles;
- regenerated both counterbalanced schedules;
- checked 3,456 complete-relation and 270 decomposition measurements;
- recomputed every complete partition universe and partition digest;
- independently recomputed both timing summaries;
- checked three source and fourteen artifact fingerprints; and
- retained zero semantic, oracle, measurement, or summary mismatches.

The functional controls refused wrong truth bindings, wrong required decomposition
artifacts, and task-contract mismatches. All eight BDD width probes were exact. No model was
trained or refit; no candidate result was served; no network, RunPod, production write, or
promotion occurred.

## Decision and recommended C35

C34 closes the immediate one-shot headroom question negatively. Full truth construction
has a single dominant cheap exact baseline, while complete GF(2) decomposition leaves only
about three tenths of one percent optimistic routing headroom. A second-machine timing run
or another timing classifier would not be a good use of resources for either surface.

The strongest next milestone is a **natural repeated-query lifecycle table**. Freeze exact
restriction, count, SAT/witness, and version-related query traces over wider natural
functions; compare fresh and resident direct/CSE/CM paths, compiled structures,
`dd.autoref`, native CUDD when available, and CaDiCaL only where each output contract
matches. Measure compile cost, query cost, persistence/reload, and break-even query count.
Train or route only if a fixed resident method shows fresh, held-out absolute headroom
larger than the full recognition and verification budget.

## Evidence

- Dataset role manifest: `docs/recognition/c34_natural_headroom_dataset.json`
- Dataset replay: `docs/recognition/c34_natural_headroom_dataset_verification.json`
- Local run: `docs/recognition/runs/c34-natural-headroom-windows-20260901-001`
- Independent run verification:
  `docs/recognition/runs/c34-natural-headroom-windows-20260901-001/independent_verification.json`
- Machine summary: `docs/recognition/learning_milestone_c34_natural_headroom_results.json`
