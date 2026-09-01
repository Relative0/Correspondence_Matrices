# CM candidate video catalog

Status: **proposed, not approved**

Candidates: 52

## Proposed first wave

1. **Conceptual animation versus measured result** (`conceptual-vs-measured`) — visual_short; Read the status before reading the result.
2. **What a correspondence matrix is** (`what-is-explicit-cm`) — core_explainer; The matrix changes the layout, not the underlying Boolean function.
3. **Explicit dense CM versus CM-IR** (`explicit-cm-vs-cm-ir`) — core_explainer; The matrix is an output layout; CM-IR is a program that can produce outputs.
4. **Plain CSE versus sharing-aware CSE-flat** (`cse-vs-cse-flat`) — core_explainer; CSE-flat strengthens plain CSE without sacrificing the sharing that made CSE useful.
5. **From DAGs to flat instructions: operations, storage, and execution** (`instruction-operations-memory`) — deep_dive; Flat syntax, flat instructions, and packed storage are different stages of one execution pipeline.
6. **Preparation, kernel, wrapper, and end-to-end time** (`measurement-boundaries`) — core_explainer; The boundary is part of the result, not a footnote to it.
7. **How to read a CM/comparator ratio** (`read-a-ratio`) — visual_short; A ratio becomes evidence only after its direction and scope are explicit.
8. **Corrected B2/B4 V3 kernel result** (`b2b4-corrected`) — core_explainer; The bare-kernel result survived correction; the universal speed claim did not.
9. **EPFL AND/INV parity and its mechanism** (`epfl-parity`) — core_explainer; No extra structural reduction meant no accepted kernel advantage on this workload.
10. **How an audit changed the headline** (`correction-story`) — core_explainer; A good audit changes the claim without pretending the history never happened.
11. **D8 Linux confirmation: exact but unprofitable** (`recognition-d8`) — visual_short; D8 is an exact engineering success and a profitability failure at the same time.

## Learning paths

### general

Explain Boolean functions, CM artifacts, comparator fairness, and scoped evidence before choosing a representation.

conceptual-vs-measured → why-boolean-computation → expression-truth-function → live-support-ambient → what-is-explicit-cm → what-cm-does-not-claim → explicit-cm-vs-cm-ir → cse-plain-language → cse-vs-cse-flat → measurement-boundaries → read-a-ratio → scope-boundaries → toolbox-map → representation-decision → source-hash-reproduction

### technical-research

Trace every v2 lesson from evidence grammar through representation, execution, comparison, applications, CRSE, and provenance.

conceptual-vs-measured → why-boolean-computation → expression-truth-function → live-support-ambient → what-is-explicit-cm → what-cm-does-not-claim → explicit-cm-vs-cm-ir → cm-ir-nodes-sharing → canonicalization-interning → cm-ir-persistence → packed-words-selection → eager-lazy → pair-aware → hybrid-partial → parallel-cm → raw-ast → cse-plain-language → cse-vs-cse-flat → cm-ir-vs-cse-flat-mechanism → instruction-operations-memory → measurement-boundaries → read-a-ratio → scope-boundaries → reuse-break-even → b2b4-corrected → b2b4-runpod → epfl-parity → selector-width-limit → exact-comparison-protocol → no-fastest-chart → correction-story → toolbox-map → configuration-models → circuits → policy-rule-systems → representation-decision → recognition-question → recognition-c2 → recognition-c3-c5 → recognition-c6 → recognition-c9-c11 → recognition-c12-c16 → recognition-c17-c20 → recognition-c21-c22 → recognition-c23 → recognition-d-tasks → recognition-d8 → recognition-d9 → recognition-d10 → recognition-e1-e2 → source-hash-reproduction

### recognition-research

Follow the current CRSE arc from proposal learning through exact guarded systems and retained negative results.

recognition-question → recognition-c2 → recognition-c3-c5 → recognition-c6 → recognition-c9-c11 → recognition-c12-c16 → recognition-c17-c20 → recognition-c21-c22 → recognition-c23 → recognition-d-tasks → recognition-d8 → recognition-d9 → recognition-d10 → recognition-e1-e2

