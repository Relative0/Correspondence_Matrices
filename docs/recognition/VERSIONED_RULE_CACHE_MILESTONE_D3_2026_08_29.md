# CRSE Milestone D3: versioned proved-rule cache

Date: 2026-08-29

Retained run: `docs/recognition/runs/versioned-rule-20260829-002`

Independent verification: `docs/recognition/verification/versioned-rule-20260829-002.json` (`pass`)

## What was implemented

Milestone D3 extends the fixed proved-rule boundary from one rule to a small
two-rule pack:

1. `aig-xor-dnf/v1`: the specific AIG XOR macro from D2.
2. `aig-demorgan-or/v1`: `NOT(NOT A AND NOT B) -> A OR B`.

Each rule is proved over all four values of the Boolean metavariables `A` and
`B`, for eight retained proof rows. The general OR shape intentionally also
matches the outer shape of the specific XOR macro. The pack records a fixed
priority, with XOR first, and the compiled matcher reports that overlap rather
than allowing file order or learned confidence to decide it.

The artifact remains inert, strictly validated JSON. It contains patterns,
truth rows, rule order, and hashes, but cannot select code beyond the two fixed
built-in implementations.

## Exact structural cache

The cache operates on stable named cones. A hit requires all three of:

- the same proved-pack hash;
- the same SHA-256 of the canonical v2 source DAG;
- byte-for-byte equality of that canonical source DAG.

Object identity is deliberately insufficient: every version is serialized and
reloaded into new Python objects. If the source or pack identity changes, only
that cone entry is invalidated and recomputed. Removed cone IDs have an explicit
invalidation path. The cache stores only the proved rewritten expression and
its deterministic accounting, never an unverified learned answer.

## Versioned comparison

The generated workload has 32 structurally distinct named cones. Each cone has
one XOR and one De Morgan OR application in a shared DAG. Versions `v2` and `v3`
each change exactly four different cones. Each timed arm rebuilds and executes
CSE for all 32 cones; scalar enumeration audits the complete eight-variable
outputs outside the timer.

| Version | Changed | Cache hits | Invalidations | Reused applications | Cached total | Fresh pack total | Cache speedup | Speed vs no rewrite |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 | 0 | 0 | 0 | 0 | 17.243 ms | 14.535 ms | 0.843x | 0.197x |
| v2 | 4 | 28 | 4 | 56 | 6.861 ms | 14.293 ms | 2.083x | 0.495x |
| v3 | 4 | 28 | 4 | 56 | 6.799 ms | 14.324 ms | 2.107x | 0.498x |

Across the complete three-version sequence, the median times were:

- no rewrite: 10.328 ms;
- fresh rule-pack matching: 43.296 ms;
- persistent cached rule pack: 31.340 ms.

Caching was **1.382x faster than fresh rematching** across the full sequence.
For the two changed versions after the cold population, it was about **2.1x
faster**. Exact accounting matched the declared changes: 28 hits and four
invalidations on each transition, with zero stale results.

The cache still did not beat skipping rewrites. No-rewrite CSE was about 3.03x
faster over the full sequence. Canonical identity construction, changed-cone
matching, and cache management still cost more than the small downstream CSE
saving. The pack and cache are therefore not promoted into production routing.

## Verification and limits

- 27 timed version/arm/round cells completed with zero semantic mismatches.
- The independent verifier reproduced eight proof rows and all 96 retained
  cone expressions, checked all 27 measurement rows, and verified eight exact
  changed-cone invalidations.
- The run uses three rounds on one machine and generated related DAGs. The 32
  cones are structurally distinct but are mechanism fixtures, not independent
  natural hardware histories.
- There is no learned rule, learned CM, or learned cache decision in this slice.

## Recommended next experiment

Keep the exact pack/cache mechanism, but add a cheap predeclared scheduler that
can skip canonical cache lookup when the expected downstream saving is too
small. Measure it first on a frozen generated profitability split, then on
actual related circuit revisions or another provenance-reviewed versioned
source. Compare skip, fresh matching, cached matching, and no rewrite without
tuning on the confirmation histories.
