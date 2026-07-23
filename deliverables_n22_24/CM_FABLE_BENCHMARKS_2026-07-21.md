# Fable Benchmarks — Endorsed Code State (post-audit), 2026-07-21/22

Project contact: **Brian Theory (Droncheff)** — direct questions about this work to him.
Benchmarks and analysis prepared with Claude Fable 5 (Anthropic).

Companion to `CM_FABLE_AUDIT_V2_2026-07-21.md` (repo root). All headline timings:
instrumentation off, medians over ≥5 interleaved rounds, oracle checks outside timed
windows, benchmark interpreter `.venv` Python 3.13.5 unless stated. Correctness re-runs
also executed on system Python 3.10.11.

> **Audit V3 correction (2026-07-23):** This document remains the record of what the
> Fable session measured. `CM_AUDIT_V3_2026-07-23.md` supersedes three interpretations:
> (1) fresh n=24 wrapper medians span 1.02–1.09 rather than one universal 1.02;
> (2) the n=24→32 wrapper drift isolates to fixed-binding bookkeeping in the current
> matched-scope control, not an inherently growing Bitset kernel; and (3) the §7d
> “all-live” generator was semantically flawed—only 4/29 rows were truly all-live and
> the n=32 formula had exact support 16. The corrected all-live V3 series runs through
> n=26. Original CSVs below are preserved unchanged.

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

## 7c. Extended campaign on RunPod (2026-07-22): n=24–32, depths 4–8

Run remotely (pod `x82z2pbpofhcgz`, 2 vCPU, $0.06/hr, ~3 min wall-clock) to keep the
local machine free: 300 formulas per (n, depth) cell, n ∈ {24,26,28,30,32} ×
depths {4,5,6,8} = 6,000 formulas, threshold 16, guard 16, same protocol as §7b.
**All 4,183 accepted results bit-correct; every decline explicitly counted.**
Data: `CM_FABLE_extended_n32_{raw,summary}.csv`; runner:
`fable_extended_campaign_worker_2026_07_22.py` (+ push/poll scripts).

Wrapper CM/Bitset medians (accepted trials):

| n \ depth | 4 | 5 | 6 | 8 (survivors only) |
|--:|--:|--:|--:|--:|
| 24 | 1.01 | 1.04 | 0.99 | 0.92 |
| 26 | 0.98 | 1.00 | 0.96 | 0.90 |
| 28 | 0.92 | 0.97 | 0.94 | 0.84 |
| 30 | 0.89 | 0.94 | 0.93 | 0.85 |
| 32 | **0.84** | 0.92 | 0.91 | 0.88 |

Decline rates: 0% at depth 4 everywhere; ≤1.3% at depth 5; 24→37% at depth 6
(rising with n); 89–94% at depth 8 — the depth-8 rows are survivor-only medians over
18–33 formulas and carry the documented selection bias (declined counts published
alongside). live_k distributions: median 5–6 / 9–10 / 14–15 / 22–28 at depths
4/5/6/8 — depth, not n, controls live_k, confirming §7b at 4× the ambient size.

**New finding — the ratio drifts in CM's favor as ambient n grows** (e.g. depth 4:
1.01 → 0.84 from n=24 → 32; the same monotone drift at every depth; by n=30–32 CM's
end-to-end median is ahead at every depth). Mechanism (honest reading): CM's canonical
reduced program is size-independent of the ambient variable count, so its per-call cost
stays flat (~3.3 µs at depth 4), while the matched-scope Bitset control's per-call cost
grows with n (3.3 → 4.0 µs) — its raw AST and fixed-variable binding still reference
all n − live_k dropped variables (the bound-template cache key alone sorts ~26 fixed
entries at n=32). This is a real structural decoupling — the reduced representation
scales with the problem's true support, the raw formula with its nominal size — but at
these µs magnitudes a substantial share of the gap is fixed-binding bookkeeping in the
control, so we report it as a drift with a mechanism, not as "CM dominates at n=32".

**Audit V3 isolation:** Holding the exact formula, support, and FlatProgram constant while
increasing only ambient n from 24 to 32 raised the raw control by 1.83 µs. The cached
binder rose by 1.50 µs, prebound operation evaluation changed by -0.08 µs, and the CM
wrapper changed by -0.13 µs (`CM_V3AUDIT_F4_binding_profile_{raw,summary}.csv`). Thus the
isolated drift is a property of fixed-map key construction/cache lookup in this control,
not a growing raw-Bitset evaluation cost. The end-to-end measurements remain valid for
the current harness; the claimed representation mechanism does not.

