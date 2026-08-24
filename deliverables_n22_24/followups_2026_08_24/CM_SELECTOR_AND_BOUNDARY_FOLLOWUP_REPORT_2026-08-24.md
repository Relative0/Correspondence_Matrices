# CM selector and boundary follow-up — 2026-08-24

## Verdict

The three frozen follow-ups are complete.

1. The symmetric B2/B4 comparison passed exact packed equality on all 264 rows. Once both sides use the current selector, the CM wrapper is near parity with the raw-AST arm at `k=16`, not clearly faster: B2 CM/raw geomean `1.062`; B4 geomeans `1.086`, `1.075`, and `1.090` at ambient `n=16,20,24`. At smaller support the raw-AST arm is substantially faster because CM wrapper cost dominates.
2. The dedicated `k=13..15` study rejects a universal width-only threshold change. The current `k=16` policy passes the balanced synthetic tuning gate on Windows but fails held-out EPFL there; it fails at least one predeclared gate on all three Linux pods. Lower thresholds improve held-out circuits but create large, sometimes catastrophic, misses on balanced synthetic formulas.
3. The isolated `k=17..20` boundary sweep passed all 16 cases. The production wrapper refused every case before explicit allocation; explicitly authorized direct kernels agreed bit-for-bit, had no timeout/OOM, and stayed below the predeclared estimate and RSS caps.

The production recommendation is therefore to keep `WORDS_AUTO_MIN_VARS = 16` as the conservative default for now. Do not replace it with another single support threshold based on this study. The next selector experiment should be feature-based and independently validated (for example, support width plus program liveness/operator-work features).

## Frozen protocols

- Python `3.13.5`; Runpod NumPy `2.3.2`.
- Synthetic gap corpus: 48 formulas, balanced across `k=13,14,15`, four operator families, and tree/shared shapes; two formulas per cell.
- Held-out gap corpus: 23 exact-support roots from the frozen EPFL corpus. The raw-AST timing arm admitted 17 of these under the 16 MiB temporary-memory protocol; the CM arm admitted all 23.
- Synthetic corpus SHA-256: `ba394c3342af638ab70b62c3c232dee3d8f0770d858aca2fcdb6e693a29f4516`.
- EPFL corpus SHA-256: `bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`.
- Selector gate, declared before timing: regret geomean at most `1.10` and zero rows with regret at least `2.0`.
- Boundary limits: one subprocess per case, 45-second timeout, 64 MiB estimated temporary-memory cap, 512 MiB peak-RSS cap, three timed repetitions.
- Every evidence writer refused to overwrite existing outputs.

## Symmetric B2/B4 successor

The legacy B2/B4 reruns compared the current CM selector against a direct words-oriented BitSet arm. That asymmetry made the apparent sign reversal unsuitable as a current-policy conclusion. The successor uses the same support-width policy on CM-node and raw-AST sides and separately records explicit flat and words kernels.

| Corpus | live k | ambient n | formulas | CM wrapper / raw current geomean |
|---|---:|---:|---:|---:|
| B2 | 4 | 4 | 32 | 4.617 |
| B2 | 6 | 6 | 32 | 3.689 |
| B2 | 8 | 8 | 32 | 3.436 |
| B2 | 10 | 10 | 32 | 2.940 |
| B2 | 12 | 12 | 32 | 1.903 |
| B2 | 16 | 16 | 32 | 1.062 |
| B4 | 8 | 16/20/24 | 8 each | 3.436 / 3.450 / 3.455 |
| B4 | 12 | 16/20/24 | 8 each | 2.255 / 2.254 / 2.291 |
| B4 | 16 | 16/20/24 | 8 each | 1.086 / 1.075 / 1.090 |

Packed mismatches: `0 / 264`.

## Dedicated selector gap study

### Current `k=16` policy