## Full catalog

### Conceptual animation versus measured result (`conceptual-vs-measured`)

- Track / tier / priority: Series orientation / visual_short / P0
- Central question: Did this animation happen in an experiment, or is it only showing how an idea could work?
- Viewer outcome: Read the status before reading the result.
- Prerequisites: none
- Claims: conceptual-label-rule
- Caveats: A clear diagram is not evidence until its source, scope, boundary, and uncertainty are attached.

### Why Boolean computation matters (`why-boolean-computation`)

- Track / tier / priority: Boolean functions and explicit CM / visual_short / P1
- Central question: How do we turn a rule that sounds reasonable into something every machine must answer the same way?
- Viewer outcome: The stable object is the assignment-to-output mapping, not the syntax or storage chosen later.
- Prerequisites: conceptual-vs-measured
- Claims: boolean-decision-semantics
- Caveats: This lesson motivates exact Boolean computation; it does not establish that CM is the best representation for every task.

### Expression, truth table, and Boolean function (`expression-truth-function`)

- Track / tier / priority: Boolean functions and explicit CM / core_explainer / P1
- Central question: If two formulas look different, are they necessarily different computations?
- Viewer outcome: Syntax can change while the function remains identical.
- Prerequisites: why-boolean-computation
- Claims: boolean-decision-semantics, expression-function-distinction
- Caveats: Matching one or two examples is not equivalence; the declared assignment universe must match exactly.

### Live support versus ambient variables (`live-support-ambient`)

- Track / tier / priority: Boolean functions and explicit CM / visual_short / P1
- Central question: Why can a six-variable table contain a function that really depends on only three variables?
- Viewer outcome: Nominal width and semantic support answer different questions.
- Prerequisites: expression-truth-function
- Claims: live-vs-ambient
- Caveats: Smaller live support changes the active problem description, but it does not by itself select the fastest engine.

### What a correspondence matrix is (`what-is-explicit-cm`)

- Track / tier / priority: Boolean functions and explicit CM / core_explainer / P0
- Central question: How can one truth table become a two-dimensional object without changing a single output?
- Viewer outcome: The matrix changes the layout, not the underlying Boolean function.
- Prerequisites: expression-truth-function
- Claims: cm-explicit-definition, live-vs-ambient
- Caveats: The matrix is a dense output layout; this definition does not make it compact, a solver, or universally fast.

### What CM does not claim to be (`what-cm-does-not-claim`)

- Track / tier / priority: Boolean functions and explicit CM / visual_short / P1
- Central question: What goes wrong when one method name is used as the answer to three different questions?
- Viewer outcome: CM is one exact representation family, not a universal answer label.
- Prerequisites: what-is-explicit-cm
- Claims: cm-output-contract-boundary, dense-vs-ir-distinct, no-universal-winner
- Caveats: Current evidence supports scoped comparisons, not a claim that CM wins every task or boundary.

### Explicit dense CM versus CM-IR (`explicit-cm-vs-cm-ir`)

- Track / tier / priority: Boolean functions and explicit CM / core_explainer / P0
- Central question: When a benchmark says CM, is it timing a matrix, a program graph, or a wrapper that creates both?
- Viewer outcome: The matrix is an output layout; CM-IR is a program that can produce outputs.
- Prerequisites: what-is-explicit-cm, what-cm-does-not-claim
- Claims: cm-ir-definition, dense-vs-ir-distinct, cm-output-contract-boundary
- Caveats: A CM-IR kernel result is not automatically a dense-CM or public-wrapper result.

### CM-IR nodes, sharing, and roots (`cm-ir-nodes-sharing`)

- Track / tier / priority: CM-IR representation and identity / core_explainer / P1
- Central question: If the same Boolean subproblem appears twice, why store and compute it twice?
- Viewer outcome: One node can serve several consumers without changing the function.
- Prerequisites: explicit-cm-vs-cm-ir
- Claims: cm-ir-definition, cm-ir-sharing-roots
- Caveats: Sharing reduces repeated structure, but the amount of reduction depends on the expression and canonicalization rules.

