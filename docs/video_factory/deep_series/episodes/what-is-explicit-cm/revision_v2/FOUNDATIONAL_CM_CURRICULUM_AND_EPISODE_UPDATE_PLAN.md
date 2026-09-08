# Foundational CM curriculum and episode update plan

Date: 2026-09-01  
Status: editorial recommendation; not content approval or production authorization  
Primary research input SHA-256: `48e6f8d121842624ff8e9230cc83d8a09444c14ba30fc77dd522a8ad71cd73bd`

## Decision

Use a three-video mini-arc. Move the current `what-is-explicit-cm` lesson to the
third position and rewrite it as a repository-specific implementation lesson.

The three lessons answer different questions:

1. **Why are there sixteen 2×2 operator CMs?**
2. **How does the paper construct larger CMs from logical matrices?**
3. **How does this repository lay one Boolean function out over ordered row and
   column variables?**

Combining those questions would recreate the ambiguity between sixteen binary
operators, sixteen assignments of one four-variable function, a paper-valued
CM, and the repository's arbitrary rectangular output layout.

The current planned neighbors already own the remaining distinctions:

- `what-cm-does-not-claim` owns compactness, solver, and performance non-claims;
- `explicit-cm-vs-cm-ir` owns the detailed dense-matrix/CM-IR/output comparison;
- `cm-ir-nodes-sharing` owns CM-IR internals;
- `packed-words-selection` owns packed execution.

The new mini-arc should preview those topics in one sentence at most, not teach
them twice.

## Recommended order

### Lesson 5 — `operator-cms-from-truth-tables`

**Title:** Why There Are Sixteen 2×2 Operator CMs  
**Target:** 4:30–5:45  
**Thesis:** Two Boolean inputs have four assignments. One complete choice of
four output bits defines one binary Boolean function, so there are `2^4 = 16`
such functions, each represented in the paper by one complete 2×2 operator CM.

**Owns**

- two inputs and four ordered assignments;
- assignment versus output;
- one complete four-bit pattern versus one matrix entry;
- `2^4 = 16` binary Boolean functions;
- one 2×2 matrix as one whole operator/function;
- the sixteen-matrix Figure 1 gallery;
- the effect of declared operand/state order.

**Does not teach**

- four-variable truth layouts;
- LMs or detailed bra-ket machinery;
- arbitrary row/column partitions;
- repository APIs, CM-IR, packed outputs, or benchmarks.

**Suggested beats**

1. Put the four ordered input pairs `00, 01, 10, 11` around an empty 2×2 grid.
2. Populate AND one entry at a time; then outline all four entries and label the
   whole matrix `AND`.
3. Let each of the four outputs visibly switch between 0 and 1; count
   `2 × 2 × 2 × 2 = 16` complete patterns.
4. Expand to the gallery of sixteen 2×2 matrices. Name only a useful subset:
   false, AND, XOR, OR, implication if its order is clearly declared, and true.
5. Swap the operand labels for an asymmetric example to show why order matters.
6. Retrieval: present one 2×2 pattern and ask for its four ordered outputs before
   naming the operator.

**Visual spine:** four input-state cards → one populated operator matrix →
sixteen complete matrices. Every box carries either an input pair, an output,
or an operator label.

**Handoff:** “A 2×2 CM represents one complete two-input operator. Next we will
see how the paper builds larger logical objects for compound expressions.”

### Lesson 6 — `logical-matrices-to-higher-dimensional-cms`

**Title:** From Logical Matrices to Higher-Dimensional CMs  
**Target:** 5:30–7:00  
**Thesis:** In the paper, a logical matrix contains logical expressions; positive
valuation turns those entries into a binary correspondence matrix, and the same
framework constructs larger square matrices for compound logical relationships.

**Owns**

- LM versus CM;
- expression-valued entry versus binary-valued entry;
- positive valuation;
- one fully worked 4×4 construction;
- basis/variable ordering;
- the paper's square higher-dimensional construction;
- the connection from elementary operator CMs to compound functions.

**Does not teach**

- the repository's arbitrary 2×8 and 8×2 layouts;
- implementation internals or performance;
- a full symbolic treatment of every bra-ket identity.

**Suggested beats**

1. Return briefly to one 2×2 operator CM—no Figure 1 recap.
2. Replace the binary entries with expression-valued LM entries, using a
   visibly different shape/color.
3. Evaluate one LM entry under a declared truth assignment.
4. Apply a visibly labeled positive-valuation operation to the complete LM.
5. Build one 4×4 LM using the paper's actual construction path; do not make a
   completed 4×4 grid appear from a truth-column reshape.