## 7d. Comprehensive full-variable campaign (2026-07-22): nothing reduced, nothing pruned

Two regimes, requested to cover the populations the earlier campaigns didn't: formulas
where **every ambient variable is live** (computed at full 2^n output, n=16–32), and
formulas the guard previously **declined** (live_k 17–26, computed exactly over their
true support). Ran on RunPod: head on the standing $0.06/hr pod (n≤26; its container
RAM killed the n=28 attempt — recovered from the volume, nothing lost), tail + Regime B
on a temporary 16-vCPU/128 GB pod ($0.88/hr, ~25 min, terminated after download).
Data: `CM_FABLE_comprehensive_{fullvars,beyondguard}.csv` (+ `RECOVERED_*`, `*_tail_*`
provenance files); worker: `fable_comprehensive_worker_2026_07_22.py`.

**Correctness: every row bit-exact.** All methods agree over the complete computed
output (exhaustive by packed equality — including the full 2^32-row output at n=32),
and every formula passes a 2,000-row independent scalar oracle that re-evaluates the
original expression from scratch.

**Regime A — all-variables-live, full output (words engine medians):**

> **Audit V3 retraction of the liveness label:** `_balanced_all_vars_once` sometimes
> constructs `Xor(Xor(a,b), Eqv(a,Not(b)))`, which is constant false. The retry checks
> `CMNode.vars` (post-rewrite syntactic support), not semantic influence. Exact BDD
> support found only 4/29 committed rows truly all-live; median semantic support was 16,
> and the n=32 row's support was 16. The timings and bit-equality fields remain genuine
> full-*ambient-output* measurements of a sharing-rich family, but they do not establish
> all-variable liveness and must not be used as the n=32 all-live bracket. Audit V3's
> corrected generator excludes the cancelling EQV mixer, verifies exact BDD support, and
> finds CM 1.75–2.52× faster through n=26
> (`CM_V3AUDIT_F5_corrected_all_live_{raw,summary}.csv`).

| n | CM | Bitset | CM advantage | | n | CM | Bitset | CM advantage |
|--:|--:|--:|--:|---|--:|--:|--:|--:|
| 16 | 0.07 ms | 0.13 ms | 1.9× | | 26 | 45 ms | 112 ms | 2.5× |
| 18 | 0.16 ms | 0.29 ms | 1.9× | | 28 | 219 ms | 731 ms | 3.3× |
| 20 | 0.49 ms | 0.70 ms | 1.4× | | 30 | 0.97 s | 1.90 s | 2.0× |
| 22 | 2.3 ms | 4.0 ms | 1.7× | | 32 | **3.86 s** | **7.78 s** | **2.0×** |
| 24 | 10 ms | 15 ms | 1.4× | | | | | |

Bigint-engine ratios (n≤28) run 1.9–4.3× in CM's favor on the same formulas. **Family
caveat (the honest mechanism):** this generator builds XOR-joined trees with deliberate
subformula reuse, so it is a sharing-rich family — CM's interning collapses repeats
that the raw-AST Bitset re-executes. It brackets CM's structural advantage from above,
as the sparse random family (§7b: ~parity) brackets it from below. Both are true; a
paper should show both. Full 2^32-row exact computation with bit-verified agreement is
itself a first for this project.

**Regime B — beyond the guard, computed not pruned:** 72 formulas with live_k 17–26
(depths 6/8, n=24/28/32) — the population `--cm-max-full-output-vars 16` declines —
computed exactly over their true support (2^17–2^26 rows, up to ~30 ms each via words).
CM/Bitset ratio: median 0.96, p10–p90 0.90–1.03 — parity with a slight CM edge,
uniform across n and live_k. **Conclusion: the guard is a policy cap on output size,
not a capability wall; lifting it (a parameter) computes these formulas exactly at
ordinary cost.**

Audit V3 terminology correction: `live_k` here is the safe post-rewrite retained scope,
not a proof of globally minimal semantic support. Six local reproductions, including
retained_k 24–26, were complete packed matches plus sampled scalar-oracle matches
(`CM_V3AUDIT_F5_beyondguard_local.csv`); the policy-cap conclusion survives.

## 7e. CUDD/ROBDD apples-to-apples rerun on RunPod (2026-07-23)

