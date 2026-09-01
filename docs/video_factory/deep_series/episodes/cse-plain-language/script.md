# Common subexpression elimination in plain language

Video ID: `cse-plain-language`  
Episode content identity: `dc7be815be409b1dda1525b601f68f0e0ed8d31eab9ab6ee0338936d8c8a0077`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: plain structural CSE

What is the simplest way to stop computing the same subtree twice? This episode has one job: Plain structural CSE identifies repeated expression subtrees, computes each once, and reuses the result while preserving exact semantics. We build on Why a raw expression tree repeats work; their definitions stay fixed while this lesson adds a new layer. Common subexpression elimination computes a repeated structural subtree once and reuses its result.

Watch for the label common subexpression; it stays attached to the artifact this episode means. When we say structural identity, the highlight identifies its layer before we interpret it. The term reuse receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. Assign structural keys to both S subtrees and show their equality before any merge occurs. Replace the second computation with a reference to the first result and replay the evaluation counter. Now isolate plain structural CSE inside Shared Boolean expression.

The example definition and output meaning stay fixed while only the state for plain structural CSE changes. That matched before-and-after view assigns the visible consequence to plain structural CSE, not to a substituted workload. Duplicate subtrees receive matching structural-key tags. Now isolate structural key and shared result inside Shared Boolean expression.

The example definition and output meaning stay fixed while only the state for structural key and shared result changes. That matched before-and-after view assigns the visible consequence to structural key and shared result, not to a substituted workload. Common subexpression elimination computes repeated expression subtrees once and reuses them. Read that statement only within this scope: comparator definition used by correction.

Its declared measurement boundary is mechanism. The uncertainty field says none. The nearest confusing lesson is Plain CSE versus sharing-aware CSE-flat; it owns plain CSE versus CSE-flat, while this episode owns plain structural CSE. Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use.

Holding that element fixed lets this episode isolate plain structural CSE. The left branch combines S with C and D, while the right branch combines the same S with E. Holding that element fixed lets this episode isolate structural key and shared result. Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output.

A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges. Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations. Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers. Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F.

The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison. Any claimed reduction must point to the repeated S path or another named transformation actually present here. The output check closes both paths against the same exact truth behavior before performance is interpreted. The starting state preserves the stable definition: S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E.

After the change, the composition makes plain structural CSE inspectable: Duplicate subtrees receive matching structural-key tags.

## c03 — Boundary, retrieval, and transfer

Plain CSE shares repeats; it does not necessarily flatten an associative chain into a wider instruction. Choose which two subtrees have a matching structural key and which merely happen to share one operator. Share identical work first; ask about flattening next. A common mistake is this: CSE automatically performs every normalization or associative flattening available to CM-IR.

Repair it by returning to the owned distinction: plain structural CSE.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Share identical work first; ask about flattening next. CSE removes repeated computation by making structural reuse explicit.
