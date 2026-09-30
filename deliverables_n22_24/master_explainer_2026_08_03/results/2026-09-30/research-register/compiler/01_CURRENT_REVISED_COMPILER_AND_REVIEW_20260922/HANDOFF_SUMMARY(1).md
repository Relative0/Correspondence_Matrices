# Computational CM Paper Handoff Summary

## What this second paper is

The second paper is the computational manuscript **Operator-Level Boolean Computation with Correspondence Matrices**. It was already being developed before the CM/LM foundations split and is explicitly referred to in the newer foundations work as the computational companion.

Its intended computational thesis is:

> represent binary connectives as compact CM tokens carrying typed operand-frame metadata; normalize signed/swapped occurrences into a canonical frame; perform sound local operator fusion/folding before operand evaluation or polynomial expansion where possible; and fall back safely when the local CM rule does not apply.

## Why the split happened

The earlier manuscript also contained formula-valued LM theory, valuation, logical pairing, ANF/STP representation discussion, and other foundations material. Those topics are now developed much more fully in the companion foundations manuscript **Correspondence and Logical Matrices: A Boolean Operator Calculus**.

The computational paper should therefore be revised to avoid duplicating that mathematics and instead focus on:

- compiler semantics;
- typed frame recognition and alignment;
- pure/hybrid/retabulated/fallback paths;
- implementation architecture;
- cost model;
- fair baselines;
- empirical mechanism evidence;
- negative boundaries;
- confirmatory evaluation.

## Important existing evidence in the current computational manuscript

The current manuscript reports three distinct evidence levels:

1. **Correctness/implementation checks:** finite tests plus exhaustive signed alignment/fusion checks.
2. **S1/S2 exploratory mechanism evidence:** some strata show substantial pre-expansion symbolic savings, but CM folding ties an equivalently capable generic local truth-function optimizer on the main reduced-output metrics.
3. **P14-PY0 dispatcher study:** a preregistered negative aggregate result; selected synthetic folds can be highly profitable, but the dispatcher loses overall against direct ANF lowering on the acquired corpora.
4. **Protocol v3:** broader token/packed comparison remains unexecuted in the manuscript snapshot.

These must not be merged into one headline result.

## Key review conclusions already addressed in the manuscript

- hybrid structural + retabulation behavior is now explicit rather than hidden;
- root outcomes are distinguished as pure structural, hybrid pair, full retabulation, and ordinary fallback;
- direct packed four-bit evaluation is a mandatory comparator;
- sharing is stratified by AST occurrences and unique nodes;
- fixed substitutions and shared token query behavior were added;
- the primary success criterion was made singular;
- ABC/AIG is mandatory for a frozen translatable subset in protocol v3;
- kernel-only fusion is not presented as an end-to-end speed claim.

## Post-split recommendation

The new agent should first create a **split map** and remove most LM theory from the computational paper. The current paper is a strong source document, but it should not simply be polished in place without reconsidering its architecture.

A likely final paper is shorter, more computational, and more explicit about the distinction between:

- mathematical soundness of frame-aware fusion;
- reduction in symbolic work;
- uniqueness/non-uniqueness to CM representation;
- actual end-to-end performance.
