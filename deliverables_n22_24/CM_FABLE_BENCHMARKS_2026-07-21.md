# Fable Benchmarks — Endorsed Code State (post-audit), 2026-07-21/22

Project contact: **Brian Theory (Droncheff)** — direct questions about this work to him.
Benchmarks and analysis prepared with Claude Fable 5 (Anthropic).

Companion to `CM_FABLE_AUDIT_V2_2026-07-21.md` (repo root). All headline timings:
instrumentation off, medians over ≥5 interleaved rounds, oracle checks outside timed
windows, benchmark interpreter `.venv` Python 3.13.5 unless stated. Correctness re-runs
also executed on system Python 3.10.11.

## 1. Exhaustive correctness (re-run of the audit harness, both interpreters)

- Python 3.13.5: 30 expressions × n=16–24, **134,086,656 rows/method, 0 failures**
  (CM reduced/full, raw bitset, recursive CM-IR, C1a flat, adversarial, `dd.autoref`,
  bound-cache purity). `CM_audit_2026-07-21_py313_fable_*.csv`.
- Python 3.10.11: 12 expressions × n=16/20, 6,684,672 rows/method, 0 failures.
  `CM_audit_2026-07-21_py310_fable_*.csv`.
- Liveness-freeing branch **force-enabled** (gate constants zeroed) adversarial fuzz:
  2,909 checks × both interpreters, 0 failures — shared-fanout/diamond DAGs, repeated-arg
  ops, 400 mixed-`fixed` rebinding trials, cached-template integrity, static
  no-read-after-release schedule audit. `fable_adversarial_liveness_2026_07_21.py`.
- numpy-words backend (new, §5): 1,827 checks × both interpreters, 0 failures, including
  packed-output equality at n=16–24 (exhaustive by construction), scratch-buffer reuse,
  width switching, fixed rebinding, and the <6-var fallback. Suite: `python -m pytest -q`
  = **159 passed** with the extended words assertions folded into the existing tests.

## 2. Env-build cliff (re-run, fresh first-touch)

| n | old builder | vectorized | ratio | bit-identical |
|--:|--:|--:|--:|:--:|
| 3.13.5, n=16 | 117 ms | 5.8 ms | 20× | yes |
| 3.13.5, n=18 | 1.18 s | 35 ms | 33× | yes |
| 3.13.5, n=20 | 16.3 s | 123 ms | 132× | yes |
| 3.10.11, n=20 | 21.9 s | 127 ms | 173× | yes |

(`CM_env_build_2026-07-21_{py313,py310}_fable.csv`.) Confirms C2 and the R3 enabler story;
absolute old-builder numbers swing ±30% between sessions but the cliff is unambiguous.

## 3. Corrected-baseline headline (C3 blast radius) — supersedes `CM_n16_24_headline.csv` ratios at n≥18

Paired, interleaved, depth-4 random expressions, 8 trials/n, `hybrid_threshold=7`,
guard 16, flat eval on. "Old" = the fe73f82 comparator (recursive CM-DAG walk at n≥18);
"new" = flattened raw AST at matched scope (`CM_FABLE_c3_blast_radius_{raw,summary}.csv`):

| n | CM wrapper µs | old bitset µs | corrected bitset µs | new/old | CM/corrected (median) | per-trial range |
|--:|--:|--:|--:|--:|--:|:--|
| 16 | 48.0 | 51.5 | 42.2 | 0.82 | 1.14 | 0.79–1.41 |
| 18 | 10.4 | 17.6 | 8.5 | 0.48 | 1.23 | 0.94–1.47 |
| 20 | 12.4 | 20.4 | 9.9 | 0.49 | 1.26 | 0.86–31.7* |
| 22 | 13.0 | 23.1 | 10.5 | 0.45 | 1.24 | 0.88–45.7* |
| 24 | 6.5 | 10.3 | 7.7 | 0.75 | 0.84 | 0.62–1.10 |

\* the outlier trials are `live_k > 7` cases that fall to the numpy TT-vector path
(repr 4); the reduced-bitset trials (repr 3) cluster near the median. Any published
median must disclose the repr mix.

Correctness in this run: all trials bit-exact; the old and corrected comparators agreed
bit-for-bit on every trial (the C3 bug was a fairness bug, never a correctness bug).

