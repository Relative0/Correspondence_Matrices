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
pyeda = try_import("pyeda")

from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv, random_expr, eval_expr_tt, tseitin_cnf
from cm_build import compile_expr_to_cm
try:
    from cm_build_lazy import compile_expr_to_cm_lazy
    HAS_LAZY=True
except Exception:
    HAS_LAZY=False
from cm_normalize import canonical_layout
from expr_simplify import simplify_via_sympy, bdd_sop

_GRID_CACHE: Dict[int, np.ndarray] = {}

def get_eval_grid(n: int) -> np.ndarray:
    G = _GRID_CACHE.get(n)
    if G is not None:
        return G
    L = 1 << n
    A = np.zeros((L, n), dtype=np.uint8)
    for v in range(n):
        block = 1 << (n - 1 - v)
        pattern = np.concatenate([np.zeros(block, dtype=np.uint8), np.ones(block, dtype=np.uint8)])
        reps = L // (2*block)
        A[:, v] = np.tile(pattern, reps)
    _GRID_CACHE[n] = A
    return A

def time_backends_on_expr(n: int, expr, use_dd: bool, use_espresso: bool, verbose: bool) -> Dict[str, Any]:
    build_tt = (n <= 16)
    run_sympy = (n <= 16)
    run_espresso = use_espresso and (n <= 16)

    tt = None
    t_cm = None
    cm_ok = None
    if build_tt:
        if verbose: print(f"[n={n}] CM compile ...")
        R, C = canonical_layout([f"x{i}" for i in range(n)])
        t0 = time.perf_counter()
        M_cm = compile_expr_to_cm_lazy(expr, R, C, fixed={}) if (HAS_LAZY and args.cm_lazy) else compile_expr_to_cm(expr, R, C, fixed={})
        t_cm = time.perf_counter() - t0
        tt = M_cm.reshape(-1).view(np.uint8)
        try:
            tt_ref = eval_expr_tt(expr, n)
            tt_ref = tt_ref.astype(np.uint8).reshape(-1)
            cm_ok = bool(np.array_equal(tt, tt_ref))
        except Exception:
            cm_ok = False

    bdd_time = None
    bdd_nodes = None
    robdd_ok = None
    if build_tt and (not args.no_robdd):
        if verbose: print(f"[n={n}] ROBDD (Python) from TT ...")
        class BDDTT:
            def __init__(self, n_vars):
                self.n=n_vars; self.t=1; self.f=0; self.unique={}; self.nodes=[(-1,-1,-1),(-1,-1,-1)]; self.cache={}
            def mk(self, var, low, high):
                if low==high: return low
                key=(var,low,high); u=self.unique.get(key)
                if u is None: u=len(self.nodes); self.nodes.append((var,low,high)); self.unique[key]=u
                return u
            def build(self, tt):
                assert tt.size==(1<<self.n)
                def rec(v,s,l):
                    seg=tt[s:s+l]; key=(v,s,hash(seg.tobytes()))
                    if key in self.cache: return self.cache[key]
                    if l==1:
                        u=self.t if seg[0]==1 else self.f; self.cache[key]=u; return u
                    half=l//2; lo=rec(v+1,s,half); hi=rec(v+1,s+half,half); u=self.mk(v,lo,hi); self.cache[key]=u; return u
                return rec(0,0,tt.size)
            def size(self, root):
                seen=set()
                def dfs(u):
                    if u in (self.f,self.t) or u in seen: return
                    seen.add(u); v,lo,hi=self.nodes[u]; dfs(lo); dfs(hi)
                dfs(root); return len(seen)+2
        bdd_mgr = BDDTT(n)
        t1 = time.perf_counter(); root = bdd_mgr.build(tt); bdd_time = time.perf_counter() - t1
        bdd_nodes = bdd_mgr.size(root)
        robdd_ok = True  # built directly from CM TT

    dd_time = None
    dd_nodes = None
    if use_dd and (not args.no_dd):
        try:
            if verbose: print(f"[n={n}] dd.autoref from AST ...")
            from dd import autoref as _dd
            mgr2 = _dd.BDD(); names=[f"x{i}" for i in range(n)]; mgr2.declare(*names)
            def rec(z):
                if isinstance(z, Var): return mgr2.var(names[z.i])
                if isinstance(z, Not): return ~rec(z.a)
                if isinstance(z, And): return rec(z.a) & rec(z.b)
                if isinstance(z, Or):  return rec(z.a) | rec(z.b)
                if isinstance(z, Xor): return rec(z.a) ^ rec(z.b)
                if isinstance(z, Imp): return (~rec(z.a)) | rec(z.b)
                if isinstance(z, Eqv): return ~(rec(z.a) ^ rec(z.b))
                raise TypeError(z)
            t2 = time.perf_counter(); root2 = rec(expr); dd_time = time.perf_counter() - t2
            dd_nodes = mgr2.size
        except Exception:
            dd_time=None; dd_nodes=None

    sympy_time = None; sympy_ok = None
    bdd_sop_time = None; bdd_sop_ok = None
    espresso_time = None; espresso_ok = None

    if build_tt:
        try:
            import sympy as sp
            if run_sympy and (not args.no_sympy):
                if verbose: print(f"[n={n}] Sympy simplify_logic (DNF) ...")
                t4 = time.perf_counter()
                simp = simplify_via_sympy(expr, n, form="dnf")
                sympy_time = time.perf_counter() - t4
                xs = [sp.symbols(f"x{i}") for i in range(n)]
                f = sp.lambdify(xs, simp, "numpy")
                A = get_eval_grid(n)
                tt_sympy = np.array(f(*[A[:,i] for i in range(n)])).astype(np.uint8).reshape(-1)
                sympy_ok = bool(np.array_equal(tt, tt_sympy))
        except Exception:
            sympy_time = None; sympy_ok = False

        try:
            if run_espresso and (not args.no_espresso) and (pyeda is not None):
                if verbose: print(f"[n={n}] Espresso (pyeda) simplify ...")
                from pyeda.inter import ttvars, truthtable, espresso_exprs
                import sympy as sp
                t6 = time.perf_counter()
                xs = ttvars('x', n)
                ones_idx = np.flatnonzero(tt)  # speed
                T = truthtable(xs, ones_idx.tolist())
                f_simplified, = espresso_exprs(T.to_expr())
                espresso_time = time.perf_counter() - t6
                esp_expr = sp.sympify(str(f_simplified), evaluate=False)
                f3 = sp.lambdify([sp.symbols(f"x{i}") for i in range(n)], esp_expr, "numpy")
                A = get_eval_grid(n)
                tt_esp = np.array(f3(*[A[:,i] for i in range(n)])).astype(np.uint8).reshape(-1)
                espresso_ok = bool(np.array_equal(tt, tt_esp))
        except Exception:
            espresso_time = None; espresso_ok = False

        try:
            if (not args.no_bdd_sop) and (n <= 8):
                if verbose: print(f"[n={n}] BDD→SOP extraction ...")
                import sympy as sp
                t5 = time.perf_counter()
                sop_str = bdd_sop(expr, n)
                bdd_sop_time = time.perf_counter() - t5
                xs = [sp.symbols(f"x{i}") for i in range(n)]
                sop_expr = sp.sympify(sop_str, evaluate=False)
                f2 = sp.lambdify(xs, sop_expr, "numpy")
                A = get_eval_grid(n)
                tt_sop = np.array(f2(*[A[:,i] for i in range(n)])).astype(np.uint8).reshape(-1)
                bdd_sop_ok = bool(np.array_equal(tt, tt_sop))
        except Exception:
            bdd_sop_time = None; bdd_sop_ok = False

    return {
        "cm_time_s": t_cm,
        "cm_ok": cm_ok,
        "bdd_time_s": bdd_time,
        "bdd_nodes": bdd_nodes,
        "dd_time_s": dd_time,
        "dd_nodes": dd_nodes,
        "sympy_time_s": sympy_time,
        "sympy_ok": sympy_ok,
        "bdd_sop_time_s": bdd_sop_time,
        "bdd_sop_ok": bdd_sop_ok,
        "espresso_time_s": espresso_time,
        "espresso_ok": espresso_ok,
        "robdd_ok": robdd_ok,
    }

