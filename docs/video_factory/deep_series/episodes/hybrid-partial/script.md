# Hybrid versus partial-hybrid materialization

Video ID: `hybrid-partial`  
Episode content identity: `6adb16867512ed450c0e4c04c2033271a59aebb52bf0fda47f7e918b065da4e6`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: whole-subtree hybrid collapse

Does hybrid execution collapse the whole graph, or can it preserve structure and choose child by child? This episode has one job: Hybrid and partial-hybrid modes differ in whether they collapse a whole subtree or preserve upper structure while dispatching selected children to packed or dense materialization. We build on CM-IR nodes, sharing, and roots, Packed truth vectors: big integers, machine words, and masks; their definitions stay fixed while this lesson adds a new layer. Hybrid can collapse an eligible region; partial-hybrid preserves more graph structure and dispatches selected children.

Watch for the label hybrid materialization; it stays attached to the artifact this episode means. When we say partial-hybrid materialization, the highlight identifies its layer before we interpret it. The term full collapse receives its own visual state so it cannot drift into a neighboring concept. We will keep no reinflation visible whenever its definition controls the inference.

## c02 — Worked example: Shared Boolean expression

The next sequence uses Shared Boolean expression as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Shared Boolean expression. S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E. Carry AST, CSE, CSE-flat, CM-IR, lowering, and operation accounting across episodes.

We now construct the Shared Boolean expression and name every part before interpreting it. The accompanying view makes this step concrete: A shared DAG carries a live-support heat map and explicit dispatch decisions.

## c03 — Mechanism: child-level partial-hybrid dispatch; no-reinflation output

Color nodes by live support and show whole-subtree hybrid collapse under one declared mode. Restore the DAG, dispatch only eligible children in partial-hybrid mode, and preserve the parent structure through output. Now isolate whole-subtree hybrid collapse inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for whole-subtree hybrid collapse changes.

That matched before-and-after view assigns the visible consequence to whole-subtree hybrid collapse, not to a substituted workload. Hybrid view collapses the selected whole region into one packed block. Now isolate child-level partial-hybrid dispatch inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for child-level partial-hybrid dispatch changes.

That matched before-and-after view assigns the visible consequence to child-level partial-hybrid dispatch, not to a substituted workload. Partial-hybrid view collapses children while the upper graph remains and feeds a no-reinflation output. Now isolate no-reinflation output inside Shared Boolean expression. The example definition and output meaning stay fixed while only the state for no-reinflation output changes.

That matched before-and-after view assigns the visible consequence to no-reinflation output, not to a substituted workload. Hybrid and partial-hybrid materialization are distinct dispatch modes: whole-subtree collapse and child-level structure-preserving dispatch must not be conflated. Read that statement only within this scope: current CM-IR materialization modes. Its declared measurement boundary is materialization strategy.

The uncertainty field says workload dependent. Packed bigint and machine-word evaluators store the same ordered truth vector in different exact execution layouts with explicit masks and tail handling. Read that statement only within this scope: current packed evaluator implementations. Its declared measurement boundary is execution representation.

The uncertainty field says backend choice remains workload dependent. The nearest confusing lesson is Pair-aware CM collapse; it owns pair eligibility, while this episode owns whole-subtree hybrid collapse. Begin with A and B, compute the shared subexpression S once, and keep that identity color on every outgoing use. Holding that element fixed lets this episode isolate whole-subtree hybrid collapse.

The left branch combines S with C and D, while the right branch combines the same S with E. Holding that element fixed lets this episode isolate child-level partial-hybrid dispatch. Both branches meet at the final OR, so the shared node changes program structure without changing the Boolean output. Holding that element fixed lets this episode isolate no-reinflation output.

A raw syntax view may draw S twice; a shared graph draws one node with two outgoing edges. Lowering the graph assigns dependency-ordered slots, but slot numbers are not new Boolean operations. Instruction count, primitive execution count, live buffers, and packed storage therefore remain separate ledgers. Changing from bigint bits to word lanes changes storage and execution layout, not the meaning of S or F.

The stable variable order A through E prevents a convenient reordering from hiding inside a method comparison. Any claimed reduction must point to the repeated S path or another named transformation actually present here. The output check closes both paths against the same exact truth behavior before performance is interpreted. The starting state preserves the stable definition: S=A AND B; F=(S AND C AND D) OR (S AND E), with binary source syntax and stable variable order A,B,C,D,E.

After the change, the composition makes whole-subtree hybrid collapse inspectable: Hybrid view collapses the selected whole region into one packed block. The invariant is the example's meaning; the variable is whole-subtree hybrid collapse. If the same output is reached through a different path, the diagram must still identify whether whole-subtree hybrid collapse changed. After the change, the composition makes child-level partial-hybrid dispatch inspectable: Partial-hybrid view collapses children while the upper graph remains and feeds a no-reinflation output.

The invariant is the example's meaning; the variable is child-level partial-hybrid dispatch. If the same output is reached through a different path, the diagram must still identify whether child-level partial-hybrid dispatch changed. After the change, the composition makes no-reinflation output inspectable: Partial-hybrid view collapses children while the upper graph remains and feeds a no-reinflation output. The invariant is the example's meaning; the variable is no-reinflation output.

If the same output is reached through a different path, the diagram must still identify whether no-reinflation output changed. The accompanying view makes this step concrete: Partial-hybrid view collapses children while the upper graph remains and feeds a no-reinflation output. The accompanying view makes this step concrete: Hybrid view collapses the selected whole region into one packed block.

## c04 — Boundary, retrieval, and transfer

These are implemented strategies, not guarantees that one wins every support size or workload. Identify which of two resulting artifacts came from whole collapse and which from child-level dispatch. Hybrid changes the materialization boundary; partial-hybrid changes it selectively. A common mistake is this: Hybrid and partial-hybrid are two labels for the same full-collapse behavior.

Repair it by returning to the owned distinction: whole-subtree hybrid collapse.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Hybrid changes the materialization boundary; partial-hybrid changes it selectively. Watch which structure survives the dispatch decision.
