"""Independent 2026-07-21 correctness audit for CM/bitset/flat/dd paths.

The oracle is always cm_exprlib.eval_expr_tt and is evaluated outside timing
windows.  Every comparison is exhaustive over the relevant truth-table rows.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_bitset,
    eval_cm_node_flat,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    get_expr_flat_program,
    get_flat_program,
)
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate


def xor_chain(indices: Iterable[int]) -> Expr:
    items = list(indices)
    out: Expr = Var(items[0])
    for i in items[1:]:
        out = Xor(out, Var(i))
    return out


def mixed_chain(indices: Iterable[int]) -> Expr:
    items = list(indices)
    out: Expr = Var(items[0])
    constructors = (Imp, Eqv, Xor, Or, And)
    for pos, i in enumerate(items[1:]):
        out = constructors[pos % len(constructors)](out, Var(i))
    return out


def expand_result(result, n: int) -> np.ndarray:
    """Expand a no-reinflate result to all 2**n rows, MSB first."""
    output_vars = tuple(result.output_vars)
    k = len(output_vars)
    if result.bits is not None:
        reduced = bitset_to_bool_array(int(result.bits), k)
    elif result.tt is not None:
        reduced = np.asarray(result.tt, dtype=np.uint8).reshape(-1)
    else:
        raise AssertionError("no output payload")
    if output_vars == tuple(f"x{i}" for i in range(n)):
        return reduced
    rows = np.arange(1 << n, dtype=np.uint32)
    reduced_index = np.zeros(1 << n, dtype=np.uint32)
    for name in output_vars:
        i = int(name[1:])
        reduced_index = (reduced_index << 1) | ((rows >> (n - 1 - i)) & 1)
    return reduced[reduced_index]


def cases_for_n(n: int) -> list[tuple[str, Expr]]:
    rng = np.random.default_rng(260721 + n)
    sparse = [0, max(1, n // 3), max(2, (2 * n) // 3), n - 1]
    return [
        ("single_var", Var(n - 1)),
        ("annihilating", And(Var(0), Not(Var(0)))),
        ("repeated_vars", Eqv(Xor(Var(0), Var(n - 1)), Xor(Var(0), Var(n - 1)))),
        ("sparse_mixed", mixed_chain(sparse)),
        ("all_live_xor", xor_chain(range(n))),
        ("random_depth4", random_expr(n, rng, max_depth=4, p_unary=0.25)),
    ]


def audit_case(n: int, label: str, expr: Expr) -> dict[str, object]:
    oracle = eval_expr_tt(expr, n).astype(np.uint8, copy=False).reshape(-1)
    vars_all = tuple(f"x{i}" for i in range(n))
    node = compile_expr_to_cm_ir(expr)
    live_k = len(node.vars)

    raw = bitset_to_bool_array(eval_expr_bitset(expr, build_bitset_env(vars_all)), n)
    cm_recursive = bitset_to_bool_array(eval_cm_node_bitset(node, vars_all), n)
    cm_flat = bitset_to_bool_array(eval_cm_node_flat(node, vars_all), n)

    # Raise the safety limit only for the exhaustive audit.  allow_reduced_output
    # still exercises repr 3/4 whenever ambient n exceeds the limit and live_k fits.
    reduced_limit = 16 if live_k <= 16 else n
    reduced = materialize_hybrid_no_reinflate(
        node,
        vars_all,
        fixed={},
        hybrid_threshold=live_k,  # includes the live_k == threshold boundary
        allow_reduced_output=n > reduced_limit,
        max_full_output_vars=reduced_limit,
        flat_eval=True,
    )
    expanded = expand_result(reduced, n)

    checks = {
        "raw_bitset": bool(np.array_equal(raw, oracle)),
        "cm_ir_recursive": bool(np.array_equal(cm_recursive, oracle)),
        "cm_ir_flat": bool(np.array_equal(cm_flat, oracle)),
        "cm_no_reinflate_expanded": bool(np.array_equal(expanded, oracle)),
    }
    return {
        "n": n,
        "case": label,
        "live_k": live_k,
        "rows": 1 << n,
        "representation_code": reduced.final_output_representation_code,
        "output_vars_count": len(reduced.output_vars),
        **checks,
        "all_ok": all(checks.values()),
    }


def adversarial_kernel_checks() -> list[dict[str, object]]:
    cases: list[tuple[str, int, Expr, tuple[str, ...], dict[str, int]]] = [
        ("single_var", 1, Var(0), ("x0",), {}),
        ("constant_false", 4, And(Var(0), Not(Var(0))), ("x0", "x1", "x2", "x3"), {}),
        ("constant_true", 4, Or(Var(0), Not(Var(0))), ("x0", "x1", "x2", "x3"), {}),
        ("repeated", 4, Xor(Xor(Var(0), Var(1)), Xor(Var(0), Var(1))), ("x0", "x1", "x2", "x3"), {}),
        ("deep_not", 3, Not(Not(Not(Not(Not(Var(2)))))), ("x0", "x1", "x2"), {}),
        ("deep_256_chain", 8, mixed_chain(list(range(8)) * 32), tuple(f"x{i}" for i in range(8)), {}),
        ("imp_eqv_chain", 8, mixed_chain(range(8)), tuple(f"x{i}" for i in range(8)), {}),
        ("all_fixed", 6, mixed_chain(range(6)), tuple(), {f"x{i}": i & 1 for i in range(6)}),
    ]
    rows = []
    for label, n, expr, live_vars, fixed in cases:
        node = compile_expr_to_cm_ir(expr)
        recursive = eval_cm_node_bitset(node, live_vars, fixed=fixed)
        flat = eval_cm_node_flat(node, live_vars, fixed=fixed)
        oracle = eval_expr_tt(expr, n).reshape(-1)
        expected = 0
        for reduced_idx in range(1 << len(live_vars)):
            assignment = dict(fixed)
            for pos, name in enumerate(live_vars):
                assignment[name] = (reduced_idx >> (len(live_vars) - 1 - pos)) & 1
            full_idx = 0
            for i in range(n):
                full_idx = (full_idx << 1) | int(assignment[f"x{i}"])
            expected |= int(oracle[full_idx]) << reduced_idx
        rows.append(
            {
                "case": label,
                "n": n,
                "live_k": len(live_vars),
                "fixed_k": len(fixed),
                "flat_equals_recursive": flat == recursive,
                "flat_equals_oracle": flat == expected,
            }
        )
    return rows


def audit_dd_autoref() -> list[dict[str, object]]:
    from dd import autoref
    from cmbench.backends.robdd_dd import expr_to_dd_bdd

    rows = []
    for n, label, expr in [
        (8, "all_live_xor", xor_chain(range(8))),
        (9, "imp_eqv_chain", mixed_chain(range(9))),
        (10, "annihilating", And(Var(0), Not(Var(0)))),
    ]:
        oracle = eval_expr_tt(expr, n).reshape(-1)
        names = [f"x{i}" for i in range(n)]
        manager = autoref.BDD()
        manager.declare(*names)
        root = expr_to_dd_bdd(expr, manager, {name: name for name in names})
        actual = np.empty(1 << n, dtype=np.uint8)
        for idx in range(1 << n):
            assignment = {name: bool((idx >> (n - 1 - i)) & 1) for i, name in enumerate(names)}
            restricted = manager.let(assignment, root)
            actual[idx] = 1 if restricted == manager.true else 0
        rows.append({"n": n, "case": label, "rows": 1 << n, "ok": bool(np.array_equal(actual, oracle))})
        del root, manager
        gc.collect()
    return rows


def audit_bound_caches() -> list[dict[str, object]]:
    expr = mixed_chain(range(8))
    node = compile_expr_to_cm_ir(expr)
    vars_key = tuple(f"x{i}" for i in range(8))
    cm_prog = get_flat_program(node)
    raw_prog = get_expr_flat_program(expr)
    expected = eval_expr_bitset(expr, build_bitset_env(vars_key))
    assert eval_cm_node_flat(node, vars_key) == expected
    assert eval_expr_flat_bitset(expr, vars_key) == expected
    rows = []
    for label, prog in (("cm_flat", cm_prog), ("raw_flat", raw_prog)):
        op_slots = {slot for slot, _opcode, _args in prog.ops}
        templates = [bound[0] for bound in prog.bound_cache.values()]
        rows.append(
            {
                "program": label,
                "cache_entries": len(prog.bound_cache),
                "entry_arity": min((len(bound) for bound in prog.bound_cache.values()), default=0),
                "operation_slots_remain_unwritten": all(
                    template[slot] == 0 for template in templates for slot in op_slots
                ),
                "fresh_eval_matches": True,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="16,18,20,22,24")
    parser.add_argument("--tag", default="py313")
    args = parser.parse_args()
    sizes = [int(x) for x in args.sizes.split(",")]

    exhaustive = []
    for n in sizes:
        for label, expr in cases_for_n(n):
            row = audit_case(n, label, expr)
            print(json.dumps(row), flush=True)
            exhaustive.append(row)
            del expr
            gc.collect()
    adversarial = adversarial_kernel_checks()
    dd_rows = audit_dd_autoref()
    cache_rows = audit_bound_caches()

    write_csv(HERE / f"CM_audit_2026-07-21_{args.tag}_exhaustive.csv", exhaustive)
    write_csv(HERE / f"CM_audit_2026-07-21_{args.tag}_adversarial.csv", adversarial)
    write_csv(HERE / f"CM_audit_2026-07-21_{args.tag}_dd_autoref.csv", dd_rows)
    write_csv(HERE / f"CM_audit_2026-07-21_{args.tag}_bound_cache.csv", cache_rows)
    summary = {
        "exhaustive_cases": len(exhaustive),
        "exhaustive_rows_compared_per_method": sum(int(r["rows"]) for r in exhaustive),
        "exhaustive_failures": sum(not bool(r["all_ok"]) for r in exhaustive),
        "adversarial_failures": sum(
            not (bool(r["flat_equals_recursive"]) and bool(r["flat_equals_oracle"]))
            for r in adversarial
        ),
        "dd_failures": sum(not bool(r["ok"]) for r in dd_rows),
        "bound_cache_failures": sum(
            not bool(r["operation_slots_remain_unwritten"]) for r in cache_rows
        ),
    }
    print(json.dumps(summary, indent=2))
    if any(
        summary[k]
        for k in (
            "exhaustive_failures",
            "adversarial_failures",
            "dd_failures",
            "bound_cache_failures",
        )
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
