# CRSE Learning Milestone C5: variable-conditioned equivariant cuts

Date: 2026-08-29  
Status: **complete and independently verified**  
Production promotion: **no**

## Architecture change

C4 predicted all cut memberships from one global graph vector. C5 makes cut
prediction a variable-level task while keeping the same 94 structure-matched
EPFL pairs, splits, seeds, epochs, pair batches, loss weights, and validation
threshold rule.

The new 136,962-parameter GNN:

- sends messages in both child-to-parent and parent-to-child directions;
- removes absolute variable identity from learned node features;
- retains a context-rich embedding for each variable node;
- applies one shared cut head to every variable; and
- uses `x0` only as the `A | B` orientation anchor.

Renaming any non-anchor variable therefore permutes the corresponding output
without changing the class score. Thirty-two retained permutation audits across
four trained models had exactly zero numerical error.

Two arms trained under seeds 1049 and 1301:

- `variable_cut_gnn`: classification plus direct per-variable cut loss;
- `variable_cut_rank_gnn`: the same model plus same-pair margin loss.

All proposals still require a freshly recomputed truth vector and an exact
candidate-partition witness.

## Learned results

| Model | Seed | Split | Proposal BA | Pair ranking | Accepted-positive recall | Canonical-cut recall | Safe learned / exact ANF |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| variable-cut | 1049 | test | 0.594 | 0.625 | 0.125 | 0.125 | 6.511x |
| variable-cut | 1049 | confirmatory | 0.778 | 1.000 | 0.222 | 0.389 | 7.409x |
| variable-cut | 1301 | test | 0.562 | 0.688 | 0.188 | 0.125 | 7.041x |
| variable-cut | 1301 | confirmatory | 0.750 | 0.944 | 0.333 | 0.444 | 7.021x |
| variable-cut plus ranking | 1049 | test | 0.500 | 0.625 | 0.125 | 0.188 | 6.328x |
| variable-cut plus ranking | 1049 | confirmatory | 0.667 | 1.000 | 0.056 | 0.389 | 6.288x |
| variable-cut plus ranking | 1301 | test | 0.531 | 0.500 | 0.125 | 0.125 | 6.682x |
| variable-cut plus ranking | 1301 | confirmatory | 0.778 | 1.000 | 0.056 | 0.222 | 9.232x |

The non-ranking variable-conditioned arm improved C4 direct-cut accepted recall
from 0 to 0.125/0.188 on the held-out square circuit and from 0.111 to as high
as 0.333 on confirmatory circuits. It also reached 0.750-0.778 confirmatory
balanced accuracy. Those improvements did not satisfy the frozen cross-seed and
cross-split criteria. Test balanced accuracy remained 0.562-0.594, and the
charged learned path was 6.3-9.2 times slower than exact truth-vector ANF.

The ranking loss did not help partition acceptance. It produced perfect
confirmatory pair ordering but lower accepted recall. The most useful learned
result is therefore the variable-conditioned architecture without ranking, not
the combined loss.

## Deterministic source controls

C5 also adds two source-DAG controls that run before truth-vector construction.

The conservative interaction over-approximation treats AND/OR/implication as
potentially coupling every variable in their child supports. It is sound but
AIG lowering connects every retained cone, so it safely abstained on all cases.

The second control propagates exact bounded GF(2) monomial sets through the
source DAG. It handles cancellation directly and obtains the exact ANF
interaction components without first materializing the complete truth vector.

| Control | Split | BA | Accepted-positive recall | Median total | p95 total |
| --- | --- | ---: | ---: | ---: | ---: |
| conservative over-approximation | test | 0.500 | 0.000 | 0.198 ms | 0.610 ms |
| conservative over-approximation | confirmatory | 0.500 | 0.000 | 0.097 ms | 0.435 ms |
| source symbolic ANF | test | 1.000 | 1.000 | 0.373 ms | 2.600 ms |
| source symbolic ANF | confirmatory | 1.000 | 1.000 | 0.428 ms | 63.721 ms |
| truth-vector ANF | test | 1.000 | 1.000 | 0.590 ms | 6.050 ms |
| truth-vector ANF | confirmatory | 1.000 | 1.000 | 0.524 ms | 7.716 ms |

The symbolic source path was 1.58x faster at the test median and 1.22x faster at
the confirmatory median. It also beat truth-vector ANF at test p95. A small
number of symbolic polynomial products produced a 63.7 ms confirmatory p95,
about 8.3 times the truth-vector p95, so the frozen source-cost criterion failed.
This is promising exact algorithmic evidence with an unresolved tail, not a
production speedup.

## Criteria, safety, and verification

Equivariance and exact symbolic-source criteria passed. Classification,
accepted-partition, pair-ranking, C4-improvement, learned-cost, and symbolic
p95-cost criteria failed. Safety passed; production promotion remains false.

The independent verifier:

- regenerated all 188 functions and 94 matched pairs;
- recomputed 188 scalar truth tables and canonical partitions;
- reconstructed all 188 truth tables independently from source symbolic ANFs;
- proved exact source edges are subsets of conservative approximate edges;
- loaded four retained model artifacts;
- replayed 96 validation and 272 held-out predictions;
- replayed 136 source controls, 136 pair rankings, 32 equivariance checks, and
  68 exact controls; and
- checked the retained C4 dependency and every artifact/source hash.

Verification status: **pass**. Semantic mismatches: **zero**.

## Next boundary

The architecture change helped, but the deterministic symbolic path is now the
stronger immediate opportunity. The next implementation should represent ANF
monomial sets as bounded bitsets, cache repeated polynomial products by exact
operand identity, record term/product counts, and fall back to truth-vector ANF
before an operation budget is exceeded. Compare the hybrid against both current
exact paths on the same frozen cones and retain median, p95, and maximum cost.

Further neural fitting should pause until there is a representation change or a
larger training-circuit population. The present 48 training pairs from five
circuits are insufficient evidence for another hyperparameter search.

All 18 research tracks and all eight application areas remain preserved.

## Evidence

- Retained run: `docs/recognition/runs/natural-variable-cut-20260829-001`
- Independent verification: `docs/recognition/verification/natural-variable-cut-20260829-001.json`
- Machine summary: `docs/recognition/learning_milestone_c5_variable_conditioned_cut_results.json`
