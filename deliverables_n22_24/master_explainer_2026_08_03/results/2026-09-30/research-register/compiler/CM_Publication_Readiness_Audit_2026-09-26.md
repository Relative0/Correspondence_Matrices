---
title: "Publication-Readiness Audit"
subtitle: "Operator-Level Boolean Computation with Correspondence Matrices"
author: "Independent source review, mathematical checks, and simulated referee perspectives"
date: "26 September 2026"
geometry: "margin=0.85in"
fontsize: 11pt
colorlinks: true
linkcolor: blue
urlcolor: blue
header-includes:
  - \usepackage{longtable,booktabs,array}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyhead[L]{\small CM compiler -- publication-readiness audit}
  - \fancyhead[R]{\small 26 September 2026}
  - \fancyfoot[C]{\thepage}
  - \setlength{\headheight}{15pt}
  - \setlength{\emergencystretch}{3em}
---

# I. Executive verdict

**Overall readiness: 65.3/100, reported as approximately 65/100.** This is a structured editorial assessment, not an acceptance probability, a measurement with statistical precision, or a percentage of work completed. Confidence is high for the elementary mathematical checks and inspected source behavior, moderate for overall positioning, and lower for the completeness of historical empirical reproduction and the exhaustion of prior art.

| Decision | Current verdict |
|:--|:--|
| Public preprint | **GO AFTER SPECIFIED CORRECTIONS** |
| Serious peer-reviewed submission | **MAJOR REVISION BEFORE SUBMISSION** |
| Complete paper reproducibility package | **NOT YET REPRODUCIBLE** |
| Best present identity | Narrow compiler-method/specification paper with exploratory and negative empirical boundaries |
| Findings | **0 P0; 7 P1; 4 P2; 3 P3** |

The Boolean core is substantially sound. I did not find a counterexample to selection, signed normalization, same-frame fusion, structural soundness, the explicitly syntactic completeness theorem, or exact tabulation. The worked example is correct. Fresh exhaustive local checks and bounded/reference-model tests passed. The current manuscript also makes several important limitations unusually explicit: pointwise truth-table fusion is classical, generic local optimization matches the exploratory symbolic reductions, the dispatcher study is negative against direct compilation, and the designated pair-compiler confirmatory protocol remains unexecuted. These are strengths, not reasons to manufacture an overclaim that the paper no longer makes. [M, Sections 2-4, 8-10; E1]

Nevertheless, the current manuscript is not ready for serious submission. The most concrete defect is an output-contract mismatch: the implementation materializes all retained ambient row/column axes, including fixed or irrelevant ones, whereas the artifact table and cost model describe unfixed output axes. The formal judgments also need a cleaner separation between admissible derivations and the derivation chosen by a compiler strategy. The exact publication package does not close the manuscript-to-code-to-test-to-raw-data chain. Finally, careful disclaimers do not by themselves establish that the residual compiler contribution is sufficiently differentiated or empirically informative for a standalone research paper. [M, lines 258-328, 430-496, 567-619; C1-C3]

**No P0 means no demonstrated collapse of the central Boolean result. It does not mean there are no release conditions.** The P1 findings include contract corrections needed before this draft should be released as an implementation-backed preprint. A performance-oriented submission remains on hold until directly matched evidence exists. A narrower methods or negative-results submission is possible in principle, but its reusable contribution must be made demonstrable rather than merely asserted.

The manuscript was not edited during this audit. The six referee reports below are simulated disciplinary perspectives produced within this audit, not six independently recruited human reviews.

# II. What was actually inspected

## Archive and current manuscript

The supplied `CM Computation(1).zip` contains **58 files**: 31 Markdown files, three PDFs, five TeX files, six CSV files, six JSON files, four text files, one Python file, one bibliography file, and one diff. The directory tree, manifests, current manuscript, historical manuscripts, review/response records, contribution ledgers, and reproducibility pointers were examined. Text files were screened recursively; substantive current and historical review/evidence documents were read beyond their filenames. [E2]

The designated current manuscript is the **14-page** PDF and corresponding TeX in `01_CURRENT_REVISED_COMPILER_AND_REVIEW_20260922/`. The source was read through its definitions, displayed rules, proofs, examples, evidence sections, appendices, and references. The current source was compiled independently. The rebuilt PDF has 14 pages and matches the supplied PDF's normalized extracted text on every page. This is not a claim of binary-identical PDFs. Rendered pages were inspected, including the alignment/fusion diagram, inference rules, and empirical table. [E3]

Historical material includes a 24-page portfolio predecessor and a 21-page legacy manuscript. Their role is source lineage and review context, not replacement of the designated current draft. Earlier review reports and responses were checked against the actual revised statements rather than accepted at face value.

## Implementation examined

The live public repository was accessed through the GitHub connection. Its inspected `main` revision was pinned to:

`0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`

The repository README and complete relevant portions of `cm_build_pair.py`, `cm_token.py`, and `cm_normalize.py` were inspected. These establish the behavior of the pair path, token operations, layout conversion, and dense output lifting at that revision. They do **not** establish that this revision generated every historical table or the reported 116-test run. [C1-C3]

## What was executed

This audit executed independent finite mathematics and reference-model tests, checked archive hashes, rebuilt the current manuscript, and attempted the retained historical static manuscript checker. It did **not** execute the author's full compiler test suite, rerun the 51,102-row timing campaign, reproduce bootstrap intervals from raw measurements, or run the unexecuted confirmatory study. Those distinctions are essential to the verdict.

The sole Python file shipped inside the ZIP is a historical **manuscript checker**, not the compiler implementation or an exhaustive Boolean verifier. Its execution fails because the historical protocol-v3 file it requires is absent from the retained relative location. That failure concerns the completeness of the historical package, not the validity of the current TeX build. [E4]

## External research

Fresh primary-source checks covered Cheng-Zhao-Xu's Boolean matrix calculus, Mishchenko-Chatterjee-Brayton's DAG-aware AIG rewriting, official Kitty and mockturtle documentation, Bryant's BDD work, equality saturation through egg, Darwiche-Marquis's knowledge-compilation framework, Bricken's matrix-logic document, and official JOSS review criteria. The strongest claim-level comparisons are discussed in Section IX. This is a substantive targeted search, not a claim that every prior publication in every neighboring field has been exhausted. Some externally hosted PDFs could be text-read but not screenshot-rendered by the available web renderer; failed rendering was not silently counted as visual inspection.

# III. Evidence hierarchy and version determination

The root `README_FIRST.md` and `CLAIMS_AND_UNIQUENESS.md` designate the revised compiler directory as current. I therefore use the following hierarchy:

1. Current TeX/PDF for what the manuscript claims.
2. Pinned executable source for what the inspected implementation does.
3. Raw results and reproducible commands, when available, for empirical facts.
4. Reports, ledgers, reviewer responses, and handoffs as claims requiring corroboration.
5. Historical manuscripts and prompts for lineage, not current authority.

The current TeX SHA-256 is:

`5189ac98c826c54af4e291e0516216caffa93dc521e54bec679ee33a2e5e7fd4`

All **54 entries in the current root manifest** matched the corresponding archived files. The separate review manifest also passed **2/2** checks. These checks establish file integrity relative to the supplied manifests, not scientific validity or complete coverage of every necessary research artifact. [E2]

The relocated historical manifest originally records 52 files. Reconciliation by content hash finds **47 of those 52 historical contents elsewhere in the current archive**, with five unmatched. Counting every broken historical relative path as an absent artifact would overstate the problem. The actionable issue is to document relocation and the five unmatched historical entries, not to declare the current manifest corrupt. [E5]

The automated relative-Markdown-link scan found **19 unresolved links**. Some point intentionally outside this package. This is a bounded navigation check, not a complete census of unavailable data. Four duplicate-content groups were found, including duplicated R1, R2, and response documents across current and historical directories. They are the same evidence appearing twice, not independent corroboration.

The package's September 26 research-viability assessment was treated as another analysis to test. Its conclusions were not used as a substitute for source inspection, proof checking, or fresh literature comparison.

# IV. Publication-readiness scorecard

