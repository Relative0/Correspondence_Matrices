> **Correction (2026-07-21, see `deliverables_n22_24/CM_ARCHITECTURE_AND_AUDIT.md` §4.3):**
> the "ROBDD/CUDD unavailable on native Windows" statements below are imprecise. **CUDD** is
> unavailable here; the **ROBDD backend via `dd.autoref` did run and was verified correct**
> (`robdd_ok=True`, `exact_tt`). The null I saw was an empty TT-*extraction* column, not a
> failed build. Also note the benchmark interpreter is Python **3.13.5** (venv), not 3.10.11.

# CM n=18/20 Feasibility Report

> Measurement campaign for Correspondence Matrices at n=18 and n=20, focused on the
> `materialize_hybrid_no_reinflate` reduced-output path and how the comparison methods
> (raw bitset, `dd`, ROBDD) scale alongside it. Follows `OPUS_N20_RUNPOD_AGENDA.md`.
>
> Machine: Windows 10, Python 3.10.11, `.\.venv\Scripts\python.exe`. Base commit `1a984e4`.
> Date: 2026-07-21. **No library code was changed** (measurement-only campaign), so the
> `python -m pytest -q` 159/159 baseline is unaffected — nothing in the timed paths, the
> guard, or the diagnostics was touched. The reduced-output guard
> (`cm_ir.py:1441-1494`) and `--cm-max-full-output-vars 16` were used exactly as shipped.

---

## 1. Headline verdict

**n=18 and n=20 are feasible for the CM no-reinflate path — but feasibility is governed by
the expression's *live-variable count* `live_k`, not by the nominal `n`.** The path stays
cheap and correct whenever `live_k ≤ 16` (the `--cm-max-full-output-vars` guard). When an
expression is structurally rich enough that all `n` variables are live (`live_k > 16`), the
guard **correctly refuses** to materialize — this is by design, not a failure: CM never
builds a dense 2^18 / 2^20 output.

Across the headline sweep (n=16/18/20, 8 trials each, depth-4 random expressions, threshold
7), CM no-reinflate was **correct on every trial** with **0 mismatches across 24,000
independent sampled-oracle checks**, running at **~1.7–1.8× the matched-scope raw-bitset
baseline** in the compile-once/cached regime.

### 1.1 Second finding: RunPod was not needed, and why

The agenda's premise (§2) was that the correctness oracle `eval_expr_tt` costs
"2^20 Python evals per expression, roughly seconds-to-tens-of-seconds," motivating remote
offload. **That premise is outdated: `eval_expr_tt` (`cm_exprlib.py:80`) is fully
numpy-vectorized** — one array op per AST node over the 2^n rows — so the measured oracle
cost is:

| n | 2^n rows | `eval_expr_tt` (vectorized) |
|--:|--:|--:|
| 16 | 65,536 | ~19 ms |
| 18 | 262,144 | ~118 ms |
| 20 | 1,048,576 | ~583 ms |

Sub-second at n=20. Furthermore, in `--large-n-safe` mode the full 2^n oracle **does not
run at all**: correctness is verified by (a) self-consistency of the CM reduced output vs
`eval_cm_node_bitset` over the *same reduced* variables, and (b) an optional independent
`--sampled-correctness K` check that evaluates the AST **per sampled assignment**
(`cmbench/expr/eval.py:37`, no full-TT build). Both are cheap.

The consequence: the CM reduced path, the raw-bitset baseline, and the oracle are **all
locally cheap at n=20**. A 2-vCPU RunPod pod ($0.06/hr) with ~6 s of proxy/readiness wall
overhead per remote call offers **no compute advantage** for this workload. Per an explicit
decision on this campaign, all measurement was performed **locally**; **pod-hours spent:
0** (pod left `EXITED`, never started).

---

## 2. Setup

- Generator: `random_expr` (depth-4 unless noted), balanced CM layout, seed 123.
- CM path: `compile_expr_to_cm_ir` → `materialize_hybrid_no_reinflate`, persistent
  structural-hash IR cache on, `--cm-hybrid-threshold 7`, `--cm-max-full-output-vars 16`,
  `--large-n-safe` for n>16 (routes through the reduced-output guard).
- Cached per-eval = median over `--cm-eval-repeat 100`, instrumentation off for headline
  numbers (separate runs for the profile/breakdown columns).
- Comparison methods: raw bitset always; `dd` (dd.autoref, pure Python) as the symbolic
  baseline. **ROBDD/CUDD is unavailable on native Windows** (handoff §7: `dd.cudd` does not
  import here) and returned null on every trial — noted, not a CM finding.
