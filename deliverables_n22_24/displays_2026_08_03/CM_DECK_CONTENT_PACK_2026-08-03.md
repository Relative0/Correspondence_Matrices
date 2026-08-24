# CM deck content pack — rebuilt from the 2026-08-03 benchmark refresh

Slide-by-slide content for the deck rebuild. The deck PDF is frozen at Audit
V4 (2026-07-24); this pack replaces its benchmark section outright.

**Companion chart page:** `cm_benchmark_refresh_charts_2026_08_03.html`
(regenerate with `cm_display_build_2026_08_03.py`). Each slide below names the
chart panel id (`#c1` … `#c16`) that supplies its figure.

**Provenance:** display build at git `6e8a283`; campaign evidence generated at
git `eab8879`, committed across `7de7120`, `5fb2763`, `85673e9`, `61fec68`
(B1–B7) and `891f56c`, `6e8a283` (BX1, BX2). Every number on every slide is
read from a raw or summary file by the build script — none is retyped from
prose. Per-panel file+field lists are in the "Data provenance" disclosure on
each chart card and in `cm_display_data_2026_08_03.json`.

**Scope labels are mandatory on every figure.** Three scopes appear and are
never pooled: *synthetic generator* (`e3-corrected-2026-08-02.1`, local
Windows/Ryzen), *EPFL AND/INV cones* (real circuits, local Windows/Ryzen),
*pod platform* (Linux/AMD EPYC). `live_k` is the x-axis wherever a support
size appears — never nominal `n`.

---

## Slide 1 — Where the advantage actually is

**Chart:** `#c1` — forest plot, CM kernel ÷ plain structural CSE, three scopes
with their own CIs.

**Headline:** The repaired CM kernel is 7–13% faster than plain structural CSE,
and the result reproduces off the development box.

**Body:**
- Local synthetic, 192 formulas: **0.8876** [0.873, 0.902] (stratified-by-cell
  bootstrap, independent reaggregation).
- External EPFL, 129 cones from 19 real circuits: **0.9268** [0.9026, 0.9507]
  (circuit-clustered bootstrap).
- Five Linux/EPYC pods: **0.8773 – 0.8884**, every CI excluding parity.

**Mechanism line (say this, it is the honest one):** the advantage is *n-ary
instruction merging*, not semantic op-compression. On the EPFL circuits CM
emits exactly the CSE-flat instruction and executed-op counts (both ratios
1.000) — the mechanism predicts parity there, and parity is measured.

**Claim-map rows:** 1, 11, 12.

---

## Slide 2 — And where it is not: kernel equivalence with strong CSE

**Chart:** `#c2` — same forest form, ratio vs CSE + sharing-aware flattening.

**Headline:** Against a CSE baseline that also flattens, CM is
kernel-*equivalent*. Outcome A is final.

**Body:**
- External EPFL primary: **0.9998** [0.9747, 1.0249], circuit-clustered.
- Local synthetic: 1.004. Pods: 0.960–0.971.
- The residual straddles parity and **its sign is not stable** — 1.004 local,
  0.9998 external, 0.96–0.97 on EPYC. Never present it as a CM win in either
  direction; say "≈parity".
- Pre-registered materiality rule, applied as written: geomean ≤ 0.95 → **no**;
  clustered CI excludes parity → **no**; median break-even ≤ 1000 → yes.
  Conditions fail ⇒ optimization not warranted, **Outcome A converts
  provisional → final**.

**So-what:** the differentiators are canonical keys, the persistent cache, and
serde — not kernel speed. Say that plainly; it is a stronger position than a
contested 1.5%.

**Claim-map row:** 10.

---

## Slide 3 — What moves the number (local detail)

**Chart:** `#c3` — two panels: bars by live_k, then the family × shape grid.

**Body:** Strata 0.875 / 0.868 / 0.921 at live_k 8 / 12 / 16. The family × shape
grid (24 formulas per cell) is where the variation lives:

| family | tree | shared |
|---|---|---|
| xor_dom | 0.844 | **0.755** |
| andor_dom | 0.944 | 0.848 |
| impeqv_dom | 0.977 | 0.936 |
| mixed | **0.991** | 0.834 |

XOR-dominant shared formulas benefit most (longest mergeable chains); mixed
trees sit at parity (0.991, CI [0.960, 1.023] touching 1.00). Identity fields
exact on 192/192; CI overlaps the archived result.

