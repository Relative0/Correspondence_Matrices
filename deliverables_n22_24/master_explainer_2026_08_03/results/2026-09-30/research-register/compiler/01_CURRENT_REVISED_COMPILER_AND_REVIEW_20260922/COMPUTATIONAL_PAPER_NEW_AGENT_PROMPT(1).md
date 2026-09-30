# Deep Revision Prompt: Rebuild the Computational CM Paper After the CM/LM Split

You are acting as a **senior research software architect, Boolean-computation researcher, compiler specialist, experimental-methodology reviewer, and mathematical editor**.

Your primary task is to revise and strengthen the manuscript:

> **Operator-Level Boolean Computation with Correspondence Matrices**

This paper began as a combined CM/LM foundations + compiler manuscript. The research program has now been deliberately split.

A separate foundations manuscript now owns the deeper mathematical and symbolic material:

> **Correspondence and Logical Matrices: A Boolean Operator Calculus**

The computational paper should therefore be rebuilt as a focused paper on **typed CM compilation, frame normalization, operator fusion/folding, fallback semantics, implementation architecture, and empirical evaluation**.

Read the supplied artifacts first. Do not rely only on this prompt.

---

## 1. Source precedence

Use this order when sources conflict:

1. `Operator-Level_Boolean_Computation_with_Correspondence_Matrices_current.pdf` — current computational manuscript to revise.
2. `Correspondence_and_Logical_Matrices_Boolean_Operator_Calculus_LM_Centered.pdf` — authoritative current foundations paper and the hard boundary for material that should not be duplicated.
3. `Computational_Paper_Response_to_R2.md` — current disposition of the computational review findings.
4. `Computational_Paper_Review_Panel_R2.md` and `Computational_Paper_Review_Panel_R1.md` — earlier review context.
5. `CM_LM_Audit_Astra.*` — independent deep audit, especially useful for prior-art boundaries, notation, and the relationship between the foundations and computational papers.
6. Verification/context notes only as supporting evidence, not as substitutes for proofs or experiment artifacts.

If an artifact references code or benchmark packages that are not actually present in this handoff, explicitly identify them as missing rather than reconstructing empirical claims from prose.

---

## 2. Hard publication split

The separate foundations paper now owns, in substantial detail:

- compact CM semantics as a Boolean operator representation;
- the `\Theta` / `[\Theta]` notation and true-first convention;
- formula-valued Logical Matrices (LMs);
- the LM frame normal form;
- general valuation from LM to numeric CM;
- logical pairing and basis reconstruction;
- n-ary LM/tensor extensions;
- the general coherence of LM lift, valuation, pairing, pointwise Boolean superposition, and signed frame transport;
- higher-dimensional correspondence maps and block constructions;
- Boolean closure, rank/separability interpretations, and the broader foundations literature audit.

**Do not republish these as major results in the computational paper.**

The computational paper may summarize the minimum mathematical contract it needs, with a clear citation to the companion foundations paper.

In particular, the computational paper should probably retain only enough theory to establish:

1. the compact numeric CM token for a binary connective;
2. declared operand-frame metadata;
3. transpose / row / column / output transformations needed for normalization;
4. the same-frame fusion theorem;
5. compiler soundness and fallback behavior.

Everything beyond that should be included only if it directly contributes to the compiler or experiment.

---

## 3. Preserve current notation

Unless there is a real mathematical objection, preserve:

```math
\mathbb B=\{0,1\}\cong\mathbb F_2.
```

XOR is written

```math
\Updownarrow
```

not `\oplus`.

XNOR/equivalence as a Boolean connective is written

```math
\Leftrightarrow.
```

A binary logical connective/operator variable is

```math
\Theta,
```

and its compact CM is

```math
[\Theta].
```

Use lowercase `x,y` for Boolean values/assignments and uppercase `X,Y` for symbolic logical operands when both levels appear.

Do not casually revert to `C_f` notation for the binary CM if `[\Theta]` is clearer.

---

## 4. The computational paper's intended core

The central computational idea is not merely that truth tables can be combined pointwise.

The useful compiler transformation is:

> **recognize operator occurrences that refer to the same logical operand frame; transport signed/swapped occurrences into one canonical frame; then fuse the corresponding CM tokens before evaluating or expanding the operands.**