- `--no-espresso --no-sympy --no-numba --no-bdd-sop` throughout (impractical/irrelevant at
  this scale).

Representation codes (from `FinalNoReinflateResult`): **1** full TT vector, **2** full
packed bitset, **3** reduced packed bitset (live vars only), **4** reduced TT vector.

---

## 3. Headline table — CM no-reinflate (reduced) vs raw bitset

Depth-4 random expressions, 8 trials/n, cached per-eval medians, `--large-n-safe`.
CM and bitset are compared over the **same output scope** (full at n=16; the reduced live
vars at n=18/20), which is the only apples-to-apples comparison — CM does not, by design,
produce a full 2^18/2^20 output.

| n | live_k (per-trial range) | repr codes | guard fired | CM cached µs | bitset cached µs | ratio CM/bitset | correctness |
|--:|:--|:--|--:|--:|--:|--:|:--|
| 16 | 16 (all) | 1, 2 | 0/8 | 123.8 | 73.5 | **1.68×** | 8/8 OK, 0/8000 mm |
| 18 | 1–8 | 3, 4 | 8/8 | 29.8 | 16.6 | **1.80×** | 8/8 OK, 0/8000 mm |
| 20 | 1–9 | 3, 4 | 8/8 | 21.8 | 12.8 | **1.71×** | 8/8 OK, 0/8000 mm |

Readings:
- **n=18/20 absolute times are *lower* than n=16**, because the reduced output tracks
  `live_k` (1–9 here), not nominal n. This is the core "runtime tracks reduced live-var
  count" property, confirmed at 18/20.
- The ~1.7–1.8× residual vs matched-scope bitset is consistent with the post-R1/R2/R3 n≤16
  baselines (`CM_speedup_phase2_report.md`: 1.9× at n=16) and is the known
  per-node dispatch/wrap scaffolding overhead, not a scaling wall.
- **Zero correctness mismatches** across 24,000 sampled-oracle checks (8 trials × 1000
  samples × 3 sizes).

---

## 4. Guard behavior (agenda §4.3) — feasibility is a function of live_k

The reduced-output guard has three outcomes at n>16: **repr 3** (clean, `live_k ≤ 7`, packed
bitset), **repr 4** (clean, `7 < live_k ≤ 16`, TT-vector fallback), and **refusal** (the
`cm_ir.py:1491` `ValueError`, `live_k > 16`). I swept expression depth at n=20 (30
expressions/depth) to map how often each fires:

| depth | repr 3 (bitset, live≤7) | repr 4 (TT, 7<live≤16) | refused (live>16) | live_k range |
|--:|--:|--:|--:|:--|
| 2  | 30 | 0  | 0  | 1–4  |
| 4  | 16 | 14 | 0  | 0–11 |
| 6  | 0  | 17 | 13 | 8–20 |
| 8  | 0  | 0  | 30 | 17–20 |
| 10 | 0  | 0  | 30 | 20   |

The refusal is the intended guard `ValueError`
(`refusing to materialize reduced no-reinflate output for 20 live variables;
max_full_output_vars=16`), confirmed directly. **Interpretation:** n=20 CM is feasible for
structurally simple / low-fan-in functions (shallow, or few live variables) and is *correctly*
declined for functions that genuinely depend on all 20 inputs — for which there is no
sub-2^20 representation and bitset/BDD are the right tools. The guard never silently produced
a wrong or oversized output.

---

## 5. Regime split (agenda §4.2)

`--cm-profile-cached-exec`, cumulative component sums (proportions, not per-eval absolutes):

| n | bitset-eval | dispatch | var-order | result-wrap | dominant term |
|--:|--:|--:|--:|--:|:--|
| 16 | ~85% | ~6% | ~1% | ~7% | **bitset-eval** (2^16-bit bigint arithmetic) |
| 18 | ~46% | ~23% | ~4% | ~25% | bitset-eval, but scaffolding now comparable |
| 20 | ~55% | ~21% | ~4% | ~19% | bitset-eval, scaffolding comparable |

At n=16 (full 65,536-bit output) the cached regime is **bitset-eval-dominated**, matching
`CM_pre_writing_validation_report.md`. At n=18/20 the reduced outputs are tiny (2^live_k,
live_k≤9 here), so the fixed per-node Python scaffolding (dispatch + result-wrap) rises to
roughly half the cost — i.e. the reduced path is **not** bigint-op-bound; it is bounded by
fixed interpreter overhead, exactly the regime the Tier-C flat evaluator
(`CM_tierC_rescope_report.md`) targets.

