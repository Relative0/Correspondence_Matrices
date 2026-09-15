# Task diagnostic ledger

Measured from `task-run-001/TASK_RESULTS.json`; uninstrumented medians, five repeats. Phases use their own separate pass denominator. See `TASK_METHODS.md` for contract and resolution limits.

| Task / case | Arm / q | Wall median (ms) | CPU median (ms) | Output bytes | Traced peak bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| assignment_batch / absorption-k4 | raw_batch / 1 | 3.9812 | 0.0000 | 512 | 114595 |
| assignment_batch / absorption-k4 | cse_batch / 1 | 3.9598 | 0.0000 | 512 | 114576 |
| assignment_batch / absorption-k4 | cm_batch / 1 | 4.0555 | 0.0000 | 512 | 114472 |
| assignment_batch / absorption-k4 | sympy_cse_off / 1 | 4.7315 | 0.0000 | 512 | 136048 |
| assignment_batch / absorption-k4 | sympy_cse_on / 1 | 5.0282 | 15.6250 | 512 | 141804 |
| assignment_batch / balanced-k8 | raw_batch / 1 | 5.9343 | 0.0000 | 512 | 211765 |
| assignment_batch / balanced-k8 | cse_batch / 1 | 6.0367 | 0.0000 | 512 | 194526 |
| assignment_batch / balanced-k8 | cm_batch / 1 | 5.9401 | 15.6250 | 512 | 190454 |
| assignment_batch / balanced-k8 | sympy_cse_off / 1 | 8.2599 | 15.6250 | 512 | 229470 |
| assignment_batch / balanced-k8 | sympy_cse_on / 1 | 8.4218 | 15.6250 | 512 | 223394 |
| restriction / balanced-k8 | cse_packed / 1 | 0.4385 | 0.0000 | 8 | 51418 |
| restriction / balanced-k8 | cm_packed / 1 | 0.5754 | 0.0000 | 8 | 49282 |
| restriction / balanced-k8 | cse_packed / 64 | 1.1534 | 0.0000 | 512 | 71167 |
| restriction / balanced-k8 | cm_packed / 64 | 1.1359 | 0.0000 | 512 | 70887 |
| exact_count / contradiction-k4 | cse_packed / 1 | 0.3669 | 0.0000 | 11 | 38155 |
| exact_count / contradiction-k4 | cm_packed / 1 | 0.3736 | 0.0000 | 11 | 37883 |
| exact_count / contradiction-k4 | sympy_task / 1 | 0.5335 | 0.0000 | 11 | 41086 |
| exact_count / balanced-k8 | cse_packed / 1 | 0.7574 | 0.0000 | 13 | 51322 |
| exact_count / balanced-k8 | cm_packed / 1 | 0.8898 | 0.0000 | 13 | 49210 |
| exact_count / balanced-k8 | sympy_task / 1 | 22.1069 | 15.6250 | 13 | 166330 |
| sat_status / contradiction-k4 | cse_packed / 1 | 0.3657 | 0.0000 | 15 | 38155 |
| sat_status / contradiction-k4 | cm_packed / 1 | 0.3844 | 0.0000 | 15 | 37883 |
| sat_status / contradiction-k4 | sympy_task / 1 | 0.4973 | 0.0000 | 15 | 38934 |
| sat_status / balanced-k8 | cse_packed / 1 | 0.5883 | 0.0000 | 14 | 51322 |
| sat_status / balanced-k8 | cm_packed / 1 | 0.7619 | 0.0000 | 14 | 49210 |
| sat_status / balanced-k8 | sympy_task / 1 | 1.4853 | 0.0000 | 14 | 99090 |
| equivalence_status / contradiction-k4 | cse_packed / 1 | 0.4395 | 0.0000 | 15 | 38889 |
| equivalence_status / contradiction-k4 | cm_packed / 1 | 0.4636 | 0.0000 | 15 | 37990 |
| equivalence_status / contradiction-k4 | sympy_task / 1 | 0.7717 | 0.0000 | 15 | 41683 |
| equivalence_status / balanced-k8 | cse_packed / 1 | 0.7918 | 0.0000 | 14 | 61378 |
| equivalence_status / balanced-k8 | cm_packed / 1 | 0.9442 | 0.0000 | 14 | 57970 |
| equivalence_status / balanced-k8 | sympy_task / 1 | 1.1484 | 0.0000 | 14 | 55130 |
| simplified_expression / absorption-k4 | cse_shared_minimizer / 1 | 0.5343 | 0.0000 | 12 | 44403 |
| simplified_expression / absorption-k4 | cm_shared_minimizer / 1 | 0.6238 | 0.0000 | 12 | 44107 |
| simplified_expression / absorption-k4 | sympy_default / 1 | 0.6864 | 0.0000 | 12 | 41405 |
| simplified_expression / absorption-k4 | sympy_forced / 1 | 0.6159 | 0.0000 | 12 | 41357 |
| simplified_expression / balanced-k8 | cse_shared_minimizer / 1 | 69.3551 | 62.5000 | 996 | 365656 |
| simplified_expression / balanced-k8 | cm_shared_minimizer / 1 | 66.3687 | 62.5000 | 996 | 364648 |
| simplified_expression / balanced-k8 | sympy_default / 1 | 75.6585 | 78.1250 | 996 | 378271 |
| simplified_expression / balanced-k8 | sympy_forced / 1 | 76.3735 | 78.1250 | 996 | 379056 |
| family / identical_seed2 | cse_family / 1 | 1.7528 | 0.0000 | 16 | 49597 |
| family / identical_seed2 | cm_cache_off / 1 | 2.8438 | 0.0000 | 16 | 46661 |
| family / identical_seed2 | cm_cache_on / 1 | 2.1196 | 0.0000 | 16 | 78186 |
| family / identical_seed2 | public_cache_off / 1 | 5.7521 | 0.0000 | 16 | 84901 |
| family / identical_seed2 | public_cache_on / 1 | 4.7493 | 0.0000 | 16 | 124928 |
| family / shared_seed2 | cse_family / 1 | 2.2398 | 0.0000 | 16 | 64965 |
| family / shared_seed2 | cm_cache_off / 1 | 3.4623 | 0.0000 | 16 | 70749 |
| family / shared_seed2 | cm_cache_on / 1 | 3.8617 | 0.0000 | 16 | 167480 |
| family / shared_seed2 | public_cache_off / 1 | 7.0723 | 15.6250 | 16 | 113983 |
| family / shared_seed2 | public_cache_on / 1 | 7.4136 | 0.0000 | 16 | 222456 |
| family / composition_seed3 | cse_family / 1 | 1.8532 | 0.0000 | 10 | 62340 |
| family / composition_seed3 | cm_cache_off / 1 | 2.8795 | 0.0000 | 10 | 67204 |
| family / composition_seed3 | cm_cache_on / 1 | 3.3797 | 0.0000 | 10 | 94328 |
| family / composition_seed3 | public_cache_off / 1 | 5.3707 | 15.6250 | 10 | 98461 |
| family / composition_seed3 | public_cache_on / 1 | 6.3810 | 0.0000 | 10 | 126065 |
| family / mutation_seed3_0 | cse_family / 1 | 1.5751 | 0.0000 | 10 | 55900 |
| family / mutation_seed3_0 | cm_cache_off / 1 | 2.1982 | 0.0000 | 10 | 57612 |
| family / mutation_seed3_0 | cm_cache_on / 1 | 2.1900 | 0.0000 | 10 | 102688 |
| family / mutation_seed3_0 | public_cache_off / 1 | 3.8142 | 0.0000 | 10 | 82244 |
| family / mutation_seed3_0 | public_cache_on / 1 | 4.1708 | 0.0000 | 10 | 136623 |
| family / mutation_seed3_0.15 | cse_family / 1 | 1.6388 | 0.0000 | 10 | 70012 |
| family / mutation_seed3_0.15 | cm_cache_off / 1 | 2.4275 | 0.0000 | 10 | 74236 |
| family / mutation_seed3_0.15 | cm_cache_on / 1 | 2.6319 | 0.0000 | 10 | 123272 |
| family / mutation_seed3_0.15 | public_cache_off / 1 | 4.2250 | 0.0000 | 10 | 99396 |
| family / mutation_seed3_0.15 | public_cache_on / 1 | 4.5412 | 0.0000 | 10 | 157671 |
| family / mutation_seed3_1 | cse_family / 1 | 7.3941 | 0.0000 | 10 | 290020 |
| family / mutation_seed3_1 | cm_cache_off / 1 | 9.2900 | 15.6250 | 10 | 295964 |
| family / mutation_seed3_1 | cm_cache_on / 1 | 9.8310 | 0.0000 | 10 | 334002 |
| family / mutation_seed3_1 | public_cache_off / 1 | 14.6843 | 15.6250 | 10 | 337353 |
| family / mutation_seed3_1 | public_cache_on / 1 | 15.8363 | 15.6250 | 10 | 375389 |

