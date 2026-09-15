import cm_bench
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.expr.visitors import collect_subtree_hashes_fast, expr_children


def test_expr_children_matches_expected_shapes():
    assert expr_children(Var(0)) == ()
    assert len(expr_children(Not(Var(0)))) == 1
    assert len(expr_children(And(Var(0), Var(1)))) == 2


def test_collect_subtree_hashes_fast_matches_legacy_hash_multiset():
    expressions = [
        And(Var(0), Var(1)),
        Or(Not(Var(0)), Var(1)),
        Xor(Var(0), Var(1)),
        Eqv(Imp(Var(0), Var(1)), Or(Not(Var(0)), Var(1))),
    ]

    for expr in expressions:
        assert sorted(cm_bench.collect_subtree_hashes(expr)) == sorted(collect_subtree_hashes_fast(expr))

