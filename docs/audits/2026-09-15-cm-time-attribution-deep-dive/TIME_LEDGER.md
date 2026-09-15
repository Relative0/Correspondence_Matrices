# Time ledger — caller boundaries, exclusive phases and delivery

All new observations are local diagnostics on disclosed development fixtures at `e334de594262059cc18cf37eaab56b0f79e94843`. This ledger includes **all 137 corrected ladder cells and all 70 task cells**. Nothing is pooled into a benchmark claim. No scientific disposition changed.

## 1. Sources, units and denominator rules

| Source | Records | Used for |
|---|---:|---|
| [ladder_summary.json](ladder_summary.json) → `ladder-run-002.json` | 137 | Seven-repeat uninstrumented cold and resident timings; separate three-pass exclusive phases, cProfile and tracemalloc |
| [TASK_SUMMARY.json](TASK_SUMMARY.json) → `task-run-001/TASK_RESULTS.json` | 70 | Five-repeat task caller timings; separate phases and memory |
| [frozen_evidence.json](frozen_evidence.json) | predecessor records | Arithmetic-only reinterpretation; no fixture replay |

The structured [PROFILE_RESULTS.json](PROFILE_RESULTS.json) ties these sources together. Every cell's absolute phase wall/CPU time, percentage of its own instrumented caller, counts/helpers and memory details are in the linked summaries. Full seven-repeat min/max ranges and instrument dilation for all137 ladder cells also appear in [LADDER_FINDINGS.md](LADDER_FINDINGS.md). [TASK_LEDGER.md](TASK_LEDGER.md) includes nested public-family subspans; those are annotations inside a caller and must not be added again.

**Uninstrumented ladder units:** µs per operation. Cold q1 includes supplied JSON parse/decode, setup, execution, packed delivery and exact guard; it excludes process launch and disk loading. Resident q64 is an already-initialized 64-operation session divided by64; warm-up/setup is outside it. **Task units:** ms for the whole requested task, including all q contexts or variants, not per query. Task fixture loading/generation, adapters, output and checks are charged according to [TASK_METHODS.md](TASK_METHODS.md). Dense output arms have a different output contract and remain labelled.

**Phase denominator:** each table divides exclusive phase sums by its own phase-pass caller sum. Instrumented phase percentages are not percentages of the faster uninstrumented caller. Parent/cumulative spans are never added to children. Separate medians do not form an additive partition. Allocation inside arithmetic and word conversion inside grouped evaluators remain grouped; absent exclusive evidence is unknown.

**CPU limitation:** 1795/1918 ladder whole-pass CPU samples are zero; smallest observed positive value is 15.625 ms. Task observations are likewise quantized. API-reported resolution does not make submillisecond CPU shares reliable. A zero CPU median means no resolved median CPU increment, not zero work.

Only corrected `ladder-run-002.json` supports this ledger. `ladder-run-001.json` and `ladder-smoke-001.json` are preserved but superseded because the original tracer missed imported evaluator aliases. No corrected totals are inferred by editing those records.

## 2. Process startup, imports and unresolved outside-script cost

Separate fresh-process pass; already-imported library cells above incur no analogous per-call startup phase. Parent wall includes process launch, script work, stdout delivery and shutdown. Import span begins at script entry after importing `time`. Residual is parent wall minus script entry-to-payload wall; it cannot be uniquely split into launch, transport, early imports or shutdown. Child process CPU is a separate whole-process observation and is not summed with parent wall.

| Process repeat | Parent caller wall ms | Script imports wall/CPU ms | Script entry→payload wall ms | Outside-script residual wall ms | Child process CPU ms |
|---|---:|---:|---:|---:|---:|
| 1 | 378.000 | 260.225/250.000 | 269.601 | 108.398 | 328.125 |
| 2 | 378.851 | 260.321/250.000 | 270.127 | 108.724 | 328.125 |
| 3 | 379.870 | 269.184/250.000 | 279.057 | 100.813 | 296.875 |

## 3. All137 ladder cells: uninstrumented medians

Wall and CPU are µs per operation. Exact byte output matched on every row. Complete ranges, all phase fields and memory scopes remain in `ladder_summary.json.cells`; the table retains every arm, including diagnostic wrapper and dense-contract controls.

