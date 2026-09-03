# CM neural architecture reassessment

> **Current-decision update (2026-09-03):** a later cache-isolated seven-arm run
> closed native slots against CSE/CM bigint and word controls in one source-bound
> experiment. Native won all 18 exposed cases, again giving exactly `1.0000x`
> selector headroom. See
> `CM_NATIVE_PORTFOLIO_BASELINE_CLOSURE_2026_09_03.md`. This report and its frozen
> artifact remain the preceding verified assessment.

**Date:** 2026-09-02  
**Scope:** development-only audit and fail-closed label/economics integration; no
training, prospective data, production routing, model promotion, commit, or push.

## Decision

The current neural work should **not** be retrained or extended on the present
targets.

The executable neural research culminates in task **B**, exact-decomposition/cut
proposal, with task **C**, pair/partition ranking, as an auxiliary loss. It is not
an exact answer engine and it is not the C36 backend selector. The proposed C37
selector would have been task **D**, exact-backend selection, optionally learned
through task **E**, cost prediction.

Both routes now fail before training:

- C5's verified learned path is 6.3–9.2 times slower than the exact ANF control,
  has low accepted-positive recall, and cannot terminate the complete
  global-best search established by C21.
- The repaired post-R2 word-only portfolio has only `1.000415621x` q64 oracle
  headroom.
- The separate verified task-identical engine run includes bigint and gives all
  18 exposed cases the same label, `cse_bigint`. Its best fixed method and
  per-case oracle are both 85,568,450 ns, so gross selector headroom is exactly
  `1.000000000x`.

Changing GNN depth, adding exact-backend features, or training a cost model would
therefore add cost to a decision that is absent on the available cohort. The
scientifically justified implementation is a version-bound readiness gate that
rejects stale labels and records the negative decision.

## Task separation

| Task | Present project status | Decision |
|---|---|---|
| A. Predict exact answers/relations | Early synthetic neural experiments classified hidden affine structure; no model is an accepted exact answer backend | Stop as an execution target; an exact output/check remains required |
| B. Predict decomposition/cut candidates | C3–C5, ending in the variable-conditioned GNN | Freeze as negative research evidence; exact ANF is stronger |
| C. Rank partitions | C4/C5 ranking losses and C21 task-matched completion evidence | Stop until a sound certificate avoids material exact work |
| D. Select an exact backend | Proposed after historical C36; no neural C37 model exists | Stop: post-R2/full-engine headroom gates fail |
| E. Predict runtime/cost | Small classical policies exist elsewhere; no current neural cost model uses post-R2 targets | Reformulate only after a new exact portfolio has measurable regret |
| F. Learn a CM representation | Matrix, graph, fused, and retrieval representation studies exist | Research-only; no current downstream task or matched economic gate warrants training |

These tasks have different contracts. Classification or ranking accuracy is not
credited as exact computation, and a valid decomposition is not substituted for
the deterministic globally best artifact.

## Architecture and representation map

The model inventory was instantiated under Torch 2.10.0+cpu and parameter counts
were recomputed from live model objects.

| Research stage | Inputs | Representative models and parameters | Outputs |
|---|---|---|---|
| Initial fixed-width study | Dense 16x16 Boolean CM/truth matrix with a validity mask; serialized expression DAG v2 | matrix MLP 73,985; matrix CNN 83,841; graph GNN 79,233; fused 72,337; graph retrieval 72,992 | affine membership or retrieval embedding |
| Variable-width study | Padded dense mathematical CM/truth matrix through 10 variables; source DAG | variable matrix MLP 99,953; multiscale CM 60,289; graph GNN 80,001; fused 64,017 | decomposition membership and auxiliary structure |
| Natural C3 | Source DAG plus cheap structural controls | structural linear 18; natural GNN 80,001; multitask GNN 82,926 | decomposability and ANF-interaction edges |
| Natural C4 | Source DAG and same-circuit matched pairs | structural pair ranker 18; direct-cut/rank GNN 80,651 | membership, canonical row cut, pair rank |
| Natural C5 | Bidirectional source DAG, per-variable embeddings, shared cut head | variable-cut GNN and variable-cut-plus-rank GNN, both 136,962 | membership plus ten shared variable-membership logits |

Terminology is important:

- The matrix tensors are dense bounded truth-function/mathematical-CM inputs.
- The graph tensors are canonical serialized Boolean DAGs that preserve sharing,
  operator, edge role, negation, root, and declared variable universe.
- CM IR is a separate canonical compiler/execution representation and is not a
  neural input here. It must not be described as the mathematical CM.
- Packed ANF is an exact teacher/control and decomposition representation, not a
  learned embedding in C5.
- The C5 model does not consume R2 schedules, liveness masks, instruction counts,
  residual-width distributions, query count, or measured backend costs. Adding
  those fields would only be appropriate for a live task-D/E decision.

