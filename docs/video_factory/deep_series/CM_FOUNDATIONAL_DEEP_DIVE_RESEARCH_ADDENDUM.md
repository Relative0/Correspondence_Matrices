# Addendum — CM foundations, correspondence, layout coordinates, and episode partition

Date: 2026-09-01  
Applies to: `CM_FOUNDATIONAL_DEEP_DIVE_RESEARCH_PROMPT.md`  
Status: supplementary research instructions; no content or production approval

## How to use this addendum

Paste this addendum after the existing foundational deep-dive research prompt.
It does not replace or relax any instruction in that prompt. In particular, the
same read-only constraints, primary-source requirements, complete statement
audit, benchmark boundaries, and single-report deliverable still apply.

The earlier prompt already asks whether the material belongs in one, two, or
three episodes. This addendum makes the missing decisions explicit: what the
matrices correspond to, when the name “correspondence matrix” is justified,
what “address” means, and how the paper's elementary 2×2 objects connect—or do
not connect—to the repository's arbitrary row/column layouts.

## Provisional answer that must be verified, not assumed

Use the following only as a hypothesis to test against the paper, code, and
other primary sources:

1. Each of the sixteen 2×2 binary matrices in the paper's Figure 1 corresponds
   to one of the sixteen possible Boolean functions of two binary inputs. In
   that elementary setting, “operator CM” may be a clear learner-facing name.
2. A larger valued matrix can still correspond to a Boolean function or
   compound logical expression under declared basis/variable ordering. It does
   not necessarily correspond to one elementary two-input operator. Calling it
   an “operator matrix” may therefore become misleading even if “CM” remains
   justified by the paper's higher-dimensional construction.
3. The repository accepts ordered row variables `R` and column variables `C`,
   aligns the function over `R + C`, and reshapes the exact outputs to
   `2^|R| × 2^|C|`. Thus a 4×4, 2×8, or 8×2 artifact can encode the same
   four-variable truth mapping under different declared partitions.
4. That code fact alone does not prove that every arbitrary rectangular output
   is a CM in the originating paper's sense. It may instead be a repository
   generalization, a row-column truth matrix, or a convenient CM-compatible
   output layout. The report must decide which description is supportable.
5. “Address” is at most an analogy for a row/column coordinate or array index.
   A learner should first see the assignment bits determine a labeled row and
   column; only then may “address” be introduced, if it remains useful.

For each hypothesis, return **verified**, **partly verified**, or **rejected**,
with exact paper and code locators. Do not preserve the terminology merely
because the repository currently uses it.

## Additional questions the report must answer

### A. What is the correspondence?

Answer separately for each object below. State the two things being put in
correspondence and whether the relation is one-to-one, dependent on ordering,
or only an implementation convention.

1. A paper-style 2×2 CM for a two-input Boolean operator.
2. A paper-style 4×4 logical matrix before valuation.
3. The corresponding 4×4 CM after positive valuation.
4. A higher-dimensional paper CM.
5. The repository's dense output from `compile_expr_to_cm`.
6. The repository's 2×8 and 8×2 layouts.
7. CM-IR, which is not itself the final dense matrix.
8. Packed and reduced outputs, which may preserve the function but not the
   visible row-column matrix.

At minimum, test these candidate explanations:

- input-state pair ↔ matrix entry;
- complete truth assignment ↔ row/column coordinate;
- logical operator/function ↔ complete valued matrix;
- logical expression in an LM entry ↔ its Boolean valuation in a CM entry;
- syntax/computation graph ↔ CM-IR node structure.

Identify which explanation belongs to which layer. Reject any single slogan
that improperly collapses all five.

### B. Are the larger artifacts still “corresponding to logical operators”?

Give a direct answer in three levels:

1. **Elementary:** Does every one of the sixteen 2×2 matrices represent exactly
   one binary Boolean operator/function, under fixed input order?
2. **Composed:** Does a 4×4 or higher-dimensional valued matrix represent a
   compound Boolean function, an operation assembled from smaller operators,
   a valuation of an LM, or some combination of these descriptions?
3. **Repository-generalized:** Does an arbitrary `2^|R| × 2^|C|` dense output
   retain a formal correspondence to a function's assignments and values even
   when its rectangular shape is not the paper's stated `2^n × 2^n` form?

Explain the difference between “corresponds to a Boolean function” and
“is one of the elementary operator CMs.” Determine whether the series should
reserve **operator CM** for 2×2 examples and use a different qualified name for
larger or repository-specific artifacts.

### C. What exactly changes when a layout changes?

For one fixed function and fixed full variable order, compare its truth vector,
4×4 `AB/CD` layout, 2×8 `A/BCD` layout, and 8×2 `ABC/D` layout. Create a small
mapping table for assignment `A=1, B=0, C=1, D=1` that shows:

- the unchanged complete assignment;
- the unchanged output value;
- the row bit string and integer index;
- the column bit string and integer index;
- the matrix shape;
- the assumptions needed to reverse a coordinate back to an assignment.