### Canonicalization, interning, and normalization (`canonicalization-interning`)

- Track / tier / priority: CM-IR representation and identity / core_explainer / P1
- Central question: What has to happen before two differently written subexpressions can share one node?
- Viewer outcome: Equivalent structure becomes reusable only after its identity is made explicit.
- Prerequisites: cm-ir-nodes-sharing
- Claims: cm-ir-normalization-interning, cm-extra-transformations
- Caveats: Canonicalization is implementation scoped; it does not prove a globally minimal representation.

### CM-IR persistence and version identity (`cm-ir-persistence`)

- Track / tier / priority: CM-IR representation and identity / deep_dive / P1
- Central question: When is a graph saved yesterday still the right graph for today's source?
- Viewer outcome: Persistence is an identity and invalidation contract, not merely saving bytes.
- Prerequisites: canonicalization-interning
- Claims: cm-ir-persistence-contract, source-provenance-contract
- Caveats: A hash match supports identity checking; it does not by itself establish scientific truth or permit stale reuse.

### Packed truth vectors: big integers, machine words, and masks (`packed-words-selection`)

- Track / tier / priority: Execution and materialization paths / core_explainer / P1
- Central question: How can one machine operation evaluate many assignments at the same time?
- Viewer outcome: Packed storage changes how outputs travel through the machine, not what outputs mean.
- Prerequisites: live-support-ambient, explicit-cm-vs-cm-ir
- Claims: packed-truth-vector-contract
- Caveats: Packing is an exact execution layout, not a dense CM and not evidence that words are always faster than bigint.

### Eager and lazy CM paths (`eager-lazy`)

- Track / tier / priority: Execution and materialization paths / visual_short / P1
- Central question: If both paths return the same output, what exactly makes one eager and the other lazy?
- Viewer outcome: Eager and lazy change scheduling, not semantics.
- Prerequisites: explicit-cm-vs-cm-ir, cm-ir-nodes-sharing
- Claims: eager-lazy-contract
- Caveats: The implementation distinction does not establish a universal performance ranking.

### Pair-aware CM collapse (`pair-aware`)

- Track / tier / priority: Execution and materialization paths / visual_short / P1
- Central question: When can a larger expression safely collapse to one tiny row-column pair?
- Viewer outcome: One live variable per axis makes the pair path possible; everything else stays on the exact fallback path.
- Prerequisites: cm-ir-nodes-sharing, live-support-ambient
- Claims: pair-aware-contract
- Caveats: Pair eligibility is experimental and local; ineligible cases must fall back without changing semantics.

### Hybrid versus partial-hybrid materialization (`hybrid-partial`)

- Track / tier / priority: Execution and materialization paths / core_explainer / P1
- Central question: Does hybrid execution collapse the whole graph, or can it preserve structure and choose child by child?
- Viewer outcome: Hybrid changes the materialization boundary; partial-hybrid changes it selectively.
- Prerequisites: cm-ir-nodes-sharing, packed-words-selection
- Claims: hybrid-partial-contract, packed-truth-vector-contract
- Caveats: These are implemented strategies, not guarantees that one wins every support size or workload.

### Parallel CM materialization (`parallel-cm`)

- Track / tier / priority: Execution and materialization paths / visual_short / P1
- Central question: If rows can be computed independently, why not always send every row to another worker?
- Viewer outcome: Parallelism redistributes work; it does not remove the need to count the work.
- Prerequisites: hybrid-partial
- Claims: parallel-materialization-contract
- Caveats: Parallelism adds scheduling and data-movement cost, so availability is not evidence of a speedup.

### Why a raw expression tree repeats work (`raw-ast`)

- Track / tier / priority: Comparators and lowering / visual_short / P1
- Central question: Why does the evaluator compute A AND B twice when both copies mean the same thing?
- Viewer outcome: The raw tree shows the duplication that later comparators are designed to remove.
- Prerequisites: expression-truth-function
- Claims: raw-ast-ablation-definition
- Caveats: Raw AST is an informative ablation, not the strongest comparator for a system that shares structure.

