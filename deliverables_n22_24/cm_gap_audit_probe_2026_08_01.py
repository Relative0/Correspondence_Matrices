from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import (
    FlatProgram,
    _FLAT_OP_AND,
    _FLAT_OP_EQV,
    _FLAT_OP_IMP,
    _FLAT_OP_NOT,
    _FLAT_OP_OR,
    _FLAT_OP_XOR,
    _eval_words,
    compile_expr_flat,
    eval_cm_node_words,
    eval_expr_words_bitset,
    get_flat_program,
)
from cm_expr_serde import expr_from_json, expr_to_json
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir
from cmbench.backends.robdd_dd import expr_to_dd_bdd, safe_bdd_node_count


DELIVERABLES = ROOT / "deliverables_n22_24"
CORPUS = DELIVERABLES / "v4audit_corpus_2026_07_24.jsonl"
LOCAL_RAW = DELIVERABLES / "CM_v4audit_packed_eval_raw.csv"
POD_RAW = DELIVERABLES / "CM_v4audit_packed_eval_raw_runpod.csv"
OUT = DELIVERABLES / "cm_gap_audit_probe_results_2026_08_01.json"


OPS = {And: "AND", Or: "OR", Xor: "XOR", Imp: "IMP", Eqv: "EQV"}
OPCODES = {
    "AND": _FLAT_OP_AND, "OR": _FLAT_OP_OR, "XOR": _FLAT_OP_XOR,
    "IMP": _FLAT_OP_IMP, "EQV": _FLAT_OP_EQV, "NOT": _FLAT_OP_NOT,
}


def timed(fn, repeats: int = 1, blocks: int = 5) -> float:
    samples = []
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        samples.append((time.perf_counter() - t0) / repeats)
    return min(samples)


def tree_nodes(expr) -> int:
    if isinstance(expr, Var):
        return 1
    if isinstance(expr, Not):
        return 1 + tree_nodes(expr.a)
    return 1 + tree_nodes(expr.a) + tree_nodes(expr.b)


def dag_nodes(expr) -> int:
    seen = set()
    stack = [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Not):
            stack.append(cur.a)
        elif not isinstance(cur, Var):
            stack.extend((cur.a, cur.b))
    return len(seen)


class IdMemoBuilder(CMIRBuilder):
    """Scratch-only version of build with identity memoization."""

    def __init__(self):
        super().__init__()
        self.expr_memo = {}

    def build(self, expr):
        cached = self.expr_memo.get(id(expr))
        if cached is not None:
            return cached
        node = super().build(expr)
        self.expr_memo[id(expr)] = node
        return node


def compile_memo(expr):
    return IdMemoBuilder().build(expr)


def shared_ladder(depth: int):
    cur = Xor(Var(0), Var(1))
    for level in range(depth):
        a = Var(2 + (2 * level) % 14)
        b = Var(2 + (2 * level + 1) % 14)
        cur = Or(And(cur, a), And(cur, b))
    return cur


def add_words(a, b):
    width = max(len(a), len(b))
    out = []
    carry = None
    for i in range(width):
        ai = a[i] if i < len(a) else None
        bi = b[i] if i < len(b) else None
        terms = [x for x in (ai, bi, carry) if x is not None]
        if not terms:
            out.append(None)
            carry = None
        elif len(terms) == 1:
            out.append(terms[0])
            carry = None
        elif len(terms) == 2:
            out.append(Xor(terms[0], terms[1]))
            carry = And(terms[0], terms[1])
        else:
            ab = Xor(ai, bi)
            out.append(Xor(ab, carry))
            carry = Or(And(ai, bi), And(ab, carry))
    if carry is not None:
        out.append(carry)
    return out


def multiplier_bits(nb: int, topology: str):
    rows = []
    for j in range(nb):
        rows.append([None] * j + [And(Var(i), Var(nb + j)) for i in range(nb)])
    if topology == "sequential":
        acc = rows[0]
        for row in rows[1:]:
            acc = add_words(acc, row)
        return acc
    while len(rows) > 1:
        nxt = []
        for i in range(0, len(rows), 2):
            nxt.append(add_words(rows[i], rows[i + 1]) if i + 1 < len(rows) else rows[i])
        rows = nxt
    return rows[0]