6. Value it into one 4×4 binary CM and state that it represents compound logic,
   not one elementary two-input operator.
7. Show the square higher-dimensional pattern and its ordering requirement.
8. Retrieval: predict the valued bit for one highlighted LM entry.

**Visual spine:** 2×2 anchor → expression-valued LM → highlighted valuation →
binary CM → constructed 4×4 LM/CM. Motion is reserved for construction and
valuation.

**Notation policy:** teach state pair, matrix position, LM, and valuation in
plain language first. Show bra/ket notation as a secondary label, not as the
entry point.

**Handoff:** “The paper's larger CMs are valued logical matrices built under a
declared ordering. Now we can separate that construction from the explicit
row-column layout implemented by this repository.”

### Lesson 7 — retained ID `what-is-explicit-cm`

**Title:** The Repository's Explicit Row-Column CM Layout  
**Target:** 5:15–6:15  
**Thesis:** The repository materializes one exact Boolean function as a dense
row-column truth matrix over ordered lists `R` and `C`; changing that partition
changes the matrix shape and coordinates while preserving every complete
assignment-to-output pair.

**Owns**

- ordered row and column variable lists;
- complete assignment versus output value;
- row index, column index, and coordinate;
- `2^|R| × 2^|C|` as the repository rule;
- balanced and rectangular repository layouts;
- what is invariant and what changes under re-partitioning;
- the context required to decode a coordinate;
- explicit/dense materialization;
- the qualified term **repository explicit CM layout**.

**Does not teach**

- the paper's LM derivation beyond a ten-second reminder;
- detailed CM-IR structure;
- detailed representation comparisons;
- SAT/solver boundaries;
- benchmark results or speed claims.

**Handoff:** “Now that the representation boundary is clear, the next lesson
separates what this dense layout guarantees from what it does not claim about
compactness, solving, or speed.”

## Exact update plan for `SCRIPT_V2.md`

### 0:00–0:25 — replace completely

Cut:

- “These are sixteen answers…”;
- “Only their addresses did”;
- the immediate unqualified claim that each displayed layout is an explicit CM.

Open instead on sixteen persistent **assignment-output cards** for the one
four-variable example:

> “This one four-variable function has sixteen possible input assignments.
> Each assignment has exactly one output. We will keep those pairs fixed while
> changing how the repository lays them out.”

Include a five-second reminder badge:

> “Different sixteen: the preceding lesson's sixteen matrices were sixteen
> different two-input functions.”

Do not replay the operator gallery.

### 0:25–0:58 — retain mechanism, rewrite terminology

- Change **ordered set** to **ordered list** or **ordered sequence**.
- Introduce literal implementation labels `R=[A,B]` and `C=[C,D]`.
- Use **row index**, **column index**, and **coordinate**, not address.
- Qualify the object:

> “In this repository, the dense result is called an explicit CM layout.”

### 0:58–1:50 — retain the 4×4 construction with a new boundary

Keep the current Boolean example, ordering, headers, and correct rows:

```text
0111
0111
0111
1000
```

Replace “watch the truth table fold” with:

> “The repository aligns the outputs to the declared order `A,B,C,D`, then
> arranges the `AB` bits as the row index and the `CD` bits as the column
> index.”

Add only this paper boundary:

> “This implementation route is not the paper's logical-matrix derivation.”

### 1:50–2:42 — keep and tighten the forward example

Keep `1011 → M[2,3]=1`. Preserve the full assignment and output as one card
while the row and column indices are derived. Remove the sentence about “not
losing the assignment”; the later reverse-decoding test teaches that more
precisely.

### 2:42–3:18 — keep, but make context explicit

Keep the reverse example `M[3,1]=0 → 1101`, but state that this recovery is
possible only because `R`, `C`, their order, and the MSB-first convention remain
visible. A bare coordinate does not identify an assignment.

### 3:18–4:05 — retain the retrieval pause

Keep `1110 → M[3,2]=0`, but shorten the setup. The learner should answer three
things in order: row index, column index, output.

### 4:05–4:58 — keep re-partitioning, change the claim

Retain all three repository layouts and track the same assignment-output pair:

| Layout | `R` | `C` | Coordinate for `1011` | Output |
|---|---|---|---:|---:|
| 4×4 | `[A,B]` | `[C,D]` | `(2,3)` | 1 |
| 2×8 | `[A]` | `[B,C,D]` | `(1,3)` | 1 |
| 8×2 | `[A,B,C]` | `[D]` | `(5,1)` | 1 |

Use:

> “The Boolean mapping did not change. The repository partition did, so the
> same assignment-output pair now occupies a different coordinate in a
> differently shaped matrix.”

