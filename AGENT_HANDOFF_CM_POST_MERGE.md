# Post-Merge CM / Bitset / Hybrid Handoff

## Executive Summary

This document reconstructs the major Correspondence Matrix (CM), bitset, hybrid-materialization, and benchmark changes completed in this thread, and records the previously observed correctness and performance baselines that existed before later merge activity.

This repo has since been merged with additional code. The next agent should treat the details below as **expected post-thread behavior** and **previously observed baselines**, not as proof that the merged state still satisfies them. The immediate task after ingesting this document is verification: confirm that the merged code still preserves the same semantics, CLI surface, diagnostics, and approximate benchmark relationships, or determine precisely where it diverged.

This handoff is intentionally technical rather than conversational. It is meant to be read once and then used as the operating spec for regression checking.

## Purpose

The goal of this handoff is to give the next agent a decision-complete picture of:

- what was implemented in the CM / bitset / hybrid work in this thread,
- what files and interfaces are expected to exist,
- what tests and benchmark outputs previously passed,
- what performance relationships were previously observed,
- what commands should be rerun after merge,
- and how to reason about mismatches if the merged state no longer behaves the same way.

The central question for the next agent is:

> Does the merged code still preserve the previously established correctness and approximate benchmark characteristics of the CM, full-collapse hybrid, partial-hybrid, CM-parallel, and bitset backends?

## Current Expected Architecture

### Primary backend stack

The intended backend stack visible in the repo at the end of this thread is:

- symbolic DAG / CM IR: [cm_ir.py](c:\Users\brian\Documents\CM_Computation\cm_ir.py)
- eager CM wrapper: [cm_build.py](c:\Users\brian\Documents\CM_Computation\cm_build.py)
- lazy CM wrapper: [cm_build_lazy.py](c:\Users\brian\Documents\CM_Computation\cm_build_lazy.py)
- parallel CM materialization path: [cm_parallel.py](c:\Users\brian\Documents\CM_Computation\cm_parallel.py)
- bitset backend: [bitset_backend.py](c:\Users\brian\Documents\CM_Computation\bitset_backend.py)
- benchmark harness: [cm_bench.py](c:\Users\brian\Documents\CM_Computation\cm_bench.py)

### Expected materialization modes

The materialization layer in [cm_ir.py](c:\Users\brian\Documents\CM_Computation\cm_ir.py) is expected to support these modes:

| Mode | Meaning | Expected use |
| --- | --- | --- |
| `numpy` | Dense NumPy-only CM materialization | Baseline/reference execution path |
| `hybrid` | Full-collapse bitset execution for a qualifying subtree | Benchmark comparison path; fastest hybrid observed in prior runs |
| `partial_hybrid` | Node-level hybridization: small child subproblems can use bitset while parent combination stays in CM/NumPy form | Expected default CM execution mode after this thread |

### Default expectations

At the end of this thread, the expected defaults were:

- default CM materialization mode: `partial_hybrid`
- benchmark compare mode baseline CM: forced `numpy`
- benchmark compare mode additional collections:
  - full-collapse `hybrid`
  - `partial_hybrid`
  - `CM_parallel` using `partial_hybrid`
  - `bitset`
- canonical layout default: `balanced` non-padded split, with `legacy_square` retained as an option

### Expected diagnostic families

The benchmark and materialization code is expected to expose these diagnostic concepts:

| Diagnostic | Meaning |
| --- | --- |
| `subtree_cache_hits` / `subtree_cache_misses` | CM IR subtree interning / reuse |
| `canonical_rewrites` | algebraic / canonicalization rewrites during IR build |
| `pruned_branches` | constant-folded or short-circuited branches |
| `materializations` | number of materialization results memoized |
| `live_vars_max` | max live variable count seen at materialization |
| `bitset_materializations` / `numpy_materializations` | backend choice counts by materialization result |
| `bitset_nodes` / `numpy_nodes` | backend choice counts at node level |
| `materialization_live_vars_total` | cumulative live-variable count over materializations |
| `materialization_avg_k` | average live-variable count per materialization |
| `hybrid_depth_max` | deepest level at which hybrid bitset dispatch occurred |
| `full_collapse_occurred` | whether the full-collapse root path was taken |

