# Correspondence Matrices and neural learning — assessment, 2026-08-29

Status: research recommendation, not an implemented neural system or a speedup
claim. The current CRSE software remains the exact-backend decision-tree pilot.
No new model training, dependency installation, VM, GPU service, or upload was
performed for this assessment.

## Conclusion

CMs are a worthwhile experimental domain for learning structural recognition,
decomposition, and optimization strategy. Binary values alone are not the reason.
The useful combination is exact semantics, controllable transformations, repeated
substructure, and mechanically checkable training labels.

The strongest design to test is a learned proposer plus an exact executor and
checker. A model can save search work by ranking useful rewrites, partitions,
or equivalent-subexpression candidates. It must not replace a logical proof
with a high-confidence classification.

CMs may be especially useful as a training teacher: compute small exact CMs
offline to supervise a graph model, then apply that model to expression graphs
without first constructing an enormous dense CM at inference time.

## What the paper contributes

Source reviewed: Brian Droncheff, *Correspondence Matrices; Algorithms for
Propositional Logic*, attached 29-page PDF. All pages were text-extracted; pages
7, 8, 12, and 24–26 were also rendered and visually inspected for matrix layout.
The original PDF was not edited or re-exported.

- Section 3 / page 7 gives all 16 two-input operators as 2x2 binary CMs.
- Page 8 explicitly relates a CM to a truth table with a fixed variable order.
- Section 3.1 relates transposition, negation, and rotations to operand changes.
- Sections 3.2.1–3.2.3 cover decomposition, quotient/set difference, and
  pointwise composition for aligned operands.
- Section 5.3 / page 24 contrasts small-matrix composition with expansion into
  a larger matrix. That choice is a natural potential learning target.

The elementary 2x2 operations do not need neural prediction: there are only
16 operators, with four bits each. Even all four-input truth functions number
only 65,536, so exhaustive small-function tables and deterministic synthesis
are important controls. Merely recovering these tables is not evidence of
generalization or of a useful learned speedup.

An in-memory independent Boolean sanity check covered all 16 x 16 x 16 choices
of two inner operators and one combining operator, at all four assignments:
16,384 pointwise-composition checks, zero mismatches. This is a finite check of
that composition property, not a validation of every derivation in the paper.

## Where a model might help

| Target | What is learned | Exact work retained / baseline |
| --- | --- | --- |
| Decomposition | Which variable partition, cofactor split, or local factorization to try first | Verify factorization; compare deterministic partition search, BDD ordering, and explicit CM block analysis |
| Rewrite scheduling | Which valid rule and subexpression to choose, and when to stop | Apply admitted rules or prove new candidates; compare CSE-flat, deterministic CM simplification, ABC/e-graph search |
| Functional retrieval | Rank likely equivalent, complementary, or related subexpressions despite different syntax | Exact signatures for materialized small CMs, hashing, SAT/BDD checks for graph candidates |
| Version/context reuse | Which unchanged regions or specialized residual programs will repay preparation | Verify dependencies/context keys; compare ordinary incremental compilation, memoization, incremental SAT/BDD |
| Backend selection | Predict cost including setup, query count, feature cost, and memory limits | Exact backend results; compare fixed choices, a cheap explicit rule, and a small tree |

Concrete motif labels can include repeated/complementary cofactors, irrelevant
variables, affine/XOR structure, mux structure, symmetry, and disjoint-support
AND or XOR decompositions. Local deterministic detectors are essential controls;
many of these patterns can already be found very cheaply.

For an aligned variable partition, a disjoint conjunction can have matrix form
`M = a b^T`, and an XOR of such terms has form `M = XOR_i a_i b_i^T`.
Here multiplication is Boolean AND and addition is XOR: rank/factorization is
over GF(2), not approximate floating-point SVD. A network could propose a
promising partition; exact algebra would establish the decomposition. A lower
rank is not automatically a faster executable representation once factor
construction, storage, and subsequent query costs are charged.

For two already materialized, aligned CMs, equality, AND/OR/XOR, quotient
`A AND NOT B`, and popcount are strong packed-bit operations. Replacing them
with neural inference is a low-priority negative control. Searching a large
library for a useful relation or rewrite is a different, more plausible target.

## Representation and model size

Compare three input representations on matched tasks:

1. Small dense CMs/cofactor blocks: fixed-support 4-, 6-, and 8-variable functions
   give 4x4, 8x8, and 16x16 balanced layouts. A small CNN or MLP is a reasonable
   experimental baseline for motif/rule scoring, not a default winner.
2. A shared recursive block representation: useful if block structure exists
   and is available cheaply. Compare with exact block deduplication first.
3. The source expression/AIG/CM-IR graph: preserve operator types, edge roles,
   negations, sharing, and variable identity. Use small CMs or sampled semantics
   for training supervision. A graph neural network can score candidates without
   requiring a dense full-function table as its input.

For a first neural comparison, a roughly 50,000–250,000-parameter local-block
or graph scorer is a reasonable proposed budget, not a measured optimum.
A 64-channel graph model with a few message-passing layers is a candidate.
Always report actual parameter count, activation/graph memory, inference latency,
and training cost. The 48-formula pilot is not enough to justify such a model.
No LLM is needed. Binary inputs do not imply binary weights/activations; a
binarized network would be a separate experimental choice.

CM layout must include the variable partition/order and bit convention. A pixel
rotation is not automatically a semantics-preserving augmentation. Swapping or
negating inputs changes how the function is indexed; output negation changes
the function. Augment with explicit transformations and correctly transformed
labels. Binary-count neighbors are not always one-variable Hamming neighbors,
so ordinary image-locality assumptions deserve a direct test.

Keep variable-renamed, permuted, and equivalently rewritten variants grouped
within a split. An embedding is not a collision-free semantic identifier.
Predicting that two functions are similar or equal does not establish equality.

## Size and output limits

An explicit single-output truth table over k independent binary variables has
2^k bits, irrespective of whether displayed as a vector or a matrix. Examples:

| k | Bit-packed output only | Same values as float32 input |
| --- | ---: | ---: |
| 16 | 8 KiB | 256 KiB |
| 24 | 2 MiB | 64 MiB |
| 32 | 512 MiB | 16 GiB |
| 40 | 128 GiB | 4 TiB |

These exclude masks, intermediate arrays, activations, and multiple outputs.
Sixteen variables is a pilot admission limit, not a universal mathematical
maximum. Expression size and live variable support are separate quantities.
A very large expression can still have small support or a compact decomposition.

If the benchmark starts with an expression and asks for its CM, giving a model
that already-built CM for free is circular. Charge construction, or use a
graph/block input available before construction. Training on arbitrary random
truth tables offers no guarantee of useful structure or shorter exact outputs.

## Fit to the existing master explainer

Reviewed the current embedded data in
`deliverables_n22_24/master_explainer_2026_08_03/index.html`, including its
2026-08-27 eight-field benchmark catalog and 2026-08-28 feature-model update.
These are the site's research scenarios, not evidence of deployed performance.

| Scenario | Neural experiment worth prioritizing | Task-matched comparisons |
| --- | --- | --- |
| Configuration/product families | Predict useful partial-context specialization and decomposition across sessions/versions | Incremental SAT, BDD configurator, exact CM/CSE, cached compiled predicates |
| Hardware cone/version workflows | Rank equivalent/complementary cone candidates and rewrite choices | ABC/AIG, CSE-flat, CM, SAT miter, CUDD |
| Security-policy version audit | Rank changed regions and restriction strategies; never predict final authorization | Native policy authority on a verified Boolean subset, BDD/SAT audit, ordinary incremental code |
| Pure Boolean compiler predicates | Rank local rewrites and known-fact specialization | Deterministic compiler rules, equality saturation, CSE-flat, BDD/SAT |
| Biological update rules | Rank shared-rule reuse and intervention simplification | Compiled update functions and domain tools with identical update semantics |
| Agent guardrails / regulated rules | Apply the same offline Boolean analysis, retaining native rich-language semantics | Native enforcement/decision-table engine and exact audit baselines |
| Classical reversible control logic | Rank Boolean rewrites with explicit constants and output conventions | Reversible simulator / Boolean equivalence checks; no quantum-state claim |

Configuration is the site's strongest first domain recommendation; hardware
already supplies real circuit-derived material. Those are the best first two
domains for this learning experiment as well. The remaining domains need valid
importers and natural traces before domain-performance claims.

The existing results also caution against one global training label such as
"CM always wins": the site's formula-balanced B2/B4 bare-kernel CM/CSE-flat
time ratio is about 0.891, whereas blocked EPFL is about 1.000 with an interval
crossing parity. Preparation and wrapper boundaries matter. These are recorded
site results, not independently rerun performance measurements in this review.