def run_bench(sizes: List[int], trials: int, seed: int, max_depth: int, verbose: bool):
    import pandas as pd
    rng = np.random.default_rng(seed)
    use_dd = (dd is not None and hasattr(dd, "autoref"))
    use_espresso = (pyeda is not None)
    rows = []
    for n in sizes:
        if verbose:
            print(f"\n=== n = {n} ===")
            if n > 16:
                print("[info] n>16: skipping Sympy/Espresso/TT")
        exprs = [random_expr(n, rng, max_depth=max_depth, p_unary=0.25) for _ in range(trials)]
        for t, expr in enumerate(exprs):
            if verbose: print(f"  Trial {t+1}/{trials}")
            res = time_backends_on_expr(n, expr, use_dd=use_dd, use_espresso=use_espresso, verbose=verbose)
            res["n_vars"] = n; res["trial"] = t
            rows.append(res)
    import pandas as pd
    df = pd.DataFrame(rows)

    def safe_median(s): 
        try: return float(s.dropna().median())
        except Exception: return None
    def safe_all(s):
        try:
            x = s.dropna().tolist()
            return all(x) if x else None
        except Exception: return None
    def count_true(s):
        try:
            x = s.dropna().tolist()
            return sum(1 for v in x if v is True)
        except Exception:
            return 0

    agg = df.groupby("n_vars").agg(
        cm_time_s_median=("cm_time_s", safe_median),
        bdd_time_s_median=("bdd_time_s", safe_median),
        dd_time_s_median=("dd_time_s", safe_median),
        sympy_time_s_median=("sympy_time_s", safe_median),
        bdd_nodes_median=("bdd_nodes", safe_median),
        dd_nodes_median=("dd_nodes", safe_median),
        espresso_time_s_median=("espresso_time_s", safe_median),
        cm_ok_all=("cm_ok", safe_all),
        sympy_ok_all=("sympy_ok", safe_all),
        robdd_ok_all=("robdd_ok", safe_all),
        sympy_ok_count=("sympy_ok", count_true),
        bdd_sop_time_s_median=("bdd_sop_time_s", safe_median),
        bdd_sop_ok_all=("bdd_sop_ok", safe_all),
        espresso_ok_all=("espresso_ok", safe_all),
        trials=("trial","count")
    ).reset_index()

    agg["backend_dd"] = use_dd
    agg["backend_espresso"] = use_espresso
    return df, agg