## Implemented Changes From This Thread

### 1. Bitset validation and caching

The bitset backend in [bitset_backend.py](c:\Users\brian\Documents\CM_Computation\bitset_backend.py) was validated and extended so that:

- truth-table ordering matches `eval_expr_tt` exactly,
- masking uses the full TT width implied by `n_vars`,
- `build_bitset_env(vars)` is cached by variable tuple rather than recomputed per trial,
- cache statistics are exposed for tests,
- bitset outputs can be converted back into CM-compatible hypercube arrays,
- CM IR nodes can be evaluated directly through bitset logic without rebuilding ASTs.

Expected helper behavior after this thread:

- `build_bitset_env(vars)` returns cached envs keyed by `tuple(vars)`
- `bitset_env_cache_stats()` exposes hits/misses/size
- `eval_expr_bitset(...)` respects exact-width masking
- `eval_cm_node_bitset(...)` evaluates CM IR nodes over a live variable set plus optional fixed values
- `bitset_to_bool_hypercube(...)` converts packed bitsets back to the hypercube shape expected by the CM materializer

### 2. CM computation-reduction redesign

The dense eager/lazy CM behavior was reworked around a symbolic shared DAG in [cm_ir.py](c:\Users\brian\Documents\CM_Computation\cm_ir.py). The intent was to reduce total work before parallelizing anything.

Key changes expected from this redesign:

- compile expressions into a shared CM DAG rather than repeatedly materializing dense matrices,
- canonicalize repeated logical structure so duplicate subtrees are interned and reused,
- apply algebraic simplifications and branch pruning during IR build,
- enforce delayed materialization so dense arrays appear only at the execution boundary,
- cache alignment plans used to reconcile variable layouts,
- keep subproblems scoped to their live variable sets rather than ambiently expanding too early,
- switch default layout policy to `balanced` while retaining `legacy_square` for comparison.

Expected conceptual result:

- eager and lazy wrappers still return dense matrices to callers,
- but internally the system should no longer behave like a dense evaluator at every intermediate node.

### 3. CM parallelization

Parallel CM work was retained in [cm_parallel.py](c:\Users\brian\Documents\CM_Computation\cm_parallel.py), but after the DAG redesign it became a secondary optimization rather than the main route to performance gains.

Expected properties after this thread:

- deterministic results,
- same semantics as non-parallel CM,
- parallelism applied during selected combine/materialization work,
- no semantic differences from eager/lazy CM,
- benchmark timing should exclude TT extraction/conversion.

Important historical conclusion:

- earlier measurements showed that parallelism alone was not the main bottleneck,
- therefore later work focused on reducing computation rather than expanding parallel scheduling.

### 4. Hybrid execution work

Hybrid materialization evolved in two steps.

#### Full-collapse hybrid (`hybrid`)

Implemented first:

- if the live variable count `k` for the current materialization target was small enough, the entire qualifying subtree was evaluated through bitset,
- result was converted back into a CM-compatible hypercube,
- this generally improved over pure NumPy CM,
- but it bypassed the CM combination structure for the collapsed subtree.

Expected behavior:

- `full_collapse_occurred = 1` when the root/path collapsed,
- `hybrid_depth_max = 0` in the common full-collapse case.

#### Partial hybrid (`partial_hybrid`)

Implemented later:

- preserve CM structure at the current/parent node,
- evaluate children first,
- allow small child subproblems to use bitset,
- combine child outputs using the CM alignment/combine path,
- support `bitset + bitset`, `bitset + numpy`, and `numpy + numpy` child combinations through the existing array path.

Expected behavior:

- root-level full collapse should not occur in normal `partial_hybrid` operation,
- `full_collapse_occurred = 0`,
- `hybrid_depth_max` should generally be at least `1` in cases where child dispatch occurs,
- diagnostics should show both bitset and NumPy node/materialization counts.