Half-points are used where the evidence falls between the prompt's integer anchors. Weighted contribution is `weight x score / 5`. An unassessable item is not automatically mathematically false: the low score records missing assurance.

| Category | Weight | Score /5 | Weighted /100 |
|:--|--:|--:|--:|
| Mathematical correctness | 15 | 4.5 | 13.5 |
| Formal completeness and proof adequacy | 10 | 3.5 | 7.0 |
| Novelty and differentiation | 12 | 2.5 | 6.0 |
| Prior-art coverage and citation quality | 8 | 3.5 | 5.6 |
| Claim-evidence calibration | 10 | 4.0 | 8.0 |
| Experimental methodology and evidence | 10 | 2.0 | 4.0 |
| Manuscript-implementation alignment | 8 | 2.5 | 4.0 |
| Reproducibility and artifact quality | 8 | 2.0 | 3.2 |
| Scope and substantive completeness | 6 | 4.0 | 4.8 |
| Exposition and readability | 5 | 4.0 | 4.0 |
| Resolution of reviewer concerns | 4 | 3.5 | 2.8 |
| Contribution positioning and venue fit | 4 | 3.0 | 2.4 |
| **Total** | **100** | | **65.3** |

**Mathematical correctness -- high confidence.** The stated local algebra and semantic soundness arguments check out. A score of 5 requires a fully consistent domain/strategy/output contract and stronger linkage to the actual execution path. This is not a penalty for the mathematics being elementary; significance is scored separately.

**Formal completeness -- high confidence.** The structural fragment is defined, the induction is valid, and tabulation has a clear truth-value invariant. Missing precision concerns support, strategy-indexed outcomes, and how a selected pair frame relates to ambient layout lists. A complete operational contract would materially improve this score.

**Novelty -- moderate confidence.** The manuscript responsibly narrows its claim, but the remaining novelty of explicit frame metadata plus familiar truth-table rewriting is not yet convincingly established. To reach 5, the paper needs a concrete reusable distinction, a close comparator analysis, and evidence that readers gain more than a renamed implementation pattern. Absolute priority is not established.

**Prior art -- moderate to high confidence.** Many important antecedents are already credited. Improvements should concentrate on directly comparable truth-table/cut implementations and a feature-level comparison, not a longer undifferentiated bibliography. At least one bibliographic page range needs correction.

**Claim-evidence calibration -- high confidence.** Classical algebra, the generic tie, negative results, and an unexecuted study are explicitly acknowledged. The remaining problem is making reported tests, available artifacts, and independently reproducible evidence unmistakably different, and ensuring output-cost language matches the API.

**Experimental evidence -- moderate confidence.** The planned task contract is thoughtful and the negative result is honestly presented. But the current pair-compiler primary endpoint lacks completed confirmatory evidence, and supplied raw evidence is insufficient for a fresh reconstruction of historical statistics. A plan is not a completed experiment.

**Implementation alignment -- high confidence on inspected functions.** The token transformations, strategy modes, ownership, and row/column restrictions largely align. Retained output axes, root-fallback commitment, and derivability-versus-strategy language remain material. Exact historical revision alignment is not proven by finding current code online.

**Reproducibility -- high confidence about package contents.** The manuscript builds and manifest checks pass. The complete source/test/data/protocol chain is not closed. A source URL and a report of passing tests are not equivalent to an executable paper artifact.

**Scope -- high confidence.** The compiler/foundations split is coherent. The paper should not absorb unrelated LM, phase, or quantum theory to inflate depth. Some older multi-endpoint material can be shortened.

**Exposition -- high confidence.** The revised rules and worked example are substantially clearer than the older concerns suggest. A single decision table and a precise API contract would eliminate much remaining ambiguity.

**Reviewer resolution -- moderate to high confidence.** Many prior issues genuinely are fixed; some concern removed material. Artifact closure and operational precision remain unresolved. Repeated copies of the same review do not increase confidence independently.

**Positioning -- moderate confidence.** The methods/specification identity is more credible than a new Boolean-algebra or demonstrated-speedup identity. Venue choice should follow the evidence completed next, not be used to evade the same scientific questions.

# V. Central contribution audit

## Claim inventory

| Claim family | Assessment | Main evidence |
|:--|:--|:--|
| Four coefficients represent a binary function | Correct, elementary, not residual novelty | M Section 2; E1 |
| Signed/swapped frame transport | Correct; classical transformation ingredients | M Section 3; C2; E1 |
| Same-frame pointwise fusion | Correct; direct prior-art antecedent | M Theorem 1; L1 |
| Structural rule soundness | Correct for the defined fragment | M Theorem 2 |
| Syntactic-fragment completeness | Correct, deliberately limited | M Theorem 3 |
| Exact local tabulation | Correct with explicit syntactic support and substitutions | M tabulation lemma; C1 |
| S/T/H semantic soundness | Correct; operational provenance needs separation | M Theorem 4; C1 |
| Fallback preserves program meaning | Conditional on the ordinary builder; not an independent audit of that builder | M Section 4; C1 |
| Constant-size fusion kernel | Correct, not constant-cost end-to-end compilation | M Section 5 |
| Dense output bound | Correct general output principle; wrong parameter for the inspected ambient API | M lines 434, 488-496; C1/C3 |
| S1/S2 mechanism advantage over direct expansion | Reported; not unique against matched generic optimization | M Section 8.2 |
| P14 dispatcher boundary | Reported negative result on a different endpoint | M Section 8.3 |
| Pair-compiler speed advantage | Not established; current draft does not claim it | M Sections 7-10 |
| Novel typed compiler formulation | Plausibly useful packaging; substantive differentiation unresolved | M Sections 1, 6, 9; L1-L4 |

## Strongest defensible contribution

The manuscript gives an explicit, frame-carrying specification of a restricted two-variable truth-function compiler: normalize signed/swapped primitive occurrences into a declared row/column frame; preserve the frame through complement and pointwise fusion; distinguish structural, tabulated, and hybrid derivations; and fall back when the selected strategy cannot produce a pair result. It provides semantic soundness and completeness for a precisely generated syntactic fragment, together with reported exploratory and negative results that prevent the local kernel from being mistaken for a demonstrated general performance advantage. This is an integration, correctness-contract, and evaluation-boundary contribution, not a new algebra of truth tables. [M Sections 2-10; C1-C3]

The unresolved question is whether that integration is sufficiently non-obvious, reusable, and supported to justify a standalone research paper. An explicit failure-mode taxonomy, executable contract tests, and a task-matched comparative result would strengthen that case far more than adding unrelated theorems.

## What should not be claimed

The paper should not claim first discovery of Boolean truth matrices, first pointwise composition of truth vectors, a general semantic canonicalizer, completeness for arbitrary Boolean formulas, automatic retention of successful child folds after root failure, compression of all requested outputs to four bits, a demonstrated pair-compiler speedup, or unique performance gains that an equally informed generic truth-function optimizer cannot realize. It should not describe a not-yet-archived historical run as independently reproduced in this audit.

# VI. Mathematical correctness report

## Selection and the Boolean field

The true-first vector and matrix convention is internally consistent. XOR-AND contraction selects exactly one coefficient because the two state vectors are one-hot. The proposition does not require an invalid distributivity of an arbitrary outer connective over XOR. The use of $\mathbb F_2$ should continue to mean XOR as addition and AND as multiplication, while implication, OR, and equivalence remain Boolean functions rather than field-linear maps. [M lines 113-165]

In particular, linearity in coefficient space is not linearity in input truth values. The binary AND table still represents a nonlinear Boolean function of its inputs. Nothing in the inspected proof requires that false identification.

## Transpose, polarity, and complement

Operand exchange corresponds to transpose; input negations permute the corresponding state axis; output negation complements all four coefficients. The source implements these actions consistently, including the subtlety that negating the first source operand affects the column axis after an operand swap. These transformations passed exhaustive token-level checks. [M lines 169-242; C2; E1]

The introduction's counterexample is sound: storing both $X\Rightarrow Y$ and $Y\Rightarrow X$ as the same untransported implication token and XORing them would give zero. Correct transport makes their XOR the exclusive-or function, token `0110`.

