# CRSE Milestone D7: bounded multi-pass normalization

Date: 2026-08-29

Retained run: `docs/recognition/runs/natural-normalization-20260829-001`

Independent verification: `docs/recognition/verification/natural-normalization-20260829-001.json` (`pass`)

## Normalization contract

D7 reuses the sealed 32-cone D5 EPFL slice to test multi-pass mechanics at the
frozen high-reuse policy of 128 packed executions per cone. Because the cases
were already observed in D5, this is exploratory and is not labeled independent
confirmation.

The bounded normalizer records and charges a final no-op pass that establishes
the fixpoint. Every productive pass must strictly reduce expanded AST operator
occurrences. Exact repeated-state detection, an eight-pass limit, a 1,024 total
application limit, and refusal instead of returning a partial result enforce
termination. The fixed pack's declared XOR-over-OR priority remains active;
tests also exercise a mode that refuses any overlap.

Every arm pays flattened CSE construction and 128 packed executions:

| Arm | Median charged time | Speed versus no rewrite |
| --- | ---: | ---: |
| No rewrite | 1,076.156 ms | 1.000x |
| One pass | 1,024.558 ms | **1.050x** |
| Fixpoint | 1,336.725 ms | 0.805x |

The one-pass result is consistent with D5's observation that high reuse can
amortize matching. It is not a new-source or new-machine confirmation.

## Rule incidence and passes

The single pass applied 18 XOR and 433 De Morgan rules. Fixpoint normalization
found those same applications plus 18 common-factor contractions that become
visible only after De Morgan lowering. Of 32 cones, one needed no productive
pass, 26 needed one, and five needed two. The declared XOR/OR overlap occurred
18 times.

Despite smaller rewritten kernels, fixpoint was **0.766x** versus one pass. Its
413.886 ms normalization cost exceeded the combined CSE-build and kernel savings.

## Verification and decision

The independent verifier reproduced the sealed selection, all 16 rule proof
rows, 469 fixpoint applications, exact result identities, and nine measurement
rows with zero semantic mismatches.

Multi-pass rewriting is now exact, bounded, and capable of exposing a later
rule, but it is not profitable on this workload. Keep one pass as the candidate
high-reuse policy and do not promote fixpoint normalization. Linux or another
natural source is still required for confirmation.
