# CRSE Learning Milestone C4: direct-cut supervision and matched-pair ranking

Date: 2026-08-29  
Status: **complete, independently verified negative result**  
Production promotion: **no**

## Question

C3 showed that predicting ANF interaction edges independently was too brittle:
one incorrect edge could join otherwise correct components, and a minimum-cut
decoder often selected the wrong partition. C4 tests the recommended correction
without changing the frozen data:

1. supervise the complete canonical variable cut directly;
2. train against same-circuit positive/negative pairs;
3. compare a coarse structural pair ranker with graph proposals; and
4. charge graph construction, inference, and exact acceptance against exact ANF.

## Frozen data and design

C4 regenerates the C3 structure-matched dataset exactly: 94 positive/negative
pairs and 188 natural EPFL circuit cones. Training contains 48 pairs,
validation 12, test 16, and development-confirmatory evaluation 18. All pairs
stay inside one circuit and split, all have the same live-variable count, and
median node-count, depth, and edge-count differences are zero.

For every positive, the target is the canonical most-balanced exact partition.
The row side always contains `x0`, removing `A | B` versus `B | A` ambiguity.
The graph decoder enumerates every bounded nontrivial row side containing `x0`
and chooses the assignment with minimum mean direct-membership negative log
likelihood.

Three arms trained for 30 epochs under seeds 1049 and 1301, using the same pair
batches, Adam learning rate 0.003, and validation-only classification thresholds:

- `structural_pair_ranker`: 18 parameters, classification plus matched-pair
  margin loss; it has no learned partition and triggers full exact ANF proof;
- `direct_cut_gnn`: 80,651 parameters, classification plus direct cut loss;
- `cut_rank_gnn`: 80,651 parameters, classification, direct cut, and matched-pair
  margin losses.

The direct-cut loss weight is 0.75. Ranking weight and margin are both 0.50.
All model artifacts are inert, hash-checked float32 JSON.

## Results

| Model | Seed | Split | Proposal BA | Pair ranking | Accepted-positive recall | Canonical-cut recall | Safe learned / exact ANF |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| cut-rank GNN | 1049 | test | 0.469 | 0.375 | 0.062 | 0.188 | 5.754x |
| cut-rank GNN | 1049 | confirmatory | 0.639 | 0.889 | 0.222 | 0.278 | 4.739x |
| cut-rank GNN | 1301 | test | 0.594 | 0.500 | 0.062 | 0.062 | 5.307x |
| cut-rank GNN | 1301 | confirmatory | 0.583 | 0.833 | 0.056 | 0.167 | 5.035x |
| direct-cut GNN | 1049 | test | 0.500 | 0.312 | 0.000 | 0.062 | 5.960x |
| direct-cut GNN | 1049 | confirmatory | 0.639 | 0.778 | 0.111 | 0.056 | 4.734x |
| direct-cut GNN | 1301 | test | 0.531 | 0.438 | 0.000 | 0.062 | 5.926x |
| direct-cut GNN | 1301 | confirmatory | 0.667 | 0.833 | 0.111 | 0.056 | 4.643x |
| structural ranker | 1049 | test | 0.656 | 0.562 | 0.375 | n/a | 1.833x |
| structural ranker | 1049 | confirmatory | 0.500 | 1.000 | 0.333 | n/a | 1.428x |
| structural ranker | 1301 | test | 0.594 | 0.562 | 0.688 | n/a | 2.594x |
| structural ranker | 1301 | confirmatory | 0.639 | 1.000 | 0.833 | n/a | 1.749x |

`Safe learned / exact ANF` is a slowdown: values above one mean the learned
proposal and required exact check were slower. Exact ANF median time was about
0.59 ms. The cut GNN paths took about 4.6-6.0 times as long end to end.

Direct cut supervision improved partition recovery over the C3 fixed-component
decoder on some confirmatory cases. Pair ranking also transferred strongly to
the three confirmatory circuits. Neither result was stable on the held-out
`square` circuit: cut-rank pair accuracy fell to 0.375/0.500 and accepted-positive
recall remained 0.062 for both seeds.

The structural ranker illustrates the difference between relative and absolute
signals. It ranked every positive above its matched negative on confirmatory
circuits, yet validation-selected absolute thresholds produced inconsistent
classification. It also lacks a partition, so every proposal must run the full
exact ANF detector and cannot avoid that cost.

## Criteria and safety

The predeclared classification, accepted-partition, pair-ranking,
ranking-improvement, and cost criteria all failed. Safety passed.

A learned score never changed a function. Graph positives proposed a concrete
cut and were accepted only after fresh truth-vector construction and a complete
partition witness. Structural positives triggered the full exact ANF proof.
Rejected proposals and abstentions retained the original function. There were
zero accepted negative functions and zero final semantic changes across 408
held-out model rows.

The independent verifier:

- regenerated all 188 functions and 94 pair identities;
- recomputed all truth tables and canonical partitions independently;
- loaded six retained model artifacts;
- replayed 144 validation predictions and thresholds;
- replayed 408 held-out predictions and exact decisions;
- recomputed 204 pair rankings and 68 exact controls; and
- checked every artifact and source SHA-256 seal.

Verification status: **pass**.

## Interpretation and next boundary

Direct supervision fixed the decoder formulation but not the domain-transfer or
cost problem. The current global graph embedding appears able to learn some
circuit-relative ordering while failing to identify variable membership robustly
on an unseen circuit. More epochs or another threshold search would tune on a
known failure and would not constitute fresh evidence.

The next local implementation should make variable membership a node-level
problem: retain per-variable embeddings, score every variable against the root
and graph context, and use a permutation-equivariant cut loss. The deterministic
comparison should include a source-level variable-interaction approximation that
does not build the truth vector. Freeze that design on EPFL before obtaining a
second dataset. A separate-family run is not justified until the EPFL test split
shows stable cut recovery and the charged path approaches exact ANF cost.

All 18 research tracks and all eight application areas remain preserved.

## Evidence

- Retained run: `docs/recognition/runs/natural-cut-ranking-20260829-001`
- Independent verification: `docs/recognition/verification/natural-cut-ranking-20260829-001.json`
- Machine summary: `docs/recognition/learning_milestone_c4_direct_cut_ranking_results.json`
