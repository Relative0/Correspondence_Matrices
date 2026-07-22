"""RunPod comprehensive campaign 2: full-variable computation, nothing pruned.

Regime A ("full variables"): balanced all-vars expressions — every ambient variable
live — computed at FULL 2^n output, n=16..32, CM & Bitset, bigint & words engines,
plus the CM wrapper. Sizes whose working set exceeds available RAM are refused by an
explicit pre-check and reported (not silently skipped).

Regime B ("beyond the guard, computed not pruned"): deep formulas whose live_k is
17..26 — the population the reduced-output guard declines — computed exactly over
their true support (2^live_k rows) by both sides, both engines.

Correctness everywhere: CM vs Bitset packed equality (exhaustive over the computed
scope by construction) + a 2,000-row sampled independent scalar oracle per formula.
Serves /health, /progress, /results like the first campaign worker.
"""
from __future__ import annotations

import base64
import csv
import json
import os
import statistics
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter

import numpy as np

from bitset_backend import (
    build_bitset_env,
    clear_bitset_env_cache,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
)
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

OUT_DIR = "/workspace/cm/out2"
STATE = {"done": False, "error": None, "phase": "starting", "rows_done": 0,
         "started_monotonic": perf_counter(), "notes": []}
LOCK = threading.Lock()


def note(msg):
    with LOCK:
        STATE["notes"].append(msg)