### Common subexpression elimination in plain language (`cse-plain-language`)

- Track / tier / priority: Comparators and lowering / visual_short / P1
- Central question: What is the simplest way to stop computing the same subtree twice?
- Viewer outcome: Share identical work first; ask about flattening next.
- Prerequisites: raw-ast
- Claims: cse-definition
- Caveats: Plain CSE shares repeats; it does not necessarily flatten an associative chain into a wider instruction.

### Plain CSE versus sharing-aware CSE-flat (`cse-vs-cse-flat`)

- Track / tier / priority: Comparators and lowering / core_explainer / P0
- Central question: Can we widen an AND chain without tearing apart the sharing we just created?
- Viewer outcome: CSE-flat strengthens plain CSE without sacrificing the sharing that made CSE useful.
- Prerequisites: cse-plain-language
- Claims: cse-definition, cse-flat-definition
- Caveats: Always-splice flattening is not the comparator contract; shared children must be preserved.

### CM-IR versus CSE-flat: shared mechanisms and extra transformations (`cm-ir-vs-cse-flat-mechanism`)

- Track / tier / priority: Comparators and lowering / core_explainer / P1
- Central question: After CSE-flat already shares and flattens, what work is actually left for CM-IR to remove?
- Viewer outcome: Common mechanisms belong to both arms; only measured deltas belong to the comparison.
- Prerequisites: cse-vs-cse-flat, canonicalization-interning
- Claims: cse-flat-definition, cm-extra-transformations, cm-ir-normalization-interning
- Caveats: A method label is not a mechanism, and one workload's residual reduction is not universal.

### From DAGs to flat instructions: operations, storage, and execution (`instruction-operations-memory`)

- Track / tier / priority: Comparators and lowering / deep_dive / P0
- Central question: When someone says flat, do they mean a flattened expression, a linear instruction program, or packed bits?
- Viewer outcome: Flat syntax, flat instructions, and packed storage are different stages of one execution pipeline.
- Prerequisites: cm-ir-vs-cse-flat-mechanism, packed-words-selection
- Claims: flat-program-lowering, operation-metrics-distinct, memory-traffic-hypothesis, epfl-mechanism
- Caveats: Instruction and operation counts are measured structural metrics, but hardware memory traffic remains a hypothesis unless measured directly.

### Preparation, kernel, wrapper, and end-to-end time (`measurement-boundaries`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P0
- Central question: How can a kernel be faster while the easy public call is slower?
- Viewer outcome: The boundary is part of the result, not a footnote to it.
- Prerequisites: instruction-operations-memory
- Claims: b2b4-v3-kernel, public-wrapper-slower, epfl-preparation-cost, no-universal-winner
- Caveats: Numbers from different boundaries may be shown together only when they remain visibly separate.

### How to read a CM/comparator ratio (`read-a-ratio`)

- Track / tier / priority: Measurement, evidence, and corrections / visual_short / P0
- Central question: Does a ratio below one mean faster, slower, or nothing at all?
- Viewer outcome: A ratio becomes evidence only after its direction and scope are explicit.
- Prerequisites: measurement-boundaries
- Claims: ratio-label-rule
- Caveats: Position and color cannot substitute for labels, scope, boundary, and uncertainty.

### Why scopes and boundaries matter (`scope-boundaries`)

- Track / tier / priority: Measurement, evidence, and corrections / visual_short / P1
- Central question: Why can't four honest numbers be averaged into one honest winner?
- Viewer outcome: Honest evidence gets narrower before it gets stronger.
- Prerequisites: read-a-ratio
- Claims: no-universal-winner, ratio-label-rule, cm-output-contract-boundary
- Caveats: B2/B4, EPFL, preparation, kernel, and wrapper evidence remain separate when their scopes differ.