| Case | Arm | Cold wall µs | Cold CPU µs | Resident wall µs/call | Resident CPU µs/call | Output bytes |
|---|---|---:|---:|---:|---:|---:|
| random-shared-seed0-k8 | raw_recursive | 135.200 | 0.000 | 14.137 | 0.000 | 32 |
| random-shared-seed0-k8 | memo_ast | 127.100 | 0.000 | 18.130 | 0.000 | 32 |
| random-shared-seed0-k8 | occurrence_flat | 196.800 | 0.000 | 7.250 | 0.000 | 32 |
| random-shared-seed0-k8 | cse_flat | 199.700 | 0.000 | 5.428 | 0.000 | 32 |
| random-shared-seed0-k8 | cm_common_flat | 443.500 | 0.000 | 5.417 | 0.000 | 32 |
| random-shared-seed0-k8 | bare_cm_flat | 427.300 | 0.000 | 6.311 | 0.000 | 32 |
| random-shared-seed0-k8 | cm_recursive | 390.200 | 0.000 | 18.916 | 0.000 | 32 |
| random-shared-seed0-k8 | public_cm | 470.800 | 0.000 | 28.331 | 0.000 | 32 |
| random-shared-seed0-k8 | public_cm_diag | 477.100 | 0.000 | 33.177 | 0.000 | 32 |
| random-shared-seed0-k8 | cse_words | 269.700 | 0.000 | 23.370 | 0.000 | 32 |
| random-shared-seed0-k8 | cm_words | 506.500 | 0.000 | 23.164 | 0.000 | 32 |
| random-shared-seed1-k8 | raw_recursive | 118.200 | 0.000 | 14.477 | 0.000 | 32 |
| random-shared-seed1-k8 | memo_ast | 124.500 | 0.000 | 16.172 | 0.000 | 32 |
| random-shared-seed1-k8 | occurrence_flat | 166.000 | 0.000 | 8.453 | 0.000 | 32 |
| random-shared-seed1-k8 | cse_flat | 213.600 | 0.000 | 4.798 | 0.000 | 32 |
| random-shared-seed1-k8 | cm_common_flat | 431.800 | 0.000 | 4.573 | 0.000 | 32 |
| random-shared-seed1-k8 | bare_cm_flat | 403.400 | 0.000 | 5.427 | 0.000 | 32 |
| random-shared-seed1-k8 | cm_recursive | 368.200 | 0.000 | 18.206 | 0.000 | 32 |
| random-shared-seed1-k8 | public_cm | 465.300 | 0.000 | 26.334 | 0.000 | 32 |
| random-shared-seed1-k8 | public_cm_diag | 471.000 | 0.000 | 34.202 | 0.000 | 32 |
| random-shared-seed1-k8 | cse_words | 265.200 | 0.000 | 20.414 | 0.000 | 32 |
| random-shared-seed1-k8 | cm_words | 519.200 | 0.000 | 19.966 | 0.000 | 32 |
| random-existing-k3 | raw_recursive | 97.300 | 0.000 | 19.359 | 0.000 | 1 |
| random-existing-k3 | memo_ast | 85.800 | 0.000 | 15.137 | 0.000 | 1 |
| random-existing-k3 | occurrence_flat | 157.300 | 0.000 | 9.386 | 0.000 | 1 |
| random-existing-k3 | cse_flat | 148.300 | 0.000 | 3.781 | 0.000 | 1 |
| random-existing-k3 | cm_common_flat | 318.100 | 0.000 | 2.525 | 0.000 | 1 |
| random-existing-k3 | bare_cm_flat | 315.300 | 0.000 | 3.225 | 0.000 | 1 |
| random-existing-k3 | cm_recursive | 306.400 | 0.000 | 8.606 | 0.000 | 1 |
| random-existing-k3 | public_cm | 383.400 | 0.000 | 22.833 | 0.000 | 1 |
| random-existing-k3 | public_cm_diag | 373.400 | 0.000 | 31.666 | 0.000 | 1 |
| random-existing-k8 | raw_recursive | 97.000 | 0.000 | 6.913 | 0.000 | 32 |
| random-existing-k8 | memo_ast | 99.200 | 0.000 | 18.209 | 0.000 | 32 |
| random-existing-k8 | occurrence_flat | 142.900 | 0.000 | 4.305 | 0.000 | 32 |
| random-existing-k8 | cse_flat | 156.400 | 0.000 | 3.458 | 0.000 | 32 |
| random-existing-k8 | cm_common_flat | 388.500 | 0.000 | 3.489 | 0.000 | 32 |
| random-existing-k8 | bare_cm_flat | 341.700 | 0.000 | 4.389 | 0.000 | 32 |
| random-existing-k8 | cm_recursive | 312.600 | 0.000 | 13.348 | 0.000 | 32 |
| random-existing-k8 | public_cm | 399.500 | 0.000 | 24.755 | 0.000 | 32 |
| random-existing-k8 | public_cm_diag | 411.100 | 0.000 | 31.397 | 0.000 | 32 |
| random-existing-k8 | cse_words | 237.400 | 0.000 | 14.747 | 0.000 | 32 |
| random-existing-k8 | cm_words | 423.700 | 0.000 | 15.050 | 0.000 | 32 |
| random-existing-k12 | raw_recursive | 114.000 | 0.000 | 17.359 | 0.000 | 512 |
| random-existing-k12 | memo_ast | 102.900 | 0.000 | 21.075 | 0.000 | 512 |
| random-existing-k12 | occurrence_flat | 138.600 | 0.000 | 14.139 | 0.000 | 512 |
| random-existing-k12 | cse_flat | 165.800 | 0.000 | 9.306 | 0.000 | 512 |
| random-existing-k12 | cm_common_flat | 340.100 | 0.000 | 6.817 | 0.000 | 512 |
| random-existing-k12 | bare_cm_flat | 337.800 | 0.000 | 7.652 | 0.000 | 512 |
| random-existing-k12 | cm_recursive | 288.400 | 0.000 | 16.817 | 0.000 | 512 |
| random-existing-k12 | public_cm | 499.800 | 0.000 | 28.334 | 0.000 | 512 |
| random-existing-k12 | public_cm_diag | 509.200 | 0.000 | 35.289 | 0.000 | 512 |
| random-existing-k12 | cse_words | 291.200 | 0.000 | 19.755 | 0.000 | 512 |
| random-existing-k12 | cm_words | 498.800 | 0.000 | 13.363 | 0.000 | 512 |
| random-existing-k16 | raw_recursive | 309.400 | 0.000 | 56.650 | 0.000 | 8192 |
| random-existing-k16 | memo_ast | 300.400 | 0.000 | 94.181 | 0.000 | 8192 |
| random-existing-k16 | occurrence_flat | 416.300 | 0.000 | 46.189 | 0.000 | 8192 |
| random-existing-k16 | cse_flat | 337.800 | 0.000 | 36.256 | 0.000 | 8192 |
| random-existing-k16 | cm_common_flat | 500.700 | 0.000 | 36.234 | 0.000 | 8192 |
| random-existing-k16 | bare_cm_flat | 535.700 | 0.000 | 37.798 | 0.000 | 8192 |
| random-existing-k16 | cm_recursive | 503.500 | 0.000 | 73.236 | 0.000 | 8192 |
| random-existing-k16 | public_cm | 613.000 | 0.000 | 62.300 | 0.000 | 8192 |
| random-existing-k16 | public_cm_diag | 617.800 | 0.000 | 69.502 | 0.000 | 8192 |
| random-existing-k16 | cse_words | 497.600 | 0.000 | 38.367 | 0.000 | 8192 |
| random-existing-k16 | cm_words | 675.700 | 0.000 | 38.853 | 0.000 | 8192 |
| shared-h | raw_recursive | 63.600 | 0.000 | 4.450 | 0.000 | 4 |
| shared-h | memo_ast | 58.000 | 0.000 | 7.528 | 0.000 | 4 |
| shared-h | occurrence_flat | 80.200 | 0.000 | 2.939 | 0.000 | 4 |
| shared-h | cse_flat | 96.400 | 0.000 | 2.223 | 0.000 | 4 |
| shared-h | cm_common_flat | 234.400 | 0.000 | 2.220 | 0.000 | 4 |
| shared-h | bare_cm_flat | 195.700 | 0.000 | 3.020 | 0.000 | 4 |
| shared-h | cm_recursive | 177.000 | 0.000 | 7.880 | 0.000 | 4 |
| shared-h | public_cm | 245.500 | 0.000 | 22.619 | 0.000 | 4 |
| shared-h | public_cm_diag | 240.300 | 0.000 | 29.989 | 0.000 | 4 |
| equal-separate-h | raw_recursive | 60.200 | 0.000 | 4.361 | 0.000 | 4 |
| equal-separate-h | memo_ast | 59.700 | 0.000 | 9.581 | 0.000 | 4 |
| equal-separate-h | occurrence_flat | 82.200 | 0.000 | 2.980 | 0.000 | 4 |
| equal-separate-h | cse_flat | 110.500 | 0.000 | 2.262 | 0.000 | 4 |
| equal-separate-h | cm_common_flat | 224.600 | 0.000 | 2.244 | 0.000 | 4 |
| equal-separate-h | bare_cm_flat | 228.400 | 0.000 | 3.045 | 0.000 | 4 |
| equal-separate-h | cm_recursive | 197.800 | 0.000 | 7.509 | 0.000 | 4 |
| equal-separate-h | public_cm | 243.800 | 0.000 | 24.159 | 0.000 | 4 |
| equal-separate-h | public_cm_diag | 273.200 | 0.000 | 29.102 | 0.000 | 4 |
| single-consumer-chain-k12 | raw_recursive | 109.900 | 0.000 | 9.217 | 0.000 | 512 |
| single-consumer-chain-k12 | memo_ast | 104.000 | 0.000 | 19.987 | 0.000 | 512 |
| single-consumer-chain-k12 | occurrence_flat | 129.600 | 0.000 | 6.044 | 0.000 | 512 |
| single-consumer-chain-k12 | cse_flat | 172.300 | 0.000 | 3.980 | 0.000 | 512 |
| single-consumer-chain-k12 | cm_common_flat | 447.000 | 0.000 | 3.792 | 0.000 | 512 |
| single-consumer-chain-k12 | bare_cm_flat | 445.100 | 0.000 | 4.930 | 0.000 | 512 |
| single-consumer-chain-k12 | cm_recursive | 404.100 | 0.000 | 12.975 | 0.000 | 512 |
| single-consumer-chain-k12 | public_cm | 461.900 | 0.000 | 25.144 | 0.000 | 512 |
| single-consumer-chain-k12 | public_cm_diag | 529.800 | 0.000 | 32.903 | 0.000 | 512 |
| single-consumer-chain-k12 | cse_words | 233.800 | 0.000 | 12.689 | 0.000 | 512 |
| single-consumer-chain-k12 | cm_words | 481.800 | 0.000 | 12.734 | 0.000 | 512 |
| fixed-structure-output-k4 | raw_recursive | 50.100 | 0.000 | 2.862 | 0.000 | 2 |
| fixed-structure-output-k4 | memo_ast | 45.200 | 0.000 | 5.920 | 0.000 | 2 |
| fixed-structure-output-k4 | occurrence_flat | 59.300 | 0.000 | 1.834 | 0.000 | 2 |
| fixed-structure-output-k4 | cse_flat | 79.000 | 0.000 | 1.861 | 0.000 | 2 |
| fixed-structure-output-k4 | cm_common_flat | 141.400 | 0.000 | 1.867 | 0.000 | 2 |
| fixed-structure-output-k4 | bare_cm_flat | 129.000 | 0.000 | 2.600 | 0.000 | 2 |
| fixed-structure-output-k4 | cm_recursive | 122.700 | 0.000 | 6.517 | 0.000 | 2 |
| fixed-structure-output-k4 | public_cm | 188.600 | 0.000 | 22.678 | 0.000 | 2 |
| fixed-structure-output-k4 | public_cm_diag | 200.200 | 0.000 | 29.236 | 0.000 | 2 |
| fixed-structure-output-k4 | dense_cm | 289.600 | 0.000 | 47.128 | 0.000 | 16 |
| fixed-structure-output-k8 | raw_recursive | 73.800 | 0.000 | 2.958 | 0.000 | 32 |
| fixed-structure-output-k8 | memo_ast | 66.100 | 0.000 | 5.616 | 0.000 | 32 |
| fixed-structure-output-k8 | occurrence_flat | 79.300 | 0.000 | 2.023 | 0.000 | 32 |
| fixed-structure-output-k8 | cse_flat | 105.700 | 0.000 | 2.056 | 0.000 | 32 |
| fixed-structure-output-k8 | cm_common_flat | 158.000 | 0.000 | 2.052 | 0.000 | 32 |
| fixed-structure-output-k8 | bare_cm_flat | 155.800 | 0.000 | 2.809 | 0.000 | 32 |
| fixed-structure-output-k8 | cm_recursive | 145.000 | 0.000 | 6.283 | 0.000 | 32 |
| fixed-structure-output-k8 | public_cm | 213.100 | 0.000 | 23.636 | 0.000 | 32 |
| fixed-structure-output-k8 | public_cm_diag | 243.700 | 0.000 | 35.539 | 0.000 | 32 |
| fixed-structure-output-k8 | cse_words | 138.500 | 0.000 | 6.998 | 0.000 | 32 |
| fixed-structure-output-k8 | cm_words | 273.600 | 0.000 | 6.495 | 0.000 | 32 |
| fixed-structure-output-k16 | raw_recursive | 251.200 | 0.000 | 23.694 | 0.000 | 8192 |
| fixed-structure-output-k16 | memo_ast | 239.500 | 0.000 | 38.172 | 0.000 | 8192 |
| fixed-structure-output-k16 | occurrence_flat | 254.400 | 0.000 | 19.389 | 0.000 | 8192 |
| fixed-structure-output-k16 | cse_flat | 212.300 | 0.000 | 19.431 | 0.000 | 8192 |
| fixed-structure-output-k16 | cm_common_flat | 280.700 | 0.000 | 19.320 | 0.000 | 8192 |
| fixed-structure-output-k16 | bare_cm_flat | 349.900 | 0.000 | 19.434 | 0.000 | 8192 |
| fixed-structure-output-k16 | cm_recursive | 266.500 | 0.000 | 39.397 | 0.000 | 8192 |
| fixed-structure-output-k16 | public_cm | 390.800 | 0.000 | 43.686 | 0.000 | 8192 |
| fixed-structure-output-k16 | public_cm_diag | 361.100 | 0.000 | 50.017 | 0.000 | 8192 |
| fixed-structure-output-k16 | cse_words | 386.600 | 0.000 | 23.333 | 0.000 | 8192 |
| fixed-structure-output-k16 | cm_words | 546.000 | 0.000 | 23.137 | 0.000 | 8192 |
| fixed-structure-output-k16 | dense_cm | 378.000 | 0.000 | 138.206 | 244.141 | 65536 |
| fixed-structure-output-k18 | raw_recursive | 817.500 | 0.000 | 93.575 | 0.000 | 32768 |
| fixed-structure-output-k18 | memo_ast | 841.600 | 0.000 | 131.214 | 244.141 | 32768 |
| fixed-structure-output-k18 | occurrence_flat | 880.400 | 0.000 | 70.333 | 0.000 | 32768 |
| fixed-structure-output-k18 | cse_flat | 675.700 | 0.000 | 68.291 | 0.000 | 32768 |
| fixed-structure-output-k18 | cm_common_flat | 774.100 | 0.000 | 70.572 | 0.000 | 32768 |
| fixed-structure-output-k18 | bare_cm_flat | 770.600 | 0.000 | 70.256 | 0.000 | 32768 |
| fixed-structure-output-k18 | cm_recursive | 719.000 | 0.000 | 136.064 | 244.141 | 32768 |
| fixed-structure-output-k18 | public_cm | 1023.200 | 0.000 | 100.769 | 0.000 | 32768 |
| fixed-structure-output-k18 | public_cm_diag | 927.900 | 0.000 | 104.862 | 244.141 | 32768 |
| fixed-structure-output-k18 | cse_words | 1498.000 | 0.000 | 72.411 | 0.000 | 32768 |
| fixed-structure-output-k18 | cm_words | 1750.200 | 0.000 | 73.341 | 0.000 | 32768 |

