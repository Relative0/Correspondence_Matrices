# Time ledger

All measurements are local development diagnostics. Negative differences mean less wall time.
Resident pairs alternate independent baseline/candidate CM modules and caches within one process. Each run uses 21 blocks.
The baseline and candidate have identical inputs, requested outputs and engine settings. Family rows additionally deliver new provenance.

## Resident caller observations

| Case | Baseline A, us | Candidate A, us | Candidate/baseline A | B | Material slowdown in both? |
|---|---:|---:|---:|---:|---|
| packed4/fastTrue | 18.44 | 19.79 | 1.073 | 1.072 | False |
| packed4/fastFalse | 20.99 | 21.25 | 1.013 | 0.990 | False |
| words16/fastTrue | 34.20 | 35.69 | 1.044 | 1.038 | False |
| words16/fastFalse | 38.57 | 39.18 | 1.016 | 1.034 | False |
| fallback8/fastTrue | 134.97 | 121.96 | 0.904 | 0.891 | False |
| fallback8/fastFalse | 112.97 | 115.20 | 1.020 | 0.985 | False |
| reduced20/fastTrue | 15.65 | 16.57 | 1.059 | 1.056 | False |
| reduced20/fastFalse | 17.63 | 17.66 | 1.002 | 1.009 | False |
| compile/shared/persistentFalse | 106.00 | 106.40 | 1.004 | 0.995 | False |
| compile/shared/persistentTrue | 145.40 | 129.60 | 0.891 | 0.906 | False |
| family/shared_block_mix/persistentFalse | 2714.65 | 2781.90 | 1.025 | 1.000 | False |
| family/shared_block_mix/persistentTrue | 2876.53 | 2948.97 | 1.025 | 1.006 | False |
| family/composition_mix/persistentFalse | 1668.12 | 1707.85 | 1.024 | 1.037 | False |
| family/composition_mix/persistentTrue | 2140.25 | 1942.92 | 0.908 | 0.908 | False |
| family/identical/persistentFalse | 1189.10 | 1233.67 | 1.037 | 1.077 | False |
| family/identical/persistentTrue | 759.95 | 787.17 | 1.036 | 1.048 | False |

## Independent fresh-worker absolute times

These describe final source behavior; do not interpret their difference from earlier worker medians as an exclusive phase.
CPU uses the sum of block process-CPU samples divided by total calls. Raw samples, profile counts and memory are in the two worker records.

