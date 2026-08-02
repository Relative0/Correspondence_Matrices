# BX2 — CUDD order sensitivity: best-of-10 + dynamic reordering (2026-08-03)

Optional-gap extension of B5, closing Audit V4's request for fixed-order,
best-of-k-with-search-totals, and dynamic-reorder rows on one box. Pod:
RunPod `cpu3c` SECURE, AMD EPYC 9655, python:3.10, dd 0.5.7 + CUDD from
source (fail-closed `dd.cudd` on all 192 rows), terminated after
collection. **Cost $0.0016.** Frozen corrected-E3 corpus (SHA verified
on-pod). Scripts: `cm_bx2_cudd_orders_2026_08_03.py` (+ worker/orchestrator
`cm_bx2_pod_*_2026_08_03.py`). Wall 4.8 s on-pod.

Correctness: 256 seeded assignments per variant vs the CM packed bits
(sampled mode, stated as such; the fixed-order arm carries B5's exhaustive
full-extraction equality on this same corpus). Zero mismatches across
192 × 12 builds.

**Timing convention note (differs from B5's build number):** the build
window here is expression-to-BDD conversion only, after manager creation
and variable declaration — Audit V4's convention. B5's `cudd_build_us`
(~2.5 ms) included fresh-manager creation + declaration; the conversion
itself is tens of µs. Both are real costs; they answer different questions
and must not be mixed in one chart.

## Results (medians per stratum)

| live_k | fixed build µs / nodes | best-10 selected µs / nodes | best-10 median µs | pure 10-build sum µs | search total incl. verification µs | reorder build µs / nodes |
|---:|---|---|---:|---:|---:|---|
| 8  | 18.3 / 17 | 13.4 / 14 | 13.4 | 156 | 15,378 | 14.2 / 17 |
| 12 | 28.3 / 42 | 21.2 / 29 | 23.0 | 249 | 18,959 | 23.8 / 42 |
| 16 | 39.5 / 78 | 31.5 / 54 | 35.7 | 392 | 22,277 | 34.8 / 78 |

Node ratios (median, selected vs fixed): 0.79 / 0.71 / 0.70 by stratum.

## Findings

1. **Best-of-10 buys a real but modest node reduction (~21–30%)** over the
   fixed natural order on this corpus, at a pure search cost of ~8–10× a
   single build (10 builds + manager setups; the recorded search-total
   column additionally includes per-order correctness checking and
   overstates pure search ~50×). V4's methodological point stands: quoting
   the selected order's build time without the search total is misleading.
2. **Dynamic reordering is a no-op at this scale**: final node counts are
   identical to fixed order in every stratum (ratio 1.00) — these BDDs
   (≤78 nodes) never reach CUDD's reordering trigger. The dynamic-reorder
   row exists now, and it says "irrelevant below the trigger threshold."
3. No conclusion of B5 changes: even the best-of-10 selected builds remain
   symbolic-construction numbers; packed extraction economics are untouched.

## Verdict

**BX2 COMPLETE — best-of-10 gives ~21–30% smaller BDDs for ~8–10× pure
search cost; dynamic reordering never triggers at k ≤ 16; V4's labeling
caution (search cost must be quoted) is confirmed with same-box data.**
