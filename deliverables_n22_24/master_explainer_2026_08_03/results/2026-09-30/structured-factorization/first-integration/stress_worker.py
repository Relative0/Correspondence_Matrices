"""One isolated hostile live-move sequence, called only by check_stress.py."""
import json
import random
import sys
from time import perf_counter, perf_counter_ns

import psutil

from dev_fixtures import planted
from exact_miter import equivalent_to_cnf
from live_moves import LiveSession, candidates
from reference.hybrid_core import balanced_tree, compile_extract

MEMORY_CHECK_BYTES = 1024 ** 3


def run(n, steps):
    started = perf_counter()
    rng = random.Random(2026093017 + n)
    clauses = planted(n, n * 3, 2026093011 + n)
    tree = balanced_tree(range(1, n + 1))
    process = psutil.Process()
    counts = {'forward_successes': 0, 'immediate_undos': 0,
              'limited_failures': 0, 'limited_successes': 0,
              'long_sequence_restorations': 0, 'fresh_structure_checks': 0,
              'sat_miter_checks': 0, 'extra_root_miter_checks': 0}
    max_rss = 0
    max_peak_wset = 0
    forward_ns = 0
    undo_ns = 0
    restore_ns = 0
    with LiveSession(n, clauses, tree) as session:
        extra = session.manager.disjoin(session.manager.literal(1), session.manager.literal(n))
        extra.ref()
        session.extra_roots.append(extra)
        extra_cnf = [[1, n]]
        base = session.snapshot()
        baseline_live_size = session.manager.live_size()
        assert equivalent_to_cnf(n, clauses, session.root)
        assert equivalent_to_cnf(n, extra_cnf, extra)
        counts['sat_miter_checks'] += 1
        counts['extra_root_miter_checks'] += 1
        accepted = []
        def check_memory():
            nonlocal max_rss, max_peak_wset
            memory = process.memory_info()
            max_rss = max(max_rss, memory.rss)
            max_peak_wset = max(max_peak_wset, getattr(memory, 'peak_wset', memory.rss))
            if max_peak_wset > MEMORY_CHECK_BYTES:
                raise MemoryError('Worker exceeded checked 1 GiB peak working set')

        for i in range(steps):
            parent = session.snapshot()
            path, kind, target = rng.choice(candidates(parent['tree']))
            # Force repeated native failures without changing the parent.
            if i % 5 == 0:
                session.manager.init_vtree_size_limit(session.manager.vtree())
                session.manager.set_vtree_operation_size_limit(1.0)
                session.manager.set_vtree_cartesian_product_limit(1)
                before = perf_counter_ns()
                ok, _ = session.move(path, kind, limited=1)
                forward_ns += perf_counter_ns() - before
                if ok == 0:
                    counts['limited_failures'] += 1
                    assert session.snapshot() == parent
                else:
                    counts['limited_successes'] += 1
                    assert session.snapshot()['tree'] == target
                    before = perf_counter_ns()
                    session.undo(path, kind)
                    undo_ns += perf_counter_ns() - before
                    assert session.snapshot() == parent
                assert equivalent_to_cnf(n, clauses, session.root)
                assert equivalent_to_cnf(n, extra_cnf, extra)
                counts['sat_miter_checks'] += 1
                counts['extra_root_miter_checks'] += 1
            # A permissive but finite relative size limit stresses real
            # successes and failures during a long changing-tree walk.
            session.manager.init_vtree_size_limit(session.manager.vtree())
            session.manager.set_vtree_operation_size_limit(1.6)
            session.manager.set_vtree_cartesian_product_limit(256)
            before = perf_counter_ns()
            ok, _ = session.move(path, kind, limited=1)
            forward_ns += perf_counter_ns() - before
            if not ok:
                counts['limited_failures'] += 1
                assert session.snapshot() == parent
                continue
            counts['forward_successes'] += 1
            moved = session.snapshot()
            assert moved['tree'] == target
            assert equivalent_to_cnf(n, clauses, session.root)
            assert equivalent_to_cnf(n, extra_cnf, extra)
            counts['sat_miter_checks'] += 1
            counts['extra_root_miter_checks'] += 1
            if i % 8 == 0:
                fresh = compile_extract(n, clauses, target)
                assert all(fresh[k] == moved[k] for k in
                           ('tree', 'sdd_size', 'sdd_count', 'direct_partition', 'satisfiable'))
                counts['fresh_structure_checks'] += 1
            if i % 3 == 0:
                before = perf_counter_ns()
                session.undo(path, kind)
                undo_ns += perf_counter_ns() - before
                assert session.snapshot() == parent
                assert equivalent_to_cnf(n, clauses, session.root)
                counts['sat_miter_checks'] += 1
                counts['immediate_undos'] += 1
            else:
                accepted.append((path, kind))
            check_memory()

        # Undo the accepted walk in reverse order, restoring the initial tree.
        for path, kind in reversed(accepted):
            before = perf_counter_ns()
            session.undo(path, kind)
            restore_ns += perf_counter_ns() - before
            assert equivalent_to_cnf(n, clauses, session.root)
            assert equivalent_to_cnf(n, extra_cnf, extra)
            counts['sat_miter_checks'] += 1
            counts['extra_root_miter_checks'] += 1
            counts['long_sequence_restorations'] += 1
        assert session.snapshot() == base
        session.manager.garbage_collect()
        assert session.manager.dead_count() == 0
        ending_live_size = session.manager.live_size()
        # Canonical reduced SDD plus the same extra root should recover the
        # baseline live allocation at the original vtree.
        assert ending_live_size == baseline_live_size, (
            baseline_live_size, ending_live_size)
        assert session.compile_count == 1
        check_memory()
    return {'status': 'PASS', 'n': n, 'steps': steps, 'counts': counts,
            'max_rss_bytes': max_rss, 'max_peak_wset_bytes': max_peak_wset,
            'baseline_live_size': baseline_live_size,
            'ending_live_size': ending_live_size,
            'forward_ms': forward_ns / 1e6, 'immediate_undo_ms': undo_ns / 1e6,
            'long_restore_ms': restore_ns / 1e6,
            'seconds': perf_counter() - started,
            'campaign_inputs_executed': 0}


if __name__ == '__main__':
    print(json.dumps(run(int(sys.argv[1]), int(sys.argv[2]))), flush=True)