## Public family measured subspans

These are nested inside the public-family arm. Residual is computed per observation before taking its median, so the displayed independent medians need not add exactly. The surrounding diagnostic caller additionally includes disclosed fixture generation, reference creation and structural family diagnostics.

| Case / persistence | Family total (ms) | Compile (ms) | Evaluate (ms) | Conversion/guard/bookkeeping residual (ms) |
| --- | ---: | ---: | ---: | ---: |
| identical_seed2 / public_cache_off | 2.7534 | 1.9690 | 0.6178 | 0.1666 |
| identical_seed2 / public_cache_on | 1.4044 | 0.8909 | 0.3854 | 0.1291 |
| shared_seed2 / public_cache_off | 3.1190 | 2.2256 | 0.7048 | 0.1886 |
| shared_seed2 / public_cache_on | 3.7447 | 2.3711 | 0.7557 | 0.1699 |
| composition_seed3 / public_cache_off | 2.2805 | 1.5033 | 0.5972 | 0.1387 |
| composition_seed3 / public_cache_on | 2.9618 | 2.2276 | 0.5750 | 0.1527 |
| mutation_seed3_0 / public_cache_off | 1.8412 | 1.1930 | 0.5247 | 0.1489 |
| mutation_seed3_0 / public_cache_on | 1.8298 | 1.1111 | 0.4689 | 0.1106 |
| mutation_seed3_0.15 / public_cache_off | 1.7474 | 1.1242 | 0.5080 | 0.1154 |
| mutation_seed3_0.15 / public_cache_on | 1.9542 | 1.3423 | 0.4767 | 0.1049 |
| mutation_seed3_1 / public_cache_off | 3.8979 | 2.9512 | 0.8031 | 0.1436 |
| mutation_seed3_1 / public_cache_on | 4.8854 | 3.8959 | 0.8404 | 0.1857 |
