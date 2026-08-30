# CRSE Milestone D4: profitability-gated proved rules

Date: 2026-08-29

Retained run: `docs/recognition/runs/rule-profitability-20260829-002`

Independent verification: `docs/recognition/verification/rule-profitability-20260829-002.json` (`pass`)

## Why this differs from the website kernel results

The website's headline `0.888` value is an empirical **kernel-only** CM/plain-CSE
ratio on 192 local synthetic formulas. The matched external EPFL ratio is
`0.927`; five Linux synthetic replications range from about `0.877` to `0.888`.
The headline `1.0038` CM/CSE-flat value is likewise kernel-only on the local
synthetic cohort. Its matched EPFL value is `0.9998`, with its interval spanning
parity.

Those experiments compile first and time exact packed execution. They also
report the other side of the contract: CM preparation was about 4.1-4.4 times
the comparator preparation cost. Median finite break-even was 78 executions on
synthetic formulas, 105 against plain CSE on EPFL, and 174.5 against CSE-flat on
EPFL; some cases never broke even.

D3 instead charged structural identity, cache lookup or matching, rewriting,
CSE construction, and one execution. Its loss to no-rewrite CSE was therefore a
preparation-dominated full-pipeline result. Neither measurement is theoretical.
They measure different boundaries and reuse counts.

## Implementation

D4 adds:

- `boolean-common-factor/v1`, proving
  `(A AND B) OR (A AND C) = A AND (B OR C)` over eight valuations;
- a three-rule inert pack with 16 total exhaustive proof rows;
- fixed overlap priority and a strict operator-count-decrease requirement;
- a deterministic gate using task, expected reuse, and upstream node count only;
- exact cache serialization and verified reload;
- additions, removals, modifications, and exact reverts;
- forced digest-collision, pack-change, capacity, and stale-entry controls.

The gate never certifies a rewrite. A skipped cone executes the unchanged exact
expression. An eligible cone still requires exact source identity and a matcher
compiled from the proved pack.

## Generated result

The retained run has 32 cones, four related versions, three timing rounds, and
reuse counts of 1, 8, 32, and 128.

| Arm | Median four-version time | Speed versus no rewrite |
| --- | ---: | ---: |
| No rewrite | 52.815 ms | 1.000x |
| Fresh pack | 80.942 ms | 0.653x |
| Cached pack | 67.840 ms | 0.779x |
| Gated cache | 59.250 ms | 0.891x |

Gating was **1.366x faster than fresh matching** and about **1.145x faster than
ungated caching**, but remained slower than no rewrite. The optimistic zero-cost
cached oracle offered only **1.017x** headroom. Training a selector on this
generated cohort would therefore be unjustified.

All 48 measurement cells completed with zero mismatches. The independent
verifier reproduced 16 proof rows, all four versions, and all cache accounting.
Serialized reload hit 3/3 entries. Forced collisions, capacity overflow, and
pack changes all refused or invalidated exactly.

## Decision

The mechanism passes its safety and hardening criteria. It does not pass the
generated profitability criterion and is not promoted. The next experiment uses
the unchanged gate on a sealed natural source where larger packed kernels and
high reuse may provide enough downstream work to amortize preparation.