## 4. All70 task cells: uninstrumented medians

Times are **ms for the whole task**, including q1/q64 or a complete family as labelled. All rows are `ok` with exact correctness. Input loading/conversion dominates some small assignment tasks; symbolic minimization dominates the balanced expression. These are task-specific contracts, so the ms values must not be directly ranked against the µs complete-output prepared ladder.

| Task | Case | Arm | q | Wall ms/task | CPU ms/task | Output bytes |
|---|---|---|---:|---:|---:|---:|
| assignment_batch | absorption-k4 | raw_batch | 1 | 3.9812 | 0.0000 | 512 |
| assignment_batch | absorption-k4 | cse_batch | 1 | 3.9598 | 0.0000 | 512 |
| assignment_batch | absorption-k4 | cm_batch | 1 | 4.0555 | 0.0000 | 512 |
| assignment_batch | absorption-k4 | sympy_cse_off | 1 | 4.7315 | 0.0000 | 512 |
| assignment_batch | absorption-k4 | sympy_cse_on | 1 | 5.0282 | 15.6250 | 512 |
| assignment_batch | balanced-k8 | raw_batch | 1 | 5.9343 | 0.0000 | 512 |
| assignment_batch | balanced-k8 | cse_batch | 1 | 6.0367 | 0.0000 | 512 |
| assignment_batch | balanced-k8 | cm_batch | 1 | 5.9401 | 15.6250 | 512 |
| assignment_batch | balanced-k8 | sympy_cse_off | 1 | 8.2599 | 15.6250 | 512 |
| assignment_batch | balanced-k8 | sympy_cse_on | 1 | 8.4218 | 15.6250 | 512 |
| restriction | balanced-k8 | cse_packed | 1 | 0.4385 | 0.0000 | 8 |
| restriction | balanced-k8 | cm_packed | 1 | 0.5754 | 0.0000 | 8 |
| restriction | balanced-k8 | cse_packed | 64 | 1.1534 | 0.0000 | 512 |
| restriction | balanced-k8 | cm_packed | 64 | 1.1359 | 0.0000 | 512 |
| exact_count | contradiction-k4 | cse_packed | 1 | 0.3669 | 0.0000 | 11 |
| exact_count | contradiction-k4 | cm_packed | 1 | 0.3736 | 0.0000 | 11 |
| exact_count | contradiction-k4 | sympy_task | 1 | 0.5335 | 0.0000 | 11 |
| exact_count | balanced-k8 | cse_packed | 1 | 0.7574 | 0.0000 | 13 |
| exact_count | balanced-k8 | cm_packed | 1 | 0.8898 | 0.0000 | 13 |
| exact_count | balanced-k8 | sympy_task | 1 | 22.1069 | 15.6250 | 13 |
| sat_status | contradiction-k4 | cse_packed | 1 | 0.3657 | 0.0000 | 15 |
| sat_status | contradiction-k4 | cm_packed | 1 | 0.3844 | 0.0000 | 15 |
| sat_status | contradiction-k4 | sympy_task | 1 | 0.4973 | 0.0000 | 15 |
| sat_status | balanced-k8 | cse_packed | 1 | 0.5883 | 0.0000 | 14 |
| sat_status | balanced-k8 | cm_packed | 1 | 0.7619 | 0.0000 | 14 |
| sat_status | balanced-k8 | sympy_task | 1 | 1.4853 | 0.0000 | 14 |
| equivalence_status | contradiction-k4 | cse_packed | 1 | 0.4395 | 0.0000 | 15 |
| equivalence_status | contradiction-k4 | cm_packed | 1 | 0.4636 | 0.0000 | 15 |
| equivalence_status | contradiction-k4 | sympy_task | 1 | 0.7717 | 0.0000 | 15 |
| equivalence_status | balanced-k8 | cse_packed | 1 | 0.7918 | 0.0000 | 14 |
| equivalence_status | balanced-k8 | cm_packed | 1 | 0.9442 | 0.0000 | 14 |
| equivalence_status | balanced-k8 | sympy_task | 1 | 1.1484 | 0.0000 | 14 |
| simplified_expression | absorption-k4 | cse_shared_minimizer | 1 | 0.5343 | 0.0000 | 12 |
| simplified_expression | absorption-k4 | cm_shared_minimizer | 1 | 0.6238 | 0.0000 | 12 |
| simplified_expression | absorption-k4 | sympy_default | 1 | 0.6864 | 0.0000 | 12 |
| simplified_expression | absorption-k4 | sympy_forced | 1 | 0.6159 | 0.0000 | 12 |
| simplified_expression | balanced-k8 | cse_shared_minimizer | 1 | 69.3551 | 62.5000 | 996 |
| simplified_expression | balanced-k8 | cm_shared_minimizer | 1 | 66.3687 | 62.5000 | 996 |
| simplified_expression | balanced-k8 | sympy_default | 1 | 75.6585 | 78.1250 | 996 |
| simplified_expression | balanced-k8 | sympy_forced | 1 | 76.3735 | 78.1250 | 996 |
| family | identical_seed2 | cse_family | 1 | 1.7528 | 0.0000 | 16 |
| family | identical_seed2 | cm_cache_off | 1 | 2.8438 | 0.0000 | 16 |
| family | identical_seed2 | cm_cache_on | 1 | 2.1196 | 0.0000 | 16 |
| family | identical_seed2 | public_cache_off | 1 | 5.7521 | 0.0000 | 16 |
| family | identical_seed2 | public_cache_on | 1 | 4.7493 | 0.0000 | 16 |
| family | shared_seed2 | cse_family | 1 | 2.2398 | 0.0000 | 16 |
| family | shared_seed2 | cm_cache_off | 1 | 3.4623 | 0.0000 | 16 |
| family | shared_seed2 | cm_cache_on | 1 | 3.8617 | 0.0000 | 16 |
| family | shared_seed2 | public_cache_off | 1 | 7.0723 | 15.6250 | 16 |
| family | shared_seed2 | public_cache_on | 1 | 7.4136 | 0.0000 | 16 |
| family | composition_seed3 | cse_family | 1 | 1.8532 | 0.0000 | 10 |
| family | composition_seed3 | cm_cache_off | 1 | 2.8795 | 0.0000 | 10 |
| family | composition_seed3 | cm_cache_on | 1 | 3.3797 | 0.0000 | 10 |
| family | composition_seed3 | public_cache_off | 1 | 5.3707 | 15.6250 | 10 |
| family | composition_seed3 | public_cache_on | 1 | 6.3810 | 0.0000 | 10 |
| family | mutation_seed3_0 | cse_family | 1 | 1.5751 | 0.0000 | 10 |
| family | mutation_seed3_0 | cm_cache_off | 1 | 2.1982 | 0.0000 | 10 |
| family | mutation_seed3_0 | cm_cache_on | 1 | 2.1900 | 0.0000 | 10 |
| family | mutation_seed3_0 | public_cache_off | 1 | 3.8142 | 0.0000 | 10 |
| family | mutation_seed3_0 | public_cache_on | 1 | 4.1708 | 0.0000 | 10 |
| family | mutation_seed3_0.15 | cse_family | 1 | 1.6388 | 0.0000 | 10 |
| family | mutation_seed3_0.15 | cm_cache_off | 1 | 2.4275 | 0.0000 | 10 |
| family | mutation_seed3_0.15 | cm_cache_on | 1 | 2.6319 | 0.0000 | 10 |
| family | mutation_seed3_0.15 | public_cache_off | 1 | 4.2250 | 0.0000 | 10 |
| family | mutation_seed3_0.15 | public_cache_on | 1 | 4.5412 | 0.0000 | 10 |
| family | mutation_seed3_1 | cse_family | 1 | 7.3941 | 0.0000 | 10 |
| family | mutation_seed3_1 | cm_cache_off | 1 | 9.2900 | 15.6250 | 10 |
| family | mutation_seed3_1 | cm_cache_on | 1 | 9.8310 | 0.0000 | 10 |
| family | mutation_seed3_1 | public_cache_off | 1 | 14.6843 | 15.6250 | 10 |
| family | mutation_seed3_1 | public_cache_on | 1 | 15.8363 | 15.6250 | 10 |