def available_ram_bytes():
    """Container cgroup limit (v2 then v1), falling back to host MemAvailable."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(path) as f:
                raw = f.read().strip()
            if raw and raw != "max" and int(raw) < (1 << 46):
                return int(raw)
        except Exception:
            pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except Exception:
        pass
    return None


def full_output_est_bytes(n, n_vars_env):
    width_bytes = (1 << n) // 8
    # peak: bigint env + words env coexist during conversion (2x), plus ~20 scratch
    # buffers and transient copies
    return int(2.2 * n_vars_env * width_bytes) + 20 * width_bytes


def timed(fn, reps):
    t0 = perf_counter()
    for _ in range(reps):
        fn()
    return (perf_counter() - t0) / reps


# ---- balanced all-vars generator (mirrors cmbench.expr.generators semantics) ----
def _balanced_all_vars_once(n, rng):
    """XOR-join keeps every variable live; the mixing wrap uses only non-XOR ops so
    canonical XOR flattening can never cancel a subtree into a constant."""
    mix_ops = (And, Or, Imp, Eqv)
    leaves = [Var(i) for i in range(n)]
    rng.shuffle(leaves)
    nodes = leaves[:]
    while len(nodes) > 1:
        nxt = []
        for i in range(0, len(nodes) - 1, 2):
            a, b = nodes[i], nodes[i + 1]
            if rng.random() < 0.25:
                a = Not(a)
            joined = Xor(a, b)
            if rng.random() < 0.5:
                other = mix_ops[int(rng.integers(0, len(mix_ops)))]
                joined = Xor(joined, other(nodes[i], Not(nodes[i + 1])))
            nxt.append(joined)
        if len(nodes) % 2:
            nxt.append(nodes[-1])
        nodes = nxt
    return nodes[0]


def balanced_all_vars(n, rng):
    """Retry until canonicalization confirms all n variables stay live."""
    for _ in range(40):
        expr = _balanced_all_vars_once(n, rng)
        if len(compile_expr_to_cm_ir(expr).vars) == n:
            return expr
    raise RuntimeError(f"could not build an all-live expression at n={n}")


def scalar_eval(expr, assignment):
    t = type(expr)
    if t is Var:
        return assignment[expr.i]
    if t is Not:
        return 1 - scalar_eval(expr.a, assignment)
    a = scalar_eval(expr.a, assignment)
    b = scalar_eval(expr.b, assignment)
    if t is And:
        return a & b
    if t is Or:
        return a | b
    if t is Xor:
        return a ^ b
    if t is Imp:
        return (1 - a) | b
    return 1 - (a ^ b)  # Eqv


def sampled_oracle_ok(expr, bits, scope_vars, fixed, n_samples, seed):
    """Check n_samples random rows of the packed result against direct recursive
    evaluation of the ORIGINAL expression (independent of every packed evaluator)."""
    rng = np.random.default_rng(seed)
    k = len(scope_vars)
    idx_of = {name: pos for pos, name in enumerate(scope_vars)}
    for _ in range(n_samples):
        row = int(rng.integers(0, 1 << k))
        assignment = {}
        for name, pos in idx_of.items():
            assignment[int(name[1:])] = (row >> (k - 1 - pos)) & 1
        for name, val in fixed.items():
            assignment[int(name[1:])] = int(val)
        if scalar_eval(expr, assignment) != ((bits >> row) & 1):
            return False
    return True


def run_campaign():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows_a, rows_b = [], []
    try:
        ram = available_ram_bytes()
        note(f"MemAvailable={ram}")

        # ---------------- Regime A: full variables, full output ----------------
        with LOCK:
            STATE["phase"] = "A: full-arity full-output"
        TRIALS_A = {28: 2, 30: 2, 32: 1}
        for n in (28, 30, 32):
            vars_all = tuple(f"x{i}" for i in range(n))
            est = full_output_est_bytes(n, n)
            ram_now = available_ram_bytes() or 0
            if est > 0.8 * ram_now:
                rows_a.append({"n": n, "trial": None, "status": "refused_memory",
                               "est_bytes": est, "avail_bytes": ram_now,
                               "cm_bigint_us": None, "bs_bigint_us": None,
                               "cm_words_us": None, "bs_words_us": None,
                               "wrapper_us": None, "all_agree": None, "oracle_ok": None})
                note(f"n={n} full-output refused: est {est/1e9:.1f} GB vs avail {ram_now/1e9:.1f} GB")
                continue
            use_bigint = n <= 28  # bigint full-output beyond 28 is minutes/eval
            use_wrapper = n <= 28  # wrapper currently runs the bigint kernel
            for trial in range(TRIALS_A[n]):
                rng = np.random.default_rng(52_000_000 + n * 1000 + trial)
                expr = balanced_all_vars(n, rng)
                node = compile_expr_to_cm_ir(expr)

                ref = eval_cm_node_words(node, vars_all)
                agree = eval_expr_words_bitset(expr, vars_all) == ref
                if use_bigint:
                    agree = agree and eval_cm_node_flat(node, vars_all) == ref
                    agree = agree and eval_expr_flat_bitset(expr, vars_all) == ref
                if use_wrapper:
                    res = materialize_hybrid_no_reinflate(
                        node, vars_all, fixed={}, hybrid_threshold=n,
                        allow_reduced_output=False, max_full_output_vars=None,
                        flat_eval=True)
                    agree = agree and int(res.bits) == int(ref)
                else:
                    res = None
                oracle = sampled_oracle_ok(expr, int(ref), vars_all, {}, 2000,
                                           seed=8600 + n * 100 + trial)

                reps = 1
                rounds = 3 if n <= 26 else 2
                t = {"cw": [], "bw": [], "cb": [], "bb": [], "wr": []}
                for rnd in range(rounds):
                    order = [("cw", lambda: eval_cm_node_words(node, vars_all)),
                             ("bw", lambda: eval_expr_words_bitset(expr, vars_all))]
                    if use_bigint:
                        order += [("cb", lambda: eval_cm_node_flat(node, vars_all)),
                                  ("bb", lambda: eval_expr_flat_bitset(expr, vars_all))]
                    if use_wrapper:
                        order += [("wr", lambda: materialize_hybrid_no_reinflate(
                            node, vars_all, fixed={}, hybrid_threshold=n,
                            allow_reduced_output=False, max_full_output_vars=None,
                            flat_eval=True))]
                    off = (trial + rnd) % len(order)
                    for name, fn in order[off:] + order[:off]:
                        t[name].append(timed(fn, reps) * 1e6)
                med = {k: (round(statistics.median(v), 1) if v else None) for k, v in t.items()}
                rows_a.append({"n": n, "trial": trial, "status": "ok",
                               "est_bytes": est, "avail_bytes": ram_now,
                               "cm_bigint_us": med["cb"], "bs_bigint_us": med["bb"],
                               "cm_words_us": med["cw"], "bs_words_us": med["bw"],
                               "wrapper_us": med["wr"],
                               "all_agree": agree, "oracle_ok": oracle})
                with LOCK:
                    STATE["rows_done"] += 1
                del expr, node, ref, res
                clear_bitset_env_cache()
                import bitset_backend as bb_mod
                bb_mod.clear_words_env_cache()
                import gc
                gc.collect()
            self_persist(rows_a, rows_b)

        # -------- Regime B: beyond-the-guard formulas, computed over support --------
        with LOCK:
            STATE["phase"] = "B: live_k 17-26 computed (not pruned)"
        TARGET_PER_CELL = 12
        for n in (24, 28, 32):
            vars_all = tuple(f"x{i}" for i in range(n))
            for depth in (6, 8):
                found = 0
                for trial in range(4000):
                    if found >= TARGET_PER_CELL:
                        break
                    rng = np.random.default_rng(63_000_000 + n * 100_000 + depth * 10_000 + trial)
                    expr = random_expr(n, rng, max_depth=depth, p_unary=0.25)
                    node = compile_expr_to_cm_ir(expr)
                    lk = len(node.vars)
                    if not (17 <= lk <= 26):
                        continue
                    found += 1
                    live = tuple(v for v in vars_all if v in set(node.vars))
                    dropped = {v: 0 for v in vars_all if v not in set(node.vars)}
                    ref = eval_cm_node_words(node, live)
                    agree = eval_expr_words_bitset(expr, live, fixed=dropped) == ref
                    use_bigint = lk <= 22
                    if use_bigint:
                        agree = agree and eval_cm_node_flat(node, live) == ref
                        agree = agree and eval_expr_flat_bitset(expr, live, fixed=dropped) == ref
                    oracle = sampled_oracle_ok(expr, int(ref), live, dropped, 2000,
                                               seed=9600 + n * 100 + trial)
                    rounds = 3 if lk <= 22 else 2
                    t = {"cw": [], "bw": [], "cb": [], "bb": []}
                    for rnd in range(rounds):
                        order = [("cw", lambda: eval_cm_node_words(node, live)),
                                 ("bw", lambda: eval_expr_words_bitset(expr, live, fixed=dropped))]
                        if use_bigint:
                            order += [("cb", lambda: eval_cm_node_flat(node, live)),
                                      ("bb", lambda: eval_expr_flat_bitset(expr, live, fixed=dropped))]
                        off = (found + rnd) % len(order)
                        for nm, fn in order[off:] + order[:off]:
                            t[nm].append(timed(fn, 1) * 1e6)
                    med = {k: (round(statistics.median(v), 1) if v else None) for k, v in t.items()}
                    rows_b.append({"n": n, "depth": depth, "trial": trial, "live_k": lk,
                                   "cm_words_us": med["cw"], "bs_words_us": med["bw"],
                                   "cm_bigint_us": med["cb"], "bs_bigint_us": med["bb"],
                                   "ratio_words": round(med["cw"] / med["bw"], 3),
                                   "all_agree": agree, "oracle_ok": oracle})
                    with LOCK:
                        STATE["rows_done"] += 1
                    del expr, node, ref
                    clear_bitset_env_cache()
                    import bitset_backend as bb_mod
                    bb_mod.clear_words_env_cache()
                    import gc
                    gc.collect()
                note(f"B cell n={n} depth={depth}: {found} formulas with live_k 17-26")
                self_persist(rows_a, rows_b)

        with LOCK:
            STATE["done"] = True
            STATE["phase"] = "done"
    except Exception:
        with LOCK:
            STATE["error"] = traceback.format_exc()


def self_persist(rows_a, rows_b):
    for name, rows in (("fullvars", rows_a), ("beyondguard", rows_b)):
        if rows:
            with open(f"{OUT_DIR}/CM_comprehensive_{name}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader(); w.writerows(rows)


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
            self._j({"ok": True, "service": "cm-remote-worker", "mode": "campaign2"})
        elif path == "/progress":
            with LOCK:
                out = dict(STATE)
            out["elapsed_s"] = round(perf_counter() - out.pop("started_monotonic"), 1)
            self._j(out)
        elif path == "/results":
            out = {}
            for name in ("fullvars", "beyondguard"):
                p = f"{OUT_DIR}/CM_comprehensive_{name}.csv"
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        out[name] = base64.b64encode(f.read()).decode()
            with LOCK:
                out["done"] = STATE["done"]
                out["error"] = STATE["error"]
                out["notes"] = STATE["notes"]
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
