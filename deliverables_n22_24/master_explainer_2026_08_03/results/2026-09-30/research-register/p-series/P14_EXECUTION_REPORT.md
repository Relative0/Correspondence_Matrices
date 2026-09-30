# P14-PY0 prospective execution report

## Decision

**NO-GO for production rollout and NO-GO for P14-PY1 replication of the unchanged exact dispatcher.**

Correctness passed, but the primary performance gate did not. Exact dispatch (E) was about 3.9% faster than the minimal P13 observer (F) on both corpora, yet the natural-corpus simultaneous interval narrowly included parity. More decisively, E was slower than direct lowering (D): 5.1% on synthetic cases and 6.1% on natural cones by the preregistered case-balanced geometric mean.

## Frozen scope and execution

- 384 synthetic cases: 12 families x 32 sealed seeds.
- 107 natural cones from 14 previously uninspected EPFL design families; the frozen snapshot contained 14 eligible families after excluding the six historical families, below the draft target of 16.
- Three fresh sequential timing workers, three measured blocks after one warmup, recipe and compiler-IR endpoints.
- 51,102 measured timing rows and 2,455 separate peak-memory observations.
- Worker wall times: 4,960.8 s, 4,416.1 s, and 3,657.7 s.
- No paid compute. Total P14 artifact size was about 160 MB, below the 4 GiB cap.

## Correctness gate

**PASS.** All seven implementations produced equal ANF outputs and matched truth behavior across all 491 sealed cases and 512 fresh targeted cases. The gate also passed 332 invariants, 1,000 historical fuzz cases, 2,000 adversarial DAGs, 14,708 integer-boundary checks, 4,040 targeted checks, and 768 exhaustive token compositions.

Exact dispatch selected folding for 5/384 synthetic cases and 0/107 natural cones. All five selected cases were in `encoding_variants`; their E/D case ratios ranged from 0.075 to 0.389, and folding reduced pair-term counts from 8,496-61,184 to 64-128. The optimization is valuable when triggered, but the sealed workload exposed very few profitable opportunities.

## Primary recipe endpoint

Ratios below 1 favor the numerator. The 98.75% intervals are the frozen Bonferroni simultaneous bounds over the four confirmatory E/F and E/D comparisons.

| Corpus | Comparison | Geomean | 95% CI | Simultaneous 98.75% CI | Wins | Gate |
|---|---:|---:|---:|---:|---:|---:|
| Synthetic | E/F | 0.9606 | 0.9489--0.9770 | 0.9455--0.9811 | 297/384 | Pass |
| Synthetic | E/D | 1.0508 | 0.9887--1.0971 | 0.9683--1.1075 | 76/384 | Fail |
| Natural | E/F | 0.9610 | 0.9475--0.9931 | 0.9411--1.0001 | 76/107 | Fail (borderline) |
| Natural | E/D | 1.0607 | 1.0258--1.0843 | 1.0176--1.0927 | 21/107 | Fail |

The synthetic E/D aggregate-time ratio was 0.9899, while its case-balanced geomean was 1.0508. This divergence means a few expensive cases dominate aggregate time; the preregistered case-balanced result controls the decision.

## Diagnostic comparators

Always-fold (A) and the generic optimizer (G) were not confirmatory arms. On natural recipe cases they were substantially slower than D: A/D 1.7364 and G/D 1.7343. On synthetic cases their geomeans were below 1, but their medians were above 1 and their simultaneous intervals included parity, showing strong family heterogeneity.

Canonical always-fold versus canonical direct had geomean 0.5921, median 1.2439, and simultaneous interval 0.3363--1.0712. The wide interval and opposing geomean/median again show that a small set of expensive cases dominates total benefit.

At the compiler-IR endpoint, E/F was 0.9652 synthetic and 0.9681 natural, but E/D was 1.7469 synthetic and 1.9595 natural. Observer construction and cloning therefore dominate when recipe construction is excluded from D.

## Peak-memory observations

These are descriptive `tracemalloc` peaks from a separate pass, not RSS measurements or confirmatory intervals. Maximum traced peak was 27,487,176 bytes.

| Corpus | Comparison | Peak-memory geomean ratio | Median ratio | Wins |
|---|---:|---:|---:|---:|
| Synthetic | E/F | 0.9718 | 0.9789 | 373/384 |
| Synthetic | E/D | 1.0931 | 1.0793 | 5/384 |
| Natural | E/F | 0.9729 | 0.9753 | 98/107 |
| Natural | E/D | 1.0065 | 1.0067 | 22/107 |

## Deviations and amendments

1. The local design was frozen at three workers and 10 ms target batches with a 40 ms predicted slow-arm cap, rather than the draft's 30 workers and 100 ms batches. Close effects are therefore treated as inconclusive.
2. Before timing, the correctness harness was amended to enforce the declared 60-second limit per arm instead of incorrectly applying it to the aggregate of seven arms plus oracle work. The original freeze is preserved byte-for-byte.
3. After worker 1 completed, the user authorized extending total and remaining-worker wall caps to preserve the run. No arm-level values had been inspected; holdouts, repetitions, comparisons, and analysis rules were unchanged.
4. Before analysis, an execution-only analyzer copy pre-indexed timing rows instead of rescanning the full table inside every bootstrap draw. Seed, draw order, statistic, intervals, and report formulas were unchanged. The frozen analyzer is preserved.

## Artifacts

- `P14_RESULTS.json`: complete timing and operation-count results.
- `P14_CASE_RATIOS.csv`: case-level timing ratios.
- `correctness_results.json`: correctness gate and case metadata.
- `memory_results.json` and `P14_MEMORY_SUMMARY.json`: raw and summarized peak-memory observations.
- `P14_FREEZE.json` and `P14_FREEZE_V1_ORIGINAL.json`: amended and original freeze records.
- `P14_BUDGET_EXTENSION.json` and `P14_ANALYSIS_EXECUTION_AMENDMENT.json`: transparent execution amendments.
- `P14_ARTIFACT_MANIFEST.json`: SHA-256 checksums and sizes.

The unchanged exact dispatcher should not advance to production or independent P14-PY1 confirmation. A future experiment should first redesign or remove observer overhead and then preregister a new gate; the five selected synthetic cases show that the folding mechanism itself can be highly effective when a profitable opportunity is present.