Feature-model performance remains marked provisional with measurement gaps.
At k=16 its point-query data contain 86 valid queries out of 20,480. A classifier
that always says "invalid" would score about 99.58% accuracy and still fail
every valid query. Raw classification accuracy is therefore the wrong success
criterion for an exact configurator. Likewise, a small Hamming difference can
contain a consequential policy change; approximate similarity is not safe diff.

## Fair experiment design

1. Fix the task and artifact: complete vector, point/partial query, equivalence,
   exact count, compact executable representation, or version delta. Do not mix
   those contracts into one speed ranking. Uniform assignment samples do not
   certify equivalence, unsatisfiability, exact count, or lossless compression.
2. Use exact labels from independent Boolean execution or proof-producing
   backends. Candidate rule/factor outputs require complete local checking,
   or a suitable proof at larger support. Unknown/timeout means reject/fallback,
   not accept. Admitted universal rules can reuse their proofs and check only
   applicability; do not repeatedly redo an expensive universal proof.
3. Compare fixed exact methods, exact cache/motif tables, cheap rules, tiny trees,
   and neural policies under equal candidate/search budgets. Compare the same
   neural architecture on CM versus graph inputs, with construction charged.
4. Split by original circuit/model history, not individual matrix pixels,
   timing rounds, neighboring versions, or renamed copies. Use held-out families,
   larger support, new compositions, dense/random negative controls, and hard
   near-matches. Keep training/validation/confirmatory test roles separate.
5. Start with supervised cost/ranking labels or imitation from bounded exact
   search. Add counterexamples and hard negatives to a subsequent training set,
   never to a frozen test. Consider reinforcement learning only if multi-step
   choices have measurable long-term effects and a cheaper supervised baseline
   leaves opportunity. Distillation and quantization are later latency ablations.
6. Measure end-to-end preparation + feature extraction + inference + exact work
   + required proof/check + fallback. Include conversion, transfers, model load,
   batching delay, and lost sharing. Report cold, warm, repeated-context, and
   version-update cells separately, plus baseline caching on equivalent terms.
7. Report wall time, peak memory, proof failures, refusal/coverage, total output
   correctness, tail slowdown, search budget, and training/data-generation cost.
   Cluster uncertainty by independent source/history, not repeated timing rows.
   Record models that never repay preparation. Retain raw rows and all failures.

For a repeated-query optimization, compare
`learned_setup + Q * learned_query` with `baseline_setup + Q * baseline_query`.
Put inference/check cost in setup only if it is genuinely reusable across those
queries; otherwise charge it per query. Total saved work must exceed added work.

## Related research: precedent, not a CM performance result

[DeepGate2](https://arxiv.org/abs/2305.16373) uses truth-table differences as
supervision for circuit graph representations and evaluates downstream synthesis
and SAT tasks. It is a close precedent for using CM semantics as a teacher.
[DeepGate3](https://arxiv.org/abs/2407.11095) adds hierarchical/subcircuit modeling
to a graph-based architecture. Neither establishes that a dense-CM neural model
will beat this repository's exact implementations.

[NeuRewriter](https://arxiv.org/abs/1810.00337) investigates learned local rewrite
choices for combinatorial optimization. [egg](https://arxiv.org/abs/2004.03082)
provides an efficient equality-saturation baseline for exploring admitted
rewrites. An e-graph does not make an arbitrary neural-proposed equality sound.
Those mechanisms inform candidate selection; exact CM semantics remain separate.

## Source integrity and a labeling correction

Attached PDF SHA-256:
`7a9958a2ec34e61318855a3e8054d668c7d9654de3316c4fe546f7db7a2503a9`.
Reviewed master-explainer HTML SHA-256:
`9e91b74ffc1d978ef05fdafcbae57ba02c49423c3e1c6d8bdee02635a44ad93d`.

One worked example on paper page 12 appears to have a variable-name typo:
`(X implies Y) XOR (X OR Y)` is `NOT Y`, rather than the printed `NOT X`.
For X=1,Y=0, the left side is 1 while NOT X is 0. All four assignments were
independently checked. The pointwise-CM composition rule itself passes the finite
check above. Generate future learning labels mechanically; do not transcribe
worked-example conclusions without verification. This review did not edit the
paper or claim a complete formal audit of it.
