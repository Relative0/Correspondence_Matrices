# CRSE Milestone D5: proved-rule profitability on natural EPFL cones

Date: 2026-08-29

Retained run: `docs/recognition/runs/natural-rule-20260829-001`

Independent verification: `docs/recognition/verification/natural-rule-20260829-001.json` (`pass`)

## Sealed natural contract

D5 freezes the D4 gate and evaluates 32 natural EPFL AND/INV cones from 15
circuits. Each cone has equal semantic and syntactic support from 9 through 12
variables. Milestones C and D selected only support-8 records, so this slice has
no case overlap and is not used for training.

The source corpus, upstream commit, circuit hashes, expression structural hash,
and frozen truth digest are checked before timing. Three sessions repeat the
same natural cones. This measures warm reuse, but it is not described as a
changed circuit history.

Every arm pays for its applicable gate, identity or matching, rewrite, flattened
CSE construction, and 1, 8, 32, or 128 packed executions. No-rewrite CSE remains
the primary comparator.

## Results

| Arm | Median three-session time | Speed versus no rewrite |
| --- | ---: | ---: |
| No rewrite | 182.454 ms | 1.000x |
| Fresh pack | 268.757 ms | 0.679x |
| Cached pack | 207.467 ms | 0.879x |
| Gated cache | 177.141 ms | **1.030x** |

The cold first session remained slower:

| Session | Gate speed versus no rewrite | Gate speed versus fresh pack |
| --- | ---: | ---: |
| Cold session 1 | 0.834x | 1.236x |
| Warm session 2 | 1.156x | 1.730x |
| Warm session 3 | 1.168x | 1.734x |

The reuse strata explain the aggregate:

| Executions | Fresh pack | Cached pack | Gated cache |
| ---: | ---: | ---: | ---: |
| 1 | 0.238x | 0.450x | 0.978x |
| 8 | 0.346x | 0.591x | 0.967x |
| 32 | 0.583x | 0.806x | 0.795x |
| 128 | 1.004x | 1.164x | **1.167x** |

The pack found 18 XOR applications in nine cases and 433 De Morgan OR
applications in 31 cases. The factoring rule had zero applications because the
raw EPFL corpus uses an AND/INV language and the current matcher performs one
bottom-up pass rather than rematching newly lowered OR nodes.

The optimistic cached oracle was **1.121x**, so the natural workload has real but
limited scheduling headroom. This contrasts with D4's 1.017x generated oracle.

## Verification and decision

- All 36 session/arm/round cells completed with zero semantic mismatches.
- The independent verifier reproduced the sealed 32-case selection, 16 proof
  rows, all timings/accounting identities, and 451 natural rule applications.
- The achieved 1.030x sequence gain is small and machine-specific.
- The gate was frozen from D4; the 128-use result was observed here and must not
  be tuned and relabeled as confirmation on the same data.

No production promotion follows from one local machine, one natural corpus, and
identical sessions. The next confirmatory test should predeclare a high-reuse
policy, use another natural source or Linux replication, include tail latency,
and keep cold startup plus no rewrite as controls. Actual related revisions are
still required for the R09 confirmation.
