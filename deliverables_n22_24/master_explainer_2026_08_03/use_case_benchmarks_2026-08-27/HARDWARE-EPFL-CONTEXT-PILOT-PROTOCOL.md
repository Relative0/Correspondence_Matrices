# EPFL real-cone partial-context pilot protocol

**Status:** VOID after fail-closed preflight; superseded by V2.

**Frozen:** 2026-08-27, before this pilot was executed.

**Scope:** hardware/EDA adjacency; real circuit expressions with generated contexts.
**Claim boundary:** this is not a real design-history trace and cannot establish deployed-workflow or domain dominance.

The four-record smoke happened to contain equal syntactic and semantic support. The all-record preflight then encountered `x14` on a cone with 15 syntactic inputs but 14 semantically active inputs and aborted before creating an output directory. This protocol incorrectly specified semantic-support width even though the frozen truth artifact retains syntactically present dead axes. No timing result from the failed run is retained. V2 corrects the artifact contract without inspecting any completed full-run timing.

## Question

On all admitted expressions in the project's frozen EPFL circuit-cone corpus, does a family-compiled CM artifact evaluate repeated partial contexts more efficiently than the strongest artifact-equivalent structural-CSE-flat program, while preserving exact packed behavior?

## Frozen input

- File: `deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl`
- Expected SHA-256: `bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`
- Eligibility: every record with `status == "admitted"` and an `expression_v2`; expected count 129. No performance-based selection or post-hoc exclusions.
- The expressions are extracted from real EPFL combinational AIGs. Context assignments are generated for this pilot and are not natural design traces.

## Context construction

For every expression, use its complete semantic support in the same reversed variable order as the frozen truth digest. Evaluate:

- one all-free context;
- four deterministic contexts with 25% of variables fixed;
- four deterministic contexts with 50% fixed; and
- four deterministic contexts with 75% fixed.

Variable selection and Boolean values are derived from SHA-256 of the immutable record ID, fraction, and context index. Every seed/input is written to raw results. No context is retained or removed based on timing.

## Arms and artifact contract

1. `cm_family`: compile expressions in corpus order with the process-local structural persistent cache enabled, then lower the resulting CM node to the existing flat packed program.
2. `cse_flat`: compile each expression with structural CSE plus sharing-aware associative flattening.

Both arms produce the complete packed truth vector over the same residual free-variable order and use the same bigint/NumPy backend policy. Packed equality is asserted before timing for every expression/context. The all-free output is also checked against the corpus's frozen truth SHA-256. Any mismatch aborts the run; it is never converted into a skipped timing row.

## Timing and reporting

- Prewarm each arm/context once after construction and correctness checks.
- Seven measured rounds, 20 evaluations per arm per round.
- Alternate arm order by a deterministic parity of formula, context, and round.
- Record median nanoseconds per call, CM/CSE-flat ratio, program operation counts, compile timings, and persistent-cache hit/miss diagnostics.
- Primary aggregation: equal-weight circuit-clustered geometric mean of CM/CSE-flat context ratios with a 4,000-draw fixed-seed percentile bootstrap over source circuits.
- Also report row-weighted results and results by fixed fraction. Do not pool construction time with warm evaluation.

## Interpretation gate

- Zero correctness mismatches is mandatory.
- A warm-kernel follow-up signal requires circuit-weighted CM/CSE-flat geometric mean no greater than 0.95 and an upper 95% circuit-bootstrap endpoint below 1.0.
- Persistent-cache hits support only the existence of cross-expression reusable structure; they do not prove favorable total economics.
- Even if the timing gate passes, the result remains “real-cone/generated-context adjacency.” A field claim still requires a natural version/context trace and comparison with an AIG/incremental verification workflow.

## Outputs

The runner refuses to overwrite its output directory and writes a run manifest, raw CSV, summary JSON, and SHA-256 checksum file under `runs/hardware-epfl-context-pilot-2026-08-27/`.