## 5. All-arm ladder phase overview

Each row time-weights all available cases for that arm/treatment by their own measured phase-pass caller times. Absolute values are mean µs per operation across cases and passes. Listed phases are the largest four; the full exclusive partition is in `ladder_summary.json.time_weighted_phases_by_arm`. A grouped phase intentionally retains inseparable mechanisms.

| Arm | Treatment; cases | Mean own caller µs | Largest four phases: own %; mean µs | Unresolved/probe % |
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

## 6. Representative complete exclusive phase partitions

These full partitions show contrasting mechanisms. They are descriptive observed phase passes, with CPU granularity and probe overhead retained. Nothing here is normalized against an uninstrumented denominator. Every unshown cell has the same detailed fields in the summary JSON; the complete per-cell ledger is not limited to these examples.

### random-shared-seed0-k8 / cm_common_flat / cold_q1 per operation

Separate phase-pass caller: **1284.133 µs wall**, **0.000 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| rewrites_and_key_construction | 276.700 | 0.000 | 21.55 |
| source_traversal_build_memo | 216.533 | 0.000 | 16.86 |
| keys_and_interning | 207.833 | 0.000 | 16.18 |
| support_propagation | 130.967 | 0.000 | 10.20 |
| input_dag_decode_and_validation | 74.933 | 0.000 | 5.84 |
| intern_uid_lookup | 66.733 | 0.000 | 5.20 |
| source_traversal_structural_uid | 63.100 | 0.000 | 4.91 |
| unresolved_harness_and_probe_remainder | 57.300 | 0.000 | 4.46 |
| lowering_cm_flat | 42.633 | 0.000 | 3.32 |
| canonical_sort_and_keys | 28.800 | 0.000 | 2.24 |
| positional_masks_cache_and_construction | 28.300 | 0.000 | 2.20 |
| input_json_parse | 19.667 | 0.000 | 1.53 |
| build_lifecycle | 14.000 | 0.000 | 1.09 |
| compile_cache_lookup_and_lifecycle | 12.300 | 0.000 | 0.96 |
| kernel_and_intermediate_allocation_release | 10.333 | 0.000 | 0.80 |
| liveness_release_plan | 9.233 | 0.000 | 0.72 |
| restriction_key_validation_cache_and_binding | 8.900 | 0.000 | 0.69 |
| compile_lifecycle | 6.967 | 0.000 | 0.54 |
| flat_cache_lookup | 6.100 | 0.000 | 0.48 |
| packed_integer_to_bytes_delivery | 1.467 | 0.000 | 0.11 |
| common_complete_output_correctness_guard | 1.333 | 0.000 | 0.10 |

