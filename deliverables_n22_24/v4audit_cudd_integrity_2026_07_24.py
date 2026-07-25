"""Reconstruct committed CUDD summaries, seed parity, and current chart arrays."""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.robdd_dd import select_dd_module

BASE = Path(__file__).resolve().parent
OUT = BASE / "CM_v4audit_cudd_integrity_checks.csv"
RECON = BASE / "CM_v4audit_cudd_reconstructed_summary.csv"


def truth(v):
    return str(v).lower() == "true"


def pct(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=float), q))


def main():
    checks = []
    with (BASE / "CM_FABLE_cudd_wrapper32_raw.csv").open(newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    with (BASE / "CM_FABLE_cudd_wrapper32_summary.csv").open(newline="", encoding="utf-8") as fh:
        committed = {int(r["n"]): r for r in csv.DictReader(fh)}
    reconstructed = []
    parity_failures = 0
    for n in sorted({int(r["n"]) for r in raw}):
        sel = [r for r in raw if int(r["n"]) == n]
        identity_ok = all(
            r["cudd_backend"] == "dd.cudd" and truth(r["cudd_is_cudd"])
            and r["cudd_status"] == "ok" and truth(r["cudd_ok"]) and truth(r["ok"])
            for r in sel
        )
        for r in sel:
            trial = int(r["trial"])
            expr = random_expr(
                n, np.random.default_rng(9_100_000 + 10_000 * n + trial),
                max_depth=4, p_unary=0.25,
            )
            if len(compile_expr_to_cm_ir(expr).vars) != int(r["live_k"]):
                parity_failures += 1
        ratios = [float(r["ratio"]) for r in sel]
        rec = {
            "n": n, "trials": len(sel),
            "all_correct": all(truth(r["ok"]) for r in sel),
            "cudd_all_status_ok": all(r["cudd_status"] == "ok" for r in sel),
            "cudd_all_is_cudd": all(truth(r["cudd_is_cudd"]) for r in sel),
            "cudd_sampled_ok_count": sum(truth(r["cudd_ok"]) for r in sel),
            "autoref_sampled_ok_count": sum(truth(r["autoref_ok"]) for r in sel),
            "live_k_median": statistics.median(float(r["live_k"]) for r in sel),
            "cm_us_median": round(statistics.median(float(r["cm_us"]) for r in sel), 2),
            "bitset_us_median": round(statistics.median(float(r["bitset_us"]) for r in sel), 2),
            "ratio_cm_bitset_median": round(statistics.median(ratios), 3),
            "ratio_p10": round(pct(ratios, 10), 3),
            "ratio_p90": round(pct(ratios, 90), 3),
            "cudd_build_us_median": round(statistics.median(float(r["cudd_build_median_us"]) for r in sel), 2),
            "autoref_build_us_median": round(statistics.median(float(r["autoref_build_median_us"]) for r in sel), 2),
            "ratio_cudd_build_bitset_median": round(statistics.median(
                float(r["cudd_build_median_us"]) / float(r["bitset_us"]) for r in sel), 3),
            "ratio_cudd_build_cm_median": round(statistics.median(
                float(r["cudd_build_median_us"]) / float(r["cm_us"]) for r in sel), 3),
            "cudd_nodes_median": statistics.median(float(r["cudd_nodes"]) for r in sel),
        }
        reconstructed.append(rec)
        prior = committed[n]
        compare_fields = [k for k in rec if k != "n"]
        summary_match = all(str(rec[k]).lower() == str(prior[k]).lower() for k in compare_fields)
        checks.append({"check": f"wrapper_n{n}", "ok": identity_ok and summary_match,
                       "detail": f"identity={identity_ok}; summary={summary_match}; rows={len(sel)}"})
    checks.append({"check": "wrapper_seed_expression_parity", "ok": parity_failures == 0,
                   "detail": f"live_k mismatches={parity_failures}/2700"})

    for name in ("CM_FABLE_cudd_matched_headline_runpod_raw.csv",
                 "CM_FABLE_autoref_matched_headline_runpod_raw.csv"):
        with (BASE / name).open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        is_cudd_file = "cudd_" in name
        ok = len(rows) == 40 and all(
            r["robdd_status"] == "ok"
            and truth(r["robdd_ok"])
            and int(float(r["cm_hybrid_threshold"])) == 7
            and (truth(r["robdd_is_cudd"]) is is_cudd_file)
            and (r["robdd_backend"] == ("dd.cudd" if is_cudd_file else "dd.autoref"))
            for r in rows
        )
        checks.append({"check": name, "ok": ok, "detail": f"rows={len(rows)}; threshold=7"})
        summary_name = name.replace("_raw.csv", "_summary.csv")
        with (BASE / summary_name).open(newline="", encoding="utf-8") as fh:
            summary_rows = {int(r["n_vars"]): r for r in csv.DictReader(fh)}
        summary_ok = True
        for n in sorted({int(r["n_vars"]) for r in rows}):
            sel = [r for r in rows if int(r["n_vars"]) == n]
            dst = summary_rows[n]
            for raw_field, summary_field in (
                ("bitset_time_s", "bitset_time_s_median"),
                ("robdd_build_time_s", "robdd_build_time_s_median"),
                ("robdd_total_build_plus_extract_time_s", "robdd_total_build_plus_extract_time_s_median"),
                ("cm_hybrid_no_reinflate_time_s", "cm_hybrid_no_reinflate_time_s_median"),
            ):
                vals = [float(r[raw_field]) for r in sel if r[raw_field] != ""]
                if vals:
                    summary_ok &= statistics.median(vals) == float(dst[summary_field])
                else:
                    summary_ok &= dst[summary_field] == ""
            summary_ok &= (
                float(dst["ratio_robdd_build_over_bitset"])
                == float(dst["robdd_build_time_s_median"]) / float(dst["bitset_time_s_median"])
            )
        checks.append({"check": summary_name, "ok": summary_ok,
                       "detail": f"groups={len(summary_rows)}; medians/ratio reconstructed"})

    cudd_module, cudd_error = select_dd_module("cudd")
    checks.append({"check": "explicit_cudd_no_fallback", "ok": cudd_module is None,
                   "detail": f"module={cudd_module}; error_present={bool(cudd_error)}"})

    expected_chart = [r["ratio_cudd_build_bitset_median"] for r in reconstructed]
    for page in ("cm_benchmark_charts.html", "cm_head_to_head_explained.html"):
        text = (BASE / page).read_text(encoding="utf-8")
        match = re.search(
            r'"CUDD symbolic build [^"]*":\s*\[([^\]]+)\]', text
        )
        actual = [float(x.strip()) for x in match.group(1).split(",")] if match else []
        chart_ok = actual == [round(float(x), 2) for x in expected_chart]
        prose_ok = "symbolic" in text and bool(re.search(r"not the\s+flat", text))
        checks.append({"check": f"{page}_cudd_array", "ok": chart_ok and prose_ok,
                       "detail": f"parsed={actual}; expected={[round(float(x),2) for x in expected_chart]}"})

    with RECON.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(reconstructed[0])); w.writeheader(); w.writerows(reconstructed)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(checks[0])); w.writeheader(); w.writerows(checks)
    failed = [r for r in checks if not r["ok"]]
    print(json.dumps({"checks": len(checks), "failed": failed}, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
