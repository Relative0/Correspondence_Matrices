# Pair-aware CM collapse

Video ID: `pair-aware`  
Episode content identity: `ea5766e36eb2c7b23155b2a2591abea56266de96d9e9247f574add7c9dd738ef`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: pair eligibility

When can a larger expression safely collapse to one tiny row-column pair? This episode has one job: Pair-aware collapse is an experimental shortcut for the precise boundary of one live row variable and one live column variable after fixed bindings, with exact fallback otherwise. We build on CM-IR nodes, sharing, and roots, Live support versus ambient variables; their definitions stay fixed while this lesson adds a new layer. The pair-aware shortcut requires exactly one live row variable and one live column variable after fixed inputs are applied.

Watch for the label pair-aware path; it stays attached to the artifact this episode means. When we say one live row variable, the highlight identifies its layer before we interpret it. The term one live column variable receives its own visual state so it cannot drift into a neighboring concept. We will keep fallback visible whenever its definition controls the inference.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Apply fixed bindings until exactly one live variable remains on each axis and construct the eligible two-by-two tile. Add a third live variable, refuse the shortcut, and forward the unchanged problem to the standard path. Pair-aware collapse applies only after fixed assignments leave one live row variable and one live column variable; otherwise it forwards to the standard path.

Read that statement only within this scope: current experimental pair-aware implementation. Its declared measurement boundary is construction eligibility. The uncertainty field says experimental implementation status. The nearest confusing lesson is Eager and lazy CM paths; it owns eager construction timing, while this episode owns pair eligibility.

## c03 — Boundary, retrieval, and transfer

Pair eligibility is experimental and local; ineligible cases must fall back without changing semantics. Decide whether three support/fixed-binding cases are pair-eligible before the fallback arrow appears. One live variable per axis makes the pair path possible; everything else stays on the exact fallback path. Now isolate pair eligibility inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for pair eligibility changes. That matched before-and-after view assigns the visible consequence to pair eligibility, not to a substituted workload. Row and column support counters shrink independently to one and one. Now isolate 2-by-2 token-pair collapse inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for 2-by-2 token-pair collapse changes. That matched before-and-after view assigns the visible consequence to 2-by-2 token-pair collapse, not to a substituted workload. The eligible axes snap into a two-by-two token tile and compute all four cases. Now isolate fallback boundary inside Four-variable truth layout.

The example definition and output meaning stay fixed while only the state for fallback boundary changes. That matched before-and-after view assigns the visible consequence to fallback boundary, not to a substituted workload. An ineligible third variable diverts through a clearly labeled exact fallback arrow. The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D.

Holding that element fixed lets this episode isolate pair eligibility. A and B select the row, C and D select the column, and MSB-first order fixes both index conventions. Holding that element fixed lets this episode isolate 2-by-2 token-pair collapse. Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit.

Holding that element fixed lets this episode isolate fallback boundary. Folding the truth-table output column into a four-by-four grid changes the layout, not the function. Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it. A common mistake is this: Any subexpression with two total variables is automatically pair-eligible regardless of axis placement.

Repair it by returning to the owned distinction: pair eligibility.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: One live variable per axis makes the pair path possible; everything else stays on the exact fallback path. The shortcut is defined by its boundary and fallback, not by its name.
