"""B6 analysis: pod-clustered evaluation of the cross-platform replication.

Reads every pod result under b6_pod_replication_2026_08_03*/pod*/ plus the
local B1 replay archive. Applies the pre-registered acceptance criteria:
identity fields exact on every pod; every pod's stratified-bootstrap CI for
the all-corpus blocked geomean excludes parity AND point within +-0.05 of
the local 0.8876; PASSED/FAILED/INCONCLUSIVE (<3 pods). Pod-to-pod variance
reported, never pooled away.
"""
import json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOCAL = json.loads((BASE / "b1_e3_replay_2026_08_03" /
                    "cm_gap_e3_corrected_results_2026_08_02.json").read_text(encoding="utf-8"))
LOCAL_GEOMEAN = 0.8876
ARCH_ROWS = {r["id"]: r for r in LOCAL["formulas"]}
IDENT = ["structural_hash", "truth_sha256", "unfolded_occurrences", "structural_dag_nodes"]
METRICS = [f"{arm}_{m}" for arm in ("cm", "cse", "cse_flat", "raw")
           for m in ("flat_instructions", "executed_word_ops", "loads",
                     "peak_live_word_buffers")]


def stratified_ci(rows, draws=4000, seed=20260803):
    cells = defaultdict(list)
    for r in rows:
        cells[(r["stratum_live_k"], r["op_family"], r["shape"])].append(
            math.log(r["blocked_ratio_median"]))
    cells = list(cells.values())
    rng = random.Random(seed)
    total = sum(len(c) for c in cells)
    means = []
    for _ in range(draws):
        acc = 0.0
        for cell in cells:
            m = len(cell)
            acc += sum(cell[rng.randrange(m)] for _ in range(m))
        means.append(acc / total)
    means.sort()
    return math.exp(means[int(0.025 * draws)]), math.exp(means[int(0.975 * draws)])


pods = []
for run_dir in sorted(BASE.glob("b6_pod_replication_2026_08_03*")):
    if not run_dir.is_dir():
        continue
    for pod_dir in sorted(run_dir.glob("pod*")):
        res_path = pod_dir / "cm_gap_e3_corrected_results_2026_08_02.json"
        if not res_path.exists():
            continue
        res = json.loads(res_path.read_text(encoding="utf-8"))
        rows = {r["id"]: r for r in res["formulas"]}
        mismatches = []
        for fid, r in rows.items():
            a = ARCH_ROWS[fid]
            for f in IDENT + METRICS:
                if r.get(f) != a.get(f):
                    mismatches.append((fid, f))
        logs = [math.log(r["blocked_ratio_median"]) for r in rows.values()]
        geo = math.exp(statistics.mean(logs))
        lo, hi = stratified_ci(list(rows.values()))
        rr_logs = [math.log(r["rr_ratio"]) for r in rows.values()]
        flat_logs = [math.log(r["cm_kernel_us"] / r["cse_flat_kernel_us"])
                     for r in rows.values() if "cse_flat_kernel_us" in r]
        pods.append({
            "pod_dir": str(pod_dir.relative_to(BASE)),
            "cpu": res["_meta"].get("cpu") or res["_meta"].get("platform"),
            "platform": res["_meta"]["platform"],
            "numpy": res["_meta"]["numpy"],
            "corpus_sha256_ok": res["_meta"]["corpus_sha256"]
                == LOCAL["_meta"]["corpus_sha256"],
            "n_formulas": len(rows),
            "identity_exact": not mismatches,
            "n_identity_mismatches": len(mismatches),
            "blocked_geomean": geo, "ci95": [lo, hi],
            "rr_geomean": math.exp(statistics.mean(rr_logs)),
            "cm_cse_flat_geomean": math.exp(statistics.mean(flat_logs)),
            "ci_excludes_parity": hi < 1.0,
            "within_0p05_of_local": abs(geo - LOCAL_GEOMEAN) <= 0.05,
        })

n_complete = len(pods)
geos = [p["blocked_geomean"] for p in pods]
verdict = "INCONCLUSIVE"
if n_complete >= 3:
    ok = all(p["identity_exact"] and p["ci_excludes_parity"]
             and p["within_0p05_of_local"] and p["corpus_sha256_ok"] for p in pods)
    verdict = "PASSED" if ok else "FAILED"
out = {
    "n_pods_complete": n_complete,
    "local_reference_geomean": LOCAL_GEOMEAN,
    "pods": pods,
    "pod_to_pod": {
        "geomean_min": min(geos) if geos else None,
        "geomean_max": max(geos) if geos else None,
        "geomean_spread": (max(geos) - min(geos)) if geos else None,
        "sigma_across_pods": statistics.stdev(geos) if len(geos) > 1 else None,
    },
    "verdict": f"CROSS-PLATFORM REPLICATION {verdict}",
}
out_path = BASE / "b6_pod_replication_2026_08_03" / "b6_analysis_2026_08_03.json"
if out_path.exists():
    sys.exit(f"refusing to overwrite {out_path}")
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
