# CM candidate video catalog

Status: **proposed, not approved**

Candidates: 45

## Proposed first wave

1. **What a correspondence matrix is** (`what-is-explicit-cm`) — core_explainer; Build the row/column truth layout from assignments.
2. **Explicit dense CM versus CM-IR** (`explicit-cm-vs-cm-ir`) — core_explainer; Compare truth layout with a canonical computation graph.
3. **Plain CSE versus sharing-aware CSE-flat** (`cse-vs-cse-flat`) — core_explainer; Show safe associative flattening without destroying shared nodes.
4. **CM-IR versus CSE-flat: common ground and extra transformations** (`cm-ir-vs-cse-flat-mechanism`) — core_explainer; Attribute reductions to sharing, flattening, normalization, or merging.
5. **Preparation, kernel, wrapper, and end-to-end time** (`measurement-boundaries`) — core_explainer; Place every cost on a boundary pipeline.
6. **Corrected B2/B4 V3 kernel result** (`b2b4-corrected`) — core_explainer; Read the formula-balanced interval and the narrowing k-dependence.
7. **EPFL AND/INV parity and its mechanism** (`epfl-parity`) — core_explainer; Show why equal instruction structure predicted parity.
8. **How to read a CM/comparator ratio** (`read-a-ratio`) — visual_short; Name direction, scope, interval, and boundary before reading position.
9. **How an audit changed the headline** (`correction-story`) — core_explainer; Walk from weak comparator language to scoped corrected claims.
10. **D8 Linux confirmation: exact but unprofitable** (`recognition-d8`) — visual_short; Show a successful verification with a negative promotion result.

## Learning paths

### nontechnical

Explain what CM is, what it is not, and how to read scoped evidence.

why-boolean-computation → expression-truth-function → live-support-ambient → what-is-explicit-cm → what-cm-does-not-claim → explicit-cm-vs-cm-ir → read-a-ratio → scope-boundaries → correction-story

### technical-research

Trace representation, compiler transformations, measurement boundaries, inference, and negative promotion results.

expression-truth-function → explicit-cm-vs-cm-ir → cm-ir-nodes-sharing → canonicalization-interning → cse-vs-cse-flat → cm-ir-vs-cse-flat-mechanism → measurement-boundaries → b2b4-corrected → epfl-parity → exact-comparison-protocol → recognition-question → recognition-d8

## Full catalog

### Why Boolean computation matters (`why-boolean-computation`)

- Track / tier / priority: Foundations / visual_short / P1
- Central question: Why Boolean computation matters?
- Viewer outcome: Show how one decision rule becomes assignments and outputs.
- Prerequisites: none
- Claims: cm-explicit-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Expression, truth table, and Boolean function (`expression-truth-function`)

- Track / tier / priority: Foundations / core_explainer / P1
- Central question: Expression, truth table, and Boolean function?
- Viewer outcome: Separate syntax from the function it denotes.
- Prerequisites: why-boolean-computation
- Claims: cm-explicit-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Live support versus ambient variables (`live-support-ambient`)

- Track / tier / priority: Foundations / visual_short / P1
- Central question: Live support versus ambient variables?
- Viewer outcome: Explain why nominal width can overstate the active problem.
- Prerequisites: expression-truth-function
- Claims: live-vs-ambient
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### What a correspondence matrix is (`what-is-explicit-cm`)

- Track / tier / priority: Foundations / core_explainer / P0
- Central question: What a correspondence matrix is?
- Viewer outcome: Build the row/column truth layout from assignments.
- Prerequisites: expression-truth-function
- Claims: cm-explicit-definition, live-vs-ambient
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### What CM does not claim to be (`what-cm-does-not-claim`)

- Track / tier / priority: Foundations / visual_short / P1
- Central question: What CM does not claim to be?
- Viewer outcome: Refuse speed, solver, and universal representation overclaims.
- Prerequisites: what-is-explicit-cm
- Claims: dense-vs-ir-distinct, no-universal-winner
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Explicit dense CM versus CM-IR (`explicit-cm-vs-cm-ir`)

- Track / tier / priority: Foundations / core_explainer / P0
- Central question: Explicit dense CM versus CM-IR?
- Viewer outcome: Compare truth layout with a canonical computation graph.
- Prerequisites: what-is-explicit-cm
- Claims: cm-ir-definition, dense-vs-ir-distinct
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### CM-IR nodes, sharing, and roots (`cm-ir-nodes-sharing`)

- Track / tier / priority: Representations / core_explainer / P1
- Central question: CM-IR nodes, sharing, and roots?
- Viewer outcome: Read a CMNode DAG and identify reuse.
- Prerequisites: explicit-cm-vs-cm-ir
- Claims: cm-ir-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Canonicalization, interning, and normalization (`canonicalization-interning`)