*Reporting note:* the B1 summary reports family and shape only as this
interaction grid — there are no family-only or shape-only marginal rows, so do
not quote a "by family" average.

*Optional slide — fold into slide 1's notes if the deck is tight.*

**Claim-map row:** 1.

---

## Slide 4 — External validation, circuit by circuit

**Chart:** `#c4` — dumbbell, 19 EPFL circuits, both arms.

**Body:** 129 admitted cones, 0 runtime-guard skips. Against CSE-flat the
circuits scatter symmetrically around parity (0.893 – 1.104); against plain CSE
almost every circuit sits below 1.00. By semantic support: 8–10 → 1.018,
11–13 → 0.986, 14–16 → 0.978.

**Discipline note for the speaker:** per-circuit values are descriptive only.
The single inferential statement is the circuit-clustered all-corpus CI on
slide 2.

**Claim-map rows:** 10, 11.

---

## Slide 5 — It is not a one-box result (NEW)

**Chart:** `#c5` — per-pod forest against the local reference line.

**Headline:** Cross-platform replication passed, 5/5.

**Body:** Five RunPod `cpu3c` pods (AMD EPYC, Linux, numpy 2.2.6 vs 2.3.2
local) re-ran the SHA-verified frozen corpus through the frozen driver.
Identity fields exact on 192/192 per pod; every CI excludes parity; pod-to-pod
spread **0.011** (σ 0.0046) against a local reference of 0.8876.

**Say the caveat:** the cm/cse_flat arm tilts to 0.96–0.97 on EPYC vs ≈1.00
local. That is the "residual sign is not stable" caveat measured on a second
CPU family — report it, do not pool it away.

**Claim-map row:** 12 (UPGRADED from "no cross-platform claim").

---

## Slide 6 — The wrapper boundary: REWRITTEN

**Chart:** `#c6` — CM wrapper ÷ bare BitSet by live_k, cached and uncached.

> **This slide replaces the V4 C1 slide. The old chart and the sentence
> "CM modestly ahead at controlled live_k 12/16" must not reappear anywhere.**

**Headline:** At the wrapper boundary, BitSet leads at every live_k ≤ 16.

**Body:** Cached medians 7.83× (k=4) → 1.40× (k=16); uncached warm-env
3.6–4.3× throughout. The trend falls with live_k but never crosses parity; the
crossover, if any, sits above the k=16 guard. p10 reaches ~0.96 only at
k=12/16 — a minority of formulas, never a median.

**Corroboration:** `#c8` re-runs the *exact* V4 C1 protocol on
corrected-admission corpora and agrees (1.29–1.80 at every cell).

**Where CM's story lives instead:** the kernel level (slides 1–2) plus
canonical keys, persistent cache, serde.

**Claim-map row:** 4 (REVISED).

---

## Slide 7 — Why: overhead is co-equal through k = 16

**Chart:** `#c7` — grouped columns, CM wrapper total / bare BitSet / overhead.

**Body:** Median wrapper overhead grows **50 → 91 µs** across k=6…16 while the
kernels are tens of µs. The archived "median 23 µs" is superseded on this
corpus and protocol — and the qualitative claim it supported (overhead
dominates the small-k harness boundary) comes out *stronger*.

**Claim-map row:** 5 (REVISED).

---

## Slide 8 — Nominal n is not workload size

**Chart:** `#c8` — grouped columns, live_k × ambient n.

**Body:** The same formulas embedded at ambient n ∈ {16, 20, 24} by fixing dead
variables. Ratios are flat across ambient n at fixed live_k (k=8: 1.76/1.77/1.80;
k=12: 1.71/1.69/1.72; k=16: 1.29/1.33/1.33). The guard sweep says the same
thing: median live_k is 5–6 at depth 4 regardless of whether n is 16 or 24.

**Claim-map rows:** 6 (CONFIRMED) and 4 (REVISED) — one chart, both facts.

---

## Slide 9 — Guard correctness

**Chart:** `#c9` — decline rate by n, grouped by depth.

**Headline:** 0 wrong guards and 0 oversized outputs in 3,000 fresh trials.

**Body:** Depth 4 → 0% decline at every n; depth 6 → 2–24% (n=18→24); depth 8 →
75–93%. These fresh post-repair numbers replace the superseded pre-repair
n ≥ 18 sweeps.

**Claim-map row:** 7 (CONFIRMED).

---

## Slide 10 — Compilation scales with structure, not tree size

**Chart:** `#c10` — two panels; the orange shared-ladder line is the money plot.

