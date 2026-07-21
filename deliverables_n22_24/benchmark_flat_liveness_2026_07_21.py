"""Paired flat-vs-flat benchmark for C1a last-use slot freeing.

Headline timings are instrumentation-off medians.  The same expressions, input masks,
operation semantics, and liveness policy are used for CM-flat and raw-AST-flat paths.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bitset_backend import (  # noqa: E402
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    get_expr_flat_program,
    get_flat_program,
)
from cm_exprlib import eval_expr_tt, random_expr  # noqa: E402
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate  # noqa: E402
from cmbench.expr.generators import random_expr_balanced_all_vars  # noqa: E402


METHODS = (
    "raw_recursive",
    "raw_flat_retained",
    "raw_flat_liveness",
    "cm_recursive",
    "cm_flat_retained",
    "cm_flat_liveness",
    "cm_wrapper_generic",
    "cm_wrapper_liveness",
)


def repeats_for_n(n: int) -> int:
    if n <= 4:
        return 500
    if n <= 8:
        return 300
    if n <= 12:
        return 150
    if n <= 16:
        return 20
    if n <= 18:
        return 8
    if n <= 20:
        return 3
    return 1


def timed(fn, repeats: int) -> float:
    start = perf_counter()
    for _ in range(repeats):
        fn()
    return (perf_counter() - start) / repeats


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_cases(regime: str, n: int, trials: int):
    for trial in range(trials):
        rng = np.random.default_rng(20260721 + n * 100 + trial)
        if regime == "cached_depth4":
            expr = random_expr(n, rng, max_depth=4, p_unary=0.25)
        else:
            expr = random_expr_balanced_all_vars(n, rng, max_depth=8)
        yield trial, expr


def run(regimes: list[str], sizes: list[int], trials: int, sessions: int):
    raw_rows: list[dict[str, object]] = []
    case_cache = []
    for regime in regimes:
        regime_sizes = [n for n in sizes if regime == "cached_depth4" or n >= 16]
        for n in regime_sizes:
            vars_all = tuple(f"x{i}" for i in range(n))
            env = build_bitset_env(vars_all)
            for trial, expr in build_cases(regime, n, trials):
                node = compile_expr_to_cm_ir(expr)
                expected = eval_expr_bitset(expr, env)
                oracle = eval_expr_tt(expr, n).astype(np.uint8, copy=False).reshape(-1)
                if not np.array_equal(bitset_to_bool_array(expected, n), oracle):
                    raise AssertionError((regime, n, trial, "oracle"))
                del oracle
                gc.collect()

                funcs = {
                    "raw_recursive": lambda e=expr, en=env: eval_expr_bitset(e, en),
                    "raw_flat_retained": lambda e=expr, vs=vars_all: eval_expr_flat_bitset(
                        e, vs, free_dead_slots=False
                    ),
                    "raw_flat_liveness": lambda e=expr, vs=vars_all: eval_expr_flat_bitset(
                        e, vs, free_dead_slots=True
                    ),
                    "cm_recursive": lambda nd=node, vs=vars_all: eval_cm_node_bitset(nd, vs),
                    "cm_flat_retained": lambda nd=node, vs=vars_all: eval_cm_node_flat(
                        nd, vs, free_dead_slots=False
                    ),
                    "cm_flat_liveness": lambda nd=node, vs=vars_all: eval_cm_node_flat(
                        nd, vs, free_dead_slots=True
                    ),
                    "cm_wrapper_liveness": lambda nd=node, vs=vars_all, nn=n: materialize_hybrid_no_reinflate(
                        nd,
                        vs,
                        fixed={},
                        diagnostics=None,
                        hybrid_threshold=nn,
                        max_full_output_vars=None,
                        flat_eval=True,
                    ).bits,
                    "cm_wrapper_generic": lambda nd=node, vs=vars_all, nn=n: materialize_hybrid_no_reinflate(
                        nd,
                        vs,
                        fixed={},
                        diagnostics=None,
                        hybrid_threshold=nn,
                        max_full_output_vars=None,
                        flat_eval=True,
                        flat_fast_path=False,
                    ).bits,
                }
                for method, fn in funcs.items():
                    if fn() != expected:
                        raise AssertionError((regime, n, trial, method))
                case_cache.append((regime, n, trial, expr, node, funcs))

    for session in range(sessions):
        for case_index, (regime, n, trial, expr, node, funcs) in enumerate(case_cache):
            repeats = repeats_for_n(n)
            offset = (session + trial + n) % len(METHODS)
            order = METHODS[offset:] + METHODS[:offset]
            for method in order:
                seconds = timed(funcs[method], repeats)
                raw_rows.append(
                    {
                        "regime": regime,
                        "n": n,
                        "session": session,
                        "trial": trial,
                        "method": method,
                        "seconds": seconds,
                        "microseconds": seconds * 1e6,
                        "repeats": repeats,
                        "raw_slots": get_expr_flat_program(expr).n_slots,
                        "cm_slots": get_flat_program(node).n_slots,
                        "live_k": len(node.vars),
                    }
                )
            gc.collect()
            print(f"completed {regime} n={n} session={session} trial={trial}", flush=True)

    summary: list[dict[str, object]] = []
    keys = sorted({(str(r["regime"]), int(r["n"])) for r in raw_rows})
    for regime, n in keys:
        selected = [r for r in raw_rows if r["regime"] == regime and r["n"] == n]
        method_medians = {}
        for method in METHODS:
            values = [float(r["microseconds"]) for r in selected if r["method"] == method]
            method_medians[method] = statistics.median(values)
        session_ratios = []
        for session in range(sessions):
            session_rows = [r for r in selected if r["session"] == session]
            cm = statistics.median(
                float(r["microseconds"]) for r in session_rows if r["method"] == "cm_flat_liveness"
            )
            raw = statistics.median(
                float(r["microseconds"]) for r in session_rows if r["method"] == "raw_flat_liveness"
            )
            session_ratios.append(cm / raw)
        ratio_mean = statistics.mean(session_ratios)
        ratio_cv = statistics.stdev(session_ratios) / ratio_mean if len(session_ratios) > 1 else 0.0
        summary.append(
            {
                "regime": regime,
                "n": n,
                "samples_per_method": len(selected) // len(METHODS),
                **{f"{method}_us_median": method_medians[method] for method in METHODS},
                "raw_flat_liveness_speedup": method_medians["raw_flat_retained"]
                / method_medians["raw_flat_liveness"],
                "cm_flat_liveness_speedup": method_medians["cm_flat_retained"]
                / method_medians["cm_flat_liveness"],
                "cm_live_over_raw_live": method_medians["cm_flat_liveness"]
                / method_medians["raw_flat_liveness"],
                "cm_wrapper_over_raw_live": method_medians["cm_wrapper_liveness"]
                / method_medians["raw_flat_liveness"],
                "session_ratio_min": min(session_ratios),
                "session_ratio_max": max(session_ratios),
                "session_ratio_cv": ratio_cv,
                "session_ratio_p10": percentile(session_ratios, 10),
                "session_ratio_p90": percentile(session_ratios, 90),
            }
        )
    return raw_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regimes", default="cached_depth4,fulloutput_fullarity")
    parser.add_argument("--sizes", default="4,8,12,16,18,20,22,24")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--sessions", type=int, default=5)
    parser.add_argument("--tag", default="py313")
    args = parser.parse_args()
    if args.trials < 5 or args.sessions < 5:
        raise SystemExit("publication runs require --trials >= 5 and --sessions >= 5")
    regimes = [x for x in args.regimes.split(",") if x]
    sizes = [int(x) for x in args.sizes.split(",")]
    raw_rows, summary = run(regimes, sizes, args.trials, args.sessions)
    write_csv(HERE / f"CM_flat_liveness_{args.tag}_raw.csv", raw_rows)
    write_csv(HERE / f"CM_flat_liveness_{args.tag}_summary.csv", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
