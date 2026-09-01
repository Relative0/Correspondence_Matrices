# Why a raw expression tree repeats work

Video ID: `raw-ast`  
Episode content identity: `00399cd40a52a1121a264e04f5dec6e34f6bcc1bd2d5d74f69d619abed014212`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: raw AST evaluation

Why does the evaluator compute A AND B twice when both copies mean the same thing? This episode has one job: Raw AST evaluation follows every syntactic occurrence, making repeated work visible as an ablation but not providing the strongest generic comparator. We build on Expression, truth table, and Boolean function; their definitions stay fixed while this lesson adds a new layer. A raw AST follows the written tree and performs work at each syntactic occurrence.

Watch for the label abstract syntax tree; it stays attached to the artifact this episode means. When we say raw evaluation, the highlight identifies its layer before we interpret it. The term ablation receives its own visual state so it cannot drift into a neighboring concept.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. Evaluate the repeated S=A AND B branch once in each syntactic location and increment the counter twice. Freeze the repeated result and preview the sharing question without yet implementing CSE. Now isolate raw AST evaluation inside Shared Boolean expression.

The example definition and output meaning stay fixed while only the state for raw AST evaluation changes. That matched before-and-after view assigns the visible consequence to raw AST evaluation, not to a substituted workload. An evaluation pulse visits both copies and an operation counter advances twice. Now isolate repeated syntactic work inside Shared Boolean expression.

The example definition and output meaning stay fixed while only the state for repeated syntactic work changes. That matched before-and-after view assigns the visible consequence to repeated syntactic work, not to a substituted workload. The repeated subtree is outlined in two positions of the syntax tree. Now isolate ablation role inside Shared Boolean expression.

The example definition and output meaning stay fixed while only the state for ablation role changes. That matched before-and-after view assigns the visible consequence to ablation role, not to a substituted workload. The two identical result tokens hover near each other, setting up the next episode's merge. Raw AST evaluation follows the expression tree without structural sharing or sharing-aware associative flattening, so it is an ablation rather than the strongest generic comparator.

Read that statement only within this scope: corrected comparator ladder. Its declared measurement boundary is mechanism. The uncertainty field says none. The nearest confusing lesson is Common subexpression elimination in plain language; it owns plain structural CSE, while this episode owns raw AST evaluation.

Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use. Holding that element fixed lets this episode isolate raw AST evaluation. The left branch combines S with C and D, while the right branch combines the same S with E. Holding that element fixed lets this episode isolate repeated syntactic work.

Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output. Holding that element fixed lets this episode isolate ablation role. A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges. Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations.

Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers. Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F.

## c03 — Boundary, retrieval, and transfer

Raw AST is an informative ablation, not the strongest comparator for a system that shares structure. Count how many times the repeated subtree is evaluated before the counter reveals the answer. The raw tree shows the duplication that later comparators are designed to remove. A common mistake is this: Raw AST is a fair final baseline for a compiler whose competitors share repeated subexpressions.

Repair it by returning to the owned distinction: raw AST evaluation.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: The raw tree shows the duplication that later comparators are designed to remove. Repeated syntax makes the cost of not sharing visible.
