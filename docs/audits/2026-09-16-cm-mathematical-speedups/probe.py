"""Bounded research probes; no optimizer or production-code changes.

Run from the repository root with Python -B. Writes a new JSON evidence file.
The cut census is exploratory on exposed corpora, not confirmation.
"""
import hashlib
import json
import platform
import sys
from collections import Counter
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cm_exprlib import Var, Not, And, Or, Xor, Imp, Eqv
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir
from bitset_backend import compile_expr_cse, compile_flat, program_metrics, build_bitset_env, eval_expr_bitset
from cm_token import cm_compose, cm_token_value
from cmbench.recognition.rule_pack import compile_rule_pack, prove_rule_pack_v2

OPS = {'and': And, 'or': Or, 'xor': Xor, 'imp': Imp, 'eqv': Eqv}
PRIMITIVES = {'and': 1, 'or': 1, 'xor': 1, 'not': 2, 'imp': 3, 'eqv': 3}
PACK = compile_rule_pack(prove_rule_pack_v2())


def truth(op, a, b=None):
    return {'and': lambda: a & b, 'or': lambda: a | b,
            'xor': lambda: a ^ b, 'not': lambda: a ^ 15,
            'imp': lambda: (a ^ 15) | b,
            'eqv': lambda: (a ^ b) ^ 15}[op]()


def metrics(e):
    return {'cse': program_metrics(compile_expr_cse(e, flatten=True)),
            'cm': program_metrics(compile_flat(compile_expr_to_cm_ir(e)))}


def templates():
    a, b = Var(0), Var(1)
    pool = [a, b, Not(a), Not(b), Xor(a, a), Eqv(a, a)]
    for ctor, swap, na, nb in product(OPS.values(), (False, True), (False, True), (False, True)):
        x, y = (b, a) if swap else (a, b)
        pool.append(ctor(Not(x) if na else x, Not(y) if nb else y))
    best = {}
    for e in pool:
        t = eval_expr_bitset(e, build_bitset_env(['x0', 'x1']))
        cost = metrics(e)['cm']['executed_bigint_ops']
        if t not in best or cost < best[t][0]:
            best[t] = (cost, e)
    assert len(best) == 16
    return best


def census(doc, best):
    """At most 8 nontrivial cuts plus the self cut per node; no rewrites.

    Token propagation uses at most 9*9 cut pairs per binary node. This
    exploratory shell rebuilding is not bounded that way: repeated interior
    walks and compiler calls can take quadratic work in the source size.

    A trivial cut names its root as an opaque leaf. A nontrivial cut combines
    child cuts only if their union has at most two leaves. We skip shared
    interior nodes, and report maxima rather than adding overlapping gains.
    """
    nodes = doc['nodes']
    fanout = Counter()
    for n in nodes:
        for key in ('a', 'b'):
            if key in n:
                fanout[n[key]] += 1
    cuts = []
    candidates = []
    for i, n in enumerate(nodes):
        current = {(i,): 12}
        if n['op'] != 'var':
            left = cuts[n['a']]
            right = cuts[n['b']] if 'b' in n else {(): 0}
            found = {}
            for (ca, ta), (cb, tb) in product(left.items(), right.items()):
                frame = tuple(sorted(set(ca) | set(cb)))
                if len(frame) > 2:
                    continue
                def align(old, token):
                    out = 0
                    for a, b in product((0, 1), repeat=2):
                        values = dict(zip(frame, (a, b)))
                        x = values[old[0]] if old else 0
                        y = values[old[1]] if len(old) == 2 else 0
                        out |= cm_token_value(token, x, y) << (2*a+b)
                    return out
                found[frame] = truth(n['op'], align(ca, ta), align(cb, tb))
            for frame in sorted(found, key=lambda f: (len(f), f))[:8]:
                current[frame] = found[frame]
                if len(frame) != 2 or all(nodes[v]['op'] == 'var' for v in frame):
                    continue
                interior = set()
                pending = [i]
                while pending:
                    j = pending.pop()
                    if j in frame or j in interior:
                        continue
                    interior.add(j)
                    pending.extend(nodes[j][key] for key in ('a', 'b') if key in nodes[j])
                if any(j != i and fanout[j] > 1 for j in interior):
                    continue
                original = sum(PRIMITIVES[nodes[j]['op']] for j in interior)
                gain = original - best[found[frame]][0]
                if gain <= 0:
                    continue
                # Rebuild the small cut shell with two placeholder inputs and
                # ask current CM-IR whether its existing rewrites already win.
                rebuilt = {frame[0]: Var(0), frame[1]: Var(1)}
                for j in sorted(interior):
                    nn = nodes[j]
                    rebuilt[j] = Not(rebuilt[nn['a']]) if nn['op'] == 'not' else OPS[nn['op']](rebuilt[nn['a']], rebuilt[nn['b']])
                mm = metrics(rebuilt[i])
                assert eval_expr_bitset(rebuilt[i], build_bitset_env(['x0', 'x1'])) == found[frame]
                residual = mm['cm']['executed_bigint_ops'] - best[found[frame]][0]
                packed = PACK.rewrite(rebuilt[i], 2).result
                pack_mm = metrics(packed)
                pack_residual = min(pack_mm['cm']['executed_bigint_ops'], pack_mm['cse']['executed_bigint_ops']) - best[found[frame]][0]
                candidates.append({'root': i, 'leaves': frame, 'token': found[frame],
                                   'raw_bigint_saving': gain, 'cm_shell_bigint_saving': residual,
                                   'one_pass_pack_shell_bigint_saving': pack_residual,
                                   'interior_nodes': len(interior)})
        cuts.append(current)
    return {'nodes': len(nodes), 'candidate_cuts': len(candidates),
            'residual_cuts': sum(c['cm_shell_bigint_saving'] > 0 for c in candidates),
            'residual_after_one_pass_pack': sum(c['cm_shell_bigint_saving'] > 0 and c['one_pass_pack_shell_bigint_saving'] > 0 for c in candidates),
            'max_cm_shell_bigint_saving': max((c['cm_shell_bigint_saving'] for c in candidates), default=0),
            'examples': sorted(candidates, key=lambda c: -c['cm_shell_bigint_saving'])[:3]}


