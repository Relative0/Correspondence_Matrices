# Claim Map Addendum — optional gaps BX1/BX2 (2026-08-03)

Extends `CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md` (rows 14–15) after
the two optional-gap runs. Base commit `61fec68`.

| # | deck claim | status | refreshed evidence |
|---|---|---|---|
| 15 (revisited) | Engine crossover: "bigint/flat below six variables, words at six and above" | **REVISED — workload-dependent** | BX1 (`bx1_crossover_2026_08_03\`): flat bigint beats recursive at every k (0.55–0.88, CONFIRMED); but on corrected-E3-scale formulas the words engine's ~15–20 µs fixed dispatch keeps flat fastest through k=12; words wins only at k=16 (0.82× vs flat). Restate as: words wins when (2^k words) × ops amortizes the fixed overhead — not at a universal k=6. Deck-era corpora (larger op counts) genuinely crossed at 6; both statements are corpus-scoped |
| 14 (revisited) | CUDD best-of-10 labeling; search cost excluded; reorder rows missing | **CLOSED with data** | BX2 (`bx2_cudd_orders_2026_08_03\`): best-of-10 selected BDDs 21–30% smaller than fixed order at ~8–10× pure search cost (10-build sums 156/249/392 µs vs single builds 18/28/40 µs); dynamic reordering never triggers at ≤78 nodes (node ratio 1.00). V4's "quote the search total" caution confirmed same-box |

Display note: BX1's crossover chart (three engine curves vs live_k, log-µs)
and BX2's two-panel (nodes: fixed/best10/reorder; cost: single build vs
10-build search sum) are both ready for the display agent; raw/summary
files are in the two directories above. The BX2 build-window convention
differs from B5's (conversion-only vs manager-inclusive) — never mix them
in one chart.

Costs: BX1 local ($0); BX2 one pod $0.0016, terminated; **RunPod account
verified to have zero pods remaining after collection.** Campaign pod total
now $0.0174.