## 4. Liveness freeing (C6) — third-party benchmark re-run, unmodified script, fresh session

`CM_flat_liveness_py313_fable_{raw,summary}.csv`, full-output full-arity, 25
samples/method/n:

| n | raw retained→last-use | CM retained→last-use | CM speedup | CM-flat / raw-flat |
|--:|:--|:--|--:|--:|
| 18 | 6.72→5.26 ms (1.28×) | 5.06→4.56 ms (1.11×) | 1.11× | 0.87 |
| 20 | 24.6→22.6 ms (1.09×) | 24.6→20.1 ms (1.23×) | 1.23× | 0.89 |
| 22 | 149.3→86.4 ms (1.73×) | 177.4→84.6 ms (**2.10×**) | 2.10× | 0.98 |
| 24 | 818→835 ms (0.98×) | 767→773 ms (0.99×) | 0.99× | 0.92 |

Reproduces the third party's table in direction and magnitude (its n=22 CM 2.02× → my
2.10×; its honest n=24 neutral → my 0.99×). Peak-allocation re-run matches its memory
table to the decimal (raw 27.3×/25.3×/25.4×, CM 13.4×/12.4×/15.2× reductions at
n=18/20/22; `CM_flat_liveness_memory_fable_{raw,summary}.csv`).

## 5. NEW: numpy-uint64 word backend (Tier-C C1b-lite) — the remaining large-n lever, landed

`eval_cm_node_words` / `eval_expr_words_bitset` in `bitset_backend.py` execute the same
`FlatProgram` over 64-bit word vectors with `out=`-style in-place numpy ops. Scratch
buffers are **colored by the existing last-use schedule**: 13–21 buffers instead of one
per slot (~40 MB instead of ~500 MB at n=24), zero allocations in steady state. Inputs
come from a small words-env cache (≤4 entries) plus shared const arrays. Below 6 live
vars (width < one word) the functions fall back to the bigint flat kernel, so they are
bit-compatible drop-ins at every size. Both sides get the identical mechanism — CM *and*
the raw-AST fairness control.

Medians, balanced all-vars depth-8 expressions, 3 trials × 5 rounds, paired:

| n | bigint CM µs | words CM µs | CM speedup | bigint raw µs | words raw µs | raw speedup |
|--:|--:|--:|--:|--:|--:|--:|
| 12 | 246 | 541 | 0.45× | 283 | 604 | 0.47× |
| 14 | 572 | 770 | 0.74× | 740 | 888 | 0.83× |
| 16 | 2,008 | 1,098 | 1.83× | 3,304 | 1,410 | 2.34× |
| 18 | 6,828 | 2,601 | 2.63× | 7,564 | 2,880 | 2.63× |
| 20 | 37,300 | 9,170 | 4.07× | 38,925 | 10,164 | 3.83× |
| 22 | 139,403 | 27,842 | 5.01× | 148,560 | 30,116 | 4.93× |
| 24 | 945,181 | 135,407 | **6.98×** | 1,029,785 | 141,445 | **7.28×** |

Python 3.10.11 reproduces the profile (7.26×/7.32× at n=24). Honest boundaries:

- **Words loses below ~2^14–2^16 bits** (0.45–0.83× at n=12/14): numpy call overhead
  exceeds the op cost on narrow masks. The bigint kernel stays the right default; words
  is opt-in, exactly as the handoff's C1b-lite entry predicted.
- The CM-vs-raw fairness ratio is *unchanged* by words (both sides speed up nearly
  equally) — this does not move the CM-vs-bitset headline, it moves the shared full-output
  cost floor at n≥16 by ~2–7×.
- The n=24 allocator-dominance diagnosis from the liveness work is confirmed causally:
  removing per-op bigint allocation (not just retaining fewer intermediates) is what
  unlocks n=24.
- Not yet wired into the `cm_bench` CLI (no schema churn in this pass); follow-up:
  a `--cm-words-eval` flag mirroring `--cm-flat-eval`.

Verification artifacts: `fable_words_verify_2026_07_21.py` (this directory).

## 6. Decline behavior (C5), end-to-end