## Theorem 1: same-frame fusion

**Verified.** Once both tables refer to the same ordered assignments, selecting a coefficient after applying an outer Boolean function entrywise equals applying that function to the two selected coefficients. The common-frame premise is essential. The proof is short because the underlying fact is elementary. The current manuscript correctly identifies it as classical and cites a direct truth-vector antecedent. [M lines 193-210; L1]

This theorem is a legality invariant for the compiler, not strong evidence of mathematical novelty by itself.

## Theorem 2: structural soundness

**Verified for the stated constructors.** The primitive case follows from frame transport; NOT preserves the frame and complements the output; fusion preserves the frame and uses Theorem 1. Structural induction is sufficient. Distinct returned row/column variables and a substitution map that binds neither must remain explicit assumptions. [M lines 249-313, 370-376]

## Theorem 3: structural completeness and token uniqueness

**Correct, modest, and appropriately qualified.** The structural fragment is generated by the same primitive, NOT, and same-frame binary constructors admitted by the compiler. Completeness follows by induction on that grammar. The unique token is unique for the represented function in a fixed ordered frame. The theorem is not semantic completeness for all expressions equivalent to that function, nor uniqueness of provenance or derivation. [M lines 378-395]

Do not revive an old objection by accusing the current paper of claiming semantic completeness: it expressly disclaims that. Equally, do not market this closure theorem as a maximal characterization of pair-compilable functions. Its value is the exact specification of a guaranteed recognition fragment.

## Exact tabulation and Theorem 4

**Semantically correct, operationally underspecified.** Four evaluations determine the binary truth function exactly. NOT and fusion above tabulated children remain sound; marking their ancestry as H is sensible. The source's root classification implements this distinction. [M lines 315-328, 398-407; C1]

However, the displayed TAB rule does not encode strategy permission or failure of a preferred structural derivation. For $X\land Y$, both an S primitive derivation and a T tabulation derivation satisfy the displayed rules. This is not a contradiction in the truth token. It means the judgment describes admissible derivations unless a separate strategy relation says which one is selected.

A second example makes the fallback issue visible. Let

$$e=X\lor(Y\land Y).$$

The TAB rule is applicable on the syntactic frame $\{X,Y\}$. The pure-structural implementation nevertheless returns no pair, because it is not allowed to use that rule and cannot structurally construct the needed children. Therefore, "no pair judgment is derivable" cannot be used unqualified as the meaning of failure of every strategy.

**Recommended repair:** retain the present relation for admissible derivations and add a strategy-indexed operational outcome, for example $\operatorname{compile}_s(e,\Gamma)$. State that successful outcomes witness a valid judgment, but not every valid judgment is selected by every strategy. Then define the ordered primitive/recursive/tabulation/failure cases. This avoids weakening the soundness proof or pretending that token uniqueness implies provenance uniqueness.

## Syntactic support versus essential dependence

The implementation collects variable names occurring in the AST and removes fixed names. It does not compute essential functional support. [C1, `_pairable_vars` and `_expr_stats`]

For

$$e=(X\land Y)\mathbin{\Updownarrow}(X\land Y),$$

syntactic support is $\{X,Y\}$ but essential support is empty. Returning a zero token with that frame is correct. Define explicitly

$$\operatorname{vars}_F(e)=\operatorname{vars}(e)\setminus\operatorname{dom}(F),$$

or give `supp` this explicitly syntactic meaning. Do not silently replace it with a semantic minimization criterion, which would change the implemented language of admissions.

## Worked example

The revised example is correct:

$$[X\Rightarrow\neg Y]=0111,\qquad [\neg Y\Rightarrow X]=1110,$$

$$0111\mathbin{\Updownarrow}1110=1001=[X\Leftrightarrow Y].$$

The example usefully illustrates transport before fusion and should remain. [M lines 333-359; E1]

## Complexity and termination

Constant-size token fusion and four-evaluation tabulation are accurately separated from recognition and materialization. The $O(k)$ signed-literal scan, occurrence-based structural traversal, possible repeated support scans, and distinction between occurrence count $N$ and unique-node count $U$ are appropriate cautions. A finite-tree recursion argument proves mathematical termination, not immunity from a Python recursion limit. The bounded skewed-tree protocol addresses an execution hazard without changing that distinction. [M lines 475-499, 556]

The dense-output statement needs correction for the inspected API. Moreover, `2^n bits` describes logical information, not necessarily physical NumPy allocation: an owned Boolean array stores one element per entry and is not a bit-packed token. Report logical entries, packed bytes where applicable, and actual allocated bytes separately.

# VII. Independent computational verification

Fresh script: `verification/independent_finite_checks.py`. It uses an independent scalar truth-function oracle, token transformations, and a small reference AST compiler. It does not import the author's implementation. Its purpose is to check local identities and explicit operational examples, not benchmark production code.

| Verification family | Executed coverage | Result |
|:--|:--|:--|
| One-hot selection | 16 tokens x 4 assignments | PASS |
| Signed frame transport | 128 representation records; 512 assignments | PASS |
| Signed same-frame fusion | 262,144 table cases; 1,048,576 assignment checks | PASS |
| Bounded structural fragment | 8,080 constructed expressions | PASS |
| Seeded reference strategies | 5,000 expressions x 3 modes = 15,000 runs | PASS |
| Successful seeded outputs | 6,615 tokens checked against the scalar oracle | PASS |

The signed-fusion enumeration includes 16 possible left tables, 16 right tables, eight signed/swapped frames for each, 16 outer binary functions, and all four assignments. Some table cases represent the same Boolean function through different frames; these are representation tests, not distinct mathematical functions.

The bounded structural set contains 40 signed primitives, 40 negations of primitives, and the 8,000 binary combinations of primitive pairs under five supported connectives. It is not an exhaustive enumeration of all finite structural expressions.

The seeded reference runs use seed `20260926`, expressions of bounded depth, and fixed-substitution cases. The result breakdown is S=98, T=4,880, H=1,637, and no-pair=8,385. No-pair outcomes are expected policy results, not correctness failures. Every successful token agreed with direct evaluation. The explicit regressions include the worked example, untransported implication failure, constant-function syntactic support, TAB/H ancestry, and nonunique derivability. [E1]

**Scope limitation:** these checks support the finite identities and the reference interpretation. They do not verify every production dependency, the general fallback builder, old benchmark outputs, Python runtime behavior on arbitrary depth, or any speedup. The manuscript's reported 116 tests and separately reported 1,048,576 checks remain author-reported historical evidence; matching the latter count in a fresh enumeration does not establish that the original checker was rerun.

# VIII. Compiler-contract and implementation audit

The inspected source largely supports the intended restricted compiler, but the following distinctions must become part of the publication contract.

| Contract component | Source behavior | Assessment |
|:--|:--|:--|
| Signed primitive recognition | Five connectives over signed literals; disjoint row/column variables | Match |
| Token transport | True-first token; transpose and input-polarity actions | Match |
| Same-frame fusion | Both variable names must match | Match |
| S/T/H | Root outcome depends on retained structural/tabulated ancestry | Substantive match; formal selection needs precision |
| Support | Syntactic variables minus fixed names | Manuscript ambiguous |
| Pure mode | No local retabulation | Match |
| Hybrid mode | Structural attempts before local retabulation | Match |
| Retabulation mode | Four evaluations of the whole eligible root | Match |
| Legacy `structural` mode | Alias for **hybrid**, recorded diagnostically | Must not be mistaken for pure mode |
| Failed root | Ordinary builder receives the original expression | Commitment boundary insufficiently explicit |
| Token-only failure | Returns no token and outcome metadata | Not itself a dense fallback execution |
| Dense output | All ambient R/C axes retained and materialized | Mismatch with unfixed-axis wording |
| Output ownership | Broadcast result copied into owned storage | Match |
| Exact historical revision | Not linked to every reported test/table | Not established |

## Retained output axes: a concrete contract mismatch

Take

$$e=(X\land Y)\lor Z,\qquad F=\{Z\mapsto0\},$$

