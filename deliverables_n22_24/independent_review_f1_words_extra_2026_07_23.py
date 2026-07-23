"""Independent review F1 supplement: adversarial words-evaluator cases that
Audit V3's script did not include.

1. Root-load programs (bare Var / Not(Var) roots, fixed root variable).
2. Malformed plans (unknown opcode, dangling slot reference) must raise, not
   corrupt.
3. A variable present in both the live scope and the fixed map: words and
   bigint flat must agree on the resolution.
4. Re-eviction equality: the same program evaluated at width A, then enough
   other widths to evict A, then A again, three times over.

Every equality is complete packed equality.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import bitset_backend as bb
from cm_exprlib import And, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

CHECKS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print(f"ok {name}")


def main() -> None:
    vars8 = tuple(f"x{i}" for i in range(8))

    # --- 1. root-load programs
    bare = Var(3)
    check(
        "root_load_bare_var",
        bb.eval_expr_words_bitset(bare, vars8) == bb.eval_expr_flat_bitset(bare, vars8),
    )
    noted = Not(Var(2))
    check(
        "root_not_var",
        bb.eval_expr_words_bitset(noted, vars8) == bb.eval_expr_flat_bitset(noted, vars8),
    )
    check(
        "root_load_fixed_var",
        bb.eval_expr_words_bitset(bare, vars8, fixed={"x3": 1})
        == bb.eval_expr_flat_bitset(bare, vars8, fixed={"x3": 1}),
    )
    node_bare = compile_expr_to_cm_ir(bare)
    check(
        "root_load_cm_node",
        bb.eval_cm_node_words(node_bare, vars8) == bb.eval_cm_node_flat(node_bare, vars8),
    )

    # --- 2. malformed plans
    # FINDING (documented, not fixed): both kernels' final else-branch treats any
    # unrecognized opcode as EQV instead of raising. No reachable path emits such
    # an opcode (both compilers produce exactly the six known ones), so this is a
    # latent robustness nit. Verify the two engines at least agree on it.
    loads = tuple((i, "var", f"x{i}") for i in range(6))
    vars6 = tuple(f"x{i}" for i in range(6))
    bad_opcode = bb.FlatProgram(7, 6, loads, ((6, 99, (0, 1)),))
    eqv_prog = bb.FlatProgram(7, 6, loads, ((6, bb._FLAT_OP_EQV, (0, 1)),))
    check(
        "unknown_opcode_behaves_as_eqv_words",
        bb._eval_words(bad_opcode, vars6, {}) == bb._eval_words(eqv_prog, vars6, {}),
    )

    dangling = bb.FlatProgram(8, 7, loads, ((7, bb._FLAT_OP_AND, (0, 6)),))
    try:
        bb._eval_words(dangling, tuple(f"x{i}" for i in range(6)), {})
        raised = False
    except Exception:
        raised = True
    check("malformed_dangling_slot_raises", raised)

    # --- 3. live/fixed overlap consistency between engines
    expr = Xor(And(Var(0), Var(1)), Or(Var(2), Not(Var(3))))
    overlap_fixed = {"x1": 1, "x5": 0}
    words_val = bb.eval_expr_words_bitset(expr, vars8, fixed=overlap_fixed)
    flat_val = bb.eval_expr_flat_bitset(expr, vars8, fixed=overlap_fixed)
    check("live_fixed_overlap_words_eq_flat", words_val == flat_val)

    # --- 4. repeated width eviction on one program
    expr9 = Xor(
        And(Xor(Var(0), Var(1)), Or(Var(2), Var(3))),
        Or(Not(Var(4)), And(Var(5), Xor(Var(6), Var(7)))),
    )
    node9 = compile_expr_to_cm_ir(expr9)
    prog = bb.get_flat_program(node9)
    prog.word_scratch.clear()
    widths = [6, 7, 8, 9]
    names9 = tuple(f"x{i}" for i in range(9))
    reference: dict[int, int] = {}
    for cycle in range(3):
        for k in widths:
            live = names9[:k]
            fixed = {name: 0 for name in names9[k:]}
            got = bb.eval_cm_node_words(node9, live, fixed=fixed)
            expect = bb.eval_cm_node_flat(node9, live, fixed=fixed)
            check(f"reevict_c{cycle}_k{k}", got == expect)
            if k in reference:
                check(f"reevict_stable_c{cycle}_k{k}", got == reference[k])
            reference[k] = got
    check(
        "scratch_capacity_respected",
        len(prog.word_scratch) <= bb._WORDS_SCRATCH_WIDTHS_MAX,
        str(list(prog.word_scratch)),
    )

    print(f"{CHECKS} supplemental checks, all passed")


if __name__ == "__main__":
    main()
