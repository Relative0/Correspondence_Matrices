# Post-split revision memo

## *Operator-Level Boolean Computation with Correspondence Matrices*

**Prepared:** 22 September 2026  
**Purpose:** paper-split audit, claim/evidence ledger, and rewrite plan supporting the accompanying initial manuscript draft.

---

## 1. Executive assessment of the post-split paper

The strongest paper now available is a **focused compiler/mechanism paper with a systems-methodology spine**. The mathematical foundations should no longer carry the paper. The companion manuscript, *Correspondence and Logical Matrices: A Boolean Operator Calculus*, now owns the formula-valued LM theory, valuation, logical pairing, higher-arity tensor/map constructions, and the broader coherence calculus. The computational manuscript can therefore become materially shorter and clearer.

The defensible computational thesis is:

> A binary CM is useful to the compiler as a compact four-bit operator token **only when it is paired with a typed operand frame**. The compiler recognizes signed/swapped two-operand occurrences, transports them into a common canonical frame, and fuses compatible tokens before evaluating or expanding the operands. It explicitly distinguishes pure structural folding, hybrid folding through locally retabulated descendants, whole-root retabulation, and ordinary fallback. This transformation is sound. It can reduce pre-expansion work, but current evidence does not show that the reduction is uniquely CM-specific or that the complete pair-compiler is end-to-end faster under its still-unexecuted confirmatory protocol.

This is stronger than preserving the old combined CM/LM manuscript. It makes the paper's claim falsifiable, gives the negative results a coherent role, and avoids competing with the foundations paper for ownership of the same mathematics.

### Recommended publication shape

A hybrid of **Option A (compiler paper)** and **Option B (optimization/mechanism paper)** is best supported by the evidence. The paper should also inherit selected methodological discipline from Option C: task-matched endpoints, direct packed baselines, preparation costs, reuse, sharing, fallback frequency, and explicit negative regions.

The current evidence supports:

- a formal and implementation-level story for typed frame normalization and fusion;
- evidence that local small-function folding can reduce work before ANF expansion;
- evidence that an equally capable generic local truth-function optimizer can reach the same reduced symbolic result;
- a completed negative dispatcher boundary showing that profitable local cases need not amortize selection overhead;
- a broader project-level pattern, visible in later current-source benchmarks, that direct BitSet/CSE-flat controls often remain strong and that wrapper/setup overhead can erase kernel gains.

The current evidence does **not** support:

- a universal CM speedup claim;
- a claim that pointwise truth-function combination is novel;
- a claim that the pair compiler beats direct packed evaluation end to end;
- a prevalence claim for structural fusion on representative natural workloads;
- a claim that later CM-family benchmark campaigns are measurements of the pair compiler. They use different tasks and endpoints and are therefore context, not protocol-v3 results.

---

## 2. Section-by-section split map

