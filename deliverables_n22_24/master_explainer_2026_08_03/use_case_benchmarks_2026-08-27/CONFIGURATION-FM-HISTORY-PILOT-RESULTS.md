# Feature-model bounded-neighborhood pilot results

**Run date:** 2026-08-27  
**Executable protocol:** `CONFIGURATION-FM-HISTORY-PILOT-PROTOCOL-V2.md`  
**Pinned source:** SoftVarE-Group Feature-Model Benchmark commit `afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`

## Outcome

The complete 40-endpoint history run did not start because the source host would not deliver uncached payload objects in this environment. That attempt is retained as a void acquisition record: it produced no provenance, parsed model, correctness result, or timing.

A diagnostic cohort using all three exact official payloads that had already arrived completed successfully:

- `automotive2@2_1`: 14,010 declared variables and 237,685 native clauses;
- `FinancialServices01@2017-05-22`: 557 variables and 4,992 clauses; and
- `BusyBox@2007-05-20_17-12-43`: 439 variables and 463 clauses.

The run evaluated incidence-selected and deterministic-hash-selected eight-feature neighborhoods for each model: six rows across three real application histories. Contexts are generated around native satisfying products; they are not natural user traces. All inputs are checksummed, the satisfying products are serialized, and the run passed a separate audit that reparsed all three models and independently reconstructed every packed relation with a scalar CNF evaluator.

## Correctness

- Four-way equality (`cm_family`, `cnf_bitset`, `cse_flat`, and CaDiCaL 1.9.5): **6/6 exact**.
- Stored satisfying product present in every neighborhood: **6/6**.
- Independent audit: **passed**, with all run checksums, ratios, clustered aggregates, gates, payload checksums, witnesses, slice choices, residual clause counts, and 6 packed digests recomputed.
- Correctness gate: **passed**.

## Performance findings

Ratios below are equal-weight history-clustered geometric means; lower is better for CM.

| Comparison | CM ratio | 95% history bootstrap | Gate | Result |
|---|---:|---:|---|---|
| Specialized packed CNF | 2.1970 | [1.9773, 2.5758] | <= 0.95 and upper < 1 | **Fail** |
| Structural-CSE flat | 0.5618 | [0.4550, 0.6541] | secondary only | CM about **1.78x faster** |
| 256 native CaDiCaL checks | 0.0005376 | [0.0001724, 0.0009749] | <= 0.80 and upper < 1 | **Pass** |

The CaDiCaL gap is roughly 1,860x for this exhaustive 256-assignment batch, but it does **not** show general SAT dominance. The specialized direct-CNF evaluator is the more informative artifact-equivalent comparator, and it was about 2.20x faster than CM overall.

There is one important morphology signal. On the automotive incidence slice, conditioning left 628 clauses / 644 literals. CM used 45 flat instructions and 87 word operations versus CSE's 75 / 278; it was 28.5% faster than the specialized CNF arm and 2.71x faster than CSE. On sparse residuals (7--35 clauses in four of the other rows), direct CNF usually won decisively. This suggests a testable crossover based on residual constraint density and canonical operation reduction, not blanket CM superiority.

## Construction and reuse

Family-mode CM compilation took 1.4456x the total independently fresh CM compilation time in this diagnostic cohort. Persistent hits were `1` for automotive and `0` for the other two histories. The family-construction gate failed.

This cohort has only one version from each history, so it cannot answer the central adjacent-version reuse question. The single automotive hit came from compiling its second slice, not a later product-family release. It is evidence that the cache functions, not evidence of cross-version economics.

## Interpretation and next experiment

The result narrows the useful hypothesis:

1. CMs are promising for dense conditioned neighborhoods where canonicalization removes substantial repeated Boolean work.
2. A direct packed CNF scan is the correct baseline and usually wins on sparse residuals.
3. Exhaustive local batches can strongly beat repeated native SAT calls, but that advantage belongs partly to batch-explicit semantics and must not be attributed solely to CMs.
4. No cross-version reuse claim is supported yet.

The next run should complete the frozen 40-endpoint cohort from a predownloaded or archived copy of the same pinned commit, then stratify the preregistered result by residual clauses, literals, and CM/CSE operation reduction. Thresholds or routing policies must be learned only after the complete cohort, not from these three favorable/unfavorable examples. A later natural-session trace should test arbitrary partial assignments and incremental SAT rather than fixed local neighborhoods.

## Artifacts

- Completed diagnostic cohort: `runs/configuration-fm-history-pilot-real3-2026-08-27/`
- Void full-cohort acquisition record: `runs/configuration-fm-history-pilot-2026-08-27/`
- Runner: `cm_feature_model_history_pilot.py`
- Independent audit: `cm_feature_model_history_pilot_audit.py`
- Focused regression tests: `tests/test_cm_feature_model_history_pilot.py`
