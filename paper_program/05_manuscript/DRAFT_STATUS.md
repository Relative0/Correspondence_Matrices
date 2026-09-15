# Manuscript draft status

Title: **Operator-Level Boolean Computation with Correspondence Matrices**  
Author: **Brian Theory**  
Draft date: 2026-09-15

## Drafted in manuscript prose

- Abstract, with no unsupported quantitative performance claim.
- Introduction and scoped contribution statement.
- Relationship to the 2018 public manuscript.
- CM states, axes, generic `[Θ]` notation, and XOR--AND contraction.
- CM selection, coefficient-space linearity, basis expansion, and the
  XOR/XNOR/Impax identities.
- Representation map distinguishing formula-valued LMs, numeric CMs, truth
  vectors, ANF coefficients, and STP logical structure matrices.
- Formula-valued LM definition, positive and general valuation, logical
  pairing, valuation commutation, and the nonphysical boundary.
- Operand transformation, aligned fusion, typed pure-structural, hybrid,
  whole-retabulation, and ordinary-fallback outcomes, and explicit layout
  admissibility.
- Compiler artifact table, formal judgment and inference rules, worked trace,
  signed-pair algorithm, soundness, termination, layout conversion, ownership,
  complexity, provenance counters, and verification boundary.
- Evaluation protocol v3 with a sole primary cell, direct packed-AST/common-LUT
  and synthesis comparators, explicit sharing/cache/fixed/recursion policies,
  workload strata, correctness gate, sampling procedure, and freeze manifest.
- Formula-valued LM theory now precedes the empirical sequence and explicitly
  remains outside the implemented and timed compiler path.
- Higher-arity size correction and initial limitations/conclusion text.
- Appendix-ready proofs for representation, selection, coefficient linearity,
  signed transformations, fusion, LM valuation/pairing, ANF separation, and
  higher-arity entry counting, plus the finite-verification scope.

## Deliberately incomplete

- The empirical results section contains no results. It must remain that way
  until the frozen corpus/run manifest and confirmatory campaign are complete.
- Figure 5 is not yet produced because it must visualize measured results.
- Exact primary-page citations for the Kim and Stern antecedents remain a
  literature-audit gate. Kim is therefore not yet cited in the manuscript.
- Final venue formatting, word count, acknowledgments, public archival
  identifier, tagged-PDF accessibility, and submission metadata remain open.

## Next drafting pass

Build and validate the protocol-v3 harness, perform a non-confirmatory pilot,
then freeze the natural corpus, AIG environment, and run manifest. Only after
that freeze should the confirmatory campaign populate Results and Figure 5.

`check_manuscript.py` performs lightweight notation, citation, label, and
environment checks. A full PDF build additionally requires completion of the
local MiKTeX setup.
