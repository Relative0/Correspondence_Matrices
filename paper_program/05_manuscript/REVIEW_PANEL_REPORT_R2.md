# Fresh review-panel report after the revised manuscript

**Manuscript:** *Operator-Level Boolean Computation with Correspondence
Matrices*  
**Author:** Brian Theory  
**Review round:** R2, based on the current 19-page compiled manuscript and its
current LaTeX, proof appendix, implementation, tests, and evaluation protocol  
**Panel type:** three simulated independent reviewer roles, not contacted human
reviewers

## Executive verdict

The mathematical core is now sound in the areas that previously required
repair. The manuscript is ready for expert circulation as a working preprint or
technical report. It still requires major revision before submission as a
completed applied-computing paper.

The highest-priority new finding is an implementation/specification mismatch:
the compiler strategy called `structural` can retabulate an unsuccessful child
and then fuse it with a structurally compiled child. This creates a hybrid
structural--retabulation path that is not explicitly covered by the manuscript's
pure-structural/retabulation/fallback classification. This must be resolved
before the empirical protocol is frozen.

The other submission blockers are the still-unfrozen and unexecuted
confirmatory campaign, a non-singular primary success criterion, incomplete
natural-corpus/AIG decisions, and the placement of the formula-valued LM theory
after the Results/evidence section.

## Panel composition and independent verdicts

### Reviewer 1: mathematical logic and semantics

**Verdict:** no critical mathematical error remains in the requested core;
ready for expert circulation, but the compiler proof should be made more formal
for a theory-oriented venue.

Confirmed correct:

- the operand-exchange rule uses the operator transpose;
- the contraction is explicitly XOR--AND over `GF(2)`, not ordinary real
  multiplication;
- the defined clockwise rotation maps the XNOR CM to the XOR CM;
- XOR/XNOR entrywise XOR yields the all-ones Impax CM;
- structural soundness, exact retabulation, and fallback are stated as distinct
  claims;
- LM position coefficients use `c_{ij}:=\Theta_{b_i b_j}` rather than
  overloading truth-assignment indices;
- the logical-pairing and valuation identities are correct;
- positive LM valuation, Boolean Möbius/ANF conversion, and STP conversion are
  correctly distinguished.

Remaining mathematical work:

1. Express the compiler as a typed judgment over a declared AST grammar, with
   inference rules and an induction proof, if targeting formal methods or
   theoretical computer science.
2. Correct small typing/presentation points: lowercase `x,y` in the numeric
   same-operands theorem; explicitly type the STP truth row and entrywise
   complement; write `b_{i^*}=v(A\Leftrightarrow X)` in the appendix; and place
   an explicit conjunction between an ANF coefficient and its monomial.
3. Replace the abstract's statement that the evaluation is already “frozen”
   with “a protocol to be frozen before execution.”

### Reviewer 2: compiler, systems, and experimental methodology

**Verdict:** major revision; conditionally ready for a non-confirmatory harness
pilot after the hybrid-path issue is resolved.

Confirmed improvements:

- the mandatory direct packed four-bit comparator is both specified and
  implemented;
- once producers yield the same token, common LUT query cost is no longer
  claimed as a CM advantage;
- NPN, LUT, AIG, DAG-sharing, and bit-parallel antecedents are treated
  conservatively;
- the cost model distinguishes AST occurrences, unique DAG nodes, negation
  chains, output axes, support-discovery cost, and dense-output cost;
- unsupported speed, memory, prevalence, and break-even claims are withheld;
- targeted pair-alignment and packed-backend tests pass.

Submission blockers and pre-run corrections:

1. **Classify or eliminate the hybrid path.** `_compile_pair` may return a
   retabulated child and later fuse it with another child. Either prove this
   hybrid construction, restrict retabulation to the root, or expose separate
   `pure_structural` and `hybrid_pair` strategies. Record root outcomes as pure
   structural, hybrid, full retabulation, or ordinary fallback.
2. **Make the primary test singular.** Select one exact primary comparison or
   define a multiplicity-controlled family-level rule. Justify the 20% time and
   10% memory thresholds.
3. **Freeze the corpus and synthesis arm.** Record natural-circuit provenance,
   licenses, extraction/exclusion rules, support and sharing distributions, and
   decide whether the ABC/AIG arm is mandatory for a defined subset.