### random-shared-seed0-k8 / public_cm / resident_q64 per operation

Separate phase-pass caller: **87.127 µs wall**, **81.380 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| public_wrapper_lifecycle | 29.978 | 0.000 | 34.41 |
| public_budget_guards | 22.568 | 81.380 | 25.90 |
| kernel_and_intermediate_allocation_release | 14.265 | 0.000 | 16.37 |
| unresolved_harness_and_probe_remainder | 12.780 | 0.000 | 14.67 |
| restriction_key_validation_cache_and_binding | 2.245 | 0.000 | 2.58 |
| public_budget_guard_source_traversal | 1.399 | 0.000 | 1.61 |
| packed_integer_to_bytes_delivery | 1.370 | 0.000 | 1.57 |
| common_complete_output_correctness_guard | 1.267 | 0.000 | 1.45 |
| flat_cache_lookup | 1.255 | 0.000 | 1.44 |

### fixed-structure-output-k18 / cm_common_flat / resident_q64 per operation

Separate phase-pass caller: **81.251 µs wall**, **81.380 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| kernel_and_intermediate_allocation_release | 39.767 | 0.000 | 48.94 |
| packed_integer_to_bytes_delivery | 27.951 | 0.000 | 34.40 |
| unresolved_harness_and_probe_remainder | 11.033 | 81.380 | 13.58 |
| common_complete_output_correctness_guard | 2.500 | 0.000 | 3.08 |

