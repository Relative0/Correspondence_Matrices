# Frozen natural secondary timing, 26 September 2026

This is a **descriptive secondary** study on the 71 original EPFL primary-output cones selected and correctness-checked in [04](../04_NATURAL_CIRCUIT_EXTENSION_20260926/README.md). It does not replace the failed synthetic v4 primary utility result or complete the broader protocol-v3 systems campaign. The [protocol](PROTOCOL_V5_NATURAL_SECONDARY.md), [harness](study_v5_natural.py), case/input hashes, configuration, environment, and empty raw result files were frozen in [run 001](run_natural_timing_001/FREEZE.json) before natural timing. One excluded ABC command smoke before the freeze is disclosed in the protocol.

For each cone, resident Python arms produced the same full packed truth bitset. The direct arm evaluated the unchanged AST; the CM arm attempted hybrid pair compilation and used ordinary CM IR construction/evaluation on root fallback. Both checked the complete bitset against the original BLIF oracle on every invocation. The ABC arm ran `read_blif; strash; dc2; write_aiger` in a fresh subprocess and checked each exported AIG exhaustively. ABC process wall includes startup and export, so it is not a speed ratio against the Python producer timers. Python AIGER parse/simulation is not native ABC query time.

| Evidence | Run 001 result |
|---|---:|
| Selected cases and designs | 71 cases, **10** designs |
| Complete Python paired timing | 70 cases, 2,100 rows, 15 repetitions per arm/case |
| Retained timing failure | Adder `f[1]` (case index 4): second calibration block 90.47 ms, below frozen 100 ms floor |
| Python memory | 71 cases, 142 fresh-process arm rows |
| ABC conversion and exhaustive truth | 71 cases, 1,065 repetitions, all correct |
| Median case-level direct/CM producer ratio | **0.0376** across 70 complete cases |
| Cases faster with direct packed | **70/70** complete cases |
| Median direct/CM ratio by hybrid root | Pure structural: 0.240 (4); full retabulation: 0.112 (1); ordinary fallback: 0.0360 (65) |
| Median relative CM peak-working-set increase | −0.15%; common process/import memory dominates |
| Median case-level ABC subprocess wall | 304 ms; unmatched to Python producer timers |

The ratio is the median across cases of each case's median direct per-call time divided by its median CM per-call time. It is not a ratio of pooled times. The missing adder case remains in the 71-case denominator and is not imputed. No hypothesis test or natural-case success threshold was specified. The selected cones cluster within source designs and overlap earlier P1–P14 families. The before/after power scheme and process affinity records matched; this does not establish constancy throughout the run. ABC process memory, an applicable ROBDD/generic comparator, prepared reuse, sharing, dense outputs, and independent natural families remain unmeasured.

The immutable [analyzer output](run_natural_timing_001/ANALYSIS.json) and [raw timing](run_natural_timing_001/TIMING.jsonl), [memory](run_natural_timing_001/MEMORY.jsonl), [ABC](run_natural_timing_001/ABC.jsonl), and [failure](run_natural_timing_001/FAILURES.jsonl) records are retained. The separate [independent verifier](verify_run001.py) checks the frozen case count, row and repetition coverage, AIG truth digests, raw hashes, and ratio arithmetic:

```powershell
python verify_run001.py
python study_v5_natural.py analyze
```

**Frozen-text correction.** The protocol's sentence saying the cones share *nine* designs, the frozen analyzer's `limits` string saying *nine* designs, and the frozen 04 README's “nine designs / 11 designs” sentence are clerical errors. The premeasurement `NATURAL_ADMISSION.json` and 71 `NATURAL_CASES.jsonl` records show **ten selected designs and ten with no eligible primary output**. Those frozen files were not edited to avoid breaking their recorded hashes. The current manuscript and navigation use the corrected counts. This correction changes no case selection, raw timing, root outcome, or ratio.

Run 001 is intentionally left incomplete after the calibration shortfall. Any changed calibration policy or additional result would require a separately numbered, labeled run; these 70 complete-case figures are not a confirmatory substitute for v4.
