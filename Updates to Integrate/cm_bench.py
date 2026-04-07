
#!/usr/bin/env python3
import time, argparse
from typing import Dict, Any, List
import numpy as np

def try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None

dd = try_import("dd")
pysat = try_import("pysat")
pyeda = try_import("pyeda")
pysat_minisat_ok = False
if pysat is not None:
    try:
        from pysat.solvers import Minisat22
        pysat_minisat_ok = True
    except Exception:
        pysat_minisat_ok = False

from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv, random_expr, eval_expr_tt, tseitin_cnf
from cm_build import compile_expr_to_cm
try:
    from cm_build_lazy import compile_expr_to_cm_lazy
    HAS_LAZY=True
except Exception:
    HAS_LAZY=False
from cm_normalize import canonical_layout
from expr_simplify import simplify_via_sympy, bdd_sop

def time_backends_on_expr(n: int, expr, use_sat: bool, use_dd: bool, use_espresso: bool, verbose: bool) -> Dict[str, Any]:
    build_tt = (n <= 16)

    tt = None
    t_cm = None
    if build_tt:
        if verbose: print(f"[n={n}] CM compile (canonical lift + pointwise) ...")
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        t0 = time.perf_counter()
        M_cm = compile_expr_to_cm_lazy(expr, R, C, fixed={}) if (HAS_LAZY and args.cm_lazy) else compile_expr_to_cm(expr, R, C, fixed={})
        t_cm = time.perf_counter() - t0
        tt = M_cm.reshape(-1).view(np.uint8)

    return {
        "cm_time_s": t_cm,
    }

def run_bench(sizes: List[int], trials: int, seed: int, max_depth: int, verbose: bool):
    import pandas as pd
    rng = np.random.default_rng(seed)
    rows = []
    for n in sizes:
        if verbose:
            print(f"\n=== n = {n} ===")
            if n > 16:
                print("[info] n>16: skipping TT-based paths")
        exprs = [random_expr(n, rng, max_depth=max_depth, p_unary=0.25) for _ in range(trials)]
        for t, expr in enumerate(exprs):
            if verbose: print(f"  Trial {t+1}/{trials}")
            res = time_backends_on_expr(n, expr, False, False, False, verbose)
            res["n_vars"] = n; res["trial"] = t
            rows.append(res)
    import pandas as pd
    df = pd.DataFrame(rows)

    def safe_median(s): 
        try: return float(s.dropna().median())
        except Exception: return None

    agg = df.groupby("n_vars").agg(
        cm_time_s_median=("cm_time_s", safe_median),
        trials=("trial","count")
    ).reset_index()

    agg["backend_dd"] = False
    agg["backend_sat"] = False
    agg["backend_espresso"] = False
    return df, agg

def print_summary_table(agg):
    print("\n=== Summary (per n_vars) ===")
    print("Columns: n | CM_med_s | trials")
    for _, row in agg.sort_values("n_vars").iterrows():
        fnum = lambda x: f"{x:>10.6f}" if isinstance(x, float) and not (x!=x) else f"{'nan':>10}"
        print(f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {int(row['trials'] or 0):>6}")

def main():
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=str, default="4,8,16,32")
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--out-prefix", type=str, default="bench_random_ops")
    ap.add_argument("--print-summary", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--cm-lazy", action="store_true")
    global args
    args = ap.parse_args()
    sizes = [int(s) for s in args.sizes.split(",") if s]

    df_raw, df_agg = run_bench(sizes, args.trials, args.seed, args.max_depth, args.verbose)
    raw_path = f"{args.out_prefix}_raw.csv"
    agg_path = f"{args.out_prefix}_summary.csv"
    df_raw.to_csv(raw_path, index=False)
    df_agg.to_csv(agg_path, index=False)
    print("Wrote", raw_path, "and", agg_path)
    if args.print_summary:
        print_summary_table(df_agg)

if __name__ == "__main__":
    main()