### assignment_batch / balanced-k8 / cm_batch / 1 whole task

Separate phase-pass caller: **6320.300 µs wall**, **5208.333 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| supplied_assignment_loading | 4086.267 | 5208.333 | 64.65 |
| packed_conversion | 754.400 | 0.000 | 11.94 |
| input_document_loading_json_decode | 523.033 | 0.000 | 8.28 |
| assignment_binding_kernel_array_to_list | 472.267 | 0.000 | 7.47 |
| cm_representation_compile | 292.400 | 0.000 | 4.63 |
| input_parse | 78.500 | 0.000 | 1.24 |
| unresolved_python_bookkeeping | 78.500 | 0.000 | 1.24 |
| delivery_digest | 21.433 | 0.000 | 0.34 |
| correctness_guard | 8.133 | 0.000 | 0.13 |
| variable_basis_mapping | 5.367 | 0.000 | 0.08 |

### restriction / balanced-k8 / cm_packed / 64 whole task

Separate phase-pass caller: **1783.667 µs wall**, **0.000 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| input_document_loading_json_decode | 386.400 | 0.000 | 21.66 |
| execution_kernel | 291.733 | 0.000 | 16.36 |
| unresolved_python_bookkeeping | 260.000 | 0.000 | 14.58 |
| cm_representation_compile | 243.367 | 0.000 | 13.64 |
| mask_context_binding | 218.700 | 0.000 | 12.26 |
| variable_basis_mapping | 149.967 | 0.000 | 8.41 |
| packed_conversion | 97.433 | 0.000 | 5.46 |
| input_parse | 63.167 | 0.000 | 3.54 |
| lowering | 39.967 | 0.000 | 2.24 |
| restriction_context_construction | 13.133 | 0.000 | 0.74 |
| delivery_digest | 13.100 | 0.000 | 0.73 |
| output_delivery | 3.567 | 0.000 | 0.20 |
| correctness_guard | 3.133 | 0.000 | 0.18 |