def print_summary_table(agg):
    print("\n=== Summary (per n_vars) ===")
    print("Columns: n | CM_med_s | ROBDD_med_s | dd_med_s | Sympy_simpl_med_s | BDD_SOP_med_s | Espresso_med_s | ROBDD_nodes_med | dd_nodes_med | CM_OK | Sympy_OK | Sympy_OK_count/trials | ROBDD_OK | BDD_SOP_OK | Espresso_OK | trials | ROBDD? | dd? | ESP?")
    for _, row in agg.sort_values("n_vars").iterrows():
        fnum = lambda x: f"{x:>10.6f}" if isinstance(x, float) and not (x!=x) else f"{'nan':>10}"
        fint = lambda x: 0 if (x is None or (isinstance(x, float) and (x!=x))) else int(x)
        fbool = lambda x: 'OK' if x is True else ('--' if x is None else 'NO')
        trials = int(row['trials'] or 0)
        okc = int(row.get('sympy_ok_count') or 0)
        print(f"{int(row['n_vars']):>2} | {fnum(row['cm_time_s_median'])} | {fnum(row['bdd_time_s_median'])} | {fnum(row['dd_time_s_median'])} | "
              f"{fnum(row['sympy_time_s_median'])} | {fnum(row['bdd_sop_time_s_median'])} | {fnum(row['espresso_time_s_median'])} | "
              f"{fint(row['bdd_nodes_median']):>15} | {fint(row['dd_nodes_median']):>12} | {fbool(row.get('cm_ok_all')):>5} | {fbool(row['sympy_ok_all']):>7} | "
              f"{okc}/{trials:>5} | {fbool(row.get('robdd_ok_all')):>9} | {fbool(row['bdd_sop_ok_all']):>11} | {fbool(row['espresso_ok_all']):>11} | {trials:>6} | "
              f"{'Y' if row.get('backend_robdd') else 'N'}  | {'Y' if row['backend_dd'] else 'N'}  | {'Y' if row['backend_espresso'] else 'N'}")

