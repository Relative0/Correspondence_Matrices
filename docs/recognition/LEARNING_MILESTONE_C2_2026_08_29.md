# CRSE Learning Milestone C2: variable-size exact decomposition

Date: 2026-08-29  
Status: **complete, verified negative neural result**  
Production promotion: **no**

## What was added

C2 replaces the earlier fixed-eight-variable affine label with a richer exact
CM target. For the balanced variable partition, a function is positive exactly
when its correspondence matrix satisfies

`M[r,c] XOR M[r,0] XOR M[0,c] XOR M[0,0] = 0`

for every cell. A positive therefore has canonical exact factors
`M[r,c] = g[r] XOR h[c]`. The teacher retains those row and column truth
factors and independently recomposes them before any proposal can be accepted.

The generated set contains 80 positive/negative parent pairs, or 160 functions.
Every negative changes exactly one truth-table assignment from its positive
parent and is proved not to decompose. Training mixes 4, 6, and 8 variables;
the confirmatory split contains only 10-variable functions and 32x32 CMs.

| Split | Functions | Variables | Role |
| --- | ---: | --- | --- |
| training | 96 | 4, 6, 8 | fitting only |
| validation | 24 | 8 | threshold selection only |
| test | 24 | 8 | held-out source encoding |
| confirmation | 16 | 10 | held-out encoding and matrix size |
| EPFL | 32 | 8 | frozen natural evaluation only |

The retained EPFL functions are all negative for this decomposition target.
They can measure specificity and false proposals, but cannot support sensitivity,
balanced accuracy, or a natural-positive generalization claim.

## Matched learned comparison

Two seeds actually trained, serialized, reloaded, and prediction-checked each of:

- a fixed-canvas variable Matrix MLP;
- a shared multiscale CM network with 1x1, 2x2, 4x4, and 8x8 adaptive blocks;
- a variable-universe source-DAG GNN with operator, edge-role, variable, root,
  sharing, and ambient-size information;
- a fused multiscale-CM plus graph model.

All eight models used the same 96 training IDs, per-seed minibatch ordering,
Adam optimizer, 25 epochs, batch size 32, and learning rate 0.003. Thresholds
were selected from validation predictions only. The EPFL slice never affected
training or threshold selection.

## Results

Values are balanced accuracy except that EPFL reports specificity because its
positive count is zero.

| Model | Test, seeds 317 / 571 | n=10 confirmation | EPFL specificity |
| --- | ---: | ---: | ---: |
| Variable Matrix MLP | 0.500 / 0.500 | 0.500 / 0.500 | 0.688 / 0.219 |
| Multiscale CM | 0.667 / 0.500 | 0.500 / 0.500 | 0.281 / 0.656 |
| Variable Graph GNN | 0.500 / 0.500 | 0.500 / 0.438 | 0.000 / 0.844 |
| Fused | 0.500 / 0.500 | 0.500 / 0.500 | 0.000 / 0.000 |
| Exact CM parity detector | 1.000 | 1.000 | 1.000 |
| Always abstain | 0.500 | 0.500 | 1.000 |

Neither predeclared learning criterion passed. No graph or fused model exceeded
the Matrix MLP by 0.05 on both test and confirmation for both seeds, and no
architecture reached 0.75 confirmation accuracy for both seeds.

The failure modes are informative. Matrix losses stayed close to random-choice
cross entropy: a single changed cell is hard to recover from padded raw or
pooled images. Graph and fused training losses reached zero, but validation,
held-out encoding, and size transfer remained near chance. They learned the
training source syntax rather than the exact functional relation. Several
validation-calibrated thresholds went to an extreme, and frozen EPFL specificity
ranged from 0.000 to 0.844.

## Exactness and verification

A learned positive remained only a proposal. The acceptance path recomputed the
complete truth function, checked the anchored parity identity, constructed the
canonical factors, and recomposed them. Rejected proposals and abstentions kept
the original exact function. Across 768 learned evaluation rows there were zero
accepted semantic mismatches and zero witness mismatches.

The independent verifier:

- regenerated all 160 generated functions;
- reloaded the 32 frozen EPFL functions;
- recomputed all 192 truth tables with the scalar assignment interpreter;
- used an independent nested-loop decomposition test;
- loaded all eight inert, hash-checked float32 JSON model artifacts;
- reproduced validation calibration and all 768 predictions; and
- checked all 96 exact-control rows.

Verification status: **pass**.

## Interpretation and next boundary

The exact decomposition infrastructure works across variable sizes and exposes
cofactor labels, exact factors, and functional distance for later multitask
work. The neural result says capacity or more epochs alone is not the next
responsible move. The next dataset must contain source-independent natural
positives and negatives, or at least several label-balanced expression encodings
with structure-matched hard negatives. Before another neural run, add a
deterministic cofactor-signature/linear control and auxiliary residual or factor
targets. Keep the exact detector and always-abstain baselines.

This result does not show a speedup. If the full CM already exists, the analytic
parity detector is exact, cheaper, and perfect. A learned graph shortlist could
only become useful before CM materialization and only for a downstream rewrite
whose verified operation savings exceed graph inference plus exact acceptance.

All 18 research tracks and all eight application areas remain in the register.

## Evidence

- Retained run: `docs/recognition/runs/variable-decomposition-20260829-001`
- Independent verification: `docs/recognition/verification/variable-decomposition-20260829-001.json`
- Machine summary: `docs/recognition/learning_milestone_c2_results.json`
- Video-agent brief: `docs/recognition/CRSE_NEURAL_VIDEOS_AGENT_PROMPT_2026_08_29.md`