### simplified_expression / balanced-k8 / cm_shared_minimizer / 1 whole task

Separate phase-pass caller: **65536.600 µs wall**, **62500.000 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| correctness_guard | 45127.333 | 46875.000 | 68.86 |
| shared_sympy_minimizer | 18625.167 | 15625.000 | 28.42 |
| input_document_loading_json_decode | 453.667 | 0.000 | 0.69 |
| expression_quality_guard | 425.100 | 0.000 | 0.65 |
| expression_serialization | 268.433 | 0.000 | 0.41 |
| cm_representation_compile | 229.000 | 0.000 | 0.35 |
| unresolved_python_bookkeeping | 104.433 | 0.000 | 0.16 |
| minterm_materialization | 104.200 | 0.000 | 0.16 |
| input_parse | 82.533 | 0.000 | 0.13 |
| lowering | 40.333 | 0.000 | 0.06 |
| mask_context_binding | 36.467 | 0.000 | 0.06 |
| variable_basis_mapping | 24.167 | 0.000 | 0.04 |
| execution_kernel | 8.700 | 0.000 | 0.01 |
| delivery_digest | 7.067 | 0.000 | 0.01 |

### family / shared_seed2 / cm_cache_on / 1 whole task

Separate phase-pass caller: **4213.900 µs wall**, **5208.333 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| cm_compile_including_reuse_management | 2382.867 | 0.000 | 56.55 |
| fixture_ingress_family_generation | 677.700 | 0.000 | 16.08 |
| public_reference_construction | 558.100 | 5208.333 | 13.24 |
| lowering | 297.467 | 0.000 | 7.06 |
| unresolved_python_bookkeeping | 101.533 | 0.000 | 2.41 |
| mask_context_binding | 65.567 | 0.000 | 1.56 |
| correctness_guard | 57.967 | 0.000 | 1.38 |
| execution_kernel | 55.767 | 0.000 | 1.32 |
| packed_conversion | 13.067 | 0.000 | 0.31 |
| persistent_cache_clear | 2.067 | 0.000 | 0.05 |
| output_delivery | 1.800 | 0.000 | 0.04 |

