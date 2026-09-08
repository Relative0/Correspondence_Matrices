# Teacher audit of the three foundational CM scripts — v4

Date: 2026-09-01  
Status: implemented as new editorial revisions; no rendering or remote work authorized

## Overall finding

The three-script partition is sound, but the previous drafts sometimes taught
through correction: “not sixteen outputs,” “not the same construction,” or
“same number, different objects” appeared before learners had a positive model
to attach those distinctions to. The v4 revisions use a consistent sequence:

1. show one concrete object;
2. state what it is and what each visible part means;
3. perform one complete worked operation;
4. ask the learner to retrieve or apply the idea;
5. state a nearby boundary only after the core model is stable.

No concept was moved to a different episode. The changes refine instructional
order, reduce narration, and make the visuals carry more of the explanation.

## Episode 1: Why there are sixteen 2×2 operator CMs

### Diagnosis

The former opening began with a gallery and the correction “not sixteen
outputs.” That made an anticipated misconception the learner's first model.
Moving conventional truth-table cards into the paper order also required an
unnecessary spatial translation before the CM had been defined.

### Implemented changes

- Replaced the contrast-first hook with a positive definition: two input
  switches produce four identified cases, and four outputs complete one CM.
- Delayed the sixteen-matrix gallery until after `2^4=16` has been derived.
- Introduced the paper's state order directly; removed the conventional-order
  rearrangement.
- Kept AND as the sole construction example. Other familiar operators are
  rapid pattern-reading examples, not additional derivations.
- Reduced the gallery's named load and made implication the single ordering
  example.
- Moved the “sixteen functions versus sixteen assignments” distinction to a
  short end-of-lesson language checkpoint.
- Simplified retrieval to one semantic prompt: agreement versus disagreement.

### Additions and subtractions

Added: an explicit definition of the complete matrix as the rule; a visible
state identity on every cell; a single-sentence count interpretation.  
Subtracted: the defensive opening, the truth-order card shuffle, the large
decision tree, repeated four-case questions, and premature paper-gallery view.

## Episode 2: From logical matrices to higher-dimensional CMs

### Diagnosis

The former draft defined an LM by contrasting it with a previous CM, then
showed both the base LM and equivalence LM in quick succession. Its account of
positive valuation (“an unnegated state is positive”) could be mistaken for a
general truth assignment rule. The larger construction also placed several
technical nouns before their visible functions were clear.

### Implemented changes

- Defined an LM positively from four expression-valued cells.
- Made `LM expressions → V_T → CM bits` the persistent causal rail.
- Reworded positive valuation narrowly and operationally: positive variable
  states receive one, complemented states zero, and expressions are evaluated
  consistently from those values.
- Separated the base-LM definition from the equivalence valuation example.
- Explained the larger construction by the job of each stage before naming
  tensor/projection notation.
- Required one false implication case to be tracked before the complete 4×4
  result appears.
- Preserved the exact paper result and its non-obvious `(Y,W)` by `(X,Z)` order.
- Kept the repository boundary at the end, after the paper mechanism is stable.

### Additions and subtractions

Added: a stage-by-stage conceptual construction, one worked 4×4 cell, and a
cell-type retrieval test.  
Subtracted: the “matrix before bits?” contrast hook, a full symbolic projection
display, repetitive LM/CM contrasts, and an early rectangular-layout preview.

## Episode 3: The repository's explicit row-column CM layout

### Diagnosis

The former opening again led with a distinction between two kinds of
“sixteen.” Displaying sixteen assignment cards before the indexing task was
defined created visual density without a focal object. The ending previewed
CM-IR, packed output, solving, and performance even though none was taught.

### Implemented changes

- Opened with one four-variable function and one tracked assignment-output
  pair, `1011 → 1`.
- Introduced `R`, `C`, and MSB-first immediately before using them.
- Placed the tracked assignment first; only then materialized the other fifteen
  cells.
- Separated coordinate decoding from the stored value both verbally and
  visually.
- Retained the useful missing-metadata test and the `1110` retrieval problem.
- Made repartitioning the main synthesis: the function/output remains fixed
  while shape and coordinate change.
- Reduced the paper/repository boundary to one precise sentence after the
  mechanism.
- Removed the CM-IR, packed-output, solver, and performance previews.

### Additions and subtractions

Added: a concrete purpose for the coordinate, a stationary invariant rail, and
a stronger coordinate-versus-value distinction.  
Subtracted: the correction-first recap, the opening card swarm, a repeated full
evaluation in retrieval narration, and unrelated next-episode icons.

## Cross-episode ownership after revision

| Episode | Owns | Briefly references | Must not teach |
|---|---|---|---|
| Operator CMs | four two-input cases; one full rule; `2^4=16`; paper state order | later four-input “sixteen” as a language check | LM construction; repository indexing |
| Logical matrices | expression-valued LM; positive valuation; paper's compound square construction | prior operator CM; later repository layout boundary | rectangular indexing API; performance |
| Repository layout | ordered `R/C`; coordinate encoding/decoding; dense repartitioning | paper construction in one boundary sentence | LM derivation; CM-IR; packed output; solvers |

## Visual adequacy verdict

Each spoken mechanism now has an observable action:

- inputs claim cells;
- outputs complete a rule;
- binary choices produce the count;
- valuation changes entry type without moving the cell;
- smaller expressions occupy declared positions before the 4×4 result;
- row and column bits visibly produce coordinates;
- repartitioning moves a card while its assignment-output identity remains fixed.

The visuals are explanatory rather than decorative. Full galleries and grids
appear only after the learner has a focal example, and no slide relies on three
static boxes or paragraph text as a substitute for the mechanism.

## Remaining human review gates

- Domain review of the positive-valuation wording and the conceptual
  tensor/projection explanation.
- Voice audition for warmth, phrasing, and mathematical symbol pronunciation.
- Low-resolution animatic review to confirm that cell labels remain readable
  and that pauses are long enough for retrieval.

These are content and production review gates, not authorization to render or
use paid infrastructure.
