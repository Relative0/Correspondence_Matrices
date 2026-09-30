# Supplementary measured diagnostics

These experiments ran after all principal trials and baseline selection were final. They do not tune objectives, change the primary metric, or rescue the failed algorithmic gate.

## Actual persistent versus fresh SAT

Twenty training instances, three repetitions and three implementations yielded 180 complete runs and 14,220 independently checked cut answers, with zero discrepancies/timeouts. All cuts have the same deterministic order. The persistent/fresh-same-base comparison uses byte-identical controlled clauses; the third method constructs the original cut-specific Phase 3 formula. The controlled diagnostic deliberately uses the frozen Phase 4 encoder, without the new optional equality-support gates.

| SAT workload | Runs | Median end-to-end ms | Median solve ms | Total conflicts | Total propagations |
|---|---:|---:|---:|---:|---:|
| persistent_controlled | 60 | 2.501 | 1.143 | 4545 | 483630 |
| fresh_solver_same_base | 60 | 26.476 | 2.045 | 16134 | 761217 |
| fresh_phase3_per_cut | 60 | 26.902 | 1.388 | 16821 | 571269 |


On paired instance medians, persistent/fresh-same-base geometric ratio is **0.124832**, and persistent/fresh-Phase3 is **0.106228**. This is real timing evidence for this small fixed-cut workload, including setup and encoding costs. It is not an encoding-size ratio. Repeated solver setup dominates much of the gap; neither retained learned-clause counts nor a causal attribution of all savings to learning is measured. Persistence is established prior art and already common to every principal method, so this result does not establish a new vtree adaptation benefit. Raw per-query counters/times and source hashes are preserved in data/sat_reuse_results.json.

## Move-by-move objective relation

The diagnostic maps all **10,440** evaluated move occurrences onto **1,020** distinct input/tree-pair moves and **174** distinct certified-partition residual measurements. Every measurement completed and agreed with independent semantic and simultaneous truth. One fresh process measures each unique input/partition once, then the measurement is explicitly reused in every matching move record. This is exploratory profiling, not repeated timing inference.

Size/exposure classes: {"both_equal": 417, "exposure_equal_size_changes": 457, "size_down_exposure_down": 0, "size_down_exposure_up": 0, "size_equal_exposure_changes": 0, "size_up_exposure_down": 145, "size_up_exposure_up": 1}.

Size/SAT-call Pareto classes: {"candidate_dominates_size_calls": 40, "equal_size_calls": 417, "parent_dominates_size_calls": 562, "tradeoff_size_calls": 1, "unavailable": 0}.

The one observed tradeoff is `repeated_module_heldout_n6`: actual SDD element size **17 to 18**, directly exposed blocks **1 to 2**, residual SAT calls **7 to 5**. The pure SAT solve-time diagnostic changes from 0.4224 to 0.3302 ms, while its complete residual-stage diagnostic changes from 22.587 to 27.750 ms. This illustrates why fewer calls and a tiny SAT-time difference are not automatically a total-runtime benefit. The latter timings are single measurements, not robust speed estimates.

`data/size_exposure_tradeoff_example.json` records CNF, both vtrees, partitions and measurements. It is a computational example of nonidentical size/exposure objectives. It does not show that globally size-optimal and globally exposure-optimal trees are necessarily disjoint, nor prove a general objective dominance theorem. No held-out move is selected to revise the frozen heuristic.

## Public controls

All three MIT-licensed official PySAT documentation CNFs passed, including one false formula handled outside the nonfalse prime-factor contract. Source URLs are in code/public_controls.py and data/public_control_results.json; attribution is retained in licenses/PySAT_LICENSE.txt. These are public smoke checks only. No public industrial corpus was run, and no result is described as industrial-scale validation.