### Reuse and break-even economics (`reuse-break-even`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P1
- Central question: How many evaluations does it take to repay a more expensive compilation?
- Viewer outcome: Preparation is a debt; reuse determines whether the debt is ever repaid.
- Prerequisites: measurement-boundaries, read-a-ratio
- Claims: epfl-preparation-cost
- Caveats: Some retained cases never break even, and a modeled crossing is not an end-to-end deployment guarantee.

### Corrected B2/B4 V3 kernel result (`b2b4-corrected`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P0
- Central question: What survives after the comparator, balancing, exactness, and boundary problems are corrected?
- Viewer outcome: The bare-kernel result survived correction; the universal speed claim did not.
- Prerequisites: scope-boundaries, cse-vs-cse-flat
- Claims: b2b4-v3-kernel, b2b4-v3-k16, public-wrapper-slower, exactness-gates
- Caveats: These estimates are conditional on this workload, machine, run, comparator, and boundary.

### Three-pod B2/B4 replication (`b2b4-runpod`)

- Track / tier / priority: Measurement, evidence, and corrections / visual_short / P1
- Central question: What does three-machine agreement add, and what does it still not prove?
- Viewer outcome: Replication adds another scope; it does not erase scope.
- Prerequisites: b2b4-corrected
- Claims: b2b4-runpod-replication, ratio-label-rule
- Caveats: The three pod values are descriptive; they are not a predeclared pooled confidence interval.

### EPFL AND/INV parity and its mechanism (`epfl-parity`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P0
- Central question: What happens when the strong comparator has already captured every associative merge available in the circuit?
- Viewer outcome: No extra structural reduction meant no accepted kernel advantage on this workload.
- Prerequisites: scope-boundaries, cse-vs-cse-flat, measurement-boundaries
- Claims: epfl-parity, epfl-mechanism, epfl-preparation-cost, circuit-cone-support
- Caveats: EPFL parity is scoped to these cones and does not contradict the distinct B2/B4 kernel result.

### Why width alone did not select the engine (`selector-width-limit`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P1
- Central question: If machine words sound natural above a certain width, why not switch at that number?
- Viewer outcome: Width informs the decision; it does not make the decision alone.
- Prerequisites: packed-words-selection, measurement-boundaries
- Claims: selector-no-width-rule, representation-decision-factors
- Caveats: The focused study reused validation and failed its gate; it did not justify a universal width threshold.

### Truth digests, alternating schedules, clustering, and intervals (`exact-comparison-protocol`)

- Track / tier / priority: Measurement, evidence, and corrections / deep_dive / P1
- Central question: What can make a precise timing number wrong even when the timer itself is accurate?
- Viewer outcome: Each protocol guard earns one part of the claim and no more.
- Prerequisites: b2b4-corrected, read-a-ratio
- Claims: exactness-gates, ratio-label-rule, b2b4-v3-kernel
- Caveats: The retained interval models formula clustering within the declared run; it does not model every machine or future workload.

### Why one blended fastest-method chart is dishonest (`no-fastest-chart`)

- Track / tier / priority: Measurement, evidence, and corrections / visual_short / P1
- Central question: What had to be hidden to make one method look fastest everywhere?
- Viewer outcome: The honest answer is conditional because the actual tasks are different.
- Prerequisites: scope-boundaries, b2b4-corrected, epfl-parity
- Claims: no-universal-winner, ratio-label-rule, cm-output-contract-boundary
- Caveats: Current CM evidence deliberately contains a kernel advantage, a parity workload, and a slower wrapper.

### How an audit changed the headline (`correction-story`)

- Track / tier / priority: Measurement, evidence, and corrections / core_explainer / P0
- Central question: Did the audit erase the old work, or did it change what the work was allowed to claim?
- Viewer outcome: A good audit changes the claim without pretending the history never happened.
- Prerequisites: exact-comparison-protocol, no-fastest-chart
- Claims: b2b4-v3-kernel, epfl-parity, public-wrapper-slower, no-universal-winner, exactness-gates
- Caveats: The current conclusion is not one replacement ratio: EPFL, B2/B4 kernel, and the wrapper remain separate results.

### CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions (`toolbox-map`)

- Track / tier / priority: Toolbox and applications / deep_dive / P1
- Central question: Which tool is best—the one that returns every output, one witness, a canonical graph, or a smaller expression?
- Viewer outcome: Tools become comparable only after they are asked to do the same job.
- Prerequisites: what-cm-does-not-claim, cse-vs-cse-flat, packed-words-selection
- Claims: toolbox-output-contracts, cm-output-contract-boundary, no-universal-winner
- Caveats: This map explains interfaces and retained evidence; it is not a full tutorial or universal benchmark for every tool.

### Configuration and feature-model workloads (`configuration-models`)

- Track / tier / priority: Toolbox and applications / deep_dive / P1
- Central question: What changes when the rule set is almost the same tomorrow but not byte-for-byte identical?
- Viewer outcome: Configuration performance lives in the sequence of related questions, not one isolated formula.
- Prerequisites: toolbox-map, cm-ir-persistence
- Claims: configuration-revision-workload, cm-ir-persistence-contract, representation-decision-factors
- Caveats: The retained studies are bounded revision and task cases; they do not establish universal CM dominance for configuration systems.

### Circuit workloads: structure, truth, and exact controls (`circuits`)

- Track / tier / priority: Toolbox and applications / core_explainer / P1
- Central question: When a circuit has thousands of gates, what exact function is one output cone asking us to compute?
- Viewer outcome: Measure the function of the cone you actually selected, not the size of the circuit around it.
- Prerequisites: toolbox-map, live-support-ambient, cse-vs-cse-flat
- Claims: circuit-cone-support, epfl-parity, epfl-mechanism, exactness-gates
- Caveats: The accepted parity result belongs to selected EPFL AND/INV cones, not to all circuits or all tasks.

### Policy and rule systems with related revisions (`policy-rule-systems`)

- Track / tier / priority: Toolbox and applications / core_explainer / P1
- Central question: If two policy versions share most of their rules, how much work can be reused safely?
- Viewer outcome: Safe rule reuse is an end-to-end identity and cost problem.
- Prerequisites: toolbox-map, cm-ir-persistence, measurement-boundaries
- Claims: policy-rule-revision-workload, crse-d2-d7-evolution, crse-d-mixed
- Caveats: More exact rewrites or fewer operations do not guarantee a faster overhead-inclusive policy task.

### Which representation should I try? (`representation-decision`)

- Track / tier / priority: Toolbox and applications / core_explainer / P1
- Central question: What should you ask before choosing CM, CSE-flat, packed evaluation, BDD, or SAT?
- Viewer outcome: The right representation is conditional on the task you actually need to complete.
- Prerequisites: configuration-models, circuits, policy-rule-systems, no-fastest-chart
- Claims: representation-decision-factors, dense-vs-ir-distinct, selector-no-width-rule, no-universal-winner
- Caveats: The decision flow narrows eligible approaches; it does not replace measurement on a new workload.

### What the CRSE research program asks (`recognition-question`)

- Track / tier / priority: CRSE recognition research / core_explainer / P1
- Central question: Can a learned system suggest useful Boolean structure without becoming the authority on correctness?
- Viewer outcome: CRSE studies when guidance helps while exact computation remains the safety authority.
- Prerequisites: conceptual-vs-measured, cm-ir-nodes-sharing, exact-comparison-protocol
- Claims: crse-experimental, crse-initial-learning-slice, crse-current-program-map, conceptual-label-rule
- Caveats: CRSE is a project label in the authoritative sources; no production model or invented acronym expansion is allowed.

### C2 variable-size decomposition: exact control, learned failure (`recognition-c2`)

- Track / tier / priority: CRSE recognition research / core_explainer / P1
- Central question: What if the exact detector works perfectly but the learned detector fails on a larger size?
- Viewer outcome: Exact recognition advanced; learned transfer did not.
- Prerequisites: recognition-question
- Claims: crse-c2-negative, crse-experimental
- Caveats: The exact detector's success does not rescue the failed learned size-transfer criterion.

