# What a correspondence matrix is

Video ID: `what-is-explicit-cm`  
Episode content identity: `d69af680b3e9f9c966954e7a5be608053a1751850b69384d6bd258ca663fccca`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: row/column variable partition

How can one truth table become a two-dimensional object without changing a single output? This episode has one job: An explicit correspondence matrix is a dense truth-layout obtained by partitioning variables into row and column axes and placing one exact output in each assignment cell. We build on Expression, truth table, and Boolean function; their definitions stay fixed while this lesson adds a new layer. An explicit CM lays the truth values out over a declared split between row and column variables.

Watch for the label correspondence matrix; it stays attached to the artifact this episode means. When we say row variables, the highlight identifies its layer before we interpret it. The term column variables receives its own visual state so it cannot drift into a neighboring concept. We will keep cell assignment visible whenever its definition controls the inference.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Now isolate row/column variable partition inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for row/column variable partition changes. That matched before-and-after view assigns the visible consequence to row/column variable partition, not to a substituted workload.

One assignment splits into row bits and column bits; two index cursors meet at its cell. The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D. Holding that element fixed lets this episode isolate row/column variable partition. Folding the truth-table output column into a four-by-four grid changes the layout, not the function.

A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix. An exact equality check across the views is the gate before any timing ratio is allowed to matter. The starting state preserves the stable definition: F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. After the change, the composition makes row/column variable partition inspectable: One assignment splits into row bits and column bits; two index cursors meet at its cell.

The invariant is the example's meaning; the variable is row/column variable partition. If the same output is reached through a different path, the diagram must still identify whether row/column variable partition changed. The accompanying view makes this step concrete: A sixteen-row truth table folds physically into a four-by-four matrix.

## c03 — Mechanism: assignment-to-cell indexing; dense CM output layout

Partition A,B onto rows and C,D onto columns, then derive binary indices from one assignment. Fold the truth-table output column into the 4-by-4 grid and query several cells in both directions. Now isolate assignment-to-cell indexing inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for assignment-to-cell indexing changes.

That matched before-and-after view assigns the visible consequence to assignment-to-cell indexing, not to a substituted workload. Now isolate dense CM output layout inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for dense CM output layout changes. That matched before-and-after view assigns the visible consequence to dense CM output layout, not to a substituted workload.

Live-support highlighting removes an inert axis while the declared ambient layout remains outlined. An explicit CM is a dense truth-layout representation over a declared row/column variable split. Read that statement only within this scope: implemented dense output contract. Its declared measurement boundary is representation.

The uncertainty field says none. Live support and ambient variables are distinct: live variables affect the function, while ambient variables may still define the displayed assignment universe. Read that statement only within this scope: CM IR materialization semantics. The nearest confusing lesson is Live support versus ambient variables; it owns live support, while this episode owns row/column variable partition.

A and B select the row, C and D select the column, and MSB-first order fixes both index conventions. Holding that element fixed lets this episode isolate assignment-to-cell indexing. Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit. Holding that element fixed lets this episode isolate dense CM output layout.

Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it. Live support can remove an input from active computation even when the ambient layout still reserves its axis. The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone. Holding variable order fixed makes matrix, packed-vector, and program views comparable without an indexing ambiguity.

After the change, the composition makes assignment-to-cell indexing inspectable: One assignment splits into row bits and column bits; two index cursors meet at its cell. The invariant is the example's meaning; the variable is assignment-to-cell indexing. If the same output is reached through a different path, the diagram must still identify whether assignment-to-cell indexing changed. After the change, the composition makes dense CM output layout inspectable: Live-support highlighting removes an inert axis while the declared ambient layout remains outlined.

The invariant is the example's meaning; the variable is dense CM output layout. If the same output is reached through a different path, the diagram must still identify whether dense CM output layout changed. The accompanying view makes this step concrete: Live-support highlighting removes an inert axis while the declared ambient layout remains outlined. The accompanying view makes this step concrete: One assignment splits into row bits and column bits; two index cursors meet at its cell.

## c04 — Boundary, retrieval, and transfer

The matrix is a dense output layout; this definition does not make it compact, a solver, or universally fast. Given one four-bit assignment, choose its row and column cell before the cursors move. The matrix changes the layout, not the underlying Boolean function. A common mistake is this: A correspondence matrix is an unrelated numerical approximation rather than an exact truth layout.

Repair it by returning to the owned distinction: row/column variable partition.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: The matrix changes the layout, not the underlying Boolean function. A CM cell is simply one exact assignment viewed through two coordinated indices.
