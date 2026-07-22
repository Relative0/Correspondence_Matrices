"""Fable audit: adversarial verification of last-use slot freeing.

Forces release_dead=True at small n by patching the gate constants, then
exhaustively oracle-checks diverse structures, repeated-call template integrity,
and rebinding across different (vars_key, fixed) keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
sys.path.insert(0, str(REPO))

import bitset_backend as bb
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
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, random_expr
from cm_ir import compile_expr_to_cm_ir

# Force the freeing branch on for every program, no matter how small.
bb._FLAT_FREE_MIN_VARS = 0
bb._FLAT_FREE_MIN_SLOTS = 0

failures = []
checks = 0


def check(label, cond):
    global checks
    checks += 1
    if not cond:
        failures.append(label)
        print("FAIL:", label)


def oracle_bits(expr, n):
    tt = eval_expr_tt(expr, n).astype(np.uint8, copy=False).reshape(-1)
    out = 0
    for idx, v in enumerate(tt):
        if v:
            out |= 1 << idx
    return out


# --- 1. Structured adversarial cases: shared subtrees, wide fan-out, repeated args ---
def shared_fanout(n):
    """One shared subexpression consumed by many ops spread across the program."""
    shared = Xor(Var(0), Var(1))
    out = shared
    for i in range(2, n):
        out = And(Or(out, shared), Xor(Var(i), shared))
    return out


def diamond(n):
    """Deep diamond DAG after CM interning: s used at top and bottom."""
    s = And(Var(0), Var(1))
    left = s
    for i in range(2, n, 2):
        left = Or(left, Var(i))
    right = s
    for i in range(3, n, 2):
        right = Xor(right, Var(i))
    return Eqv(And(left, right), s)


def self_op(n):
    """Ops whose args repeat the same slot."""
    a = Xor(Var(0), Var(1))
    return Or(Eqv(a, a), And(Xor(a, a), Var(n - 1)))


structured = []
for n in (4, 6, 8, 10):
    structured += [
        (f"shared_fanout_n{n}", n, shared_fanout(n)),
        (f"diamond_n{n}", n, diamond(n)),
        (f"self_op_n{n}", n, self_op(n)),
    ]

for label, n, expr in structured:
    vars_all = tuple(f"x{i}" for i in range(n))
    exp = oracle_bits(expr, n)
    node = compile_expr_to_cm_ir(expr)
    check(f"{label}/raw_flat_free", eval_expr_flat_bitset(expr, vars_all, free_dead_slots=True) == exp)
    check(f"{label}/raw_flat_keep", eval_expr_flat_bitset(expr, vars_all, free_dead_slots=False) == exp)
    check(f"{label}/cm_flat_free", eval_cm_node_flat(node, vars_all, free_dead_slots=True) == exp)
    check(f"{label}/cm_flat_keep", eval_cm_node_flat(node, vars_all, free_dead_slots=False) == exp)
    # Repeated calls: cached bound template must not be corrupted by prior releases.
    for repeat in range(3):
        check(f"{label}/repeat{repeat}", eval_cm_node_flat(node, vars_all, free_dead_slots=True) == exp)

# --- 2. Random fuzz with mixed fixed bindings and rebinding of cached programs ---
rng = np.random.default_rng(57721)
for trial in range(400):
    n = int(rng.integers(3, 9))
    expr = random_expr(n, rng, max_depth=int(rng.integers(3, 8)), p_unary=0.3)
    node = compile_expr_to_cm_ir(expr)
    vars_all = tuple(f"x{i}" for i in range(n))
    tt = eval_expr_tt(expr, n).astype(np.uint8, copy=False).reshape(-1)
    exp_full = 0
    for idx, v in enumerate(tt):
        if v:
            exp_full |= 1 << idx
    check(f"fuzz{trial}/raw_full", eval_expr_flat_bitset(expr, vars_all, free_dead_slots=True) == exp_full)
    check(f"fuzz{trial}/cm_full", eval_cm_node_flat(node, vars_all, free_dead_slots=True) == exp_full)

    # Random fixed subset: rebind the SAME cached FlatProgram with a different key.
    k_fix = int(rng.integers(0, n))
    fixed_names = list(rng.choice(n, size=k_fix, replace=False))
    fixed = {f"x{i}": int(rng.integers(0, 2)) for i in fixed_names}
    live = tuple(v for v in vars_all if v not in fixed)
    # reference: recursive CM evaluator (independently verified vs oracle above at full arity)
    ref = eval_cm_node_bitset(node, live, fixed=fixed)
    got_cm = eval_cm_node_flat(node, live, fixed=fixed, free_dead_slots=True)
    got_raw = eval_expr_flat_bitset(expr, live, fixed=fixed, free_dead_slots=True)
    check(f"fuzz{trial}/cm_fixed", got_cm == ref)
    check(f"fuzz{trial}/raw_fixed", got_raw == ref)
    # Direct oracle check of the reduced scope
    exp_red = 0
    nlive = len(live)
    for ridx in range(1 << nlive):
        assignment = dict(fixed)
        for pos, name in enumerate(live):
            assignment[name] = (ridx >> (nlive - 1 - pos)) & 1
        fidx = 0
        for i in range(n):
            fidx = (fidx << 1) | int(assignment[f"x{i}"])
        exp_red |= int(tt[fidx]) << ridx
    check(f"fuzz{trial}/cm_fixed_oracle", got_cm == exp_red)
    # Immediately re-evaluate full arity again: template integrity after rebinding
    check(f"fuzz{trial}/cm_full_again", eval_cm_node_flat(node, vars_all, free_dead_slots=True) == exp_full)

# --- 3. Bound-cache template integrity after release-heavy usage ---
expr = shared_fanout(8)
node = compile_expr_to_cm_ir(expr)
vars_all = tuple(f"x{i}" for i in range(8))
prog = get_flat_program(node)
_ = eval_cm_node_flat(node, vars_all, free_dead_slots=True)
for (key, (template, mask)) in prog.bound_cache.items():
    check("template_no_none", all(v is not None for v in template))

# --- 4. release_after static sanity on real programs: no slot read after release ---
def audit_schedule(prog):
    released_at = {}
    for op_index, dead in enumerate(prog.release_after):
        for s in dead:
            released_at[s] = op_index
    for op_index, (slot, _opc, args) in enumerate(prog.ops):
        for a in args:
            if a in released_at and released_at[a] < op_index:
                return False
    if prog.root_slot in released_at:
        return False
    return True


for label, n, expr in structured:
    node = compile_expr_to_cm_ir(expr)
    check(f"{label}/schedule_cm", audit_schedule(get_flat_program(node)))
    check(f"{label}/schedule_raw", audit_schedule(get_expr_flat_program(expr)))

rng2 = np.random.default_rng(31415)
for trial in range(200):
    n = int(rng2.integers(3, 12))
    expr = random_expr(n, rng2, max_depth=int(rng2.integers(4, 9)), p_unary=0.3)
    node = compile_expr_to_cm_ir(expr)
    check(f"sched{trial}/cm", audit_schedule(get_flat_program(node)))
    check(f"sched{trial}/raw", audit_schedule(get_expr_flat_program(expr)))

print(f"\nTOTAL checks: {checks}, failures: {len(failures)}")
if failures:
    sys.exit(1)
print("ALL PASS (release forced on for every program)")