| Current manuscript material | Keep in computational paper | Summarize + cite foundations | Move entirely to foundations | Delete / demote | Rationale |
|---|:---:|:---:|:---:|:---:|---|
| Abstract | ✓ rewrite |  |  |  | Make compiler transformation, evidence hierarchy, and unexecuted protocol the center. |
| Introduction: operator view, compiler question, novelty boundary | ✓ | ✓ |  |  | Keep the computational motivation; cite companion for the full operator calculus. |
| CM definition, true-first convention, XOR–AND selection | ✓ brief | ✓ |  |  | Needed to make the compiler independently readable, but only as a minimal imported contract. |
| Coefficient-space linearity and basis expansion |  | ✓ | ✓ detail |  | Not needed for the compiler beyond a short warning that input-linearity is not implied. |
| XOR/XNOR rotation and Impax discussion |  | ✓ if mentioned | ✓ detail | ✓ main text | Interesting notation/structure, but not needed to establish compiler legality or performance. |
| Operand transforms: transpose, row/column reversal, output complement | ✓ | ✓ |  |  | Core normalization mechanism. |
| Same-frame pointwise fusion identity | ✓ | ✓ antecedence |  |  | Core compiler rule; explicitly not claimed as new mathematics. |
| Typed pair judgment and frame invariant | ✓ |  |  |  | Central formal contribution of computational paper. |
| Pure structural soundness | ✓ |  |  |  | Central correctness theorem. |
| Exact four-assignment retabulation | ✓ |  |  |  | Establishes explicit fallback inside two-variable support. |
| Hybrid provenance/soundness | ✓ |  |  |  | Important because earlier review found the hidden hybrid path. |
| Ordinary IR fallback contract | ✓ |  |  |  | Defines the compiler's safe boundary. |
| Five implementation artifacts | ✓ |  |  |  | Essential to prevent token/dense-output endpoint confusion. |
| Layout conversion / ownership / complexity | ✓ |  |  |  | Systems contribution and experimental fairness. |
| ANF/STP representation derivations |  | ✓ | ✓ mathematical detail | ✓ most main text | Retain only enough related-work explanation to distinguish endpoints. |
| Formula-valued LMs |  | ✓ one paragraph | ✓ |  | Companion paper now owns this material. |
| LM valuation and logical pairing |  | ✓ one sentence | ✓ |  | No role in timed compiler path. |
| Higher-arity LM/tensor theory |  | ✓ size boundary only | ✓ |  | Keep only the non-compression/output-size limitation if relevant. |
| Related work: Cheng/Zhao/Xu | ✓ |  |  |  | Direct prior art for pointwise truth-vector combination. |
| NPN/LUT/AIG, packed truth functions, CSE, ROBDD | ✓ strengthen |  |  |  | Closest operational antecedents/comparators. |
| Experimental protocol v3 | ✓ |  |  |  | Required to define what a performance claim would mean. |
| S1/S2 mechanism evidence | ✓ |  |  |  | Useful exploratory evidence if explicitly separated from speedup claims. |
| P14-PY0 dispatcher result | ✓ |  |  |  | Valuable negative systems boundary; endpoint is ANF lowering, not packed evaluation. |
| Later project-wide CM benchmark results | ✓ discussion only |  |  |  | Include only as task-matched context; do not relabel as pair-compiler evidence. |
| Full LM proof appendix |  |  | ✓ | ✓ | Duplicative after the split. |
| Compiler proof appendix | ✓ |  |  |  | Retain concise induction and retabulation proof. |
| Full higher-arity entry-count proof |  | ✓ sentence | ✓ | ✓ | A one-line exponential-output limitation is enough here. |

---

## 3. Correctness audit of the compiler transformation

### 3.1 Minimal semantic contract

For a binary connective variable `Theta` in a declared true-first frame,

```text
[Theta] = [[Theta_11, Theta_10],
           [Theta_01, Theta_00]].
```

For bits `x,y`, the XOR–AND one-hot contraction selects exactly the entry indexed by `(x,y)`. The compiler does not need the full LM theory to use this fact.

### 3.2 Frame typing is the legality condition

A four-bit token is insufficient by itself. A pair occurrence must carry at least:

- canonical row operand;
- canonical column operand;
- row polarity;
- column polarity;
- declared truth-state order.

Operand exchange is represented by transpose; signed input changes are row/column reversals; output negation complements token bits. These are sound because they merely reindex or complement the four assignments.

The example

```text
(X => Y) XOR (Y => X)
```

is a useful admission test. The second implication does not initially inhabit the `(X,Y)` frame. It must first be transported by transpose. Only then is entrywise XOR legal, yielding the XOR token. The value of this example is not the truth-table identity; it demonstrates why frame metadata is semantic information rather than incidental array layout.

### 3.3 Pair invariant

The useful compiler invariant is:

```text
E_t(r,c) = e[r/R, c/C]
```

for all `r,c in B`, after applying fixed substitutions, whenever the compiler returns `Pair(R,C,t)`.

This is sufficient to prove the four compiler outcomes separately.

### 3.4 Pure structural soundness

Induct on the derivation:

1. **Signed primitive:** correctness follows from transpose/row/column transforms.
2. **Negation:** complementing the token complements the represented function pointwise.
3. **Fusion:** if both children satisfy the invariant in the *same* `(R,C)` frame, applying the outer Boolean connective entrywise preserves the invariant.

No four-assignment retabulation is used on this path.

### 3.5 Exact retabulation

If the live support after fixed substitution is exactly two distinct canonical variables `(R,C)`, evaluating the subtree at `(1,1),(1,0),(0,1),(0,0)` produces the unique four-bit token satisfying the invariant. This is exact but computationally different from structural folding; it must therefore remain a distinct provenance class and experimental arm.