4. **Repair instrumentation before confirmation.** Current `nodes_total` and
   `pairable_ratio` are not comparable across strategies. Record AST
   occurrences, unique nodes, negation scans, speculative pair constructions,
   and final root outcome separately.
5. **Predeclare runtime policies.** Resolve recursion behavior for deeply
   skewed trees, support fixed substitutions in the packed comparator or exclude
   them, distinguish cache-miss/cache-hit setup, and use one shared LUT query
   implementation for every token producer.
6. **Represent sharing explicitly.** Record both `N` and `U`, and stratify
   identity sharing, equal-but-separately-allocated subtrees, and no sharing.

### Reviewer 3: editor, accessibility, and audience fit

**Verdict:** defensible applied-computing narrative and suitable working
preprint; not yet a completed submission.

Confirmed improvements:

- the CM/operator, alignment/fusion, and compiler contribution appears early;
- the prior-art boundary and direct packed comparator are clear;
- “logical pairing” now has an exact proposition and does not imply physical or
  quantum measurement;
- the evidence boundary is unusually clear and appropriately conservative;
- the compiled PDF is clean, with no clipping, missing references, or broken
  symbols.

Structural and presentation recommendations:

1. Move the formula-valued LM extension before Experimental Method, or move it
   to a companion paper/appendix. Theory introduced after Results makes the
   manuscript appear to restart.
2. State explicitly that the present compiler operates on numeric CM tokens and
   pair metadata, not formula-valued LMs, if that is the intended boundary.
3. Split the representation figure: retain CM-to-truth-vector-to-ANF/STP with
   related work, and place LM-to-CM valuation with the LM section.
4. Add typed pseudocode/inference rules and one worked compiler trace showing
   AST, frame metadata, transformations, fusion, fallback, and counts.
5. Add a reproducibility statement with implementation version, supplement or
   repository location, commands, environment, and hashes.
6. Improve print accessibility: larger internal figure type, vector figures,
   ragged-right or redesigned comparison tables, metadata/keywords, and tagged
   PDF when preparing the public version.

## Consensus: what is now established

The following earlier concerns should no longer be reported as defects:

- Rule 1 correctly transposes the operator when operands exchange places.
- XOR--AND contraction is correctly typed and distinguished from ordinary
  arithmetic matrix multiplication.
- the rotation convention is explicit and the XNOR-to-XOR example is correct;
- Impax is correctly typed as the all-ones tautological operator;
- LM coefficients, polarity positions, and truth-assignment indices are no
  longer conflated;
- LMs are not equated with Zhao-style polynomials or ANF coefficients;
- ANF and STP objects are presented as external representations reached through
  explicit conversions;
- the manuscript does not claim that four-bit truth tables, Boolean matrix
  operations, NPN transforms, or LUT/AIG machinery are individually novel;
- the paper does not yet claim empirical superiority.

## Consolidated revision order

### P0: required before an experiment freeze

1. Resolve the hybrid compiler semantics in code, theorem, tests, diagnostics,
   and experimental arm names.
2. Define one primary comparison or a multiplicity-controlled primary family;
   justify its practical thresholds.
3. Freeze the corpus, AIG/ABC decision, sharing strata, recursion policy,
   fixed-substitution policy, cache state, timing boundaries, common query, and
   immutable manifest.
4. Run only a non-confirmatory pilot to find harness defects; then freeze a new
   run identifier before any confirmatory measurement.

### P1: required before manuscript submission

1. Move the LM theory before the empirical sequence or relocate it outside the
   main paper, and state whether it participates in the compiler.
2. Add formal typed pseudocode or inference rules, including the chosen hybrid
   policy, plus a worked trace.
3. Execute the confirmatory campaign and report all wins, ties, losses,
   timeouts, fallbacks, memory results, and conversion/materialization costs.
4. Add the reproducibility and availability statement.

### P2: polish

Apply the localized mathematical wording fixes, split the representation
figure, enlarge small annotations, improve table typography, and add document
accessibility metadata.

## Venue and audience implication

The best fit after a successful, reproducible evaluation is an applied
symbolic-computation or logic-and-computation venue. Logic synthesis/EDA becomes
plausible only if circuit workloads and sharing-aware/AIG baselines establish a
useful region. The current theorems alone are probably too elementary for a
mathematical-logic contribution and too implementation-specific for a
theory-only compiler paper. As a working technical report, however, the present
manuscript is ready to circulate for specialized feedback.