### family / identical_seed2 / public_cache_on / 1 whole task

Separate phase-pass caller: **4808.467 µs wall**, **5208.333 µs process CPU** (mean per stated operation). Percentages use this phase pass only.

| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |
|---|---:|---:|---:|
| public_family_structural_diagnostics | 1871.800 | 5208.333 | 38.93 |
| public_family_inclusive | 1665.167 | 0.000 | 34.63 |
| fixture_ingress_family_generation | 688.767 | 0.000 | 14.32 |
| public_reference_construction | 500.267 | 0.000 | 10.40 |
| unresolved_python_bookkeeping | 78.767 | 0.000 | 1.64 |
| correctness_guard | 3.700 | 0.000 | 0.08 |

## 7. Perturbation, omitted splits and predecessor quantitative context

Ladder instrumentation dilation: median **2.29×**, range **0.84×–10.05×** over274 cell/treatment ratios. Task phase dilation: median **1.02×**, range **0.81×–2.12×**. These separate-pass ratios are not correction factors; values below1 are retained. Task and ladder pass definitions differ and are not pooled.

`cache lookup/validation/binding` and `kernel/allocation/release` are grouped where the code does not expose independent spans. Persistent-cache validation has no equality-fallback phase; reported count placeholders from diagnostics-free family runs are null in the task summary. CPU allocation to tiny phases and native allocation traffic remain unresolved. Symbolic, SAT/count and BDD preparations belong to those algorithms and cannot be relabelled CM wrapper cost.

Frozen predecessor observations remain quantitatively separate from local timings:

| Frozen source | Read measured rows | Exact quantitative location |
|---|---:|---|
| SymPy development Y02–Y05 | 186 | `frozen_evidence.json.sympy_gate`: nine gate ratios, per-arm/case caller/task spans and residuals |
| Performance development | 1296 | `performance_development`: cold/warm session times, separate strengthened CSE, staged spans and process lifecycle |
| Continuation development | 612 | `continuation_development`: setup/query-delivery/cleanup exact partitions and separate warm/memory data |
| Architecture retry and corrected Clang query ladder | separate historical schedules | `architecture.retry002_gcc` and `architecture.query_ladder_clang`: absolute stage distributions, own-total shares and query counts |

See [FROZEN_EVIDENCE.md](FROZEN_EVIDENCE.md) for the complete reaggregation, source-custody verification and timer-overlap prohibitions. Historical caller residuals are not automatically startup costs; query-prefix correctness hashes are not q1 latency measurements; old cumulative profile rows cannot yield exclusive shares. No existing evidence or claim disposition was rewritten.

## 8. Reproduction

`python -B make_time_ledger.py --output <new-file-in-this-audit.md>` reads only the three saved summaries, performs arithmetic and refuses overwrite. Input SHA-256 values:

* `ladder_summary.json`: `76501aaa191bfd993c19af06dc47034042ba6d2bf3846a7943f236b61ad8fe2a`
* `TASK_SUMMARY.json`: `7040a61e156407cadadf466ab45d1f35f8d6de2647d421ec5d39210e42a00dee`
* `frozen_evidence.json`: `b95ec2d9f95b735275452079c4821a7d87bf5d3d8595528d43faf3730a1bd5e3`

No further timing is needed to reproduce this ledger. Unresolved splits remain explicitly unresolved; no scientific disposition changed.