### C3-C5 natural cuts: improvements without held-out promotion (`recognition-c3-c5`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: Can better natural data and a better readout turn local improvement into a reliable held-out cut?
- Viewer outcome: The learned path improved, but the exact control remained the accepted path.
- Prerequisites: recognition-c2
- Claims: crse-c3-c5-negative, crse-experimental
- Caveats: Improvement on confirmatory circuits did not satisfy the required held-out promotion or cost criteria.

### C6-C8 exact source ANF: packed cores and transfer (`recognition-c6`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: What can advance when a deterministic exact core improves but one frozen gate still misses?
- Viewer outcome: Exact transfer was stronger than any universal backend ranking.
- Prerequisites: recognition-c3-c5, packed-words-selection
- Claims: crse-c6-advance, crse-c7-c8-transfer, packed-truth-vector-contract
- Caveats: Exact identity transferred; the fastest set, packed, or bitset representation did not become universal.

### C9-C11 exact routing: static trees, guarded restart, and one-pass conversion (`recognition-c9-c11`)

- Track / tier / priority: CRSE recognition research / core_explainer / P1
- Central question: Can an exact router solve a catastrophic tail and still be the wrong default?
- Viewer outcome: C9-C11 explain why C12 needed a robust guarded policy rather than a more confident universal router.
- Prerequisites: recognition-c6
- Claims: crse-c9-c11-negative, crse-current-program-map
- Caveats: All three preserved exact outputs; none beat the best fixed arm on every retained split, so tail protection and median profitability remain separate.

### C12-C16 exact dispatch, tail guards, and GF(2) artifacts (`recognition-c12-c16`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: Can one exact system protect catastrophic tails without slowing every sparse case?
- Viewer outcome: The later C milestones advance a cross-machine exact guarded portfolio, not one universal engine.
- Prerequisites: recognition-c9-c11
- Claims: crse-c12-c16-exact, crse-current-program-map
- Caveats: C16 passed the corrected Linux second-machine gate, but one tiny local case regressed and a fresh non-XOR-heavy family remains untested.

### C17-C20 exact policies: dispatch, transfer, fitting, and compilation (`recognition-c17-c20`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: How can the same exact policy look strong in aggregate and still fail the rule needed for safe deployment?
- Viewer outcome: C17-C20 turn a promising exact arm into a better-understood policy boundary, not a promoted universal dispatcher.
- Prerequisites: recognition-c12-c16, measurement-boundaries
- Claims: crse-c17-c20-exact-policy, crse-current-program-map
- Caveats: C19 supplies fresh source-cluster confirmation on one machine, while C20 is a retrospective same-machine replay, so neither licenses a universal production rule.

### C21-C22 task-matched GF(2): seven methods and a frozen source-packed portfolio (`recognition-c21-c22`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: What changes when seven methods must return the best exact artifact instead of any reconstructible factor?
- Viewer outcome: C21-C22 justify a guarded source-packed candidate for fresh testing, not a learned router or deployed default.
- Prerequisites: recognition-c17-c20, exact-comparison-protocol, instruction-operations-memory
- Claims: crse-c21-c22-task-matched, crse-experimental
- Caveats: C21 is retrospective one-machine evidence, and C22 is implementation readiness without fresh timing, so the narrow source-packed lead is not a production claim.

### C23 fresh Yosys transfer: exact confirmation without routing headroom (`recognition-c23`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: Does a fresh source family turn the narrow C21 winner into a deployable routing rule?
- Viewer outcome: C23 strengthens the fixed exact portfolio evidence while making another learned router less compelling, not more.
- Prerequisites: recognition-c21-c22, exact-comparison-protocol, measurement-boundaries
- Claims: crse-c23-fresh-yosys-transfer, crse-experimental
- Caveats: The fixed paths transfer, but the best two are separated by only 0.62%, the oracle offers only 4.7% pre-router headroom, and compiled execution still regresses on individual cases.