Prior ROBDD comparisons (`ROBDD_CM_fair_comparison_report.md`, `CUDD_ROBDD_extraction_report.md`)
used `dd.autoref` or older CUDD-in-Docker numbers that were **not** run against the
endorsed CM/Bitset code state. This section supersedes them for CUDD head-to-head.

**Environment audit (2026-07-23):**

- Native Windows (CPython 3.10.11): `dd 0.5.7` pure-Python wheel — `dd.autoref` OK,
  `dd.cudd` **not importable**. Native Windows can never be labeled CUDD.
- Docker Desktop (WSL2 `docker-desktop` distro, `python:3.10-slim`): `pip install dd`
  selects the manylinux wheel; `dd.cudd` imports from
  `dd/cudd.cpython-310-x86_64-linux-gnu.so`. Verified again this session (smoke run
  `bench_cudd_docker_smoke_*.csv`, all rows `robdd_backend=dd.cudd`).
- **RunPod pod `x82z2pbpofhcgz`** (cm-computation-worker, 2 vCPU / 4 GB, $0.06/hr,
  Python 3.10.20, Linux 6.5): `dd.cudd` imports from the same manylinux wheel. All
  headline numbers below are from this pod.

**Method.** The endorsed repo state (root `*.py` + `cmbench/`) was pushed to the pod
via the bootstrap `/put`+`/deploy` channel and `cm_bench.py` was run **twice in the
same environment**, once per ROBDD backend, with CM, Bitset, and ROBDD computed inside
each single invocation — so every row of a run uses the identical seeded expression,
and the two runs use the identical expression stream (verified: per-(n, trial)
`expr_node_count`/`expr_vars_used_count`/`expr_depth_actual` match exactly across runs):

```
python cm_bench.py --sizes 16,18,20,22,24 --trials 8 --max-depth 4 --seed 424242 \
  --expr-style ordinary --cm-layout balanced --cm-compare-no-reinflate \
  --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 \
  --cm-flat-eval --cm-max-full-output-vars 16 --large-n-safe \
  --no-espresso --no-sympy --no-bdd-sop --no-numba \
  --robdd-dd-backend {cudd|autoref} --robdd-order-policy best-of-k \
  --robdd-order-sweeps 10 --robdd-measure-tt-extract --robdd-tt-extract-max-n 16 \
  --print-summary --out-prefix bench_{cudd|autoref}_matched_headline_runpod
```

Outputs: `deliverables_n22_24/CM_FABLE_cudd_matched_headline_runpod_{raw,summary}.csv`,
`CM_FABLE_autoref_matched_headline_runpod_{raw,summary}.csv` (same dir; the gitignored repo-root `bench_*_runpod_*.csv` copies are identical).

**Backend identity validation (from the raw CSVs, all 40 rows each):** CUDD run has
`robdd_backend = robdd_backend_module = dd.cudd`, `robdd_is_cudd = True`,
`robdd_cudd_available = True`, `robdd_status = ok`, `robdd_ok = True`; autoref run has
`dd.autoref` / `robdd_is_cudd = False` / `status ok`. All CM/Bitset/ROBDD correctness
flags true in both runs. Note `--robdd-dd-backend cudd` does **not** fall back
silently — if `dd.cudd` were missing the rows would read `robdd_status=unavailable`
(demonstrated on native Windows in `smoke_robdd_cudd_required_raw.csv`).

**Results (medians over 8 trials/n, RunPod pod, seconds):**

| n | CUDD build | autoref build | CUDD build+TT-extract | autoref build+TT-extract | CM no-reinflate (full) | Bitset (full) |
|--:|--:|--:|--:|--:|--:|--:|
| 16 | 0.000025 | 0.000104 | 0.364 | 0.753 | 0.000090 | 0.000075 |
| 18 | 0.000016 | 0.000090 | — | — | 0.000198 | 0.000027 |
| 20 | 0.000013 | 0.000103 | — | — | 0.000220 | 0.000028 |
| 22 | 0.000015 | 0.000110 | — | — | 0.000233 | 0.000031 |
| 24 | 0.000020 | 0.000167 | — | — | 0.000457 | 0.000070 |

Cached per-eval (µs, CUDD run): CM no-reinflate 17.1 / 3.9 / 3.8 / 4.0 / 243.2 vs
Bitset 19.0 / 3.2 / 3.1 / 3.5 / 4.0 at n = 16/18/20/22/24 (the n=24 CM value is the
known `hybrid_threshold=7` mis-tuning stratum; see §7b — thr=16 removes it).

**Reading, kept deliberately conservative:**