For aligned occurrences,

```math
(x\Theta_1 y)\Phi(x\Theta_2 y)
=
\left\langle x\middle|
\left([\Theta_1]\widehat{\Phi}[\Theta_2]\right)
\middle|y\right\rangle.
```

The raw pointwise numerical identity has prior art. The computational contribution should therefore be framed around the **typed admission rule, normalization, folding architecture, fallback boundary, and measured cost/benefit** rather than claiming pointwise truth-table combination itself as new.

A key motivating example is the frame-mismatch case

```math
(X\Rightarrow Y)\Updownarrow(Y\Rightarrow X).
```

Naively fusing `[\Rightarrow]` with `[\Rightarrow]` is wrong because the second occurrence has frame `(Y,X)`. After alignment,

```math
[\Rightarrow]\widehat{\Updownarrow}[\Rightarrow]^T
=[\Updownarrow].
```

This is a good concise illustration of why the compiler must carry frame type information.

---

## 5. Existing compiler architecture to preserve and audit

The current manuscript distinguishes several artifacts that must not be conflated:

- compact 4-bit CM operator token;
- pair surrogate = token + canonical row/column frame metadata;
- general CM/Boolean IR;
- lowered/flat program;
- explicit dense truth-relation output.

Preserve or improve this separation.

The pair compiler has three important strategies / provenance classes:

- **pure structural** — frame recognition, signed alignment, negation, and same-frame fusion only;
- **hybrid** — structural compilation may consume locally retabulated two-variable descendants;
- **whole retabulation** — explicitly evaluate all four assignments for a binary-support root;
- otherwise **ordinary fallback** to the general IR path.

The review history specifically found and then fixed a hidden hybrid path. Make sure the paper, theorem statements, implementation names, diagnostics, and experimental arms remain consistent.

---

## 6. Soundness story

The paper should give a concise but formal compiler soundness argument.

A useful invariant is that a returned framed pair token `t` for canonical row variable `R` and column variable `C` satisfies

```math
E_t(r,c)=e[r/R,c/C]
```

for all `r,c in B` after fixed substitutions.

The paper should retain distinct results for:

1. pure structural alignment/fusion soundness;
2. exact four-assignment retabulation;
3. hybrid soundness;
4. top-level fallback correctness contract.

Do not overformalize the paper if a compact typed-judgment presentation suffices, but make the implementation independently reproducible from the text.

---

## 7. Prior-art boundary

The paper must be especially careful about novelty.

Known or strongly antecedented ingredients include:

- truth-table and LUT representations;
- packed small truth functions;
- input negation / permutation / output negation;
- NPN equivalence and canonicalization;
- pointwise Boolean combination of truth vectors;
- AIG/LUT rewriting;
- common-subexpression sharing;
- Boolean matrix algebra;
- bit-parallel evaluation;
- generic local truth-function optimization.

The paper should directly compare with at least:

- Cheng/Zhao/Xu Boolean-matrix/truth-vector work;
- NPN/LUT/AIG synthesis practice;
- direct packed truth-table evaluation;
- ROBDDs where meaningful;
- a generic local truth-function optimizer given equivalent local information.

The paper should not argue that a reduction is important only if it is uniquely CM-specific. A useful optimization can still matter if a generic optimizer can reproduce it. Instead separate:

- **mechanism value** — can frame-aware local folding reduce symbolic work before expansion?
- **representation-specific value** — does CM metadata make that reduction especially direct, cheap, compositional, or reusable?
- **end-to-end value** — does the full compiler actually save time/memory after recognition, planning, conversion, and fallback costs?

---

## 8. Existing evidence that must be represented honestly

The current manuscript already separates several evidence levels. Preserve that discipline.

### A. Correctness evidence

The current paper reports focused tests covering the 16 tokens, eight signed frames, primitive connectives, recursive fusion, hybrid provenance, retabulation, fixed substitutions, and random two-variable formulas, plus exhaustive signed-alignment/fusion enumeration.

Verify the exact current counts from the manuscript/source artifacts before publishing them.

### B. S1/S2 exploratory mechanism evidence

