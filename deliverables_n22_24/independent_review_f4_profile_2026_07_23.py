"""Independent review of F4 with methods different from V3's timer split.

1. cProfile: run eval_expr_flat_bitset over the same-formula population at
   ambient n=24 and n=32; report the cumulative-time fraction spent inside
   _bind_flat_program and build key/sort helpers. If V3's attribution is right,
   the profile delta between ambients should be concentrated in the binder.

2. Micro-decomposition of the binder cache-hit path into its parts:
   dict(fixed) items -> sorted() -> tuple() -> hash -> dict.get, plus the
   template.copy() that lives in the eval (slot-count-dependent, not ambient-
   dependent). Measured at synthetic fixed sizes 8..64 to expose the scaling law.

3. Population comparability: live_k and program-op distributions of the
   original extended-campaign populations at n=24 vs n=32 (depth 4), from the
   committed raw CSV — the check that V3's same-formula isolation transfers to
   the independently generated populations.
"""
from __future__ import annotations

import cProfile
import csv
import pstats
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir

OUT = REPO / "deliverables_n22_24"
TRIALS = 60
CALLS = 400


def build_population():
    pop = []
    for trial in range(TRIALS):
        expr = random_expr(
            24,
            np.random.default_rng(26_000_000 + 24 * 100_000 + 4 * 10_000 + trial),
            max_depth=4,
            p_unary=0.25,
        )
        node = compile_expr_to_cm_ir(expr)
        output_vars = tuple(node.vars)
        pop.append((expr, output_vars))
    return pop


def profile_fraction(pop, ambient_n):
    vars_all = tuple(f"x{i}" for i in range(ambient_n))
    fixtures = [
        (expr, out, {name: 0 for name in vars_all if name not in out})
        for expr, out in pop
    ]
    for expr, out, fixed in fixtures:  # warm caches
        bb.eval_expr_flat_bitset(expr, out, fixed=fixed)

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(CALLS // TRIALS):
        for expr, out, fixed in fixtures:
            bb.eval_expr_flat_bitset(expr, out, fixed=fixed)
    profiler.disable()
    stats = pstats.Stats(profiler)
    total = stats.total_tt
    bind = 0.0
    sort_builtin = 0.0
    for (filename, _line, name), stat in stats.stats.items():
        cumulative = stat[3]
        internal = stat[2]
        if name == "_bind_flat_program":
            bind = cumulative
        if name == "sorted":
            sort_builtin = internal
    return {"ambient_n": ambient_n, "profile_total_s": round(total, 4),
            "bind_cum_s": round(bind, 4),
            "bind_fraction": round(bind / total, 3),
            "sorted_internal_s": round(sort_builtin, 4)}


def key_scaling():
    rows = []
    out_vars = tuple(f"x{i}" for i in range(6))
    for fixed_count in (8, 16, 18, 24, 26, 32, 48, 64):
        fixed = {f"x{i}": 0 for i in range(100, 100 + fixed_count)}
        items = None

        def t(fn, reps=20000):
            start = perf_counter()
            for _ in range(reps):
                fn()
            return (perf_counter() - start) / reps * 1e6

        us_items = t(lambda: tuple(fixed.items()))
        us_sorted = t(lambda: sorted(fixed.items()))
        us_key = t(lambda: (out_vars, tuple(sorted(fixed.items()))))
        key = (out_vars, tuple(sorted(fixed.items())))
        us_hash = t(lambda: hash(key))
        cache = {key: 1}
        us_get = t(lambda: cache.get(key))
        rows.append(
            {
                "fixed_count": fixed_count,
                "items_us": round(us_items, 3),
                "sorted_items_us": round(us_sorted, 3),
                "full_key_us": round(us_key, 3),
                "hash_prebuilt_us": round(us_hash, 3),
                "dict_get_prebuilt_us": round(us_get, 3),
            }
        )
    return rows


def template_copy_scaling():
    rows = []
    for n_slots in (16, 32, 64, 128):
        template = list(range(n_slots))
        start = perf_counter()
        for _ in range(50000):
            template.copy()
        us = (perf_counter() - start) / 50000 * 1e6
        rows.append({"n_slots": n_slots, "copy_us": round(us, 3)})
    return rows


def population_comparability():
    with (OUT / "CM_FABLE_extended_n32_raw.csv").open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if int(r["depth"]) == 4]
    out = []
    for n in (24, 28, 32):
        sel = [r for r in rows if int(r["n"]) == n and r.get("live_k")]
        live = [int(r["live_k"]) for r in sel]
        out.append(
            {
                "n": n,
                "rows": len(sel),
                "live_k_median": statistics.median(live) if live else None,
                "live_k_p90": float(np.percentile(live, 90)) if live else None,
            }
        )
    return out


def main():
    pop = build_population()
    prof = [profile_fraction(pop, 24), profile_fraction(pop, 32)]
    for row in prof:
        print(row)
    scaling = key_scaling()
    for row in scaling:
        print(row)
    copies = template_copy_scaling()
    for row in copies:
        print(row)
    comparability = population_comparability()
    for row in comparability:
        print(row)

    with (OUT / "CM_independent_review_f4_profile.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.writer(fh)
        writer.writerow(["section", "payload"])
        for section, rows in (
            ("cprofile", prof),
            ("key_scaling", scaling),
            ("template_copy", copies),
            ("population_comparability", comparability),
        ):
            for row in rows:
                writer.writerow([section, repr(row)])


if __name__ == "__main__":
    main()
