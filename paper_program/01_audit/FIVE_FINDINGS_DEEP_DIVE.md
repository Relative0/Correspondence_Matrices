# Deep review of the panel's five findings

**Manuscript:** *Operator-Level Boolean Computation with Correspondence Matrices*  
**Author:** Brian Theory  
**Review date:** 2026-09-15  
**Scope:** mathematical correctness, paper order, closest operational prior art,
baseline design, and the evidence boundary of the current working draft.

## Executive verdict

I agree with all five submission-blocker findings, with one important
qualification. Findings 1, 3, 4, and 5 can be resolved in the manuscript and
protocol now. Finding 2 cannot honestly be closed until a frozen confirmatory
campaign is run. The correct present action is to specify the missing arms and
timing boundaries, state the finite correctness evidence already available, and
leave every performance claim open. Filling a Results table with exploratory or
superseded measurements would make the paper weaker, not more complete.

The review also confirmed the panel's associated mathematical corrections. In
particular, the original LM notation overloaded `\Theta_{ij}` for two different
index domains. The revised paper now uses assignment indices
`\Theta_{xy}`, where `x,y\in\{1,0\}`, and position coefficients
`c_{ij}:=\Theta_{b_i b_j}`, where `i,j\in\{1,2\}`, `b_1=1`, and `b_2=0`.
That change is mathematical typing, not cosmetic typography.

## 1. Rule 1: transpose the operator, not the scalar

### Verdict: agree; corrected

For a row vector `\langle X|`, a matrix `[\Theta]`, and a column vector
`|Y\rangle`, the contraction is scalar-valued. Exchanging the two operand axes
requires transposing the operator:

```text
<Y|[Theta]|X> = <X|[Theta]^T|Y>.
```

The removed expression,
`<X|[Theta]|Y>^T`, merely transposes a scalar. Under ordinary transpose rules
that scalar is unchanged, so the expression reduces to
`<X|[Theta]|Y>` and does not implement operand exchange for a non-symmetric
operator. Implication is the clearest counterexample because its truth matrix is
not symmetric. The invalid equality could therefore silently reverse the
argument order of implication.

The figure and caption now retain only the valid identity and explicitly say
that the transpose belongs to the operator. The appendix separately proves that
transpose exchanges input assignments. No new or paper-specific transpose
semantics is introduced.

Related consistency corrections were made at the same time:

- Boolean contraction now uses a neutral indicator `\chi_x(r)` for both bra and
  ket components, avoiding a ket-indexed symbol on the bra side.
- The 90-degree map is explicitly defined as
  `[[a,b],[c,d]] -> [[c,a],[d,b]]` for clockwise rotation. The paper says that
  the counterclockwise rotation happens to agree for the particular symmetric
  XNOR matrix; it does not present rotation as the general operand transform.
- The early Impax statement is quantified over lowercase bits
  `x,y\in\mathbb B`; formula-valued bras and kets are introduced later.

## 2. Empirical campaign and Results

### Verdict: agree; protocol repaired, measurements still required

The panel is correct that an empty empirical section cannot substantiate a
compiler-performance claim. It is also correct that query reuse must be framed
carefully. Once two producer paths return the same four-bit truth word, the
subsequent lookup is the same shift-and-mask operation. Repeating that lookup
can amortize a preparation difference; it cannot create a distinct CM query
advantage.

The revised method therefore names the following boundaries separately:

1. structural support discovery, signed-frame alignment, token fusion, and
   completed-token return;
2. support discovery plus four complete scalar AST evaluations for exact
   retabulation;
3. environment construction plus one sharing-aware packed AST traversal;
4. flat/word-program lowering, binding, and prepared execution;
5. the common completed-token/LUT lookup;
6. ROBDD construction and query;
7. AIG import/construction, rewriting or mapping, and simulation/query on the
   circuit subset; and
8. conversion, allocation, and explicit packed or dense materialization.

The Results section now reports only the evidence that exists: exhaustive
small-domain checks and implementation tests. It explicitly withholds runtime,
memory, break-even, structural-success-frequency, and failure-region claims
until the corpus and manifest are frozen and the campaign is executed. Ties,
losses, timeouts, budget rejections, and ordinary-IR fallbacks must remain in
the final dataset.

