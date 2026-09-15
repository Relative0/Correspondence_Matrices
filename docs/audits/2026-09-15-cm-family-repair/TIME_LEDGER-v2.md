# Time ledger

All measurements are local development diagnostics. Negative differences mean less wall time.
Resident pairs alternate independent baseline/candidate CM modules and caches within one process. Each run uses 21 blocks.
The baseline and candidate have identical inputs, requested outputs and engine settings. Family rows additionally deliver new provenance.

## Resident caller observations

| Case | Baseline A, us | Candidate A, us | Candidate/baseline A | B | Material slowdown in both? |
|---|---:|---:|---:|---:|---|
| packed4/fastTrue | 19.30 | 20.68 | 1.072 | 1.043 | False |
| packed4/fastFalse | 20.51 | 20.42 | 0.996 | 1.000 | False |
| words16/fastTrue | 33.10 | 34.46 | 1.041 | 1.039 | False |
| words16/fastFalse | 36.62 | 36.51 | 0.997 | 0.988 | False |
| fallback8/fastTrue | 138.36 | 124.68 | 0.901 | 0.952 | False |
| fallback8/fastFalse | 139.61 | 139.52 | 0.999 | 1.012 | False |
| reduced20/fastTrue | 21.10 | 22.67 | 1.075 | 1.063 | False |
| reduced20/fastFalse | 20.07 | 19.95 | 0.994 | 1.008 | False |
| compile/shared/persistentFalse | 120.30 | 121.70 | 1.012 | 0.985 | False |
| compile/shared/persistentTrue | 162.20 | 145.10 | 0.895 | 0.902 | False |
| family/shared_block_mix/persistentFalse | 3024.32 | 3052.03 | 1.009 | 1.025 | False |
| family/shared_block_mix/persistentTrue | 3487.22 | 3543.30 | 1.016 | 1.027 | False |
| family/composition_mix/persistentFalse | 2036.70 | 2073.00 | 1.018 | 1.014 | False |
| family/composition_mix/persistentTrue | 2269.93 | 2134.47 | 0.940 | 0.870 | False |
| family/identical/persistentFalse | 1502.05 | 1513.55 | 1.008 | 1.059 | False |
| family/identical/persistentTrue | 945.35 | 986.27 | 1.043 | 1.068 | False |

## Independent fresh-worker absolute times

These describe final source behavior; do not interpret their difference from earlier worker medians as an exclusive phase.
CPU uses the sum of block process-CPU samples divided by total calls. Raw samples, profile counts and memory are in the two worker records.

