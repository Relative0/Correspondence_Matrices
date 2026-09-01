# Learning Milestone C18: independent exact CM/GF(2) dispatcher transfer

**Date:** 2026-08-31  
**Status:** independent-source exact transfer verified; timing scout complete; promotion refused

## Frozen source corpus

C18 moved outside the Yosys generator family used for C15-C17. A pinned local VTR checkout
provided already materialized BLIF circuits. The freeze admitted combinational cones with 3-10
live variables and at most 256 source nodes, capped each circuit at eight cones, and selected by
a stable SHA-256 order. Four C16 truth overlaps and three within-C18 duplicates were excluded.

The final evaluation-only slice contains **73 cones from 10 VTR circuits**. A source verifier
reparsed every original BLIF file and reproduced every support, topology record, packed truth
vector, and digest with zero mismatches. The C17 policy was not refit.

LogikBench is inventoried as a later RTL phase. It was not mixed into this result because its
synthesis command, Yosys version, generated BLIF, per-benchmark license, and equivalence proof
still need a separate frozen transform.

## Exact transfer and timing

The unchanged platform-bound C17 policy selected screened exact analysis for 72 cases and the
tiny-case exhaustive bypass for one case. Advice-off selected exhaustive for all 73. Exhaustive
and screened best artifact identities matched on every cone; all returned artifacts reconstructed
the original truth vectors.

The single-round transfer scout charged BLIF packed-truth construction, the complete dispatcher
call boundary, analysis, and exact artifact checks.

| Measure | Result |
|---|---:|
| C17 selected vs direct exhaustive, aggregate | **8.3782x** |
| Direct screened vs direct exhaustive | **8.1085x** |
| Advice-off vs direct exhaustive | **1.0015x** |
| Per-case median C17 speedup | **5.3777x** |
| Per-case 5th-percentile slow tail | **1.3236x** |
| Minimum case | **0.6207x** |

The minimum was an `n=4` DES cone. The lone `n=3` case measured 0.8213x. The ten `n=4` cases
ranged from 0.6207x to 3.144x, so a blanket `n<=4` exhaustive rule is not justified.

## Verification and decision

The independent run verifier checked the frozen dataset and policy digests, source and artifact
fingerprints, replayed all 73 exact functional cases, checked all 292 measurement rows, and
recomputed the summary. It reported zero semantic or artifact mismatches.

This is a strong exact cross-family result and a promising aggregate timing result. It remains a
single-round, one-machine scout, and the predeclared minimum-case no-regret gate failed. Production
promotion is false. The next dispatcher milestone should add a genuinely cheap work estimate or
direct call-site bypass that can distinguish the mixed `n=4` cases, then repeat this frozen slice
for multiple rounds and on a second machine without fitting on C18.

## Evidence

- Freeze plan: `docs/recognition/C18_INDEPENDENT_CORPUS_FREEZE_PLAN_2026_08_31.md`
- Source inventory: `docs/recognition/c18_independent_corpus_source_inventory.json`
- Frozen dataset: `docs/recognition/c18_independent_cone_dataset.json`
- Source replay: `docs/recognition/c18_independent_corpus_verification.json`
- Run: `docs/recognition/runs/c18-independent-gf2-transfer-windows-20260831-001`
- Machine summary: `docs/recognition/learning_milestone_c18_independent_gf2_transfer_results.json`