def compile_structural_cse(expr) -> FlatProgram:
    loads = []
    ops = []
    slot_by_key = {}
    key_by_id = {}

    def rec(cur):
        prior_key = key_by_id.get(id(cur))
        if prior_key is not None:
            return slot_by_key[prior_key], prior_key
        if isinstance(cur, Var):
            key = ("var", int(cur.i))
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                loads.append((slot, "var", f"x{cur.i}"))
                slot_by_key[key] = slot
        elif isinstance(cur, Not):
            child_slot, child_key = rec(cur.a)
            key = ("NOT", child_key)
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                ops.append((slot, OPCODES["NOT"], (child_slot,)))
                slot_by_key[key] = slot
        else:
            left_slot, left_key = rec(cur.a)
            right_slot, right_key = rec(cur.b)
            opname = OPS[type(cur)]
            key = (opname, left_key, right_key)
            if key not in slot_by_key:
                slot = len(loads) + len(ops)
                ops.append((slot, OPCODES[opname], (left_slot, right_slot)))
                slot_by_key[key] = slot
        key_by_id[id(cur)] = key
        return slot_by_key[key], key

    root_slot, _ = rec(expr)
    return FlatProgram(len(loads) + len(ops), root_slot, tuple(loads), tuple(ops))


def variance_audit(path: Path):
    rows = [r for r in csv.DictReader(path.open(newline="", encoding="utf-8")) if r["status"] == "ok"]
    sparse = [r for r in rows if r["family"] == "sparse_depth4"]
    by_id = defaultdict(list)
    live_k = {}
    for row in sparse:
        by_id[row["id"]].append(math.log(float(row["paired_ratio"])))
        live_k[row["id"]] = int(row["live_k"])
    groups = defaultdict(list)
    for ident, values in by_id.items():
        groups[live_k[ident]].append(
            {"id": ident, "mean": statistics.mean(values), "median": statistics.median(values), "within_var": statistics.variance(values)}
        )
    residual_ss_mean = 0.0
    residual_ss_median = 0.0
    residual_df = 0
    contributing_n = 0
    error_terms = []
    for values in groups.values():
        if len(values) <= 1:
            continue
        contributing_n += len(values)
        residual_df += len(values) - 1
        mean_center = statistics.mean(v["mean"] for v in values)
        median_center = statistics.mean(v["median"] for v in values)
        residual_ss_mean += sum((v["mean"] - mean_center) ** 2 for v in values)
        residual_ss_median += sum((v["median"] - median_center) ** 2 for v in values)
        error_terms.extend(v["within_var"] / len(by_id[v["id"]]) for v in values)
    all_formula_n = len(by_id)
    observed_var = residual_ss_mean / residual_df
    return {
        "file": path.name,
        "formula_count": all_formula_n,
        "contributing_formula_count": contributing_n,
        "residual_df": residual_df,
        "group_counts": {str(k): len(v) for k, v in sorted(groups.items())},
        "sigma_formula_mean_df_corrected": math.sqrt(observed_var),
        "sigma_formula_median_df_corrected": math.sqrt(residual_ss_median / residual_df),
        "sigma_biased_divide_by_all_formulas": math.sqrt(residual_ss_median / all_formula_n),
        "sigma_latent_moments": math.sqrt(max(0.0, observed_var - statistics.mean(error_terms))),
        "repeat_counts": dict(Counter(int(r["repeat"]) for r in rows)),
    }


def run_compile_probe():
    rows = []
    for depth in range(0, 11):
        expr = shared_ladder(depth)
        serialized = expr_from_json(expr_to_json(expr))
        row = {
            "family": "shared_ladder",
            "depth": depth,
            "dag_nodes": dag_nodes(expr),
            "tree_nodes": tree_nodes(expr),
            "unfold_factor": tree_nodes(expr) / dag_nodes(expr),
            "serialized_dag_nodes": dag_nodes(serialized),
        }
        row["compile_current_us"] = timed(lambda: compile_expr_to_cm_ir(expr), blocks=3) * 1e6
        row["compile_idmemo_us"] = timed(lambda: compile_memo(expr), blocks=3) * 1e6
        row["compile_serialized_current_us"] = timed(lambda: compile_expr_to_cm_ir(serialized), blocks=3) * 1e6
        row["compile_serialized_idmemo_us"] = timed(lambda: compile_memo(serialized), blocks=3) * 1e6
        node = compile_memo(expr)
        row["cm_ops"] = len(get_flat_program(node).ops)
        rows.append(row)
    return rows


