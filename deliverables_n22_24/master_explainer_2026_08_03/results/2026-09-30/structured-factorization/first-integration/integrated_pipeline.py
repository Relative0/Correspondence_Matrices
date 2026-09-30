"""Development integration of live PySDD search with exact residual SAT.

This module has no evaluator or ground-truth input. It does not load any Phase
5B campaign manifest. B2/B3/F1/F2 use byte-identical Phase 5B source copies.
"""
from __future__ import annotations

from itertools import combinations
import sys
from time import perf_counter_ns

from live_moves import LiveSession, candidates
from reference.benchmark import neighbors, objective, syntax_tree
from reference.hybrid_core import (
    _sdd_tree, _validate, balanced_tree, canonical, compile_extract,
    exact_refine, leaves,
)

METHODS = ('B2', 'B3', 'B4', 'F1', 'F2', 'L1', 'L2')
MAX_ROUNDS = 2
MAX_NEW_NEIGHBORS_PER_ROUND = 6


def freeze(tree):
    return tree if isinstance(tree, int) else tuple(freeze(x) for x in tree)


def separator_tree(n, clauses):
    """B4: syntax-only balanced minimum-edge-cut tree, components as clades."""
    graph = {v: set() for v in range(1, n + 1)}
    for clause in clauses:
        support = sorted({abs(lit) for lit in clause})
        for a, b in combinations(support, 2):
            graph[a].add(b)
            graph[b].add(a)

    unseen = set(graph)
    components = []
    while unseen:
        stack = [min(unseen)]
        component = set()
        while stack:
            v = stack.pop()
            if v in component:
                continue
            component.add(v)
            stack.extend(graph[v] - component)
        unseen.difference_update(component)
        components.append(tuple(sorted(component)))

    def recurse(nodes):
        if len(nodes) == 1:
            return nodes[0]
        anchor, rest = nodes[0], nodes[1:]
        best = None
        # Smaller imbalance first, then fewer crossing primal edges, then
        # lexicographic labels. The anchor eliminates mirrored candidates.
        for left_size in {len(nodes) // 2, (len(nodes) + 1) // 2}:
            if not 1 <= left_size < len(nodes):
                continue
            for extra in combinations(rest, left_size - 1):
                left = (anchor, *extra)
                left_set = set(left)
                crossing = sum(w not in left_set for v in left for w in graph[v] if w in nodes)
                key = (abs(len(nodes) - 2 * left_size), crossing, left)
                if best is None or key < best[0]:
                    best = key, left
        left = best[1]
        left_set = set(left)
        right = tuple(v for v in nodes if v not in left_set)
        return recurse(left), recurse(right)

    return balanced_tree([recurse(c) for c in components])


def score(method, compiled, carrier, n):
    return objective('M1' if method.endswith('1') else 'M2', compiled,
                     carrier, [], n)


def _fresh_search(method, n, clauses, carrier):
    tree = syntax_tree(n, clauses)
    current = compile_extract(n, clauses, tree)
    compile_ns = int(current['compile_seconds'] * 1e9)
    extract_ns = int(current['extract_seconds'] * 1e9)
    trace = []
    seen = {repr(tree)}
    rounds = []
    if not current['satisfiable']:
        return current, trace, rounds, {
            'compile_ns': compile_ns, 'extract_ns': extract_ns,
            'initial_gc_ns': 0, 'move_ns': 0, 'undo_ns': 0,
            'replay_ns': 0, 'candidate_failures': 0,
            'cnf_compilations': 1,
        }
    for round_no in range(MAX_ROUNDS):
        old = current
        best = current
        batch = [t for t in neighbors(freeze(current['tree']))
                 if repr(t) not in seen][:MAX_NEW_NEIGHBORS_PER_ROUND]
        for target in batch:
            seen.add(repr(target))
            candidate = compile_extract(n, clauses, target)
            compile_ns += int(candidate['compile_seconds'] * 1e9)
            extract_ns += int(candidate['extract_seconds'] * 1e9)
            candidate_score = score(method, candidate, carrier, n)
            became_best = candidate_score < score(method, best, carrier, n)
            trace.append({
                'round': round_no, 'parent_tree': old['tree'],
                'tree': candidate['tree'], 'score': candidate_score,
                'became_best': became_best,
                'sdd_size': candidate['sdd_size'],
                'sdd_count': candidate['sdd_count'],
                'direct_partition': candidate['direct_partition'],
                'compile_ns': int(candidate['compile_seconds'] * 1e9),
                'extract_ns': int(candidate['extract_seconds'] * 1e9),
            })
            if became_best:
                best = candidate
        current = best
        rounds.append({'round': round_no, 'selected_tree': current['tree'],
                       'considered': len(batch)})
        if freeze(best['tree']) == freeze(old['tree']):
            break
    return current, trace, rounds, {
        'compile_ns': compile_ns, 'extract_ns': extract_ns,
        'initial_gc_ns': 0, 'move_ns': 0, 'undo_ns': 0, 'replay_ns': 0,
        'candidate_failures': 0, 'cnf_compilations': 1 + len(trace),
    }


def _live_search(method, n, clauses, carrier):
    tree = syntax_tree(n, clauses)
    trace, rounds = [], []
    totals = {'compile_ns': 0, 'extract_ns': 0, 'initial_gc_ns': 0,
              'move_ns': 0, 'undo_ns': 0, 'replay_ns': 0,
              'candidate_failures': 0, 'cnf_compilations': 1}
    with LiveSession(n, clauses, tree) as session:
        totals['compile_ns'] = session.compile_ns
        totals['initial_gc_ns'] = session.initial_gc_ns
        begin = perf_counter_ns()
        current = session.snapshot()
        totals['extract_ns'] += perf_counter_ns() - begin
        if not current['satisfiable']:
            return current, trace, rounds, totals
        seen = {repr(tree)}
        for round_no in range(MAX_ROUNDS):
            old = current
            best = current
            chosen = None
            batch = [(path, kind, target) for path, kind, target
                     in candidates(freeze(current['tree']))
                     if repr(target) not in seen][:MAX_NEW_NEIGHBORS_PER_ROUND]
            for path, kind, target in batch:
                seen.add(repr(target))
                before = perf_counter_ns()
                ok, native_ns = session.move(path, kind, limited=0)
                forward_ns = perf_counter_ns() - before
                totals['move_ns'] += forward_ns
                if ok != 1:
                    totals['candidate_failures'] += 1
                    raise RuntimeError('Uncapped local move failed')
                try:
                    begin = perf_counter_ns()
                    candidate = session.snapshot()
                    totals['extract_ns'] += perf_counter_ns() - begin
                    if candidate['tree'] != target:
                        raise AssertionError('Native move produced the wrong tree')
                    candidate_score = score(method, candidate, carrier, n)
                    became_best = candidate_score < score(method, best, carrier, n)
                    trace.append({
                        'round': round_no, 'parent_tree': old['tree'],
                        'tree': candidate['tree'], 'score': candidate_score,
                        'became_best': became_best,
                        'sdd_size': candidate['sdd_size'],
                        'sdd_count': candidate['sdd_count'],
                        'direct_partition': candidate['direct_partition'],
                        'path': path, 'kind': kind,
                        'move_ns': forward_ns, 'native_move_ns': native_ns,
                    })
                    if became_best:
                        best, chosen = candidate, (path, kind)
                finally:
                    before = perf_counter_ns()
                    session.undo(path, kind)
                    totals['undo_ns'] += perf_counter_ns() - before
                if _sdd_tree(session.manager.vtree()) != old['tree']:
                    raise AssertionError('Inverse did not restore parent tree')
            if chosen is not None:
                before = perf_counter_ns()
                ok, _ = session.move(*chosen, limited=0)
                totals['replay_ns'] += perf_counter_ns() - before
                if ok != 1:
                    raise RuntimeError('Uncapped winner replay failed')
            current = best
            if session.snapshot() != current:
                raise AssertionError('Final live candidate differs after replay')
            rounds.append({'round': round_no, 'selected_tree': current['tree'],
                           'considered': len(batch)})
            if freeze(best['tree']) == freeze(old['tree']):
                break
        if session.compile_count != 1:
            raise AssertionError('Live session compiled the CNF more than once')
    return current, trace, rounds, totals


def run_trial(method, instance):
    """Run one non-oracle method. Caller controls process isolation and limits."""
    if method not in METHODS:
        raise ValueError(method)
    n = instance['n']
    clauses = [tuple(c) for c in instance['clauses']]
    carrier = instance.get('carrier')
    _validate(n, clauses, carrier)
    start = perf_counter_ns()
    if method in ('F1', 'F2'):
        compiled, trace, rounds, costs = _fresh_search(method, n, clauses, carrier)
        minimize_ns = 0
    elif method in ('L1', 'L2'):
        compiled, trace, rounds, costs = _live_search(method, n, clauses, carrier)
        minimize_ns = 0
    else:
        tree = (balanced_tree(range(1, n + 1)) if method == 'B2' else
                syntax_tree(n, clauses) if method == 'B3' else
                separator_tree(n, clauses))
        compiled = compile_extract(n, clauses, tree, minimize=method == 'B2')
        trace, rounds = [], []
        costs = {'compile_ns': int(compiled['compile_seconds'] * 1e9),
                 'extract_ns': int(compiled['extract_seconds'] * 1e9),
                 'initial_gc_ns': 0, 'move_ns': 0, 'undo_ns': 0,
                 'replay_ns': 0, 'candidate_failures': 0,
                 'cnf_compilations': 1}
        minimize_ns = int(compiled['minimize_seconds'] * 1e9)
    search_done = perf_counter_ns()
    exact = None if not compiled['satisfiable'] else exact_refine(
        n, clauses, compiled['direct_partition'], carrier=carrier)
    finished = perf_counter_ns()
    if sys.platform == 'linux':
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        memory_metric = 'ru_maxrss_bytes'
    else:
        try:
            import psutil
            memory = psutil.Process().memory_info()
            peak = getattr(memory, 'peak_wset', memory.rss)
            memory_metric = ('process_peak_wset' if hasattr(memory, 'peak_wset')
                             else 'endpoint_rss')
        except ImportError:
            peak, memory_metric = None, 'unavailable'
    return {
        'status': 'ok', 'method': method, 'id': instance.get('id'), 'n': n,
        'satisfiable': compiled['satisfiable'],
        'tree': compiled['tree'], 'direct_partition': compiled['direct_partition'],
        'sdd_size': compiled['sdd_size'], 'sdd_count': compiled['sdd_count'],
        'exact': exact, 'trace': trace, 'rounds': rounds,
        'timing_ns': {**costs, 'minimize_ns': minimize_ns,
                      'search_stage_ns': search_done - start,
                      'exact_stage_ns': finished - search_done,
                      'total_ns': finished - start},
        'peak_memory_bytes': peak, 'memory_metric': memory_metric,
    }