| Case | Wall A, us | Wall B, us | CPU A, us/call | Wall block min–max A, us/call |
|---|---:|---:|---:|---:|
| packed4/fast | 19.46 | 21.72 | 23.25 | 18.19–24.28 |
| packed4/generic | 19.13 | 19.19 | 23.25 | 17.69–20.47 |
| packed4/counts | 22.16 | 24.19 | 23.25 | 19.30–24.93 |
| packed4/timing | 22.15 | 24.45 | 11.63 | 21.02–24.82 |
| packed4/profile | 25.04 | 29.04 | 34.88 | 24.07–33.60 |
| packed4/direct_bitset | 3.88 | 4.14 | 11.63 | 3.69–4.10 |
| packed4/cse_flat | 1.68 | 1.75 | 0.00 | 1.67–1.90 |
| packed4/bare_cm | 1.35 | 1.42 | 0.00 | 1.34–2.80 |
| words16/fast | 32.99 | 32.91 | 34.88 | 31.97–35.07 |
| words16/generic | 30.32 | 33.23 | 23.25 | 29.57–37.09 |
| words16/counts | 36.36 | 36.55 | 46.50 | 33.92–38.30 |
| words16/timing | 34.09 | 37.43 | 34.88 | 32.85–41.77 |
| words16/profile | 39.87 | 40.39 | 34.88 | 38.52–52.84 |
| words16/direct_bitset | 24.59 | 24.83 | 23.25 | 22.62–29.88 |
| words16/cse_flat | 9.65 | 10.32 | 0.00 | 9.61–10.12 |
| words16/bare_cm | 9.39 | 9.69 | 11.63 | 9.33–24.83 |
| fallback8/fast | 116.78 | 118.83 | 116.26 | 111.79–130.59 |
| fallback8/generic | 126.13 | 116.41 | 139.51 | 121.41–155.75 |
| fallback8/counts | 133.46 | 138.40 | 127.88 | 124.74–168.96 |
| fallback8/timing | 133.45 | 138.23 | 139.51 | 126.46–169.91 |
| fallback8/profile | 143.38 | 143.06 | 151.13 | 130.55–234.92 |
| fallback8/direct_bitset | 10.22 | 10.44 | 11.63 | 9.65–11.95 |
| fallback8/cse_flat | 3.59 | 3.51 | 11.63 | 3.43–5.28 |
| fallback8/bare_cm | 2.63 | 2.64 | 0.00 | 2.60–2.85 |
| reduced20/fast | 18.31 | 18.52 | 23.25 | 17.71–24.38 |
| reduced20/generic | 17.91 | 19.57 | 34.88 | 16.64–24.61 |
| reduced20/counts | 21.91 | 20.85 | 23.25 | 20.07–24.57 |
| reduced20/timing | 22.98 | 22.67 | 23.25 | 21.09–24.37 |
| reduced20/profile | 26.31 | 28.76 | 23.25 | 24.61–31.90 |
| compile/shared/persistentFalse | 107.60 | 116.00 | 0.00 | 105.60–126.60 |
| compile/shared/persistentTrue | 131.40 | 138.40 | 0.00 | 128.40–147.50 |
| compile/shared/root_hit | 32.73 | 38.11 | 34.88 | 30.47–39.09 |
| compile/simple/persistentFalse | 55.60 | 58.10 | 0.00 | 54.40–70.70 |
| compile/simple/persistentTrue | 71.10 | 73.50 | 0.00 | 69.80–87.00 |
| compile/simple/root_hit | 21.98 | 22.43 | 23.25 | 20.88–24.04 |
| family/shared_block_mix/persistentFalse | 2903.25 | 2933.32 | 2976.19 | 2695.15–3224.45 |
| family/shared_block_mix/persistentTrue | 2952.20 | 2987.95 | 2976.19 | 2830.93–3115.85 |
| family/composition_mix/persistentFalse | 1698.23 | 1728.25 | 1674.11 | 1634.05–1992.53 |
| family/composition_mix/persistentTrue | 1985.63 | 2027.93 | 2046.13 | 1880.05–2104.82 |
| family/identical/persistentFalse | 1239.83 | 1276.70 | 1302.08 | 1192.50–1483.13 |
| family/identical/persistentTrue | 758.30 | 785.68 | 744.05 | 738.65–871.53 |

## Exclusive phase passes

One instrumented capture per family; these percentages use that capture alone. Compile residual includes building/adoption/support plus unobserved control. Parent exclusive time includes harness work and observer overhead.

### composition_mix

Outer caller: 8.7915 ms wall, 0.0000 ms CPU. Outside nested capture: 0.3829 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 10 | 1.9420 | 0.0000 | 23.10 |
| family_structure_diagnostics | 1 | 1.8570 | 0.0000 | 22.08 |
| persistent_root_build | 5 | 1.0381 | 0.0000 | 12.35 |
| cm_evaluate_api | 10 | 0.9880 | 0.0000 | 11.75 |
| cm_family_backend | 2 | 0.6748 | 0.0000 | 8.03 |
| reference_construction | 1 | 0.4650 | 0.0000 | 5.53 |
| direct_evaluate_api | 5 | 0.2964 | 0.0000 | 3.52 |
| persistent_sharing_eligibility | 5 | 0.2703 | 0.0000 | 3.21 |
| persistent_digest | 5 | 0.2295 | 0.0000 | 2.73 |
| family_observed | 1 | 0.2003 | 0.0000 | 2.38 |
| correctness_oracle | 10 | 0.1429 | 0.0000 | 1.70 |
| output_conversion | 10 | 0.1227 | 0.0000 | 1.46 |
| direct_correctness_oracle | 5 | 0.0876 | 0.0000 | 1.04 |
| direct_output_conversion | 5 | 0.0561 | 0.0000 | 0.67 |
| persistent_cache_insert_evict | 5 | 0.0169 | 0.0000 | 0.20 |
| persistent_cache_lookup_lru | 5 | 0.0147 | 0.0000 | 0.17 |
| cache_lifecycle_reset | 2 | 0.0063 | 0.0000 | 0.07 |

