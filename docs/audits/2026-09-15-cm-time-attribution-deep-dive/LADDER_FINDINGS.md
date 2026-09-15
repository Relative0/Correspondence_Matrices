# Corrected packed-ladder findings

Source: `ladder-run-002.json`, SHA-256 `24eeddde21be783c7598b99035207028f1768738e69744ca038f4d98abc26e40`; exact baseline `e334de594262059cc18cf37eaab56b0f79e94843`. This is diagnostic evidence on 13 disclosed cases, 137 cells and seven uninstrumented repeats per cell. No held-out input or scientific disposition changed.

**Measured** means a statistic recomputed from this frozen run. **Code-supported inference** identifies a mechanism demonstrated by the audited implementation. **Hypothesis** names an unisolated explanation. **Unknown** marks absent or inadequate evidence. All reported wins are descriptive local medians, not confirmation results or statistical superiority claims.

## 1. Main findings

* **Measured:** common-executor CM has a lower cold median in 0/13 cases and a lower resident median in 10/13; 11/13 resident ratios lie within 10% of parity. These use the identical prepared bigint executor and common complete packed-byte delivery/check contract.
* **Measured:** CM has fewer flat instructions in 3/13 cases and fewer counted bigint primitives in 3/13. A resident CM win where work was rewritten away is not evidence of faster implementation of an identical instruction stream.
* **Measured:** traced retained bytes for the common CM session exceed CSE-flat in 12/13 cases. This includes session/source/program/output/module-cache retention, not isolated CMNode bytes; the retained-object attribution is **code-supported inference**, supported by node/support metadata but not a complete graph-byte census.
* **Code-supported inference:** CSE-flat retains sharing and a flat program without constructing the canonical CMNode graph, deep node keys or per-node support tuples. The cold-vs-resident interaction isolates the practical difference between paying this setup and reusing it. It does not separately identify each construction cost.
* **Unknown:** exact cumulative allocation traffic, native/process RSS, isolated cache validation/eviction time, asymptotic slopes, or whether a broad workload population prefers one representation. The small cases have correlated sharing, support and program length.

## 2. Boundary and instrumentation cautions

Cold q1 starts with a supplied serialized payload, parses/decodes it, constructs required IR/program/masks, evaluates and delivers/checks complete output bytes. File loading and process startup are absent from that caller. Resident q64 uses an already-set-up session and reports its 64-call total divided by64. A warm-up call is outside these resident timings. Setup is not recharged in resident per-call values.

Phase shares below divide sums of exclusive instrumented phase spans by sums of their own instrumented caller totals. They are time-weighted across these cells. They must not be applied to uninstrumented totals: nested Python probes strongly dilate tiny operations. `public_cm_diag` also intentionally uses the generic diagnostic wrapper, whereas `public_cm` preserves the diagnostics-free branch. Allocation inside bigint arithmetic and word conversion inside `_eval_words` remain grouped.

Earlier run001 and smoke evidence remain unchanged but are superseded for this analysis because imported evaluator aliases were initially missing from phase tracing. Only run002 is read by `summarize_ladder.py`. The script performs no timing and refuses existing output paths.

**Measured CPU limitation:** 1795/1918 whole-pass CPU observations are zero. Smallest positive observed whole-pass CPU was 0.015625 s although the API reports 1.0e-07 s resolution. Preserve the quantized CPU ranges; zero does not establish that a phase uses no CPU.

## 3. Common-executor CM versus CSE-flat

Ratios are CM/CSE from uninstrumented wall medians; resident time is per operation. `Ops` means counted bigint primitives, not flat instructions. Sharing is unfolded occurrences divided by structural DAG nodes; it includes structurally equal separately allocated subtrees and is not an identity-sharing ratio. Delta-delta = (cold CM−CSE) − (resident CM−CSE), a descriptive 2×2 representation/residency interaction in microseconds. A positive interaction says that relative CM cost shrinks after setup is resident; it is not an exclusive compile timer.

| Case | Source nodes/edges; sharing | CSE instr/ops | CM nodes; support entries; instr/ops | Cold ratio | Resident ratio | Delta-delta µs | CSE/CM retained bytes |
|---|---|---|---|---:|---:|---:|---:|
| random-shared-seed0-k8 | 23/32; 1.87 | 15/35 | 21; 59; 15/35 | 2.221 | 0.998 | 243.811 | 17959/20711 |
| random-shared-seed1-k8 | 22/31; 2.55 | 13/25 | 18; 44; 12/24 | 2.022 | 0.953 | 218.425 | 17439/19327 |
| random-existing-k3 | 19/32; 3.95 | 11/28 | 9; 16; 6/16 | 2.145 | 0.668 | 171.056 | 14795/14043 |
| random-existing-k8 | 17/22; 1.47 | 8/15 | 14; 29; 8/15 | 2.484 | 1.009 | 232.069 | 14183/16191 |
| random-existing-k12 | 19/22; 1.74 | 11/25 | 12; 21; 7/18 | 2.051 | 0.733 | 176.789 | 22879/23028 |
| random-existing-k16 | 18/20; 1.28 | 6/16 | 14; 27; 6/16 | 1.482 | 0.999 | 162.922 | 171216/173432 |
| shared-h | 10/10; 1.50 | 4/5 | 9; 21; 4/5 | 2.432 | 0.999 | 138.003 | 9332/10628 |
| equal-separate-h | 15/14; 1.50 | 4/5 | 9; 21; 4/5 | 2.033 | 0.992 | 114.119 | 10428/11724 |
| single-consumer-chain-k12 | 23/22; 1.00 | 1/11 | 13; 24; 1/11 | 2.594 | 0.953 | 274.888 | 24091/29643 |
| fixed-structure-output-k4 | 7/6; 1.00 | 3/5 | 7; 12; 3/5 | 1.790 | 1.003 | 62.394 | 7567/8351 |
| fixed-structure-output-k8 | 7/6; 1.00 | 3/5 | 7; 12; 3/5 | 1.495 | 0.998 | 52.305 | 8185/8969 |
| fixed-structure-output-k16 | 7/6; 1.00 | 3/5 | 7; 12; 3/5 | 1.322 | 0.994 | 68.511 | 164985/165769 |
| fixed-structure-output-k18 | 7/6; 1.00 | 3/5 | 7; 12; 3/5 | 1.146 | 1.033 | 96.119 | 705193/705977 |

## 4. Public versus bare CM

Both arms start from the same source fixture in cold treatment and from existing CMNodes in resident treatment; both deliver/check the same packed bytes. The delta is public median minus bare median, and its share is delta/public median. It is an incremental whole-call comparison, **not** a measured exclusive wrapper fraction: order, cache/first-use behavior and run noise interact. Negative values are retained. Public no-reinflate guard/result work is **code-supported inference**; the exclusive phase pass independently observes those helpers.

