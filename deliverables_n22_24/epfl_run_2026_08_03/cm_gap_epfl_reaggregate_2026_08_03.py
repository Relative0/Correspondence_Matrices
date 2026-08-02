"""Independent reaggregation of the EPFL campaign from raw rows.

Recomputes the primary/secondary statistics with fresh code (own bootstrap
RNG stream, same pre-registered seed/draws as the protocol requires for the
CI definition) and writes the protocol summary CSV. Compares against the
driver's analysis JSON; any point-estimate deviation > 1e-9 or CI endpoint
deviation > 0.005 is reported as a mismatch.
"""
import json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
OUT = BASE.parent
RESULTS = json.loads((OUT / "cm_gap_epfl_results_2026_08_03.json").read_text(encoding="utf-8"))
ANALYSIS = json.loads((BASE / "cm_gap_epfl_analysis_2026_08_03.json").read_text(encoding="utf-8"))
SUMMARY_CSV = OUT / "CM_gap_epfl_summary_2026_08_03.csv"

rows = [r for r in RESULTS["rows"] if r.get("status") == "ok"]
assert len(rows) == 129


def cluster_boot(sel, key, draws=4000, seed=20260803):
    rng = random.Random(seed)
    by_c = defaultdict(list)
    for r in sel:
        by_c[r["circuit"]].append(math.log(r[key]))
    circuits = sorted(by_c)
    point = math.exp(statistics.mean([v for c in circuits for v in by_c[c]]))
    means = []
    for _ in range(draws):
        sample = []
        for _ in range(len(circuits)):
            sample.extend(by_c[circuits[rng.randrange(len(circuits))]])
        means.append(statistics.mean(sample))
    means.sort()
    return (point,
            math.exp(np.percentile(means, 2.5, method="linear")),
            math.exp(np.percentile(means, 97.5, method="linear")))

checks = {}
for key, name in (("blocked_ratio_cm_cse_flat", "primary_blocked_cm_cse_flat"),
                  ("rr_ratio_cm_cse_flat", "round_robin_cm_cse_flat"),
                  ("blocked_ratio_cm_cse", "secondary_blocked_cm_cse")):
    point, lo, hi = cluster_boot(rows, key)
    ref = ANALYSIS[name]
    checks[name] = {
        "point": point, "ci": [lo, hi],
        "point_dev": abs(point - ref["geomean"]),
        "ci_dev": max(abs(lo - ref["ci95_lo"]), abs(hi - ref["ci95_hi"])),
        "point_ok": abs(point - ref["geomean"]) < 1e-9,
        "ci_ok": max(abs(lo - ref["ci95_lo"]), abs(hi - ref["ci95_hi"])) < 0.005,
    }

be = [r["breakeven_evals_vs_cse_flat"] for r in rows
      if r["breakeven_evals_vs_cse_flat"] is not None]
n_never = sum(1 for r in rows if r["never_breaks_even_vs_cse_flat"])
checks["breakeven"] = {
    "median_finite": statistics.median(be), "n_finite": len(be),
    "n_never": n_never,
    "matches_analysis": (statistics.median(be)
                         == ANALYSIS["breakeven_vs_cse_flat"]["median_finite"]
                         and n_never == ANALYSIS["breakeven_vs_cse_flat"]["n_never"]),
}
prep = math.exp(statistics.mean(
    math.log(r["prep_ratio_cm_vs_cse_flat"]) for r in rows))
checks["prep_multiple"] = {
    "geomean": prep,
    "matches": abs(prep - ANALYSIS["prep_multiple_cm_vs_cse_flat_geomean"]) < 1e-9}

# materiality re-applied independently
p, lo, hi = (checks["primary_blocked_cm_cse_flat"]["point"],
             *checks["primary_blocked_cm_cse_flat"]["ci"])
med_be_all_le_1000 = n_never * 2 <= len(rows) and statistics.median(
    [b if b is not None else float("inf")
     for b in (r["breakeven_evals_vs_cse_flat"] for r in rows)]) <= 1000
checks["materiality_independent"] = {
    "cond1": p <= 0.95, "cond2": hi < 1.0, "cond3": bool(med_be_all_le_1000),
    "optimization_worthy": bool(p <= 0.95 and hi < 1.0 and med_be_all_le_1000),
    "matches_analysis": (ANALYSIS["materiality"]["optimization_worthy"]
                         == bool(p <= 0.95 and hi < 1.0 and med_be_all_le_1000)),
}

# summary CSV (per-circuit + aggregates)
import csv
lines = []
by_c = defaultdict(list)
for r in rows:
    by_c[r["circuit"]].append(r)
for c, sel in sorted(by_c.items()):
    lines.append({
        "group": f"circuit:{c}", "category": sel[0]["category"],
        "n_formulas": len(sel),
        "geomean_cm_cse_flat_blocked": math.exp(statistics.mean(
            math.log(r["blocked_ratio_cm_cse_flat"]) for r in sel)),
        "geomean_cm_cse_blocked": math.exp(statistics.mean(
            math.log(r["blocked_ratio_cm_cse"]) for r in sel)),
        "ci95_lo": "", "ci95_hi": "", "bootstrap": "",
    })
for name, key in (("all:primary_cm_cse_flat_blocked", "primary_blocked_cm_cse_flat"),
                  ("all:cm_cse_flat_round_robin", "round_robin_cm_cse_flat"),
                  ("all:cm_cse_blocked_secondary", "secondary_blocked_cm_cse")):
    lines.append({
        "group": name, "category": "all", "n_formulas": len(rows),
        "geomean_cm_cse_flat_blocked": checks[key]["point"]
            if "flat" in name or "cse" in name else "",
        "geomean_cm_cse_blocked": "",
        "ci95_lo": checks[key]["ci"][0], "ci95_hi": checks[key]["ci"][1],
        "bootstrap": "circuit_clustered_4000",
    })
if SUMMARY_CSV.exists():
    sys.exit(f"refusing to overwrite {SUMMARY_CSV}")
with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(lines[0]))
    w.writeheader(); w.writerows(lines)

out = BASE / "cm_gap_epfl_reaggregation_2026_08_03.json"
if out.exists():
    sys.exit(f"refusing to overwrite {out}")
out.write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
