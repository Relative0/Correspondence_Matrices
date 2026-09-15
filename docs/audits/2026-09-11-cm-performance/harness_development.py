"""Local paired audit of periodic truth-mask construction; no external services.

The baseline is an exact source snapshot created before editing the implementation.
All arms return ordered, complete packed relations. Synthetic confirmation inputs
are separate from development; they are not evidence of application prevalence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import cProfile
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import pstats
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from functools import lru_cache
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import bitset_backend as bs
import cm_ir
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def periodic_env(vars_key):
    """Candidate: emit exact periodic bytes; keep the existing <=10 branch."""
    n = len(vars_key)
    if n <= 10:
        return BASELINE._build_bitset_env_cached.__wrapped__(vars_key)
    n_bytes = (1 << n) // 8
    env = {}
    for position, name in enumerate(vars_key):
        shift = n - 1 - position
        if shift < 3:
            packed = (b"\xaa", b"\xcc", b"\xf0")[shift] * n_bytes
        else:
            block_bytes = 1 << (shift - 3)
            period = b"\x00" * block_bytes + b"\xff" * block_bytes
            packed = period * (n_bytes // (2 * block_bytes))
        env[name] = int.from_bytes(packed, "little")
    return MappingProxyType(env)


def load_baseline(output):
    global BASELINE
    path = output / "baseline_bitset_backend.py"
    spec = importlib.util.spec_from_file_location("cm_mask_baseline", path)
    BASELINE = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = BASELINE
    spec.loader.exec_module(BASELINE)


@contextmanager
def arm_scope(arm):
    previous = bs._build_bitset_env_cached
    factory = BASELINE._build_bitset_env_cached.__wrapped__ if arm == "baseline" else periodic_env
    bs._build_bitset_env_cached = lru_cache(maxsize=256)(factory)
    bs.clear_words_env_cache()
    try:
        yield
    finally:
        bs.clear_words_env_cache()
        bs._build_bitset_env_cached = previous


def fixture(n, seed, sharing):
    rng = random.Random(seed)
    nodes = [Var(i) for i in range(n)]
    rng.shuffle(nodes)
    while len(nodes) > 1:
        next_level = []
        for index in range(0, len(nodes) - 1, 2):
            next_level.append(rng.choice((Xor, And, Or, Imp, Eqv))(nodes[index], nodes[index + 1]))
        if len(nodes) % 2:
            next_level.append(nodes[-1])
        nodes = next_level
    root = nodes[0]
    if sharing:
        for _ in range(8):
            common = root
            root = Xor(And(common, Var(rng.randrange(n))), Or(Not(common), Var(rng.randrange(n))))
    return expr_to_json_dag(root)


def freeze(output):
    output.mkdir(parents=True, exist_ok=False)
    baseline = ROOT / "bitset_backend.py"
    (output / "baseline_bitset_backend.py").write_bytes(baseline.read_bytes())
    cohorts = {}
    for cohort, widths, seed in (("development", (12, 16), 911001),
                                 ("confirmation", (11, 13, 18), 911101)):
        cohorts[cohort] = [dict(id=f"{cohort}-n{n}-s{sharing}", n=n,
                                   sharing=bool(sharing), seed=seed + n * 17 + sharing,
                                   document=fixture(n, seed + n * 17 + sharing, sharing))
                             for n in widths for sharing in (0, 1)]
    write_json(output / "fixtures.json", cohorts)
    source_paths = [ROOT / "cm_ir.py", ROOT / "cm_exprlib.py", ROOT / "cm_expr_serde.py",
                    ROOT / "cm_normalize.py", ROOT / "bitset_backend.py", Path(__file__)]
    source_paths += list((ROOT / "cmbench" / "backends").glob("*.py"))
    source_paths += [ROOT / "cmbench" / "output_budget.py", ROOT / "cmbench" / "__init__.py"]
    write_json(output / "freeze.json", {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "executable": sys.executable, "numpy": np.__version__,
        "platform": platform.platform(), "processor": platform.processor(), "cpu_count": os.cpu_count(),
        "fixtures_sha256": sha(output / "fixtures.json"),
        "sources": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
        "protocol": {
            "candidate": "direct periodic packed bytes only above existing width-10 boundary",
            "repeats": 9, "order": "paired AB/BA alternating; seeded cell shuffle",
            "timing": "uninstrumented whole session including decode/compile/bind/evaluate/packed delivery; caches cleared outside timing",
            "reuse": "q1 or q64 with prepared representation retained inside session; warm loop separate",
            "output": "ordered tuple of complete packed residual relations, little endian",
            "memory": "separate tracemalloc; fresh child OS endpoints and lifetime peak descriptive",
            "confirmation": "no algorithm/threshold tuning on confirmation results",
            "acceptance": "zero mismatches; cold env geomean >1.2, all targeted cold CM case medians >=0.95; warm regressions reported",
            "scope": "synthetic local engineering evidence; no routing, application or cross-machine claim",
        },
    })
    print("Frozen", output)


def oracle(case, queries):
    """Independent Boolean-vector interpretation, without the packed environment."""
    n = case["n"]
    rows = np.arange(1 << n, dtype=np.uint32)
    values = []
    for node in case["document"]["nodes"]:
        op = node["op"]
        if op == "var":
            result = ((rows >> (n - 1 - node["i"])) & 1).astype(bool)
        elif op == "not":
            result = np.logical_not(values[node["a"]])
        else:
            left, right = values[node["a"]], values[node["b"]]
            if op == "and": result = np.logical_and(left, right)
            elif op == "or": result = np.logical_or(left, right)
            elif op == "xor": result = np.logical_xor(left, right)
            elif op == "imp": result = np.logical_or(np.logical_not(left), right)
            elif op == "eqv": result = np.equal(left, right)
            else: raise ValueError(op)
        values.append(result)
    truth = values[case["document"]["root"]].reshape((2,) * n)
    return tuple(np.packbits(truth[tuple(fixed.get(f"x{i}", slice(None)) for i in range(n))].reshape(-1),
                             bitorder="little").tobytes() for fixed in queries)


def queries_for(case, q, restricted):
    n = case["n"]
    if not restricted:
        return [{} for _ in range(q)]
    # Rotating positions exercise named-basis cache misses and differing values.
    return [{f"x{(j + offset) % n}": (j >> offset) & 1 for offset in range(3)} for j in range(q)]


def session(case, backend, queries, stages=None, warm=False):
    def step(label, function):
        if stages is None:
            return function()
        start = time.perf_counter_ns()
        result = function()
        stages[label] = stages.get(label, 0) + time.perf_counter_ns() - start
        return result

    expr = step("decode", lambda: expr_from_json(case["document"]))
    if backend in ("cm_flat", "cm_words", "cm_public", "dense"):
        node = step("compile", lambda: cm_ir.compile_expr_to_cm_ir(expr))
    elif backend == "cse":
        step("compile", lambda: bs.get_expr_cse_program(expr))

    def execute():
        outputs = []
        for fixed in queries:
            live = tuple(f"x{i}" for i in range(case["n"]) if f"x{i}" not in fixed)
            if backend == "direct":
                # The legacy direct Expr evaluator infers width from len(env), so
                # use its public flat fixed-assignment control for restrictions.
                if fixed:
                    value = step("execute", lambda: bs.eval_expr_flat_bitset(expr, live, fixed=fixed))
                else:
                    env = step("bind", lambda: bs.build_bitset_env(live))
                    value = step("execute", lambda: bs.eval_expr_bitset(expr, env))
            elif backend == "cse":
                value = step("execute_bind", lambda: bs.eval_expr_flat_cse(expr, live, fixed=fixed))
            elif backend == "cm_flat":
                value = step("execute_bind", lambda: bs.eval_cm_node_flat(node, live, fixed=fixed))
            elif backend == "cm_words":
                value = step("execute_bind", lambda: bs.eval_cm_node_words(node, live, fixed=fixed))
            elif backend == "cm_public":
                value = step("execute_bind_guard", lambda: cm_ir.materialize_hybrid_no_reinflate(
                    node, live, fixed, flat_eval=True, hybrid_threshold=case["n"])).bits
            elif backend == "dense":
                split = len(live) // 2
                dense = step("execute_guard", lambda: cm_ir.materialize_cm(
                    node, live[:split], live[split:], fixed, materialize_mode="numpy", hybrid_threshold=0))
                outputs.append(step("delivery", lambda: np.packbits(dense.reshape(-1), bitorder="little").tobytes()))
                continue
            else:
                raise ValueError(backend)
            outputs.append(step("delivery", lambda: value.to_bytes(max(1, (1 << len(live)) // 8), "little")))
        return tuple(outputs)

    if warm:
        execute()
        start = time.perf_counter_ns()
        result = execute()
        return result, time.perf_counter_ns() - start
    return execute()


def interval(values, seed=912):
    rng = random.Random(seed)
    logs = [math.log(value) for value in values]
    samples = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(2000))
    return [samples[50], samples[1949]]


def campaign(output, cohort):
    fixtures = json.loads((output / "fixtures.json").read_text())[cohort]
    rows = []
    cells = [(case, backend, q, restricted) for case in fixtures
             for backend in ("direct", "cse", "cm_flat", "cm_words", "cm_public", "dense")
             for q, restricted in ((1, False), (64, False), (16, True))]
    random.Random(911).shuffle(cells)
    raw_path = output / f"{cohort}_raw.jsonl"
    with raw_path.open("x", encoding="utf-8") as raw:
        for case, backend, q, restricted in cells:
            queries = queries_for(case, q, restricted)
            expected = oracle(case, queries)
            for repeat in range(9):
                for arm in (("baseline", "candidate") if repeat % 2 == 0 else ("candidate", "baseline")):
                    gc.collect()
                    with arm_scope(arm):
                        start = time.perf_counter_ns()
                        result = session(case, backend, queries)
                        elapsed = time.perf_counter_ns() - start
                    assert result == expected, (case["id"], backend, arm)
                    with arm_scope(arm):
                        warm_result, warm_ns = session(case, backend, queries, warm=True)
                    assert warm_result == expected
                    row = dict(case=case["id"], n=case["n"], backend=backend, q=q,
                               restricted=restricted, repeat=repeat, arm=arm,
                               total_ns=elapsed, warm_ns=warm_ns,
                               output_sha256=hashlib.sha256(b"".join(result)).hexdigest(), exact=True)
                    raw.write(json.dumps(row) + "\n")
                    raw.flush()
                    rows.append(row)
            print(case["id"], backend, q, restricted, flush=True)
    summaries = []
    for case, backend, q, restricted in cells:
        subset = [r for r in rows if (r["case"], r["backend"], r["q"], r["restricted"]) ==
                  (case["id"], backend, q, restricted)]
        arms = {arm: sorted((r for r in subset if r["arm"] == arm), key=lambda r: r["repeat"])
                for arm in ("baseline", "candidate")}
        summary = dict(case=case["id"], n=case["n"], backend=backend, q=q, restricted=restricted)
        for metric in ("total_ns", "warm_ns"):
            ratios = [a[metric] / b[metric] for a, b in zip(arms["baseline"], arms["candidate"])]
            summary[metric] = {arm: statistics.median(r[metric] for r in values) for arm, values in arms.items()}
            summary[metric].update(speedup=math.exp(statistics.mean(map(math.log, ratios))),
                                   ci95=interval(ratios), min_paired_speedup=min(ratios),
                                   baseline_max=max(r[metric] for r in arms["baseline"]),
                                   candidate_max=max(r[metric] for r in arms["candidate"]))
        summaries.append(summary)
    write_json(output / f"{cohort}_summary.json", summaries)


def profile(output):
    cases = json.loads((output / "fixtures.json").read_text())["development"]
    results = []
    for case in cases:
        for backend in ("direct", "cm_public"):
            for arm in ("baseline", "candidate"):
                with arm_scope(arm):
                    profiler = cProfile.Profile()
                    profiler.enable()
                    session(case, backend, [{}])
                    profiler.disable()
                    filename = f"profile-{case['id']}-{backend}-{arm}.txt"
                    with (output / filename).open("x", encoding="utf-8") as handle:
                        pstats.Stats(profiler, stream=handle).strip_dirs().sort_stats("cumulative").print_stats(25)
                with arm_scope(arm):
                    stages = {}
                    session(case, backend, [{}], stages=stages)
                results.append(dict(case=case["id"], backend=backend, arm=arm, stages_ns=stages))
    write_json(output / "stages.json", results)


def env_bench(output):
    rows = []
    for n in (0, 1, 3, 6, 10, 11, 13, 16, 18, 20, 22):
        names = tuple(f"x{i}" for i in range(n))
        expected = BASELINE._build_bitset_env_cached.__wrapped__(names)
        for repeat in range(9):
            for arm in (("baseline", "candidate") if repeat % 2 == 0 else ("candidate", "baseline")):
                with arm_scope(arm):
                    gc.collect()
                    start = time.perf_counter_ns()
                    result = bs.build_bitset_env(names)
                    elapsed = time.perf_counter_ns() - start
                    assert result == expected
                    start = time.perf_counter_ns()
                    for _ in range(10000):
                        bs.build_bitset_env(names)
                    hit_ns = (time.perf_counter_ns() - start) / 10000
                rows.append(dict(n=n, repeat=repeat, arm=arm, total_ns=elapsed, cache_hit_ns=hit_ns))
        for arm in ("baseline", "candidate"):
            with arm_scope(arm):
                gc.collect()
                tracemalloc.start()
                result = bs.build_bitset_env(names)
                retained, peak = tracemalloc.get_traced_memory()
                del result
                bs.clear_bitset_env_cache()
                gc.collect()
                released, _ = tracemalloc.get_traced_memory()
                tracemalloc.stop()
            rows.append(dict(n=n, arm=arm, traced_retained=retained, traced_peak=peak, traced_released=released))
    write_json(output / "env.json", rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "profile", "environment", "development", "confirmation"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "freeze":
        freeze(args.output)
        return
    load_baseline(args.output)
    if args.mode == "profile": profile(args.output)
    elif args.mode == "environment": env_bench(args.output)
    else: campaign(args.output, args.mode)


if __name__ == "__main__":
    main()
