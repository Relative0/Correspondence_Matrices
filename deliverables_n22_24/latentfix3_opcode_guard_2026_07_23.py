"""Latent-fix 3 proof: explicit EQV dispatch + raise on unknown opcodes.

1) Byte-identity on the six known opcodes: in-script verbatim copies of the OLD
   catch-all dispatch loops (bigint flat and numpy words) are run against the
   NEW guarded kernels on a fuzz set covering all six opcodes; every packed
   result must be equal, and both must match the recursive bigint reference.
2) Refusal: a hand-built FlatProgram with opcode 6 raises ValueError in
   eval_expr_flat_bitset, eval_cm_node_flat, and _eval_words (it executed as
   EQV before this fix).
3) Perf formality: paired old-vs-new timing on one medium formula, 7
   interleaved rounds, medians recorded.

Writes CM_latentfix3_opcode_guard.csv; exits nonzero on failure.
"""
from __future__ import annotations

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bitset_backend import (
    FlatProgram,
    _FLAT_OP_AND,
    _FLAT_OP_EQV,
    _FLAT_OP_IMP,
    _FLAT_OP_NOT,
    _FLAT_OP_OR,
    _FLAT_OP_XOR,
    _bind_flat_program,
    _build_words_env_cached,
    _compute_word_plan,
    _eval_words,
    _words_const,
    build_bitset_env,
    eval_cm_node_flat,
    eval_expr_bitset,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
    get_expr_flat_program,
)
from cm_exprlib import Not, Var, random_expr
from cm_ir import compile_expr_to_cm_ir

OUT = Path(__file__).resolve().parent / "CM_latentfix3_opcode_guard.csv"


def _eval_flat_old(prog: FlatProgram, vars_all, fixed=None) -> int:
    """Verbatim pre-fix eval_expr_flat_bitset loop (catch-all EQV else)."""
    template, full_mask = _bind_flat_program(prog, tuple(vars_all), fixed or {})
    values = template.copy()
    release_dead = bool(len(vars_all) >= 18 and prog.n_slots >= 64)
    for op_index, (slot, opcode, arg_slots) in enumerate(prog.ops):
        if opcode == _FLAT_OP_AND:
            values[slot] = values[arg_slots[0]] & values[arg_slots[1]]
        elif opcode == _FLAT_OP_OR:
            values[slot] = values[arg_slots[0]] | values[arg_slots[1]]
        elif opcode == _FLAT_OP_XOR:
            values[slot] = values[arg_slots[0]] ^ values[arg_slots[1]]
        elif opcode == _FLAT_OP_NOT:
            values[slot] = (~values[arg_slots[0]]) & full_mask
        elif opcode == _FLAT_OP_IMP:
            values[slot] = ((~values[arg_slots[0]]) | values[arg_slots[1]]) & full_mask
        else:  # _FLAT_OP_EQV  (pre-fix catch-all)
            values[slot] = (~(values[arg_slots[0]] ^ values[arg_slots[1]])) & full_mask
        if release_dead:
            for dead_slot in prog.release_after[op_index]:
                values[dead_slot] = None
    return values[prog.root_slot]


