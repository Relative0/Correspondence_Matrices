"""Source-bound local cache/count/stream panels; no production dispatch changes.

Freeze once after correctness tests, then run development and confirmation in
order. All outputs are exclusive, and failed attempts remain available. Invoke
as ``python -B -m scripts.cm_packed_queries_campaign ...`` from the project root.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc

import numpy as np
from dd.autoref import BDD

import bitset_backend as bs
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, PackedStreamPlan


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "bitset_backend.py", "cm_ir.py", "cm_exprlib.py", "cm_expr_serde.py",
    "cm_normalize.py", "cmbench/backends/packed_mask_cache.py",
    "cmbench/backends/packed_queries.py", "scripts/cm_packed_queries_campaign.py",
    "tests/test_packed_queries.py", "tests/test_packed_queries_campaign.py",
    "scripts/cm_packed_queries_verify.py",
)
REPEATS = 9
SEED = 2026091127


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def tree(nodes, op):
    nodes = list(nodes)
    while len(nodes) > 1:
        nodes = [op(nodes[i], nodes[i + 1]) if i + 1 < len(nodes) else nodes[i]
                 for i in range(0, len(nodes), 2)]
    return nodes[0]


def count_fixture(n, block_width, seed, entangled):
    rng = random.Random(seed)
    axes = list(range(n))
    rng.shuffle(axes)
    blocks = []
    for start in range(0, n, block_width):
        leaves = [Var(i) for i in axes[start:start + block_width]]
        block = tree(leaves, rng.choice((Or, Xor, Eqv)))
        blocks.append(block)
    return expr_to_json_dag(tree(blocks, Or if entangled else And))


def stream_fixture(n, seed):
    rng = random.Random(seed)
    axes = list(range(n))
    rng.shuffle(axes)
    root = tree([Var(i) for i in axes], Xor)
    for _ in range(6):
        root = Eqv(Imp(root, Var(rng.randrange(n))), Or(root, Var(rng.randrange(n))))
    return expr_to_json_dag(root)


def cases():
    result = {"development": [], "confirmation": []}
    for cohort, widths in (("development", (12, 16)), ("confirmation", (18, 20))):
        for n in widths:
            for entangled in (False, True):
                result[cohort].append({
                    "id": f"{cohort}-count-n{n}-entangled{int(entangled)}", "task": "count",
                    "n": n, "document": count_fixture(n, 3 if n % 3 == 0 else 4,
                                                        SEED + n, entangled),
                    "entangled": entangled,
                })
    for cohort, widths in (("development", (16, 18)), ("confirmation", (17, 20))):
        for n in widths:
            result[cohort].append({"id": f"{cohort}-stream-n{n}", "task": "stream", "n": n,
                                   "document": stream_fixture(n, SEED + 100 + n)})
    for cohort, width in (("development", 16), ("confirmation", 18)):
        for mode in ("same", "renamed", "phases", "pressure"):
            result[cohort].append({"id": f"{cohort}-cache-n{width}-{mode}", "task": "cache",
                                   "n": width, "mode": mode})
    for cohort in result.values():
        for case in cohort:
            if "document" in case:
                case["document_json"] = json.dumps(case["document"], separators=(",", ":"))
    return result


def methods(case):
    if case["task"] == "count":
        return ("direct", "cse_flat", "independent_expr", "independent_cm", "bdd_autoref")
    if case["task"] == "stream":
        return ("complete", "stream_8", "stream_12", "stream_16")
    return ("uncached", "named_lru", "positional")


def queries(case, q):
    if case["task"] == "cache":
        n = case["n"]
        mode = case["mode"]
        result = []
        for i in range(32):
            width = n if mode in ("same", "renamed") else n - (i // 8 % 3) * 2
            key = 0 if mode in ("same", "phases") else i
            result.append(tuple(f"request-{key}-axis-{axis}" for axis in range(width)))
        return result
    if q == 1:
        return [{}]
    return [{f"x{(i + j * 3) % case['n']}": (i >> j) & 1 for j in range(3)}
            for i in range(q)]


def oracle(case, context):
    """Boolean NumPy DAG interpretation at each residual assignment, no packed masks."""
    live = tuple(f"x{i}" for i in range(case["n"]) if f"x{i}" not in context)
    indexes = np.arange(1 << len(live), dtype=np.uint32)
    env = {name: ((indexes >> (len(live) - i - 1)) & 1).astype(bool) for i, name in enumerate(live)}
    env.update({name: np.full(indexes.size, bool(value)) for name, value in context.items()})
    values = []
    for node in case["document"]["nodes"]:
        op = node["op"]
        if op == "var":
            value = env[f"x{node['i']}"]
        elif op == "not":
            value = np.logical_not(values[node["a"]])
        else:
            a, b = values[node["a"]], values[node["b"]]
            if op == "and": value = np.logical_and(a, b)
            elif op == "or": value = np.logical_or(a, b)
            elif op == "xor": value = np.logical_xor(a, b)
            elif op == "eqv": value = np.equal(a, b)
            elif op == "imp": value = np.logical_or(np.logical_not(a), b)
            else: raise ValueError(op)
        values.append(value)
    truth = values[case["document"]["root"]]
    return int(np.count_nonzero(truth)), hashlib.sha256(np.packbits(truth, bitorder="little").tobytes()).hexdigest()


def freeze(output):
    output.mkdir(parents=True, exist_ok=False)
    fixtures = cases()
    source_names = set(SOURCES)
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(ROOT) and path.suffix == ".py":
            relative = path.relative_to(ROOT)
            if relative.parts[0] not in (".venv", "venv", "external"):
                source_names.add(relative.as_posix())
    source_names = sorted(source_names)
    schedule = []
    for cohort in fixtures:
        for case in fixtures[cohort]:
            for q in ((32,) if case["task"] == "cache" else (1, 16)):
                arms = methods(case)
                for repeat in range(REPEATS):
                    order = arms if repeat % 2 == 0 else tuple(reversed(arms))
                    # Every candidate versus baseline pair reverses relative order.
                    for arm in order:
                        schedule.append(dict(cohort=cohort, case=case["id"], q=q, repeat=repeat, method=arm))
    write(output / "FIXTURES.json", fixtures)
    write(output / "FREEZE.json", {
        "schema": "cm-packed-queries-local/v1", "seed": SEED, "repeats": REPEATS,
        "sources": {rel: sha(ROOT / rel) for rel in source_names},
        "fixtures_sha256": sha(output / "FIXTURES.json"), "schedule": schedule,
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "dd", "networkx", "pytest")},
        "checkpoint": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "protocol": {
            "scope": "synthetic local engineering evidence; no tuned selector or default switch",
            "cold": "JSON decode, compile, bind, execute, scalar JSON or ordered vector SHA256 delivery, explicit cache/plan release",
            "warm": "same queries with prepared plan and cache, separate from cold total",
            "process_startup": "excluded from resident cells; separately recorded in lifecycle command",
            "memory": "separate tracemalloc pass, not RSS; caller discards streamed chunks after SHA256 consumption",
            "direct_control": "identity-memoized contextual interpreter; explicit recursion-cell release avoids retaining its masks until cyclic GC",
            "cache_budget": "2 MiB admitted column payload; pressure scenario 64 KiB; max build width 20",
            "acceptance": "zero semantic or guard failures; retain options and report regressions, no universal performance gate",
            "confirmation": "distinct synthetic widths/expressions; freeze precedes timings; no retuning",
        },
    })
    for rel in source_names:
        target = output / "source" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())
    print(output, flush=True)


def direct(expr, live, fixed):
    env = bs.build_bitset_env(live)
    full = (1 << (1 << len(live))) - 1
    memo = {}

    def rec(node):
        key = id(node)
        if key in memo:
            return memo[key]
        if isinstance(node, Var):
            name = f"x{node.i}"
            value = full if fixed.get(name) == 1 else (0 if name in fixed else env[name])
        elif isinstance(node, Not): value = (~rec(node.a)) & full
        else:
            a, b = rec(node.a), rec(node.b)
            if isinstance(node, And): value = a & b
            elif isinstance(node, Or): value = a | b
            elif isinstance(node, Xor): value = a ^ b
            elif isinstance(node, Eqv): value = (~(a ^ b)) & full
            elif isinstance(node, Imp): value = ((~a) | b) & full
            else: raise TypeError(node)
        memo[key] = value
        return value

    result = rec(expr)
    # Break the recursive function's self-reference before returning so this
    # strengthened direct control pays immediate release of its packed inputs.
    rec = None
    return result


def bdd_runner(document, basis):
    manager = BDD()
    manager.configure(reordering=False)
    manager.declare(*basis)
    values = []
    for node in document["nodes"]:
        op = node["op"]
        if op == "var": value = manager.var(f"x{node['i']}")
        elif op == "not": value = ~values[node["a"]]
        else:
            a, b = values[node["a"]], values[node["b"]]
            if op == "and": value = a & b
            elif op == "or": value = a | b
            elif op == "xor": value = manager.apply("xor", a, b)
            elif op == "eqv": value = ~manager.apply("xor", a, b)
            elif op == "imp": value = ~a | b
            else: raise ValueError(op)
        values.append(value)
    root = values[document["root"]]
    return lambda context: int(manager.count(manager.let({k: bool(v) for k, v in context.items()}, root),
                                             nvars=len(basis) - len(context)))


def make_runner(case, method, pool):
    basis = tuple(f"x{i}" for i in range(case["n"]))
    if case["task"] == "cache":
        if method == "positional": return pool.environment
        if method == "named_lru": return bs.build_bitset_env
        return bs._build_bitset_env_cached.__wrapped__
    document = json.loads(case["document_json"])
    # Serialized ingress is common and explicitly charged to every method.
    if method == "bdd_autoref": return bdd_runner(document, basis)
    expr = expr_from_json(document)
    if method == "independent_expr":
        return IndependentCountPlan.from_expr(expr, basis, cache=pool).count
    if method == "independent_cm":
        node = compile_expr_to_cm_ir(expr)
        return IndependentCountPlan.from_cm_node(node, basis, cache=pool).count
    if method == "direct":
        return lambda context: direct(expr, tuple(n for n in basis if n not in context), context).bit_count()
    if method.startswith("stream_"):
        return PackedStreamPlan.from_expr(expr, basis, cache=pool)
    bs.get_expr_cse_program(expr, flatten=True)
    return lambda context: bs.eval_expr_flat_cse(expr, tuple(n for n in basis if n not in context),
                                               fixed=context, flatten=True)


def consume(case, method, runner, contexts):
    values = []
    first_ready = None
    started = time.perf_counter_ns()
    for context in contexts:
        if case["task"] == "cache":
            env = runner(context)
            # The trace consumer samples every mask; no returned environments are retained.
            values.append(tuple((value.bit_length(), value & 255) for value in env.values()))
        elif case["task"] == "count":
            value = runner(context)
            values.append(value.bit_count() if method == "cse_flat" else value)
        else:
            digest = hashlib.sha256()
            if method == "complete":
                bits = runner(context)
                data = bits.to_bytes(max(1, (1 << (case["n"] - len(context))) // 8), "little")
                if first_ready is None: first_ready = time.perf_counter_ns() - started
                digest.update(data)
            else:
                for chunk in runner.iter_chunks(chunk_vars=int(method.split("_")[1]),
                                                 max_total_bits=1 << case["n"], fixed=context):
                    if first_ready is None: first_ready = time.perf_counter_ns() - started
                    digest.update(chunk.data)
            values.append(digest.hexdigest())
    return json.dumps(values, separators=(",", ":")), first_ready


def session(case, method, q, *, warm=True):
    start = time.perf_counter_ns()
    pool = PackedMaskCache(max_bytes=(65536 if case.get("mode") == "pressure" else 2 << 20), max_width=20)
    runner = make_runner(case, method, pool)
    contexts = queries(case, q)
    setup = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    result, first = consume(case, method, runner, contexts)
    query_time = time.perf_counter_ns() - start
    warm_time = 0
    if warm:
        start = time.perf_counter_ns()
        again, _ = consume(case, method, runner, contexts)
        warm_time = time.perf_counter_ns() - start
        if again != result: raise AssertionError("warm output mismatch")
    stats = pool.stats()
    start = time.perf_counter_ns()
    del runner
    pool.clear()
    bs.clear_bitset_env_cache()
    cleanup = time.perf_counter_ns() - start
    return result, {"total_ns": setup + query_time + cleanup, "setup_ns": setup,
                    "query_delivery_ns": query_time, "cleanup_ns": cleanup,
                    "warm_ns": warm_time, "first_chunk_ns": None if first is None else setup + first,
                    "cache": stats}


def expected(case, q):
    contexts = queries(case, q)
    if case["task"] == "cache":
        values = []
        for basis in contexts:
            width = len(basis)
            # Independent small periodic samples and known highest set bit.
            values.append(tuple((1 << width, sum(((row >> (width - 1 - axis)) & 1) << row for row in range(min(8, 1 << width))))
                                for axis in range(width)))
        return json.dumps(values, separators=(",", ":"))
    values = [oracle(case, context)[0 if case["task"] == "count" else 1] for context in contexts]
    return json.dumps(values, separators=(",", ":"))


def check_sources(output):
    frozen = json.loads((output / "FREEZE.json").read_text())
    if sha(output / "FIXTURES.json") != frozen["fixtures_sha256"]:
        raise ValueError("fixture identity changed")
    for relative, expected_hash in frozen["sources"].items():
        if sha(ROOT / relative) != expected_hash or sha(output / "source" / relative) != expected_hash:
            raise ValueError(f"source identity changed: {relative}")
    return frozen


def summarize(rows):
    cells = {}
    for row in rows:
        cells.setdefault((row["case"], row["q"]), []).append(row)
    result = []
    rng = random.Random(SEED + 9)
    for (case, q), group in cells.items():
        baseline = ("named_lru" if "-cache-" in case else "complete" if "-stream-" in case else "cse_flat")
        base = {r["repeat"]: r for r in group if r["method"] == baseline}
        for method in sorted({r["method"] for r in group}):
            candidate = {r["repeat"]: r for r in group if r["method"] == method}
            logs = [math.log(base[i]["total_ns"] / candidate[i]["total_ns"]) for i in sorted(base)]
            draws = sorted(math.exp(sum(rng.choice(logs) for _ in logs) / len(logs)) for _ in range(2000))
            result.append({"case": case, "q": q, "method": method, "baseline": baseline,
                           "median_total_ns": statistics.median(r["total_ns"] for r in candidate.values()),
                           "median_warm_ns": statistics.median(r["warm_ns"] for r in candidate.values()),
                           "speedup_ratio_of_medians": statistics.median(r["total_ns"] for r in base.values()) / statistics.median(r["total_ns"] for r in candidate.values()),
                           "paired_geomean_speedup": math.exp(statistics.mean(logs)),
                           "paired_bootstrap_95pct": [draws[49], draws[1949]],
                           "worst_pair_speedup": min(math.exp(x) for x in logs),
                           "median_first_chunk_ns": statistics.median(r["first_chunk_ns"] for r in candidate.values()) if candidate[0]["first_chunk_ns"] is not None else None})
    return result


def run(output, cohort):
    frozen = check_sources(output)
    fixtures = json.loads((output / "FIXTURES.json").read_text())[cohort]
    indexed = {case["id"]: case for case in fixtures}
    oracles = {(case["id"], q): expected(case, q) for case in fixtures
               for q in ((32,) if case["task"] == "cache" else (1, 16))}
    write(output / f"{cohort}-ORACLES.json", [{"case": key[0], "q": key[1], "result": value} for key, value in oracles.items()])
    rows = []
    with (output / f"{cohort}-RAW.jsonl").open("x", encoding="utf-8") as stream:
        for cell in frozen["schedule"]:
            if cell["cohort"] != cohort: continue
            bs.clear_bitset_env_cache()
            gc.collect()
            result, measurements = session(indexed[cell["case"]], cell["method"], cell["q"])
            row = dict(cell, **measurements, exact=result == oracles[(cell["case"], cell["q"])],
                       result_sha256=hashlib.sha256(result.encode()).hexdigest())
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            if not row["exact"]: raise AssertionError(cell)
            rows.append(row)
    memory = []
    for case in fixtures:
        for q in ((32,) if case["task"] == "cache" else (1, 16)):
            for method in methods(case):
                bs.clear_bitset_env_cache()
                gc.collect()
                tracemalloc.start()
                result, measurements = session(case, method, q, warm=False)
                retained, peak = tracemalloc.get_traced_memory()
                exact = result == oracles[(case["id"], q)]
                del result
                gc.collect()
                released, _ = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                if not exact: raise AssertionError((case["id"], q, method, "memory output"))
                memory.append(dict(case=case["id"], q=q, method=method, peak_bytes=peak,
                                   after_session_bytes=retained, after_gc_bytes=released,
                                   exact=exact, cache=measurements["cache"]))
    write(output / f"{cohort}-MEMORY.json", memory)
    write(output / f"{cohort}-SUMMARY.json", summarize(rows))
    print(cohort, "complete", len(rows), "timing rows", len(memory), "memory rows", flush=True)


def lifecycle(output):
    check_sources(output)
    fixtures = json.loads((output / "FIXTURES.json").read_text())
    selected = [case for cohort in fixtures.values() for case in cohort
                if (case["task"] == "count" and not case["entangled"] and case["n"] in (16, 20))
                or (case["task"] == "stream" and case["n"] in (16, 20))
                or (case["task"] == "cache" and case["mode"] == "renamed")]
    rows = []
    for case in selected:
        arms = (("cse_flat", "independent_expr") if case["task"] == "count" else
                ("complete", "stream_12") if case["task"] == "stream" else ("named_lru", "positional"))
        q = 32 if case["task"] == "cache" else 1
        target = expected(case, q)
        for repeat in range(5):
            for method in (arms if repeat % 2 == 0 else tuple(reversed(arms))):
                start = time.perf_counter_ns()
                completed = subprocess.run([sys.executable, "-B", "-m", "scripts.cm_packed_queries_campaign",
                                            "worker", "--output", str(output), "--case", case["id"],
                                            "--method", method, "--q", str(q)], cwd=ROOT, text=True,
                                           capture_output=True, timeout=60, check=True)
                elapsed = time.perf_counter_ns() - start
                row = json.loads(completed.stdout)
                row.update(case=case["id"], q=q, method=method, repeat=repeat,
                           process_lifecycle_ns=elapsed, exact=row["result"] == target)
                if not row["exact"]: raise AssertionError(row)
                rows.append(row)
    write(output / "LIFECYCLE.json", rows)
    print("lifecycle complete", len(rows), "fresh children", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "development", "confirmation", "lifecycle", "worker"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case")
    parser.add_argument("--method")
    parser.add_argument("--q", type=int)
    args = parser.parse_args()
    if args.action == "freeze": freeze(args.output)
    elif args.action == "lifecycle": lifecycle(args.output)
    elif args.action == "worker":
        fixtures = json.loads((args.output / "FIXTURES.json").read_text())
        case = next(case for cohort in fixtures.values() for case in cohort if case["id"] == args.case)
        result, measurements = session(case, args.method, args.q, warm=False)
        print(json.dumps(dict(result=result, **measurements)))
    else: run(args.output, args.action)


if __name__ == "__main__":
    main()
