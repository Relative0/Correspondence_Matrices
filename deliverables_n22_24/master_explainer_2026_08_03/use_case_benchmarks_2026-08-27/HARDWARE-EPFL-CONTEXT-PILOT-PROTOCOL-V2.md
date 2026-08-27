# EPFL real-cone partial-context pilot protocol V2

**Frozen:** 2026-08-27 after V1 failed closed during correctness preflight and before any full-run output was written.

**Scope:** hardware/EDA adjacency; real circuit expressions with generated contexts.
**Claim boundary:** this is not a real design-history trace and cannot establish deployed-workflow or domain dominance.

## Corrected artifact contract

V1 incorrectly generated the evaluator axis from `sem_support_size`. Two admitted expressions retain one syntactically present but semantically dead input, and their frozen truth artifact is defined over `synt_support_size`. V2 makes the following pre-timing correction:

- evaluation always retains every compact syntactic variable, in the same reversed order as the frozen corpus digest;
- generated contexts select and fix only variables whose original input is in `sem_support_inputs`;
- syntactically present dead variables remain free, preserving the original output width and digest convention; and
- raw output reports semantic and syntactic support and residual widths separately.

No V1 full output exists. The first all-record attempt aborted on the missing-axis correctness guard before timing rows were written.

## Question and frozen input

On all admitted expressions in the project's frozen EPFL circuit-cone corpus, does a family-compiled CM artifact evaluate repeated partial contexts more efficiently than the strongest artifact-equivalent structural-CSE-flat program, while preserving exact packed behavior?

- Corpus: `deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl`
- Expected SHA-256: `bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`
- Eligibility: all 129 records with `status == "admitted"` and `expression_v2`. No performance-based selection or post-hoc exclusions.
- The expressions are extracted from real EPFL combinational AIGs. Context assignments are generated and are not natural design traces.

## Context construction

For each expression evaluate one all-free context, then four deterministic contexts at each of 25%, 50%, and 75% of semantically active variables fixed. Variable selection and values derive from SHA-256 of the immutable record ID, fraction, and context index. Every seed and assignment is written to raw results. No context is retained or removed based on timing.

## Arms, correctness, and timing

1. `cm_family`: compile expressions in corpus order with the structural persistent cache, then lower to the existing flat packed program.
2. `cse_flat`: structural CSE plus sharing-aware associative flattening.

Both arms produce the complete packed truth vector over the same residual syntactic variable order and use the same bigint/NumPy backend policy. Equality is asserted before timing for all 1,677 expression/context rows. Each all-free result is checked against the frozen corpus digest. A mismatch aborts the run.

After prewarming, run seven measured rounds and 20 evaluations per arm per round, alternating arm order deterministically. Record median per-call nanoseconds, CM/CSE-flat ratio, operation counts, compile timings, and persistent-cache diagnostics.

Primary aggregation is the equal-weight circuit-clustered geometric mean of context ratios with a 4,000-draw fixed-seed percentile bootstrap over source circuits. Construction and warm evaluation remain separate.

## Interpretation gate

- Zero mismatches is mandatory.
- A warm-kernel follow-up signal requires circuit-weighted CM/CSE-flat geometric mean no greater than 0.95 and upper 95% circuit-bootstrap endpoint below 1.0.
- Persistent-cache hits demonstrate reusable structure only, not favorable total economics.
- A passing timing gate still means only “real-cone/generated-context adjacency.” A field claim requires a natural version/context trace and comparison with an AIG or incremental verification workflow.

The runner refuses to overwrite and writes a manifest, raw CSV, summary JSON, and checksums under `runs/hardware-epfl-context-pilot-2026-08-27/`.