def write_html_report(html_path: str, agg_all: 'pd.DataFrame', depths: List[int], sizes: List[int], trials: int):
    import pandas as pd
    css = """
    <style>
    body { font-family: Segoe UI, Roboto, Arial, sans-serif; padding: 20px; color: #222; }
    h1 { margin: 0 0 8px 0; font-size: 22px; }
    h2 { margin: 16px 0 8px 0; font-size: 18px; }
    .sub { color: #666; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: right; }
    th { background: #f7f7f9; font-weight: 600; }
    td:first-child, th:first-child { text-align: left; }
    .ok { color: #0a7f16; font-weight: 600; }
    .no { color: #b00020; font-weight: 600; }
    .dash { color: #888; }
    </style>
    """
    def fmt_bool(x):
        if x is True: return '<span class="ok">OK</span>'
        if x is None: return '<span class="dash">--</span>'
        return '<span class="no">NO</span>'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(f"<html><head><meta charset='utf-8'>{css}</head><body>")
        f.write("<h1>Boolean Backends Benchmark</h1>")
        f.write(f"<div class='sub'>sizes={sizes}, depths={depths}, trials={trials}</div>")
        for d in depths:
            section = agg_all[agg_all['max_depth']==d].copy()
            # Map boolean columns to tags
            for col in ['cm_ok_all','sympy_ok_all','robdd_ok_all','bdd_sop_ok_all','espresso_ok_all']:
                if col in section.columns:
                    section[col] = section[col].map(lambda v: fmt_bool(v))
            f.write(f"<h2>max_depth = {d}</h2>")
            f.write(section.to_html(index=False, escape=False))
        f.write("</body></html>")
    print("Wrote HTML:", html_path)

def main():
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=str, default="4,8,16")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--depth-sweep", type=str, default="")
    ap.add_argument("--out-prefix", type=str, default="bench_random_ops")
    ap.add_argument("--print-summary", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-robdd", action="store_true")
    ap.add_argument("--no-espresso", action="store_true")
    ap.add_argument("--no-bdd-sop", action="store_true")
    ap.add_argument("--no-sympy", action="store_true")
    ap.add_argument("--no-dd", action="store_true")
    ap.add_argument("--cm-lazy", action="store_true")
    ap.add_argument("--html", type=str, default="")
    global args
    args = ap.parse_args()
    sizes = [int(s) for s in args.sizes.split(",") if s]

    depths = [int(d) for d in args.depth_sweep.split(",") if d] if args.depth_sweep else [args.max_depth]
    agg_all = []
    for d in depths:
        df_raw, df_agg = run_bench(sizes, args.trials, args.seed, d, args.verbose)
        df_agg["max_depth"] = d
        agg_all.append(df_agg)
        raw_path = f"{args.out_prefix}_d{d}_raw.csv" if len(depths)>1 else f"{args.out_prefix}_raw.csv"
        agg_path = f"{args.out_prefix}_d{d}_summary.csv" if len(depths)>1 else f"{args.out_prefix}_summary.csv"
        df_raw.to_csv(raw_path, index=False)
        df_agg.to_csv(agg_path, index=False)
        print("Wrote", raw_path, "and", agg_path)
        if args.print_summary:
            print_summary_table(df_agg)

    if args.html:
        agg_cat = pd.concat(agg_all, ignore_index=True) if len(agg_all)>1 else agg_all[0]
        write_html_report(args.html, agg_cat, depths, sizes, args.trials)

if __name__ == "__main__":
    main()
