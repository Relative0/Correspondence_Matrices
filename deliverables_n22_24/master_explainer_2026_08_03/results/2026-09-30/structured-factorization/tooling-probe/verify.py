"""Independent exhaustive checks. Truth is confined to this evaluator."""
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
from time import perf_counter

from fixtures import table_cnf, timing_cases
from live_moves import LiveSession, candidates, score
from reference.benchmark import neighbors
from reference.hybrid_core import balanced_tree, canonical, leaves

ROOT = Path(__file__).resolve().parent
COUNTS = Counter()


@lru_cache(None)
def literal_masks(n):
    return [sum(1 << x for x in range(1 << n) if x & (1 << i)) for i in range(n)]


def cnf_truth(n, clauses):
    # Direct evaluation of the input CNF, independent of the compiler.
    return sum(1 << x for x in range(1 << n)
               if all(any(bool(x & (1 << (abs(l) - 1))) == (l > 0) for l in c) for c in clauses))


def sdd_truth(n, node):
    # Re-read the decision DAG after EVERY edit. No cached node elements survive.
    full = (1 << (1 << n)) - 1
    cache = {}
    masks = literal_masks(n)
    def visit(u):
        if u.id in cache:
            return cache[u.id]
        if u.is_true():
            value = full
        elif u.is_false():
            value = 0
        elif u.is_literal():
            value = masks[abs(u.literal) - 1]
            if u.literal < 0:
                value ^= full
        else:
            value = 0
            for p, s in u.elements():
                value |= visit(p) & visit(s)
        cache[u.id] = value
        return value
    return visit(node)


def projection_partition(n, truth, tree):
    """Finest compatible direct partition via Cartesian relation projections.

    This checks the extractor, not semantic prime truth, and never scores moves.
    """
    if truth == 0:
        return None
    models = {x for x in range(1 << n) if truth & (1 << x)}
    def visit(t, relation):
        if isinstance(t, int):
            return [[t]]
        left_mask = sum(1 << (v - 1) for v in leaves(t[0]))
        right_mask = sum(1 << (v - 1) for v in leaves(t[1]))
        left = {x & left_mask for x in relation}
        right = {x & right_mask for x in relation}
        if len(relation) == len(left) * len(right):
            return visit(t[0], left) + visit(t[1], right)
        return [sorted(leaves(t))]
    return canonical(visit(tree, models))


def check(session, truth, tree):
    snapshot = session.snapshot()
    assert snapshot['tree'] == tree
    assert sdd_truth(session.n, session.root) == truth, ('truth mismatch', tree)
    assert session.root.global_model_count() == truth.bit_count()
    assert snapshot['direct_partition'] == projection_partition(session.n, truth, tree)
    COUNTS['states_checked'] += 1
    COUNTS['assignment_comparisons'] += 1 << session.n
    COUNTS['false_states' if truth == 0 else 'nonfalse_states'] += 1
    return snapshot


def check_case(n, clauses, tree):
    truth = cnf_truth(n, clauses)
    with LiveSession(n, clauses, tree) as session:
        parent = check(session, truth, tree)
        descriptors = candidates(tree)
        assert [t for _, _, t in descriptors] == neighbors(tree)
        for path, kind, target in descriptors:
            ok, _ = session.move(path, kind)
            assert ok == 1
            moved = check(session, truth, target)
            with LiveSession(n, clauses, target) as fresh:
                assert check(fresh, truth, target) == moved
            session.undo(path, kind)
            assert check(session, truth, tree) == parent
            COUNTS['forward_moves'] += 1
            COUNTS['inverse_moves'] += 1
            COUNTS[kind] += 1
            COUNTS['below_root' if path else 'at_root'] += 1
        assert session.compile_count == 1
    COUNTS['initial_sessions'] += 1


def check_rounds(case):
    n, clauses = case['n'], case['clauses']
    truth = cnf_truth(n, clauses)
    tree = balanced_tree(range(1, n + 1))
    with LiveSession(n, clauses, tree) as session:
        for _ in range(3):
            parent = session.snapshot()
            best = parent
            for _, _, target in candidates(parent['tree']):
                with LiveSession(n, clauses, target) as fresh:
                    candidate = fresh.snapshot()
                    if score(candidate) < score(best):
                        best = candidate
            chosen = session.one_round()
            assert check(session, truth, best['tree']) == best
            assert session.compile_count == 1
            COUNTS['search_rounds'] += 1
            COUNTS['accepted_moves'] += chosen is not None


def check_multi_root_and_failures():
    c = timing_cases()[-1]
    n, clauses = c['n'], c['clauses']
    tree = balanced_tree(range(1, n + 1))
    truth = cnf_truth(n, clauses)
    with LiveSession(n, clauses, tree) as s:
        extra = s.manager.disjoin(s.manager.literal(1), s.manager.literal(n))
        extra.ref()
        s.extra_roots.append(extra)
        extra_truth = cnf_truth(n, [[1, n]])
        # Unreferenced temporary Apply nodes exist; move() must collect them.
        junk = s.manager.conjoin(s.manager.literal(2), s.manager.literal(3))
        assert s.manager.dead_count() > 0
        del junk
        for path, kind, target in candidates(tree):
            assert s.move(path, kind)[0] == 1
            check(s, truth, target)
            assert sdd_truth(n, extra) == extra_truth
            s.undo(path, kind)
            check(s, truth, tree)
            assert sdd_truth(n, extra) == extra_truth
            COUNTS['multi_root_roundtrips'] += 1
        base = s.snapshot()
        for path, kind, target in candidates(tree):
            s.manager.init_vtree_size_limit(s.manager.vtree())
            s.manager.set_vtree_operation_size_limit(1.0)
            s.manager.set_vtree_cartesian_product_limit(1)
            ok, _ = s.move(path, kind, limited=1)
            if ok:
                check(s, truth, target)
                s.undo(path, kind)
                COUNTS['limited_successes'] += 1
            else:
                COUNTS['limited_failures_checked'] += 1
            assert check(s, truth, tree) == base
            assert sdd_truth(n, extra) == extra_truth
        assert COUNTS['limited_failures_checked'] > 0
        # Invalid descriptors are stopped in Python before entering native code.
        for path, kind in [((0, 0, 0, 0), 'swap'), ((), 'invalid')]:
            try:
                s.move(path, kind)
            except ValueError:
                COUNTS['invalid_moves_rejected'] += 1
            else:
                raise AssertionError('Invalid move accepted')


def run():
    start = perf_counter()
    for n in (1, 2, 3):
        trees = [balanced_tree(range(1, n + 1))]
        if n == 3:
            trees.append(((1, 2), 3))
        for mask in range(1 << (1 << n)):
            for tree in trees:
                check_case(n, table_cnf(n, mask), tree)
        print(f'All Boolean functions on {n} variables checked', flush=True)
    edge_cases = [[], [[]], [[1]], [[-3]], [[1, -1]], [[2, 4], [-2, -4]]]
    for clauses in edge_cases:
        check_case(6, clauses, ((1, (3, 5)), ((2, 4), 6)))
    for case in timing_cases():
        check_case(case['n'], case['clauses'], balanced_tree(range(1, case['n'] + 1)))
        check_rounds(case)
        print(f'Checked {case["name"]}', flush=True)
    check_multi_root_and_failures()
    result = {'status': 'PASS', 'counts': dict(COUNTS), 'seconds': perf_counter() - start,
              'semantic_prime_truth_used_in_objectives': False,
              'archived_campaign_inputs_executed': 0}
    (ROOT / 'correctness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    run()