### 3.6 Hybrid soundness

A locally retabulated child is a sound base case. Subsequent structural negation or same-frame fusion preserves the invariant. The earlier hidden hybrid path is therefore mathematically acceptable **provided it is explicit in the implementation, theorem, diagnostics, and benchmark arm names**. The R2 response indicates this mismatch was repaired.

### 3.7 Fallback contract

If no pair judgment is derivable, the compiler leaves the expression on the ordinary IR path. Correctness of that branch is therefore conditional on the existing IR evaluator. This is a clean interface boundary and should be stated as such rather than folded into the pair theorem.

### 3.8 Important limitations

- Exact two-variable support is an **admission policy**, not a theorem that larger-support functions cannot be tabulated.
- Repeated-variable forms such as `X Theta X`, overlapping row/column layouts, different variable pairs, and opaque compound operands lie outside the current pure structural rule.
- A constant-time four-bit fusion is a kernel property. Recognition/traversal, support discovery, conversion, allocation, and output materialization remain part of end-to-end cost.
- The true-first compact-token layout and false-first dense-array layout must remain explicitly separated; their conversion is a reindexing, not a change of function.

---

## 4. Prior-art and novelty audit

The paper should make **no novelty claim for the raw truth-function operations**. The following ingredients are established or strongly antecedented:

- four-bit truth tables / LUTs;
- Boolean matrix representations of logic;
- XOR–AND Boolean matrix algebra;
- pointwise Boolean combination of aligned truth vectors (notably Cheng, Zhao, and Xu, 2011);
- 2x2 logical matrices and bra–matrix–ket evaluation in Bricken's internally dated 1997 note;
- input negation, permutation, output negation, and NPN equivalence;
- packed small-function manipulation;
- DAG-aware AIG rewriting and local-cut truth functions;
- CSE/hash-consing and bit-parallel evaluation;
- ROBDD canonical representation under a fixed variable order;
- generic local truth-function optimization.

The computational paper's candidate contribution is the **integration**:

1. a typed operand-frame certificate attached to the compact operator token;
2. an explicit normalization/admission procedure for signed/swapped occurrences;
3. a compositional pure/hybrid/retabulated/fallback compiler semantics;
4. provenance that exposes how a result was obtained;
5. an evaluation design that compares equivalent delivered artifacts and charges preparation, sharing, reuse, conversion, and fallback costs.

A generic local truth-function optimizer reaching the same reduction is not a failure of the mechanism. It means the reduction belongs to a broader local-function optimization family. The empirical question becomes whether the CM representation makes legality, transformation, caching, or reuse sufficiently cheap to matter in a complete system.

---

## 5. Claim and evidence ledger

### 5.1 Intended claim ledger

| Intended claim | Class | Current status | Recommended wording |
|---|---|---|---|
| A returned pure structural pair token denotes the source subtree in its canonical frame. | theorem / correctness | Supported by the typed induction. | State as theorem. |
| Four-assignment retabulation is exact for an admitted two-variable root/subtree. | theorem / correctness | Supported. | State as lemma. |
| Hybrid composition remains sound when retabulated descendants are explicitly tracked. | theorem / correctness | Supported after R2 repair. | State as theorem/corollary with provenance. |
| Non-pairable expressions safely fall back to ordinary IR. | correctness contract | Supported conditional on ordinary IR correctness. | State interface assumption explicitly. |
| The implementation separates token, pair surrogate, general IR, flat program, and dense output. | implementation | Supported by current manuscript/review record. | Keep artifact table. |
| Local folding can reduce pre-expansion symbolic work. | mechanism evidence | Supported in some S1/S2 strata. | Report with the generic-optimizer tie in the same paragraph. |
| CM folding is uniquely responsible for the S1/S2 reduction. | novelty / empirical | Not supported. | Do not claim. |
| Exact dispatcher beats direct ANF lowering overall. | end-to-end empirical | Refuted in P14-PY0. | Report negative result prominently. |
| Some selected folds are individually highly profitable. | negative-boundary detail | Supported on five synthetic P14-PY0 cases. | Report without promoting the aggregate conclusion. |
| Pair compiler beats direct packed evaluation. | end-to-end empirical | Unsupported; protocol v3 unexecuted. | Explicitly open. |
| Structural fusion is common on realistic natural workloads. | prevalence | Unsupported by current pair-compiler evidence. | Make a future/confirmatory question. |
| Later CM-family benchmarks prove the pair compiler is fast. | empirical | Invalid endpoint transfer. | Do not claim. Use later campaigns only as methodological/contextual evidence. |