| Case | Cold public/bare | Cold delta µs; share % | Resident public/bare | Resident delta µs; share % | Interaction µs |
|---|---:|---:|---:|---:|---:|
| random-shared-seed0-k8 | 1.102 | 43.500; 9.2 | 4.489 | 22.020; 77.7 | 21.480 |
| random-shared-seed1-k8 | 1.153 | 61.900; 13.3 | 4.853 | 20.908; 79.4 | 40.992 |
| random-existing-k3 | 1.216 | 68.100; 17.8 | 7.080 | 19.608; 85.9 | 48.492 |
| random-existing-k8 | 1.169 | 57.800; 14.5 | 5.640 | 20.366; 82.3 | 37.434 |
| random-existing-k12 | 1.480 | 162.000; 32.4 | 3.703 | 20.683; 73.0 | 141.317 |
| random-existing-k16 | 1.144 | 77.300; 12.6 | 1.648 | 24.502; 39.3 | 52.798 |
| shared-h | 1.254 | 49.800; 20.3 | 7.489 | 19.598; 86.6 | 30.202 |
| equal-separate-h | 1.067 | 15.400; 6.3 | 7.933 | 21.114; 87.4 | -5.714 |
| single-consumer-chain-k12 | 1.038 | 16.800; 3.6 | 5.100 | 20.214; 80.4 | -3.414 |
| fixed-structure-output-k4 | 1.462 | 59.600; 31.6 | 8.722 | 20.078; 88.5 | 39.522 |
| fixed-structure-output-k8 | 1.368 | 57.300; 26.9 | 8.413 | 20.827; 88.1 | 36.473 |
| fixed-structure-output-k16 | 1.117 | 40.900; 10.5 | 2.248 | 24.252; 55.5 | 16.648 |
| fixed-structure-output-k18 | 1.328 | 252.600; 24.7 | 1.434 | 30.513; 30.3 | 222.087 |

## 5. Fixed expression, growing requested output

The disclosed implication expression retains four variables while the requested complete basis grows from k4 to k18. The packed byte counts are 2, 32, 8192 and 32768. This holds logical/source structure fixed and exposes width-dependent mask, execution and output work. It does not distinguish unavoidable output emission from all intermediate operations over the same width. Dense CM cells are separate contracts and are listed in the complete ledger.

| Arm | k4 cold/resident µs | k8 cold/resident µs | k16 cold/resident µs | k18 cold/resident µs | First measured width→k18 retained/peak bytes |
|---|---:|---:|---:|---:|---:|
| raw_recursive | 50.100/2.862 | 73.800/2.958 | 251.200/23.694 | 817.500/93.575 | 4179→701805 / 5404→808964 |
| memo_ast | 45.200/5.920 | 66.100/5.616 | 239.500/38.172 | 841.600/131.214 | 4899→807369 / 5600→844840 |
| occurrence_flat | 59.300/1.834 | 79.300/2.023 | 254.400/19.389 | 880.400/70.333 | 6527→704153 / 7045→846468 |
| cse_flat | 79.000/1.861 | 105.700/2.056 | 212.300/19.431 | 675.700/68.291 | 7567→705193 / 10173→847508 |
| cm_common_flat | 141.400/1.867 | 158.000/2.052 | 280.700/19.320 | 774.100/70.572 | 8351→705977 / 8957→848292 |
| bare_cm_flat | 129.000/2.600 | 155.800/2.809 | 349.900/19.434 | 770.600/70.256 | 8231→705857 / 8957→848172 |
| cm_recursive | 122.700/6.517 | 145.000/6.283 | 266.500/39.397 | 719.000/136.064 | 7255→809725 / 8957→847252 |
| public_cm | 188.600/22.678 | 213.100/23.636 | 390.800/43.686 | 1023.200/100.769 | 9023→706649 / 10001→849553 |
| public_cm_diag | 200.200/29.236 | 243.700/35.539 | 361.100/50.017 | 927.900/104.862 | 9548→707302 / 10473→850041 |
| cse_words | not run | 138.500/6.998 | 386.600/23.333 | 1498.000/72.411 | 10757→1362295 / 11281→1397739 |
| cm_words | not run | 273.600/6.495 | 546.000/23.137 | 1750.200/73.341 | 11901→1363439 / 12425→1398883 |

## 6. Exclusive phase totals on their own denominators

Each row aggregates the three phase passes of every available cell for that arm/treatment. Total and top phases are mean microseconds per call across the cells; percentages use summed observed elapsed time. All phases and call/mean-helper costs for every cell are retained in `ladder_summary.json`. The unresolved/probe remainder is reported explicitly; it is not redistributed.