The manuscript reports a canonical S1/S2 record with 10,500 generated cases, 10,389 completing in all four arms. CM folding and an equivalently capable generic local optimizer agree on the principal symbolic-output metrics for all admitted all-arm cases. Some strata show substantial pre-expansion work reduction relative to direct ANF, but the generic optimizer achieves the same reduction.

Interpret this as:

> evidence that local small-function folding can reduce pre-expansion symbolic work, **not** evidence of unique CM semantics or confirmed end-to-end speedup.

### C. P14-PY0 negative dispatcher boundary

The current manuscript reports a separately frozen dispatch study in which the exact dispatcher was slower overall than direct ANF lowering on the acquired synthetic and natural corpora, despite some highly profitable selected synthetic cases.

Preserve the preregistered aggregation and the negative conclusion. Do not select a favorable alternative statistic after the fact.

### D. Protocol v3

The broader token/packed evaluation protocol remains, in the current manuscript, **unexecuted**. It is designed to compare the actual framed CM pair compiler against direct packed evaluation, prepared packed evaluation, general CM IR, ROBDD, and an ABC/AIG-compatible arm where applicable.

Do not write results for this protocol unless genuine run artifacts are supplied.

---

## 9. Critical question: what paper should this become now?

Do not assume the existing paper structure is still optimal after the LM split.

Consider at least three possible publication shapes:

### Option A — Compiler paper

A focused paper on:

- typed operand frames;
- normalization;
- local CM token fusion;
- hybrid/fallback semantics;
- implementation;
- benchmark methodology and results.

### Option B — Optimization/mechanism paper

A narrower paper on:

- pre-expansion local function folding;
- CM frame metadata as one implementation;
- matched generic truth-function comparator;
- where symbolic work is reduced;
- why end-to-end overhead may erase the benefit;
- selective dispatch / break-even analysis.

### Option C — Systems/methodology paper

A paper emphasizing:

- how to evaluate small-domain symbolic optimizations fairly;
- separating kernel wins from compiler wins;
- explicit output/materialization costs;
- prepared vs one-shot endpoints;
- sharing and reuse;
- negative results and dispatcher boundaries.

Determine which shape the actual evidence supports best.

A hybrid is acceptable if coherent, but do not keep historical material merely because it was once in the manuscript.

---

## 10. What to remove or reduce after the split

Strongly consider removing from the computational paper's main body:

- the full formula-valued LM section;
- extended logical pairing theory;
- higher-dimensional LM theory;
- spectral/eigenvalue material;
- phase/quantum analogies;
- general Boolean-calculus foundations that are now owned by the companion paper.

A brief foundations section may define the exact numeric rules needed by the compiler and point to the companion foundations paper for the general theory.

This should materially shorten and sharpen the paper.

---

## 11. Experimental review — be adversarial

Audit the evaluation as if reviewing for a compiler / symbolic-computation venue.

Check:

- Are timing endpoints genuinely comparable?
- Are preparation costs included where required?
- Are token-only results ever compared against competitors that materialize larger outputs?
- Is direct packed four-bit evaluation used as the closest simple non-CM baseline?
- Is DAG sharing preserved for methods that support it?
- Are identity-shared and merely structurally equal subtrees distinguished?
- Are natural workloads representative and fully provenance-recorded?
- Are ABC/AIG tool versions and commands frozen?
- Is garbage collection/process startup/threading/affinity/hash-seed policy specified?
- Are failures/timeouts/rejections retained rather than silently filtered?
- Are primary hypotheses singular and preregistered?
- Are negative results reported with the same prominence as positive mechanism evidence?

Do not allow a kernel-only constant-time token fusion to be presented as an end-to-end complexity result.

---

## 12. Investigate whether the paper should exploit newer benchmark artifacts

The broader project contains later benchmark/optimization investigations beyond the manuscript snapshot, including multiple planner/dispatcher iterations and Gate-P studies.

If such artifacts are supplied separately, examine them, but do not import them automatically.

For each later benchmark artifact determine:

1. Is it on the same task/endpoint as this paper?
2. Was it preregistered or exploratory?
3. Was it independently verified?
4. Does it supersede an older result?
5. Does it strengthen a mechanism claim, a runtime claim, or merely diagnose overhead?
6. Should it be in this paper, a supplement, or a later optimization paper?