and request row axes `[X,Z]` and column axes `[Y]`. The remaining function is $X\land Y$, and the successful pair token can be the AND token on $(X,Y)$. However, the dense wrapper calls `lift_cm` with the original row and column lists. That function reinserts absent axes as broadcast dimensions and copies to shape

$$2^{2}\times 2^{1}=4\times2,$$

so the returned array has **eight entries**, not the four entries of a projected table over the two unfixed variables. This is a direct source-derived example, not a claimed full-runtime reproduction. [C1, `compile_expr_to_cm_pair`; C3, `lift_cm`]

The current manuscript says "requested unfixed Boolean axes" in its artifact table and defines $n$ accordingly in the cost model. Repair it to distinguish retained ambient axes from free/essential variables. The least disruptive correction is documentation: define $m=|\mathcal R|+|\mathcal C|$ for the retained layout and state that this API returns $2^m$ entries even when some axes are fixed or semantically irrelevant. A projected-output API would also be legitimate, but it would be a code/contract change requiring new tests and appropriately versioned measurements. [M lines 434, 488-496]

## Root failure and speculative work

In the dense wrapper, an unsuccessful root token compilation calls the ordinary builder on the **original expression**. Successful pair children are not substituted into a retained transformed tree. For $(X\land Y)\lor Z$ with all three variables live, the left child can compile while the root cannot be represented by this one-pair path. The child's token work does not thereby become a committed optimization in the returned ordinary compilation. [C1]

The source's counters can record successful pair attempts made during such unsuccessful enclosing attempts. They must not be interpreted as counts of optimizations surviving into the returned program. Prefer two explicit concepts: attempted/locally constructed pair operations and committed contribution to the returned result. The ordinary builder may perform its own simplifications; this finding does not claim that fallback performs no optimization at all.

## Frames and ambient layouts

The formal judgment fixes a particular pair $(R,C)$, while the API receives lists of ambient row and column variables and discovers a pair inside them. State the bridge: a successful result selects one row name and one column name from the respective disjoint layouts, neither bound by $F$. The frame is an ordered pair of variable identifiers, not merely identical token values or equal matrix dimensions. General compound-operand frame theory is not implemented by this primitive recognizer.

## Caches and phase accounting

`cm_token.py` constructs composition lookup tables and caches `cm_compose`; `cm_normalize.py` caches layout metadata. A reproducible cold/warm protocol must state what is initialized outside the timer and which caches are cleared. This is a benchmark-definition issue, not evidence of an existing manipulated measurement. [C2-C3]

# IX. Novelty and prior-art report

## Closest claim-level antecedents

| Proposed element | Closest comparison | Residual differentiation |
|:--|:--|:--|
| Entrywise outer Boolean fusion | Cheng-Zhao-Xu, Proposition 3.3 | Not new as an algebraic identity |
| Compact truth-function operations | Kitty Boolean, swap, flip, support/extension operations | Explicit compiler frame/provenance contract, if demonstrated useful |
| Local function rewriting with input mappings | Cut-based AIG rewriting and NPN treatment | Smaller restricted compiler and explicit failure/provenance presentation |
| Canonical token in fixed frame | Truth-table uniqueness; broader canonical representations such as BDDs | Not general semantic normalization |
| Matrix/ket interpretation | Existing matrix/vector-logic literature, including Bricken | Exposition/integration rather than automatic priority |
| Rewrite correctness and fallback | Standard compiler proof and partial-evaluation patterns | Exact implemented policy and executable boundary cases |
| Repeated-query tradeoffs | Knowledge-compilation and prepared-representation distinctions | Must be evidenced for the actual endpoint |
| S/T/H reporting | Derivation/strategy provenance for this implementation | Possible methodological utility; exact priority unresolved |

Cheng, Zhao, and Xu explicitly give the same-variable truth-vector identity underlying pointwise outer Boolean combination. Their paper also defines XOR-AND Boolean matrix multiplication. The revised manuscript already acknowledges this direct antecedent, which is correct scholarly positioning. It should keep treating Theorem 1 as a compiler legality lemma rather than an independent algebraic discovery. [L1, Proposition 3.3 and Definition 2.7]

The official Kitty interface supplies truth-table Boolean operations, variable swapping/flipping, dependence tests, cofactors, and expansion to larger bases. This makes it a particularly useful concrete comparison for the paper's low-level operations. It does not prove that Kitty contains the same S/T/H compiler policy, but it prevents those primitive operations or basic variable bookkeeping from carrying the novelty burden. [L2]

The AIG rewriting literature supplies a more demanding comparator for any circuit-optimization claim: local cut functions, input/output transformations, sharing-aware replacement, and an explicit distinction between a candidate rewrite and a committed graph change. The present pair compiler is not identical to that algorithm; the relevant question is what its restricted formulation teaches beyond established local-function rewriting. [L3; L4]

## Novelty confidence

**High confidence:** raw truth-table representation, pointwise fusion, signed input transformation, and fixed-frame token uniqueness are not the new research contribution.

**Moderate confidence:** the package has a coherent, explicit compiler-contract presentation that may be useful pedagogically and as a research artifact. The combination of provenance distinctions, failure examples, and honest endpoint accounting is worth preserving.

**Low to moderate confidence:** that presentation currently establishes enough distinctive methodology for a standalone serious research article. A fresh search did not establish first priority for the exact combined S/T/H formulation, and no inference from "not located" to "new" is warranted.

**Unresolved:** whether an execution-backed, contract-focused comparison will reveal a reusable benefit in reliability, diagnosis, integration, or performance that ordinary local truth-table implementations do not already make apparent.

## Adversarial test of the contribution

A generic local truth-function optimizer can implement the same four-bit Boolean operation. The paper's own reported generic tie supports that boundary rather than undermining its honesty. The typed frame is a real correctness requirement, but real requirements can be standard engineering rather than novel research. The S/T/H labels are useful only to the extent that they diagnose distinct execution paths or scientific questions, not simply because three names have been introduced.

A skeptical compiler reviewer could learn something reusable from an executable contract suite covering frame alignment, fixed-axis output, attempted versus committed folds, and unfair endpoint comparisons. At present, that reusable artifact is not closed in the supplied package. This is the most promising way to strengthen the claim without inventing a deeper Boolean algebra.

## Recommended contribution wording

> We specify and evaluate a restricted, frame-carrying compiler for binary truth-function subexpressions. The Boolean table operations are classical; our focus is the explicit legality, strategy-provenance, fallback, and output contracts, together with the conditions under which these operations do or do not yield an implementation benefit.

Use this only with the evaluation actually completed, and do not imply that merely formalizing familiar metadata establishes first priority.

## Citation correction

The manuscript's Mishchenko-Chatterjee-Brayton DAC 2006 entry lists pages 532-536. The primary publication record gives **532-535**. This is a minor bibliographic repair, not a scientific defect. Bricken's internally dated document should continue to carry the manuscript's caveat that an internal 1997 date is not independently established public-release priority. [L3; L7]

# X. Experimental evidence and methodology

## Evidence already reported

The following are the manuscript's reported results, checked for internal interpretation and consistency, **not regenerated from raw data in this audit**. [M Section 8]

S1/S2 contains 10,500 generated cases, of which 10,389 completed in all four arms: 3,750 S1 and 6,639 S2. The remaining 111 are retained in the population accounting rather than simply disappearing. CM and generic local optimization agree on seven principal symbolic-output metrics in the admitted comparison. The generic arm records more folds in 6,010 cases and CM more in zero; fold counts are not wall-clock performance. The defensible conclusion is a local pre-expansion mechanism that is not representation-exclusive.

P14-PY0 is recipe-to-owned-ANF compilation, not the pair-token primary endpoint. The manuscript reports 491 frozen cases, 51,102 measured rows, and three sequential workers. Its displayed E/D geometric means are 1.0508 on synthetic cases and 1.0607 on natural cases: with lower ratios better, the exact dispatcher is about 5.08% and 6.07% slower than direct compilation in those aggregate comparisons. The specified success gate failed. Selected synthetic wins do not overturn that conclusion.