def run():
    best = templates()
    checks = 0
    for p, q, op, a, b in product(range(16), range(16), OPS, (0, 1), (0, 1)):
        actual = cm_token_value(cm_compose(p, q, op.upper()), a, b)
        x, y = cm_token_value(p, a, b), cm_token_value(q, a, b)
        expected = truth(op, 15*x, 15*y) & 1
        assert actual == expected
        checks += 1
    # All maps from a two-bit physical input into two operand bits, including
    # identical, complemented, dependent and overlapping operands.
    substitution_checks = 0
    for amap, bmap, p, q, op in product(range(16), range(16), range(16), range(16), OPS):
        for assignment in range(4):
            a, b = (amap >> assignment) & 1, (bmap >> assignment) & 1
            lhs = truth(op, 15*cm_token_value(p, a, b), 15*cm_token_value(q, a, b)) & 1
            rhs = cm_token_value(cm_compose(p, q, op.upper()), a, b)
            assert lhs == rhs
            substitution_checks += 1
    a = And(Var(0), Var(1)); b = Xor(Var(1), Var(2))
    examples = []
    for label, old, new in [
        ('xor_and_or', Xor(And(a, b), Or(a, b)), Xor(a, b)),
        ('mutual_implication', And(Imp(a, b), Imp(b, a)), Eqv(a, b)),
        ('eliminate_second_operand', Or(And(a, b), And(a, Not(b))), a),
    ]:
        assert eval_expr_bitset(old, build_bitset_env(['x0', 'x1', 'x2'])) == eval_expr_bitset(new, build_bitset_env(['x0', 'x1', 'x2']))
        examples.append({'name': label, 'original': metrics(old), 'analytic_replacement': metrics(new),
                         'one_pass_pack': metrics(PACK.rewrite(old, 3).result)})
    files = ['deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl',
             'docs/recognition/c36_wide_repeated_query_dataset.json']
    rows = []
    for line in (ROOT / files[0]).read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if 'expression_v2' in row and row['synt_support_size'] == row['sem_support_size'] and 11 <= row['synt_support_size'] <= 16:
            rows.append(('exposed_epfl', row['id'], row['expression_v2']))
    for row in json.loads((ROOT / files[1]).read_text(encoding='utf-8'))['cases']:
        rows.append(('exposed_c36', row['case_id'], row['expression_v2']))
    scans = []
    for cohort, ident, doc in rows:
        expr_from_json(doc)  # existing schema validation
        scans.append({'cohort': cohort, 'id': ident, **census(doc, best)})
    dependencies = files + ['cm_ir.py', 'bitset_backend.py', 'cm_exprlib.py', 'cm_expr_serde.py', 'cm_token.py', 'cm_build_pair.py', 'cmbench/recognition/rule_pack.py']
    out = {'status': 'exploratory_exact_static_only', 'python': sys.version,
           'platform': platform.platform(), 'fusion_checks': checks,
           'substitution_checks': substitution_checks, 'mismatches': 0,
           'template_bigint_costs': {str(k): v[0] for k, v in best.items()},
           'examples': examples, 'census': scans,
           'source_sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in dependencies}}
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('probe-results.json')
    with target.open('x', encoding='utf-8') as f:
        json.dump(out, f, indent=2); f.write('\n')
    print(json.dumps({'fusion_checks': checks, 'substitution_checks': substitution_checks,
                      'cases': len(scans), 'cases_with_residual': sum(r['residual_cuts'] > 0 for r in scans),
                      'residual_cuts': sum(r['residual_cuts'] for r in scans), 'mismatches': 0}))


if __name__ == '__main__':
    run()