### Symmetry and structural assumptions

C5 removes absolute variable identity from learned node features, uses one
shared variable head, and retains `x0` only as the orientation anchor. The
retained audit and the current tests show exactly zero error under a non-anchor
variable swap.

The graph encodings intentionally preserve source-DAG sharing and left/right
edge roles. Consequently, the current learned functions are not guaranteed to
be invariant to replacing a shared DAG by an equivalent duplicated tree or to
commutative operand reordering. Those transformations preserve the semantic C5
label, so a future representation-learning revival must either canonicalize
them or add explicit metamorphic loss/tests. Changing the frozen C5 artifact now
is not justified because its task and economics already fail.

## Labels, splits, and leakage controls

C5 uses exact labels regenerated from the bounded truth function:

- decomposable/indecomposable membership;
- the deterministic canonical partition;
- per-variable row membership; and
- exact ANF interaction edges for auxiliary/control work.

Every accepted learned proposal recomputes the exact truth vector and crosses
`partition_witness`. Abstention or failed checking retains the unchanged exact
result. The model never certifies correctness.

The retained C5 cohort has 188 rows in 94 structure-matched pairs:

| Split | Rows / pairs | Circuits | Use |
|---|---:|---|---|
| train | 96 / 48 | adder, hyp, mem_ctrl, multiplier, router | fitting only |
| validation | 24 / 12 | div | threshold calibration only |
| test | 32 / 16 | square | held-out evaluation |
| confirmatory | 36 / 18 | sin, sqrt, voter | historical held-out evaluation |

The freezer rejects cross-split semantic duplicates and alpha-renamed structural
duplicates, proves circuit-set disjointness, balances labels within each split,
and keeps each positive/negative matched pair in one circuit and one split.
The historical confirmation split has already been inspected; it is not a new
prospective corpus and must not be reused to tune another model.

Model JSON binds architecture, parameter count, Torch/device/dtype, complete
state, training seed/schedule provenance, dataset hash, training-pair hash, and
final state hash. Load rejects schema, tensor, metadata, state, or payload-hash
changes. The C5 run additionally binds dataset, sources, models, calibration,
raw predictions, exact checks, and reports in its artifact manifest.

## Stale assumptions and label replacement

| Label/evidence generation | Exposed q64 labels | Status |
|---|---|---|
| Historical C36 family rule | 14 direct AST, 4 compiled projection | Rejected: it exploits occurrence-recursive R0 and was selected post hoc |
| Restricted evaluator `-003` | 17 R2, 1 compiled projection | Valid post-R2 diagnostic, but rejected for training because CSE/CM arms are word-only |
| Multi-query/engine `-001` | 18 CSE bigint | Valid exposed development diagnostic; zero selector headroom; not confirmation |

The engine run also contains R2, CSE bigint/words, CM-IR bigint/words, and full
projection in one counterbalanced run. R1 is present in the separate `-003` run,
where it is slower than R2 at q64. Because R1 and bigint were not measured in one
current-source-closed run, the new audit deliberately refuses to manufacture a
combined training label table from cross-run timings. That missing single-run
closure is another fail-closed condition, although the zero-headroom bigint
result already stops training.

The retained engine manifest predates the current bytes of `bitset_backend.py`
and `gf2_restricted_evaluators.py`; this drift is recorded. The current `-003`
restricted run has no source drift. No stale model or label artifact is silently
reclassified as current.

## Baselines and perfect-predictor economics

Values below are sums of 18 per-case medians. Totals from different runs are
shown separately and are not combined into per-case labels.

### Current-source post-R2 restricted run

| Method | q64 total |
|---|---:|
| R0 occurrence recursion | 820.203 ms |
| R1 identity memo | 133.408 ms |
| R2 topological/liveness | **108.557 ms** |
| compiled projection | 158.359 ms |
| flattened CSE words | 163.448 ms |
| CM IR words | 179.124 ms |
| optimized per-case oracle | 108.512 ms |

Gross headroom is only 45,100 ns across all 18 cases:

`108,557,450 / 108,512,350 = 1.0004156209x`.

### Same-task engine run with bigint controls

| Method | q64 total |
|---|---:|
| CSE bigint | **85.568 ms** |
| CM IR bigint | 99.597 ms |
| R2 per query | 118.706 ms |
| full projection | 142.373 ms |
| CSE words | 150.161 ms |
| CM IR words | 162.945 ms |
| per-case oracle | **85.568 ms** |

All 18 oracle labels are CSE bigint. Thus:

`85,568,450 / 85,568,450 = 1.0000000000x`.

The old C36 recognition allowance was 123,400 ns per case, or 2,221,200 ns for
18 cases. Even setting tensor construction, model inference, exact verification,
and fallback to zero gives only:

`85,568,450 / (85,568,450 + 2,221,200) = 0.9746986120x`.

This is an optimistic upper bound. Real inference, verification, and fallback
are nonnegative and can only reduce it. There is no need to spend a prospective
corpus to confirm a selector whose exposed-development oracle has no gross gain.

For task B/C, C5 already measured the actual boundary: representation,
inference, exact checking, and fallback made the safe learned path 6.3–9.2 times
slower than exact truth-vector ANF. C21 then showed that a ranked partition does
not reduce work when the same global-best candidate universe must be completed.
The tested ANF full screen and bounded-rank continuation also missed their
complete-task/pruning gates, so they do not create a new trainable early-stop
decision.

## Implemented changes

- `cmbench/recognition/neural_reassessment.py`
  - validates artifact, result, source-manifest, interpreter/verification, and
    exposed-development boundaries;
  - requires R0/R1/R2 in the repaired diagnostic and bigint/word/R2/projection
    coverage in the engine diagnostic;
  - recomputes per-case label counts, fixed/oracle totals, headroom, and an
    optimistic charged upper bound;
  - rejects stale/missing R2 or bigint labels;
  - records current source drift and refuses cross-run label synthesis; and
  - provides an advice-off contract that abstains and keeps the unchanged exact
    fallback when the training gate fails.
- Added bounded artifact runner and replay verifier under `scripts/`.
- Added `tests/test_neural_reassessment.py` for current economics, stale R2 or
  bigint omission, tampered label source, artifact replay/tamper detection,
  abstention, and advice-off fallback equivalence.
- Created and independently replayed the new development artifact:
  `docs/recognition/runs/neural-architecture-reassessment-development-20260902-001/`.

The artifact assessment SHA-256 is
`b6025da7d5169f448629c62f01ff60b0f06e9f9fe8a172382735c654cead2f9f`;
its verifier status is `verified`. It records zero training, prospective data,
production writes, and promotion.

No frozen model or earlier experiment artifact was overwritten. No neural
architecture, production backend, or route was modified.

## Verification and tests

### Environments

| Environment | Interpreter | Torch | pytest | Use |
|---|---|---|---|---|
| `.venv` | Python 3.13.5, `C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe` | missing | 9.1.1 | reassessment and exact suites |
| `.venv-crse-neural` | Python 3.13.5, `C:\Users\brian\Documents\CM_Computation\.venv-crse-neural\Scripts\python.exe` | 2.10.0+cpu | missing | Torch suites via standard-library `unittest` |

The dependency split was not hidden: Torch tests were run with `unittest`
because pytest is not installed in the Torch environment.

### Results

- Five Torch test files under `.venv-crse-neural`: **24 passed**.
  They cover matrix/graph/fused forwards, deterministic seed training, model
  save/reload and tamper refusal, circuit-disjoint data, semantic/alpha leakage,
  exact decomposition/reconstruction, source controls, and C5 variable-renaming
  equivariance.
- Focused reassessment and exact-backend suite under `.venv`: **30 passed in
  4.92 s**.
- Broad non-neural suite with the documented Torch/generated-chart exclusions:
  **1,225 passed, 4 warnings, 1,127 subtests passed in 207.17 s**.
- New artifact independent replay: `verified`; three evidence runs and 36
  backend-label rows replayed.

The four broad-suite warnings are the existing `dd.bdd.BDD.__del__`
referenced-node shutdown warnings in persistence tests. There were no
correctness failures. An initial focused invocation encountered a Windows
permission error creating pytest's user temp directory; the unchanged tests
passed after using a fresh workspace-local `--basetemp`.

## What is ruled out and what remains warranted

Ruled out on current evidence:

- the old `U/N > 10` family/backend label;
- neural or shallow routing on the exposed C36 cohort;
- training from the word-only `-003` labels;
- another C5 hyperparameter/architecture sweep;
- partition ranking before a sound early-termination certificate; and
- calling CM IR the mathematical CM or crediting exact C6 gains to learning.

No prospective neural experiment is warranted now. A future experiment becomes
scientifically eligible only after exact methods are frozen in one
source-closed run and either:

1. a new task-matched backend portfolio has at least about `1.10x` development
   oracle headroom after cheap analytical controls; or
2. a sound branch-and-bound/certificate mechanism removes material global-best
   decomposition work and passes its complete-task gate.

At that point the first controls should be analytical cost equations, a linear
or quantile model, and a shallow tree. Any graph/CM model must use circuit/source
splits, representation-matched AST/DAG and packed-ANF controls, explicit
sharing/tree and operand-order metamorphic tests, validation-only abstention,
exact verification, advice-off equivalence, full charged timing, and a newly
frozen prospective corpus. None of those preconditions is currently met.