### identical

Outer caller: 5.0189 ms wall, 0.0000 ms CPU. Outside nested capture: 0.4604 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 16 | 1.1477 | 0.0000 | 25.18 |
| cm_evaluate_api | 16 | 0.8589 | 0.0000 | 18.84 |
| cm_family_backend | 2 | 0.7210 | 0.0000 | 15.82 |
| family_structure_diagnostics | 1 | 0.4524 | 0.0000 | 9.92 |
| reference_construction | 1 | 0.3403 | 0.0000 | 7.47 |
| family_observed | 1 | 0.1904 | 0.0000 | 4.18 |
| correctness_oracle | 16 | 0.1592 | 0.0000 | 3.49 |
| output_conversion | 16 | 0.1452 | 0.0000 | 3.19 |
| persistent_sharing_eligibility | 8 | 0.1390 | 0.0000 | 3.05 |
| persistent_digest | 14 | 0.1208 | 0.0000 | 2.65 |
| direct_evaluate_api | 8 | 0.0790 | 0.0000 | 1.73 |
| direct_correctness_oracle | 8 | 0.0714 | 0.0000 | 1.57 |
| direct_output_conversion | 8 | 0.0680 | 0.0000 | 1.49 |
| persistent_cache_lookup_lru | 14 | 0.0420 | 0.0000 | 0.92 |
| persistent_cache_insert_evict | 7 | 0.0183 | 0.0000 | 0.40 |
| cache_lifecycle_reset | 2 | 0.0049 | 0.0000 | 0.11 |

### shared_block_mix

Outer caller: 13.0631 ms wall, 15.6250 ms CPU. Outside nested capture: 0.9390 ms wall.

| Phase (exclusive) | Calls | Wall, ms | CPU, ms | Capture wall % |
|---|---:|---:|---:|---:|
| cm_compile_api | 16 | 4.7160 | 0.0000 | 38.90 |
| family_structure_diagnostics | 1 | 2.1094 | 15.6250 | 17.40 |
| cm_evaluate_api | 16 | 1.3273 | 0.0000 | 10.95 |
| cm_family_backend | 2 | 0.7887 | 0.0000 | 6.51 |
| persistent_digest | 110 | 0.5611 | 0.0000 | 4.63 |
| reference_construction | 1 | 0.5290 | 0.0000 | 4.36 |
| persistent_sharing_eligibility | 8 | 0.4210 | 0.0000 | 3.47 |
| direct_evaluate_api | 8 | 0.3700 | 0.0000 | 3.05 |
| persistent_cache_lookup_lru | 110 | 0.2940 | 0.0000 | 2.42 |
| family_observed | 1 | 0.2010 | 0.0000 | 1.66 |
| correctness_oracle | 16 | 0.1717 | 0.0000 | 1.42 |
| persistent_cache_insert_evict | 58 | 0.1634 | 0.0000 | 1.35 |
| output_conversion | 16 | 0.1585 | 0.0000 | 1.31 |
| persistent_root_build | 1 | 0.1471 | 0.0000 | 1.21 |
| direct_correctness_oracle | 8 | 0.0882 | 0.0000 | 0.73 |
| direct_output_conversion | 8 | 0.0713 | 0.0000 | 0.59 |
| cache_lifecycle_reset | 2 | 0.0064 | 0.0000 | 0.05 |