These data are scientifically useful if the underlying record is traceable. They cannot be promoted into evidence that the newly specified pair-token compiler beats a direct packed evaluator. Nor should performance across different endpoints, different preparation regimes, or later CM-family backends be pooled into one headline.

## Unexecuted confirmatory protocol

The current manuscript explicitly says protocol v3 is unexecuted. No executed campaign matching that designated primary cell was established from the supplied archive and inspected source material. This is a statement about available evidence, not proof that no additional private results exist elsewhere.

The current primary cell is already well specified: signed/permuted pure-structural balanced formulas, $N=1023$, $U=N$, no fixed variables, token output, one use, and a direct packed AST comparator. It should not be silently replaced after results are seen. Any revision to the protocol should be versioned and its reason recorded before confirmatory measurement. [M lines 556-560, 617]

## Is the confirmatory experiment a publication blocker?

**Not for every possible paper identity; yes for a demonstrated-performance identity.** A rigorous methods/specification or negative-results article need not obtain a positive speedup. However, the current combination of elementary formal results and inherited different-endpoint data does not yet establish a compelling standalone contribution merely by disclaiming performance. Repositioning requires a genuinely useful executable method, well-documented failure taxonomy, or directly relevant negative comparative result.

My recommendation is to complete a focused, task-matched study rather than add more unrelated mathematics. A valid negative result can support the narrowed paper. A successful performance threshold is not a universal requirement for publication, and choosing a new endpoint after a failed threshold would weaken the research.

## Smallest scientifically meaningful next study

Preserve the declared primary token endpoint and its comparator. Execute the pure, hybrid, and root-retabulation variants on distinct expression families; record support discovery, structural attempts, retabulation, fallback, and complete preparation costs. Ensure the comparator produces the same token/frame order and pays for equivalent support discovery. Include the declared primary case rather than substituting an easier one.

Add a modest natural-input admission survey before committing to a huge speed campaign. Count eligible roots and failed roots, not just favorable constructed subexpressions; distinguish candidate child folds from contributions retained by the current root-only wrapper. For sharing experiments, use both identity-shared DAGs and separately allocated equal trees, and compare against sharing-aware evaluation.

Use formula/case families as the independent units of inference. Timing repetitions estimate measurement noise; they are not new workloads. Predeclare aggregation, uncertainty estimation, exclusions, and success/failure handling. Select a sufficient case count from pilot variability rather than an arbitrary large number. Archive the pilot separately from confirmation. Report negative and zero-admission results.

The primary 20% speed criterion and 10% memory allowance are engineering decision thresholds, not mathematical necessities. Explain their rationale. Do not interpret failure to cross them as failure of semantic soundness.

## Reuse and break-even reasoning

For different query costs, a prepared method wins when

$$C_{\mathrm{prep,new}}+qC_{\mathrm{query,new}}
<C_{\mathrm{prep,base}}+qC_{\mathrm{query,base}}.$$

If both methods produce the same four-bit token and call the same query routine, their query cost is the same $L$:

$$T_{\mathrm{new}}(q)=C_{\mathrm{new}}+qL,\qquad
T_{\mathrm{base}}(q)=C_{\mathrm{base}}+qL.$$

The preparation-time ordering cannot reverse merely by increasing $q$; the difference remains $C_{\mathrm{new}}-C_{\mathrm{base}}$. The draft already recognizes shared lookup costs, so this is a useful explicit clarification, not a newly discovered false speedup claim. A reuse advantage requires a genuine difference in the work retained or performed per query.

# XI. Reproducibility assessment

## What is reproducible now

The current manuscript can be built. Its supplied and rebuilt PDFs agree in normalized page text. The current manifest can be verified. The audit's independent finite checks can be rerun from the included script and produce a machine-readable result. Relevant current public implementation functions can be located at an immutable commit. These are substantial positive facts. [E1-E3; C1-C3]

## What is not yet closed

The package does not supply a self-contained, exact implementation snapshot tied to all manuscript claims, complete historical test logs and commands, raw S1/S2 and P14 records with regeneration scripts for the current tables, or a complete executable frozen confirmatory package. Some supporting files refer to separate supplements or external directories. Such supplements may exist, but their existence and consistency cannot be inferred from a link label alone.

The historical manuscript checker exits with a missing-protocol requirement. Current source availability does not make that old packaging defect disappear, and the historical defect does not imply the current manuscript cannot compile. These are separate tests with separate outcomes.

## Minimum artifact closure

Create one versioned release manifest that binds manuscript source/PDF, implementation revision, dependency lock, exact commands, test logs, benchmark generators, seeds, raw results, analysis scripts, table outputs, and documented machine/environment information. Include an explicit map from each empirical table to its generating command and data. Separate completed studies from unexecuted plans and historical superseded data.

Supply a clean-run command for correctness and a separate command for analysis regeneration. Timing runs should have an honest resource/time estimate. Document optional dependencies and cache policy. A manifest must cover the necessary artifacts, not merely all files that happened to be copied into the ZIP.

License and third-party benchmark redistribution status should be checked at release time; this audit does not assert that a licensing violation exists. Similarly, any journal-specific disclosure requirements should be checked against the selected venue rather than guessed.

**Artifact gate: NOT YET REPRODUCIBLE as a complete paper package.** A more precise public statement is: manuscript build and independent local mathematics reproducible; historical author tests/statistics not independently reproduced here; full confirmatory experiment not executed in the available record.

# XII. Reviewer-feedback resolution matrix

The matrix consolidates substantive issue families across R1, R2, the responses, the September 22 panel, and historical adversarial/reproducibility records. Duplicate copies of a report are counted once. Historical requests about deleted companion-paper material are not silently treated as unresolved compiler defects. [R1-R6]

| Prior issue family | Current status | Evidence / remaining action |
|:--|:--|:--|
| Scalar transpose used where operator transport is required | RESOLVED | Current Section 3 transposes the operator |
| XOR-AND versus ordinary arithmetic unclear | RESOLVED | Current contraction convention is explicit |
| Hybrid derivations hidden inside structural mode | MOSTLY RESOLVED | S/T/H and modes exist; strategy relation still needs precision |
| Provenance R conflicts with row R | RESOLVED | Provenance now T |
| Primitive and TAB rules insufficiently explicit | MOSTLY RESOLVED | Displayed rules added; TAB selection premise remains informal |
| Equations for NOT/fusion difficult to read | RESOLVED | Plain-language explanations and worked example added |
| Missing structural-fragment guarantee | RESOLVED | Theorem 3 states limited syntactic completeness |
| Completeness overstated semantically | OBJECTION NOT VALID against current wording | Current text expressly limits the claim |
| Incorrect or missing worked derivation | RESOLVED | Tokens independently checked |
| Generic local optimizer missing from interpretation | RESOLVED | Generic tie explicitly limits CM-specific claim |
| Direct packed baseline needed | RESOLVED at protocol level | Execution and artifact closure remain outstanding |
| Multiple moving primary endpoints | RESOLVED at text level | One primary cell now declared |
| Sharing confounded with representation | MOSTLY RESOLVED | N/U and sharing cases specified; completed matched study absent |
| Excessive skew depth / runtime recursion risk | MOSTLY RESOLVED | Protocol caps skewed cases; no universal runtime guarantee |
| True-first versus dense-array order mismatch | RESOLVED for conversion | Explicit conversion agrees with code |
| Broadcast view writable ownership | RESOLVED in inspected source | `lift_cm` returns a copy |
| Reported old counters mistaken for AST counts | MOSTLY RESOLVED | Source documents legacy counters; commitment still needs distinction |
| Cache/cold/warm policy complete | CANNOT VERIFY as frozen experiment | Caches exist; exact executable protocol is not in package |
| Exact source/test/data archive required | UNRESOLVED | Public current code does not bind historical runs |
| Pair confirmatory results required for performance claims | UNRESOLVED | Current text honestly reports nonexecution |
| Positive speedup required for any publishable paper | OBJECTION TOO STRONG | Depends on contribution identity and evidentiary quality |
| Deeper LM/STP/phase material required here | OUT OF CURRENT SCOPE | Split removes it; not necessary for restricted compiler proof |
| Natural workload prevalence and practical significance | UNRESOLVED | Admission survey/direct evidence still needed |
| Closest prior-art comparison rather than broad citations | PARTIALLY RESOLVED | Good prose exists; implementation-level matrix still needed |
| Threshold rationale and clean freeze | PARTIALLY RESOLVED | Thresholds explicit; rationale/complete artifact absent |