Historical conclusion from prior benchmark runs:

- `partial_hybrid` behaved correctly and preserved structure,
- but it did not beat full-collapse `hybrid` in the sampled runs,
- likely because conversion and parent-side NumPy combine overhead still outweighed the benefit of preserving structure at these sizes.

### 5. Benchmark integration

The benchmark harness in [cm_bench.py](c:\Users\brian\Documents\CM_Computation\cm_bench.py) was extended so CM variants could be compared directly.

Expected CLI and reporting capabilities after this thread:

- `--cm-layout {balanced,legacy_square}`
- `--cm-parallel` and related tuning flags
- `--cm-hybrid-threshold`
- `--cm-compare-hybrid`
- `--experiment cm_vs_bitset`

Expected compare-mode collections:

| Label in results | Intended execution path |
| --- | --- |
| `CM` | NumPy-only baseline when compare mode is enabled |
| `CM_hybrid` | Full-collapse hybrid |
| `CM_partial_hybrid` | Partial node-level hybrid |
| `CM_parallel` | Parallel CM materialization, using partial hybrid policy |
| `bitset` | Direct bitset backend |

Expected ratio outputs include:

- `ratio_cm_hybrid_over_cm`
- `ratio_cm_hybrid_over_bitset`
- `ratio_cm_partial_hybrid_over_cm`
- `ratio_cm_partial_hybrid_over_bitset`
- `ratio_cm_parallel_over_cm`
- `ratio_cm_parallel_over_bitset`

## Expected Test Coverage

The following tests are expected to exist and continue covering the semantics established in this thread:

- [tests/test_bitset_backend.py](c:\Users\brian\Documents\CM_Computation\tests\test_bitset_backend.py)
- [tests/test_cm_parallel.py](c:\Users\brian\Documents\CM_Computation\tests\test_cm_parallel.py)
- [tests/test_cm_optimizations.py](c:\Users\brian\Documents\CM_Computation\tests\test_cm_optimizations.py)
- [tests/test_bench_integration.py](c:\Users\brian\Documents\CM_Computation\tests\test_bench_integration.py)

### What those tests are expected to prove

| Test file | Expected coverage |
| --- | --- |
| [tests/test_bitset_backend.py](c:\Users\brian\Documents\CM_Computation\tests\test_bitset_backend.py) | truth-table ordering, exact masking, cache hits, CM-node bitset evaluation correctness |
| [tests/test_cm_parallel.py](c:\Users\brian\Documents\CM_Computation\tests\test_cm_parallel.py) | parallel correctness vs sequential CM and determinism |
| [tests/test_cm_optimizations.py](c:\Users\brian\Documents\CM_Computation\tests\test_cm_optimizations.py) | layout correctness, CSE reuse, pruning, compile-vs-materialize separation, fixed-variable dimensionality reduction, full-hybrid behavior, partial-hybrid behavior, default mode expectations |
| [tests/test_bench_integration.py](c:\Users\brian\Documents\CM_Computation\tests\test_bench_integration.py) | CLI/output-schema stability for compare mode and diagnostic columns |

### Previously observed passing states in this thread

Previously observed milestones in this thread were:

- after hybrid-materialization work: `20` tests passing
- after partial-hybrid work: `23` tests passing

These counts were correct **at the time they were recorded in this thread**. They must be treated as historical baselines only. After merge, the next agent should rerun the suite rather than assuming these counts still hold.

## Previously Observed Benchmark Results

The benchmark artifacts already present in the repo and relevant to this thread are:

- balanced-vs-legacy layout comparison:
  - [bench_cm_reduced_balanced_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_reduced_balanced_summary.csv)
  - [bench_cm_reduced_legacy_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_reduced_legacy_summary.csv)
- full-collapse hybrid compare:
  - [bench_cm_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_hybrid_summary.csv)
- partial-hybrid compare:
  - [bench_cm_partial_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_partial_hybrid_summary.csv)

