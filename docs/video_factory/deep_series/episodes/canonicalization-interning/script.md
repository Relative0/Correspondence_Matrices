# Canonicalization, interning, and normalization

Video ID: `canonicalization-interning`  
Episode content identity: `3836465af089eda1663baf518ecc61cd0c706ecbbc8ceacb8d02ec4c3df7f3f6`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: normalization

What has to happen before two differently written subexpressions can share one node? This episode has one job: Normalization chooses a stable structure, structural keys identify it, and interning reuses the matching node; these stages cooperate but are not synonyms. We build on CM-IR nodes, sharing, and roots; their definitions stay fixed while this lesson adds a new layer. Normalization makes structure stable, a key identifies that structure, and interning reuses the stored node.

Watch for the label normalization; it stays attached to the artifact this episode means. When we say canonical form, the highlight identifies its layer before we interpret it. The term structural key receives its own visual state so it cannot drift into a neighboring concept. We will keep interning visible whenever its definition controls the inference.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. Now isolate normalization inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for normalization changes. That matched before-and-after view assigns the visible consequence to normalization, not to a substituted workload.

Messy equivalent syntax enters three labeled stations: NORMALIZE, KEY, INTERN. Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use. Holding that element fixed lets this episode isolate normalization. A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges.

Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F. The output check closes both paths against the same exact truth behavior before performance is interpreted. The starting state preserves the stable definition: S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. After the change, the composition makes normalization inspectable: Messy equivalent syntax enters three labeled stations: NORMALIZE, KEY, INTERN.

The invariant is the example's meaning; the variable is normalization. If the same output is reached through a different path, the diagram must still identify whether normalization changed. The accompanying view makes this step concrete: Messy equivalent syntax enters three labeled stations: NORMALIZE, KEY, INTERN. Read normalization from input to consequence through one matched view: Messy equivalent syntax enters three labeled stations: NORMALIZE, KEY, INTERN; every surrounding entity keeps its prior meaning.

The diagram treats normalization as a located state, artifact, or boundary rather than as an unexplained method label.

## c03 — Mechanism: canonical structural identity; interning

Send differently ordered associative/commutative syntax through normalization and display the resulting stable child order. Compute the structural key, query the intern table, and reuse or create the node as separate visible actions. Now isolate canonical structural identity inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for canonical structural identity changes.

That matched before-and-after view assigns the visible consequence to canonical structural identity, not to a substituted workload. A transformation ledger records which stage changed syntax, identity, or storage reuse. Now isolate interning inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for interning changes.

That matched before-and-after view assigns the visible consequence to interning, not to a substituted workload. Normalization, canonical structural keys, and interning are distinct stages: rewrites choose a canonical form, keys identify it, and interning reuses an existing node. Read that statement only within this scope: current CM-IR compiler. Its declared measurement boundary is representation construction.

The uncertainty field says implementation-defined. CM-IR can add canonical normalization and merging beyond the transformations shared with CSE-flat. Read that statement only within this scope: corrected mechanism interpretation. Its declared measurement boundary is mechanism.

The uncertainty field says workload dependent. The nearest confusing lesson is CM-IR persistence and version identity; it owns CM-IR persistent identity, while this episode owns normalization. The left branch combines S with C and D, while the right branch combines the same S with E. Holding that element fixed lets this episode isolate canonical structural identity.

Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output. Holding that element fixed lets this episode isolate interning. Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations. Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers.

The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison. Any claimed reduction must point to the repeated S path or another named transformation actually present here. After the change, the composition makes canonical structural identity inspectable: A transformation ledger records which stage changed syntax, identity, or storage reuse. The invariant is the example's meaning; the variable is canonical structural identity.

If the same output is reached through a different path, the diagram must still identify whether canonical structural identity changed. After the change, the composition makes interning inspectable: A transformation ledger records which stage changed syntax, identity, or storage reuse. The invariant is the example's meaning; the variable is interning. If the same output is reached through a different path, the diagram must still identify whether interning changed.

The accompanying view makes this step concrete: A transformation ledger records which stage changed syntax, identity, or storage reuse. The accompanying view makes this step concrete: Tokens reorder and flatten before a digest appears; only then does the intern table return a node.

## c04 — Boundary, retrieval, and transfer

Canonicalization is implementation scoped; it does not prove a globally minimal representation. Place normalization, key construction, and intern-table lookup in the correct order. Equivalent structure becomes reusable only after its identity is made explicit. A common mistake is this: Canonicalization, hashing, and interning are the same operation.

Repair it by returning to the owned distinction: normalization.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Equivalent structure becomes reusable only after its identity is made explicit. Do not collapse rewriting, identification, and reuse into one magic step.
