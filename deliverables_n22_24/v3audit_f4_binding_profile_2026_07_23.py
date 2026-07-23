"""Audit V3 isolation of ambient-n drift in the matched-scope Bitset control.

The same depth-4 formula is evaluated at ambient n=24 and n=32. Its true
support and FlatProgram are therefore identical; only the fixed-binding key
gains eight irrelevant ambient names. Timings split the cache-hit binder from
prebound operation evaluation.
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import random_expr
from cm_ir import compile_expr_to_cm_ir, materialize_hybrid_no_reinflate

TRIALS = 200
ROUNDS = 7
REPS = 300


def timed(fn) -> float:
    start = perf_counter()
    for _ in range(REPS):
        fn()
    return (perf_counter() - start) / REPS * 1e6


def eval_prebound(prog: bb.FlatProgram, template: list[int], full_mask: int) -> int:
    values = template.copy()
    for slot, opcode, args in prog.ops:
        if opcode == bb._FLAT_OP_AND:
            values[slot] = values[args[0]] & values[args[1]]
        elif opcode == bb._FLAT_OP_OR:
            values[slot] = values[args[0]] | values[args[1]]
        elif opcode == bb._FLAT_OP_XOR:
            values[slot] = values[args[0]] ^ values[args[1]]
        elif opcode == bb._FLAT_OP_NOT:
            values[slot] = (~values[args[0]]) & full_mask
        elif opcode == bb._FLAT_OP_IMP:
            values[slot] = ((~values[args[0]]) | values[args[1]]) & full_mask
        elif opcode == bb._FLAT_OP_EQV:
            values[slot] = (~(values[args[0]] ^ values[args[1]])) & full_mask
        else:
            raise AssertionError(opcode)
    return values[prog.root_slot]


def main() -> None:
    raw: list[dict[str, object]] = []
    for trial in range(TRIALS):
        expr = random_expr(
            24,
            np.random.default_rng(26_000_000 + 24 * 100_000 + 4 * 10_000 + trial),
            max_depth=4,
            p_unary=0.25,
        )
        node = compile_expr_to_cm_ir(expr)
        output_vars = tuple(node.vars)
        prog = bb.get_expr_flat_program(expr)
        reference = None
        for ambient_n in (24, 32):
            vars_all = tuple(f"x{i}" for i in range(ambient_n))
            fixed = {name: 0 for name in vars_all if name not in output_vars}
            template, full_mask = bb._bind_flat_program(prog, output_vars, fixed)
            expected = eval_prebound(prog, template, full_mask)
            if bb.eval_expr_flat_bitset(expr, output_vars, fixed=fixed) != expected:
                raise AssertionError("prebound/raw mismatch")
            cm_result = materialize_hybrid_no_reinflate(
                node,
                vars_all,
                fixed={},
                hybrid_threshold=16,
                allow_reduced_output=True,
                max_full_output_vars=16,
                flat_eval=True,
            )
            if cm_result.bits is None or int(cm_result.bits) != expected:
                raise AssertionError("CM/raw mismatch")
            if reference is None:
                reference = expected
            elif reference != expected:
                raise AssertionError("ambient size changed output")

            key = (output_vars, tuple(sorted(fixed.items())))

            def full_raw():
                return bb.eval_expr_flat_bitset(expr, output_vars, fixed=fixed)

            def bind_hit():
                return bb._bind_flat_program(prog, output_vars, fixed)

            def prebound_eval():
                return eval_prebound(prog, template, full_mask)

            def prekey_lookup():
                return prog.bound_cache.get(key)

            def key_sort_hash():
                return hash((output_vars, tuple(sorted(fixed.items()))))

            def cm_wrapper():
                return materialize_hybrid_no_reinflate(
                    node,
                    vars_all,
                    fixed={},
                    hybrid_threshold=16,
                    allow_reduced_output=True,
                    max_full_output_vars=16,
                    flat_eval=True,
                )

            funcs = {
                "full_raw_us": full_raw,
                "bind_hit_us": bind_hit,
                "prebound_eval_us": prebound_eval,
                "prekey_lookup_us": prekey_lookup,
                "key_sort_hash_us": key_sort_hash,
                "cm_wrapper_us": cm_wrapper,
            }
            samples = {name: [] for name in funcs}
            names = tuple(funcs)
            for round_index in range(ROUNDS):
                offset = (trial + ambient_n + round_index) % len(names)
                order = names[offset:] + names[:offset]
                for name in order:
                    samples[name].append(timed(funcs[name]))
            med = {name: statistics.median(values) for name, values in samples.items()}
            raw.append(
                {
                    "trial": trial,
                    "ambient_n": ambient_n,
                    "live_k": len(output_vars),
                    "fixed_count": len(fixed),
                    "program_slots": prog.n_slots,
                    "program_ops": len(prog.ops),
                    **med,
                    "full_minus_prebound_us": med["full_raw_us"] - med["prebound_eval_us"],
                }
            )
        if (trial + 1) % 50 == 0:
            print(f"{trial + 1}/{TRIALS} formulas", flush=True)

    summary: list[dict[str, object]] = []
    metrics = (
        "full_raw_us",
        "bind_hit_us",
        "prebound_eval_us",
        "prekey_lookup_us",
        "key_sort_hash_us",
        "cm_wrapper_us",
        "full_minus_prebound_us",
    )
    by_n = {
        ambient_n: [row for row in raw if row["ambient_n"] == ambient_n]
        for ambient_n in (24, 32)
    }
    medians = {
        ambient_n: {
            metric: statistics.median(float(row[metric]) for row in rows)
            for metric in metrics
        }
        for ambient_n, rows in by_n.items()
    }
    for ambient_n in (24, 32):
        row: dict[str, object] = {
            "ambient_n": ambient_n,
            "trials": len(by_n[ambient_n]),
            "live_k_median": statistics.median(int(item["live_k"]) for item in by_n[ambient_n]),
            "fixed_count_median": statistics.median(
                int(item["fixed_count"]) for item in by_n[ambient_n]
            ),
        }
        row.update({f"{metric}_median": value for metric, value in medians[ambient_n].items()})
        summary.append(row)

    delta_full = medians[32]["full_raw_us"] - medians[24]["full_raw_us"]
    delta_prebound = medians[32]["prebound_eval_us"] - medians[24]["prebound_eval_us"]
    delta_bind = medians[32]["bind_hit_us"] - medians[24]["bind_hit_us"]
    summary.append(
        {
            "ambient_n": "delta_32_minus_24",
            "trials": TRIALS,
            "live_k_median": "",
            "fixed_count_median": 8,
            "full_raw_us_median": delta_full,
            "bind_hit_us_median": delta_bind,
            "prebound_eval_us_median": delta_prebound,
            "prekey_lookup_us_median": (
                medians[32]["prekey_lookup_us"] - medians[24]["prekey_lookup_us"]
            ),
            "key_sort_hash_us_median": (
                medians[32]["key_sort_hash_us"] - medians[24]["key_sort_hash_us"]
            ),
            "cm_wrapper_us_median": medians[32]["cm_wrapper_us"] - medians[24]["cm_wrapper_us"],
            "full_minus_prebound_us_median": delta_full - delta_prebound,
        }
    )

    out = REPO / "deliverables_n22_24"
    with (out / "CM_V3AUDIT_F4_binding_profile_raw.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    with (out / "CM_V3AUDIT_F4_binding_profile_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(summary)


if __name__ == "__main__":
    main()
