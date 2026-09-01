# Packed truth vectors: big integers, machine words, and masks

Video ID: `packed-words-selection`  
Episode content identity: `c9ccdfbe9d125d473305ab4bec7f4d1f950348c91af51815c6ddbc8a71f80f4a`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: packed truth-vector ordering

How can one machine operation evaluate many assignments at the same time? This episode has one job: Bigint and word-packed evaluators carry the same ordered truth vector in different exact storage/execution layouts; selector performance belongs to a later episode. We build on Live support versus ambient variables, Explicit dense CM versus CM-IR; their definitions stay fixed while this lesson adds a new layer. Packed evaluation stores many ordered truth values in one integer or several machine words.

Watch for the label packed bitset; it stays attached to the artifact this episode means. When we say machine word, the highlight identifies its layer before we interpret it. The term full mask receives its own visual state so it cannot drift into a neighboring concept. We will keep tail mask visible whenever its definition controls the inference.

## c02 — Worked example: Four-variable truth layout

The next sequence uses Four-variable truth layout as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Four-variable truth layout. F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. Carry assignments, live support, explicit CM, packed truth vectors, and exact output across episodes.

We now construct the Four-variable truth layout and name every part before interpreting it. Now isolate packed truth-vector ordering inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for packed truth-vector ordering changes. That matched before-and-after view assigns the visible consequence to packed truth-vector ordering, not to a substituted workload.

Truth-table outputs slide into bit positions with MSB-first ordering labeled. The example fixes F of A, B, C, and D as A AND B, exclusive-or C OR D. Holding that element fixed lets this episode isolate packed truth-vector ordering. Folding the truth-table output column into a four-by-four grid changes the layout, not the function.

A packed truth vector stores the same exact outputs in a different physical arrangement from the displayed matrix. An exact equality check across the views is the gate before any timing ratio is allowed to matter. The starting state preserves the stable definition: F(A,B,C,D)=(A AND B) XOR (C OR D), row variables A,B, column variables C,D, MSB-first ordering. After the change, the composition makes packed truth-vector ordering inspectable: Truth-table outputs slide into bit positions with MSB-first ordering labeled.

The invariant is the example's meaning; the variable is packed truth-vector ordering. If the same output is reached through a different path, the diagram must still identify whether packed truth-vector ordering changed. The accompanying view makes this step concrete: Truth-table outputs slide into bit positions with MSB-first ordering labeled. Read packed truth-vector ordering from input to consequence through one matched view: Truth-table outputs slide into bit positions with MSB-first ordering labeled; every surrounding entity keeps its prior meaning.

## c03 — Mechanism: bigint versus word arrays; tail masking

Pack sixteen ordered truth bits into an integer, then re-express the same ordering as machine-word lanes. Apply one Boolean operation in parallel and demonstrate why unused tail bits must be masked. Now isolate bigint versus word arrays inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for bigint versus word arrays changes.

That matched before-and-after view assigns the visible consequence to bigint versus word arrays, not to a substituted workload. One long bigint bar splits into fixed-width word lanes without changing bit identities. Now isolate tail masking inside Four-variable truth layout. The example definition and output meaning stay fixed while only the state for tail masking changes.

That matched before-and-after view assigns the visible consequence to tail masking, not to a substituted workload. A gate operates across all bits; a tail mask removes invalid high positions. Packed bigint and machine-word evaluators store the same ordered truth vector in different exact execution layouts with explicit masks and tail handling. Read that statement only within this scope: current packed evaluator implementations.

Its declared measurement boundary is execution representation. The uncertainty field says backend choice remains workload dependent. The nearest confusing lesson is Eager and lazy CM paths; it owns eager construction timing, while this episode owns packed truth-vector ordering. A and B select the row, C and D select the column, and MSB-first order fixes both index conventions.

Holding that element fixed lets this episode isolate bigint versus word arrays. Every four-bit assignment names exactly one of the sixteen cells, and every cell returns one exact output bit. Holding that element fixed lets this episode isolate tail masking. Reading a cell forward evaluates an assignment; reading it backward recovers the row and column bits that selected it.

Live support can remove an input from active computation even when the ambient layout still reserves its axis. The explicit matrix is dense by contract, so compactness and speed require separate evidence rather than definition alone. Holding variable order fixed makes matrix, packed-vector, and program views comparable without an indexing ambiguity. After the change, the composition makes bigint versus word arrays inspectable: One long bigint bar splits into fixed-width word lanes without changing bit identities.

The invariant is the example's meaning; the variable is bigint versus word arrays. If the same output is reached through a different path, the diagram must still identify whether bigint versus word arrays changed. After the change, the composition makes tail masking inspectable: A gate operates across all bits; a tail mask removes invalid high positions. The invariant is the example's meaning; the variable is tail masking.

If the same output is reached through a different path, the diagram must still identify whether tail masking changed. The accompanying view makes this step concrete: A gate operates across all bits; a tail mask removes invalid high positions. The accompanying view makes this step concrete: One long bigint bar splits into fixed-width word lanes without changing bit identities.

## c04 — Boundary, retrieval, and transfer

Packing is an exact execution layout, not a dense CM and not evidence that words are always faster than bigint. Locate the bit representing one assignment and predict the correct tail mask. Packed storage changes how outputs travel through the machine, not what outputs mean. A common mistake is this: Packed words, CSE-flat, and a dense correspondence matrix are interchangeable representations.

Repair it by returning to the owned distinction: packed truth-vector ordering.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Packed storage changes how outputs travel through the machine, not what outputs mean. Keep truth ordering, storage layout, and backend selection as three separate ideas.