- Guard sweep re-run (script unmodified, same seeds ⇒ deterministic match): depth 4 never
  declines at any n≤32; n=24 decline rates 0% / 0.7% / 23.3% / 92.0% at depths 4/5/6/8;
  wrong-guard and oversized-output counts 0 everywhere across 6,000 expressions
  (`CM_audit_2026-07-21_decline_distribution_fable.csv`).
- End-to-end CLI check of the new summary column: see §7.

## 7. End-to-end CLI runs on the endorsed state

- Headline-style run (`--sizes 16,18,20,22,24 --trials 8 --max-depth 4 --seed 424242
  --cm-compare-no-reinflate --large-n-safe --cm-flat-eval --cm-hybrid-threshold 7
  --cm-max-full-output-vars 16 --cm-eval-repeat 50`, non-bitset backends off):
  40/40 rows bit-correct (`cm_hybrid_no_reinflate_ok` and `bitset_ok` all true);
  `bitset_baseline_kind` = `raw_ast_flat` at n=16 and `raw_ast_flat_matched_scope` at
  n≥18 in every row; `declined_count` 0 at depth 4, as required by the §6 distribution.
  `fable_headline_endorsed_{raw,summary}.csv`.
- Decline demo (`--sizes 24 --trials 30 --max-depth 6 --seed 987654`, same config):
  **5 of 30 declined** (consistent with the 23% depth-6 rate), 25 survivors all correct,
  and the summary carries `cm_hybrid_no_reinflate_declined_count=5` next to the
  survivor-only median — the selection bias can no longer hide.
  `fable_decline_d6_{raw,summary}.csv`.

## 7b. Robust wrapper campaign (2026-07-22 follow-up): 300 formulas/n + threshold fix

The §3/§7 wrapper ratios came from 8 depth-4 formulas per n. A follow-up campaign ran
**300 formulas per n** (1,500 total, 5 interleaved rounds each, every trial verified
bit-correct; `CM_FABLE_wrapper_stats300_{raw,summary}.csv` and `..._t16_...`):

| n | wrapper CM/Bitset median (thr=7) | median (thr=16) | p10–p90 (thr=16) | live_k median/p90/max |
|--:|--:|--:|:--|:--|
| 16 | 1.08 | 1.04 | 0.61–1.34 | 5 / 8 / 11 |
| 18 | 1.28 | 1.25 | 0.95–1.56 | 5 / 8 / 10 |
| 20 | 1.25 | 1.18 | 0.89–1.51 | 6 / 9 / 11 |
| 22 | 1.17 | 1.12 | 0.79–1.43 | 6 / 9 / 12 |
| 24 | 1.06 | **1.02** | 0.78–1.36 | 6 / 9 / 12 |

Findings:

- **The §3 n=24 value (0.84) was sampling luck** — all 8 draws had live_k ≤ 6
  (a few-percent event). Robust n=24 median: 1.02. The §3 table remains as the paired
  old-vs-new comparator record; this table supersedes its CM/corrected column as the
  wrapper headline.
- **live_k is n-independent** (median 5–6, p90 8–9 at every n), as the depth-4 leaf-count
  argument predicts.
- **Stratified (thr=16):** live_k ≤ 4 → CM ahead/tied end-to-end (0.87–1.06);
  5–7 → Bitset modestly ahead (1.05–1.28); ≥ 8 → 1.12–1.38.
- **Threshold mis-tuning found and fixed in configuration:** under `hybrid_threshold=7`,
  live_k ≥ 8 formulas (~20% of draws) fell to the numpy TT-vector path at **~40× behind**
  the fair Bitset. `--cm-hybrid-threshold 16` keeps them on the bitset kernel: that
  stratum drops to 1.12–1.38× with bit-identical outputs and no regression in the other
  strata. **Recommendation: adopt threshold 16 as the benchmark default** (config change
  only; no library-default change made).

## 8. Variance statement

Full-arity large-n session CVs in this session's runs were 7–16% (consistent with the
third party's 6–10%, better-behaved than the inherited ±30–50% warning), but tiny
microsecond-scale reduced outputs remain noisy (per-trial CM/raw spread 0.6–1.7 plus
repr-4 outliers). Report ranges and medians with the repr mix; never single constants.
