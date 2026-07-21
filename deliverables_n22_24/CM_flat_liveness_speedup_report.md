# Flat last-use freeing and fair raw-bitset speedup

Date: 2026-07-21  
Interpreter: benchmark venv Python 3.13.5, NumPy 2.3.2  
Protocol: instrumentation off, 5 expressions x 5 sessions (25 samples/method/size), rotated method
order, oracle checks before timing.

## What changed

`FlatProgram` now computes a per-operation last-use schedule during lowering. The executor clears
dead bigint references immediately after their final consumer. Selection is automatic at
`live_k >= 18` and at least 64 slots; measured n<=16 programs retain the old behavior because
clearing overhead did not repay itself there. `free_dead_slots=False` preserves the original C1a
executor for controlled comparisons.

The same machinery was added to a first-class flattened raw-AST bitset evaluator. It performs no
CM canonicalization or DAG sharing, uses the same cached input masks, supports fixed variables,
and applies the same liveness selector. This is now the fair compile-once bitset control.

Two adjacent fixes landed with it:

- The large-n matched-scope timer now uses raw-AST-flat rather than the CM-IR recursive evaluator;
  ordinary `--cm-flat-eval` runs now select raw-flat on the bitset side too.
- A diagnostics-off CM wrapper route bypasses generic instrumentation setup when C1a is selected;
  `flat_fast_path=False` retains the old wrapper for comparison.

## Full-output time result

All times are medians in microseconds.

| n | raw retained | raw last-use | raw speedup | CM retained | CM last-use | CM speedup | CM/raw last-use |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 6,399 | 5,518 | 1.16x | 5,370 | 4,639 | 1.16x | 0.84x |
| 20 | 25,615 | 21,983 | 1.17x | 25,056 | 19,714 | 1.27x | 0.90x |
| 22 | 137,991 | 94,866 | 1.45x | 170,618 | 84,511 | **2.02x** | 0.89x |
| 24 | 819,263 | 818,509 | 1.00x | 729,955 | 768,545 | 0.95x | 0.94x |

The n=22 outlier was a real retained-intermediate problem and is removed. n=24 is a measured
neutral/negative time result, not hidden: last-use still sharply reduces memory, but allocator and
machine state dominate the timing at that width.

## Peak-allocation result

Traced peak allocations, median of 5 expressions:

| n | raw retained | raw last-use | reduction | CM retained | CM last-use | reduction |
|---:|---:|---:|---:|---:|---:|---:|
| 18 | 9.69 MB | 0.35 MB | 27.3x | 7.52 MB | 0.56 MB | 13.4x |
| 20 | 39.0 MB | 1.54 MB | 25.3x | 31.3 MB | 2.52 MB | 12.4x |
| 22 | 156.3 MB | 6.16 MB | 25.4x | 127.9 MB | 8.39 MB | 15.2x |

This validates the mechanism independently of wall-clock noise: output values are unchanged, but
wide dead intermediates no longer remain referenced until return.

## Wrapper and reduced-output result

The paired diagnostics-off fast path was 1.15x faster at n=8 and 1.29x at n=12, and neutral at
n=4/16 in this run. Fixed result construction remains material at tiny widths.

With the corrected matched-scope raw-flat baseline, five repeated CLI sessions gave:

| ambient n | CM wrapper | raw flat | median CM/raw | session range |
|---:|---:|---:|---:|---:|
| 18 | 5.84 us | 5.04 us | 1.15x | 0.90x-1.38x |
| 20 | 6.54 us | 4.86 us | 1.43x | 1.19x-1.64x |
| 22 | 6.77 us | 5.52 us | 1.23x | 0.90x-1.61x |
| 24 | 6.34 us | 5.80 us | 1.09x | 0.88x-1.70x |

Thus the speedup benefits both implementations, and the fair outcome is not CM dominance:
CM-flat is competitive at the kernel, while its result/scope wrapper remains visible for tiny
reduced outputs.

## Correctness and artifacts

- Final exhaustive sweep: 30 expressions, n=16-24, 134,086,656 rows per method, zero failures.
- Adversarial flat cases and direct `dd.autoref`: zero failures.
- System Python 3.10.11 cross-check: zero failures.
- Full pytest: 159/159.

Data and reproducers:

- `CM_flat_liveness_py313_final_{raw,summary}.csv`
- `CM_flat_liveness_memory_{raw,summary}.csv`
- `CM_flat_liveness_wrapper_paired_{raw,summary}.csv`
- `CM_reduced_fair_sessions_summary.csv`
- `benchmark_flat_liveness_2026_07_21.py`
- `measure_flat_liveness_memory_2026_07_21.py`