def _eval_words_old(prog: FlatProgram, vars_key, fixed_map) -> int:
    """Verbatim pre-fix _eval_words loop (catch-all EQV else), shared scratch."""
    if prog.word_plan is None:
        prog.word_plan = _compute_word_plan(prog)
    steps, n_buffers, root_loc, load_info = prog.word_plan
    n_words = (1 << len(vars_key)) // 64
    env = _build_words_env_cached(vars_key)
    scratch = prog.word_scratch.get(n_words)
    if scratch is None:
        scratch = [np.empty(n_words, dtype="<u8") for _ in range(n_buffers)]
        prog.word_scratch[n_words] = scratch

    def resolve(loc):
        tag, x = loc
        if tag == "s":
            return scratch[x]
        kind, payload = load_info[x]
        if kind == "const":
            return _words_const(n_words, int(payload))
        if payload in fixed_map:
            return _words_const(n_words, int(bool(fixed_map[payload])))
        return env[payload]

    for out, opcode, arg_locs in steps:
        dst = scratch[out]
        a0 = resolve(arg_locs[0])
        if opcode == _FLAT_OP_NOT:
            np.bitwise_not(a0, out=dst)
            continue
        a1 = resolve(arg_locs[1]) if len(arg_locs) > 1 else None
        if opcode == _FLAT_OP_AND:
            np.bitwise_and(a0, a1, out=dst)
            for extra in arg_locs[2:]:
                np.bitwise_and(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_OR:
            np.bitwise_or(a0, a1, out=dst)
            for extra in arg_locs[2:]:
                np.bitwise_or(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_XOR:
            np.bitwise_xor(a0, a1, out=dst)
            for extra in arg_locs[2:]:
                np.bitwise_xor(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_IMP:
            np.bitwise_not(a0, out=dst)
            np.bitwise_or(dst, a1, out=dst)
        else:  # _FLAT_OP_EQV  (pre-fix catch-all)
            np.bitwise_xor(a0, a1, out=dst)
            np.bitwise_not(dst, out=dst)
    return int.from_bytes(resolve(root_loc).tobytes(), "little")


def main() -> int:
    rng = np.random.default_rng(20260723)
    rows = []
    failures = 0

    # 1) Byte-identity fuzz, n=8..16, all six opcodes covered collectively.
    opcodes_seen = set()
    for n in range(8, 17, 2):
        names = tuple(f"x{i}" for i in range(n))
        env = build_bitset_env(names)
        for expr_index in range(8):
            expr = random_expr(n, rng, max_depth=6, p_unary=0.3)
            prog = get_expr_flat_program(expr)
            opcodes_seen.update(op for _slot, op, _args in prog.ops)
            ref = int(eval_expr_bitset(expr, env))
            new_flat = int(eval_expr_flat_bitset(expr, names))
            old_flat = int(_eval_flat_old(prog, names))
            new_words = int(eval_expr_words_bitset(expr, names))
            old_words = int(_eval_words_old(prog, names, {}))
            ok = ref == new_flat == old_flat == new_words == old_words
            failures += 0 if ok else 1
            rows.append(
                {
                    "check": "byte_identity",
                    "n_vars": n,
                    "expr_index": expr_index,
                    "detail": "",
                    "ok": ok,
                }
            )
    all_ops_covered = opcodes_seen >= {0, 1, 2, 3, 4, 5}
    failures += 0 if all_ops_covered else 1
    rows.append(
        {
            "check": "opcode_coverage",
            "n_vars": "",
            "expr_index": "",
            "detail": sorted(opcodes_seen),
            "ok": all_ops_covered,
        }
    )

    # 2) Unknown opcode raises in all three kernels.
    bad = FlatProgram(2, 1, ((0, "var", "x0"),), ((1, 6, (0, 0)),))
    raised = {}
    bad_expr = Not(Var(0))
    object.__setattr__(bad_expr, "_bitset_flat_program", bad)
    try:
        eval_expr_flat_bitset(bad_expr, ("x0",))
        raised["eval_expr_flat_bitset"] = False
    except ValueError:
        raised["eval_expr_flat_bitset"] = True
    bad_node = compile_expr_to_cm_ir(Not(Var(0)))
    object.__setattr__(bad_node, "_flat_program", bad)
    try:
        eval_cm_node_flat(bad_node, ("x0",))
        raised["eval_cm_node_flat"] = False
    except ValueError:
        raised["eval_cm_node_flat"] = True
    finally:
        object.__setattr__(bad_node, "_flat_program", None)
    try:
        _eval_words(bad, tuple(f"x{i}" for i in range(6)), {})
        raised["_eval_words"] = False
    except ValueError:
        raised["_eval_words"] = True
    for kernel, did_raise in raised.items():
        failures += 0 if did_raise else 1
        rows.append(
            {"check": "unknown_opcode_raises", "n_vars": "", "expr_index": "", "detail": kernel, "ok": did_raise}
        )

    # 3) Perf formality: one medium formula, 7 interleaved rounds, medians.
    n = 18
    names = tuple(f"x{i}" for i in range(n))
    expr = random_expr(n, rng, max_depth=9, p_unary=0.3)
    prog = get_expr_flat_program(expr)
    eval_expr_words_bitset(expr, names)  # warm caches/plans
    _eval_words_old(prog, names, {})
    eval_expr_flat_bitset(expr, names)
    _eval_flat_old(prog, names)
    REPEAT = 60
    variants = {
        "words_new": lambda: eval_expr_words_bitset(expr, names),
        "words_old": lambda: _eval_words_old(prog, names, {}),
        "flat_new": lambda: eval_expr_flat_bitset(expr, names),
        "flat_old": lambda: _eval_flat_old(prog, names),
    }
    times = {k: [] for k in variants}
    order = list(variants)
    for round_index in range(16):
        # Alternate execution order so slow drift cannot systematically favor
        # whichever variant runs later in the round.
        for k in order if round_index % 2 == 0 else reversed(order):
            fn = variants[k]
            t0 = time.perf_counter()
            for _ in range(REPEAT):
                fn()
            times[k].append((time.perf_counter() - t0) / REPEAT)
    medians = {k: statistics.median(v) for k, v in times.items()}
    mins = {k: min(v) for k, v in times.items()}
    for k in variants:
        rows.append({"check": "perf_median_s", "n_vars": n, "expr_index": "", "detail": k, "ok": medians[k]})
        rows.append({"check": "perf_min_s", "n_vars": n, "expr_index": "", "detail": k, "ok": mins[k]})
    words_ratio = mins["words_new"] / mins["words_old"]
    flat_ratio = mins["flat_new"] / mins["flat_old"]
    rows.append({"check": "perf_ratio_new_over_old", "n_vars": n, "expr_index": "", "detail": "words", "ok": round(words_ratio, 4)})
    rows.append({"check": "perf_ratio_new_over_old", "n_vars": n, "expr_index": "", "detail": "flat", "ok": round(flat_ratio, 4)})

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"failures={failures} opcode_coverage={sorted(opcodes_seen)} raised={raised} "
        f"perf_ratio words={words_ratio:.4f} flat={flat_ratio:.4f} -> {OUT.name}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
