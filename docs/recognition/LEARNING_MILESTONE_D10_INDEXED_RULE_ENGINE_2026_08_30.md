# Milestone D10/R03-R05: indexed proved-rule engine

Date: 2026-08-30  
Status: implemented, measured, and independently verified; exact infrastructure accepted; production promotion refused

## What was implemented

D10 adds an inert four-rule proof pack and a fixed executable matcher for:

- mux/Shannon contraction;
- shared-enable comparator slices;
- three-input adder carry/majority; and
- repeated arithmetic XOR cancellation.

The pack contains 56 exhaustive Boolean truth rows. Loading reproduces every
row and hash before compilation. The executable path pre-indexes rules by root
operator, arity, shallow structural digest, and bounded support. A cheap screen
can bypass UID construction and matching when no indexed site is eligible.
Every accepted application must strictly decrease the canonical structurally
shared operator count, so save/reload cannot change the termination measure.
Priority, conflicts, application provenance, and per-rule counts are explicit.

The changed-cone cache binds the complete canonical source DAG, rule-pack hash,
and variable count. The frozen probe exercised cold fill, warm reuse, source
change, removal, addition, revert, and serialized reload. It recorded 8/8 warm
hits, one source invalidation, one removal invalidation, one revert invalidation,
and 8/8 reload hits, with exact reconstruction throughout.

## Frozen workload and correction

The retained run is
[`d10-rule-engine-windows-20260830-002`](runs/d10-rule-engine-windows-20260830-002).
It contains 16 positive source-backed compositions and 14 independently authored
raw Yosys-bench controls verified to contain no eligible rule. The positive
cases deliberately wrap Yosys expressions in the four motifs; they do not
estimate natural motif frequency. Reuse counts are 1, 8, 32, and 128.

Run `001` is retained as superseded diagnostic evidence. Its initial assumption
that every selected raw cone was a no-op control was false: the matcher correctly
found natural carry shapes inside four arithmetic cones. Run `002` fixed the
control definition by admitting only matcher-audited rule-free raw cones. No
timing result from `001` is used for the decision.

Seven balanced rounds produced 1,050 complete-path rows. Every arm charges CSE
construction and repeated execution. The indexed and full-scan arms also charge
matching; the cache arm charges structural identity; the explicit-CM arm builds
and compares complete correspondence matrices at every proposal.

## Exactness and timing

The independent verifier replayed all 30 cases and all 1,050 measurement rows.
It found zero semantic mismatches and zero false matches in the 14 no-op controls.
The experiment made 217 explicit per-instance CM proof calls.

| Slice | Indexed vs no rewrite | Warm cache vs no rewrite | Per-instance CM vs no rewrite |
| --- | ---: | ---: | ---: |
| All 30 cases | 0.2747x | 0.7740x | 0.1315x |
| 16 motif cases | 0.2417x | 0.8248x | 0.1051x |
| 14 no-op controls | 0.4455x | 0.6601x | 0.4463x |
| 8 high-reuse motifs | 0.3116x | 0.8959x | 0.1417x |

The optimistic free per-case oracle had exactly 1.0000x headroom because no
indexed case beat no rewrite. The matcher is far cheaper than rebuilding an
explicit CM proof at each site, but neither is competitive with compiling the
unchanged expression directly through CSE on these small cones. The no-op screen
also costs too much relative to the tiny baseline.

The local promotion gate therefore failed. No Runpod resource was created and
cost was $0; repeating a result with no local oracle headroom would not add useful
evidence. The exact pack, cache, invalidation, and provenance contracts remain
useful research infrastructure, but the runtime path stays disabled.

## Limits and next use

This is a bounded source-backed composition study, not natural-frequency or
production evidence. A future rewrite study should first locate larger natural
cones where a proved contraction removes enough downstream work to create
measurable oracle headroom. It should retain the no-rewrite, full-scan,
per-instance-CM, advice-off, cache, and changed-version controls.