| Arm | Treatment; cells | Mean instrumented caller µs/call | Top exclusive phases (share; mean µs/call) | Unresolved/probe % |
|---|---|---:|---|---:|
| raw_recursive | cold_q1; 13 | 236.651 | positional_masks_cache_and_construction: 36.5%; 86.351; input_dag_decode_and_validation: 21.2%; 50.251; raw_ast_kernel_and_allocation: 10.4%; 24.541; input_json_parse: 6.9%; 16.428 | 22.0 |
| raw_recursive | resident_q64; 13 | 33.445 | raw_ast_kernel_and_allocation: 52.7%; 17.634; packed_integer_to_bytes_delivery: 13.0%; 4.343; common_complete_output_correctness_guard: 3.8%; 1.255 | 30.5 |
| memo_ast | cold_q1; 13 | 250.190 | positional_masks_cache_and_construction: 36.9%; 92.354; input_dag_decode_and_validation: 18.2%; 45.546; memo_ast_kernel_and_allocation: 12.8%; 32.038; input_json_parse: 7.2%; 18.103 | 21.0 |
| memo_ast | resident_q64; 13 | 44.229 | memo_ast_kernel_and_allocation: 63.9%; 28.283; packed_integer_to_bytes_delivery: 10.5%; 4.623; common_complete_output_correctness_guard: 3.0%; 1.347 | 22.6 |
| occurrence_flat | cold_q1; 13 | 306.392 | positional_masks_cache_and_construction: 25.7%; 78.792; input_dag_decode_and_validation: 17.3%; 53.141; lowering_occurrence_flat: 12.0%; 36.821; kernel_and_intermediate_allocation_release: 6.5%; 19.879 | 18.7 |
| occurrence_flat | resident_q64; 13 | 27.474 | kernel_and_intermediate_allocation_release: 45.6%; 12.517; packed_integer_to_bytes_delivery: 16.8%; 4.626; common_complete_output_correctness_guard: 4.8%; 1.306 | 32.9 |
| cse_flat | cold_q1; 13 | 317.815 | positional_masks_cache_and_construction: 25.0%; 79.382; structural_cse_and_lowering: 20.5%; 65.085; input_dag_decode_and_validation: 15.8%; 50.328; kernel_and_intermediate_allocation_release: 5.1%; 16.221 | 17.8 |
| cse_flat | resident_q64; 13 | 24.791 | kernel_and_intermediate_allocation_release: 40.4%; 10.023; packed_integer_to_bytes_delivery: 17.8%; 4.421; common_complete_output_correctness_guard: 5.6%; 1.378 | 36.2 |
| cm_common_flat | cold_q1; 13 | 1006.646 | rewrites_and_key_construction: 20.4%; 205.228; keys_and_interning: 14.1%; 141.497; source_traversal_build_memo: 13.4%; 134.900; positional_masks_cache_and_construction: 8.6%; 86.367 | 5.8 |
| cm_common_flat | resident_q64; 13 | 24.274 | kernel_and_intermediate_allocation_release: 39.1%; 9.491; packed_integer_to_bytes_delivery: 17.8%; 4.329; common_complete_output_correctness_guard: 5.3%; 1.283 | 37.8 |
| bare_cm_flat | cold_q1; 13 | 978.959 | rewrites_and_key_construction: 21.0%; 205.449; keys_and_interning: 14.0%; 136.987; source_traversal_build_memo: 13.1%; 127.849; positional_masks_cache_and_construction: 8.5%; 83.436 | 5.0 |
| bare_cm_flat | resident_q64; 13 | 34.161 | kernel_and_intermediate_allocation_release: 44.7%; 15.254; packed_integer_to_bytes_delivery: 13.8%; 4.703; restriction_key_validation_cache_and_binding: 5.3%; 1.827; common_complete_output_correctness_guard: 3.9%; 1.344 | 29.0 |
| cm_recursive | cold_q1; 13 | 950.085 | rewrites_and_key_construction: 21.3%; 202.254; keys_and_interning: 14.7%; 139.238; source_traversal_build_memo: 13.2%; 125.826; positional_masks_cache_and_construction: 10.2%; 96.882 | 5.3 |
| cm_recursive | resident_q64; 13 | 47.319 | cm_recursive_kernel_and_allocation: 62.6%; 29.616; packed_integer_to_bytes_delivery: 10.5%; 4.952; common_complete_output_correctness_guard: 2.8%; 1.343; positional_masks_cache_and_construction: 2.7%; 1.290 | 21.4 |
| public_cm | cold_q1; 13 | 1084.354 | rewrites_and_key_construction: 18.4%; 199.721; keys_and_interning: 12.9%; 140.220; source_traversal_build_memo: 11.6%; 126.305; positional_masks_cache_and_construction: 7.9%; 86.072 | 4.7 |
| public_cm | resident_q64; 13 | 92.686 | public_wrapper_lifecycle: 31.6%; 29.305; public_budget_guards: 24.0%; 22.245; kernel_and_intermediate_allocation_release: 18.1%; 16.810; packed_integer_to_bytes_delivery: 5.4%; 4.972 | 14.0 |
| public_cm_diag | cold_q1; 13 | 1093.503 | rewrites_and_key_construction: 18.7%; 204.418; keys_and_interning: 12.4%; 135.605; source_traversal_build_memo: 11.6%; 127.138; positional_masks_cache_and_construction: 7.2%; 78.977 | 5.0 |
| public_cm_diag | resident_q64; 13 | 103.659 | public_wrapper_lifecycle: 35.6%; 36.937; public_budget_guards: 22.9%; 23.694; kernel_and_intermediate_allocation_release: 16.7%; 17.298; packed_integer_to_bytes_delivery: 4.6%; 4.734 | 13.8 |
| cse_words | cold_q1; 9 | 549.378 | positional_masks_cache_and_construction: 22.4%; 123.033; words_masks_cache_and_construction: 21.7%; 119.241; structural_cse_and_lowering: 12.9%; 71.015; words_execution_binding_scratch_and_integer_conversion: 11.3%; 62.048 | 10.5 |
| cse_words | resident_q64; 9 | 51.238 | words_execution_binding_scratch_and_integer_conversion: 50.7%; 25.973; packed_integer_to_bytes_delivery: 12.2%; 6.226; flat_cache_lookup: 3.0%; 1.547; common_complete_output_correctness_guard: 3.0%; 1.521 | 28.8 |
| cm_words | cold_q1; 9 | 1222.144 | rewrites_and_key_construction: 18.4%; 224.907; keys_and_interning: 12.2%; 149.026; source_traversal_build_memo: 11.1%; 135.752; positional_masks_cache_and_construction: 9.8%; 119.907 | 4.2 |
| cm_words | resident_q64; 9 | 46.398 | words_execution_binding_scratch_and_integer_conversion: 51.0%; 23.642; packed_integer_to_bytes_delivery: 13.0%; 6.016; common_complete_output_correctness_guard: 3.0%; 1.403; flat_cache_lookup: 2.7%; 1.245 | 27.9 |
| dense_cm | cold_q1; 2 | 628.733 | complete_materialization: 12.5%; 78.900; rewrites_and_key_construction: 11.7%; 73.517; source_traversal_build_memo: 8.8%; 55.583; keys_and_interning: 8.4%; 52.967 | 8.4 |
| dense_cm | resident_q64; 2 | 142.662 | complete_materialization: 27.3%; 38.929; dense_array_delivery: 17.5%; 25.016; numpy_materialization_and_execution: 14.6%; 20.842; cm_recursive_kernel_and_allocation: 10.5%; 14.914 | 10.5 |

**Measured instrumentation dilation:** median 2.29×, range 0.84×–10.05× across 274 cell/treatment ratios. This is a cross-pass diagnostic ratio, not a correction factor. The 137-cell ledger below includes each treatment's own dilation.

## 7. Memory, caches and unresolved mechanisms

Tracemalloc was a separate cold pass. Current bytes retain result, session Expr/CM/program and module caches; peak bytes describe the traced peak over that call. These are not cumulative allocation traffic or process RSS. Node shallow+dict bytes omit descendant tuples/strings and shared ownership. `metrics.cm.support_entries_sum`, source edges/sharing, flat instructions/primitives and live-buffer counts permit structural comparison, but they cannot uniquely distribute retained bytes among mechanisms.

The integer/word paths retain different execution state. Word scratch arrays may persist with a program; bigint operations allocate results, and these small programs generally do not trigger the width-and-slot release policy together. Cache entry counters are observed after the memory pass, not a dedicated hit/miss/eviction campaign. This ladder has no persistent family cache reuse. Relevant family evidence is separate. Allocation/release and execution remain a measured joint phase; isolated allocation time is unknown.

The full relation is required by this ladder's output contract. SAT/count/equivalence/batch tasks are not represented by these complete-output times; their smaller requested answers and task-matched controls require separate ledgers. This run cannot attribute an entire public regression to a single mechanism or establish independent scaling laws. No optimization or routing recommendation follows from it.

## 8. Complete 137-cell uninstrumented ledger

Times are microseconds per operation; brackets give the full seven-repeat min/max range, not a confidence interval. CPU for resident q64 is total CPU divided by64. Dilation is cold/resident phase-pass median caller time divided by the matching uninstrumented median. All 137 records are included, including diagnostic-wrapper and dense-contract arms.