- Track / tier / priority: Representations / core_explainer / P1
- Central question: Canonicalization, interning, and normalization?
- Viewer outcome: Show which rewrites change keys and which preserve meaning.
- Prerequisites: cm-ir-nodes-sharing
- Claims: cm-ir-definition, cm-extra-transformations
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Eager and lazy CM paths (`eager-lazy`)

- Track / tier / priority: Representations / visual_short / P1
- Central question: Eager and lazy CM paths?
- Viewer outcome: Distinguish when dense work is performed, without inventing a ranking.
- Prerequisites: explicit-cm-vs-cm-ir
- Claims: variants-implemented
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Pair-aware CM collapse (`pair-aware`)

- Track / tier / priority: Representations / visual_short / P1
- Central question: Pair-aware CM collapse?
- Viewer outcome: Explain the fixed-input and two-live-variable eligibility boundary.
- Prerequisites: cm-ir-nodes-sharing
- Claims: variants-implemented
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Hybrid versus partial-hybrid materialization (`hybrid-partial`)

- Track / tier / priority: Representations / core_explainer / P1
- Central question: Hybrid versus partial-hybrid materialization?
- Viewer outcome: Separate full bitset collapse from child-level hybrid dispatch.
- Prerequisites: cm-ir-nodes-sharing
- Claims: variants-implemented
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Parallel CM materialization (`parallel-cm`)

- Track / tier / priority: Representations / visual_short / P1
- Central question: Parallel CM materialization?
- Viewer outcome: Show where parallelism applies and why it is secondary to work reduction.
- Prerequisites: hybrid-partial
- Claims: variants-implemented
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Packed bitsets, words, and width selection (`packed-words-selection`)

- Track / tier / priority: Representations / core_explainer / P1
- Central question: Packed bitsets, words, and width selection?
- Viewer outcome: Connect support width to packed execution without claiming width alone is sufficient.
- Prerequisites: live-support-ambient
- Claims: variants-implemented, selector-no-width-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### CM-IR persistence and version identity (`cm-ir-persistence`)

- Track / tier / priority: Representations / deep_dive / P1
- Central question: CM-IR persistence and version identity?
- Viewer outcome: Trace canonical hashes, reload, invalidation, and exact byte checks.
- Prerequisites: canonicalization-interning
- Claims: cm-ir-definition, exactness-gates
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Raw AST evaluation as an ablation (`raw-ast`)

- Track / tier / priority: Comparators / visual_short / P1
- Central question: Raw AST evaluation as an ablation?
- Viewer outcome: Explain why raw AST is informative but not the strongest comparator.
- Prerequisites: expression-truth-function
- Claims: cse-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Common subexpression elimination in plain language (`cse-plain-language`)

- Track / tier / priority: Comparators / visual_short / P1
- Central question: Common subexpression elimination in plain language?
- Viewer outcome: Animate one repeated subtree becoming one shared result.
- Prerequisites: raw-ast
- Claims: cse-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Plain CSE versus sharing-aware CSE-flat (`cse-vs-cse-flat`)

- Track / tier / priority: Comparators / core_explainer / P0
- Central question: Plain CSE versus sharing-aware CSE-flat?
- Viewer outcome: Show safe associative flattening without destroying shared nodes.
- Prerequisites: cse-plain-language
- Claims: cse-definition, cse-flat-definition
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### CM-IR versus CSE-flat: common ground and extra transformations (`cm-ir-vs-cse-flat-mechanism`)

- Track / tier / priority: Comparators / core_explainer / P0
- Central question: CM-IR versus CSE-flat: common ground and extra transformations?
- Viewer outcome: Attribute reductions to sharing, flattening, normalization, or merging.
- Prerequisites: cse-vs-cse-flat, canonicalization-interning
- Claims: cse-flat-definition, cm-extra-transformations
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Instructions, primitive operations, and memory traffic (`instruction-operations-memory`)

- Track / tier / priority: Comparators / deep_dive / P1
- Central question: Instructions, primitive operations, and memory traffic?
- Viewer outcome: Keep three proposed mechanisms separate and measurable.
- Prerequisites: cm-ir-vs-cse-flat-mechanism
- Claims: epfl-mechanism, no-universal-winner
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Why one blended fastest-method chart is dishonest (`no-fastest-chart`)

- Track / tier / priority: Comparators / visual_short / P1
- Central question: Why one blended fastest-method chart is dishonest?
- Viewer outcome: Expose incomparable boundaries before ranking anything.
- Prerequisites: cm-ir-vs-cse-flat-mechanism
- Claims: no-universal-winner, ratio-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Preparation, kernel, wrapper, and end-to-end time (`measurement-boundaries`)