Especially avoid mixing fundamentally different endpoints (e.g. ANF production vs packed truth evaluation) under one headline speedup claim.

---

## 13. Recommended concrete deliverables

Produce the following before rewriting the manuscript:

### A. Paper-split map

A table with columns:

- current section/result;
- keep in computational paper;
- summarize + cite foundations paper;
- move entirely to foundations paper;
- delete;
- rationale.

### B. Claim ledger

For every intended computational-paper claim, classify as:

- theorem/correctness claim;
- implementation claim;
- mechanism evidence;
- end-to-end empirical result;
- negative boundary;
- unexecuted protocol / future work.

### C. Evidence ledger

Map each empirical sentence to a concrete artifact or mark it unsupported.

### D. New paper outline

Design the strongest post-split architecture.

### E. Revised abstract and contributions

Write a conservative abstract and 3–5 precise contributions.

### F. Missing-artifact list

Identify everything needed before submission, especially code, raw results, environment captures, frozen manifests, and repository/archive identifiers.

### G. Revised manuscript

Only after A–F, produce a new manuscript draft.

---

## 14. Likely post-split architecture to test

Do not treat this as mandatory, but assess something like:

1. **Introduction and exact claim boundary**
2. **Minimal CM compiler semantics**
3. **Typed operand frames and normalization**
4. **Structural fusion, retabulation, and fallback**
5. **Implementation architecture and complexity/cost model**
6. **Closest prior art and comparators**
7. **Experimental questions and protocol**
8. **Results / evidence levels**
9. **Discussion: when folding helps and why it may not amortize**
10. **Limitations and conclusion**

The deeper LM mathematics should be cited to the companion foundations paper rather than redeveloped here.

---

## 15. Important conceptual distinction

The paper should not require that a useful reduction be uniquely CM-specific.

A result like:

> “CM folding and a generic local truth-function optimizer reach the same reduced symbolic form”

is **not** a failure of the optimization mechanism.

It means the reduction belongs to a more general small-function/local-cut optimization family.

The scientific questions then become:

- Does the CM representation make recognition or transformation cheaper?
- Does typed frame metadata make legality explicit?
- Does it compose naturally with the broader CM compiler?
- Does it expose useful reuse/precomputation opportunities?
- On what workload regions does the benefit amortize?

Keep this distinction explicit.

---

## 16. Questions the final paper must answer

1. What exactly is the compiler transformation?
2. What are its soundness conditions?
3. What is its asymptotic and constant-factor cost?
4. When does it avoid repeated operand work?
5. When does it merely retabulate a tiny truth function?
6. When does a generic local optimizer do exactly the same thing?
7. What is specifically useful about the CM representation/frame metadata?
8. What are the fallback conditions?
9. How often does structural fusion occur on realistic workloads?
10. When does preprocessing cost amortize?
11. What is the closest direct packed baseline?
12. Does the method ever win end to end under a fair matched-capability comparison?
13. Where does it lose, and why?
14. How does sharing affect the answer?
15. What output types/reuse counts change the break-even point?

If the current artifacts cannot answer a question, say so rather than filling the gap rhetorically.

---

## 17. Final review posture

Be willing to conclude any of the following:

- the computational paper is strong after removing LM theory;
- the paper should be shorter and more systems-oriented;
- the current evidence supports a mechanism paper but not a performance paper;
- the unexecuted protocol must be completed before submission;
- a negative result is itself the correct publication outcome;
- some later benchmark work should be separated into another paper rather than folded in.

The goal is the **strongest defensible paper**, not preservation of the current manuscript.

---

## 18. Final requested output order

Return:

1. Executive assessment of the post-split paper.
2. Section-by-section split map.
3. Correctness audit of the compiler transformation.
4. Prior-art/novelty audit.
5. Evidence ledger.
6. Recommended paper thesis.
7. Recommended outline.
8. Revised abstract.
9. Revised contribution list.
10. Missing experiments/artifacts.
11. Detailed revision plan.
12. Then, if enough evidence exists, produce a rewritten manuscript draft or a precise rewrite specification.

Do not silently treat the foundations manuscript as disposable background. It is the authoritative companion that allows this computational paper to become much more focused.
