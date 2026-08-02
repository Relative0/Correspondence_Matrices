"""B1 acceptance check: fresh corrected-E3 replay vs archived acceptance results.

Independent reaggregation from raw rows (no reuse of the driver's summarize()):
- identity fields exact vs archive (structural_hash, truth_sha256, per-arm
  instruction/op/load/buffer counts) per formula;
- all-corpus blocked geomean recomputed from raw blocked_ratio_median rows;
- CI-overlap test vs archived 0.888 [0.876, 0.899] (stratified bootstrap here);
- cm/cse_flat kernel geomean recomputed from raw kernel timings.
"""
import json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
NEW = json.loads((BASE / "cm_gap_e3_corrected_results_2026_08_02.json").read_text(encoding="utf-8"))
ARCH = json.loads((BASE.parent / "cm_gap_e3_corrected_results_2026_08_02.json").read_text(encoding="utf-8"))

new_rows = {r["id"]: r for r in NEW["formulas"]}
arch_rows = {r["id"]: r for r in ARCH["formulas"]}
assert set(new_rows) == set(arch_rows), "formula id sets differ"

IDENT = ["structural_hash", "truth_sha256", "unfolded_occurrences", "structural_dag_nodes"]
ARMS = ["cm", "cse", "cse_flat", "raw"]
METRICS = ["flat_instructions", "executed_word_ops", "loads", "peak_live_word_buffers"]
ident_mismatches = []
for fid, r in new_rows.items():
    a = arch_rows[fid]
    for f in IDENT + [f"{arm}_{m}" for arm in ARMS for m in METRICS]:
        if r.get(f) != a.get(f):
            ident_mismatches.append((fid, f, r.get(f), a.get(f)))

logs = [math.log(r["blocked_ratio_median"]) for r in new_rows.values()]
geo_all = math.exp(statistics.mean(logs))

# stratified bootstrap over (stratum, family, shape) cells, own RNG
cells = defaultdict(list)
for r in new_rows.values():
    cells[(r["stratum_live_k"], r["op_family"], r["shape"])].append(math.log(r["blocked_ratio_median"]))
cells = list(cells.values())
rng = random.Random(20260803)
total = sum(len(c) for c in cells)
means = []
for _ in range(4000):
    acc = 0.0
    for cell in cells:
        m = len(cell)
        acc += sum(cell[rng.randrange(m)] for _ in range(m))
    means.append(acc / total)
means.sort()
ci = (math.exp(means[int(0.025 * 4000)]), math.exp(means[int(0.975 * 4000)]))

# cm/cse_flat kernel geomean from raw timings
flat_logs = [math.log(r["cm_kernel_us"] / r["cse_flat_kernel_us"])
             for r in new_rows.values() if "cse_flat_kernel_us" in r]
geo_flat = math.exp(statistics.mean(flat_logs))

# archived reference (recomputed from archived raw rows, not its summary)
arch_logs = [math.log(r["blocked_ratio_median"]) for r in arch_rows.values()]
arch_geo = math.exp(statistics.mean(arch_logs))
ARCH_CI = (0.876, 0.899)

per_stratum = {}
for k in (8, 12, 16):
    sel = [math.log(r["blocked_ratio_median"]) for r in new_rows.values() if r["stratum_live_k"] == k]
    per_stratum[k] = math.exp(statistics.mean(sel))

overlap = ci[0] <= ARCH_CI[1] and ARCH_CI[0] <= ci[1]
verdict = {
    "identity_fields_exact": not ident_mismatches,
    "n_identity_mismatches": len(ident_mismatches),
    "identity_mismatches_first10": ident_mismatches[:10],
    "new_geomean_all_blocked": geo_all,
    "new_ci95_stratified": ci,
    "per_stratum_geomean": per_stratum,
    "archived_geomean_recomputed_from_raw": arch_geo,
    "archived_ci": ARCH_CI,
    "ci_overlap_vs_archive": overlap,
    "new_cm_vs_cse_flat_geomean": geo_flat,
    "n_flat_rows": len(flat_logs),
    "acceptance": bool(not ident_mismatches and overlap and abs(geo_flat - 0.985) < 0.03),
}
out = BASE / "b1_acceptance_check_results_2026_08_03.json"
if out.exists():
    sys.exit("refusing to overwrite " + str(out))
out.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
print(json.dumps(verdict, indent=2))
