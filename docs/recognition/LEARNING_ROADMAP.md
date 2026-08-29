# CRSE learning implementation roadmap

The [machine-readable register](experiment_register.json) preserves R01-R18,
the full transformation inventory, and all eight application families from the
owner's implementation brief. An implemented interface is not a measured track.
No model is promoted; Windows launcher, containment, deployment and cloud work
remain deferred. Existing historical evidence remains unchanged.

## Working sequence

Current checkpoints: [A/B implementation and results](LEARNING_MILESTONES_AB_2026_08_29.md),
[C implementation and results](LEARNING_MILESTONE_C_2026_08_29.md), and the
[first D task-computation results](LEARNING_MILESTONE_D_2026_08_29.md), followed
by the [D2 proved-rule reuse result](PROVED_RULE_MILESTONE_D2_2026_08_29.md) and
the [D3 versioned rule-cache result](VERSIONED_RULE_CACHE_MILESTONE_D3_2026_08_29.md).
A/B, the first bounded slice of C, and three bounded slices of D are implemented
and measured. C includes actual
matrix MLP, CNN, GNN, fused, and contrastive retrieval training plus a frozen
EPFL evaluation slice. Its synthetic representation signal passed, retrieval
missed its threshold, and EPFL transfer was poor. D now measures four separate
task contracts through direct, CSE, CM-IR and explicit dense-CM paths, a fitted
task/query router, exact caching, and stop/one-rewrite scheduling on a new EPFL
slice. Routing gains were task-specific; dense-CM construction and per-instance
rewrite proof were negative results. These are measured smokes, not broad
graph-learning or transformation/reuse completion. D2 now proves one AIG-XOR
motif over Boolean metavariables and reuses a fixed structural matcher. It beats
repeating explicit CM proof, including at five internal sites in two EPFL cones,
but still loses to the no-rewrite CSE control. D3 adds a second proved rule,
deterministic overlap priority, and exact changed-cone invalidation across three
generated DAG versions. Persistent caching halves fresh rematching cost on
sparse changes but still loses to no rewrite. Further D work and E remain
pending. The
[optional framework request](NEURAL_DEPENDENCY_REQUEST.md) was approved and
executed in an isolated environment.

1. **A: reusable foundation.** Retain feature ablations with the original
   direct/CSE/CM harness, add the equally cheap query-count rule, bind feature
   schemas to models, and implement bounded task/proposal/check/CM contracts.
2. **B: actual neural comparison.** Train a small NumPy MLP on exact hidden-affine
   labels; save/reload it and compare verified replacements with fixed exact
   paths, an exact motif detector, a tiny cost tree, and an answer-cache control.
3. **C: graph learning.** The first matched matrix/graph/fused and contrastive
   retrieval slice is measured with exact CM supervision and a provenance-reviewed
   local EPFL source. Extend it with natural positive examples, richer targets,
   recursive/hierarchical controls, calibration and independent replication.
4. **D: transformations and reuse.** The first task-matched slice is measured:
   complete vectors, points, restrictions and repeated vectors across direct,
   CSE, CM-IR and explicit CM, plus a cost policy, exact cache and one checked
   root rewrite. The first compiled proved rule is also measured, with strict
   artifact admission, near-match controls and internal EPFL applications. A
   two-rule pack and versioned structural cache now exercise deterministic
   overlap and localized invalidation. Continue with profitability scheduling,
   natural version histories, partitions/GF(2), and BDD/AIG controls.
5. **E: remaining methods and applications.** Offline LLM proposals and optional
   approved distillation, learning-method comparisons, adaptive replay, solver
   guidance, negative controls, and remaining application families.

## Evidence rules

Every run requires an explicit finite manifest before execution and a fresh,
ignored output directory. Keep raw rows, models, split IDs, exact checks,
source/data hashes, environment, and incomplete records. Training/validation,
exploratory tests and sealed confirmation are distinct. More rounds on one
formula or more syntactic variants of one function are not independent samples.

CM means dense local truth-function input in the teacher; the original `cm`
portfolio arm means CM-IR simplification followed by the bigint executor.
Truth input construction is charged when starting from an expression. Accepted
replacements require independent exact checking, including its cost. One switch
disables learned advice and restores the same exact result contract.

Generated mechanism demonstrations are not natural-domain generalization.
No dependency installation, download, API call, commit, push, or publication
is implied by this roadmap. Group any future resource requests by exact package,
revision, license, size, local destination, effects, and finite compute budget.
