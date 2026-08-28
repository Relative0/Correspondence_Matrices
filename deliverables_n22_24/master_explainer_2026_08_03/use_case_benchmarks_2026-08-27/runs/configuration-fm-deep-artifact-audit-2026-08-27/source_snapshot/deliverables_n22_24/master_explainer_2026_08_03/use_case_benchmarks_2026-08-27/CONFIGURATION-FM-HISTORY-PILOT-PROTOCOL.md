# Real feature-model history / bounded-neighborhood pilot protocol

**Frozen:** 2026-08-27, before acquiring or parsing the benchmark payload and before implementing or timing the runner.

**Scope:** configuration systems and software product families; real versioned feature-model constraints with generated, correctness-gated local product neighborhoods.

**Claim boundary:** this pilot does not represent unrestricted partial-configuration analysis. It fixes all variables outside a small slice to values from a satisfying product and exhaustively scores the slice. It can test exact batch-neighborhood evaluation and cross-version artifact reuse, but cannot establish dominance over incremental SAT for arbitrary partial assignments, explanations, counting, or large projected configuration spaces.

## Question and source

On an ordinally selected, complete set of version transitions from the curated Feature-Model Benchmark histories, can a family-compiled CM artifact evaluate exact bounded product neighborhoods faster or with more reusable construction than strong artifact-equivalent baselines, while preserving every bit of the native CNF relation?

- Source: `https://github.com/SoftVarE-Group/feature-model-benchmark`, branch `master`.
- The exact acquired commit, license checksum, payload checksums, and inventory must be recorded before model parsing.
- Acquisition is read-only. No source script or other third-party code will be executed.
- The source repository is an input cache and is not part of the project commit. A small provenance manifest and experiment outputs are project artifacts.

## Frozen corpus selection

Use `statistics/Complete.csv` and source metadata to identify every history. For each history, order revisions by the corpus's explicit history/version metadata; filenames are only a fallback and must be reported if used. Select these adjacent transitions:

1. the first transition;
2. the transition whose later-version ordinal is nearest the history midpoint; and
3. the last transition.

Deduplicate a transition if a short history maps two rules to the same pair. Admit both endpoints of every selected transition when a DIMACS payload is present, the header and clause counts parse exactly, literals are within the declared variable range, and CaDiCaL 1.9.5 reports the model satisfiable. Exclude only with a recorded reason; never use timing or CM behavior for selection. Run the complete admitted set.

## Frozen neighborhoods

For each admitted model, obtain one deterministic CaDiCaL satisfying product. Construct two eight-variable slices without looking at performance:

- `incidence`: the eight original variables with greatest clause incidence, breaking ties by variable number;
- `hash`: the first eight variables after sorting by SHA-256 of `<model-id>|<variable>`.

If a model has fewer than eight declared variables, it is ineligible. Fix every variable outside the slice to its satisfying-product value. The required output is the packed truth vector, in ascending assignment-index order with the first slice variable as the least-significant assignment bit, for all `2^8 = 256` slice assignments. This is a local product neighborhood, not existential projection over the fixed variables.

## Arms

1. `cm_family`: translate the DIMACS CNF into the project's Boolean expression IR; compile models in history/version order using the existing structural persistent CM cache; lower to the existing packed flat evaluator.
2. `cnf_bitset`: a CNF-specific packed evaluator that applies each clause directly to the same 256-bit assignment axis. This is the strongest artifact-equivalent specialized baseline.
3. `cse_flat`: compile the identical Boolean expression with structural CSE and sharing-aware flattening, then use the same packed evaluator as CM.
4. `cadical195`: keep one native PySAT CaDiCaL 1.9.5 solver per model and solve all 256 complete assignments through assumptions, packing the Boolean results into the same artifact.

Construction, first evaluation, and prewarmed evaluation are reported separately. Include solver construction in cold CaDiCaL results, but not in warm results. Record expression/flat-program operation counts, source clause counts, persistent-cache hits/misses, memory-relevant artifact sizes, and transition overlap statistics.

## Correctness and timing

- Before timing, assert bit-for-bit equality of all four arms for every admitted model/slice.
- Assert the satisfying-product assignment is present in both slice vectors.
- Independently reparse every DIMACS payload and spot-check deterministic assignment indices with a separate scalar clause evaluator.
- Any mismatch aborts the run before performance output is accepted.
- Prewarm each arm, then take seven measured rounds, alternating arm order deterministically. Use a calibrated batch for packed evaluators and one complete 256-query batch for CaDiCaL.
- Primary warm statistic: history-clustered geometric mean of `cm_family / cnf_bitset` with a fixed-seed, 4,000-draw percentile bootstrap over histories.
- Secondary statistics: CM/CSE-flat, CM/CaDiCaL, compile/construction ratios, per-slice results, cross-version persistent reuse, and end-to-end crossover session counts.

## Interpretation gates

- Zero correctness mismatches is mandatory.
- A specialized warm-kernel advantage requires the primary CM/CNF-bitset geometric mean to be at most `0.95` and its upper 95% history-bootstrap endpoint below `1.0`.
- An incumbent batch advantage requires CM/CaDiCaL geometric mean at most `0.80` with upper endpoint below `1.0`.
- A family-construction advantage requires total family-compiled CM construction time at least 10% below independently fresh CM construction for the same models, with nonzero persistent hits in every multi-version history.
- Cache hits alone are evidence of structural reuse, not favorable economics. A passing bounded-neighborhood gate must not be generalized to arbitrary SAT, projected model counting, unrestricted feature-model analysis, or natural user sessions.

The runner must refuse to overwrite and write a manifest, inventory, raw CSV, summary JSON, independent audit, and SHA-256 checksums under a dated run directory.
