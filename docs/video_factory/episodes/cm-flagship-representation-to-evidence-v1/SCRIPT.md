# cm-flagship-representation-to-evidence-v1 — narration script

## 1. One picture, three questions

**ch01-three-questions-01-1**

A correspondence matrix may look like a grid of zeros and ones, but that picture joins several different questions.

**ch01-three-questions-01-2**

We must separate what is represented, how it is computed, and which part a benchmark actually timed.

**ch01-three-questions-02-1**

When those layers are blended, a scoped measurement can quietly become a universal speed claim.

**ch01-three-questions-02-2**

This episode keeps representation, transformation, preparation, evaluation, and wrapper cost visibly separate from beginning to end.

**ch01-three-questions-03-1**

We will build the explicit matrix, compare it with CM-IR and sharing-aware CSE-flat, then read the corrected evidence.

**ch01-three-questions-03-2**

The goal is not to crown a winner; it is to learn how to ask a precise, reproducible question.

## 2. What the explicit matrix says

**ch02-explicit-layout-01-1**

Start with the Boolean function x zero exclusive-or x one, inside an ambient universe containing four declared variables.

**ch02-explicit-layout-01-2**

Only x zero and x one affect the output; x two and x three still determine where repeated values appear in the displayed layout.

**ch02-explicit-layout-02-1**

Live support tells us which inputs can change the function, while ambient width tells us how assignments are organized.

**ch02-explicit-layout-02-2**

Those are both real properties, but they should not be collapsed into one number or used as an automatic engine selector.

**ch02-explicit-layout-03-1**

The explicit correspondence matrix is an exact row-and-column truth layout over the declared variable split.

**ch02-explicit-layout-03-2**

That exactness does not imply that materializing the dense layout is always the cheapest way to evaluate or store the same function.

## 3. Explicit CM versus CM-IR

**ch03-explicit-versus-ir-01-1**

An explicit CM and CM-IR can describe the same Boolean computation while preserving different information.

**ch03-explicit-versus-ir-01-2**

The matrix makes every truth position visible; CM-IR makes canonical nodes, roots, sharing, and reusable compiled structure visible.

**ch03-explicit-versus-ir-02-1**

CM-IR can be compiled, interned, persisted, and evaluated without first rebuilding a dense matrix.

**ch03-explicit-versus-ir-02-2**

A dense CM may still be the required output, but that materialization belongs to a specific output boundary rather than every execution path.

**ch03-explicit-versus-ir-03-1**

Use the explicit matrix when the row-and-column truth artifact itself is required, and CM-IR when reusable structure is the question.

**ch03-explicit-versus-ir-03-2**

If performance matters, time construction, evaluation, extraction, and repeated reuse separately instead of hiding them behind one method name.

## 4. Where the work actually disappears

**ch04-transformation-mechanisms-01-1**

A raw syntax tree can repeat the same subtree, while structural common-subexpression elimination turns that repetition into one shared result.

**ch04-transformation-mechanisms-01-2**

Sharing-aware CSE-flat may also flatten safe associative structure, and CM-IR can add canonical normalization, interning, or merging.

**ch04-transformation-mechanisms-02-1**

A timing difference alone cannot tell us whether sharing, flattening, canonicalization, memory layout, or some other effect removed the work.

**ch04-transformation-mechanisms-02-2**

Mechanism claims need a workload where the relevant transformation is present, plus an ablation or structural count that can distinguish competing explanations.

**ch04-transformation-mechanisms-03-1**

CM-IR should not be compared only against a weak raw tree when sharing-aware CSE-flat already captures much of the common structure.

**ch04-transformation-mechanisms-03-2**

A fair comparison asks what additional transformation remains and whether this workload actually contains an opportunity for it to matter.

## 5. The boundary changes the answer

**ch05-measurement-boundaries-01-1**

Preparation includes parsing, compilation, canonicalization, interning, and any data structure that must exist before evaluation begins.

**ch05-measurement-boundaries-01-2**

A bare kernel times an already-built program, while a public wrapper can include setup, conversion, validation, extraction, or a complete truth-output contract.

**ch05-measurement-boundaries-02-1**

A lower repeated-evaluation cost can be valuable only after the one-time preparation cost has been paid.

**ch05-measurement-boundaries-02-2**

The break-even point depends on how many related evaluations occur, which outputs are required, and whether the prepared representation can actually be reused unchanged.

**ch05-measurement-boundaries-03-1**

Every comparison first needs exact output agreement, stable source identity, and a schedule that does not hand one method a systematic order advantage.

**ch05-measurement-boundaries-03-2**

Then the interval must respect the dependence structure, and the plotted ratio must name its numerator, denominator, workload, scope, and timing boundary.

## 6. What the corrected evidence supports

**ch06-corrected-evidence-01-1**

The corrected B2 and B4 result supports a workload-specific reduction for the compiled evaluator kernel, not every CM call.

**ch06-corrected-evidence-01-2**

EPFL AND-and-inverter workloads show parity where CSE-flat already captured the available structure, while the public wrapper remained slower on its broader boundary.

**ch06-corrected-evidence-02-1**

Three guarded CPU pods reproduced an overall CM-to-CSE-flat range near zero point nine one for the same compiled-kernel workload.

**ch06-corrected-evidence-02-2**

At live k sixteen the gap narrowed, and every pod passed exactness and source-integrity gates; replication did not convert the result into universal dominance.

**ch06-corrected-evidence-03-1**

The audit did not erase the useful result; it replaced a broad headline with a stronger, reproducible statement about one workload and one boundary.

**ch06-corrected-evidence-03-2**

It also retained parity and negative observations, because those results reveal where the proposed mechanism is absent or where surrounding costs dominate.

## 7. A practical decision rule

**ch07-decision-rule-01-1**

Choose the representation only after naming the required output, the reusable structure, and the pattern of repeated work.

**ch07-decision-rule-01-2**

Ambient width alone did not yield a reliable selector, and no evidence supports choosing an engine from its label.

**ch07-decision-rule-02-1**

For every performance statement, name the workload, required output, transformation, and exact timed path.

**ch07-decision-rule-02-2**

Then verify exactness, source identity, uncertainty, and reuse assumptions before transferring the result.

**ch07-decision-rule-03-1**

An explicit CM is an exact dense truth layout, while CM-IR is a canonical reusable program representation.

**ch07-decision-rule-03-2**

Performance belongs to a workload and measured boundary; precise coordinates turn caution into action.