### 5.2 Evidence ledger

| Empirical sentence / fact | Concrete basis available now | Status for initial draft |
|---|---|---|
| 116 focused tests passed on 19 Sep 2026. | Current computational manuscript and R2 response. Raw test package not attached in this chat. | May report as current implementation record; mark archival package as submission requirement. |
| 1,048,576 signed-alignment/fusion cases were exhaustively checked. | Current manuscript plus review/audit narrative. | May report as implementation assurance, not proof. |
| S1/S2: 10,500 generated; 10,389 all-arm completions; 3,750 S1 / 6,639 S2. | Current manuscript; prompt says canonical record exists but raw package is not attached here. | Report as existing exploratory record; do not imply fresh rerun. |
| S1/S2 CM and generic tie on seven main reduced-output metrics in all admitted all-arm cases. | Current manuscript. | Report as mechanism evidence and novelty boundary. |
| P14-PY0: 384 synthetic + 107 natural; 51,102 measured rows; equality passed all 491 frozen cases and 512 targeted cases. | Current manuscript. | Report as a separate completed frozen study. |
| P14-PY0 E/D geometric means 1.0508 synthetic and 1.0607 natural. | Current manuscript with intervals. | Keep negative conclusion and preregistered aggregation. |
| Corrected 25 Aug kernel study: bare CM/CSE-flat about 0.891 formula-balanced overall, narrowing to 0.961 at k=16; public wrapper slower. | Public project correction record, 25 Aug 2026. | Discussion context only; different endpoint from pair compiler. |
| Current-source 3 Sep complete-relation comparison: packed CM arm did not beat current direct BitSet; BitSet won all 78 runnable clusters. | Public architecture refresh record, independently verified. | Discussion/context only; reinforces direct-packed comparator choice. |
| 3–4 Sep q-ladder: CSE-flat best fixed arm at q64 on two host/compiler configurations; native path had unfavorable minimums. | Public architecture refresh record. | Discussion/context only; different repeated-restriction contract. |
| Protocol v3 pair-compiler confirmatory campaign. | Protocol exists; current manuscript explicitly says unexecuted. | Must remain unexecuted/open in draft. |

### 5.3 Evidence-level rule

The paper should visually and verbally separate:

1. **proof / finite correctness assurance**;
2. **exploratory mechanism evidence**;
3. **completed end-to-end result on a different ANF-dispatch endpoint**;
4. **separate project-wide benchmark context on other contracts**;
5. **unexecuted pair-compiler confirmatory protocol**.

No result should migrate upward in this hierarchy merely because it is favorable.

---

## 6. Recommended paper thesis

> **Typed CM folding is a sound local compiler transformation, not a universal new Boolean algebra or guaranteed speedup.** A compiler can normalize signed/swapped binary operator occurrences into a canonical operand frame, fuse exactly compatible four-bit tokens, retain provenance for structural and retabulated paths, and fall back safely. Exploratory evidence shows that such local folding can reduce symbolic work before expansion, while a matched generic local optimizer can reproduce the same reduction. A completed dispatcher experiment shows that selection overhead can erase large local wins. The remaining performance question is whether the full frame-aware compiler amortizes recognition, preparation, sharing, conversion, and fallback costs against strong packed/DAG baselines.

This thesis is honest even if the eventual protocol-v3 result is negative.

---

## 7. Recommended outline

1. **Introduction and exact claim boundary**  
   Motivate frame mismatch; state the compiler transformation; state what is antecedented and what remains open.
2. **Minimal CM compiler contract**  
   Four-bit true-first token, one-hot selection, operand-frame metadata. Refer to companion foundations paper for the broader calculus.
3. **Typed normalization and fusion**  
   Swap/polarity/output transforms; common-frame admission; motivating implication example.
4. **Pair compiler and soundness**  
   Grammar, judgment, provenance, pure structural rule, exact retabulation, hybrid path, ordinary fallback.
5. **Implementation architecture and cost model**  
   Five artifacts; pseudocode; layout conversion; ownership; N/U/H/S/D/k/n cost variables; sharing.