Because the baseline and timing boundaries changed materially, protocol v1 is
marked superseded before measurement and
`EVALUATION_PROTOCOL_V2.md` is the current preregistration draft. No number from
an exploratory or superseded run is promoted into confirmatory evidence.

This finding is therefore **not closed**. It has been converted from an
underspecified blocker into a concrete run requirement.

## 3. Closest compiler and logic-synthesis literature

### Verdict: agree; novelty claim narrowed and comparison expanded

The prior-art concern is substantial. The individual ingredients “store a
small truth function in bits,” “negate or permute inputs,” and “combine truth
functions pointwise” are established techniques. The revised paper no longer
treats any one of them as the novelty.

NPN equivalence explicitly permits input negation, input permutation, and
output negation. Zhou, Wang, and Mishchenko define those transformations and
describe NPN classification as a standard component of synthesis and technology
mapping.[1] This overlaps directly with CM row/column swaps, transpose, and
token complement at the level of finite truth data. It differs in objective:
NPN classification searches or computes a representative of an equivalence
class, whereas the CM compiler retains a declared ordered row/column frame and
uses a typed transform to make two occurrences composable. The paper therefore
does not claim a new NPN canonicalizer.

The overlap with cut-based and AIG rewriting is equally important. Mishchenko,
Chatterjee, and Brayton represent four-input cut functions as 16-bit strings,
classify them up to NPN transformations, and use precomputed DAGs in an AIG
rewriter.[2] Their method also makes graph sharing operationally central. This
means a comparison against four-bit storage alone cannot establish novelty,
and a tree-only baseline could make the CM path look artificially favorable.

Modern logic-synthesis surveys likewise distinguish explicit truth tables for
small-support functions from network/DAG representations used when support
grows.[3] The revised manuscript therefore treats the constant four-bit token
as a small-support kernel, not a general compression of arbitrary Boolean
functions. Its candidate contribution is the integrated combination of:

- explicit row/column frame metadata;
- exact signed-literal admission and transformation rules;
- entrywise outer-connective fusion only after frame equality;
- a semantic invariant for the returned framed token;
- an exact retabulation lemma and ordinary-IR fallback; and
- a measured implementation boundary among token, pair surrogate, IR, flat
  program, and dense output.

The paper now contains a comparison table and a “closest operational
antecedents” discussion covering NPN classification, LUT/truth-table storage,
AIG/DAG rewriting, and bit-parallel simulation. Constant folding, partial
evaluation, hash-consing, and common-subexpression elimination remain relevant
implementation comparators and must be described with the final code snapshot.
The current claim is an integration claim whose usefulness is empirical, not a
claim that its primitive bit operations are new.

## 4. Direct four-bit packed evaluator

### Verdict: agree; an existing implementation is now made the primary direct comparator

The repository already contained the critical implementation, but the previous
phrase “sharing-aware scalar and packed-bit evaluator” did not define it tightly
enough. `bitset_backend.eval_expr_bitset` memoizes by expression-node identity
and evaluates the source DAG using machine bit operations. This is not CM
alignment or four-pass retabulation.

For variable order `(R,C)`, bit positions from least to most significant encode
`(00,01,10,11)`. Consequently:

```text
R = 1100_2
C = 1010_2
```

Applying each Boolean connective to those packed masks evaluates all four
assignments in one DAG traversal. Reading the four-bit result from most to least
significant bit gives `(11,10,01,00)`, exactly the declared CM token order. No
data-dependent reorder is required; only the bit-significance convention must
be stated.

This is the closest simple comparator for the pairable two-variable domain.
Bit-parallel simulation is established practice: Lee and colleagues describe
using machine words to simulate many Boolean patterns in parallel.[4] The
comparison is therefore between two ways to *produce* the same four-bit truth
word:

- CM structural compilation attempts to recognize signed primitives and fuse
  already aligned tokens; and
- the direct packed baseline evaluates the source DAG once over four assignment
  masks.

A second, prepared flat/word program is kept separate because lowering once and
executing many times answers a different reuse question. A four-bit LUT query is
also separate and common to both producers. This design prevents preparation,
evaluation, and lookup from being silently mixed.

## 5. Paper order

### Verdict: agree; rendered order changed

The title promises a computation paper. Leading with the representation map and
formula-valued LM theory made the manuscript resemble a broad matrix-logic or
quantum-analogy paper before the reader reached its strongest contribution.
That order also encouraged reviewers to judge novelty at the level where the
antecedents are strongest.