Then distinguish these possible changes:

- only a view/reshape changes;
- the declared row/column partition changes;
- variable order changes;
- the mathematical matrix object changes while the represented Boolean
  function remains extensionally equal;
- physical memory location changes;
- a new value is computed or updated.

The report must say whether “None of the answers changed. Only their addresses
did” is technically true, pedagogically safe, and faithful to the paper. If it
is retained, define “answer” and “address” before using either. Otherwise
replace it. Consider language such as:

> The same sixteen output values occupy different labeled coordinates when we
> choose a different row-column partition.

Do not call this an “update” unless an actual state or value is being changed.
If the intended meaning of “how these updates are applied” is instead the
construction or valuation of larger CMs from logical operators, explain that
process explicitly and recommend a less ambiguous term such as **construction**,
**composition**, **valuation**, **materialization**, or **re-layout**.

### D. Does the matrix name survive arbitrary shape?

Resolve the terminology for all of the following, with a recommended safe name
and a one-sentence definition for each:

- the sixteen 2×2 CMs in Figure 1;
- a 2×2 LM;
- a 4×4 LM;
- its positive valuation as a 4×4 CM;
- the paper's stated higher-dimensional square construction;
- the repository's balanced 4×4 explicit dense output;
- the repository's arbitrary rectangular 2×8 or 8×2 output;
- a flat 16-bit truth vector;
- CM-IR;
- a packed-bit output.

Evaluate at least these naming policies:

1. Call all dense row/column outputs CMs without qualification.
2. Reserve CM for objects constructed under the paper's definition and call
   arbitrary rectangular outputs **row-column truth matrices**.
3. Use explicit qualifiers, such as **paper CM**, **higher-dimensional valued
   CM**, and **repository explicit CM layout**.

Recommend one policy for the videos, source code documentation, content Bible,
glossary, and benchmark reporting. The policy must allow a learner to trace
claims without implying that the paper defined an API it did not define.

### E. How does the larger matrix arise?

Reconstruct one small example from first principles. The visual explanation
must not jump directly from a truth-table output column to a 4×4 grid if the
paper derives the 4×4 object through logical matrices, tensor products,
composition, or valuation.

Determine which of these are mathematically equivalent views and which are
distinct constructions:

1. Enumerating a function's truth table and reshaping its output column.
2. Building an LM whose entries are logical expressions.
3. Applying positive valuation to obtain a binary CM.
4. Composing elementary operator CMs or associated state-vector operations.
5. The repository compiling an expression to CM-IR and materializing a dense
   `R × C` output.

If two paths yield the same 4×4 binary array, do not infer that their internal
objects, algorithms, or explanatory purpose are identical. Recommend the
minimum derivation a learner needs before seeing the repository implementation.

## Required curriculum decision

Audit and either accept, modify, or reject this provisional sequence:

### Proposed lesson F — “From truth tables to the sixteen operator CMs”

**Purpose:** establish the paper-first foundation.

**Must teach:**

- two Boolean inputs have four assignments;
- a binary Boolean function chooses one output for each assignment;
- there are `2^4 = 16` such functions;
- with a fixed row/input and column/input order, each complete four-bit output
  pattern can be displayed as one 2×2 matrix;
- therefore there are sixteen distinct 2×2 binary operator CMs;
- examples should include constant false, AND, XOR, OR, implication if the
  paper includes it, and constant true;
- changing input/basis order can change placement and must be declared;
- the matrix is the complete operator/function, not one “answer.”

**Visual spine:** begin with four input-state cards, populate one 2×2 operator
matrix, then place several named operators into a 4×4 gallery of sixteen 2×2
matrices. Never display sixteen unlabelled boxes as though they were sixteen
assignments of one four-variable function.

**Retrieval check:** show an unlabeled 2×2 pattern and ask which outputs it gives
for the four ordered input pairs; optionally identify the operator only after
the output mapping is understood.

### Proposed lesson G — “From operator CMs to larger logical matrices”

**Purpose:** show how the paper moves from elementary operators to compound and
higher-dimensional objects.

**Must teach, if supported by the paper:**

- the distinction between an LM and its positive valuation as a CM;
- how the entries, basis states, and variable order are determined;
- one fully worked 4×4 construction, not merely a completed grid;
- what is composed, transformed, measured, or valued;
- why the resulting matrix corresponds to a compound logical function rather
  than to one elementary binary operator;
- the paper's square `2^n × 2^n` generalization and its assumptions;
- what the paper does and does not say about arbitrary rectangular partitions.

**Visual spine:** keep one 2×2 operator CM visible as an anchor; show the logical
construction growing to an LM; then make valuation a visible, labeled operation
that turns logical entries into binary entries. Do not use a generic “boxes
appear” montage.

**Retrieval check:** given one LM entry and a declared valuation, predict the
corresponding binary CM entry before it is revealed.

### Revised current lesson — “The repository's explicit row-column CM layout”

