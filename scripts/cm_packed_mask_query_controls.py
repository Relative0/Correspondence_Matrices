"""Descriptive count-only controls; reused development inputs, no selector fitting."""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
from pathlib import Path
import random
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import cm_packed_mask_audit as audit
from dd.autoref import BDD


def count_session(case, backend, q):
    names = tuple(f"x{i}" for i in range(case["n"]))
    if backend == "bdd_autoref":
        manager = BDD()
        manager.declare(*names)
        values = []
        for node in case["document"]["nodes"]:
            op = node["op"]
            if op == "var": value = manager.var(f"x{node['i']}")
            elif op == "not": value = ~values[node["a"]]
            else:
                left, right = values[node["a"]], values[node["b"]]
                if op == "and": value = left & right
                elif op == "or": value = left | right
                elif op == "xor": value = manager.apply("xor", left, right)
                elif op == "imp": value = ~left | right
                elif op == "eqv": value = ~manager.apply("xor", left, right)
                else: raise ValueError(op)
            values.append(value)
        root = values[case["document"]["root"]]
        return tuple(int(manager.count(root, nvars=case["n"])) for _ in range(q))
    expr = audit.expr_from_json(case["document"])
    if backend == "direct":
        env = audit.bs.build_bitset_env(names)
        return tuple(audit.bs.eval_expr_bitset(expr, env).bit_count() for _ in range(q))
    if backend == "cse_flat":
        audit.bs.get_expr_cse_program(expr, flatten=True)
        return tuple(audit.bs.eval_expr_flat_cse(expr, names, flatten=True).bit_count() for _ in range(q))
    node = audit.cm_ir.compile_expr_to_cm_ir(expr)
    return tuple(audit.cm_ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=True, hybrid_threshold=case["n"]).bits.bit_count() for _ in range(q))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit.load_baseline(args.output)
    cases = json.loads((args.output / "fixtures.json").read_text())["development"]
    schedule = [(case, q) for case in cases for q in (1, 64)]
    rows = []
    for case, q in schedule:
        expected = int.from_bytes(audit.oracle(case, [{}])[0], "little").bit_count()
        methods = ["direct", "cse_flat", "cm_public", "bdd_autoref"]
        for repeat in range(9):
            order = methods[repeat % 4:] + methods[:repeat % 4]
            for method in order:
                with audit.arm_scope("candidate"):
                    gc.collect()
                    start = time.perf_counter_ns()
                    result = count_session(case, method, q)
                    elapsed = time.perf_counter_ns() - start
                    assert result == (expected,) * q
                rows.append(dict(case=case["id"], backend=method, q=q, repeat=repeat,
                                 total_ns=elapsed, exact=True, count=expected))
        for method in methods:
            with audit.arm_scope("candidate"):
                gc.collect()
                tracemalloc.start()
                result = count_session(case, method, q)
                retained, peak = tracemalloc.get_traced_memory()
                del result
                audit.bs.clear_bitset_env_cache()
                gc.collect()
                released, _ = tracemalloc.get_traced_memory()
                tracemalloc.stop()
            rows.append(dict(case=case["id"], backend=method, q=q, traced_peak=peak,
                             traced_retained=retained, traced_released=released))
    audit.write_json(args.output / "query_controls.json", {
        "scope": "count-only diagnostics on exposed development inputs, fixed BDD order, no result cache",
        "availability": {"dd_autoref": True, "dd_cudd": importlib.util.find_spec("dd.cudd") is not None,
                         "numba": importlib.util.find_spec("numba") is not None},
        "rows": rows})
    print("Count-only exact controls complete", len(rows))


if __name__ == "__main__":
    main()
