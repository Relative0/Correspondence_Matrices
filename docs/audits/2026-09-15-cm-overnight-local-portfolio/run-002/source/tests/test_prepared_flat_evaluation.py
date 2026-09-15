from bitset_backend import (
    build_bitset_env,
    eval_expr_bitset,
    get_expr_flat_program,
    prepare_cm_node_flat_evaluation,
    prepare_expr_flat_evaluation,
)
from cm_exprlib import And, Imp, Or, Var
from cm_ir import compile_expr_to_cm_ir


def test_prepared_expr_and_cm_evaluation_match_recursive_reference():
    expr = Imp(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    for k in (4, 8, 16):
        names = tuple(f"x{i}" for i in range(k))
        reference = eval_expr_bitset(expr, build_bitset_env(names))
        assert prepare_expr_flat_evaluation(expr, names).evaluate() == reference
        node = compile_expr_to_cm_ir(expr)
        assert prepare_cm_node_flat_evaluation(node, names).evaluate() == reference


def test_bound_cache_key_ignores_irrelevant_ambient_fixed_bindings():
    expr = And(Var(0), Var(1))
    prog = get_expr_flat_program(expr)
    first = prepare_expr_flat_evaluation(
        expr, ("x0",), fixed={"x1": 0, "unused_a": 0}
    )
    second = prepare_expr_flat_evaluation(
        expr, ("x0",), fixed={"x1": 0, "unused_b": 1}
    )
    assert first.evaluate() == second.evaluate()
    assert len(prog.bound_cache) == 1


def test_bound_cache_distinguishes_relevant_fixed_values():
    expr = And(Var(0), Var(1))
    prog = get_expr_flat_program(expr)
    zero = prepare_expr_flat_evaluation(expr, ("x0",), fixed={"x1": 0})
    one = prepare_expr_flat_evaluation(expr, ("x0",), fixed={"x1": 1})
    assert zero.evaluate() != one.evaluate()
    assert len(prog.bound_cache) == 2