### A. Computation-reduction / layout comparison baseline

These were previously observed from the reduced-layout benchmark CSVs:

| n | Balanced CM median (s) | Legacy-square CM median (s) | Balanced / Legacy observation |
| --- | ---: | ---: | --- |
| 4 | 0.0002588 | 0.0002806 | similar; balanced slightly better |
| 8 | 0.0003209 | 0.0002957 | similar; legacy slightly better in this sample |
| 12 | 0.0002396 | 0.0004279 | balanced materially better |
| 16 | 0.0005596 | 0.0007322 | balanced materially better |

Qualitative expectation carried forward from those runs:

- balanced layout improved non-power-of-two and larger cases materially,
- the optimized CM pipeline improved over the legacy/padded behavior,
- even after those gains, CM still remained much slower than pure bitset.

### B. Full-collapse hybrid baseline

Previously observed from [bench_cm_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_hybrid_summary.csv):

| n | CM (NumPy baseline) | CM_hybrid | CM_parallel | bitset | `CM_hybrid / CM` | `CM_hybrid / bitset` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.0003321 | 0.0003095 | 0.0001783 | 0.0000099 | 0.9319 | 31.2626 |
| 8 | 0.0002327 | 0.0001696 | 0.0001683 | 0.0000083 | 0.7288 | 20.4337 |
| 12 | 0.0003267 | 0.0002207 | 0.0002188 | 0.0000149 | 0.6755 | 14.8121 |
| 16 | 0.0005811 | 0.0004174 | 0.0004231 | 0.0000509 | 0.7183 | 8.2004 |

Previously observed qualitative conclusion:

- optimized full-collapse hybrid materially improved over NumPy CM,
- but remained far slower than pure bitset,
- `CM_parallel` was often very close to `CM_hybrid`, indicating that once small reduced subproblems collapsed to bitset, there was not much dense work left for parallelization to win on.

### C. Partial-hybrid baseline

Previously observed from [bench_cm_partial_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_partial_hybrid_summary.csv):

| n | CM (NumPy baseline) | CM_hybrid | CM_partial_hybrid | CM_parallel | bitset |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.0006454 | 0.0001820 | 0.0002430 | 0.0002638 | 0.0000135 |
| 8 | 0.0002586 | 0.0001690 | 0.0001975 | 0.0002284 | 0.0000087 |
| 12 | 0.0004144 | 0.0002463 | 0.0003320 | 0.0002835 | 0.0000142 |
| 16 | 0.0005364 | 0.0003935 | 0.0005468 | 0.0006998 | 0.0000518 |

Previously observed ratio expectations:

| n | `CM_partial_hybrid / CM` | `CM_partial_hybrid / bitset` | Interpretation |
| --- | ---: | ---: | --- |
| 4 | 0.3765 | 18.0000 | faster than NumPy baseline, slower than full hybrid |
| 8 | 0.7637 | 22.7012 | faster than NumPy baseline, slower than full hybrid |
| 12 | 0.8012 | 23.3802 | faster than NumPy baseline, slower than full hybrid |
| 16 | 1.0194 | 10.5560 | roughly parity/slightly worse than NumPy baseline; worse than full hybrid |

Previously observed structural diagnostics from the same CSV:

| Variant | Expected collapse behavior | Previously observed values |
| --- | --- | --- |
| `CM_hybrid` | full collapse | `full_collapse_occurred = 1`, `hybrid_depth_max = 0` |
| `CM_partial_hybrid` | no root collapse, child-level hybridization | `full_collapse_occurred = 0`, `hybrid_depth_max = 1` |
| `CM_partial_hybrid` | mixed backend usage | typically `bitset_nodes = 2-3`, `numpy_nodes = 1` |
| `CM_parallel` | same partial-hybrid semantics with parallel combine path | same no-collapse pattern in the sample |

### Consolidated qualitative conclusions from prior runs

These are the high-level conclusions previously established in this thread and should be used as **baseline expectations** for post-merge verification:

- optimized CM materially improved over dense NumPy baseline behavior but still remained slower than pure bitset,
- full-collapse hybrid generally beat partial hybrid in the sampled runs,
- partial hybrid behaved correctly and showed mixed backend use, but did not outperform full-collapse hybrid in the recorded benchmarks,
- full-collapse hybrid showed `full_collapse_occurred = 1`,
- partial hybrid showed `full_collapse_occurred = 0` and hybrid depth around `1` in the recorded sample,
- benchmark gaps to pure bitset remained significant even after the redesigns.

These statements are not guarantees about the merged repo. They are the behavioral envelope the next agent should compare against.

## Post-Merge Verification Checklist

The next agent should treat the following as the minimum post-merge verification pass.

### 1. Confirm code surface still exists

Inspect whether these items still exist with the same intent:

- `materialize_mode` support in [cm_ir.py](c:\Users\brian\Documents\CM_Computation\cm_ir.py)
- default `partial_hybrid` in:
  - [cm_build.py](c:\Users\brian\Documents\CM_Computation\cm_build.py)
  - [cm_build_lazy.py](c:\Users\brian\Documents\CM_Computation\cm_build_lazy.py)
  - [cm_parallel.py](c:\Users\brian\Documents\CM_Computation\cm_parallel.py)
- benchmark flags in [cm_bench.py](c:\Users\brian\Documents\CM_Computation\cm_bench.py):
  - `--cm-hybrid-threshold`
  - `--cm-compare-hybrid`
  - `--cm-parallel`
  - `--cm-layout`
  - `--experiment cm_vs_bitset`
- benchmark columns and ratio calculations for full hybrid, partial hybrid, parallel, and bitset

### 2. Rerun the unit tests

Recommended command:

```powershell
python -m unittest discover -s tests -v
```

At minimum, the next agent should verify:

- the suite still runs,
- the key test files still execute,
- correctness failures are not being hidden by renamed tests or broken discovery.

### 3. Rerun the benchmark compare baseline

Recommended command shape matching the prior recorded runs:

```powershell
python cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 321 --out-prefix bench_cm_partial_hybrid_recheck --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 7 --cm-parallel --cm-parallel-workers 2 --cm-parallel-min-n 1 --cm-parallel-min-nodes 1 --cm-parallel-chunk-rows 32 --experiment cm_vs_bitset --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop --no-numba --print-summary
```

Optional secondary layout check:

```powershell
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 321 --out-prefix bench_cm_layout_recheck --cm-layout legacy_square --cm-parallel --cm-parallel-workers 2 --cm-parallel-min-n 1 --cm-parallel-min-nodes 1 --cm-parallel-chunk-rows 32 --experiment cm_vs_bitset --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop --no-numba --print-summary
```

### 4. Compare against stored baselines

Compare the fresh results to these artifacts:

- [bench_cm_reduced_balanced_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_reduced_balanced_summary.csv)
- [bench_cm_reduced_legacy_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_reduced_legacy_summary.csv)
- [bench_cm_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_hybrid_summary.csv)
- [bench_cm_partial_hybrid_summary.csv](c:\Users\brian\Documents\CM_Computation\bench_cm_partial_hybrid_summary.csv)

The comparison should answer:

- do correctness flags still stay `True` across CM / hybrid / partial-hybrid / parallel / bitset?
- do the compare-mode columns still exist?
- does `CM_hybrid` still fully collapse while `CM_partial_hybrid` does not?
- is default non-compare CM still using `partial_hybrid`?
- are the ratios in the same rough range as before?

### 5. Classify any divergence

If the merged state differs, classify it as one of:

- semantic breakage,
- benchmark harness drift,
- expected workload variance,
- merge-induced architectural change.

That classification should happen before making optimization changes.

## Regression Interpretation Guidance

If the merged repo does not behave like the previously observed baseline, the next agent should use the following decision path.

### If correctness tests fail

Prioritize likely semantic drift in:

- `materialize_mode` dispatch logic in [cm_ir.py](c:\Users\brian\Documents\CM_Computation\cm_ir.py)
- bitset conversion helpers in [bitset_backend.py](c:\Users\brian\Documents\CM_Computation\bitset_backend.py)
- fixed-variable handling during materialization
- shape alignment / `align_to_vars(...)`
- truth-table projection back from CM matrices in [cm_bench.py](c:\Users\brian\Documents\CM_Computation\cm_bench.py)

### If benchmark integration tests fail but correctness still passes

Check first for harness drift rather than backend semantics:

- renamed or removed CLI flags,
- changed CSV column names,
- changed summary aggregation field names,
- compare-mode no longer collecting all expected variants,
- diagnostics renamed, omitted, or no longer propagated.

### If correctness passes but performance changes materially

Compare these diagnostics first:

- `bitset_materializations` vs `numpy_materializations`
- `bitset_nodes` vs `numpy_nodes`
- `hybrid_depth_max`
- `full_collapse_occurred`
- default materialization mode in wrappers and benchmark mode selection

Interpretation guidance:

| Symptom | Most likely cause to inspect first |
| --- | --- |
| `CM_hybrid` no longer clearly faster than NumPy CM | collapse path no longer reached, threshold/default changed, or bitset conversion got slower |
| `CM_partial_hybrid` fully collapses | `allow_bitset_collapse` semantics regressed |
| `CM_partial_hybrid` never uses bitset | threshold drift, live-var accounting drift, or child dispatch no longer triggered |
| `CM_parallel` changes semantics | parallel path no longer shares the same materialization mode or combine rules |
| compare-mode `CM` looks too fast | benchmark baseline may no longer be forcing `numpy` |
| layout comparison changed drastically | default layout or TT projection behavior changed |

### Likely merge break points

The specific classes of merge-induced breakage that are most plausible here are:

- changed defaults in CM wrappers (`partial_hybrid` replaced or removed),
- altered compare-mode logic in [cm_bench.py](c:\Users\brian\Documents\CM_Computation\cm_bench.py),
- stale or renamed diagnostics breaking interpretation/tests,
- changed layout defaults in [cm_normalize.py](c:\Users\brian\Documents\CM_Computation\cm_normalize.py),
- changed TT projection or padding-handling when turning CM matrices back into truth tables,
- bitset backend changes that affect ordering, masking, or cache behavior.

## Recommended Next Steps For Another Agent

1. Confirm that the default CM materialization mode is still `partial_hybrid` in the non-compare path.
2. Confirm that benchmark compare mode still collects NumPy CM, full hybrid, partial hybrid, CM parallel, and bitset distinctly.
3. Rerun the unit tests and record whether the previously observed `20` and `23`-test milestones are still reflected or have drifted.
4. Rerun the benchmark baselines and compare against the stored summary CSVs in this repo.
5. If results differ materially, isolate whether the break is in semantics, dispatch policy, benchmark aggregation, or merge-induced unrelated code drift.
6. Only after parity is restored should optimization work resume.
7. The highest-value future optimization still suggested by prior findings is avoiding immediate ndarray conversion for `bitset + bitset` combinations, so preserved structure can remain cheap without losing the benefits of hybrid decomposition.

## Important Status Note

Everything in this file about tests and benchmark results is **previously observed in this thread** unless the next agent reruns it in the merged workspace. This document is a baseline and an expectation model, not a fresh certification of the current merged state.

## Related Existing Handoff Artifacts

This new file is specifically about the CM / bitset / hybrid benchmark work reconstructed from this thread.

Other handoff/context files already present in the repo and worth reading separately are:

- [AGENT_HANDOFF_CM.md](c:\Users\brian\Documents\CM_Computation\AGENT_HANDOFF_CM.md)
- [THREAD_RECONSTRUCTION.md](c:\Users\brian\Documents\CM_Computation\THREAD_RECONSTRUCTION.md)

Those documents cover other repository work and earlier reconstruction context. They should not replace this post-merge CM/hybrid baseline brief.
