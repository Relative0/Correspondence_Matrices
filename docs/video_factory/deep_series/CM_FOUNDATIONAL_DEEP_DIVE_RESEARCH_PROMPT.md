# CM foundational-definition and episode-5 correctness audit — research handoff prompt

Date: 2026-09-01  
Purpose: independent deep research before revising episode 5  
Default authorization: read-only research and one report; no production work

## Copy-paste prompt

```text
Act as an independent research mathematician, propositional-logic specialist,
scientific editor, and software/benchmark auditor. Your task is to determine
what a Correspondence Matrix (CM) actually is in the originating paper, how the
current repository implements and benchmarks CM-related artifacts, and whether
every learner-facing statement in the proposed episode-5 script is correct,
properly scoped, and understandable.

Do not assume the current script, content Bible, claim registry, source code,
paper, or benchmark website is correct merely because it is authoritative in
one layer of the project. Reconcile them. When they differ, describe the
difference precisely and recommend terminology that prevents the layers from
being conflated.

WORKSPACE

C:\Users\brian\Documents\CM_Computation

PRIMARY SCRIPT TO AUDIT

docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/SCRIPT_V2.md

RELATED V2 PROPOSAL ARTIFACTS

- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/PANEL_AUDIT.md
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/VISUAL_AND_PRODUCTION_SPEC_V2.md
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/CLAIM_REGISTRY_DELTA_V2.json
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/CONTENT_BIBLE_DELTA_V2.json
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/REVIEW_MANIFEST_V2.json

MANDATORY EXTERNAL PRIMARY SOURCES

1. Benchmarked results and evidence boundaries:
   https://relative0.github.io/Correspondence_Matrices/expert.html

2. Originating CM paper:
   https://www.b-theory.com/CorrespondenceMatrices.pdf

Read the entire relevant paper, not only its abstract. At minimum inspect and
cite exact page/section/equation/figure locations for:

- §2.2, bra-kets and logical state vectors;
- §3, especially the definition and construction of 2×2 correspondence
  matrices;
- Figure 1, the set of sixteen distinct 2×2 correspondence matrices;
- the statement that CMs are truth tables “rolled up,” including its ordering
  qualification;
- §4, logical matrices (LMs), measurement, and the statement that a CM is a
  positive valuation of a logical matrix;
- §5.1, construction and valuation of 4×4 matrices for four-variable logical
  expressions;
- §5.2, higher-dimensional matrices and the stated 2^n × 2^n construction for
  2n logical sub-expressions;
- §5.3 and §5.4, what computations are actually performed with these matrices;
- the conclusion's claims about transformations, composition, decomposition,
  quotienting, linearity, and measurement.

Use additional primary literature or authoritative mathematical references
where needed to check standard Boolean-function counts, truth-table semantics,
ANF/XOR decomposition, tensor products, matrix operations, and benchmarking
methodology. Clearly separate standard external facts from claims novel to this
paper. Determine and report the paper's publication status, date/version, and
whether it appears peer reviewed; do not infer validation from hosting alone.

MANDATORY REPOSITORY SOURCES

Read the relevant code rather than relying only on prose:

- cm_build.py, especially compile_expr_to_cm and eval_cm_boolean
- cm_ir.py, especially compile_expr_to_cm_ir, materialize_cm, output alignment,
  and final reshape behavior
- cm_exprlib.py
- the relevant CM/CSE/CSE-flat/BitSet benchmark drivers and contracts found by
  tracing the evidence paths in source_registry.json, claim_registry.json, and
  the benchmark reports
- docs/video_factory/source_registry.json
- docs/video_factory/claim_registry.json
- docs/video_factory/glossary.json
- docs/video_factory/deep_series/EPISODE_CONTENT_BIBLE.md
- docs/video_factory/deep_series/episode_content_bible.json
- docs/video_factory/deep_series/coverage_matrix.json
- docs/video_factory/RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md
- docs/video_factory/episodes/cm-flagship-representation-to-evidence-v1/SCRIPT.md
- docs/video_factory/deep_series/FIRST_FIVE_RELEASE_REPORT.md

Audit what the preceding lessons actually teach, not only what their titles
suggest:

- docs/video_factory/deep_series/episodes/why-boolean-computation/script.md
- docs/video_factory/deep_series/episodes/expression-truth-function/script.md
- docs/video_factory/deep_series/episodes/live-support-ambient/script.md
- their storyboards, claim maps, final captions, and produced masters when useful

Also inspect the planned neighboring lessons:

- docs/video_factory/deep_series/episodes/what-cm-does-not-claim
- docs/video_factory/deep_series/episodes/explicit-cm-vs-cm-ir
- docs/video_factory/deep_series/episodes/cm-ir-nodes-sharing
- docs/video_factory/deep_series/episodes/packed-words-selection

Read-only first. Preserve unrelated dirty work. Do not modify the current
script, content Bible, registries, release media, benchmarks, or evidence files.
Do not rerun benchmarks. Do not call RunPod or any paid/remote service. Do not
publish, commit, or push. You may write one new Markdown report if the user has
provided a writable workspace; otherwise return the complete report in chat.

THE CENTRAL PROBLEM TO RESOLVE

The proposed script opens with:

“These are sixteen answers from one Boolean function. Here they are as a list.
Now as a four-by-four grid. And now as two rows of eight. None of the answers
changed. Only their addresses did. That two-dimensional layout is an explicit
correspondence matrix.”

The user questions this. Their understanding is that there are sixteen distinct
2×2 Boolean correspondence matrices. The paper's Figure 1 indeed presents the
sixteen possible 2×2 binary matrices corresponding to the sixteen binary
Boolean operators. The script instead appears to count the sixteen input
assignments—and therefore sixteen output bits—of one four-variable Boolean
function.

Do not choose one interpretation prematurely. Determine exactly:

1. What objects the paper calls CMs at each dimensionality.
2. Why there are sixteen 2×2 binary CMs.
3. Whether a four-variable function's sixteen truth outputs, arranged as one
   4×4 array, are properly called one higher-dimensional CM under the paper.
4. Whether the repository's “explicit dense CM” is identical to, a
   specialization of, a generalization of, an engineering analogue of, or a
   terminological departure from the paper's CM/LM construction.
5. Whether arbitrary 2×8 and 8×2 arrangements are CMs under the paper, are only
   supported by the repository's arbitrary R/C output contract, or are merely
   reshaped truth tables that should not be called CMs without qualification.
6. Whether episode 5 must first teach the sixteen 2×2 operator CMs before it
   teaches a 4×4 or higher-dimensional explicit CM.
7. Whether this should be one episode, two episodes, or a different sequence.

PLAIN-LANGUAGE QUESTION: “ONLY THEIR ADDRESSES DID”

Explain this phrase twice:

- first for a learner with no programming background;
- then technically in terms of truth assignments, declared variable order,
  row/column indices, coordinates, and array layout.

Determine whether “address” is mathematically appropriate, merely a useful
computer-memory analogy, or misleading in the CM paper's bra-ket/measurement
framework. Compare alternatives such as “position,” “coordinate,” “index,”
“basis location,” and “matrix entry.” Recommend the best wording and the visual
needed to make it unambiguous.

CONCEPT TAXONOMY — DO NOT CONFLATE THESE

Construct a precise comparison table for at least:

1. A truth assignment.
2. A Boolean output or truth value.
3. A complete truth table for a Boolean function.
4. One of the sixteen binary Boolean operators.
5. One 2×2 CM from Figure 1 of the paper.
6. A 2×2 logical matrix (LM) whose entries are logical expressions.
7. A CM as the positive valuation of an LM.
8. A higher-dimensional 4×4 LM and its valued 4×4 CM in §5.
9. The paper's 2^n × 2^n higher-dimensional construction.
10. The repository's explicit dense output returned by compile_expr_to_cm.
11. The repository's CM-IR graph.
12. A packed truth vector.
13. The object produced and timed by the bare “CM kernel.”
14. The public CM wrapper and its preparation/materialization boundary.

For every row state:

- definition;
- mathematical shape/type;
- what its entries mean;
- how variable/basis ordering affects it;
- where it exists in the paper;
- where it exists in code;
- whether it is part of the benchmarked artifact;
- safe learner-facing name;
- names that would be misleading.

STATEMENT-BY-STATEMENT SCRIPT AUDIT

Audit every voiceover sentence and every factual visual direction in
SCRIPT_V2.md. Do not sample. Give each statement a stable ID based on its
timestamp and sequence.

For each statement provide:

- exact statement or a short identifying excerpt;
- classification:
  CONFIRMED, CONFIRMED ONLY FOR REPOSITORY IMPLEMENTATION,
  CONFIRMED ONLY UNDER STATED CONDITIONS, AMBIGUOUS, UNSUPPORTED,
  MISLEADING, or INCORRECT;
- the object actually being discussed;
- assumptions and necessary qualifications;
- paper locator(s);
- code locator(s);
- benchmark/evidence locator(s), if relevant;
- standard external source(s), if relevant;
- a plain-language explanation;
- corrected learner-facing wording;
- KEEP, REWRITE, MOVE, SPLIT, or CUT recommendation.

Give special scrutiny to all of these claims:

- “sixteen answers from one Boolean function”;
- list → 4×4 → 2×8 as representations of the “same” object;
- “Only their addresses changed”;
- “That two-dimensional layout is an explicit CM”;
- ordered row and column variable sets;
- assignment bits “choosing” a row and a column;
- a cell storing the function's exact output;
- “explicit” and “dense” meaning every cell is present;
- four variables implying sixteen cells;
- “truth table fold” and “layout, not meaning”;
- the forward and reverse coordinate examples;
- whether coordinates identify an assignment and under what fixed context;
- “the split is part of the matrix's identity”;
- the 2×8 / 4×4 / 8×2 comparison;
- the proposed 2^|R| × 2^|C| dimension rule versus the paper's
  2^n × 2^n formulation;
- “the word matrix does not imply matrix multiplication,” given that the paper
  explicitly develops matrix operations, transformations, bra-matrix-ket
  computation, and tensor products;
- claims that CM is not automatically compact, solver-like, or fast;
- the closing distinction among split, coordinates, assignment, and output.

Independently recompute every Boolean example and matrix shown in the script.
For F=(A AND B) XOR (C OR D), verify the truth ordering, the 4×4 matrix, and
the `1011`, `1101`, and `1110` lookups. Then determine whether this example is
representative of the paper's motivating CM construction or only convenient for
the repository's dense truth-layout API.

BENCHMARK AUDIT

Use the supplied expert page and its linked provenance, plus local retained
evidence. Do not rerun anything. Verify what each reported arm constructs,
stores, evaluates, and returns. In particular, determine whether the timed CM
kernel operates on:

- paper-style 2×2 operator CMs;
- higher-dimensional explicit matrices;
- CM-IR nodes;
- packed/full truth vectors;
- or some pipeline combining these.

Reproduce the published summary numbers from retained raw rows only when the
page says a build/reaggregation script already does this without rerunning a
benchmark. Otherwise report them as cited measurements. Check at least:

- local, EPFL, and Linux-pod CM-kernel comparisons against plain structural
  CSE;
- B1/E3 and EPFL parity evidence against CSE-flat;
- the later B2/B4 V3 workload-specific CM-versus-CSE-flat result;
- wrapper-versus-BitSet results;
- construction versus evaluation/extraction boundaries;
- break-even and never-break-even populations;
- exact-output gates;
- live_k versus ambient namespace;
- guard/refusal behavior;
- every scope limit and open discrepancy stated on the page.

For every benchmark conclusion, state:

- numerator and denominator;
- whether lower or higher is favorable;
- workload/corpus;
- machine/platform;
- schedule;
- aggregation and clustering unit;
- preparation/kernel/wrapper/extraction boundary;
- exact output contract;
- uncertainty interval when present;
- what can be claimed;
- what cannot be claimed.

The report must explicitly answer: do these benchmark results validate the
paper's theoretical CM claims, validate only this repository implementation,
or test a narrower/different engineering artifact?

PRIOR-VIDEO AND CURRICULUM AUDIT

Check whether episodes 2–4 actually establish the prerequisites needed for the
current script. Do not credit a prerequisite unless it is clearly and correctly
taught in narration and imagery.

Determine whether viewers have already learned:

- why a four-variable Boolean function has sixteen assignments;
- the difference between an assignment and an output;
- the sixteen possible binary Boolean operators;
- the sixteen 2×2 operator CMs;
- bra/ket state vectors or an accessible non-bra/ket equivalent;
- the difference between an LM and a CM;
- how a 4×4 higher-dimensional CM is derived;
- row/column ordering and indexing;
- why the repository calls its output an “explicit dense CM.”

Recommend the minimum corrected curriculum sequence. Consider at least these
options:

A. One revised episode that carefully distinguishes both meanings of sixteen.
B. A foundational episode on the sixteen 2×2 operator CMs followed by a
   separate episode on higher-dimensional/explicit CMs.
C. A paper-first episode, an implementation-mapping episode, and then a
   benchmark-artifact episode.

For the recommended option, give titles, theses, owned concepts, prerequisites,
exclusions, worked examples, and the handoff sentence between episodes. State
which current episode IDs can remain and which new IDs or versioned Bible deltas
would be required.

REQUIRED REPORT STRUCTURE

Return one self-contained Markdown report with:

1. Executive verdict.
2. Direct answers to the user's “sixteen” and “addresses” questions.
3. Publication/source-quality assessment.
4. CM/LM/implementation/benchmark concept taxonomy.
5. Paper reconstruction, from 2×2 CMs through higher dimensions.
6. Paper-versus-code semantic mapping.
7. Complete statement-by-statement SCRIPT_V2 audit.
8. Independent Boolean/matrix recomputation.
9. Benchmark result and scope audit.
10. Prior-video prerequisite audit.
11. Recommended episode partition and curriculum order.
12. A corrected outline for episode 5; do not silently replace the script.
13. Exact proposed changes to claims, glossary, and content Bible.
14. Unresolved questions that require the author's judgment.
15. Source list with direct links and precise locators.

Lead with plain language, then give the technical derivation. Use equations and
small matrices where they clarify the distinction. Quote sources sparingly and
within copyright limits. Label inference as inference. If a source conflicts
with another source, preserve the conflict instead of averaging it away.

DELIVERABLE PATH

If writing to the workspace, create only:

docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/FOUNDATIONAL_CM_RESEARCH_REPORT.md

Do not edit any other file. In the final response, include the report's absolute
path, SHA-256, a five-bullet verdict, and any blockers. The report should be
complete enough to paste back into the original video-production task without
the original agent needing to repeat the research.

SUCCESS CONDITION

The audit succeeds only if it makes it impossible for a future script to confuse
sixteen truth assignments, sixteen output bits, sixteen 2×2 operator CMs, one
4×4 higher-dimensional CM, an LM, CM-IR, a packed truth vector, and the artifact
actually timed in the benchmarks.
```