State that these arbitrary rectangles are repository-supported layouts; do not
present them as the paper's stated general square construction.

### 4:58–5:32 — reduce to the owned dense-output fact

Keep:

> “Dense means every cell in the requested output layout is materialized.”

Move the rest:

- compactness, solver behavior, and speed → `what-cm-does-not-claim`;
- detailed CM versus CM-IR versus packed-output distinction →
  `explicit-cm-vs-cm-ir`;
- remove “the word matrix does not imply matrix multiplication,” because the
  paper explicitly develops matrix operations and the sentence is too broad.

A ten-second closing preview may show the later artifact icons without
explaining them.

### 5:32–close — rewrite

Use:

> “The Boolean function fixes which output belongs to each complete assignment.
> The repository's ordered row and column lists determine where that pair
> appears. Change the partition and the matrix changes; the function does not.”

## Visual grammar for the revised lesson

- Amber: row-side bits and row index.
- Cyan: column-side bits and column index.
- White: selected assignment-output pair and selected cell.
- Gray: unselected assignments/cells.
- Keep a persistent **invariant rail** containing expression, complete
  assignment, and output.
- Keep a separate **layout rail** containing `R`, `C`, matrix shape, row index,
  and column index.
- Give every moving item an assignment ID. Do not animate anonymous 0/1 chips.
- Every screen change must perform one meaningful action: order, partition,
  index, place, decode, or re-partition.
- Do not use generic three-box summaries.
- Do not repeat the expression evaluation after the first worked lookup.
- Do not rebuild the full 16-row truth table in neighboring episodes.

## Local prerequisite reconciliation

The attached report marked episodes 2–4 unverified because it lacked local
access. The local files show:

- `why-boolean-computation` already establishes the assignment-to-output
  mapping;
- `expression-truth-function` already distinguishes expression, truth table,
  and function;
- none of the first four lessons properly teaches the sixteen 2×2 operator CMs,
  LM versus CM, or the paper's 4×4 construction;
- episodes 2–4 currently repeat row/column indexing, 4×4 folding, dense CM, and
  packed-output language before those concepts are formally introduced.

Therefore, do a limited prerequisite cleanup when those episodes receive their
next revision:

### `why-boolean-computation`

Keep the rule and assignment-to-output mapping. Remove row/column selection,
cell decoding, packed output, and dense-matrix claims. Its final visual may fan
the truth mapping toward unnamed future representations.

### `expression-truth-function`

Keep expression trees, truth-table evaluation, and semantic equivalence. Remove
forward/back matrix lookup, `AB/CD`, dense CM, live support, and packed-vector
explanations. A one-line future-representation preview is sufficient.

### `live-support-ambient`

Teach live versus ambient support using paired truth-table rows or dependency
wires, not a CM whose definition has not yet been taught. Remove the full CM
construction and packed-output recap. If a grid remains, call it a neutral
truth layout and do not teach its indexing.

These are scope reductions, not new lessons. They eliminate repetition and
restore the intended prerequisite order.

## Neighboring-episode overlap limits

### `what-cm-does-not-claim`

- Limit the explicit-layout recap to 10–15 seconds.
- Do not reconstruct the 4×4 matrix.
- Own compactness, SAT/solver mismatch, output-contract mismatch, and scoped
  performance claims.

### `explicit-cm-vs-cm-ir`

- Do not repeat the sixteen-operator gallery or LM valuation.
- Use the already-established dense layout as one fixed icon/artifact.
- Own construction, evaluation, materialization, CM-IR, packed output, and
  benchmark-boundary distinctions.

## Terminology policy

Use these learner-facing names consistently:

- **2×2 operator CM (paper)**;
- **logical matrix (LM)**;
- **higher-dimensional valued CM (paper)**;
- **repository explicit CM layout**;
- **row-column truth matrix** as the neutral term for arbitrary rectangles;
- **CM-IR graph**;
- **packed truth output**.

Reserve **operator CM** for the elementary 2×2 objects. Larger matrices
correspond to compound Boolean functions, not necessarily to one elementary
binary operator.

Use **coordinate**, **row index**, and **column index**. Do not use **address** in
the foundational mini-arc.

## Recommended next editorial work

Before any rendering:

1. Approve or revise this three-lesson partition and terminology policy.
2. Add the two new episodes to the content Bible and series order; version the
   existing `what-is-explicit-cm` entry.
3. Add paper/implementation boundary claims and split the glossary terms.
4. Write the two new scripts and `SCRIPT_V3.md` for the current lesson.
5. Run one cross-episode repetition audit and one mathematical/visual audit.
6. Render short local chapter smokes only after content approval.

No existing master should be overwritten. Any corrected release should receive
a new versioned output path.
