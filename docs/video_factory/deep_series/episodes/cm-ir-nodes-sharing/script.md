# CM-IR nodes, sharing, and roots

Video ID: `cm-ir-nodes-sharing`  
Episode content identity: `b82dd6e6ddae0b9cc930d8168794e097f8858886d9dfa820a7a0ab95bd825787`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: CMNode structure

If the same Boolean subproblem appears twice, why store and compute it twice? This episode has one job: CM-IR stores unique computation nodes in a DAG so repeated structure and multiple roots can reuse the same descendants. We build on Explicit dense CM versus CM-IR; their definitions stay fixed while this lesson adds a new layer. A CM-IR DAG stores unique nodes and lets several parents or roots point to the same descendant.

Watch for the label node; it stays attached to the artifact this episode means. When we say directed acyclic graph, the highlight identifies its layer before we interpret it. The term shared descendant receives its own visual state so it cannot drift into a neighboring concept. We will keep root visible whenever its definition controls the inference.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. Now isolate CMNode structure inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for CMNode structure changes. That matched before-and-after view assigns the visible consequence to CMNode structure, not to a substituted workload.

Two duplicate syntax branches bend toward one interned CMNode. Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use. Holding that element fixed lets this episode isolate CMNode structure. A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges.

Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F. The output check closes both paths against the same exact truth behavior before performance is interpreted. The starting state preserves the stable definition: S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. After the change, the composition makes CMNode structure inspectable: Two duplicate syntax branches bend toward one interned CMNode.

The invariant is the example's meaning; the variable is CMNode structure. If the same output is reached through a different path, the diagram must still identify whether CMNode structure changed. The accompanying view makes this step concrete: Two duplicate syntax branches bend toward one interned CMNode. Read CMNode structure from input to consequence through one matched view: Two duplicate syntax branches bend toward one interned CMNode; every surrounding entity keeps its prior meaning.

The diagram treats CMNode structure as a located state, artifact, or boundary rather than as an unexplained method label.

## c03 — Mechanism: DAG sharing; multiple roots

Watch us build the repeated subtree twice as syntax, assign its structural identity, and intern it once. Attach two roots to shared descendants and trace one evaluation without recomputing the shared node. Now isolate DAG sharing inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for DAG sharing changes.

That matched before-and-after view assigns the visible consequence to DAG sharing, not to a substituted workload. Reference-count and root badges appear while shared edges remain visibly distinct from tree edges. Now isolate multiple roots inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for multiple roots changes.

That matched before-and-after view assigns the visible consequence to multiple roots, not to a substituted workload. An evaluation pulse visits each unique node once and fans the result to both consumers. CM-IR is a canonicalized, interned shared DAG intermediate representation. Read that statement only within this scope: current implementation.

Its declared measurement boundary is representation. The uncertainty field says none. CM-IR interns reusable nodes in a DAG and can retain roots that share descendants. Read that statement only within this scope: current CM-IR implementation.

The nearest confusing lesson is Canonicalization, interning, and normalization; it owns normalization, while this episode owns CMNode structure. The left branch combines S with C and D, while the right branch combines the same S with E. Holding that element fixed lets this episode isolate DAG sharing. Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output.

Holding that element fixed lets this episode isolate multiple roots. Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations. Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers. The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison.

Any claimed reduction must point to the repeated S path or another named transformation actually present here. After the change, the composition makes DAG sharing inspectable: Reference-count and root badges appear while shared edges remain visibly distinct from tree edges. The invariant is the example's meaning; the variable is DAG sharing. If the same output is reached through a different path, the diagram must still identify whether DAG sharing changed.

After the change, the composition makes multiple roots inspectable: An evaluation pulse visits each unique node once and fans the result to both consumers. The invariant is the example's meaning; the variable is multiple roots. If the same output is reached through a different path, the diagram must still identify whether multiple roots changed. The accompanying view makes this step concrete: An evaluation pulse visits each unique node once and fans the result to both consumers.

The accompanying view makes this step concrete: Reference-count and root badges appear while shared edges remain visibly distinct from tree edges.

## c04 — Boundary, retrieval, and transfer

Sharing reduces repeated structure, but the amount of reduction depends on the expression and canonicalization rules. Point to the node that would be duplicated in a tree but shared in the DAG. One node can serve several consumers without changing the function. A common mistake is this: A CM-IR DAG must contain one independent copy of every syntactic subtree.

Repair it by returning to the owned distinction: CMNode structure.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: One node can serve several consumers without changing the function. Read CM-IR as a graph of reusable computations, not as a filled truth matrix.
