# CRSE Learning Milestone C3: natural arbitrary-partition decomposition

Date: 2026-08-29  
Status: **complete, independently verified negative neural result**  
Production promotion: **no**

## Dataset found and frozen

The full EPFL combinational benchmark checkout was already present locally at
upstream commit `0060e156826e733d69bf5b3322d1bdd0d03a1f9a` under the MIT
License. No external download occurred. The bounded scout examined BLIF cones
from original, depth-optimized, and size-optimized variants with full semantic
support from 4 through 10 variables and at most 128 source nodes.

The scout retained 9,060 exact candidate functions: 894 positives and 8,166
negatives. A positive is a naturally occurring circuit cone whose Boolean
function has a nontrivial variable partition `A | B` such that

`f(X) = g(A) XOR h(B)`.

The teacher computes the algebraic normal form (ANF). Variables are connected
when they occur together in any nonzero ANF monomial. The target holds exactly
when that interaction graph is disconnected. This discovers arbitrary
partitions rather than assuming the earlier balanced first-half/second-half
partition. Every positive retains an exact partition witness and both factors.

Ten circuits contained both labels. The frozen learning slice is balanced and
circuit-disjoint:

| Split | Circuits | Functions | Positive / negative |
| --- | --- | ---: | ---: |
| training | adder, hyp, mem_ctrl, multiplier, router | 96 | 48 / 48 |
| validation | div | 24 | 12 / 12 |
| test | square | 32 | 16 / 16 |
| confirmatory development | sin, sqrt, voter | 36 | 18 / 18 |

Across all 188 functions there are no exact semantic duplicates, no
variable-renamed structural duplicates, and no circuit overlap between splits.
Variable counts cover every value from 4 through 10.

Because the scout was inspected before selecting circuits with both labels,
the confirmatory-named split remains development evidence. It is a circuit-held-
out test inside EPFL, not a sealed independent-dataset confirmation.

## Training and exact controls

Two seeds trained each of three small CPU models for 30 epochs with the same 96
training IDs, batch size 32, Adam learning rate 0.003, and validation-only
threshold selection:

- `structural_linear`: 18 parameters over coarse graph statistics;
- `natural_graph_gnn`: 80,001 parameters over the source DAG;
- `natural_multitask_gnn`: 82,926 parameters, predicting the class plus all 45
  possible ANF variable-interaction edges for the padded 10-variable universe.

The multitask auxiliary loss weight was 0.30. Model files are inert,
hash-checked float32 JSON and were reloaded before retained evaluation.

The exact ANF detector and always-abstain classifier were retained controls.
The exact detector achieved 1.000 accuracy in every split. It is the correct
choice after a complete truth vector exists; the learned path is only a possible
early shortlist before complete CM materialization.

## First natural run

| Model | Seed | Test balanced accuracy | Development-confirmatory balanced accuracy |
| --- | ---: | ---: | ---: |
| structural linear | 619 | 0.812 | 0.556 |
| structural linear | 887 | 0.625 | 0.472 |
| graph GNN | 619 | 0.594 | 0.694 |
| graph GNN | 887 | 0.719 | 0.639 |
| multitask GNN | 619 | 0.500 | 0.500 |
| multitask GNN | 887 | 0.500 | 0.500 |

The multitask interaction-edge F1 was 0.703/0.706 on test and 0.886/0.866
on development-confirmatory. Those edge scores contained useful signal, but a
fixed 0.5 connected-component decoder was brittle: one spurious edge can join
two otherwise correct components, producing no candidate partition.

## Decoder follow-up

A follow-up performed no retraining. It loaded the two frozen multitask models,
enumerated every bounded nontrivial cut with `x0` on one side, minimized mean
predicted cross-edge probability, and selected class/cut thresholds using
validation only.

| Seed | Test proposal BA | Confirmatory proposal BA | Test accepted-positive recall | Confirmatory accepted-positive recall |
| ---: | ---: | ---: | ---: | ---: |
| 619 | 0.688 | 0.778 | 0.062 | 0.278 |
| 887 | 0.719 | 0.639 | 0.062 | 0.111 |

The decoder recovered more positive proposals, but usually ranked the wrong
partition. Exact partition witnesses rejected those proposals safely. The
predeclared proposal and accepted-positive criteria failed.

## Structure-matched repeat

To test whether coarse circuit structure was a shortcut, every positive was
paired one-to-one with a negative from the same circuit. All pairs have the same
variable count; 91.5% have the same optimization variant; median node-count,
depth, and edge-count differences are all zero. The split, labels, model
schedules, and seeds stayed fixed.

| Model | Seed | Test balanced accuracy | Development-confirmatory balanced accuracy |
| --- | ---: | ---: | ---: |
| structural linear | 619 | 0.500 | 0.500 |
| structural linear | 887 | 0.531 | 0.667 |
| graph GNN | 619 | 0.531 | 0.583 |
| graph GNN | 887 | 0.594 | 0.611 |
| multitask GNN | 619 | 0.531 | 0.556 |
| multitask GNN | 887 | 0.500 | 0.500 |

The graph advantage did not survive consistently. Test interaction-edge F1
also fell just below 0.70 for both seeds (0.689 and 0.694). This is evidence that
the unmatched task exposed structural shortcuts and that the current network
does not robustly infer the exact semantic partition.

## Safety and independent replay

No learned output replaced a Boolean function directly. A positive score only
proposed a concrete partition. Acceptance recomputed the complete truth vector
and checked the full XOR partition identity; rejection and abstention retained
the original function. All three studies recorded zero semantic mismatches.

Independent verifiers then:

- regenerated both 188-function datasets and their provenance;
- recomputed every truth table using the scalar assignment interpreter;
- independently recomputed ANF interaction edges and decomposability;
- reloaded all 12 retained trained-model artifacts across the two training runs;
- reproduced calibration and 1,104 classification rows;
- replayed 136 decoder evaluation rows and 48 decoder validation predictions;
- checked 184 exact-control rows; and
- confirmed every retained artifact inventory and SHA-256 seal.

All three independent verifications passed. The natural source and
structure-matched learning criteria failed; safety passed; production promotion
remains refused.

## Interpretation and next boundary

C3 closes the dataset gap identified by C2 inside the already licensed EPFL
corpus. We now have real circuit cones with exact positive and negative labels,
arbitrary discovered partitions, auxiliary interaction targets, held-out
circuits, and hard matched negatives. The result does not support a learned
replacement or a speed claim. It shows that exact labels and useful edge-level
signal are insufficient when the decoder must identify an entire partition.

The next responsible learning experiment should use the matched pairs, supervise
the cut objective directly, and compare a deterministic ANF signature, a pairwise
ranking baseline, and the graph proposal under the same exact acceptance cost.
Only after freezing that design should it be evaluated once on a separately
licensed circuit family such as LogikBench. OpenABC-D is also relevant but its
full release is far larger than needed for this bounded stage.

All 18 research tracks and all eight application areas remain in the register.

## Evidence

- Source scout: `docs/recognition/source_scouts/natural-decomposition-epfl-20260829-001.json`
- Natural run: `docs/recognition/runs/natural-decomposition-20260829-001`
- Decoder run: `docs/recognition/runs/natural-decomposition-decoder-20260829-001`
- Structure-matched run: `docs/recognition/runs/natural-decomposition-matched-20260829-001`
- Independent verifications: `docs/recognition/verification/natural-decomposition-*.json`
- Machine summary: `docs/recognition/learning_milestone_c3_natural_decomposition_results.json`
