"""Tests for structural adoption of foreign CMNodes (2026-08-02 consolidated audit, F4).

Compact intern keys (Phase B) registered foreign nodes — nodes built by a
different CMIRBuilder, e.g. persistent-cache hits — by bare object identity.
Structurally equal foreign nodes therefore got distinct uids, which defeated
idempotence/complement rewrites (``AND(x, x)`` stayed binary), broke the
equal-public-key ⇒ one-interned-node promise, and left recycled object ids
free to inherit stale uids. The fix adopts foreign nodes structurally
(:meth:`CMIRBuilder._adopt_foreign`) and pins them for the builder's lifetime.
"""
from __future__ import annotations

import gc
import sys

from bitset_backend import _eval_words, eval_expr_words_bitset, get_flat_program
from cm_exprlib import And, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir


def _foreign_var(name):
    return CMIRBuilder().var(name)


def test_and_of_structurally_equal_foreign_vars_is_the_var():
    b = CMIRBuilder()
    r = b.make_and((_foreign_var("x0"), _foreign_var("x0")))
    assert r.kind == "var"
    assert r.key == ("VAR", "x0")


def test_or_of_structurally_equal_foreign_vars_is_the_var():
    b = CMIRBuilder()
    r = b.make_or((_foreign_var("x0"), _foreign_var("x0")))
    assert r.kind == "var"
    assert r.key == ("VAR", "x0")


def test_xor_of_structurally_equal_foreign_vars_is_const_zero():
    b = CMIRBuilder()
    r = b.make_xor((_foreign_var("y"), _foreign_var("y")))
    assert r.kind == "const"
    assert r.const_value == 0


def test_equal_public_keys_intern_to_one_node():
    def foreign_pair():
        f = CMIRBuilder()
        return f.make_and((f.var("a"), f.var("b")))

    b = CMIRBuilder()
    na = b.make_or((foreign_pair(), b.var("c")))
    nb = b.make_or((foreign_pair(), b.var("c")))
    assert na.key == nb.key
    assert na is nb


def test_mixed_internal_and_foreign_args_match_all_internal():
    b = CMIRBuilder()
    internal = b.make_and((b.var("a"), b.var("b")))

    f = CMIRBuilder()
    foreign = f.make_and((f.var("a"), f.var("b")))

    mixed = b.make_or((internal, foreign))
    all_internal = b.make_or((internal, b.make_and((b.var("a"), b.var("b")))))
    # OR(e, e) with structurally equal args collapses to the single arg, and
    # the foreign copy must behave exactly like the internal one.
    assert mixed.key == all_internal.key
    assert mixed.key == internal.key


def test_foreign_complement_pair_collapses_to_const():
    b = CMIRBuilder()
    x = _foreign_var("x0")
    f = CMIRBuilder()
    nx = f.negate(f.var("x0"))
    r = b.make_and((x, nx))
    assert r.kind == "const"
    assert r.const_value == 0


def test_foreign_subtree_dedupes_against_internal_equivalent():
    b = CMIRBuilder()
    internal = b.make_xor((b.var("p"), b.var("q")))
    f = CMIRBuilder()
    foreign = f.make_xor((f.var("p"), f.var("q")))
    # Building over the foreign copy must reuse the internal interned parent.
    via_foreign = b.negate(foreign)
    via_internal = b.negate(internal)
    assert via_foreign is via_internal


def test_deep_foreign_chain_adoption_is_iterative():
    f = CMIRBuilder()
    cur = f.var("x0")
    depth = max(4000, sys.getrecursionlimit() * 3)
    for i in range(depth):
        cur = f.make_and((cur, f.var(f"x{i % 7 + 1}")))
    b = CMIRBuilder()
    adopted = b.negate(cur)
    assert adopted.kind == "not"
    assert adopted.args[0].key == cur.key


def test_adopted_foreign_nodes_are_pinned_against_id_reuse():
    b = CMIRBuilder()
    for round_no in range(80):
        f = CMIRBuilder()
        u = f.var("u")
        w = f.var(f"w{round_no}")
        left = f.make_xor((u, w))
        r = b.make_xor((left, left))
        assert r.kind == "const" and r.const_value == 0, round_no
        # ``left`` is spliced by associative canonicalization; its args are
        # what reach _node_uid and get adopted.
        registered = id(u)
        del u, w, left, f
        gc.collect()
        # The id stays registered AND the object stays alive (pinned), so a
        # recycled id can never inherit the stale uid.
        assert registered in b._uid_of_node
        assert any(id(n) == registered for n in b._foreign_keepalive), round_no


def test_gc_churn_with_fresh_foreign_structures_stays_correct():
    """Alternate foreign structures across GC churn; every combine through the
    long-lived builder must still match the raw packed evaluator."""
    b = CMIRBuilder()
    support = tuple(f"x{i}" for i in range(6))
    for round_no in range(60):
        f = CMIRBuilder()
        e = Xor(And(Var(round_no % 5), Var((round_no + 1) % 6)), Var(round_no % 6))
        foreign = f.make_xor((
            f.make_and((f.var(f"x{round_no % 5}"), f.var(f"x{(round_no + 1) % 6}"))),
            f.var(f"x{round_no % 6}"),
        ))
        combined = b.make_or((foreign, b.var("x5")))
        got = _eval_words(get_flat_program(combined), support, {})
        want = eval_expr_words_bitset(e, support) | eval_expr_words_bitset(Var(5), support)
        assert got == want, round_no
        del foreign, f
        gc.collect()


def test_persistent_style_reuse_across_builders_keeps_canonical_keys():
    """Combining a node compiled by one builder into a fresh builder (the
    persistent subtree regime's shape) produces the same canonical key as an
    all-in-one compile."""
    e_sub = Xor(Var(0), Var(1))
    sub_node = compile_expr_to_cm_ir(e_sub)
    b = CMIRBuilder()
    combined = b.make_and((sub_node, b.var("x2")))
    direct = compile_expr_to_cm_ir(And(Xor(Var(0), Var(1)), Var(2)))
    assert combined.key == direct.key