def run_multiplier_probe():
    rows = []
    cases = []
    for topology in ("sequential", "balanced"):
        for nb in (4, 5, 6, 7, 8):
            bits = multiplier_bits(nb, topology)
            for bit in sorted({nb - 2, nb - 1, nb}):
                if 0 <= bit < len(bits) and bits[bit] is not None:
                    cases.append((topology, nb, bit, bits[bit]))
    for topology, nb, bit, expr in cases:
        support = tuple(f"x{i}" for i in range(2 * nb))
        node = compile_expr_to_cm_ir(expr)
        raw_prog = compile_expr_flat(expr)
        cse_prog = compile_structural_cse(expr)
        cm_prog = get_flat_program(node)
        cm_val = eval_cm_node_words(node, support, fixed={})
        raw_val = eval_expr_words_bitset(expr, support, fixed={})
        cse_val = _eval_words(cse_prog, support, {})
        if not (cm_val == raw_val == cse_val):
            raise AssertionError((topology, nb, bit, "packed mismatch"))
        repeats = 100 if nb <= 6 else 20
        rows.append(
            {
                "topology": topology,
                "nb": nb,
                "output_bit": bit,
                "dag_nodes": dag_nodes(expr),
                "tree_nodes": tree_nodes(expr),
                "cm_ops": len(cm_prog.ops),
                "raw_ops": len(raw_prog.ops),
                "cse_ops": len(cse_prog.ops),
                "raw_over_cm_ops": len(raw_prog.ops) / max(1, len(cm_prog.ops)),
                "cse_over_cm_ops": len(cse_prog.ops) / max(1, len(cm_prog.ops)),
                "cm_eval_us": timed(lambda: eval_cm_node_words(node, support, fixed={}), repeats=repeats) * 1e6,
                "raw_eval_us": timed(lambda: eval_expr_words_bitset(expr, support, fixed={}), repeats=repeats) * 1e6,
                "cse_eval_us": timed(lambda: _eval_words(cse_prog, support, {}), repeats=repeats) * 1e6,
                "packed_equal": True,
            }
        )
    return rows


def run_repeat_probe():
    corpus = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    results = []
    for item in corpus:
        if item["explicit_packed_policy"] != "run":
            continue
        expr = expr_from_json(item["expression"])
        support = tuple(item["semantic_support"])
        fixed = {f"x{i}": 0 for i in range(item["nominal_n"]) if f"x{i}" not in support}
        node = compile_expr_to_cm_ir(expr)
        cm_fn = lambda: eval_cm_node_words(node, support, fixed=fixed)
        bs_fn = lambda: eval_expr_words_bitset(expr, support, fixed=fixed)
        if cm_fn() != bs_fn():
            raise AssertionError(item["id"])
        for repeat in (50, 200):
            ratios = []
            for rnd in range(6):
                if rnd % 2:
                    cm_s = timed(cm_fn, repeat, blocks=1)
                    bs_s = timed(bs_fn, repeat, blocks=1)
                else:
                    bs_s = timed(bs_fn, repeat, blocks=1)
                    cm_s = timed(cm_fn, repeat, blocks=1)
                ratios.append(cm_s / bs_s)
            results.append(
                {
                    "id": item["id"], "family": item["family"], "live_k": item["semantic_live_k"],
                    "repeat": repeat, "median_ratio": statistics.median(ratios),
                }
            )
    paired = defaultdict(dict)
    for row in results:
        paired[row["id"]][row["repeat"]] = row["median_ratio"]
    log_changes = [math.log(v[200] / v[50]) for v in paired.values()]
    return {
        "rows": results,
        "formula_count": len(paired),
        "geomean_ratio_200_over_50": math.exp(statistics.mean(log_changes)),
        "median_ratio_200_over_50": statistics.median(math.exp(x) for x in log_changes),
        "sign_flips": sum((v[50] < 1) != (v[200] < 1) for v in paired.values()),
    }


def run_bdd_probe():
    from dd.autoref import BDD

    rows = []
    for nb in (4, 5, 6, 7, 8):
        bits = multiplier_bits(nb, "balanced")
        orders = {
            "blocked": [f"x{i}" for i in range(2 * nb)],
            "interleaved": [f"x{i + offset}" for i in range(nb) for offset in (0, nb)],
        }
        for bit, expr in enumerate(bits):
            if expr is None:
                continue
            for order_name, order in orders.items():
                manager = BDD()
                manager.declare(*order)
                t0 = time.perf_counter()
                root = expr_to_dd_bdd(expr, manager, {name: name for name in order})
                build_us = (time.perf_counter() - t0) * 1e6
                rows.append(
                    {
                        "nb": nb,
                        "output_bit": bit,
                        "order": order_name,
                        "nodes": safe_bdd_node_count(manager, root),
                        "build_us_autoref": build_us,
                        "packed_truth_table_bytes": (1 << (2 * nb)) // 8,
                    }
                )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-repeat", action="store_true")
    args = parser.parse_args()
    out = {
        "variance": [variance_audit(LOCAL_RAW), variance_audit(POD_RAW)],
        "compile_scaling": run_compile_probe(),
        "multipliers": run_multiplier_probe(),
        "bdd_multiplier_bits": run_bdd_probe(),
    }
    if not args.skip_repeat:
        out["repeat_probe"] = run_repeat_probe()
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "variance": out["variance"],
        "compile_last": out["compile_scaling"][-1],
        "multiplier_rows": len(out["multipliers"]),
        "repeat_summary": {k: v for k, v in out.get("repeat_probe", {}).items() if k != "rows"},
    }, indent=2))


if __name__ == "__main__":
    main()