The fresh audit adds particular emphasis to **retained fixed axes**, **root commitment versus speculative fold counters**, and the precise distinction between **admissible derivations and deterministic outcomes**. Old favorable reviews do not settle these issues. Conversely, old unfavorable comments about absent explanations should not survive after the current draft has actually added them.

# XIII. Fresh simulated referee reports

## Referee A: mathematical correctness

**Strongest aspect:** a small and auditable semantic core. One-hot selection and frame transport make the soundness argument transparent; the syntactic completeness theorem is appropriately bounded.

**Principal concern:** the formal relation sometimes reads as both a proof system and an operational compiler trace. Multiple admissible derivations are harmless semantically but incompatible with an unqualified unique selected provenance. Syntactic support and the ambient-layout contract should be explicit.

**Required changes:** separate strategy selection; clarify support and returned axes; preserve the limited theorem statements; add explicit boundary examples. No additional phase/LM theory is needed.

**Recommendation:** major clarification before submission; no demonstrated counterexample to the core algebra.

## Referee B: compilers and logic synthesis

**Strongest aspect:** the attempt to make legality, provenance, and fallback explicit rather than advertise a four-bit operation as a general compiler advance.

**Principal concern:** ordinary truth-table and cut-based optimizers already manage function-input correspondence. Why does this particular restricted compiler warrant a research paper, rather than documentation of a small implementation? Root-only commitment also limits what natural-program optimization claims can mean.

**Required changes:** close comparison with a direct packed evaluator and generic local-function implementation; a concrete reusable contract/failure contribution; accurate root-fallback and output behavior.

**Recommendation:** major revision. Hold any systems-performance positioning until matched evidence exists.

## Referee C: experimental methodology

**Strongest aspect:** the manuscript reports the generic tie and negative dispatcher result rather than selecting only favorable examples. It names a primary pair endpoint and distinguishes preparation from queries.

**Principal concern:** completed evidence does not answer the designated pair-compiler question, and raw historical statistics were not available for reproduction in this package. Large numbers of timing rows do not establish independent case diversity.

**Required changes:** versioned frozen protocol, case-level analysis plan, complete cost accounting, direct comparison, natural admission counts, and recoverable raw-to-table pipeline.

**Recommendation:** not ready as an experimental compiler paper; a valid negative direct study could be sufficient evidence for a narrower contribution.

## Referee D: prior art and novelty

**Strongest aspect:** the draft already acknowledges the direct algebraic antecedent and several relevant implementation traditions.

**Principal concern:** "classical ingredients, new packaging" needs more than an assertion that the packaging has a name. Exact priority of the combined provenance formulation remains unresolved, and novelty of basic frame bookkeeping should not be assumed.

**Required changes:** feature-level comparison, restrained contribution wording, and one demonstrable insight or reusable artifact that survives the generic-optimizer comparison.

**Recommendation:** major revision; no basis for either absolute novelty or a categorical claim that nothing useful remains.

## Referee E: research software and reproducibility

**Strongest aspect:** the current manuscript builds, integrity checks pass, and current implementation paths are publicly inspectable at a pinned commit.

**Principal concern:** manuscript, reported isolated test run, historical experiments, and supplementary artifact paths are not bound into one reproducible release. The historical checker exposes this fragmentation.

**Required changes:** release manifest, exact environment/commands, logs, raw data, analysis scripts, clean-run verification, and clear historical/current separation.

**Recommendation:** artifact gate not passed. Packaging is partly a retrieval/release task, but empirical regeneration must actually succeed before claiming reproducibility.

## Referee F: editor

**Strongest aspect:** a coherent 14-page post-split draft with good examples and honest limitations. It is more mature than a speculative broad CM manifesto.

**Principal concern:** the strongest identity is not yet fully supported: too elementary for a strong standalone mathematics claim, not yet evaluated for a performance claim, and not yet packaged as a mature reusable software contribution.

**Required changes:** choose the methods/contract identity; correct the implementation boundaries; complete the smallest relevant comparative study and artifact; shorten peripheral historical endpoint discussion.

**Recommendation:** major revision before serious submission; a corrected preprint can be justified earlier.

## Synthesis

The perspectives agree on sound elementary mathematics and insufficient submission closure. Their priorities differ: formal precision for A, residual utility for B/D, direct evidence for C, reproducibility for E, and coherent identity for F. No artificial disagreement is needed. None requires a positive timing result as an unconditional publication criterion; all require an honest, substantial contribution with evidence appropriate to its claims.

# XIV. Completeness, scope, and exposition

Mathematical completeness is mostly adequate for the restricted fragment. The missing pieces are definitions and correspondence between levels, not an absent deep theorem. Add the strategy relation, syntactic-support definition, and ambient-frame bridge before increasing theoretical scope.

Compiler completeness needs a single operational decision table: what is recognized, which mode permits TAB, what is returned on success, what is returned on token-only failure, when the dense fallback builder is called, which attempted work is discarded, and what output axes remain. Include constants represented through redundant formulas and fixed-variable reductions even though the grammar has no primitive constant node.

Experimental completeness remains weaker. The paper asks a performance question whose designated primary test has not been performed in the available record. Older evidence can motivate that test or delimit claims, but cannot answer it by analogy.

Scholarly completeness should focus on close implementation comparisons. The related-work section is not empty or careless; broad additions alone will not solve the remaining novelty question. A short feature matrix covering frame mapping, truth-table composition, structural recognition, retabulation policy, provenance, committed rewrites, and endpoint/cost accounting would be more useful.

The foundations/compiler split should remain. Keep the one-hot contract, signed transport, and restricted rules needed here. Move detailed phase/rotation/modal work elsewhere. General CM/LM coherence results are companion-paper material unless a particular lemma is necessary to understand this algorithm.

The paper should remain **one paper** at its present compiler scope. Splitting a small algebraic kernel, a proof of its compiler use, and its immediate evaluation into separate thin papers would reduce coherence. A genuinely separate broad backend-comparison campaign can be a different paper because it asks different endpoint questions.

Editorially, the abstract already gives an unusually candid evidence boundary. Improve it by stating the contribution identity positively before listing limitations. Preserve the worked implication example. Shorten the catalogue of later project-wide benchmark ratios unless each is needed to prevent a specific confusion. A title such as **"Frame-Typed Local Truth-Function Compilation: Correctness Contracts and Empirical Boundaries"** is worth considering if the narrowed identity is adopted; the existing CM title is also defensible if its classical components are clear.

# XV. Prioritized findings and blockers

The findings below are distinct root causes, not every sentence-level instance. No P0 central mathematical invalidity was established. P1 items are major revisions; some must be corrected even before preprint release.

## P1-01. Dense output contract counts the wrong axes

**Location:** M artifact table and cost model, lines 434 and 488-496; C1 dense wrapper; C3 `lift_cm`.

**Problem:** the paper describes unfixed axes, but the inspected API retains ambient axes and broadcasts fixed/irrelevant ones. Logical bits are also not a complete physical allocation description.

**Required repair:** define retained ambient layout size and specify projected versus broadcast output. The existing implementation can be documented without changing its mathematics. Add the fixed-Z example and an output-shape regression. Do not use semantically essential variable count as the current allocation bound.

**Work type:** wording/specification essential; a regression test essential; code changes only if a new projected API is chosen. No new theorem required.

**Verification:** both pair success and fallback return the documented shape under fixed and irrelevant axes; reported memory uses actual representation bytes.

## P1-02. Derivability, strategy provenance, and support are conflated

**Location:** M lines 258-328, 361-407; C1 strategy dispatch and `_pairable_vars`.

**Problem:** unguarded judgments admit multiple provenance derivations; pure-mode failure does not imply no derivation in the unrestricted relation; `supp` is not explicitly syntactic.