---

## 6. Comparison methods at scale

Full-output runs (no `--large-n-safe`), depth-4, ms medians. `dd` = dd.autoref build.

| n | raw bitset (ms) | dd (ms) | dd nodes | CM no-reinflate |
|--:|--:|--:|--:|:--|
| 8  | 0.021 | 0.23 | — | 0.097 ms (full, repr 1/2) |
| 12 | 0.024 | 0.20 | — | 0.074 ms |
| 16 | 0.068 | 0.23 | — | 0.122 ms |
| 18 | 0.17  | 0.27 | small | (reduced path — see §3) |
| 20 | 0.29–0.43 | 0.13–0.20 | 6–7 | (reduced path — see §3) |

- **Raw bitset scales fine to n=20** (0.3–0.4 ms full 2^20-bit output); a 2^20-bit bigint is
  ~128 KB and a whole-expression evaluation is sub-millisecond. Not a bottleneck.
- **`dd` (autoref) is essentially flat in n** (0.13–0.27 ms) because BDD size depends on
  the *function*, not the input count — these depth-4 functions have 6–7 node BDDs. This is
  build-only; flat-output extraction would add cost (a separate, previously-studied task).
- No ROBDD/CUDD numbers on native Windows (unavailable — §2). No timeouts were hit; the
  ~120 s time-box was never approached because these functions are structurally small.

---

## 7. Cost / wall-time accounting

- **RunPod pod-hours: 0.** Pod never started; confirmed the campaign is locally feasible
  before incurring any cost. The pod (`x82z2pbpofhcgz`, $0.06/hr) remains `EXITED`.
- Total local wall time for the full matrix (headline + profile + ir-breakdown +
  cross-method + guard-rate + probes): a few minutes. The dominant single cost is the
  vectorized oracle (~0.58 s/expr at n=20), which is why full sampled-oracle verification
  (24,000 checks) was affordable without subsampling.

## 8. Verdict and recommended next steps

**Verdict:** n=18 and n=20 are feasible and bit-correct for the CM `hybrid_no_reinflate`
reduced-output path **whenever `live_k ≤ 16`**, at ~1.7–1.8× matched-scope bitset in the
cached regime; the guard cleanly and correctly refuses the `live_k > 16` case rather than
materializing 2^n. The scaling story is **live-var-bound, not n-bound** — exactly the
structural-reduction thesis, now confirmed two sizes past the previous n=16 frontier.
RunPod is unnecessary for this workload; the oracle-cost premise that motivated it does not
hold against the vectorized `eval_expr_tt`.

**Recommended next steps:**
1. **Prioritize the Tier-C flat evaluator (`CM_tierC_rescope_report.md`).** The n=18/20
   regime split shows reduced-output cost is dominated by fixed per-node scaffolding
   (dispatch + wrap ≈ half), precisely what C1a removes. This is the highest-leverage
   remaining win and its payoff *grows* at the reduced scale measured here.
2. If a full-output n>16 comparison against bitset/BDD is ever wanted, do it as an explicit
   *separate* study with matched output semantics — do not relax the guard. CM's value at
   n>16 is the reduced representation, not full materialization.
3. Retire the RunPod remote-oracle path from the critical benchmarking flow (keep it as an
   optional feature); update the agenda's §2 cost model to reflect the vectorized oracle.
4. To stress the guard's `repr 4` (TT-fallback, 7<live≤16) branch — thinly covered by
   depth-4 randoms — add a generator that targets `live_k ∈ {8..16}` at n=20 for a focused
   correctness/timing pass.

## 9. Artifacts

CSVs written to repo root (gitignored `*_raw.csv`/`*_summary.csv`; headline numbers pasted
above):
- `bench_n20_headline_*` — §3 headline (CM no-reinflate vs bitset, n=16/18/20).
- `bench_n20_profile_*` — §5 regime split (`--cm-profile-cached-exec`).
- `bench_n20_irbreak_*` — IR-stage breakdown companion.
- `bench_n20_crossmethod_*`, `bench_n20_robdd18_*`, `bench_n20_dd20_*` — §6 comparison.
- `bench_char_d{4,8,12}_*` — depth characterization feeding §4.
- Guard-rate-by-depth sweep (§4) reproduced inline via the CM API (no CSV).
