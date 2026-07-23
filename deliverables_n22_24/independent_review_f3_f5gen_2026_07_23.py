"""Independent review add-ons.

1. Corrected-generator sweep: 150 fresh-seed formulas (seed base 91M, disjoint
   from V3's 73M) checked for exact all-liveness via BDD support. The generator
   is provably all-live by construction (each AND/OR/IMP mixer variant is
   essential in both operands; disjoint leaf sets compose); this sweep is the
   empirical cross-check on seeds V3 never ran.

2. F3 bootstrap: 10,000-resample bootstrap CIs for the median CM/Bitset ratio
   of each committed n=24 300-formula population, from the committed raw CSVs.
   No re-timing; quantifies whether 1.02 vs 1.05/1.08/1.09 is population/session
   spread rather than median sampling noise.
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from deliverables_n22_24.independent_review_f5_support_2026_07_23 import support_bdd
from deliverables_n22_24.v3audit_f5_corrected_all_live_2026_07_23 import corrected_all_live

OUT = REPO / "deliverables_n22_24"


def bootstrap_ci(values, iters=10_000, seed=7):
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    medians = np.median(
        arr[rng.integers(0, len(arr), size=(iters, len(arr)))], axis=1
    )
    return float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))


def main():
    # --- 1. corrected generator fresh-seed sweep
    failures = 0
    total = 0
    for n in (16, 18, 20):
        for trial in range(50):
            expr = corrected_all_live(n, np.random.default_rng(91_000_000 + n * 1000 + trial))
            support, kind = support_bdd(expr, n)
            total += 1
            if len(support) != n or kind != "nonconst":
                failures += 1
                print(f"LIVENESS FAILURE n={n} trial={trial}: support={len(support)} {kind}")
    print(f"corrected generator: {total - failures}/{total} fresh formulas exactly all-live")

    # --- 2. F3 bootstrap from committed raw CSVs
    rows_out = []
    with (OUT / "CM_V3AUDIT_F3_n24_seeds_raw.csv").open(newline="", encoding="utf-8") as fh:
        f3 = list(csv.DictReader(fh))
    for seed_base in sorted({r["seed_base"] for r in f3}):
        ratios = [float(r["ratio"]) for r in f3 if r["seed_base"] == seed_base]
        lo, hi = bootstrap_ci(ratios)
        rows_out.append(
            {
                "population": f"v3_seed_{seed_base}",
                "count": len(ratios),
                "median": round(statistics.median(ratios), 4),
                "ci95_lo": round(lo, 4),
                "ci95_hi": round(hi, 4),
            }
        )
    with (OUT / "CM_FABLE_wrapper_stats300_t16_raw.csv").open(newline="", encoding="utf-8") as fh:
        arch = [r for r in csv.DictReader(fh) if int(r["n"]) == 24]
    ratios = [float(r["ratio"]) for r in arch]
    lo, hi = bootstrap_ci(ratios)
    rows_out.append(
        {
            "population": "archived_t16_n24",
            "count": len(ratios),
            "median": round(statistics.median(ratios), 4),
            "ci95_lo": round(lo, 4),
            "ci95_hi": round(hi, 4),
        }
    )
    with (OUT / "CM_independent_review_f3_bootstrap.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
        writer.writeheader()
        writer.writerows(rows_out)
    for row in rows_out:
        print(row)


if __name__ == "__main__":
    main()
