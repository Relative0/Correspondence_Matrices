"""Audit V3 adversarial checks for the numpy-words FlatProgram evaluator.

This extends the Fable verifier with cache eviction, exact n=5/6 dispatch,
all-fixed bindings, repeated operands, and variadic/multi-step opcode plans.
Each equality compares the complete packed output, so it exhausts all rows at
the evaluated support width.
"""
from __future__ import annotations

import csv
import platform
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import And, Eqv, Imp, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir


def record(rows: list[dict[str, object]], case: str, condition: bool, detail: str) -> None:
    rows.append({"case": case, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{case}: {detail}")


def eval_flat_program_bigint(
    prog: bb.FlatProgram, vars_key: tuple[str, ...], fixed: dict[str, int]
) -> int:
    template, full_mask = bb._bind_flat_program(prog, vars_key, fixed)
    values = template.copy()
    for slot, opcode, args in prog.ops:
        if opcode == bb._FLAT_OP_NOT:
            values[slot] = (~values[args[0]]) & full_mask
        elif opcode == bb._FLAT_OP_AND:
            acc = values[args[0]]
            for arg in args[1:]:
                acc &= values[arg]
            values[slot] = acc
        elif opcode == bb._FLAT_OP_OR:
            acc = values[args[0]]
            for arg in args[1:]:
                acc |= values[arg]
            values[slot] = acc
        elif opcode == bb._FLAT_OP_XOR:
            acc = values[args[0]]
            for arg in args[1:]:
                acc ^= values[arg]
            values[slot] = acc
        elif opcode == bb._FLAT_OP_IMP:
            values[slot] = ((~values[args[0]]) | values[args[1]]) & full_mask
        elif opcode == bb._FLAT_OP_EQV:
            values[slot] = (~(values[args[0]] ^ values[args[1]])) & full_mask
        else:
            raise AssertionError(f"unexpected opcode {opcode}")
    return values[prog.root_slot]


def main() -> None:
    rows: list[dict[str, object]] = []

    # A deliberately non-canonical FlatProgram: repeated args, fanout, variadic
    # AND/OR/XOR, and the two-step IMP/EQV implementations all share scratch.
    loads = tuple((i, "var", f"x{i}") for i in range(6))
    ops = (
        (6, bb._FLAT_OP_XOR, (0, 1, 1)),
        (7, bb._FLAT_OP_IMP, (6, 2)),
        (8, bb._FLAT_OP_EQV, (7, 6)),
        (9, bb._FLAT_OP_AND, (8, 7, 6, 6, 3)),
        (10, bb._FLAT_OP_OR, (9, 8, 7, 4)),
        (11, bb._FLAT_OP_XOR, (10, 9, 8, 5)),
    )
    prog = bb.FlatProgram(12, 11, loads, ops)
    steps, n_buffers, _root_loc, _load_info = bb._compute_word_plan(prog)
    for index, (out, _opcode, arg_locs) in enumerate(steps):
        input_buffers = {value for tag, value in arg_locs if tag == "s"}
        record(
            rows,
            f"plan_no_alias_op_{index}",
            out not in input_buffers,
            f"out={out}; inputs={sorted(input_buffers)}; buffers={n_buffers}",
        )
    vars6 = tuple(f"x{i}" for i in range(6))
    record(
        rows,
        "custom_program_complete_output",
        bb._eval_words(prog, vars6, {}) == eval_flat_program_bigint(prog, vars6, {}),
        "repeated/variadic/IMP/EQV packed equality at 64 rows",
    )

    # Public entry points: prove the exact fallback boundary without timing.
    expr5 = Xor(And(Var(0), Var(1)), Eqv(Var(2), Imp(Var(3), Var(4))))
    node5 = compile_expr_to_cm_ir(expr5)
    vars5 = tuple(f"x{i}" for i in range(5))
    cm_prog5 = bb.get_flat_program(node5)
    raw_prog5 = bb.get_expr_flat_program(expr5)
    ref5_cm = bb.eval_cm_node_flat(node5, vars5)
    ref5_raw = bb.eval_expr_flat_bitset(expr5, vars5)
    got5_cm = bb.eval_cm_node_words(node5, vars5)
    got5_raw = bb.eval_expr_words_bitset(expr5, vars5)
    record(rows, "n5_cm_fallback_exact", got5_cm == ref5_cm and cm_prog5.word_plan is None,
           "complete 32-row equality; word plan remains unbuilt")
    record(rows, "n5_raw_fallback_exact", got5_raw == ref5_raw and raw_prog5.word_plan is None,
           "complete 32-row equality; word plan remains unbuilt")

    expr6 = Xor(expr5, Var(5))
    node6 = compile_expr_to_cm_ir(expr6)
    cm_prog6 = bb.get_flat_program(node6)
    raw_prog6 = bb.get_expr_flat_program(expr6)
    record(rows, "n6_cm_words_exact",
           bb.eval_cm_node_words(node6, vars6) == bb.eval_cm_node_flat(node6, vars6)
           and cm_prog6.word_plan is not None,
           "complete 64-row equality; word plan built")
    record(rows, "n6_raw_words_exact",
           bb.eval_expr_words_bitset(expr6, vars6) == bb.eval_expr_flat_bitset(expr6, vars6)
           and raw_prog6.word_plan is not None,
           "complete 64-row equality; word plan built")

    # Every expression variable fixed, with six dummy live axes retaining word width.
    dummy_vars = tuple(f"x{i}" for i in range(10, 16))
    fixed_all = {f"x{i}": i & 1 for i in range(6)}
    record(rows, "all_fixed_cm",
           bb.eval_cm_node_words(node6, dummy_vars, fixed=fixed_all)
           == bb.eval_cm_node_flat(node6, dummy_vars, fixed=fixed_all),
           "all actual variables fixed; complete 64-row constant output")
    record(rows, "all_fixed_raw",
           bb.eval_expr_words_bitset(expr6, dummy_vars, fixed=fixed_all)
           == bb.eval_expr_flat_bitset(expr6, dummy_vars, fixed=fixed_all),
           "all actual variables fixed; complete 64-row constant output")

    # Thrash the global env cache (>4 keys) and per-program scratch widths (>2).
    expr9 = Xor(
        And(Xor(Var(0), Var(1)), Or(Var(2), Var(3))),
        Eqv(Imp(Var(4), Var(5)), Xor(Var(6), And(Var(7), Var(8)))),
    )
    node9 = compile_expr_to_cm_ir(expr9)
    all9 = tuple(f"x{i}" for i in range(9))
    sequences = [
        all9[:6],
        all9[:7],
        all9[:8],
        all9,
        tuple(reversed(all9[:6])),
        tuple(reversed(all9[:7])),
        (all9[1], all9[0], *all9[2:6]),
    ]
    bb.clear_words_env_cache()
    cm_prog9 = bb.get_flat_program(node9)
    raw_prog9 = bb.get_expr_flat_program(expr9)
    cm_prog9.word_scratch.clear()
    raw_prog9.word_scratch.clear()
    for round_index in range(3):
        for seq_index, live in enumerate(sequences):
            fixed = {name: (round_index + i) & 1 for i, name in enumerate(all9) if name not in live}
            cm_words = bb.eval_cm_node_words(node9, live, fixed=fixed)
            raw_words = bb.eval_expr_words_bitset(expr9, live, fixed=fixed)
            cm_ref = bb.eval_cm_node_flat(node9, live, fixed=fixed)
            raw_ref = bb.eval_expr_flat_bitset(expr9, live, fixed=fixed)
            record(rows, f"thrash_cm_r{round_index}_s{seq_index}", cm_words == cm_ref,
                   f"k={len(live)} packed equality")
            record(rows, f"thrash_raw_r{round_index}_s{seq_index}", raw_words == raw_ref,
                   f"k={len(live)} packed equality")
            record(rows, f"thrash_cross_r{round_index}_s{seq_index}", cm_words == raw_words,
                   f"k={len(live)} CM/raw agreement")
    cache_info = bb._build_words_env_cached.cache_info()
    record(rows, "env_cache_capacity", cache_info.currsize == bb._WORDS_ENV_CACHE_MAX,
           f"cache_info={cache_info}")
    record(rows, "cm_scratch_capacity",
           len(cm_prog9.word_scratch) == bb._WORDS_SCRATCH_WIDTHS_MAX,
           f"widths={list(cm_prog9.word_scratch)}")
    record(rows, "raw_scratch_capacity",
           len(raw_prog9.word_scratch) == bb._WORDS_SCRATCH_WIDTHS_MAX,
           f"widths={list(raw_prog9.word_scratch)}")

    tag = f"py{sys.version_info.major}{sys.version_info.minor}"
    output = REPO / "deliverables_n22_24" / f"CM_V3AUDIT_F1_words_adversarial_{tag}.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("case", "passed", "detail"))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{platform.python_version()}: {len(rows)} checks, all passed -> {output.name}")


if __name__ == "__main__":
    main()
