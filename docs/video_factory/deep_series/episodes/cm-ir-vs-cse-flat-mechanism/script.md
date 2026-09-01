# CM-IR versus CSE-flat: shared mechanisms and extra transformations

Video ID: `cm-ir-vs-cse-flat-mechanism`  
Episode content identity: `f1a6a53d9e1993b3b4b3ebc52307cbc0fc30eeff1fb9a70b1fe800a0bc4e8fb1`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: mechanism overlap

After CSE-flat already shares and flattens, what work is actually left for CM-IR to remove? This episode has one job: CM-IR and CSE-flat overlap in sharing and flattening; any remaining difference must be attributed to actual normalization, merging, or lowered-program changes on the scoped workload. We build on Plain CSE versus sharing-aware CSE-flat, Canonicalization, interning, and normalization; their definitions stay fixed while this lesson adds a new layer. The two compilers share mechanisms; only the remaining observed transformations can explain a scoped difference.

Watch for the label shared transformation; it stays attached to the artifact this episode means. When we say additional normalization, the highlight identifies its layer before we interpret it. The term mechanism attribution receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. The accompanying view makes this step concrete: A common transformation stack feeds both arms before they diverge.

## c03 — Mechanism: transformation attribution; CM-label overclaim prevention

Apply sharing and safe flattening to both arms, then remove those common steps from the comparison ledger. Add only observed CM-IR normalization or merging deltas and trace them into the lowered instruction structure. Now isolate mechanism overlap inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for mechanism overlap changes.

That matched before-and-after view assigns the visible consequence to mechanism overlap, not to a substituted workload. A common transformation stack feeds both arms before they diverge. Now isolate transformation attribution inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for transformation attribution changes.

That matched before-and-after view assigns the visible consequence to transformation attribution, not to a substituted workload. Now isolate CM-label overclaim prevention inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for CM-label overclaim prevention changes. That matched before-and-after view assigns the visible consequence to CM-label overclaim prevention, not to a substituted workload.

A delta ledger labels each changed node as sharing, flattening, normalization, or merging. Sharing-aware CSE-flat additionally flattens eligible associative chains while preserving shared nodes. Read that statement only within this scope: corrected comparator contract. Its declared measurement boundary is mechanism.

The uncertainty field says none. CM-IR can add canonical normalization and merging beyond the transformations shared with CSE-flat. Read that statement only within this scope: corrected mechanism interpretation. The uncertainty field says workload dependent.

Normalization, canonical structural keys, and interning are distinct stages: rewrites choose a canonical form, keys identify it, and interning reuses an existing node. Read that statement only within this scope: current CM-IR compiler. Its declared measurement boundary is representation construction. The uncertainty field says implementation-defined.

The nearest confusing lesson is From DAGs to flat instructions: operations, storage, and execution; it owns DAG-to-FlatProgram lowering, while this episode owns mechanism overlap. Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use. Holding that element fixed lets this episode isolate mechanism overlap. The left branch combines S with C and D, while the right branch combines the same S with E.

Holding that element fixed lets this episode isolate transformation attribution. Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output. Holding that element fixed lets this episode isolate CM-label overclaim prevention. A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges.

Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations. Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers. Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F. The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison.

Any claimed reduction must point to the repeated S path or another named transformation actually present here. The output check closes both paths against the same exact truth behavior before performance is interpreted. The starting state preserves the stable definition: S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. After the change, the composition makes mechanism overlap inspectable: A common transformation stack feeds both arms before they diverge.

The invariant is the example's meaning; the variable is mechanism overlap. If the same output is reached through a different path, the diagram must still identify whether mechanism overlap changed. After the change, the composition makes transformation attribution inspectable: A common transformation stack feeds both arms before they diverge. The invariant is the example's meaning; the variable is transformation attribution.

If the same output is reached through a different path, the diagram must still identify whether transformation attribution changed. After the change, the composition makes CM-label overclaim prevention inspectable: A delta ledger labels each changed node as sharing, flattening, normalization, or merging. The invariant is the example's meaning; the variable is CM-label overclaim prevention. If the same output is reached through a different path, the diagram must still identify whether CM-label overclaim prevention changed.

The accompanying view makes this step concrete: The final graphs align by semantic node and lowered instruction rather than by method logo. The accompanying view makes this step concrete: A delta ledger labels each changed node as sharing, flattening, normalization, or merging.

## c04 — Boundary, retrieval, and transfer

A method label is not a mechanism, and one workload's residual reduction is not universal. Classify four graph changes as shared CSE-flat work or an additional CM-IR transformation. Common mechanisms belong to both arms; only measured deltas belong to the comparison. A common mistake is this: Every difference between CM-IR and raw AST is an advantage unique to CM-IR over CSE-flat.

Repair it by returning to the owned distinction: mechanism overlap.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Common mechanisms belong to both arms; only measured deltas belong to the comparison. Attribute every reduction to a visible transformation, not to the letters CM.
