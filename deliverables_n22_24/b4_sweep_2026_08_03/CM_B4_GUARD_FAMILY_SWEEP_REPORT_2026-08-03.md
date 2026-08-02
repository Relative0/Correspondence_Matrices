# B4 — Guard/decline and n=16–24 family sweep (2026-08-03)

Git `eab8879`; `.venv` Python 3.13.5, numpy 2.3.2. Driver
`cm_b4_guard_family_sweep_2026_08_03.py`; fresh seeds (guard base 20260803;
headline corpus blake2b-seeded, corrected-E3 admission, corpus SHA in results
`_meta`). Wall 11.6 s. Supersedes the deck's pre-repair n≥18 numbers (already
marked superseded by the consolidated audit).

## Part 1 — guard/decline (200 trials/cell, n ∈ {16,18,20,22,24}, depth ∈ {4,6,8})

- **Guard correctness: 0 wrong guards and 0 oversized outputs in 3,000
  trials** (C3 fairness fix and reduced-output guard hold post-repair).
- Decline rates rise with n and depth exactly as the deck narrative says:
  depth 4 → 0% everywhere; depth 6 → 2–24% (n=18→24); depth 8 → 75–93%.
- Median live_k confirms nominal n is not workload size: depth 4 medians are
  5–6 regardless of n; only depth 8 pushes medians to 16–22.

## Part 2 — live_k-controlled headline refresh (V4 C1 protocol, symmetric words engines)

24 exact-support formulas (k ∈ {8,12,16} × 4 families × 2 shapes) embedded at
ambient n ∈ {16,20,24} by fixing dead variables; CM wrapper vs
`eval_expr_words_bitset`, packed-equal, 7 paired interleaved rounds.

| live_k | n=16 geomean | n=20 geomean | n=24 geomean |
|---:|---:|---:|---:|
| 8  | 1.76 | 1.77 | 1.80 |
| 12 | 1.71 | 1.69 | 1.72 |
| 16 | 1.29 | 1.33 | 1.33 |

- **Ambient n has essentially no effect** (ratios flat across n at fixed k) —
  the deck's "live_k, not nominal n, drives the workload" claim is CONFIRMED.
- **The V4 C1 sign at k=12/16 is not reproduced** on corrected-admission
  corpora: CM wrapper trails the symmetric BitSet control at every (k, n)
  cell (geomean 1.29–1.80; p10 reaches ~1.0 only at k=12/16). This replaces
  the superseded pre-repair n≥18 ratios and agrees with B2.

## Verdict

**B4 COMPLETE — guard behavior CONFIRMED (0 violations); nominal-n
irrelevance CONFIRMED; deck-era "modestly ahead at controlled 12/16"
REVISED to "BitSet leads at the wrapper boundary at all measured live_k on
corrected-admission corpora".**
