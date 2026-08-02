# B2 — Wrapper-boundary benchmark (2026-08-03)

Git `eab8879` (HEAD = origin/main); `.venv` Python 3.13.5, numpy 2.3.2, Windows
10.0.19045. Driver `cm_b2_wrapper_boundary_2026_08_03.py`; fresh deterministic
corpus (blake2b seeds, corrected-E3 admission: exact semantic support, measured
family/shape membership), 192 formulas = live_k {4,6,8,10,12,16} × 4 families ×
2 shapes × 4. Corpus SHA-256 in results `_meta`. Deterministic pilot (48
formulas, 7.4 s) passed before the full run. Packed equality across wrapper,
bare BitSet, CSE reference, and bigint reference before every timing; 7 paired
interleaved rounds (order alternating); blocked schedule only.

Arms: CM wrapper total (`materialize_hybrid_no_reinflate`, hybrid_threshold 16,
flat+words) vs bare BitSet (`eval_expr_words_bitset`; bigint fallback below 6
vars). Regimes: cached (prebuilt node/programs) and uncached warmenv (fresh
per-call compile both sides, warm process; k≥6 only — at k=4 the words engine
falls back and per-call compile is not separable; recorded as
`skipped_uncached_k_lt_6`).

## Results (medians of per-formula median paired ratios, CM/BitSet)

| live_k | cached ratio (p10–p90) | uncached warmenv ratio | CM wrapper µs | BitSet µs | wrapper overhead µs |
|---:|---|---|---:|---:|---:|
| 4  | 7.83 (4.24–11.28) | skipped | 36.2 | 3.8 | — |
| 6  | 1.97 (0.96–3.50) | 3.64 | 77.1 | 35.5 | 50.3 |
| 8  | 1.96 (1.20–3.52) | 4.15 | 102.6 | 60.0 | 69.2 |
| 10 | 1.98 (1.13–2.79) | 4.13 | 95.7 | 54.6 | 60.2 |
| 12 | 1.80 (1.14–2.67) | 4.31 | 132.7 | 72.4 | 77.8 |
| 16 | 1.40 (0.96–1.74) | 3.79 | 211.3 | 156.9 | 91.1 |

## Findings

1. **No crossover through live_k=16 on this corpus.** The deck-era claim ("CM
   modestly ahead at controlled live_k=16", V4 C1 ratio 0.925) does not
   reproduce at the wrapper boundary on exact-support corrected-admission
   formulas: the wrapper trails bare BitSet at every stratum (cached median
   1.40 at k=16; p10 0.96 — a minority of formulas reach parity). The trend
   direction (ratio falling with live_k) is preserved; the crossover, if any,
   now sits above k=16, outside the guarded regime.
2. **Wrapper overhead is the mechanism.** Median overhead grows 50→91 µs with
   k while kernels are 27–120 µs, so overhead remains a co-equal cost at k=16
   — consistent with the corrected-E3 conclusion that the wrapper boundary
   reverses the kernel-level sign. The archived "median 23 µs" overhead figure
   is superseded on this corpus/protocol (different corpus and decomposition).
3. **Uncached is uniformly worse for CM** (3.6–4.3×), tracking the known prep
   multiple (CM prep ≈4.3× CSE), unchanged in direction.
4. Note: V4 C1's 0.925 came from a different (deck-era, sparse/redundant)
   corpus in restricted scope with dead-variable fixing; B4's refresh of that
   exact protocol on corrected-admission corpora agrees with B2's direction
   (see B4 report). Scope: one local Windows box, synthetic generator only.

## Verdict

**B2 COMPLETE — deck wrapper-boundary claim REVISED: BitSet leads at every
live_k ≤ 16 on corrected-admission corpora; "CM modestly ahead at 16" is not
supported post-repair.**