**Required repair:** add a strategy-indexed operational contract and a syntactic-support definition. Explain that token uniqueness is not provenance uniqueness. Bridge fixed pair variables to ambient layout lists.

**Work type:** formal specification and short proof correspondence; no new mathematical research or performance experiment required; add mode/edge-case tests.

**Verification:** trace `X AND Y` and `X OR (Y AND Y)` under all modes, including TAB admissible but pure mode failing.

## P1-03. Exact implementation and historical test assurance are not release-bound

**Location:** M lines 567-569; reproducibility pointers and source lineage.

**Problem:** available public source does not by itself identify the code/environment that generated the 116-test report or every historical claim.

**Required repair:** archive the intended implementation commit, dependency lock, test commands, full logs, and input hashes. State explicitly which checks were rerun on the release candidate.

**Work type:** artifact recovery/packaging and actual test execution. Wording alone can limit a preprint claim but cannot establish reproducibility.

**Verification:** a clean environment reproduces the correctness suite without relying on the author's unrecorded local state.

## P1-04. Historical empirical claims lack a closed raw-to-table path

**Location:** M Section 8; retained P14/S1 reports and external supplement references.

**Problem:** the current archive does not enable independent regeneration of the reported S1/S2 counts, P14 aggregation, intervals, and table outputs.

**Required repair:** supply exact raw records, inclusion/exclusion rules, analysis scripts, seeds, and regenerated table outputs. Recovering existing raw evidence may be enough; do not automatically rerun expensive timing campaigns before checking that.

**Work type:** data recovery and analysis regeneration; new timing only if necessary. No new theorem.

**Verification:** all headline counts and displayed intervals regenerate from the declared inputs, including incomplete-case accounting.

## P1-05. Residual standalone differentiation is not yet established

**Location:** M contributions, related work, and discussion.

**Problem:** the paper correctly concedes classical primitives but does not yet demonstrate a substantial advantage or reusable insight in the residual compiler formulation.

**Required repair:** compare exact implemented features against close truth-table/cut methods; identify an execution-backed contract/failure/diagnostic contribution or task-matched performance boundary. Narrow first/novel claims where priority is unresolved.

**Work type:** focused prior-art comparison, demonstrator/artifact work, and positioning. Wording is necessary but not sufficient if nothing substantive remains.

**Verification:** a skeptical reader can state what reusable knowledge or capability the paper adds without crediting it for ordinary truth-table operations.

## P1-06. The designated pair-compiler scientific question is not yet answered

**Location:** M Sections 7-10, especially line 617.

**Problem:** no completed study matching the declared primary pair endpoint is established. Different-endpoint positive or negative results cannot substitute.

**Required repair:** execute the focused matched study, or justify a different methods/negative-results identity with its own completed evidence. A positive speedup is not required; a clear answer and usable contribution are.

**Work type:** new experiment is the recommended path; no automatic requirement for a huge campaign or deeper unrelated theory. Purely editorial relabeling is insufficient.

**Verification:** versioned protocol, raw outputs, correctness gate, case-level uncertainty, and a conclusion that follows the prespecified endpoint even when unfavorable.

## P1-07. Root commitment and diagnostic counts need an explicit contract

**Location:** M architecture/fallback narrative; C1 `_compile_pair`, `_metric_summary`, and dense wrapper.

**Problem:** locally successful child work may be discarded at root failure or root retabulation. Attempt counters are not necessarily committed optimizations.

**Required repair:** state original-root fallback explicitly and distinguish attempted work from retained-result provenance. Add a root-failure example and meaningful commitment diagnostics where the paper analyzes folds.

**Work type:** documentation and regression tests; new metrics may require code. A new persistent child-rewriting pass would be a different algorithm, not a silent repair.

**Verification:** a three-live-variable root with a pairable child demonstrates ordinary fallback and no unsupported claim of committed pair rewriting.

## P2 important improvements

**P2-01:** specify initialization, cache clearing, cold/warm regimes, recognition/preparation/query phases, and the identical-lookup no-crossover observation.

**P2-02:** explain the primary speed/memory thresholds; define sampling units, uncertainty, incomplete cases, and pilot-versus-confirmatory separation in an executable freeze.

**P2-03:** publish a compact boundary suite covering signed chains, repeated variables, fixed and irrelevant axes, invalid/overlapping layouts, constant-valued formulas, shared versus unshared ASTs, root failure, ownership, and historical mode aliases.

**P2-04:** tighten scope by shortening different-endpoint backend history and retaining only context needed for the present scientific question.

## P3 editorial and packaging improvements

**P3-01:** correct the DAC 2006 page range to 532-535 and verify final bibliography metadata.

**P3-02:** polish minor underfull table/reference layout and final draft metadata. No serious displayed-mathematics clipping was established in the inspected current renders.

**P3-03:** repair navigation and document historical relocation: 47 historical content matches and five unmatched entries, rather than presenting a naive missing-path count as missing science.

# XVI. Exact repair plan

## Before a public preprint

Correct the retained-axis/output-storage contract, define syntactic support, separate strategy outcomes from admissible derivations, and state root-failure commitment explicitly. These are focused repairs, not a request to redesign the project. Add the small illustrative cases given in this report and rerun the corresponding correctness tests.

Bind the preprint to an exact source revision and accurately label historical tests and statistics as reported unless their artifacts have been regenerated. Recover the essential supporting tables/logs where possible. If a result cannot be backed by recoverable evidence, qualify or remove that empirical claim rather than imply independent validation. Preserve the explicit statement that the pair confirmatory study is unexecuted.

Do a final source/PDF consistency build and bibliography check. Retain the strongest restrained contribution statement from Section V. These conditions are the basis for the preprint GO-after-corrections decision.

## Before serious peer-reviewed submission

Close the full release artifact and raw-to-table pipeline. Complete the focused direct pair study or an equally substantial methods/artifact demonstration appropriate to the chosen identity. Add the closest-comparator matrix and natural admission survey. Ensure that outcomes, including null or negative results, govern the conclusion.

Freeze the revised manuscript, source, protocol, and artifact together. Recheck P1-01 through P1-07 against the frozen revision rather than marking them resolved from an author response alone. The release gate should record actual commands and results.

## Strong but optional improvements

A broader production-circuit campaign, additional backends, automated proof-assistant formalization, a general compound-operand compiler, or a persistent local rewrite pass could be valuable. None should be added merely to make the paper appear deeper. Each changes scope and may create a separate research question. They should not indefinitely delay a focused, honest methods paper whose necessary evidence has been completed.

# XVII. Public preprint decision

**GO AFTER SPECIFIED CORRECTIONS.**

A corrected preprint can legitimately present a precise restricted compiler, its soundness theorem, its limited structural completeness result, the classical antecedents, and the currently established empirical boundaries. It need not pretend that a preprint requires a favorable timing result.

The current draft should not be released unchanged as an exact implementation contract because of the retained-axis mismatch and strategy/fallback ambiguity. Historical evidence should remain clearly labeled and traceable. If essential empirical support cannot be recovered, a more explicitly preliminary specification preprint is preferable to a false reproducibility claim.

The minimum gate is not "add more theory." It is **make the formal object, the implemented object, and the evidence status agree**.

# XVIII. Peer-reviewed submission decision

**MAJOR REVISION BEFORE SUBMISSION.**

This recommendation applies to a narrowed compiler-method/specification paper. The current version is not ready as a demonstrated-performance paper; that positioning is on hold until directly relevant evidence exists. A serious mathematical venue would also ask for more nontrivial mathematical content than the elementary local identities presently supply, so repositioning toward methods is more natural than inflating theorem rhetoric.

To advance to minor revision, the project should have: a consistent operational/output contract; a clean implementation/test/data release; a completed matched comparative result or a demonstrably substantial reusable-method artifact; and a feature-level account of residual differentiation. The result may be negative. What matters is that the contribution and evidence are sufficient for the identity selected.

No acceptance probability is assigned. This audit identifies scientific pressure points, not a prediction about an editorial decision.

# XIX. Venue positioning

A **compiler-methods or symbolic-computation methods venue** is the best conceptual direction if the main result is a precise executable contract, comparative implementation study, and diagnostic failure taxonomy. Such a paper must teach a reusable method beyond this project's nomenclature.