- Track / tier / priority: Performance / core_explainer / P0
- Central question: Preparation, kernel, wrapper, and end-to-end time?
- Viewer outcome: Place every cost on a boundary pipeline.
- Prerequisites: cm-ir-vs-cse-flat-mechanism
- Claims: b2b4-v3-kernel, public-wrapper-slower, epfl-preparation-cost
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Reuse and break-even economics (`reuse-break-even`)

- Track / tier / priority: Performance / core_explainer / P1
- Central question: Reuse and break-even economics?
- Viewer outcome: Animate one-time cost and per-evaluation cost without implying all cases break even.
- Prerequisites: measurement-boundaries
- Claims: epfl-preparation-cost
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Corrected B2/B4 V3 kernel result (`b2b4-corrected`)

- Track / tier / priority: Performance / core_explainer / P0
- Central question: Corrected B2/B4 V3 kernel result?
- Viewer outcome: Read the formula-balanced interval and the narrowing k-dependence.
- Prerequisites: measurement-boundaries, cse-vs-cse-flat
- Claims: b2b4-v3-kernel, b2b4-v3-k16, exactness-gates
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Three-pod B2/B4 replication (`b2b4-runpod`)

- Track / tier / priority: Performance / visual_short / P1
- Central question: Three-pod B2/B4 replication?
- Viewer outcome: Distinguish descriptive machine replication from the local interval.
- Prerequisites: b2b4-corrected
- Claims: b2b4-runpod-replication
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### EPFL AND/INV parity and its mechanism (`epfl-parity`)

- Track / tier / priority: Performance / core_explainer / P0
- Central question: EPFL AND/INV parity and its mechanism?
- Viewer outcome: Show why equal instruction structure predicted parity.
- Prerequisites: cse-vs-cse-flat, measurement-boundaries
- Claims: epfl-parity, epfl-mechanism, epfl-preparation-cost
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Why width alone did not select the engine (`selector-width-limit`)

- Track / tier / priority: Performance / core_explainer / P1
- Central question: Why width alone did not select the engine?
- Viewer outcome: Read regret gates and reused-validation limitations.
- Prerequisites: packed-words-selection
- Claims: selector-no-width-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Truth digests, alternating schedules, clustering, and intervals (`exact-comparison-protocol`)

- Track / tier / priority: Performance / deep_dive / P1
- Central question: Truth digests, alternating schedules, clustering, and intervals?
- Viewer outcome: Explain how exactness and dependence-aware inference protect a timing claim.
- Prerequisites: b2b4-corrected
- Claims: exactness-gates, ratio-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### How an audit changed the headline (`correction-story`)

- Track / tier / priority: Performance / core_explainer / P0
- Central question: How an audit changed the headline?
- Viewer outcome: Walk from weak comparator language to scoped corrected claims.
- Prerequisites: b2b4-corrected, epfl-parity
- Claims: b2b4-v3-kernel, no-universal-winner, exactness-gates
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions (`toolbox-map`)

- Track / tier / priority: Toolbox / deep_dive / P1
- Central question: CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions?
- Viewer outcome: Map representations and solvers only to retained evidence and interfaces.
- Prerequisites: what-cm-does-not-claim
- Claims: variants-implemented, no-universal-winner
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Configuration and feature-model workloads (`configuration-models`)

- Track / tier / priority: Applications / deep_dive / P1
- Central question: Configuration and feature-model workloads?
- Viewer outcome: Separate retained pilots, version deltas, persistence, and direct-task baselines.
- Prerequisites: toolbox-map
- Claims: no-universal-winner
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Circuit workloads: structure, truth, and exact controls (`circuits`)

- Track / tier / priority: Applications / core_explainer / P1
- Central question: Circuit workloads: structure, truth, and exact controls?
- Viewer outcome: Explain cone support and why AND/INV shape matters.
- Prerequisites: toolbox-map
- Claims: epfl-parity, exactness-gates
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Policy and rule systems with related revisions (`policy-rule-systems`)

- Track / tier / priority: Applications / core_explainer / P1
- Central question: Policy and rule systems with related revisions?
- Viewer outcome: Frame canonical reuse as a measured question, not a guaranteed win.
- Prerequisites: toolbox-map
- Claims: crse-d-mixed
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Which representation should I try? (`representation-decision`)

- Track / tier / priority: Applications / core_explainer / P1
- Central question: Which representation should I try??
- Viewer outcome: Choose based on output, reuse, support, exact operations, and evidence status.
- Prerequisites: toolbox-map, measurement-boundaries
- Claims: dense-vs-ir-distinct, no-universal-winner, selector-no-width-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### What the CRSE recognition program asks (`recognition-question`)