**Purpose:** teach the implementation artifact only after the paper-first
foundation is secure.

**Must teach:**

- the function, assignment, output, partition, coordinate, and stored entry are
  different objects;
- `R` and `C` are ordered variable lists in the repository API;
- the implementation produces `2^|R| × 2^|C|` exact dense output;
- one complete assignment splits into a row index and column index;
- coordinates recover assignment bits only when `R`, `C`, bit order, and fixed
  variables are known;
- changing the split can change both the matrix object and shape while
  preserving the represented function's complete input-output mapping;
- whether **CM** here is paper-faithful, generalized, or project terminology;
- no compactness or speed claim follows from dense materialization.

**Visual spine:** show persistent invariant and variant rails. The invariant
rail carries the expression, complete assignment, and output. The variant rail
carries `R`, `C`, shape, row index, and column index. Track one assignment
through 4×4, 2×8, and 8×2 only if the report validates the terminology; if not,
label the rectangular forms as repository row-column truth matrices.

**Retrieval check:** give `R`, `C`, ordering, fixed context, and one assignment;
ask for its coordinate and output. Then remove the ordering labels and ask why
the bare coordinate is insufficient.

For each proposed lesson return:

- KEEP AS PROPOSED, KEEP WITH CHANGES, MERGE, SPLIT, MOVE, or REJECT;
- final recommended title and episode ID;
- one-sentence thesis;
- owned concepts and explicit exclusions;
- prerequisite episode(s);
- target duration range;
- a beat-by-beat outline with one visual action per explanatory claim;
- exact handoff sentence to the next lesson;
- which parts of the current `SCRIPT_V2.md` can be reused, rewritten, moved, or
  cut;
- whether a new content-Bible entry is needed.

Do not rewrite `SCRIPT_V2.md` in place. Supply a corrected outline and a
timestamped patch plan in the report so the original production task can make
the changes after the research is accepted.

## Additional visual-quality requirements

The report's recommended visuals must prevent the empty-box and repetition
problems already observed in the produced videos:

1. Every matrix cell or group of cells must have a semantic role: input state,
   logical expression, valuation result, coordinate, or comparison.
2. Never use three generic boxes when a worked mapping, operator table, basis
   diagram, or before/after construction would explain the claim.
3. Preserve a stable visual grammar across lessons:
   - amber for row-side state;
   - cyan for column-side state;
   - white for the selected entry/output;
   - a distinct color for expressions awaiting valuation;
   - separate shapes for assignments, outputs, operators, LMs, CMs, and IR
     nodes.
4. Use motion only to express a mathematical action: populate, reorder,
   partition, compose, value, select, or compare.
5. When the same sixteen values are shown in multiple layouts, keep persistent
   assignment IDs—not merely identical 0/1 chips—so the viewer can tell what is
   invariant.
6. Include at least one misconception check distinguishing:
   - sixteen binary operators from sixteen assignments of a four-variable
     function;
   - a coordinate from the value stored there;
   - a paper CM from CM-IR or a packed truth vector.
7. Prefer “coordinate,” “row index,” and “column index” in foundational
   narration. Use “address” only after defining it as an implementation analogy
   and only if the panel finds that it improves rather than impairs retention.

## Required additions to the final report

In addition to the report structure already required, include:

1. **Terminology decision record:** the selected naming policy, rejected
   alternatives, and consequences for existing scripts and registries.
2. **Correspondence map:** a diagram or table showing exactly what corresponds
   to what in each paper and repository layer.
3. **Construction bridge:** a worked explanation from a two-input operator CM
   to a larger paper object and then to the repository artifact, marking any
   discontinuity rather than hiding it.
4. **Episode decision:** a definitive recommended sequence, not merely a list
   of options.
5. **SCRIPT_V2 disposition table:** for every section, state whether it belongs
   in lesson F, lesson G, the revised implementation lesson, or nowhere.
6. **Visual sufficiency test:** for every proposed beat, state what changes on
   screen, what the learner should infer, and which misconception it prevents.
7. **Open author decisions:** isolate only genuine choices that primary-source
   research cannot settle, especially whether project terminology should retain
   “CM” for arbitrary rectangular dense layouts.

## Strengthened success condition

The work is not complete until a learner can answer all of these without
guessing:

1. Why are there sixteen 2×2 Boolean operator matrices?
2. Why does one four-variable function also have sixteen assignments and
   sixteen output values?
3. Why are those two uses of “sixteen” about different objects?
4. What does one cell mean in a 2×2 operator CM?
5. What does one cell mean in a 4×4 valued CM or repository truth layout?
6. What remains invariant and what changes when `AB/CD` becomes `A/BCD`?
7. What contextual labels are needed to decode a coordinate?
8. In what sense does a larger matrix correspond to a logical function rather
   than to one elementary logical operator?
9. Which uses of “CM” come directly from the paper, and which are qualified
   repository terminology?
10. How does the dense matrix differ from CM-IR and packed output?