- **CUDD symbolic build and CUDD build+truth-table extraction are different metrics
  and must not be collapsed.** Symbolic build (13–25 µs median) beats every flat-output
  method — but it produces a BDD, not a truth table.
- When the deliverable is the flat 2^n output, extraction dominates CUDD entirely:
  0.364 s at n=16 (guarded off above n=16 by `--robdd-tt-extract-max-n 16`), roughly
  4,000–5,000× the Bitset full-output time on the same expressions.
- CUDD build is ~5–8× faster than `dd.autoref` build on identical expressions in the
  identical environment; extraction is ~2× faster than autoref's at n=16.
- Depth-4 `ordinary` expressions collapse to small BDDs (9–20 nodes), so build times
  here measure the small-BDD regime only; no claim is made about hard/large-BDD
  workloads.

**Wrapper-campaign extension to n=32 (2026-07-23, RunPod).** To put CUDD next to the
§7b/§7c wrapper chart at every n including 32,
`fable_cudd_wrapper32_campaign_2026_07_23.py` (this directory) regenerated the exact
wrapper-campaign expression stream — `random_expr` depth 4, seeds
`9_100_000 + 10_000·n + trial`, 300 formulas/n, threshold 16, guard 16, 5 interleaved
rounds — for n ∈ {16…32}, and added per-formula ROBDD symbolic-build timing for both
`dd.cudd` and `dd.autoref` (best-of-10 random orders, 64 sampled-assignment
correctness checks per build; exhaustive checks are infeasible at 2^32). Outputs
`CM_FABLE_cudd_wrapper32_{raw,summary}.csv`. Validation: 2,700/2,700 rows
`robdd_is_cudd=True`/`status=ok` on the CUDD side, all sampled checks passed, all
CM-vs-Bitset bit checks passed; same-session CM/Bitset medians reproduce the wrapper
curve's shape (1.05/1.16/1.11/1.05/0.99/0.94/0.90/0.88/0.83 here, vs the archived
Fable series 1.04/1.25/1.18/1.12/1.02/0.98/0.92/0.89/0.84 and Audit V3's paired rerun
1.05/1.27/1.23/1.15/1.05 through n=24 — the series now on the chart pages).

| n | CM/Bitset (this rerun) | CUDD build µs | autoref build µs | CUDD-build/Bitset | CUDD nodes |
|--:|--:|--:|--:|--:|--:|
| 16 | 1.05 | 14.5 | 103.9 | 0.63 | 8 |
| 18 | 1.16 | 13.8 | 105.1 | 4.40 | 9 |
| 20 | 1.11 | 15.2 | 117.3 | 4.62 | 10 |
| 22 | 1.05 | 17.3 | 110.9 | 4.81 | 10 |
| 24 | 0.99 | 12.0 | 106.0 | 3.41 | 9 |
| 26 | 0.94 | 12.1 | 112.4 | 3.34 | 10 |
| 28 | 0.90 | 12.5 | 117.3 | 3.18 | 10 |
| 30 | 0.88 | 13.1 | 123.0 | 3.19 | 12 |
| 32 | 0.83 | 14.0 | 115.4 | 3.24 | 11 |

Reading: on this reduced-scope regime (Bitset ≈ 3–4 µs at n≥18), CUDD's symbolic build
runs ~3.2–4.8× the Bitset flat-output time — constant in n, as expected for the
n-independent live support — while remaining ~8× faster than `dd.autoref`. At n=16 the
comparison flips (0.63) only because the full 2^16 output makes Bitset slower, not
because CUDD changed. **The CUDD bars are a different deliverable (a graph, not the
flat answer)**: they are charted next to the wrapper bars on the two chart pages with
that caveat stated, and no CUDD build+extract number exists beyond n=16 by design.

**Limitations:** the pod has 2 shared vCPUs — absolute times are noisier than a
dedicated box (§8 variance statement applies); `best-of-k` ordering (10 sweeps) was
granted to ROBDD, favoring it; TT extraction was measured only at n=16 by design;
the RunPod numbers should not be mixed with the local-Docker smoke numbers.

## 8. Variance statement

Full-arity large-n session CVs in this session's runs were 7–16% (consistent with the
third party's 6–10%, better-behaved than the inherited ±30–50% warning), but tiny
microsecond-scale reduced outputs remain noisy (per-trial CM/raw spread 0.6–1.7 plus
repr-4 outliers). Report ranges and medians with the repr mix; never single constants.
