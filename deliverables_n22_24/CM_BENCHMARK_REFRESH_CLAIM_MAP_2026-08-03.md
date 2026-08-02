# CM Benchmark Refresh — Claim Map (2026-08-03)

Every deck-relevant claim (deck frozen at Audit V4, 2026-07-24) mapped to its
refreshed number from this campaign (B1–B7, git `eab8879`, all evidence
paths listed in the refresh handoff). Statuses: CONFIRMED / REVISED
(old → new) / SUPERSEDED (never cite) / NOT RE-RUN.

| # | deck claim (V4-era) | status | refreshed evidence |
|---|---|---|---|
| 1 | Corrected-E3 headline: repaired CM kernel 0.888 [0.876, 0.899] vs plain CSE; ≈parity (0.985) vs CSE-flat | **CONFIRMED** | B1 fresh replay: 0.8876 [0.873, 0.902], identity fields exact 192/192; cm/cse_flat 1.004 (residual sign not stable — cite "≈parity", never a CM win) |
| 2 | Archived E3 0.843 [0.780, 0.894]; 96-formula corpus | **SUPERSEDED** (stands) | never cite except as superseded |
| 3 | 128×/240× multiplier compression | **SUPERSEDED — retraction stands** | no new evidence changes this |
| 4 | V4 C1 "BitSet dominates tiny support; 8–12 transitional; CM modestly ahead at controlled live_k 12/16" | **REVISED** | B2 + B4: BitSet-lead at tiny k confirmed (7.8× at k=4), but CM wrapper now trails at every live_k ≤ 16 on corrected-admission corpora (cached geomean 1.31 at k=16, 1.7–1.8 at k=8–12; B4 same protocol as C1: 1.29–1.80). "Modestly ahead at 12/16" is not supported post-repair; crossover, if any, is above the k=16 guard |
| 5 | Wrapper overhead median 23 µs, dominates small-k comparisons | **REVISED** | B2 decomposition: overhead 50–91 µs median on this corpus/protocol, co-equal with kernels through k=16 (the qualitative claim — overhead dominates the boundary — is stronger than before) |
| 6 | Nominal n is not workload size; live_k drives cost | **CONFIRMED** | B4: ratios flat across ambient n ∈ {16,20,24} at fixed live_k; guard-sweep median live_k 5–6 at depth 4 regardless of n |
| 7 | Guard/decline correctness (reduced-output guard, C3 fairness, engine symmetry) | **CONFIRMED** | B4: 0 wrong guards, 0 oversized outputs in 3,000 fresh trials; decline rates depth-8 75–93% at n=18–24 (fresh post-repair numbers replace superseded pre-repair n≥18 sweeps) |
| 8 | Compile/DAG scaling: prep tracks structural nodes; pathological 403 ms → 3.0 ms; unshared-tree µs class | **CONFIRMED** | B3: 8.4M-unfolded ladder compiles in 985 µs; prep linear in structural nodes; prep ratio vs CSE 2.2–7.9× (E3 geomean 4.30× consistent) |
| 9 | Prep/break-even economics: 4.30× prep, break-even median 78.5, 30/192 never | **CONFIRMED + extended** | B1 replay identical corpus; EPFL external: prep 4.11×, break-even vs CSE-flat median 174.5 finite, 55/129 never — workload-dependence stands and is worse on real circuits |
| 10 | Kernel-equivalence CM vs CSE-flat (Outcome A, provisional pending EPFL) | **CONFIRMED — now FINAL** | B7 EPFL: cm/cse_flat 0.9998 [0.975, 1.025] circuit-clustered on 129 real AND/INV cones; materiality rule fails all inferential conditions; Outcome A converts provisional → final |
| 11 | CM vs plain CSE advantage, mechanism = n-ary instruction merging | **CONFIRMED** | B7: cm/cse 0.927 [0.903, 0.951] external; instruction & executed-op ratios vs CSE-flat exactly 1.000 (AND/INV circuits have no mergeable chains beyond flattening — mechanism predicts parity, parity observed) |
| 12 | No cross-platform claim (local-box scope) | **UPGRADED** | B6: 5 cpu3c pods (EPYC), identity exact, blocked geomeans 0.877–0.888 (spread 0.011), all CIs exclude parity — CROSS-PLATFORM REPLICATION PASSED; a cross-machine statement for the 0.888-class finding is now supportable |
| 13 | CUDD: fast compact symbolic builds; packed extraction ~0.364 s at n=16, thousands× slower than words kernels; no three-way winner | **CONFIRMED (same-box, matched)** | B5: CUDD full-extraction 1.1 ms/25.6 ms/580 ms at k=8/12/16 vs 15–45 µs words kernels; robdd_is_cudd on all 192 rows; full-extraction packed equality (stronger than archived 64-sample). V4's blocked primary experiment now exists |
| 14 | CUDD "best-of-10" labeling imprecision (bars are median-of-10) | **NOT RE-RUN** | prose-only V4 finding; B5 used fixed natural order (no order search), so the refreshed comparison avoids the ambiguity entirely |
| 15 | Words/flat/bigint engine crossover (bigint below 6 vars, words ≥6) | **CONFIRMED (in passing)** | B2: words fallback at k=4 measured (bitset 3.8 µs bigint vs 35 µs words at k=6); no dedicated crossover sweep re-run |
| 16 | Schedule claims (blocked vs round-robin within ~2%, never pooled) | **CONFIRMED** | B1/B6/B7 all report both separately; agreement ~1–2% throughout |

## Slide-rebuild guidance

- Slides citing claims 1, 6–11, 13, 16: keep, with refreshed numbers.
- Slides citing claim 4 (wrapper-boundary "CM ahead at 12/16") must be
  rewritten: at the wrapper boundary BitSet leads through k=16; CM's story
  is kernel-level vs plain CSE (0.888 synthetic / 0.927 external) plus
  canonical keys, persistent cache, serde — not wrapper speed.
- Claims 2–3 remain retracted/superseded — never re-appear.
- New slide material now available: external validation (B7), cross-platform
  replication (B6), same-box CUDD matched costs (B5).
