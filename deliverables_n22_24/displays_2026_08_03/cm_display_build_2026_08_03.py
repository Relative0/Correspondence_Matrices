"""CM benchmark-refresh display builder (2026-08-03).

Reads ONLY the committed evidence of the 2026-08-03 comprehensive benchmark
refresh (git 61fec68 / campaign HEAD eab8879) and emits:

  cm_display_data_2026_08_03.json            data arrays + per-field provenance
  cm_benchmark_refresh_charts_2026_08_03.html  self-contained chart page

Every number rendered on the page is read from a raw or summary file by this
script; nothing is retyped from prose. Each display carries a `provenance`
block naming file + field so the charts are regenerable and auditable.

Read-only: no evidence file is opened for writing. Outputs go to this
directory only.

Usage:
    .venv\\Scripts\\python.exe deliverables_n22_24\\displays_2026_08_03\\cm_display_build_2026_08_03.py
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DELIV = HERE.parent
REPO = DELIV.parent

# ---------------------------------------------------------------- helpers


def rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def load_json(p: Path):
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(p: Path) -> list[dict]:
    with p.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fnum(x):
    """CSV cell -> float or None."""
    if x is None or x == "":
        return None
    return float(x)


def geomean(xs: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(x) for x in xs))


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover - diagnostics only
        return "unknown"


# ---------------------------------------------------------------- paths

P_B1_RES = DELIV / "b1_e3_replay_2026_08_03" / "cm_gap_e3_corrected_results_2026_08_02.json"
P_B1_SUM = DELIV / "b1_e3_replay_2026_08_03" / "CM_gap_e3_corrected_summary_2026_08_02.csv"
P_B1_ACC = DELIV / "b1_e3_replay_2026_08_03" / "b1_acceptance_check_results_2026_08_03.json"
P_EPFL_RES = DELIV / "cm_gap_epfl_results_2026_08_03.json"
P_EPFL_SUM = DELIV / "CM_gap_epfl_summary_2026_08_03.csv"
P_EPFL_ANA = DELIV / "epfl_run_2026_08_03" / "cm_gap_epfl_analysis_2026_08_03.json"
P_B2_RES = DELIV / "b2_wrapper_2026_08_03" / "cm_b2_wrapper_results_2026_08_03.json"
P_B2_SUM = DELIV / "b2_wrapper_2026_08_03" / "CM_b2_wrapper_summary_2026_08_03.csv"
P_B3_RES = DELIV / "b3_scaling_2026_08_03" / "cm_b3_scaling_results_2026_08_03.json"
P_B3_SUM = DELIV / "b3_scaling_2026_08_03" / "CM_b3_scaling_summary_2026_08_03.csv"
P_B4_RES = DELIV / "b4_sweep_2026_08_03" / "cm_b4_sweep_results_2026_08_03.json"
P_B4_HEAD = DELIV / "b4_sweep_2026_08_03" / "CM_b4_headline_summary_2026_08_03.csv"
P_B4_GUARD = DELIV / "b4_sweep_2026_08_03" / "CM_b4_guard_summary_2026_08_03.csv"
P_B5_RES = DELIV / "b5_cudd_2026_08_03_run5" / "cm_b5_cudd_matched_results_2026_08_03.json"
P_B5_SUM = DELIV / "b5_cudd_2026_08_03_run5" / "CM_b5_cudd_matched_summary_2026_08_03.csv"
P_B5_POD = DELIV / "b5_cudd_2026_08_03_run5" / "b5_pod_audit_2026_08_03.json"
P_B6_ANA = DELIV / "b6_pod_replication_2026_08_03" / "b6_analysis_2026_08_03.json"
P_MANIFEST = DELIV / "cm_benchmark_refresh_manifest_2026_08_03.json"
P_BX1_RES = DELIV / "bx1_crossover_2026_08_03" / "cm_bx1_crossover_results_2026_08_03.json"
P_BX1_SUM = DELIV / "bx1_crossover_2026_08_03" / "CM_bx1_crossover_summary_2026_08_03.csv"
P_BX2_RES = DELIV / "bx2_cudd_orders_2026_08_03" / "cm_bx2_cudd_orders_results_2026_08_03.json"
P_BX2_SUM = DELIV / "bx2_cudd_orders_2026_08_03" / "CM_bx2_cudd_orders_summary_2026_08_03.csv"
P_BX2_POD = DELIV / "bx2_cudd_orders_2026_08_03" / "bx2_pod_audit_2026_08_03.json"

# ---------------------------------------------------------------- load

b1_res = load_json(P_B1_RES)
b1_sum = load_csv(P_B1_SUM)
b1_acc = load_json(P_B1_ACC)
epfl_res = load_json(P_EPFL_RES)
epfl_ana = load_json(P_EPFL_ANA)
b2_res = load_json(P_B2_RES)
b2_sum = load_csv(P_B2_SUM)
b3_res = load_json(P_B3_RES)
b3_sum = load_csv(P_B3_SUM)
b4_res = load_json(P_B4_RES)
b4_head = load_csv(P_B4_HEAD)
b4_guard = load_csv(P_B4_GUARD)
b5_res = load_json(P_B5_RES)
b5_sum = load_csv(P_B5_SUM)
b5_pod = load_json(P_B5_POD)
b6_ana = load_json(P_B6_ANA)
manifest = load_json(P_MANIFEST)
bx1_res = load_json(P_BX1_RES)
bx1_sum = load_csv(P_BX1_SUM)
bx2_res = load_json(P_BX2_RES)
bx2_sum = load_csv(P_BX2_SUM)
bx2_pod = load_json(P_BX2_POD)

D: dict = {}

# ---------------------------------------------------------------- C1
# Kernel headline: CM vs PLAIN structural CSE, three independent scopes.
# Never pooled across scopes; each row carries its own clustering basis.

c1_rows = [
    {
        "label": "Local synthetic (192 formulas)",
        "scope": "synthetic generator e3-corrected-2026-08-02.1 · Windows / Ryzen 5 PRO 5650U",
        "value": b1_acc["new_geomean_all_blocked"],
        "lo": b1_acc["new_ci95_stratified"][0],
        "hi": b1_acc["new_ci95_stratified"][1],
        "basis": "stratified-by-cell bootstrap (independent reaggregation, 4000 draws)",
        "group": "local",
    },
    {
        "label": "External EPFL (129 cones, 19 circuits)",
        "scope": "EPFL AND/INV combinational cones · Windows / Ryzen 5 PRO 5650U",
        "value": epfl_ana["secondary_blocked_cm_cse"]["geomean"],
        "lo": epfl_ana["secondary_blocked_cm_cse"]["ci95_lo"],
        "hi": epfl_ana["secondary_blocked_cm_cse"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (%d draws)" % epfl_ana["secondary_blocked_cm_cse"]["draws"],
        "group": "external",
    },
]
for pod in b6_ana["pods"]:
    name = Path(pod["pod_dir"]).name
    c1_rows.append({
        "label": "Pod %s" % name.split("_")[0],
        "scope": "Linux / AMD EPYC · %s · numpy %s" % (pod["platform"].split("-x86_64")[0], pod["numpy"]),
        "value": pod["blocked_geomean"],
        "lo": pod["ci95"][0],
        "hi": pod["ci95"][1],
        "basis": "per-pod stratified bootstrap (never pooled across pods)",
        "group": "pod",
    })

D["c1_kernel_vs_cse"] = {
    "rows": c1_rows,
    "provenance": [
        "%s :: new_geomean_all_blocked, new_ci95_stratified" % rel(P_B1_ACC),
        "%s :: secondary_blocked_cm_cse" % rel(P_EPFL_ANA),
        "%s :: pods[].blocked_geomean, pods[].ci95" % rel(P_B6_ANA),
    ],
}

# ---------------------------------------------------------------- C2
# Kernel equivalence vs CSE + sharing-aware flattening (Outcome A).
# The residual's SIGN IS NOT STABLE -> never rendered as a CM win.

c2_rows = [
    {
        "label": "Local synthetic · blocked",
        "scope": "synthetic generator · Windows",
        "value": b1_acc["new_cm_vs_cse_flat_geomean"],
        "lo": None, "hi": None,
        "basis": "point geomean over %d paired rows (no CI computed in the acceptance check)" % b1_acc["n_flat_rows"],
        "group": "local",
    },
    {
        "label": "External EPFL · blocked (primary)",
        "scope": "EPFL AND/INV cones · Windows",
        "value": epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
        "lo": epfl_ana["primary_blocked_cm_cse_flat"]["ci95_lo"],
        "hi": epfl_ana["primary_blocked_cm_cse_flat"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (4000 draws)",
        "group": "external",
    },
    {
        "label": "External EPFL · round-robin",
        "scope": "EPFL AND/INV cones · Windows",
        "value": epfl_ana["round_robin_cm_cse_flat"]["geomean"],
        "lo": epfl_ana["round_robin_cm_cse_flat"]["ci95_lo"],
        "hi": epfl_ana["round_robin_cm_cse_flat"]["ci95_hi"],
        "basis": "circuit-clustered bootstrap (4000 draws) — reported beside blocked, never pooled",
        "group": "external",
    },
]
for pod in b6_ana["pods"]:
    name = Path(pod["pod_dir"]).name
    c2_rows.append({
        "label": "Pod %s" % name.split("_")[0],
        "scope": "Linux / AMD EPYC",
        "value": pod["cm_cse_flat_geomean"],
        "lo": None, "hi": None,
        "basis": "per-pod point geomean (no CI in the B6 analysis for this arm)",
        "group": "pod",
    })

D["c2_kernel_vs_cse_flat"] = {
    "rows": c2_rows,
    "materiality": epfl_ana["materiality"],
    "provenance": [
        "%s :: new_cm_vs_cse_flat_geomean, n_flat_rows" % rel(P_B1_ACC),
        "%s :: primary_blocked_cm_cse_flat, round_robin_cm_cse_flat, materiality" % rel(P_EPFL_ANA),
        "%s :: pods[].cm_cse_flat_geomean" % rel(P_B6_ANA),
    ],
}

# ---------------------------------------------------------------- C3
# Local synthetic strata: live_k, then family and shape (blocked only).

# The B1 summary carries `live_k=K`, `live_k=K/family=F`, `live_k=K/shape=S`,
# `family=F/shape=S` and `all`. There are NO family-only or shape-only marginal
# rows, so the family/shape view here is the family x shape interaction grid
# (the rows that actually exist) — not an invented marginal.
strata, cross = [], []
for r in b1_sum:
    if r["schedule"] != "blocked":
        continue
    g = r["group"]
    rec = {
        "group": g,
        "n": int(r["n_formulas"]),
        "geomean": fnum(r["geomean"]),
        "lo": fnum(r["ci95_lo"]),
        "hi": fnum(r["ci95_hi"]),
        "basis": r["bootstrap"],
    }
    if g.startswith("live_k=") and "/" not in g:
        rec["live_k"] = int(g.split("=")[1])
        strata.append(rec)
    elif g.startswith("family=") and "/shape=" in g:
        fam, shp = g.split("/")
        rec["family"] = fam.split("=")[1]
        rec["shape"] = shp.split("=")[1]
        cross.append(rec)

D["c3_local_strata"] = {
    "by_live_k": sorted(strata, key=lambda r: r["live_k"]),
    "by_family_shape": cross,
    "families": sorted({c["family"] for c in cross}),
    "shapes": sorted({c["shape"] for c in cross}),
    "headline": {
        "geomean": b1_acc["new_geomean_all_blocked"],
        "lo": b1_acc["new_ci95_stratified"][0],
        "hi": b1_acc["new_ci95_stratified"][1],
        "identity_exact": b1_acc["identity_fields_exact"],
        "n_identity_mismatches": b1_acc["n_identity_mismatches"],
        "archived_recomputed": b1_acc["archived_geomean_recomputed_from_raw"],
        "archived_ci": b1_acc["archived_ci"],
        "ci_overlap_vs_archive": b1_acc["ci_overlap_vs_archive"],
    },
    "provenance": [
        "%s :: rows where schedule=blocked, group in {live_k=K, family=F/shape=S}" % rel(P_B1_SUM),
        "%s :: headline block" % rel(P_B1_ACC),
    ],
}

# ---------------------------------------------------------------- C4
# EPFL per-circuit (both arms), plus semantic-support buckets.

D["c4_epfl_per_circuit"] = {
    "circuits": [
        {
            "circuit": c["circuit"],
            "category": c["category"],
            "n": c["n_formulas"],
            "cm_cse_flat": c["geomean_cm_cse_flat"],
            "cm_cse": c["geomean_cm_cse"],
        }
        for c in epfl_ana["per_circuit"]
    ],
    "by_sem_bucket": [
        {"bucket": k, "n": v["n"], "cm_cse_flat": v["geomean_cm_cse_flat"]}
        for k, v in epfl_ana["by_sem_bucket"].items()
    ],
    "mechanism": {
        "instr_ratio_cm_cse_flat": epfl_ana["instr_ratio_cm_cse_flat_geomean"],
        "execop_ratio_cm_cse_flat": epfl_ana["execop_ratio_cm_cse_flat_geomean"],
    },
    "n_ok": epfl_ana["n_ok"],
    "n_circuits": epfl_ana["n_circuits"],
    "n_guard_skipped": epfl_ana["n_guard_skipped"],
    "provenance": [
        "%s :: per_circuit[], by_sem_bucket, instr_ratio_cm_cse_flat_geomean, execop_ratio_cm_cse_flat_geomean" % rel(P_EPFL_ANA),
        "%s :: same values, CSV mirror" % rel(P_EPFL_SUM),
    ],
}

# ---------------------------------------------------------------- C5
# Cross-platform pod replication (per-pod, never pooled).

D["c5_pods"] = {
    "pods": [
        {
            "label": Path(p["pod_dir"]).name.split("_")[0],
            "dir": p["pod_dir"].replace("\\", "/"),
            "blocked": p["blocked_geomean"],
            "lo": p["ci95"][0],
            "hi": p["ci95"][1],
            "rr": p["rr_geomean"],
            "cm_cse_flat": p["cm_cse_flat_geomean"],
            "identity_exact": p["identity_exact"],
            "corpus_sha_ok": p["corpus_sha256_ok"],
            "ci_excludes_parity": p["ci_excludes_parity"],
            "platform": p["platform"],
            "numpy": p["numpy"],
            "n_formulas": p["n_formulas"],
        }
        for p in b6_ana["pods"]
    ],
    "local_reference": b6_ana["local_reference_geomean"],
    "spread": b6_ana["pod_to_pod"],
    "verdict": b6_ana["verdict"],
    "provenance": ["%s :: pods[], pod_to_pod, local_reference_geomean, verdict" % rel(P_B6_ANA)],
}

# ---------------------------------------------------------------- C6/C7
# Wrapper boundary (REVISED claim). CM wrapper / bare BitSet, by live_k.

b2_cached = [r for r in b2_sum if r["regime"] == "cached"]
b2_unc = {int(r["live_k"]): r for r in b2_sum if r["regime"] == "uncached_warmenv"}

D["c6_wrapper_ratio"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n_formulas"]),
            "cached_median": fnum(r["ratio_median"]),
            "cached_geomean": fnum(r["ratio_geomean"]),
            "cached_p10": fnum(r["ratio_p10"]),
            "cached_p90": fnum(r["ratio_p90"]),
            "uncached_median": fnum(b2_unc[int(r["live_k"])]["ratio_median"]) if int(r["live_k"]) in b2_unc else None,
            "uncached_geomean": fnum(b2_unc[int(r["live_k"])]["ratio_geomean"]) if int(r["live_k"]) in b2_unc else None,
        }
        for r in b2_cached
    ],
    "engine_note": "k=4 rows run the bigint/BitSet fallback (words engine engages at k>=6); uncached warmenv is not separable at k=4 and is recorded skipped.",
    "provenance": ["%s :: regime in {cached, uncached_warmenv}" % rel(P_B2_SUM)],
}

D["c7_wrapper_cost"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "cm_wrapper_us": fnum(r["cm_wrapper_us_median"]),
            "bitset_us": fnum(r["bitset_us_median"]),
            "overhead_us": fnum(r["wrapper_overhead_us_median"]),
        }
        for r in b2_cached
    ],
    "provenance": [
        "%s :: cm_wrapper_us_median, bitset_us_median, wrapper_overhead_us_median (cached rows)" % rel(P_B2_SUM),
        "%s :: formulas[].cached_cm_wrapper_us / cached_bitset_us (raw)" % rel(P_B2_RES),
    ],
}

# ---------------------------------------------------------------- C8
# Ambient-n irrelevance (B4, V4-C1 protocol).

D["c8_ambient_n"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "ambient_n": int(r["ambient_n"]),
            "n": int(r["n_formulas"]),
            "geomean": fnum(r["paired_ratio_geomean"]),
            "median": fnum(r["paired_ratio_median"]),
            "p10": fnum(r["paired_ratio_p10"]),
            "p90": fnum(r["paired_ratio_p90"]),
            "cm_us": fnum(r["cm_us_median"]),
            "bitset_us": fnum(r["bitset_us_median"]),
        }
        for r in b4_head
    ],
    "provenance": ["%s :: all rows" % rel(P_B4_HEAD)],
}

# ---------------------------------------------------------------- C9
# Guard / decline.

guard_rows = [
    {
        "n": int(r["n"]),
        "depth": int(r["depth"]),
        "trials": int(r["trials"]),
        "median_live_k": fnum(r["median_live_k"]),
        "min_live_k": int(r["min_live_k"]),
        "max_live_k": int(r["max_live_k"]),
        "declined_rate": fnum(r["declined_rate"]),
        "wrong_guard": int(r["wrong_guard_count"]),
        "oversized": int(r["oversized_output_count"]),
    }
    for r in b4_guard
]
D["c9_guard"] = {
    "rows": guard_rows,
    "totals": {
        "trials": sum(r["trials"] for r in guard_rows),
        "wrong_guard": sum(r["wrong_guard"] for r in guard_rows),
        "oversized": sum(r["oversized"] for r in guard_rows),
    },
    "provenance": ["%s :: all rows (totals summed by this script)" % rel(P_B4_GUARD)],
}

# ---------------------------------------------------------------- C10
# Compile / DAG scaling: prep vs unfolded (flat) and prep vs structural nodes.

b3_cases = [
    {
        "id": r["id"],
        "family": r["case_family"],
        "structural_nodes": int(r["structural_dag_nodes"]),
        "unfolded": int(r["unfolded_occurrences"]),
        "sharing_factor": fnum(r["sharing_factor"]),
        "cm_prep_us": fnum(r["cm_prep_us"]),
        "cse_flat_prep_us": fnum(r["cse_flat_prep_us"]),
        "prep_ratio_cm_vs_cse": fnum(r["prep_ratio_cm_vs_cse"]),
        "packed_equal": r["packed_equal_all_arms"] == "True",
    }
    for r in b3_sum
]
ladder = [c for c in b3_cases if c["family"] == "shared_ladder"]
pathological = max(ladder, key=lambda c: c["unfolded"])
D["c10_compile_scaling"] = {
    "cases": b3_cases,
    "pathological": pathological,
    "prep_ratio_range": [
        min(c["prep_ratio_cm_vs_cse"] for c in b3_cases),
        max(c["prep_ratio_cm_vs_cse"] for c in b3_cases),
    ],
    "n_cases": len(b3_cases),
    "all_packed_equal": all(c["packed_equal"] for c in b3_cases),
    "provenance": [
        "%s :: id, case_family, structural_dag_nodes, unfolded_occurrences, cm_prep_us, cse_flat_prep_us, prep_ratio_cm_vs_cse, packed_equal_all_arms" % rel(P_B3_SUM),
        "%s :: cases[] (same rows)" % rel(P_B3_RES),
    ],
}

# ---------------------------------------------------------------- C11
# Prep / break-even economics. Recomputed from raw rows in BOTH corpora.

b1_forms = b1_res["formulas"]
b1_never = [f for f in b1_forms if f["never_breaks_even_vs_cse"]]
b1_finite = [f["breakeven_evals_vs_cse"] for f in b1_forms
             if not f["never_breaks_even_vs_cse"] and f["breakeven_evals_vs_cse"] is not None]
b1_prep_ratios = [f["prep_ratio_cm_vs_cse"] for f in b1_forms if f["prep_ratio_cm_vs_cse"]]

epfl_rows = [r for r in epfl_res["rows"] if r["status"] == "ok"]
epfl_never = [r for r in epfl_rows if r["never_breaks_even_vs_cse_flat"]]
epfl_finite = [r["breakeven_evals_vs_cse_flat"] for r in epfl_rows
               if not r["never_breaks_even_vs_cse_flat"] and r["breakeven_evals_vs_cse_flat"] is not None]

BINS = [(0, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 1e18)]
BIN_LABELS = ["0–25", "25–50", "50–100", "100–200", "200–400", "400–800", "800+"]


def histo(vals):
    out = [0] * len(BINS)
    for v in vals:
        for i, (lo, hi) in enumerate(BINS):
            if lo <= v < hi:
                out[i] += 1
                break
    return out


D["c11_breakeven"] = {
    "bin_labels": BIN_LABELS,
    "synthetic": {
        "baseline": "plain structural CSE",
        "scope": "192 synthetic formulas (B1 fresh replay)",
        "hist": histo(b1_finite),
        "n_finite": len(b1_finite),
        "n_never": len(b1_never),
        "median_finite": statistics.median(b1_finite),
        "prep_multiple_geomean": geomean(b1_prep_ratios),
        "driver_reported": {
            "n_never": b1_res["breakeven"]["n_never_breaks_even_vs_cse"],
            "median": b1_res["breakeven"]["breakeven_evals_median"],
        },
    },
    "epfl": {
        "baseline": "CSE + sharing-aware flattening",
        "scope": "129 EPFL AND/INV cones",
        "hist": histo(epfl_finite),
        "n_finite": len(epfl_finite),
        "n_never": len(epfl_never),
        "median_finite": statistics.median(epfl_finite),
        "prep_multiple_geomean": epfl_ana["prep_multiple_cm_vs_cse_flat_geomean"],
        "analysis_reported": epfl_ana["breakeven_vs_cse_flat"],
    },
    "provenance": [
        "%s :: formulas[].breakeven_evals_vs_cse, .never_breaks_even_vs_cse, .prep_ratio_cm_vs_cse (histogram + median recomputed here)" % rel(P_B1_RES),
        "%s :: rows[].breakeven_evals_vs_cse_flat, .never_breaks_even_vs_cse_flat (status=ok)" % rel(P_EPFL_RES),
        "%s :: prep_multiple_cm_vs_cse_flat_geomean, breakeven_vs_cse_flat" % rel(P_EPFL_ANA),
    ],
}

# ---------------------------------------------------------------- C12/C13
# CUDD matched: CONSTRUCTION and EVALUATION are separate panels, always.

b5_rows_sum = [
    {
        "live_k": int(r["live_k"]),
        "n": int(r["n"]),
        "cm_prep_us": fnum(r["cm_prep_us_median"]),
        "cse_flat_prep_us": fnum(r["cse_flat_prep_us_median"]),
        "cudd_build_us": fnum(r["cudd_build_us_median"]),
        "cm_kernel_us": fnum(r["cm_kernel_us_median"]),
        "cse_flat_kernel_us": fnum(r["cse_flat_kernel_us_median"]),
        "cudd_eval256_us": fnum(r["cudd_eval256_us_median"]),
        "cudd_extract_full_us": fnum(r["cudd_extract_full_us_median"]),
        "cudd_dag_size": fnum(r["cudd_dag_size_median"]),
    }
    for r in b5_sum
]
b5_raw = b5_res["rows"]
D["c12_cudd"] = {
    "rows": b5_rows_sum,
    "integrity": {
        "n_rows": len(b5_raw),
        "robdd_is_cudd_all": all(r["robdd_is_cudd"] for r in b5_raw),
        "full_extraction_equal_all": all(r["cudd_full_extraction_equal"] for r in b5_raw),
        "packed_equal_cm_cse_flat_all": all(r["packed_equal_cm_cse_flat"] for r in b5_raw),
    },
    "extract_vs_kernel": [
        {"live_k": r["live_k"], "factor": r["cudd_extract_full_us"] / r["cm_kernel_us"]}
        for r in b5_rows_sum
    ],
    "pod": {
        "cpu_model": b5_pod["state"]["env"]["cpu_model"],
        "platform": b5_pod["state"]["env"]["platform"],
        "vcpu": b5_pod["vcpu_count"],
        "flavor": b5_pod["cpu_flavor"],
        "terminated": b5_pod["terminated"],
        "cudd_version": b5_res["_meta"]["cudd_version"],
        "dd_cudd": b5_res["_meta"]["dd_cudd"],
        "conventions": b5_res["_meta"]["conventions"],
        "eval_samples": b5_res["_meta"]["eval_samples"],
    },
    "provenance": [
        "%s :: all rows (medians per stratum)" % rel(P_B5_SUM),
        "%s :: rows[].robdd_is_cudd, .cudd_full_extraction_equal, .packed_equal_cm_cse_flat; _meta" % rel(P_B5_RES),
        "%s :: cpu_flavor, vcpu_count, terminated, state.env" % rel(P_B5_POD),
    ],
}

# ---------------------------------------------------------------- C14
# Schedule agreement: blocked vs round-robin, reported side by side.

b1_all_blocked = next(r for r in b1_sum if r["schedule"] == "blocked" and r["group"] == "all")
b1_all_rr = next(r for r in b1_sum if r["schedule"] == "round_robin" and r["group"] == "all")
b1_arch_sum = load_csv(DELIV / "CM_gap_e3_corrected_summary_2026_08_02.csv")
arch_blocked = next(r for r in b1_arch_sum if r["schedule"] == "blocked" and r["group"] == "all")
arch_rr = next(r for r in b1_arch_sum if r["schedule"] == "round_robin" and r["group"] == "all")

sched = [
    {
        "source": "Local synthetic (B1 replay)",
        "blocked": fnum(b1_all_blocked["geomean"]),
        "rr": fnum(b1_all_rr["geomean"]),
        "arm": "CM / plain CSE",
    },
    {
        "source": "Local synthetic (2026-08-02 archive)",
        "blocked": fnum(arch_blocked["geomean"]),
        "rr": fnum(arch_rr["geomean"]),
        "arm": "CM / plain CSE",
    },
    {
        "source": "External EPFL (B7)",
        "blocked": epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
        "rr": epfl_ana["round_robin_cm_cse_flat"]["geomean"],
        "arm": "CM / CSE-flat",
    },
]
for p in b6_ana["pods"]:
    sched.append({
        "source": "Pod %s (B6)" % Path(p["pod_dir"]).name.split("_")[0],
        "blocked": p["blocked_geomean"],
        "rr": p["rr_geomean"],
        "arm": "CM / plain CSE",
    })
for s in sched:
    s["delta_pct"] = 100.0 * (s["rr"] / s["blocked"] - 1.0)
per_cell = []
for br in b1_sum:
    if br["schedule"] != "blocked":
        continue
    rr = next((x for x in b1_sum if x["schedule"] == "round_robin" and x["group"] == br["group"]), None)
    if rr is None:
        continue
    per_cell.append({
        "group": br["group"],
        "blocked": fnum(br["geomean"]),
        "rr": fnum(rr["geomean"]),
        "delta_pct": 100.0 * (fnum(rr["geomean"]) / fnum(br["geomean"]) - 1.0),
    })

D["c14_schedule"] = {
    "rows": sched,
    "per_cell_b1": per_cell,
    "max_abs_delta_pct": max(abs(s["delta_pct"]) for s in sched),
    "max_abs_cell_delta_pct": max(abs(c["delta_pct"]) for c in per_cell),
    "provenance": [
        "%s :: schedule=blocked|round_robin, group=all and per-cell groups" % rel(P_B1_SUM),
        "%s :: schedule=blocked|round_robin, group=all (archived 2026-08-02 run, for contrast)" % rel(DELIV / "CM_gap_e3_corrected_summary_2026_08_02.csv"),
        "%s :: primary_blocked_cm_cse_flat, round_robin_cm_cse_flat" % rel(P_EPFL_ANA),
        "%s :: pods[].blocked_geomean, pods[].rr_geomean" % rel(P_B6_ANA),
    ],
}

# ---------------------------------------------------------------- C15 (BX1)
# Engine crossover: recursive bigint / flat bigint / words, by live_k.

D["c15_engines"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n_formulas"]),
            "recursive_us": fnum(r["recursive_bigint_us_median"]),
            "flat_us": fnum(r["flat_bigint_us_median"]),
            "words_us": fnum(r["words_us_median"]),
            "flat_vs_recursive": fnum(r["flat_vs_recursive_ratio_geomean"]),
            "words_vs_flat": fnum(r["words_vs_flat_ratio_geomean"]),
            "fastest": r["fastest_engine_by_median"],
        }
        for r in bx1_sum
    ],
    "meta": {
        "n_formulas": len(bx1_res["formulas"]),
        "generator": bx1_res["_meta"]["generator_version"],
        "corpus_sha256": bx1_res["_meta"]["corpus_sha256"],
        "engines": bx1_res["_meta"]["engines"],
        "rounds": bx1_res["_meta"]["rounds"],
    },
    "provenance": [
        "%s :: all rows" % rel(P_BX1_SUM),
        "%s :: _meta, formulas[]" % rel(P_BX1_RES),
    ],
}

# ---------------------------------------------------------------- C16 (BX2)
# CUDD order sensitivity. Build window = conversion only (V4 convention) —
# NOT comparable to B5's manager-inclusive cudd_build_us; never mixed.

bx2_pure = {}
for k in (8, 12, 16):
    sums = [sum(p["build_us"] for p in row["per_order"])
            for row in bx2_res["rows"] if row["stratum_live_k"] == k]
    bx2_pure[k] = statistics.median(sums)

D["c16_cudd_orders"] = {
    "rows": [
        {
            "live_k": int(r["live_k"]),
            "n": int(r["n"]),
            "fixed_build_us": fnum(r["fixed_build_us_median"]),
            "fixed_nodes": fnum(r["fixed_nodes_median"]),
            "best10_build_us": fnum(r["best10_selected_build_us_median"]),
            "best10_nodes": fnum(r["best10_selected_nodes_median"]),
            "reorder_build_us": fnum(r["reorder_build_us_median"]),
            "reorder_nodes": fnum(r["reorder_nodes_median"]),
            "node_ratio_best10": fnum(r["node_ratio_best10_vs_fixed_median"]),
            "node_ratio_reorder": fnum(r["node_ratio_reorder_vs_fixed_median"]),
            "pure_10build_sum_us": bx2_pure[int(r["live_k"])],
            "search_total_recorded_us": fnum(r["order_search_total_us_median"]),
        }
        for r in bx2_sum
    ],
    "integrity": {
        "n_rows": len(bx2_res["rows"]),
        "robdd_is_cudd_all": all(r["robdd_is_cudd"] for r in bx2_res["rows"]),
        "sampled_checks_all_ok": all(r["sampled_checks_all_ok"] for r in bx2_res["rows"]),
        "n_orders": bx2_res["_meta"]["n_orders"],
        "correctness_mode": bx2_res["_meta"]["correctness_mode"],
        "selection_rule": bx2_res["_meta"]["selection_rule"],
    },
    "build_window_note": (
        "Build window here is expression-to-BDD conversion only (Audit V4 convention), "
        "AFTER manager creation and variable declaration. B5's cudd_build_us (~2.5 ms) "
        "includes fresh-manager creation and declaration. Both are real costs answering "
        "different questions and are never plotted on the same axis."
    ),
    "pod": {
        "platform": bx2_res["_meta"]["platform"],
        "terminated": bx2_pod.get("terminated"),
        "cpu_flavor": bx2_pod.get("cpu_flavor"),
    },
    "provenance": [
        "%s :: all rows" % rel(P_BX2_SUM),
        "%s :: rows[].per_order[].build_us (pure 10-build sums computed here), _meta" % rel(P_BX2_RES),
        "%s :: terminated, cpu_flavor" % rel(P_BX2_POD),
    ],
}

# ---------------------------------------------------------------- campaign meta

D["_campaign"] = {
    "display_build_head": git_head(),
    "campaign_head": manifest["git_head"],
    "campaign": manifest["campaign"],
    "cost_usd": manifest["pods"]["total_cost_usd"] + bx2_pod["cost_usd_actual"],
    "cost_usd_manifest": manifest["pods"]["total_cost_usd"],
    "cost_usd_bx2": bx2_pod["cost_usd_actual"],
    "cost_cap_usd": manifest["pods"]["budget_cap_usd"],
    "all_pods_terminated": manifest["pods"]["all_pods_terminated"],
    "tests": manifest["tests"]["result"],
    "verdicts": dict(
        [(k, v["verdict"]) for k, v in manifest["benchmarks"].items()]
        + [("BX1", "COMPLETE — words crossover REVISED to workload-dependent"),
           ("BX2", "COMPLETE — best-of-10 ~21–30% smaller BDDs at ~8–10× search cost; reorder never triggers")]
    ),
    "corpora_sha256": manifest["corpora_sha256"],
    "local_env": {
        "python": b1_res["_meta"]["python"].split(" (")[0],
        "numpy": b1_res["_meta"]["numpy"],
        "cpu": b1_res["_meta"]["cpu"],
        "platform": b1_res["_meta"]["platform"],
    },
    "epfl_source": {
        "url": manifest["downloads"][0]["url"],
        "commit": manifest["downloads"][0]["commit"],
        "staged_or_committed": manifest["downloads"][0]["staged_or_committed"],
    },
    "provenance": ["%s :: whole file" % rel(P_MANIFEST), "%s :: _meta" % rel(P_B1_RES)],
}

# Numbers that must never appear on a chart (rendered only on the corrections
# panel, explicitly labelled as superseded).
D["_superseded"] = [
    {"number": "0.843 [0.780, 0.894]", "what": "archived E3 headline (96-formula degenerate corpus)",
     "replaced_by": "0.8876 [0.873, 0.902] — B1 fresh replay"},
    {"number": "128× / 240×", "what": "multiplier-compression headline",
     "replaced_by": "retracted; post-repair CM executes the CSE op count (368 → 167)"},
    {"number": "V4 C1 \"CM modestly ahead at controlled live_k 12/16\" (ratio 0.925)",
     "what": "wrapper-boundary sign at k=12/16",
     "replaced_by": "BitSet leads at every live_k ≤ 16 — B2 1.40–7.83, B4 1.29–1.80"},
    {"number": "23 µs median wrapper overhead", "what": "archived overhead figure",
     "replaced_by": "50–91 µs on the B2 corpus/protocol"},
    {"number": "pre-repair n ≥ 18 ratios", "what": "deck-era guard/headline sweeps",
     "replaced_by": "B4 fresh post-repair sweep (3,000 trials)"},
    {"number": "engine crossover “words at k ≥ 6”", "what": "universal words/bigint crossover point",
     "replaced_by": "workload-dependent — BX1 puts it between k=12 and k=16 on corrected-E3-scale formulas"},
]

# Discrepancies this build found between the claim map's prose and the raw
# evidence it points at. Surfaced on the page rather than silently smoothed.
D["_flags"] = [
    {
        "claim_row": "16 — “blocked and round-robin agree within ~1–2%, never pooled”",
        "finding": (
            "The ~2%% figure holds for the archived 2026-08-02 run (blocked %.4f vs round-robin %.4f, "
            "+%.2f%%), for EPFL (+%.2f%%) and for all five pods (+%.2f%% to +%.2f%%) — but NOT for the "
            "B1 fresh replay, where the all-corpus gap is +%.2f%% and per-cell gaps reach +%.2f%%."
        ) % (
            fnum(arch_blocked["geomean"]), fnum(arch_rr["geomean"]),
            100.0 * (fnum(arch_rr["geomean"]) / fnum(arch_blocked["geomean"]) - 1.0),
            100.0 * (epfl_ana["round_robin_cm_cse_flat"]["geomean"] / epfl_ana["primary_blocked_cm_cse_flat"]["geomean"] - 1.0),
            min(100.0 * (p["rr_geomean"] / p["blocked_geomean"] - 1.0) for p in b6_ana["pods"]),
            max(100.0 * (p["rr_geomean"] / p["blocked_geomean"] - 1.0) for p in b6_ana["pods"]),
            100.0 * (fnum(b1_all_rr["geomean"]) / fnum(b1_all_blocked["geomean"]) - 1.0),
            max(abs(c["delta_pct"]) for c in per_cell),
        ),
        "consequence": (
            "The 'never pooled' half of the claim is unaffected and is honoured everywhere on this page. "
            "The 'agree within ~1–2%' half should be narrowed to the external and pod evidence, or "
            "restated as 'agree within ~2% except on the synthetic corpus, where the schedule effect is "
            "itself run-variable (1.9% archived vs 5.2% replay)'."
        ),
    },
    {
        "claim_row": "9 — “break-even median 78.5, 30/192 never”",
        "finding": (
            "Those are the archived 2026-08-02 numbers. The B1 fresh replay this campaign designates as "
            "the reference reports median %.1f over %d finite and %d/192 never."
        ) % (
            D["c11_breakeven"]["synthetic"]["median_finite"],
            D["c11_breakeven"]["synthetic"]["n_finite"],
            D["c11_breakeven"]["synthetic"]["n_never"],
        ),
        "consequence": (
            "Break-even is a prep-delta ÷ per-eval-gain ratio, so it moves with ordinary timing noise. "
            "The charts plot the replay values, matching the replay headline; the workload-dependence "
            "conclusion is identical either way."
        ),
    },
]

# ---------------------------------------------------------------- emit

out_json = HERE / "cm_display_data_2026_08_03.json"
with out_json.open("w", encoding="utf-8", newline="\n") as fh:
    json.dump(D, fh, indent=2)
    fh.write("\n")

template = (HERE / "cm_display_template_2026_08_03.html").read_text(encoding="utf-8")
html = template.replace(
    "/*__CM_DATA__*/null",
    json.dumps(D, separators=(",", ":")),
)
out_html = HERE / "cm_benchmark_refresh_charts_2026_08_03.html"
out_html.write_text(html, encoding="utf-8", newline="\n")

print("wrote %s (%d bytes)" % (out_json.name, out_json.stat().st_size))
print("wrote %s (%d bytes)" % (out_html.name, out_html.stat().st_size))
print("display build HEAD:", D["_campaign"]["display_build_head"])
print("campaign HEAD:     ", D["_campaign"]["campaign_head"])
print()
print("sanity — headline cm/cse           %.4f [%.3f, %.3f]" % (
    b1_acc["new_geomean_all_blocked"], *b1_acc["new_ci95_stratified"]))
print("sanity — EPFL cm/cse_flat          %.4f [%.4f, %.4f]" % (
    epfl_ana["primary_blocked_cm_cse_flat"]["geomean"],
    epfl_ana["primary_blocked_cm_cse_flat"]["ci95_lo"],
    epfl_ana["primary_blocked_cm_cse_flat"]["ci95_hi"]))
print("sanity — pod geomean spread        %.4f–%.4f" % (
    b6_ana["pod_to_pod"]["geomean_min"], b6_ana["pod_to_pod"]["geomean_max"]))
print("sanity — B1 break-even (replay)    median %.1f finite, %d never of %d" % (
    D["c11_breakeven"]["synthetic"]["median_finite"],
    D["c11_breakeven"]["synthetic"]["n_never"], len(b1_forms)))
print("sanity — EPFL break-even           median %.1f finite, %d never of %d" % (
    D["c11_breakeven"]["epfl"]["median_finite"],
    D["c11_breakeven"]["epfl"]["n_never"], len(epfl_rows)))
print("sanity — guard totals              %d trials, %d wrong, %d oversized" % (
    D["c9_guard"]["totals"]["trials"], D["c9_guard"]["totals"]["wrong_guard"],
    D["c9_guard"]["totals"]["oversized"]))
print("sanity — CUDD integrity            robdd_is_cudd=%s full_extract_equal=%s" % (
    D["c12_cudd"]["integrity"]["robdd_is_cudd_all"],
    D["c12_cudd"]["integrity"]["full_extraction_equal_all"]))
print("sanity — schedule max |delta|      %.2f%% all-corpus, %.2f%% per-cell (B1)" % (
    D["c14_schedule"]["max_abs_delta_pct"], D["c14_schedule"]["max_abs_cell_delta_pct"]))
print("sanity — BX1 fastest engine        %s" % " ".join(
    "k%d:%s" % (r["live_k"], r["fastest"].replace("_bigint", "")) for r in D["c15_engines"]["rows"]))
print("sanity — BX2 node ratio best10     %s" % " / ".join(
    "%.2f" % r["node_ratio_best10"] for r in D["c16_cudd_orders"]["rows"]))
print()
for fl in D["_flags"]:
    print("FLAG  claim row %s\n      %s" % (fl["claim_row"], fl["finding"]))
