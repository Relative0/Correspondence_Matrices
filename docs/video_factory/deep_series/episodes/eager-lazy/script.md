# Eager and lazy CM paths

Video ID: `eager-lazy`  
Episode content identity: `0882775f7961b6aaa92df4ea5a7fd8e905a40f3cf887f846b8db7134cc64aca0`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: eager construction timing

If both paths return the same output, what exactly makes one eager and the other lazy? This episode has one job: Eager and lazy paths preserve exact semantics while placing aligned materialization work at different points in the construction timeline. We build on Explicit dense CM versus CM-IR, CM-IR nodes, sharing, and roots; their definitions stay fixed while this lesson adds a new layer. Eager work happens during construction; lazy work is deferred until the requested result must be materialized.

Watch for the label eager materialization; it stays attached to the artifact this episode means. When we say lazy materialization, the highlight identifies its layer before we interpret it. The term deferred work receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Run matched timelines: the eager path constructs aligned arrays during compilation while the lazy path retains deferred structure. Request the final output and show the lazy materialization occurring once before exact outputs meet. Now isolate eager construction timing inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for eager construction timing changes. That matched before-and-after view assigns the visible consequence to eager construction timing, not to a substituted workload. Eager fills aligned regions early; lazy carries outlined placeholders until output demand. Now isolate lazy deferred materialization inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for lazy deferred materialization changes. That matched before-and-after view assigns the visible consequence to lazy deferred materialization, not to a substituted workload. The eager and lazy CM paths differ in when aligned dense work is materialized, not in the Boolean function returned. Read that statement only within this scope: current eager/lazy implementations.

Its declared measurement boundary is construction timing. The uncertainty field says no performance ranking. The nearest confusing lesson is Packed truth vectors: big integers, machine words, and masks; it owns packed truth-vector ordering, while this episode owns eager construction timing. The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D.

Holding that element fixed lets this episode isolate eager construction timing. A and B select the row, C and D select the column, and MSB-first order fixes both index conventions. Holding that element fixed lets this episode isolate lazy deferred materialization. Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit.

Folding the truth-table output column into a four-by-four grid changes the layout, not the function. Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it. Live support can remove an input from active computation even when the ambient layout still reserves its axis. A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix.

The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone. Holding variable order fixed makes matrix, packed-vector, and program views comparable without an indexing ambiguity. An exact equality check across the views is the gate before any timing ratio is allowed to matter. The starting state preserves the stable definition: F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering.

## c03 — Boundary, retrieval, and transfer

The implementation distinction does not establish a universal performance ranking. Place three construction and materialization steps on the eager or lazy timeline. Eager and lazy change scheduling, not semantics. A common mistake is this: Lazy means no materialization work is ever performed.

Repair it by returning to the owned distinction: eager construction timing.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Eager and lazy change scheduling, not semantics. Ask when the work occurs before asking how long the whole task takes.