- Track / tier / priority: Recognition / core_explainer / P1
- Central question: What the CRSE recognition program asks?
- Viewer outcome: Separate proposal learning from exact verification and promotion.
- Prerequisites: cm-ir-nodes-sharing
- Claims: crse-experimental, conceptual-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### C2 variable-size decomposition: exact control, learned failure (`recognition-c2`)

- Track / tier / priority: Recognition / core_explainer / P1
- Central question: C2 variable-size decomposition: exact control, learned failure?
- Viewer outcome: State frozen split, comparator, failure, and no-promotion decision.
- Prerequisites: recognition-question
- Claims: crse-c2-negative
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### C3–C5 natural cuts: improvements without held-out promotion (`recognition-c3-c5`)

- Track / tier / priority: Recognition / deep_dive / P1
- Central question: C3–C5 natural cuts: improvements without held-out promotion?
- Viewer outcome: Track natural positives, matched negatives, cut heads, and transfer failures.
- Prerequisites: recognition-c2
- Claims: crse-c3-c5-negative
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### C6 packed exact source ANF: what advanced and what did not (`recognition-c6`)

- Track / tier / priority: Recognition / core_explainer / P1
- Central question: C6 packed exact source ANF: what advanced and what did not?
- Viewer outcome: Promote the deterministic core only within its passed criterion.
- Prerequisites: recognition-c3-c5
- Claims: crse-c6-advance
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Milestone D task routing: mixed boundaries (`recognition-d-tasks`)

- Track / tier / priority: Recognition / core_explainer / P1
- Central question: Milestone D task routing: mixed boundaries?
- Viewer outcome: Compare complete vectors, points, restrictions, and repeated work separately.
- Prerequisites: recognition-question, measurement-boundaries
- Claims: crse-d-mixed
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### D8 Linux confirmation: exact but unprofitable (`recognition-d8`)

- Track / tier / priority: Recognition / visual_short / P0
- Central question: D8 Linux confirmation: exact but unprofitable?
- Viewer outcome: Show a successful verification with a negative promotion result.
- Prerequisites: recognition-d-tasks
- Claims: crse-d8-negative
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### D9 abstention policy: safe, charged, not promoted (`recognition-d9`)

- Track / tier / priority: Recognition / core_explainer / P1
- Central question: D9 abstention policy: safe, charged, not promoted?
- Viewer outcome: Separate correct abstention from profitable deployment.
- Prerequisites: recognition-d8
- Claims: crse-d9-not-promoted
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### How to read a CM/comparator ratio (`read-a-ratio`)

- Track / tier / priority: Evidence literacy / visual_short / P0
- Central question: How to read a CM/comparator ratio?
- Viewer outcome: Name direction, scope, interval, and boundary before reading position.
- Prerequisites: measurement-boundaries
- Claims: ratio-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Why scopes and boundaries matter (`scope-boundaries`)

- Track / tier / priority: Evidence literacy / visual_short / P1
- Central question: Why scopes and boundaries matter?
- Viewer outcome: Compare B2/B4, EPFL, preparation, kernel, and wrapper without pooling.
- Prerequisites: read-a-ratio
- Claims: no-universal-winner, ratio-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Conceptual animation versus measured result (`conceptual-vs-measured`)

- Track / tier / priority: Evidence literacy / visual_short / P1
- Central question: Conceptual animation versus measured result?
- Viewer outcome: Teach the status grammar used in every video.
- Prerequisites: none
- Claims: conceptual-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### How a video is bound to source hashes (`source-hash-reproduction`)

- Track / tier / priority: Evidence literacy / core_explainer / P1
- Central question: How a video is bound to source hashes?
- Viewer outcome: Trace source registry to claim, brief, render job, result, and batch identity.
- Prerequisites: conceptual-vs-measured
- Claims: exactness-gates, conceptual-label-rule
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries

### Correspondence Matrices: From Representation to Honest Evidence (`cm-flagship-representation-to-evidence-v1`)

- Track / tier / priority: Long-form / deep_dive / P0
- Central question: Correspondence Matrices: From Representation to Honest Evidence?
- Viewer outcome: Follow the complete seven-chapter path from truth layout through transformation mechanisms to scoped corrected evidence.
- Prerequisites: what-is-explicit-cm, explicit-cm-vs-cm-ir, cm-ir-vs-cse-flat-mechanism, measurement-boundaries
- Claims: cm-explicit-definition, cm-ir-definition, cse-flat-definition, b2b4-v3-kernel, epfl-parity, no-universal-winner
- Caveats: Use only retained evidence within its declared scope; Do not pool incomparable boundaries
