"""RunPod campaign worker: extended CM-vs-Bitset wrapper stats at n=24..32, depths 4-8.

Pushed to the pod AS cm_remote_worker.py (the bootstrap's /deploy launches that name).
Serves /health (matching the deploy health check), /progress, and /results; the
campaign runs in a background thread and writes CSVs to /workspace/cm/out/.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import os
import statistics
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter

import numpy as np

from bitset_backend import bitset_to_bool_array, eval_expr_flat_bitset
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

SIZES = (24, 26, 28, 30, 32)
DEPTHS = (4, 5, 6, 8)
TRIALS = 300
ROUNDS = 5
GUARD = 16
THRESHOLD = 16

OUT_DIR = "/workspace/cm/out"
STATE = {
    "done": False, "error": None, "cells_total": len(SIZES) * len(DEPTHS),
    "cells_done": 0, "current": None, "trials_done": 0, "declined_total": 0,
    "correct_total": 0, "started_monotonic": perf_counter(),
}
LOCK = threading.Lock()


def timed(fn, reps):
    t0 = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - t0) / reps


def pct(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=float), q))


def run_campaign():
    os.makedirs(OUT_DIR, exist_ok=True)
    raw, summary = [], []
    try:
        for n in SIZES:
            vars_all = tuple(f"x{i}" for i in range(n))
            for depth in DEPTHS:
                with LOCK:
                    STATE["current"] = f"n={n} depth={depth}"
                cell = []
                declined = 0
                for trial in range(TRIALS):
                    rng = np.random.default_rng(26_000_000 + n * 100_000 + depth * 10_000 + trial)
                    expr = random_expr(n, rng, max_depth=depth, p_unary=0.25)
                    node = compile_expr_to_cm_ir(expr)
                    live_k = len(node.vars)
                    row = {"n": n, "depth": depth, "trial": trial, "live_k": live_k,
                           "declined": False, "ok": None, "cm_us": None,
                           "bitset_us": None, "ratio": None, "output_k": None}
                    try:
                        res = materialize_hybrid_no_reinflate(
                            node, vars_all, fixed={},
                            hybrid_threshold=THRESHOLD,
                            allow_reduced_output=True,
                            max_full_output_vars=GUARD,
                            flat_eval=True,
                        )
                    except ValueError as exc:
                        if str(exc).startswith("refusing to materialize reduced no-reinflate output"):
                            row["declined"] = True
                            declined += 1
                            raw.append(row)
                            with LOCK:
                                STATE["trials_done"] += 1
                                STATE["declined_total"] += 1
                            continue
                        raise
                    output_vars = tuple(res.output_vars)
                    row["output_k"] = len(output_vars)
                    raw_fixed = {v: 0 for v in vars_all if v not in output_vars}

                    def run_cm():
                        return materialize_hybrid_no_reinflate(
                            node, vars_all, fixed={},
                            hybrid_threshold=THRESHOLD,
                            allow_reduced_output=True,
                            max_full_output_vars=GUARD,
                            flat_eval=True,
                        )

                    def run_bs():
                        return eval_expr_flat_bitset(expr, output_vars, fixed=raw_fixed)

                    bits_bs = run_bs()
                    if res.bits is not None:
                        row["ok"] = int(res.bits) == int(bits_bs)
                    else:
                        row["ok"] = bool(np.array_equal(
                            np.asarray(res.tt, dtype=np.uint8).reshape(-1),
                            bitset_to_bool_array(int(bits_bs), len(output_vars))))

                    run_cm(); run_bs()
                    est = timed(run_cm, 3) * 1e6
                    reps = 200 if est < 50 else (40 if est < 500 else 10)
                    t_cm, t_bs = [], []
                    for rnd in range(ROUNDS):
                        if (trial + rnd) % 2:
                            t_cm.append(timed(run_cm, reps) * 1e6)
                            t_bs.append(timed(run_bs, reps) * 1e6)
                        else:
                            t_bs.append(timed(run_bs, reps) * 1e6)
                            t_cm.append(timed(run_cm, reps) * 1e6)
                    row["cm_us"] = statistics.median(t_cm)
                    row["bitset_us"] = statistics.median(t_bs)
                    row["ratio"] = row["cm_us"] / row["bitset_us"]
                    cell.append(row)
                    raw.append(row)
                    with LOCK:
                        STATE["trials_done"] += 1
                        STATE["correct_total"] += int(bool(row["ok"]))

                ratios = [r["ratio"] for r in cell]
                lks_all = [r["live_k"] for r in raw if r["n"] == n and r["depth"] == depth]

                def bucket(lo, hi):
                    rs = [r["ratio"] for r in cell if lo <= r["live_k"] <= hi]
                    return round(statistics.median(rs), 3) if rs else None

                summary.append({
                    "n": n, "depth": depth, "trials": TRIALS,
                    "declined": declined, "declined_rate": round(declined / TRIALS, 4),
                    "accepted": len(cell),
                    "all_correct": all(r["ok"] for r in cell) if cell else None,
                    "live_k_median": statistics.median(lks_all),
                    "live_k_p90": pct(lks_all, 90), "live_k_max": max(lks_all),
                    "cm_us_median": round(statistics.median(r["cm_us"] for r in cell), 2) if cell else None,
                    "bitset_us_median": round(statistics.median(r["bitset_us"] for r in cell), 2) if cell else None,
                    "ratio_median": round(statistics.median(ratios), 3) if ratios else None,
                    "ratio_p10": round(pct(ratios, 10), 3) if ratios else None,
                    "ratio_p90": round(pct(ratios, 90), 3) if ratios else None,
                    "ratio_livek_le4": bucket(0, 4),
                    "ratio_livek_5_7": bucket(5, 7),
                    "ratio_livek_8_11": bucket(8, 11),
                    "ratio_livek_12_16": bucket(12, 16),
                })
                with LOCK:
                    STATE["cells_done"] += 1
                # persist incrementally so partial results survive anything
                for name, rows in (("raw", raw), ("summary", summary)):
                    with open(f"{OUT_DIR}/CM_extended_{name}.csv", "w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=list(rows[0]))
                        w.writeheader(); w.writerows(rows)
        with LOCK:
            STATE["done"] = True
            STATE["current"] = None
    except Exception:
        with LOCK:
            STATE["error"] = traceback.format_exc()


class H(BaseHTTPRequestHandler):
    def _j(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.rstrip("/")
        if path == "/health":
            self._j({"ok": True, "service": "cm-remote-worker", "mode": "campaign"})
        elif path == "/progress":
            with LOCK:
                out = dict(STATE)
            out["elapsed_s"] = round(perf_counter() - out.pop("started_monotonic"), 1)
            self._j(out)
        elif path == "/results":
            out = {}
            for name in ("raw", "summary"):
                p = f"{OUT_DIR}/CM_extended_{name}.csv"
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        out[name] = base64.b64encode(f.read()).decode()
            with LOCK:
                out["done"] = STATE["done"]
                out["error"] = STATE["error"]
            self._j(out)
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    threading.Thread(target=run_campaign, daemon=True).start()
    ThreadingHTTPServer((args.host, args.port), H).serve_forever()


if __name__ == "__main__":
    main()