### Milestones D-D7: task routing, proved rules, caching, and normalization (`recognition-d-tasks`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: What happens when exact routing and rewriting are judged by the complete task rather than their inner kernel?
- Viewer outcome: The system became more exact and accountable faster than it became profitable.
- Prerequisites: recognition-question, measurement-boundaries, cm-ir-persistence
- Claims: crse-d-mixed, crse-d2-d7-evolution, policy-rule-revision-workload
- Caveats: Exactness and engineering completion do not guarantee overhead-inclusive profitability.

### D8 Linux confirmation: exact but unprofitable (`recognition-d8`)

- Track / tier / priority: CRSE recognition research / visual_short / P0
- Central question: Can an experiment reproduce perfectly and still fail its reason for deployment?
- Viewer outcome: D8 is an exact engineering success and a profitability failure at the same time.
- Prerequisites: recognition-d-tasks
- Claims: crse-d8-negative
- Caveats: Exact transfer passed, but profitability did not; the negative result is the final promotion authority.

### D9 abstention policy: safe, charged, not promoted (`recognition-d9`)

- Track / tier / priority: CRSE recognition research / core_explainer / P1
- Central question: If a policy avoids every bad rewrite, has it succeeded?
- Viewer outcome: A safe no-op is not free, and its cost belongs in the deployment decision.
- Prerequisites: recognition-d8
- Claims: crse-d9-not-promoted, crse-experimental
- Caveats: D9 selected the faster fixed arm correctly but remained slower after advice overhead, so no policy was promoted.

### D10 indexed rule execution: richer exact rules, negative whole-path economics (`recognition-d10`)

- Track / tier / priority: CRSE recognition research / core_explainer / P1
- Central question: Can a much better-engineered exact rule system still lose to doing nothing?
- Viewer outcome: D10 advanced the exact engine while retaining no rewrite as the economic control.
- Prerequisites: recognition-d9
- Claims: crse-d10-negative, policy-rule-revision-workload
- Caveats: More rule families and safer execution did not satisfy the retained whole-path profitability criterion.

### E1-E2 exact BDD and SAT guidance: task-aware advice with fallback (`recognition-e1-e2`)

- Track / tier / priority: CRSE recognition research / deep_dive / P1
- Central question: Should one advisor choose the same BDD order and SAT lifecycle for every question about a Boolean function?
- Viewer outcome: Task-aware advice is useful only while exact construction, checking, and fallback stay in charge.
- Prerequisites: recognition-question, toolbox-map, measurement-boundaries
- Claims: crse-e1-e2-guidance, toolbox-output-contracts, crse-experimental
- Caveats: The retained learned advice did not establish a general timing win, and solver/BDD results answer different output contracts.

### How a video is bound to source hashes (`source-hash-reproduction`)

- Track / tier / priority: Provenance and reproducibility / core_explainer / P0
- Central question: If one evidence file changes, how do we know which sentence, scene, and rendered chapter are stale?
- Viewer outcome: Reproducibility is a connected chain of identities, evidence, and approvals.
- Prerequisites: conceptual-vs-measured, exact-comparison-protocol
- Claims: source-provenance-contract, conceptual-label-rule
- Caveats: Hash identity supports reproducibility and invalidation, but it does not establish scientific truth or authorize cloud spending.

### Correspondence Matrices: From Representation to Honest Evidence (`cm-flagship-representation-to-evidence-v1`)

- Track / tier / priority: Rendered pilot / deep_dive / P0
- Central question: How do representation, transformation, and measurement boundaries change what CM evidence is allowed to claim?
- Viewer outcome: Follow the seven-chapter pilot from truth layout to scoped corrected evidence.
- Prerequisites: conceptual-vs-measured, what-is-explicit-cm, explicit-cm-vs-cm-ir, measurement-boundaries
- Claims: cm-explicit-definition, cm-ir-definition, cse-flat-definition, b2b4-v3-kernel, epfl-parity, no-universal-winner
- Caveats: The pilot remains a rendered historical baseline; v2 does not mutate its locked release identity.