A **logic-synthesis/EDA venue** becomes plausible only when the paper addresses actual circuit or local-cut workloads and demonstrates why the restricted path matters relative to established rewriting practice. ACM TODAES is an example of the disciplinary category to investigate, not a vetted immediate submission recommendation: its current scope page could not be retrieved in this audit, and current venue requirements should be checked before selection.

A **research-software paper** is a different possible outcome if the implementation becomes a documented, tested, reusable tool with a clear research need. JOSS's official review criteria emphasize the software and its scholarly functionality, documentation, tests, and licensing; it should not be treated as an automatic fallback for a weak theoretical or performance paper. The present 14-page manuscript is not, merely by renaming it, a JOSS-style software submission. [L8]

A **workshop, technical report, or appropriately scoped negative-results/methodology outlet** may suit an initial contract-and-boundary contribution. This is not an excuse to lower correctness or reproducibility standards. It changes the expected scale of the contribution, not the meaning of evidence.

Select a concrete venue after the focused direct study and artifact closure. Broad top-tier performance positioning is currently premature; a strong reusable-method identity is the more defensible path.

# XX. Final publication-readiness statement

**What is correct and worth preserving:** the one-hot Boolean contract; signed/swapped frame transport; same-frame fusion as a classical legality fact; structural soundness; the honestly limited syntactic completeness theorem; exact local tabulation; the worked example; and the unusually candid separation of mechanism evidence, generic parity, negative dispatcher evidence, and unexecuted confirmation.

**What remains insufficiently established:** the exact operational/output contract at all boundaries; full manuscript-source-test-data reproducibility; a distinctive standalone compiler contribution beyond familiar truth-function manipulation; and a direct answer to the designated pair-compiler empirical question.

If submitted tomorrow, a rigorous review would most usefully press on four questions: **What is new beyond ordinary local truth-table compilation? Does the stated contract match the code, including fixed axes and failed roots? Can the reported evidence be regenerated? What completed experiment or reusable method establishes the importance of this particular formulation?** Those are more important than adding another elementary lemma or polishing already readable prose.

The highest-value next action is a focused release gate: repair the contract, pin and test the implementation, recover the raw-to-table evidence, and complete one honestly matched pair study. Keep the paper narrow. A carefully supported negative or parity result can be valuable; a broad claimed advantage inferred from unrelated endpoints cannot.

# Source and evidence locator key

This key makes the audit portable outside this conversation. Local source lines refer to the exact current TeX hash in Section III. Source labels identify evidence, not an endorsement of every statement in that source.

## Supplied archive

**M:** `01_CURRENT_REVISED_COMPILER_AND_REVIEW_20260922/Operator_Level_CM_Compiler_Revised_Draft.tex` and same-name PDF, 14 pages. Important ranges: definitions 113-167; transforms/fusion 169-242; rules and proofs 244-414; architecture/cost 416-499; related work 501-522; protocol/evidence 524-619; discussion/conclusion/appendix thereafter.

**R1/R2:** `Computational_Paper_Review_Panel_R1.md` and `Computational_Paper_Review_Panel_R2.md` in the current-revision directory. Historical copies are duplicates, not additional reviews.

**R3:** `Computational_Paper_Response_to_R2.md`.

**R4:** `CM_Compiler_Panel_Audit_2026-09-22.md`, `Operator_Level_CM_Compiler_Revision_Memo.md`, and `REVISION_NOTES_AFTER_RULES_UPDATE_2026-09-22.md`.

**R5:** `HISTORY/PORTFOLIO_PREDECESSOR_20260921/research_and_review/`, especially `ADVERSARIAL_REVIEW.md`, `REPRODUCIBILITY.md`, `FINAL_CLAIMS.md`, `GATE_6_EMPIRICAL_DECISION.md`, and the proof/source and priority ledgers.

**R6:** `RESEARCH_VIABILITY_REVIEW_2026-09-26/RESEARCH_ASSESSMENT.md` and `DECISION.json`.

## Pinned implementation

All three files are in `Relative0/Correspondence_Matrices`, commit `0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`, accessed on 26 September 2026. Source inspection was live through the GitHub connector; this audit does not claim that the full repository was installed or executed.

**C1:** [cm_build_pair.py](https://github.com/Relative0/Correspondence_Matrices/blob/0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b/cm_build_pair.py). Blob `4379a4661d9989cbaf65707f1349fd429fdda434`. Relevant functions: `_expr_stats`, `_signed_operator_pair`, `_pairable_vars`, `_compile_pair`, `_metric_summary`, `compile_expr_to_cm_pair_token`, `compile_expr_to_cm_pair`.

**C2:** [cm_token.py](https://github.com/Relative0/Correspondence_Matrices/blob/0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b/cm_token.py). Blob `391e9249e288c219f29173f92e3b8cb5cefb7d98`. Token lookup, signed alignment, complement, lookup tables, and cached composition.

**C3:** [cm_normalize.py](https://github.com/Relative0/Correspondence_Matrices/blob/0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b/cm_normalize.py). Blob `ad1ab1c6b0846f1ffb4955df50644c84158c00c9`. `lift_cm`, ownership, ambient broadcasting, and layout caches.

## Audit-generated evidence

**E1:** `verification/independent_finite_checks.py` and `independent_finite_results.json`. Script SHA-256: `70028e689049562ee78bc5efe1a074ef1abe7fbb59832f1ac4a157d3d76473ae`.

**E2:** `evidence/archive_inventory.json`, `text_file_index.json`, and `review_manifest_checks.json`.

**E3:** `evidence/build_comparison.json`; current build logs retained under `build/` in the evidence bundle.

**E4:** `verification/historical_checker_run.txt`.

**E5:** `evidence/historical_manifest_reconciliation.json`.

## Primary external sources

**L1:** D. Cheng, Y. Zhao, X. Xu, "Matrix Approach to Boolean Calculus," 2011 IEEE CDC-ECC, pp. 6950-6955. [Conference paper](https://skoge.folk.ntnu.no/prost/proceedings/cdc-ecc-2011/data/papers/0224.pdf). In particular Definition 2.7 and Proposition 3.3. Parsed text inspected; web screenshot rendering of the relevant page failed.

**L2:** Kitty official documentation, [Operations](https://libkitty.readthedocs.io/en/stable/operations.html). Consulted for concrete truth-table operations, variable transport, support queries, and base expansion, not for a claim that it implements this exact provenance policy.

**L3:** A. Mishchenko, S. Chatterjee, R. Brayton, "DAG-aware AIG rewriting: a fresh look at combinational logic synthesis," DAC 2006, pp. 532-535, DOI 10.1145/1146909.1147048. [Author-hosted paper](https://people.eecs.berkeley.edu/~alanmi/publications/2006/dac06_rwr.pdf). Relevant algorithm page visually inspected.

**L4:** mockturtle official documentation, [Cut enumeration](https://mockturtle.readthedocs.io/en/latest/algorithms/cut_enumeration.html). Concrete implementation context for local functions and cut-based methods.

**L5:** M. Willsey et al., "egg: Fast and Extensible Equality Saturation," POPL 2021; [author preprint](https://arxiv.org/abs/2004.03082). Broader rewrite/representation context; not an automatically matched timing baseline.

**L6:** A. Darwiche and P. Marquis, "A Knowledge Compilation Map," JAIR 17 (2002), pp. 229-264; [author preprint](https://arxiv.org/abs/1106.1819). Query/representation tradeoff context, not a direct two-variable compiler antecedent.

**L7:** W. Bricken, [matrix-technique document](https://wbricken.com/pdfs/01bm/01math/03math-supporting/math-tangential/04matrix-tech.pdf), internally dated March 1997. Public-release priority not established by the internal date. R. E. Bryant, ["Graph-Based Algorithms for Boolean Function Manipulation"](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf), IEEE Transactions on Computers, 1986, provides broader canonical-representation context; it is not evidence of an identical S/T/H compiler.

**L8:** JOSS, [official review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html), accessed 26 September 2026. Venue requirements must be rechecked at actual submission.
