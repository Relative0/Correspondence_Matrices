# CRSE Milestone D6: exact cache on actual feature-model revisions

Date: 2026-08-29

Retained run: `docs/recognition/runs/natural-revision-20260829-001`

Independent verification: `docs/recognition/verification/natural-revision-20260829-001.json` (`pass`)

## Natural revision contract

D6 reuses the previously audited feature-model campaign: 20 admitted adjacent
transitions from seven real configuration histories, producing 120 bounded
conditioned relations at widths 8, 12, and 16. The source artifact checksums,
container identity, source commit, case IDs, shared named-feature domains,
conditioned CNFs, and sealed packed-relation digests are checked before timing.

A cache hit requires the stable case ID, matching source digest, and exact
canonical source bytes. The bytes cover the feature domain, width, and
conditioned CNF. Output equality is measured only as an oracle statistic and is
never used as a cache key.

Three arms begin from the conditioned CNF:

| Arm | Work charged |
| --- | --- |
| Direct CNF | Exact packed evaluation of both revision sources |
| Fresh CM | CNF-to-expression lowering, CM compilation, and packed extraction for both sources |
| Exact revision cache | Exact identity for both sources; lower, compile, and extract every miss |

The relations are bounded differences under a joint satisfying context and
shared named features. They are not whole-model equivalence results.

## Results

| Arm | Median charged time | Speed versus direct CNF |
| --- | ---: | ---: |
| Direct CNF | 696.078 ms | 1.000x |
| Fresh CM | 7,725.084 ms | 0.090x |
| Exact revision cache | 7,612.146 ms | 0.091x |

The exact cache was **1.015x** faster than fresh CM reconstruction, but the
direct CNF evaluator was about **10.94x** faster than the cached CM path. Exact
identity itself cost only 3.089 ms; the limited improvement arose because the
41 identical-source cases were inexpensive CM cases and removed only about
121 ms of median compilation.

## Identity boundary

- 41/120 later sources were exact safe cache hits.
- 79/120 later sources changed and were invalidated.
- 117/120 packed relations happened to remain equal.
- 76 equal-output cases had changed source bytes and were correctly refused as
  cache hits.
- Three cases had changed packed relations.

The unsafe semantic-only group is the key control: relation equality after the
fact cannot safely authorize skipping the computation that establishes it.

## Verification and decision

The independent verifier rehashed all seven source artifacts, reconstructed all
120 exact relations, reproduced the 41/79 hit/invalidation split, checked all
nine timing rows, and reported zero mismatches.

R09's generated-history limitation is closed for this bounded configuration
task. Profitability is not: exact reuse barely helped fresh CM and remained far
behind the direct representation-specific baseline. No CM-cache promotion
follows from this result.