| Case | Wall A, us | Wall B, us | CPU A, us/call | Wall block min–max A, us/call |
|---|---:|---:|---:|---:|
| packed4/fast | 18.62 | 17.65 | 23.25 | 18.47–19.95 |
| packed4/generic | 18.96 | 18.07 | 23.25 | 18.65–21.04 |
| packed4/counts | 19.94 | 22.17 | 11.63 | 19.58–26.28 |
| packed4/timing | 20.67 | 21.34 | 11.63 | 20.03–22.53 |
| packed4/profile | 26.01 | 24.76 | 23.25 | 25.65–28.12 |
| packed4/direct_bitset | 3.70 | 4.02 | 0.00 | 3.66–8.02 |
| packed4/cse_flat | 1.66 | 1.65 | 0.00 | 1.65–2.12 |
| packed4/bare_cm | 1.37 | 1.36 | 0.00 | 1.35–1.58 |
| words16/fast | 30.66 | 37.27 | 23.25 | 30.19–34.97 |
| words16/generic | 31.13 | 43.84 | 23.25 | 29.81–34.69 |
| words16/counts | 33.43 | 43.61 | 23.25 | 32.20–37.13 |
| words16/timing | 34.78 | 67.51 | 34.88 | 34.36–36.83 |
| words16/profile | 39.63 | 67.76 | 34.88 | 37.87–63.13 |
| words16/direct_bitset | 23.93 | 25.61 | 23.25 | 22.49–32.31 |
| words16/cse_flat | 9.83 | 12.69 | 11.63 | 9.67–10.83 |
| words16/bare_cm | 9.46 | 10.16 | 11.63 | 9.38–25.07 |
| fallback8/fast | 115.25 | 118.05 | 116.26 | 111.73–143.65 |
| fallback8/generic | 113.09 | 119.56 | 127.88 | 109.43–153.95 |
| fallback8/counts | 127.27 | 147.18 | 127.88 | 122.70–135.20 |
| fallback8/timing | 130.72 | 131.87 | 139.51 | 127.05–170.21 |
| fallback8/profile | 131.82 | 138.34 | 139.51 | 129.85–146.00 |
| fallback8/direct_bitset | 9.85 | 9.98 | 0.00 | 9.23–11.78 |
| fallback8/cse_flat | 3.39 | 3.40 | 11.63 | 3.35–3.69 |
| fallback8/bare_cm | 2.54 | 2.54 | 11.63 | 2.52–2.78 |
| reduced20/fast | 17.35 | 18.66 | 23.25 | 16.95–22.26 |
| reduced20/generic | 17.98 | 17.97 | 23.25 | 17.21–18.48 |
| reduced20/counts | 21.33 | 20.51 | 23.25 | 20.80–22.36 |
| reduced20/timing | 22.29 | 25.23 | 23.25 | 20.62–25.86 |
| reduced20/profile | 26.39 | 37.64 | 23.25 | 25.46–27.55 |
| compile/shared/persistentFalse | 108.10 | 122.80 | 0.00 | 106.90–125.10 |
| compile/shared/persistentTrue | 130.80 | 134.10 | 0.00 | 129.20–146.00 |
| compile/shared/root_hit | 33.04 | 37.77 | 34.88 | 31.17–38.60 |
| compile/simple/persistentFalse | 56.90 | 65.60 | 0.00 | 55.70–87.20 |
| compile/simple/persistentTrue | 71.80 | 75.90 | 0.00 | 68.30–97.50 |
| compile/simple/root_hit | 21.18 | 22.38 | 23.25 | 20.68–23.41 |
| family/shared_block_mix/persistentFalse | 2692.85 | 2848.95 | 2604.17 | 2641.80–2814.92 |
| family/shared_block_mix/persistentTrue | 2880.60 | 2872.40 | 2790.18 | 2703.62–3100.95 |
| family/composition_mix/persistentFalse | 1684.85 | 1729.15 | 1674.11 | 1595.05–2282.90 |
| family/composition_mix/persistentTrue | 1933.65 | 1976.75 | 2046.13 | 1843.00–2111.27 |
| family/identical/persistentFalse | 1200.10 | 1223.48 | 1302.08 | 1166.55–1455.88 |
| family/identical/persistentTrue | 740.47 | 788.10 | 744.05 | 722.55–968.95 |

## Exclusive phase passes

One instrumented capture per family; these percentages use that capture alone. Compile residual includes building/adoption/support plus unobserved control. Parent exclusive time includes harness work and observer overhead.

### composition_mix

Outer caller: 11.5935 ms wall, 15.6250 ms CPU. Outside nested capture: 0.6830 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 10 | 2.0970 | 0.0000 | 19.22 |
| persistent_root_build | 5 | 1.9965 | 15.6250 | 18.30 |
| family_structure_diagnostics | 1 | 1.9336 | 0.0000 | 17.72 |
| cm_evaluate_api | 10 | 1.3545 | 0.0000 | 12.41 |
| cm_family_backend | 2 | 0.8433 | 0.0000 | 7.73 |
| persistent_digest | 5 | 0.6806 | 0.0000 | 6.24 |
| persistent_sharing_eligibility | 5 | 0.4925 | 0.0000 | 4.51 |
| reference_construction | 1 | 0.4755 | 0.0000 | 4.36 |
| direct_evaluate_api | 5 | 0.2922 | 0.0000 | 2.68 |
| family_observed | 1 | 0.2211 | 0.0000 | 2.03 |
| correctness_oracle | 10 | 0.1761 | 0.0000 | 1.61 |
| output_conversion | 10 | 0.1614 | 0.0000 | 1.48 |
| direct_correctness_oracle | 5 | 0.0709 | 0.0000 | 0.65 |
| direct_output_conversion | 5 | 0.0581 | 0.0000 | 0.53 |
| persistent_cache_lookup_lru | 5 | 0.0271 | 0.0000 | 0.25 |
| persistent_cache_insert_evict | 5 | 0.0245 | 0.0000 | 0.22 |
| cache_lifecycle_reset | 2 | 0.0056 | 0.0000 | 0.05 |

