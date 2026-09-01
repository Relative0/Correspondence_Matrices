# Live support versus ambient variables

Video ID: `live-support-ambient`  
Episode content identity: `90d1d7d94d278292221be9e2041c0728ac3c5c1e87c09ac14c48ef3b7944e9e1`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: live support

Why can a six-variable table contain a function that really depends on only three variables? This episode has one job: The surrounding assignment universe may name more variables than the function can actually depend on after simplification or fixed bindings. We build on Expression, truth table, and Boolean function; their definitions stay fixed while this lesson adds a new layer. Live support contains variables that can change the output; ambient variables merely belong to the surrounding layout.

Watch for the label live support; it stays attached to the artifact this episode means. When we say ambient variable, the highlight identifies its layer before we interpret it. The term fixed binding receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Hold one input fixed and test which remaining variables can still change the output. Collapse duplicate ambient rows into the smaller semantic-support view without claiming an automatic timing gain. Now isolate live support inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for live support changes. That matched before-and-after view assigns the visible consequence to live support, not to a substituted workload. Nominal width and live support settle as two separate labeled counters. Now isolate ambient universe inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for ambient universe changes. That matched before-and-after view assigns the visible consequence to ambient universe, not to a substituted workload. Ambient variables form an outer ring; only output-changing wires remain bright. Now isolate fixed-variable reduction inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for fixed-variable reduction changes. That matched before-and-after view assigns the visible consequence to fixed-variable reduction, not to a substituted workload. A fixed binding removes one axis while paired rows collapse onto identical outputs. Live support and ambient variables are distinct: live variables affect the function, while ambient variables may still define the displayed assignment universe.

Read that statement only within this scope: CM IR materialization semantics. Its declared measurement boundary is representation. The uncertainty field says none. The nearest confusing lesson is What a correspondence matrix is; it owns row/column variable partition, while this episode owns live support.

The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D. Holding that element fixed lets this episode isolate live support. A and B select the row, C and D select the column, and MSB-first order fixes both index conventions. Holding that element fixed lets this episode isolate ambient universe.

Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit. Holding that element fixed lets this episode isolate fixed-variable reduction. Folding the truth-table output column into a four-by-four grid changes the layout, not the function. Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it.

Live support can remove an input from active computation even when the ambient layout still reserves its axis. A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix. The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone.

## c03 — Boundary, retrieval, and transfer

Smaller live support changes the active problem description, but it does not by itself select the fastest engine. Identify which variable is ambient after two assignments produce the same output under both of its values. Nominal width and semantic support answer different questions. A common mistake is this: Every named variable necessarily doubles the function's active computational support.

Repair it by returning to the owned distinction: live support.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Nominal width and semantic support answer different questions. Count the variables that matter to this function, not only the variables named around it.
