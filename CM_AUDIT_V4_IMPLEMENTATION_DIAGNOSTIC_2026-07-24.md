# Audit V4 implementation diagnostic inventory

Date: 2026-07-24  
Starting commit: `6419b21`  
Baseline: system Python 3.10.11, 159 tests passed

## Confirmed implementation targets

1. **Aggregation:** `cm_bench.py` and workload-specific aggregators use
   `dropna().median()` independently per column. Derived comparisons are normally
   ratios of those independent medians. Decline counts exist for selected CM
   paths, but there is no authoritative matched-observation status model covering
   refused, timeout, error, and OOM outcomes across both competitors.
2. **CUDD order search:** `run_robdd_dd_backend` builds each seeded order but
   returns only the selected manager/root plus min/median/max scalars. Selection
   is smallest final node count, then build time. Order generation and total
   search wall time are not persisted. `robdd_best_time_s` means minimum build
   interval, not the selected build or all-in best-of-k cost.
3. **Global evaluator defaults:** `cm_ir` owns mutable process globals for flat
   and words evaluation. CLI setup changes them without restoring prior values.
   Normal one-shot CLI use is safe; embedded/reentrant use can leak state.
4. **Engine selection:** ordinary, partial, and family controls independently
   reproduce words/flat/recursive precedence and provenance. Remote CM passes a
   boolean rather than a selected engine. The duplication already caused the
   fixed partial/family asymmetry.
5. **Timing schema:** timings are flat dictionary fields. Build, cached execute,
   extraction, correctness, remote transport, and BDD search intervals can be
   divided without a shared artifact/timing-type validator.
6. **Charts:** both HTML pages contain hand-maintained JavaScript arrays. V4
   direct extraction currently matches source CSV rounding, but provenance is
   prose rather than machine-validated generated metadata.
7. **Corpus:** expression JSON serialization and formula hashes exist. The V4
   corpus is immutable by content hash, but standard benchmark runners still
   regenerate formulas from seeds and summaries do not reject mixed corpus
   hashes.
8. **Binding/wrapper cost:** fixed bindings are repeatedly normalized as string
   dictionaries and sorted into cache keys. Audit V3/V4 profiling isolates the
   nominal-n drift primarily to this preparation, while small-live-k wrapper
   bookkeeping dominates the kernel.

## Compatibility constraints

- Historical CSVs and reports remain read-only records.
- New fields are authoritative; deprecated fields remain readable with their old
  meanings and are never silently reinterpreted.
- Explicit CUDD continues to fail closed.
- The words crossover below/at six live variables and the 16/17 explicit-output
  guard remain unchanged.
- CUDD symbolic build, query, and packed extraction remain distinct artifacts.

## Phased implementation map

- Add a reusable paired-comparison aggregator and integrate authoritative paired
  fields into new summaries without deleting historical columns.
- Extend the ROBDD result with per-order trials, objective, deterministic
  selection, order-generation/search/all-in timings, and compatibility aliases.
- Add scoped evaluation defaults and a central raw-expression engine policy.
- Add validated timing descriptors and corpus provenance helpers.
- Generate versioned chart-data metadata from validated sources and add a drift
  check; do not rewrite old measurements.
- Profile binding preparation before changing its representation, then benchmark
  any cache/key or prepared-evaluation change symmetrically.