### identical

Outer caller: 7.4012 ms wall, 15.6250 ms CPU. Outside nested capture: 0.9469 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 16 | 1.5728 | 0.0000 | 24.37 |
| cm_evaluate_api | 16 | 1.2070 | 15.6250 | 18.70 |
| cm_family_backend | 2 | 1.1354 | 0.0000 | 17.59 |
| family_structure_diagnostics | 1 | 0.5802 | 0.0000 | 8.99 |
| reference_construction | 1 | 0.4231 | 0.0000 | 6.56 |
| family_observed | 1 | 0.2567 | 0.0000 | 3.98 |
| output_conversion | 16 | 0.2437 | 0.0000 | 3.78 |
| correctness_oracle | 16 | 0.2379 | 0.0000 | 3.69 |
| persistent_sharing_eligibility | 8 | 0.2220 | 0.0000 | 3.44 |
| persistent_digest | 14 | 0.2044 | 0.0000 | 3.17 |
| direct_evaluate_api | 8 | 0.1119 | 0.0000 | 1.73 |
| direct_correctness_oracle | 8 | 0.0907 | 0.0000 | 1.41 |
| direct_output_conversion | 8 | 0.0750 | 0.0000 | 1.16 |
| persistent_cache_lookup_lru | 14 | 0.0653 | 0.0000 | 1.01 |
| persistent_cache_insert_evict | 7 | 0.0220 | 0.0000 | 0.34 |
| cache_lifecycle_reset | 2 | 0.0062 | 0.0000 | 0.10 |

### shared_block_mix

Outer caller: 29.3706 ms wall, 15.6250 ms CPU. Outside nested capture: 2.2051 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 16 | 10.5078 | 15.6250 | 38.68 |
| family_structure_diagnostics | 1 | 4.9051 | 0.0000 | 18.06 |
| cm_evaluate_api | 16 | 3.0257 | 0.0000 | 11.14 |
| cm_family_backend | 2 | 1.6625 | 0.0000 | 6.12 |
| persistent_digest | 110 | 1.3809 | 0.0000 | 5.08 |
| persistent_sharing_eligibility | 8 | 0.9165 | 0.0000 | 3.37 |
| reference_construction | 1 | 0.9145 | 0.0000 | 3.37 |
| direct_evaluate_api | 8 | 0.8036 | 0.0000 | 2.96 |
| persistent_cache_lookup_lru | 110 | 0.6711 | 0.0000 | 2.47 |
| family_observed | 1 | 0.4389 | 0.0000 | 1.62 |
| output_conversion | 16 | 0.4206 | 0.0000 | 1.55 |
| correctness_oracle | 16 | 0.3988 | 0.0000 | 1.47 |
| persistent_cache_insert_evict | 58 | 0.3986 | 0.0000 | 1.47 |
| persistent_root_build | 1 | 0.3283 | 0.0000 | 1.21 |
| direct_correctness_oracle | 8 | 0.2084 | 0.0000 | 0.77 |
| direct_output_conversion | 8 | 0.1709 | 0.0000 | 0.63 |
| cache_lifecycle_reset | 2 | 0.0133 | 0.0000 | 0.05 |
