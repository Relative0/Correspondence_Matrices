"""Parser/extractor correctness tests for the EPFL AIGER campaign.

Pre-registered by CM_GAP_EPFL_PROTOCOL_2026-08-03.md section 2: hand-built
synthetic fixtures (inline, no downloads), each verified by exhaustive
truth-table comparison against its known truth function, plus packed
equality of the converted expression against the reference CSE pipeline.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import _eval_words, compile_expr_cse  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "epfl_extract", ROOT / "deliverables_n22_24" / "cm_gap_epfl_extract_2026_08_03.py")
epfl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(epfl)


def _varint(x):
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def make_aig(n_inputs, outputs, ands):
    """Build a binary AIGER file body: ands = [(lhs, rhs0, rhs1)] topological."""
    M = n_inputs + len(ands)
    header = f"aig {M} {n_inputs} 0 {len(outputs)} {len(ands)}\n".encode()
    body = b"".join(f"{o}\n".encode() for o in outputs)
    enc = bytearray()
    for lhs, r0, r1 in ands:
        r0, r1 = max(r0, r1), min(r0, r1)  # binary AIGER requires rhs0 >= rhs1
        assert lhs > r0
        enc += _varint(lhs - r0)
        enc += _varint(r0 - r1)
    return header + body + bytes(enc)


def make_aag(n_inputs, outputs, ands):
    M = n_inputs + len(ands)
    lines = [f"aag {M} {n_inputs} 0 {len(outputs)} {len(ands)}"]
    lines += [str(2 * (i + 1)) for i in range(n_inputs)]
    lines += [str(o) for o in outputs]
    lines += [f"{l} {a} {b}" for l, a, b in ands]
    return ("\n".join(lines) + "\n").encode()


def cone_truth_via_expr(aig, root_lit):
    """Convert root cone to Expr and evaluate over its syntactic support with
    the reference CSE words pipeline (packed)."""
    child, support = epfl.build_tables(aig)
    sup = sorted(support[root_lit >> 1])
    var_index = {inp: j for j, inp in enumerate(sup)}
    expr = epfl.cone_to_expr(root_lit, child, var_index)
    k = len(sup)
    if k >= 6:
        # vars_key[0] is the MSB axis in _eval_words; reverse so Var(0) is
        # the LSB, matching cone_truth_bigint / exhaustive_truth bit order.
        vars_key = tuple(f"x{i}" for i in range(k - 1, -1, -1))
        return int(_eval_words(compile_expr_cse(expr), vars_key, {})), sup, expr
    # tiny support: exhaustive scalar evaluation of the expr
    from cm_exprlib import And, Not, Var
    def ev(e, asn):
        if isinstance(e, Var):
            return asn[int(e.i)]
        if isinstance(e, Not):
            return 1 - ev(e.a, asn)
        return ev(e.a, asn) & ev(e.b, asn)
    bits = 0
    for m in range(1 << k):
        asn = [(m >> j) & 1 for j in range(k)]
        bits |= ev(expr, asn) << m
    return bits, sup, expr


def exhaustive_truth(aig, root_lit):
    """Ground-truth by direct scalar simulation of the AIG."""
    I = aig["I"]
    child, support = epfl.build_tables(aig)
    sup = sorted(support[root_lit >> 1])
    k = len(sup)
    bits = 0
    for m in range(1 << k):
        val = {0: 0}
        for j, inp in enumerate(sup):
            val[inp + 1] = (m >> j) & 1
        for i in range(1, I + 1):
            val.setdefault(i, 0)
        for lhs, r0, r1 in aig["ands"]:
            v = lhs >> 1
            a = val[r0 >> 1] ^ (r0 & 1)
            b = val[r1 >> 1] ^ (r1 & 1)
            val[v] = a & b
        out = val[root_lit >> 1] ^ (root_lit & 1)
        bits |= out << m
    return bits


def parse_bytes(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return epfl.parse_aig(p), p


def test_two_input_and(tmp_path):
    aig, _ = parse_bytes(tmp_path, "and2.aig", make_aig(2, [6], [(6, 2, 4)]))
    got = exhaustive_truth(aig, 6)
    assert got == 0b1000  # x0 & x1
    bits, sup, _ = cone_truth_via_expr(aig, 6)
    assert bits == got and sup == [0, 1]


def test_inverted_output(tmp_path):
    aig, _ = parse_bytes(tmp_path, "nand2.aig", make_aig(2, [7], [(6, 2, 4)]))
    got = exhaustive_truth(aig, 7)
    assert got == 0b0111  # NAND
    bits, _, _ = cone_truth_via_expr(aig, 7)
    assert bits == got


def test_xor_from_three_ands(tmp_path):
    # xor = !( !(a & !b) & !( !a & b) )
    ands = [(6, 2, 5), (8, 3, 4), (10, 7, 9)]
    aig, _ = parse_bytes(tmp_path, "xor2.aig", make_aig(2, [11], ands))
    got = exhaustive_truth(aig, 11)
    assert got == 0b0110
    bits, _, _ = cone_truth_via_expr(aig, 11)
    assert bits == got


def test_majority3(tmp_path):
    # maj(a,b,c) = !(!(a&b) & !(a&c)) | ... build via ORs of ANDs
    # or3(ab, ac, bc) = !(!ab & !ac) | bc = !( !(!( !ab & !ac )) ... )
    ands = [(8, 2, 4),    # ab
            (10, 2, 6),   # ac
            (12, 4, 6),   # bc
            (14, 9, 11),  # !ab & !ac  == !(ab|ac)
            (16, 14, 13)]  # !(ab|ac) & !bc ; maj = !16 (lit 17)
    aig, _ = parse_bytes(tmp_path, "maj3.aig", make_aig(3, [17], ands))
    got = exhaustive_truth(aig, 17)
    expected = 0
    for m in range(8):
        a, b, c = m & 1, (m >> 1) & 1, (m >> 2) & 1
        expected |= (1 if a + b + c >= 2 else 0) << m
    assert got == expected
    bits, _, _ = cone_truth_via_expr(aig, 17)
    assert bits == got


def test_constant_outputs(tmp_path):
    aig, _ = parse_bytes(tmp_path, "const.aig", make_aig(1, [0, 1], []))
    child, support = epfl.build_tables(aig)
    # constant roots must be recognized (support of node 0 is empty)
    assert support[0] == frozenset()
    assert aig["outputs"] == [0, 1]


def test_latch_file_rejected(tmp_path):
    data = b"aig 2 1 1 1 0\n2\n2\n"
    p = tmp_path / "latch.aig"
    p.write_bytes(data)
    with pytest.raises(ValueError, match="latch"):
        epfl.parse_aig(p)


def test_binary_ascii_identical(tmp_path):
    ands = [(6, 2, 5), (8, 3, 4), (10, 7, 9)]
    bin_aig, _ = parse_bytes(tmp_path, "pair.aig", make_aig(2, [11], ands))
    asc_aig, _ = parse_bytes(tmp_path, "pair.aag", make_aag(2, [11], ands))
    norm = lambda ands: [(l, max(a, b), min(a, b)) for l, a, b in ands]
    assert norm(bin_aig["ands"]) == norm(asc_aig["ands"])
    assert bin_aig["outputs"] == asc_aig["outputs"]
    assert (bin_aig["I"], bin_aig["O"], bin_aig["A"]) == \
           (asc_aig["I"], asc_aig["O"], asc_aig["A"])
    b1, _, _ = cone_truth_via_expr(bin_aig, 11)
    b2, _, _ = cone_truth_via_expr(asc_aig, 11)
    assert b1 == b2


def test_bigint_evaluator_matches_cse_pipeline(tmp_path):
    """Independent bigint cone evaluator vs reference CSE words pipeline on a
    6-input structure (words-eligible)."""
    # chain of ANDs/ORs over 6 inputs: or via inverters
    ands = [(14, 2, 4),      # x0&x1
            (16, 15, 5),     # !(14) & !x1 ... arbitrary structure
            (18, 16, 6),
            (20, 19, 9),
            (22, 20, 10),
            (24, 23, 13),
            (26, 24, 12)]
    aig, _ = parse_bytes(tmp_path, "six.aig", make_aig(6, [27], ands))
    child, support = epfl.build_tables(aig)
    sup = sorted(support[27 >> 1])
    assert len(sup) == 6
    bits_big, full = epfl.cone_truth_bigint(27, child, sup)
    bits_expr, _, _ = cone_truth_via_expr(aig, 27)
    assert bits_big == bits_expr
    got = exhaustive_truth(aig, 27)
    assert bits_big == got
    sem = epfl.semantic_support(bits_big, sup)
    assert set(sem) <= set(sup)