6. **Closest prior art and matched comparators**  
   Cheng/Zhao/Xu, Boolean/matrix logic, NPN/LUT/AIG, direct packed evaluation, ROBDD, generic local optimizer.
7. **Experimental questions and evidence hierarchy**  
   Define endpoints and why token-only, dense-output, ANF, and repeated-restriction tasks cannot be mixed.
8. **Current results**  
   Correctness record; S1/S2 mechanism; P14-PY0 negative dispatcher; separate later project-level context.
9. **Confirmatory protocol and remaining gap**  
   Summarize protocol v3 and leave it explicitly unexecuted.
10. **Discussion and limitations**  
    When folding helps, generic equivalence, sharing, reuse, output type, fallback prevalence, non-compression.
11. **Conclusion**
12. **Appendix**  
    Compact proof details and verification scope. No LM appendix.

---

## 8. Revised abstract

Correspondence matrices (CMs) encode a binary Boolean connective as a four-bit `2 x 2` operator in a declared operand frame. This paper studies a compiler transformation built on that representation rather than claiming a new truth-table algebra. The compiler recognizes binary operator occurrences, records their row/column operands and polarities, transports swapped or negated occurrences into a canonical frame, and fuses tokens only after exact frame agreement. It distinguishes pure structural folding, hybrid folding through locally retabulated descendants, whole-root four-assignment retabulation, and ordinary fallback. We state a common semantic invariant and prove soundness for each admitted pair path. The implementation keeps compact tokens, framed pair surrogates, general Boolean IR, lowered programs, and dense outputs as distinct artifacts so that constant-size kernel operations are not confused with end-to-end costs. Existing exploratory S1/S2 records show that local small-function folding can reduce pre-expansion work in some strata, but a matched generic local truth-function optimizer reaches the same reduced outputs. A separately frozen ANF-dispatch study is negative overall: highly profitable selected synthetic folds do not repay dispatcher overhead on the aggregate synthetic and natural corpora. Broader current-source project benchmarks likewise emphasize task matching and strong packed/CSE controls, but they measure different endpoints and are not pair-compiler results. The confirmatory pair-compiler protocol against direct packed, prepared DAG, ROBDD, and synthesis-compatible baselines remains unexecuted. The contribution is therefore a typed frame-aware compilation rule, its sound fallback boundary, and a disciplined evaluation framework for determining when local folding amortizes in practice.

---

## 9. Revised contribution list

1. **Typed frame-aware compiler rule.** A four-bit CM token is paired with explicit operand-frame metadata; swap, polarity, and output transformations normalize admitted occurrences before same-frame fusion.
2. **Sound multi-path compilation semantics.** Pure structural folding, exact retabulation, hybrid composition, and ordinary fallback are separately specified and proved against one common frame invariant.
3. **Implementation and cost boundary.** The paper distinguishes compact tokens, framed surrogates, general IR, lowered programs, and dense materialized outputs, and gives a cost model that includes traversal, support discovery, sharing, conversion, allocation, and reuse.
4. **Matched mechanism and negative evidence.** Exploratory S1/S2 results show where local folding reduces pre-expansion work while tying an equally capable generic optimizer; the completed P14-PY0 study shows a concrete region where dispatcher overhead dominates despite large local wins.
5. **Confirmatory methodology.** A task-matched protocol compares the actual pair compiler with direct and prepared packed evaluation, sharing-aware alternatives, ROBDD, and an applicable AIG/ABC subset without conflating kernel, preparation, or output costs.

---

## 10. Missing experiments and artifacts

Before submission, the strongest missing item is still the **protocol-v3 pair-compiler run**. The paper can circulate as an initial technical draft without it, but the performance thesis remains incomplete.

Required submission artifacts include:

- immutable source snapshot for the pair compiler and all comparators;
- raw S1/S2 records and independent recount output;
- P14-PY0 freeze, amendments, raw timing rows, analysis code, and manifest;
- protocol-v3 harness, pilot record, final freeze, schedule, and append-only raw observations;
- exact natural-corpus provenance, licenses, inclusion/exclusion rules, and hashes;
- ABC/AIG version, commands, library inputs, and the frozen translatable subset;
- complete environment capture: OS, Python/compiler versions, CPU, memory, power policy, affinity/thread policy, GC policy, hash seed, process-start method, and timing source;
- process-RSS memory methodology for the confirmatory run;
- failures, timeouts, unsupported cases, and budget rejections retained in the raw denominator;
- public archival repository/release or DOI that binds code, data, manuscript, and results;
- final literature check for the exact compiler integration claim, not just component mathematics.

