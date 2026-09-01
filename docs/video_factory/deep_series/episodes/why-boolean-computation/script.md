# Why Boolean computation matters

Video ID: `why-boolean-computation`  
Episode content identity: `5a00c2e9b6f1cdc5f475132fc9aac4606a0b37eafd0bba2a3890740be8af6951`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: decision rule to assignment-to-output mapping

How do we turn a rule that sounds reasonable into something every machine must answer the same way? This episode has one job: Boolean computation turns a decision rule into a precise assignment-to-output mapping that can be represented and evaluated in several different ways. We build on Conceptual animation versus measured result; their definitions stay fixed while this lesson adds a new layer. A Boolean rule maps every complete assignment of its variables to exactly one true-or-false output.

Watch for the label Boolean variable; it stays attached to the artifact this episode means. When we say assignment, the highlight identifies its layer before we interpret it. The term Boolean output receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Watch us toggle one input at a time and trace why the rule's output changes or stays fixed. Keep this separation visible: the rule's meaning from any later choice of matrix, graph, solver, or packed evaluator. Now isolate decision rule to assignment-to-output mapping inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for decision rule to assignment-to-output mapping changes. That matched before-and-after view assigns the visible consequence to decision rule to assignment-to-output mapping, not to a substituted workload. The rule expands into assignment cards that become rows of an output column. Now isolate why repeated exact Boolean evaluation is useful inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for why repeated exact Boolean evaluation is useful changes. That matched before-and-after view assigns the visible consequence to why repeated exact Boolean evaluation is useful, not to a substituted workload. A concrete four-input decision rule lights its inputs and one true/false output. A Boolean expression maps each complete assignment of its variables to one Boolean output.

Read that statement only within this scope: current Boolean expression implementation. Its declared measurement boundary is semantics. The uncertainty field says none. The nearest confusing lesson is Expression, truth table, and Boolean function; it owns syntax-versus-semantics distinction, while this episode owns decision rule to assignment-to-output mapping.

The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D. Holding that element fixed lets this episode isolate decision rule to assignment-to-output mapping. A and B select the row, C and D select the column, and MSB-first order fixes both index conventions. Holding that element fixed lets this episode isolate why repeated exact Boolean evaluation is useful.

Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit. Folding the truth-table output column into a four-by-four grid changes the layout, not the function. Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it. Live support can remove an input from active computation even when the ambient layout still reserves its axis.

A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix. The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone. Holding variable order fixed makes matrix, packed-vector, and program views comparable without an indexing ambiguity.

## c03 — Boundary, retrieval, and transfer

This lesson motivates exact Boolean computation; it does not establish that CM is the best representation for every task. Predict the output after one input changes, then explain which part of the rule caused it. The stable object is the assignment-to-output mapping, not the syntax or storage chosen later. A common mistake is this: Boolean computation is only about one written expression rather than the function over all assignments.

Repair it by returning to the owned distinction: decision rule to assignment-to-output mapping.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: The stable object is the assignment-to-output mapping, not the syntax or storage chosen later. First fix the function; only then choose how to represent or evaluate it.