The rendered manuscript now follows this narrative:

1. conventions, Boolean operator matrices, and XOR–AND evaluation;
2. signed operand transforms and aligned entrywise fusion;
3. the structural theorem, exact-retabulation lemma, and top-level soundness
   boundary;
4. implementation artifacts, compiler cases, layout conversion, cost model,
   and verification boundary;
5. related-work and representation boundaries;
6. experimental method and current evidence status;
7. formula-valued LMs, valuation, and logical pairing as a symbolic extension;
8. discussion, limitations, and conclusion.

This order makes the compiler proposition visible before the denser symbolic
material. The LM section remains valuable, but its primary term is now
“logical pairing”; “measurement” is identified as historical interpretive
language and no physical or quantum-computing result is asserted.

## Additional mathematical audit

The five blockers exposed several related issues that needed correction across
the text, figures, appendix, and code:

- **LM indices.** Position indices `i,j\in\{1,2\}` use `c_{ij}`; assignment
  indices `x,y\in\{1,0\}` use `\Theta_{xy}`. The map
  `c_{ij}=\Theta_{b_i b_j}` is explicit in the manuscript and figures.
- **Outer product.** The custom `\otbktwo` notation is expanded once as an
  explicit formula-valued `2 x 2` matrix, making conjunction and XOR reduction
  visible.
- **Logical-pairing semantics.** The appendix proves
  `<A|[M_{X Theta Y}]|B> = (A<->X) Theta (Y<->B)` by showing that the two
  equivalence factors select exactly one coefficient.
- **ANF.** The Boolean Möbius transform is written concretely in the paper's
  true-first entry notation; it is not confused with positive LM valuation.
- **STP.** The delta-vector encoding and column order are declared, so the
  conversion is reproducible rather than diagrammatic.
- **Soundness.** Structural soundness, exact retabulation, and the top-level
  fallback theorem are separate results.
- **Admissibility.** The code now rejects duplicate axis names and overlapping
  row/column layouts. A repeated-variable expression cannot be misclassified as
  a two-axis pair.
- **Cost.** Negation-chain inspection, possible repeated support scans,
  AST-occurrence versus unique-DAG-node counts, and explicit-output size are
  stated separately.

## Remaining submission gates

The mathematical and presentation repairs can be compiled and independently
reviewed now. The paper is not submission-ready until three external facts are
established: the v2 protocol and corpus are frozen; the confirmatory campaign is
completed without selective attrition; and a logic-synthesis specialist reviews
the integrated novelty claim against current NPN/LUT/AIG practice. A final
symbolic-logic reviewer should independently check the LM identity and valuation
proof after typesetting.

## Sources

1. X. Zhou, L. Wang, and A. Mishchenko, “Fast Adjustable NPN Classification
   Using Generalized Symmetries,” *ACM TRETS* 12(2), Article 7, 2019.
   [Author-hosted paper](https://people.eecs.berkeley.edu/~alanmi/publications/2019/trets19_npn.pdf),
   DOI 10.1145/3313917.
2. A. Mishchenko, S. Chatterjee, and R. K. Brayton, “DAG-Aware AIG Rewriting:
   A Fresh Look at Combinational Logic Synthesis,” DAC 2006, 532–536.
   [Author-hosted paper](https://people.eecs.berkeley.edu/~alanmi/publications/2006/dac06_rwr.pdf),
   DOI 10.1145/1146909.1147048.
3. E. Testa, M. Soeken, L. G. Amarù, and G. De Micheli, “Logic Synthesis for
   Established and Emerging Computing,” *Proceedings of the IEEE* 107(1),
   165–184, 2019.
   [Author-hosted paper](https://si2.epfl.ch/~demichel/publications/archive/2019/08478240.pdf),
   DOI 10.1109/JPROC.2018.2869760.
4. W. Lee, H. Riener, A. Mishchenko, R. K. Brayton, and G. De Micheli, “A
   Simulation-Guided Paradigm for Logic Synthesis and Verification,” *IEEE
   TCAD* 41(8), 2573–2586, 2022.
   [Author-hosted paper](https://people.eecs.berkeley.edu/~alanmi/publications/2021/tcad21_sim.pdf),
   DOI 10.1109/TCAD.2021.3108704.