**Body:** One ladder structure deepened step by step, so *only* the unfolding
grows: 123 → **8,388,603 unfolded operator occurrences (68,200×) while prep
rises only 352.5 µs → 984.5 µs (2.8×)**. Plotted against structural DAG nodes
instead, the same points climb like everything else. Prep multiple vs CSE
2.2–7.9× across all 31 cases. All 31 passed complete packed equality before
timing.

**Speaker honesty note:** the blue cloud (24 other cases) drifts upward in
panel 1 because those cases vary structure *and* unfolding at once. The
controlled ladder family is what carries the claim — say so rather than
gesturing at the whole cloud.

**Claim-map row:** 8 (CONFIRMED).

---

## Slide 11 — The cost side: reuse count decides

**Chart:** `#c11` — two break-even histograms with the never-break-even mass
called out in orange.

**Body:**
- Synthetic vs plain CSE: prep **4.40×**, median **78.0** evaluations over 157
  that break even, **35 of 192 never do**.
- EPFL vs CSE-flat: prep **4.11×**, median **174.5** over 74 finite,
  **55 of 129 never do**.
- On real circuits the median finite break-even is more than twice the
  synthetic one, and 43% of cones never repay the prep cost at any reuse count.

**Two things to keep straight on this slide:** the baselines differ by design
(plain CSE for the synthetic arm, CSE-flat for the external arm) and are not
comparable to each other; and the 78.0/35 figures are the B1 *fresh replay*,
not the archived 78.5/30 — see the flags section below.

**Claim-map row:** 9 (CONFIRMED + extended).

---

## Slide 12 — CUDD: two panels, never one winner (NEW same-box evidence)

**Chart:** `#c12` — panel 1 construction, panel 2 evaluation (log, dots).

**Body:**
- **Construction:** CUDD build 2,488 / 2,507 / 2,580 µs vs CM prep 266 / 388 /
  521 µs and CSE-flat prep 78 / 107 / 129 µs. CUDD's strength is real and shows
  in the representation: 17 / 42 / 78 BDD nodes instead of 2^k truth bits.
- **Evaluation to packed output:** CM words kernel 15.4 / 24.2 / 45.4 µs vs
  CUDD full 2^k extraction 1.14 ms / 25.6 ms / 580 ms — **74× / 1,059× /
  12,782×** slower. Even 256 assignments cost ~20× a full packed kernel call.
- **Correctness bar exceeds the archived run:** `robdd_is_cudd` true on all 192
  rows (fail-closed, no autoref fallback) and **full 2^k extraction packed-equal
  to the CM bits on every formula** — exhaustive, not sampled.

**Never** render construction and evaluation as a single three-way leaderboard.
This fills Audit V4's blocked same-box primary experiment.

**Claim-map row:** 13 (CONFIRMED, same-box matched).

---

## Slide 13 — CUDD variable ordering, with the search cost quoted (NEW)

**Chart:** `#c16` — panel 1 BDD size, panel 2 search cost.

**Body:** Best-of-10 order search buys node ratios 0.79 / 0.71 / 0.70 (a 21–30%
reduction) at a *pure* search cost of 156 / 249 / 392 µs against single builds
of 18 / 28 / 40 µs — **8.5× / 8.8× / 9.9×**. Dynamic reordering is a no-op at this
scale: node ratio exactly 1.00 in every stratum, because these BDDs (≤78 nodes)
never reach CUDD's reordering trigger.