| Host | Arm / role | n | Regret geomean | Max regret | rows >=2x | Gate |
|---|---|---:|---:|---:|---:|---|
| Windows | raw / tuning | 48 | 1.041 | 1.733 | 0 | pass |
| Windows | raw / EPFL | 17 | 1.117 | 1.987 | 0 | fail |
| Windows | CM / tuning | 48 | 1.033 | 1.549 | 0 | pass |
| Windows | CM / EPFL | 23 | 1.134 | 2.142 | 1 | fail |
| Linux pod 1 | raw / tuning | 48 | 1.114 | 2.449 | 3 | fail |
| Linux pod 1 | raw / EPFL | 17 | 1.166 | 1.640 | 0 | fail |
| Linux pod 1 | CM / tuning | 48 | 1.125 | 2.328 | 3 | fail |
| Linux pod 1 | CM / EPFL | 23 | 1.208 | 1.700 | 0 | fail |
| Linux pod 2 | raw / tuning | 48 | 1.120 | 2.435 | 3 | fail |
| Linux pod 2 | raw / EPFL | 17 | 1.190 | 1.677 | 0 | fail |
| Linux pod 2 | CM / tuning | 48 | 1.133 | 2.392 | 3 | fail |
| Linux pod 2 | CM / EPFL | 23 | 1.227 | 1.689 | 0 | fail |
| Linux pod 3 | raw / tuning | 48 | 1.092 | 2.257 | 1 | fail |
| Linux pod 3 | raw / EPFL | 17 | 1.139 | 1.614 | 0 | fail |
| Linux pod 3 | CM / tuning | 48 | 1.098 | 2.111 | 2 | fail |
| Linux pod 3 | CM / EPFL | 23 | 1.183 | 1.708 | 0 | fail |

All packed comparisons were exact. All three frozen B1 controls passed, so the Linux selector failures are not attributed to a generally broken or uncontrolled benchmark environment.

### Why no threshold change is justified

- Threshold `k=14` is best on the held-out EPFL slice: Windows regret geomeans are `1.043` raw and `1.038` CM; Linux is essentially `1.000` on both arms.
- The same `k=14` policy is poor on synthetic tuning: Windows geomeans `1.224` raw / `1.195` CM, with catastrophic rows; Linux raw ranges `1.172–1.194` and CM `1.133–1.144`, also with catastrophic rows.
- Threshold `k=15` is a compromise but still has a catastrophic raw tuning row on every host and slightly exceeds the `1.10` CM held-out gate on Linux pod 2.

This is evidence of a workload interaction, not a stable scalar crossover. A feature-based model must be trained only on the tuning partition and accepted only if it clears the frozen held-out and cross-machine gates.

## Above-guard boundary sweep

- Cases: four exact-support families (`and`, `or`, `xor`, `imp`) at each `k=17,18,19,20`.
- Production wrapper refusals: `16 / 16` as required.
- Direct raw-flat/raw-words/CM-flat/CM-words packed mismatches: `0 / 16`.
- Timeouts/OOMs: `0 / 16`.
- Maximum estimated temporary allocation: `5,111,808` bytes, below 64 MiB.
- Maximum observed child peak RSS: `50,708,480` bytes, below 512 MiB.
- Per-case isolated-process wall time: `0.290–0.500` seconds.

This validates the safety guard and establishes a measured direct-kernel boundary; it does not authorize raising the production output guard.

## Runpod accounting and teardown

- Three pods completed; all per-pod snapshot digests verified.
- New pod charges: `$0.000921 + $0.002246 + $0.001274 = $0.004441`.
- Cumulative recorded exposure including prior campaign reserve: `$0.021215`, below the `$1.00` hard cap.
- All campaign termination calls succeeded.
- A separate post-campaign Runpod inventory returned `0` live pods.

## Evidence index

- `symmetric/current_policy_raw.csv`, `current_policy_summary.csv`, `current_policy_audit.json`
- `selector_gap/selector_gap_corpus.jsonl`, `local_raw.csv`, `local_selector.csv`, `local_audit.json`, `local_environment.json`
- `above_guard/local_raw.csv`, `local_audit.json`
- `../../selector_gap_runpod_2026_08_24/selector_gap_runpod_audit_2026_08_24.json` and each pod's content-addressed raw/selector/audit/control outputs