| Case | Arm | Cold wall median [min,max] µs | Cold CPU median [min,max] µs | Resident wall median [min,max] µs/call | Resident CPU median [min,max] µs/call | Dilation cold/resident | Retained/peak traced bytes |
|---|---|---:|---:|---:|---:|---:|---:|
| random-shared-seed0-k8 | raw_recursive | 135.200 [110.200, 195.000] | 0.000 [0.000, 0.000] | 14.137 [12.327, 54.233] | 0.000 [0.000, 0.000] | 1.21/1.87 | 10829/14716 |
| random-shared-seed0-k8 | memo_ast | 127.100 [117.200, 143.700] | 0.000 [0.000, 0.000] | 18.130 [17.002, 60.672] | 0.000 [0.000, 244.141] | 1.34/1.77 | 13801/14756 |
| random-shared-seed0-k8 | occurrence_flat | 196.800 [143.700, 225.800] | 0.000 [0.000, 0.000] | 7.250 [7.045, 8.064] | 0.000 [0.000, 0.000] | 1.75/2.46 | 17660/19475 |
| random-shared-seed0-k8 | cse_flat | 199.700 [181.700, 280.400] | 0.000 [0.000, 0.000] | 5.428 [5.305, 5.580] | 0.000 [0.000, 0.000] | 1.60/2.94 | 17959/26339 |
| random-shared-seed0-k8 | cm_common_flat | 443.500 [409.100, 543.000] | 0.000 [0.000, 0.000] | 5.417 [5.372, 5.892] | 0.000 [0.000, 244.141] | 2.57/3.02 | 20711/25483 |
| random-shared-seed0-k8 | bare_cm_flat | 427.300 [406.100, 449.200] | 0.000 [0.000, 0.000] | 6.311 [6.242, 6.869] | 0.000 [0.000, 0.000] | 2.72/3.82 | 20591/25483 |
| random-shared-seed0-k8 | cm_recursive | 390.200 [368.800, 443.500] | 0.000 [0.000, 0.000] | 18.916 [18.052, 28.755] | 0.000 [0.000, 244.141] | 3.24/1.84 | 19827/25483 |
| random-shared-seed0-k8 | public_cm | 470.800 [462.200, 636.400] | 0.000 [0.000, 15625.000] | 28.331 [25.769, 33.202] | 0.000 [0.000, 244.141] | 3.18/2.98 | 21319/25483 |
| random-shared-seed0-k8 | public_cm_diag | 477.100 [447.800, 584.200] | 0.000 [0.000, 0.000] | 33.177 [32.633, 38.847] | 0.000 [0.000, 0.000] | 2.64/2.91 | 21876/25483 |
| random-shared-seed0-k8 | cse_words | 269.700 [251.500, 369.100] | 0.000 [0.000, 15625.000] | 23.370 [22.531, 24.209] | 0.000 [0.000, 244.141] | 1.28/1.84 | 22371/26339 |
| random-shared-seed0-k8 | cm_words | 506.500 [468.700, 733.800] | 0.000 [0.000, 0.000] | 23.164 [22.708, 25.006] | 0.000 [0.000, 0.000] | 2.48/2.01 | 27115/27639 |
| random-shared-seed1-k8 | raw_recursive | 118.200 [115.000, 146.400] | 0.000 [0.000, 0.000] | 14.477 [13.344, 19.659] | 0.000 [0.000, 0.000] | 1.78/1.70 | 10461/14294 |
| random-shared-seed1-k8 | memo_ast | 124.500 [113.700, 140.800] | 0.000 [0.000, 0.000] | 16.172 [15.545, 22.091] | 0.000 [0.000, 0.000] | 1.34/2.16 | 13341/14294 |
| random-shared-seed1-k8 | occurrence_flat | 166.000 [150.400, 176.700] | 0.000 [0.000, 0.000] | 8.453 [8.289, 10.683] | 0.000 [0.000, 244.141] | 1.50/2.25 | 19601/21880 |
| random-shared-seed1-k8 | cse_flat | 213.600 [175.100, 253.500] | 0.000 [0.000, 0.000] | 4.798 [4.712, 5.712] | 0.000 [0.000, 0.000] | 1.36/3.25 | 17439/25422 |
| random-shared-seed1-k8 | cm_common_flat | 431.800 [378.100, 575.900] | 0.000 [0.000, 0.000] | 4.573 [4.511, 4.742] | 0.000 [0.000, 244.141] | 3.07/3.57 | 19327/23246 |
| random-shared-seed1-k8 | bare_cm_flat | 403.400 [390.500, 562.500] | 0.000 [0.000, 0.000] | 5.427 [5.344, 5.486] | 0.000 [0.000, 0.000] | 2.92/4.79 | 19207/23246 |
| random-shared-seed1-k8 | cm_recursive | 368.200 [350.900, 439.700] | 0.000 [0.000, 0.000] | 18.206 [15.484, 25.073] | 0.000 [0.000, 244.141] | 2.98/1.84 | 18831/23246 |
| random-shared-seed1-k8 | public_cm | 465.300 [434.100, 535.000] | 0.000 [0.000, 0.000] | 26.334 [25.180, 28.089] | 0.000 [0.000, 244.141] | 3.06/3.27 | 19935/23246 |
| random-shared-seed1-k8 | public_cm_diag | 471.000 [445.900, 671.800] | 0.000 [0.000, 0.000] | 34.202 [32.572, 36.905] | 0.000 [0.000, 244.141] | 2.73/2.64 | 20492/23246 |
| random-shared-seed1-k8 | cse_words | 265.200 [235.700, 377.700] | 0.000 [0.000, 0.000] | 20.414 [19.812, 23.636] | 0.000 [0.000, 244.141] | 2.00/3.58 | 21403/25422 |
| random-shared-seed1-k8 | cm_words | 519.200 [447.500, 742.300] | 0.000 [0.000, 0.000] | 19.966 [19.005, 21.509] | 0.000 [0.000, 244.141] | 2.49/2.13 | 24619/25143 |
| random-existing-k3 | raw_recursive | 97.300 [85.300, 141.700] | 0.000 [0.000, 0.000] | 19.359 [17.717, 21.339] | 0.000 [0.000, 244.141] | 1.55/1.60 | 8794/13584 |
| random-existing-k3 | memo_ast | 85.800 [84.200, 144.700] | 0.000 [0.000, 0.000] | 15.137 [13.498, 22.356] | 0.000 [0.000, 0.000] | 3.23/1.68 | 10082/13584 |
| random-existing-k3 | occurrence_flat | 157.300 [140.800, 220.000] | 0.000 [0.000, 0.000] | 9.386 [9.223, 11.505] | 0.000 [0.000, 0.000] | 1.79/2.30 | 21188/22307 |
| random-existing-k3 | cse_flat | 148.300 [142.000, 223.700] | 0.000 [0.000, 0.000] | 3.781 [3.756, 3.833] | 0.000 [0.000, 0.000] | 1.63/3.80 | 14795/22330 |
| random-existing-k3 | cm_common_flat | 318.100 [300.300, 358.700] | 0.000 [0.000, 0.000] | 2.525 [2.494, 2.656] | 0.000 [0.000, 0.000] | 3.18/5.45 | 14043/18778 |
| random-existing-k3 | bare_cm_flat | 315.300 [307.800, 561.900] | 0.000 [0.000, 15625.000] | 3.225 [3.175, 3.247] | 0.000 [0.000, 0.000] | 3.11/6.96 | 13923/18778 |
| random-existing-k3 | cm_recursive | 306.400 [284.800, 494.200] | 0.000 [0.000, 0.000] | 8.606 [7.903, 13.650] | 0.000 [0.000, 0.000] | 3.55/2.70 | 13227/18778 |
| random-existing-k3 | public_cm | 383.400 [368.500, 488.100] | 0.000 [0.000, 0.000] | 22.833 [21.350, 41.361] | 0.000 [0.000, 244.141] | 3.15/3.42 | 14651/18778 |
| random-existing-k3 | public_cm_diag | 373.400 [355.000, 677.200] | 0.000 [0.000, 0.000] | 31.666 [28.531, 39.481] | 0.000 [0.000, 244.141] | 3.27/2.65 | 15176/18778 |
| random-existing-k8 | raw_recursive | 97.000 [92.200, 121.300] | 0.000 [0.000, 0.000] | 6.913 [6.848, 7.986] | 0.000 [0.000, 0.000] | 1.78/2.96 | 8573/10432 |
| random-existing-k8 | memo_ast | 99.200 [94.800, 120.100] | 0.000 [0.000, 0.000] | 18.209 [13.027, 21.259] | 0.000 [0.000, 0.000] | 1.67/1.50 | 10457/11348 |
| random-existing-k8 | occurrence_flat | 142.900 [113.500, 164.800] | 0.000 [0.000, 15625.000] | 4.305 [4.270, 5.098] | 0.000 [0.000, 0.000] | 1.36/3.90 | 12964/14019 |
| random-existing-k8 | cse_flat | 156.400 [147.600, 195.400] | 0.000 [0.000, 0.000] | 3.458 [3.375, 4.556] | 0.000 [0.000, 0.000] | 1.67/4.67 | 14183/18697 |
| random-existing-k8 | cm_common_flat | 388.500 [323.500, 455.600] | 0.000 [0.000, 0.000] | 3.489 [3.442, 3.561] | 0.000 [0.000, 0.000] | 3.11/4.04 | 16191/19177 |
| random-existing-k8 | bare_cm_flat | 341.700 [329.400, 535.900] | 0.000 [0.000, 15625.000] | 4.389 [4.228, 4.647] | 0.000 [0.000, 0.000] | 3.30/5.50 | 16071/19177 |
| random-existing-k8 | cm_recursive | 312.600 [297.800, 365.400] | 0.000 [0.000, 0.000] | 13.348 [11.742, 17.889] | 0.000 [0.000, 244.141] | 2.98/2.24 | 15543/19177 |
| random-existing-k8 | public_cm | 399.500 [372.200, 723.900] | 0.000 [0.000, 0.000] | 24.755 [23.769, 30.159] | 0.000 [0.000, 0.000] | 2.64/3.03 | 16863/19177 |
| random-existing-k8 | public_cm_diag | 411.100 [379.500, 559.900] | 0.000 [0.000, 0.000] | 31.397 [29.330, 35.939] | 0.000 [0.000, 244.141] | 2.58/2.58 | 17420/19177 |
| random-existing-k8 | cse_words | 237.400 [205.000, 327.900] | 0.000 [0.000, 0.000] | 14.747 [14.522, 15.303] | 0.000 [0.000, 0.000] | 1.33/2.36 | 17539/18697 |
| random-existing-k8 | cm_words | 423.700 [387.400, 594.900] | 0.000 [0.000, 0.000] | 15.050 [14.547, 17.694] | 0.000 [0.000, 244.141] | 2.79/2.36 | 20739/21263 |
| random-existing-k12 | raw_recursive | 114.000 [101.000, 187.200] | 0.000 [0.000, 0.000] | 17.359 [17.253, 19.072] | 0.000 [0.000, 0.000] | 1.71/2.04 | 16725/19080 |
| random-existing-k12 | memo_ast | 102.900 [98.200, 142.400] | 0.000 [0.000, 0.000] | 21.075 [19.233, 24.548] | 0.000 [0.000, 0.000] | 1.58/1.68 | 24873/25448 |
| random-existing-k12 | occurrence_flat | 138.600 [125.300, 200.700] | 0.000 [0.000, 15625.000] | 14.139 [13.981, 16.142] | 0.000 [0.000, 0.000] | 2.19/1.84 | 22580/33319 |
| random-existing-k12 | cse_flat | 165.800 [155.600, 292.100] | 0.000 [0.000, 0.000] | 9.306 [9.031, 18.092] | 0.000 [0.000, 0.000] | 1.90/2.38 | 22879/28958 |
| random-existing-k12 | cm_common_flat | 340.100 [282.500, 503.500] | 0.000 [0.000, 0.000] | 6.817 [6.719, 12.239] | 0.000 [0.000, 244.141] | 2.53/2.64 | 23028/27355 |
| random-existing-k12 | bare_cm_flat | 337.800 [289.300, 2031.500] | 0.000 [0.000, 0.000] | 7.652 [7.592, 13.883] | 0.000 [0.000, 0.000] | 2.45/3.57 | 22908/27235 |
| random-existing-k12 | cm_recursive | 288.400 [274.200, 2022.300] | 0.000 [0.000, 15625.000] | 16.817 [14.322, 67.530] | 0.000 [0.000, 244.141] | 3.01/1.93 | 25968/26995 |
| random-existing-k12 | public_cm | 499.800 [336.800, 844.100] | 0.000 [0.000, 0.000] | 28.334 [27.014, 46.484] | 0.000 [0.000, 0.000] | 2.02/3.04 | 23636/28616 |
| random-existing-k12 | public_cm_diag | 509.200 [372.700, 579.800] | 0.000 [0.000, 15625.000] | 35.289 [34.520, 55.589] | 0.000 [0.000, 244.141] | 2.07/2.90 | 24289/29104 |
| random-existing-k12 | cse_words | 291.200 [212.900, 372.400] | 0.000 [0.000, 0.000] | 19.755 [17.819, 30.192] | 0.000 [0.000, 244.141] | 1.17/2.01 | 35023/36059 |
| random-existing-k12 | cm_words | 498.800 [349.500, 579.700] | 0.000 [0.000, 0.000] | 13.363 [13.164, 22.738] | 0.000 [0.000, 0.000] | 2.12/2.49 | 35028/36064 |
| random-existing-k16 | raw_recursive | 309.400 [259.100, 676.800] | 0.000 [0.000, 15625.000] | 56.650 [49.678, 97.620] | 0.000 [0.000, 0.000] | 0.99/1.27 | 165621/201256 |
| random-existing-k16 | memo_ast | 300.400 [232.000, 467.100] | 0.000 [0.000, 15625.000] | 94.181 [84.259, 97.878] | 0.000 [0.000, 244.141] | 1.03/1.11 | 254513/254825 |
| random-existing-k16 | occurrence_flat | 416.300 [259.800, 1768.100] | 0.000 [0.000, 0.000] | 46.189 [44.506, 54.486] | 0.000 [0.000, 244.141] | 0.84/1.21 | 169719/258278 |
| random-existing-k16 | cse_flat | 337.800 [291.300, 493.400] | 0.000 [0.000, 0.000] | 36.256 [35.534, 45.477] | 0.000 [0.000, 244.141] | 1.22/1.32 | 171216/224651 |
| random-existing-k16 | cm_common_flat | 500.700 [466.900, 1006.200] | 0.000 [0.000, 15625.000] | 36.234 [35.647, 61.495] | 0.000 [0.000, 244.141] | 2.19/1.42 | 173432/226867 |
| random-existing-k16 | bare_cm_flat | 535.700 [476.300, 647.100] | 0.000 [0.000, 15625.000] | 37.798 [37.064, 48.398] | 0.000 [0.000, 244.141] | 2.33/1.56 | 173312/226747 |
| random-existing-k16 | cm_recursive | 503.500 [448.400, 705.400] | 0.000 [0.000, 0.000] | 73.236 [63.711, 101.977] | 0.000 [0.000, 244.141] | 2.30/1.30 | 225064/226387 |
| random-existing-k16 | public_cm | 613.000 [513.400, 818.700] | 0.000 [0.000, 0.000] | 62.300 [57.670, 73.970] | 0.000 [0.000, 244.141] | 1.94/1.89 | 174016/228040 |
| random-existing-k16 | public_cm_diag | 617.800 [530.000, 682.200] | 0.000 [0.000, 0.000] | 69.502 [65.500, 77.763] | 0.000 [0.000, 244.141] | 2.22/1.93 | 174669/228528 |
| random-existing-k16 | cse_words | 497.600 [444.500, 589.600] | 0.000 [0.000, 0.000] | 38.367 [34.750, 43.373] | 0.000 [0.000, 0.000] | 1.08/1.51 | 338764/347988 |
| random-existing-k16 | cm_words | 675.700 [624.400, 728.500] | 0.000 [0.000, 0.000] | 38.853 [34.967, 46.078] | 0.000 [0.000, 244.141] | 1.93/1.44 | 341588/350812 |
| shared-h | raw_recursive | 63.600 [48.100, 129.800] | 0.000 [0.000, 0.000] | 4.450 [4.292, 9.342] | 0.000 [0.000, 0.000] | 2.17/3.67 | 5317/6944 |
| shared-h | memo_ast | 58.000 [51.000, 79.900] | 0.000 [0.000, 0.000] | 7.528 [6.700, 35.558] | 0.000 [0.000, 0.000] | 1.67/2.48 | 6197/7120 |
| shared-h | occurrence_flat | 80.200 [66.300, 113.200] | 0.000 [0.000, 0.000] | 2.939 [2.898, 3.020] | 0.000 [0.000, 244.141] | 2.05/4.73 | 8653/9309 |
| shared-h | cse_flat | 96.400 [88.000, 101.500] | 0.000 [0.000, 0.000] | 2.223 [2.203, 2.437] | 0.000 [0.000, 0.000] | 1.85/5.65 | 9332/12324 |
| shared-h | cm_common_flat | 234.400 [181.000, 1742.700] | 0.000 [0.000, 15625.000] | 2.220 [2.200, 3.052] | 0.000 [0.000, 0.000] | 2.92/5.66 | 10628/12516 |
| shared-h | bare_cm_flat | 195.700 [189.100, 258.000] | 0.000 [0.000, 0.000] | 3.020 [2.970, 4.195] | 0.000 [0.000, 0.000] | 3.23/6.65 | 10508/12516 |
| shared-h | cm_recursive | 177.000 [165.700, 199.600] | 0.000 [0.000, 0.000] | 7.880 [7.308, 14.030] | 0.000 [0.000, 244.141] | 3.43/2.88 | 9556/12516 |
| shared-h | public_cm | 245.500 [224.900, 333.100] | 0.000 [0.000, 0.000] | 22.619 [21.827, 24.519] | 0.000 [0.000, 0.000] | 2.68/3.35 | 11300/12516 |
| shared-h | public_cm_diag | 240.300 [232.400, 544.900] | 0.000 [0.000, 0.000] | 29.989 [27.872, 33.255] | 0.000 [0.000, 244.141] | 3.26/2.86 | 11825/12748 |
| equal-separate-h | raw_recursive | 60.200 [53.600, 96.800] | 0.000 [0.000, 0.000] | 4.361 [4.289, 22.075] | 0.000 [0.000, 244.141] | 3.21/3.62 | 5757/6818 |
| equal-separate-h | memo_ast | 59.700 [58.900, 105.400] | 0.000 [0.000, 0.000] | 9.581 [9.414, 11.367] | 0.000 [0.000, 244.141] | 2.17/2.18 | 7141/8256 |
| equal-separate-h | occurrence_flat | 82.200 [70.900, 107.000] | 0.000 [0.000, 0.000] | 2.980 [2.936, 3.713] | 0.000 [0.000, 0.000] | 2.02/4.45 | 9749/10358 |
| equal-separate-h | cse_flat | 110.500 [98.100, 169.000] | 0.000 [0.000, 0.000] | 2.262 [2.181, 2.362] | 0.000 [0.000, 0.000] | 1.81/5.54 | 10428/13973 |
| equal-separate-h | cm_common_flat | 224.600 [188.900, 248.700] | 0.000 [0.000, 0.000] | 2.244 [2.191, 2.258] | 0.000 [0.000, 0.000] | 3.74/6.10 | 11724/13949 |
| equal-separate-h | bare_cm_flat | 228.400 [201.000, 292.200] | 0.000 [0.000, 0.000] | 3.045 [2.967, 3.828] | 0.000 [0.000, 0.000] | 3.77/10.05 | 11660/13949 |
| equal-separate-h | cm_recursive | 197.800 [179.500, 308.200] | 0.000 [0.000, 0.000] | 7.509 [7.006, 12.763] | 0.000 [0.000, 0.000] | 3.27/2.99 | 10596/13949 |
| equal-separate-h | public_cm | 243.800 [238.600, 408.000] | 0.000 [0.000, 0.000] | 24.159 [21.822, 26.647] | 0.000 [0.000, 0.000] | 2.87/3.11 | 12452/13949 |
| equal-separate-h | public_cm_diag | 273.200 [238.300, 643.100] | 0.000 [0.000, 0.000] | 29.102 [27.486, 32.678] | 0.000 [0.000, 0.000] | 2.40/3.01 | 12977/13949 |
| single-consumer-chain-k12 | raw_recursive | 109.900 [93.500, 138.700] | 0.000 [0.000, 0.000] | 9.217 [8.344, 11.602] | 0.000 [0.000, 0.000] | 1.48/2.19 | 18005/18889 |
| single-consumer-chain-k12 | memo_ast | 104.000 [95.100, 172.300] | 0.000 [0.000, 0.000] | 19.987 [18.133, 24.622] | 0.000 [0.000, 244.141] | 1.69/1.62 | 26249/26561 |
| single-consumer-chain-k12 | occurrence_flat | 129.600 [115.500, 140.300] | 0.000 [0.000, 0.000] | 6.044 [5.870, 6.858] | 0.000 [0.000, 0.000] | 1.89/2.71 | 21843/27974 |
| single-consumer-chain-k12 | cse_flat | 172.300 [146.900, 210.700] | 0.000 [0.000, 0.000] | 3.980 [3.842, 4.788] | 0.000 [0.000, 0.000] | 1.77/3.59 | 24091/25696 |
| single-consumer-chain-k12 | cm_common_flat | 447.000 [440.000, 490.800] | 0.000 [0.000, 0.000] | 3.792 [3.694, 5.908] | 0.000 [0.000, 0.000] | 3.63/3.82 | 29643/30732 |
| single-consumer-chain-k12 | bare_cm_flat | 445.100 [392.700, 588.000] | 0.000 [0.000, 15625.000] | 4.930 [4.766, 8.125] | 0.000 [0.000, 0.000] | 3.66/4.46 | 29523/30426 |
| single-consumer-chain-k12 | cm_recursive | 404.100 [378.200, 505.800] | 0.000 [0.000, 0.000] | 12.975 [12.228, 17.081] | 0.000 [0.000, 0.000] | 3.63/2.29 | 30159/30594 |
| single-consumer-chain-k12 | public_cm | 461.900 [437.400, 585.500] | 0.000 [0.000, 15625.000] | 25.144 [22.477, 29.212] | 0.000 [0.000, 244.141] | 3.75/3.25 | 30227/31719 |
| single-consumer-chain-k12 | public_cm_diag | 529.800 [451.800, 713.700] | 0.000 [0.000, 15625.000] | 32.903 [29.869, 41.433] | 0.000 [0.000, 0.000] | 3.50/2.72 | 30880/32207 |
| single-consumer-chain-k12 | cse_words | 233.800 [191.100, 273.300] | 0.000 [0.000, 0.000] | 12.689 [12.427, 14.764] | 0.000 [0.000, 0.000] | 1.59/2.54 | 33275/34311 |
| single-consumer-chain-k12 | cm_words | 481.800 [472.700, 515.800] | 0.000 [0.000, 0.000] | 12.734 [12.594, 14.352] | 0.000 [0.000, 244.141] | 3.36/2.84 | 38659/39695 |
| fixed-structure-output-k4 | raw_recursive | 50.100 [37.300, 53.100] | 0.000 [0.000, 0.000] | 2.862 [2.659, 9.741] | 0.000 [0.000, 0.000] | 1.80/5.16 | 4179/5404 |
| fixed-structure-output-k4 | memo_ast | 45.200 [41.000, 47.300] | 0.000 [0.000, 0.000] | 5.920 [4.956, 9.794] | 0.000 [0.000, 0.000] | 2.87/4.05 | 4899/5600 |
| fixed-structure-output-k4 | occurrence_flat | 59.300 [50.100, 416.400] | 0.000 [0.000, 0.000] | 1.834 [1.816, 2.762] | 0.000 [0.000, 0.000] | 2.55/6.48 | 6527/7045 |
| fixed-structure-output-k4 | cse_flat | 79.000 [70.100, 125.600] | 0.000 [0.000, 0.000] | 1.861 [1.814, 2.719] | 0.000 [0.000, 0.000] | 3.01/6.48 | 7567/10173 |
| fixed-structure-output-k4 | cm_common_flat | 141.400 [127.000, 157.500] | 0.000 [0.000, 0.000] | 1.867 [1.856, 1.992] | 0.000 [0.000, 0.000] | 3.08/6.53 | 8351/8957 |
| fixed-structure-output-k4 | bare_cm_flat | 129.000 [122.700, 310.200] | 0.000 [0.000, 0.000] | 2.600 [2.573, 2.945] | 0.000 [0.000, 0.000] | 3.23/7.43 | 8231/8957 |
| fixed-structure-output-k4 | cm_recursive | 122.700 [108.400, 135.100] | 0.000 [0.000, 0.000] | 6.517 [5.773, 12.331] | 0.000 [0.000, 0.000] | 3.91/3.07 | 7255/8957 |
| fixed-structure-output-k4 | public_cm | 188.600 [169.100, 267.100] | 0.000 [0.000, 0.000] | 22.678 [20.839, 35.802] | 0.000 [0.000, 244.141] | 2.73/3.54 | 9023/10001 |
| fixed-structure-output-k4 | public_cm_diag | 200.200 [170.500, 359.400] | 0.000 [0.000, 0.000] | 29.236 [27.202, 38.825] | 0.000 [0.000, 0.000] | 2.76/3.21 | 9548/10473 |
| fixed-structure-output-k4 | dense_cm | 289.600 [228.500, 362.800] | 0.000 [0.000, 0.000] | 47.128 [39.119, 74.278] | 0.000 [0.000, 244.141] | 2.11/2.25 | 13309/17847 |
| fixed-structure-output-k8 | raw_recursive | 73.800 [59.000, 110.400] | 0.000 [0.000, 0.000] | 2.958 [2.864, 10.302] | 0.000 [0.000, 0.000] | 1.60/4.63 | 4797/5404 |
| fixed-structure-output-k8 | memo_ast | 66.100 [60.300, 84.000] | 0.000 [0.000, 0.000] | 5.616 [5.228, 6.334] | 0.000 [0.000, 0.000] | 2.03/3.07 | 5601/6248 |
| fixed-structure-output-k8 | occurrence_flat | 79.300 [71.600, 91.800] | 0.000 [0.000, 0.000] | 2.023 [2.002, 2.053] | 0.000 [0.000, 0.000] | 2.16/6.36 | 7145/7633 |
| fixed-structure-output-k8 | cse_flat | 105.700 [93.100, 145.400] | 0.000 [0.000, 15625.000] | 2.056 [2.025, 2.947] | 0.000 [0.000, 0.000] | 1.60/6.55 | 8185/10173 |
| fixed-structure-output-k8 | cm_common_flat | 158.000 [147.100, 498.700] | 0.000 [0.000, 0.000] | 2.052 [2.002, 2.745] | 0.000 [0.000, 0.000] | 2.88/6.34 | 8969/9457 |
| fixed-structure-output-k8 | bare_cm_flat | 155.800 [143.300, 242.600] | 0.000 [0.000, 0.000] | 2.809 [2.767, 2.916] | 0.000 [0.000, 0.000] | 2.81/7.56 | 8849/9300 |
| fixed-structure-output-k8 | cm_recursive | 145.000 [130.300, 201.800] | 0.000 [0.000, 0.000] | 6.283 [5.959, 8.022] | 0.000 [0.000, 0.000] | 3.68/3.31 | 7957/8957 |
| fixed-structure-output-k8 | public_cm | 213.100 [191.300, 554.000] | 0.000 [0.000, 0.000] | 23.636 [21.719, 45.248] | 0.000 [0.000, 244.141] | 2.56/3.33 | 9641/10649 |
| fixed-structure-output-k8 | public_cm_diag | 243.700 [223.500, 487.000] | 0.000 [0.000, 0.000] | 35.539 [27.731, 51.442] | 0.000 [0.000, 244.141] | 2.21/3.71 | 10198/11121 |
| fixed-structure-output-k8 | cse_words | 138.500 [126.400, 232.100] | 0.000 [0.000, 0.000] | 6.998 [6.436, 13.936] | 0.000 [0.000, 244.141] | 1.88/5.41 | 10757/11281 |
| fixed-structure-output-k8 | cm_words | 273.600 [180.700, 363.100] | 0.000 [0.000, 0.000] | 6.495 [6.347, 8.133] | 0.000 [0.000, 0.000] | 1.75/3.95 | 11901/12425 |
| fixed-structure-output-k16 | raw_recursive | 251.200 [189.000, 903.300] | 0.000 [0.000, 0.000] | 23.694 [21.920, 26.011] | 0.000 [0.000, 244.141] | 1.08/1.60 | 161597/188468 |
| fixed-structure-output-k16 | memo_ast | 239.500 [173.200, 314.600] | 0.000 [0.000, 0.000] | 38.172 [33.652, 50.861] | 0.000 [0.000, 0.000] | 1.04/1.33 | 188513/198128 |
| fixed-structure-output-k16 | occurrence_flat | 254.400 [184.900, 283.100] | 0.000 [0.000, 0.000] | 19.389 [17.914, 24.077] | 0.000 [0.000, 0.000] | 1.26/1.68 | 163945/199756 |
| fixed-structure-output-k16 | cse_flat | 212.300 [210.700, 237.500] | 0.000 [0.000, 0.000] | 19.431 [17.986, 23.267] | 0.000 [0.000, 244.141] | 1.67/1.78 | 164985/200796 |
| fixed-structure-output-k16 | cm_common_flat | 280.700 [269.400, 368.700] | 0.000 [0.000, 0.000] | 19.320 [18.091, 25.958] | 0.000 [0.000, 244.141] | 2.24/1.67 | 165769/201580 |
| fixed-structure-output-k16 | bare_cm_flat | 349.900 [262.000, 430.500] | 0.000 [0.000, 15625.000] | 19.434 [18.962, 25.683] | 0.000 [0.000, 0.000] | 1.85/2.14 | 165649/201460 |
| fixed-structure-output-k16 | cm_recursive | 266.500 [255.300, 297.100] | 0.000 [0.000, 0.000] | 39.397 [34.441, 45.262] | 0.000 [0.000, 244.141] | 2.10/1.54 | 190869/200540 |
| fixed-structure-output-k16 | public_cm | 390.800 [359.700, 531.800] | 0.000 [0.000, 0.000] | 43.686 [39.066, 54.753] | 0.000 [0.000, 244.141] | 1.58/2.22 | 166441/202841 |
| fixed-structure-output-k16 | public_cm_diag | 361.100 [344.000, 906.800] | 0.000 [0.000, 0.000] | 50.017 [46.120, 60.589] | 0.000 [0.000, 0.000] | 1.95/2.23 | 167094/203329 |
| fixed-structure-output-k16 | cse_words | 386.600 [357.500, 505.000] | 0.000 [0.000, 15625.000] | 23.333 [22.695, 30.242] | 0.000 [0.000, 0.000] | 1.31/1.86 | 315533/324761 |
| fixed-structure-output-k16 | cm_words | 546.000 [410.600, 700.200] | 0.000 [0.000, 15625.000] | 23.137 [22.450, 25.392] | 0.000 [0.000, 244.141] | 1.35/1.88 | 316677/325905 |
| fixed-structure-output-k16 | dense_cm | 378.000 [369.600, 586.400] | 0.000 [0.000, 0.000] | 138.206 [121.502, 204.050] | 244.141 [0.000, 244.141] | 1.65/1.27 | 79533/211109 |
| fixed-structure-output-k18 | raw_recursive | 817.500 [760.500, 1152.800] | 0.000 [0.000, 0.000] | 93.575 [87.344, 140.348] | 0.000 [0.000, 244.141] | 1.01/1.16 | 701805/808964 |
| fixed-structure-output-k18 | memo_ast | 841.600 [583.800, 857.000] | 0.000 [0.000, 0.000] | 131.214 [124.891, 147.105] | 244.141 [0.000, 244.141] | 1.12/1.07 | 807369/844840 |
| fixed-structure-output-k18 | occurrence_flat | 880.400 [602.800, 1037.700] | 0.000 [0.000, 15625.000] | 70.333 [67.478, 77.331] | 0.000 [0.000, 244.141] | 0.86/1.22 | 704153/846468 |
| fixed-structure-output-k18 | cse_flat | 675.700 [626.000, 812.000] | 0.000 [0.000, 0.000] | 68.291 [66.359, 78.464] | 0.000 [0.000, 244.141] | 1.04/1.26 | 705193/847508 |
| fixed-structure-output-k18 | cm_common_flat | 774.100 [699.600, 789.500] | 0.000 [0.000, 0.000] | 70.572 [68.577, 75.017] | 0.000 [0.000, 244.141] | 1.60/1.14 | 705977/848292 |
| fixed-structure-output-k18 | bare_cm_flat | 770.600 [699.800, 1459.800] | 0.000 [0.000, 15625.000] | 70.256 [67.084, 124.186] | 0.000 [0.000, 244.141] | 1.34/1.55 | 705857/848172 |
| fixed-structure-output-k18 | cm_recursive | 719.000 [681.800, 1162.300] | 0.000 [0.000, 0.000] | 136.064 [131.611, 168.409] | 244.141 [0.000, 244.141] | 1.99/1.11 | 809725/847252 |
| fixed-structure-output-k18 | public_cm | 1023.200 [797.400, 1694.300] | 0.000 [0.000, 15625.000] | 100.769 [93.505, 103.719] | 0.000 [0.000, 244.141] | 1.31/1.70 | 706649/849553 |
| fixed-structure-output-k18 | public_cm_diag | 927.900 [761.000, 1336.500] | 0.000 [0.000, 0.000] | 104.862 [98.205, 117.202] | 244.141 [0.000, 244.141] | 1.24/1.60 | 707302/850041 |
| fixed-structure-output-k18 | cse_words | 1498.000 [1290.100, 1655.400] | 0.000 [0.000, 0.000] | 72.411 [68.900, 81.194] | 0.000 [0.000, 244.141] | 1.00/1.31 | 1362295/1397739 |
| fixed-structure-output-k18 | cm_words | 1750.200 [1233.300, 2657.700] | 0.000 [0.000, 0.000] | 73.341 [69.233, 75.141] | 0.000 [0.000, 244.141] | 1.01/1.28 | 1363439/1398883 |

## 9. Reproduction and disposition

Run `python -B summarize_ladder.py --summary <new-audit-json> --report <new-audit-md>` from this audit directory. Inputs are `ladder-run-002.json` only; output files must be new and remain in this audit directory. The source hash is checked into the resulting summary. No profiling, fixture execution or timings occur during this analysis.

No scientific disposition changed. Remaining attribution gaps require matching exclusive phase/CPU/allocation evidence on the same caller contract; current data must retain them as unresolved. No further timing is requested by this summary.