Some of these materials appear to exist in the public repository in current or historical form, but this initial draft does not treat their mere presence as equivalent to a single frozen, submission-ready evidence package.

---

## 11. Detailed revision plan

### Phase 1 — complete the split

- Remove the standalone LM section from the computational manuscript.
- Remove LM valuation/pairing proofs and higher-arity LM material from its appendices.
- Replace them with one paragraph citing the companion foundations manuscript and explicitly saying LMs are not used by the timed compiler.
- Drop Impax/rotation exposition from the main computational argument unless retained as a one-sentence notation note.

### Phase 2 — sharpen the compiler core

- Lead with the frame-mismatch implication example.
- Define a compact frame type before showing fusion.
- Preserve the `pure_structural`, `hybrid`, and `retabulate` strategies and four root outcomes.
- Keep the invariant and compact inference rules in the main text; move proof details to the appendix.
- Add pseudocode whose case ordering matches the implementation exactly.
- Keep the artifact-separation table near the implementation section.

### Phase 3 — rewrite the novelty section around closest operations

- Put Cheng/Zhao/Xu next to the raw pointwise identity.
- Put NPN/LUT/AIG and packed truth functions next to the normalization/four-bit-token implementation.
- Put CSE/hash-consing, direct packed AST evaluation, and generic local truth-function optimization next to the systems claim.
- State that CM-specific value, if any, must come from the cost and compositionality of frame metadata and integration, not from an exclusive right to the reduction.

### Phase 4 — impose evidence hierarchy

- Keep S1/S2 as exploratory mechanism evidence.
- Keep P14-PY0 as a completed negative end-to-end result for a different ANF dispatch endpoint.
- Add a short contextual paragraph on later public project benchmarks: corrected August kernel/wrapper evidence and September current-source architecture comparisons. Explicitly label these as different task contracts.
- Keep protocol v3 visibly unexecuted.

### Phase 5 — run the missing confirmatory campaign

- Pilot only to debug the harness.
- Freeze corpus, source, toolchain, seeds, run schedule, endpoint definitions, and primary hypothesis.
- Execute without refitting the rule after results are visible.
- Populate the Results section and a performance-boundary figure with wins, ties, losses, fallbacks, failures, memory, and break-even reuse.

### Phase 6 — submission pass

- Re-run all correctness tests from the frozen source snapshot.
- Verify every quantitative sentence against a machine-readable evidence ledger.
- Replace provisional project-record references with immutable archive identifiers.
- Perform final logic-synthesis prior-art review.
- Render and visually inspect all figures/tables; provide vector figures and accessible PDF metadata.

---

## Assessment of newer public benchmark artifacts

The public project contains newer benchmark campaigns than the manuscript snapshot. They are useful, but they should **not** be automatically merged into this paper's Results section.

| Later artifact | Task / endpoint | What it legitimately informs | Recommended treatment |
|---|---|---|---|
| 25 Aug 2026 benchmark audit correction | post-compilation evaluator/kernel and public wrapper on corrected corpora | Strong generic CSE-flat baseline; kernel benefit can coexist with wrapper loss; support-size dependence | Discussion / supplement context; not pair-compiler evidence |
| 3 Sep 2026 current-source architecture comparison | complete explicit relation, repeated restrictions, related multi-root outputs | Direct BitSet is strong for complete relation; CSE-flat wins parts of reuse ladder; task-specific native benefits and regressions | Discussion/methodology context; reinforces task matching |
| 3–4 Sep cross-machine q-ladder | q1/q4/q16/q64 repeated residual relation | Setup amortization and portability of fixed-arm ordering | Methodological context only |
| 16 Sep exact count/decomposition publication | exact count/decomposition and dd/CUDD prototype | Different output contract and research question | Exclude from this paper except perhaps a project-history footnote |

The paper should therefore use the newest public evidence to **tighten its interpretation**, not to manufacture an unrun pair-compiler speed result.