**Axis warning that must appear on the slide:** this build window is
expression-to-BDD conversion only (Audit V4's convention), *after* manager
creation. Slide 12's `cudd_build_us` (~2.5 ms) includes manager creation and
variable declaration. Both are real costs answering different questions — never
plot them on the same axis.

**Claim-map addendum row:** 14 (CLOSED with data). B5 used fixed natural order,
so slide 12 is unaffected.

---

## Slide 14 — Engine selection is workload-dependent (NEW, REVISES a claim)

**Chart:** `#c15` — three engine curves vs live_k.

**Body:** Flat bigint beats the recursive evaluator at every live_k (0.55–0.88×)
— that half of the claim strengthens. But the words engine carries ~15–20 µs of
fixed dispatch, so on corrected-E3-scale formulas **flat stays fastest through
k = 12 and words wins only at k = 16** (0.82× vs flat; k=12 is still 2.7×
slower than flat).

**Restate the claim as:** words wins once (2^k words) × ops amortises ~20 µs of
fixed dispatch — *not* at a universal k = 6. The deck-era corpora had larger
per-formula op counts and genuinely crossed at 6; both statements are
corpus-scoped.

**No earlier conclusion changes:** B2 and B4 used words symmetrically on both
sides at every k ≥ 6. But an engine selector keyed only on `k ≥ 6` leaves 2–5×
on the table for small formulas at k = 6–12.

**Claim-map addendum row:** 15 (REVISED — workload-dependent).

---

## Slide 15 — Method discipline

**Chart:** `#c14` — blocked vs round-robin, every source.

**Body:** Both cache schedules are reported for every source and **never
pooled**. Agreement is tight externally (EPFL +0.78%) and on every pod (+0.51%
to +0.92%). On the synthetic corpus it is not: the B1 fresh replay disagrees by
+5.18% all-corpus (up to +12.9% per cell) where the archived run of the same
corpus disagreed by +1.91%.

**Also say:** CIs are always shown with their clustering basis —
stratified-by-cell (synthetic), circuit-clustered (EPFL), per-pod (replication).

**Claim-map row:** 16 — the "never pooled" half is CONFIRMED; the "agree within
~1–2%" half needs narrowing (see flags).

---

## Slide 16 (optional) — Corrections

**Chart:** `#corrections` table on the page.

Use only if the audience saw the V4 deck. Otherwise omit entirely — these
numbers should appear nowhere else.

| superseded | replaced by |
|---|---|
| E3 0.843 [0.780, 0.894] (96-formula degenerate corpus) | 0.8876 [0.873, 0.902], B1 fresh replay |
| 128× / 240× multiplier compression | retracted — post-repair CM executes the CSE op count (368 → 167) |
| V4 C1 "CM modestly ahead at live_k 12/16" (0.925) | BitSet leads at every live_k ≤ 16 (1.40–7.83 B2, 1.29–1.80 B4) |
| wrapper overhead median 23 µs | 50–91 µs on the B2 corpus/protocol |
| pre-repair n ≥ 18 ratios | B4 fresh post-repair sweep, 3,000 trials |
| engine crossover "words at k ≥ 6" | workload-dependent; between k=12 and k=16 at this formula scale |

---

## Flags — claim-map prose the raw evidence does not fully support

Found while re-reading every number from its source file. Neither changes a
campaign verdict; both change how a sentence should be worded.

1. **Row 16, "blocked and round-robin agree within ~1–2%."** True for the
   archived 2026-08-02 run (+1.91%), EPFL (+0.78%) and all five pods (+0.51% to
   +0.92%) — but the B1 *fresh replay* the campaign designates as the reference
   disagrees by +5.18% all-corpus, with per-cell gaps to +12.93%. Narrow the
   claim to the external and pod evidence, or restate as "agree within ~2%
   except on the synthetic corpus, where the schedule effect is itself
   run-variable (1.9% archived vs 5.2% replay)." The "never pooled" half is
   unaffected and is honoured throughout.
2. **Row 9, "break-even median 78.5, 30/192 never."** Those are the archived
   2026-08-02 numbers; the B1 fresh replay reports **78.0 over 157 finite and
   35/192 never**. Break-even is a prep-delta ÷ per-eval-gain ratio, so it moves
   with ordinary timing noise. The charts plot the replay values to match the
   replay headline; the workload-dependence conclusion is identical either way.

---

## Narrative skeleton (the four-beat version, if you need a short deck)

1. **Kernel level.** Repaired CM is 7–13% faster than plain structural CSE
   (0.888 synthetic, 0.927 external, 0.877–0.888 across five Linux pods) and
   **kernel-equivalent to CSE + sharing-aware flattening everywhere**.
   Mechanism: n-ary instruction merging. Outcome A is final — the
   differentiators are canonical keys, persistent cache, serde, not kernel
   speed. → slides 1, 2, 5
2. **Wrapper level.** BitSet leads at every measured live_k ≤ 16 on
   exact-support corpora; overhead 50–91 µs. The old "modestly ahead at 12/16"
   sentence is gone. → slides 6, 7, 8
3. **Costs.** Prep 4.1–4.3× CSE; break-even median 78 (synthetic) / 174.5
   finite with 55/129 never (EPFL). Reuse-count dependence is the story. →
   slide 11
4. **CUDD.** Compact symbolic builds, but packed output 74×–12,800× slower;
   a separate comparison, never a three-way winner. → slides 12, 13
