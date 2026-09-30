"""Fixed synthetic microbenchmark; never reads campaign data or semantic truth.

Correctness runs separately. Each timed candidate is also compared structurally
to both fresh-compilation paths outside its timing window.
"""
import gc
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
from tempfile import TemporaryDirectory
from time import perf_counter_ns, get_clock_info

from pysdd.sdd import Vtree
from fixtures import timing_cases
from live_moves import LiveSession, candidates, score
from reference.hybrid_core import _write_vtree, balanced_tree, compile_extract

ROOT = Path(__file__).resolve().parent
REPEATS = 7


def prepare(tree):
    with TemporaryDirectory(prefix='live-probe-preloaded-') as tmp:
        path = Path(tmp) / 'input.vtree'
        _write_vtree(tree, path)
        return Vtree.from_file(str(path).encode())


def stable(snapshot):
    return {k: snapshot[k] for k in ('tree', 'sdd_size', 'sdd_count', 'satisfiable', 'direct_partition')}


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2) + '\n')


def measure_candidate(session, case, descriptor, prepared, rng):
    path, kind, target = descriptor
    output = {'case': case['name'], 'n': case['n'], 'kind': kind,
              'path': path, 'parent_tree': session.snapshot()['tree'], 'target_tree': target}
    snapshots = {}
    methods = ['live', 'fresh_core', 'phase5b']
    rng.shuffle(methods)
    output['timing_order'] = methods
    for method in methods:
        if method == 'live':
            start = perf_counter_ns()
            ok, native = session.move(path, kind)
            moved_at = perf_counter_ns()
            snapshot = session.snapshot()
            score(snapshot)
            scored_at = perf_counter_ns()
            inverse = session.undo(path, kind)
            ended = perf_counter_ns()
            assert ok == 1
            output.update(live_native_ns=native, inverse_native_ns=inverse,
                          live_move_ns=moved_at-start, live_extract_score_ns=scored_at-moved_at,
                          live_move_score_undo_ns=ended-start)
        elif method == 'fresh_core':
            start = perf_counter_ns()
            fresh = LiveSession(case['n'], case['clauses'], prepared_vtree=prepared, collect=False)
            compiled_at = perf_counter_ns()
            snapshot = fresh.snapshot()
            score(snapshot)
            ended = perf_counter_ns()
            output.update(fresh_core_compile_ns=compiled_at-start,
                          fresh_core_eval_ns=ended-start,
                          fresh_cnf_apply_ns=fresh.cnf_apply_ns)
            fresh.close()
            del fresh
        else:
            start = perf_counter_ns()
            snapshot = compile_extract(case['n'], case['clauses'], target)
            score(snapshot)
            ended = perf_counter_ns()
            output.update(phase5b_compile_ns=snapshot['compile_seconds'] * 1e9,
                          phase5b_eval_ns=ended-start)
        snapshots[method] = stable(snapshot)
    assert snapshots['live'] == snapshots['fresh_core'] == snapshots['phase5b']
    output['candidate_sdd_size'] = snapshots['live']['sdd_size']
    return output


def measure_round(case, tree, templates, rng):
    methods = ['live', 'fresh_core', 'phase5b']
    rng.shuffle(methods)
    output, snapshots = {'case': case['name'], 'order': methods}, {}
    for method in methods:
        if method == 'live':
            start = perf_counter_ns()
            session = LiveSession(case['n'], case['clauses'], prepared_vtree=templates[tree])
            session.one_round()
            snapshot = session.snapshot()
            session.close()
            del session
            output['live_round_ns'] = perf_counter_ns() - start
        elif method == 'fresh_core':
            start = perf_counter_ns()
            session = LiveSession(case['n'], case['clauses'], prepared_vtree=templates[tree], collect=False)
            snapshot = session.snapshot()
            best_session = session
            for _, _, target in candidates(tree):
                fresh = LiveSession(case['n'], case['clauses'], prepared_vtree=templates[target], collect=False)
                candidate = fresh.snapshot()
                if score(candidate) < score(snapshot):
                    best_session.close()
                    best_session = fresh
                    snapshot = candidate
                else:
                    fresh.close()
                del fresh
            best_session.close()
            del session, best_session
            output['fresh_core_round_ns'] = perf_counter_ns() - start
        else:
            start = perf_counter_ns()
            snapshot = compile_extract(case['n'], case['clauses'], tree)
            for _, _, target in candidates(tree):
                candidate = compile_extract(case['n'], case['clauses'], target)
                if score(candidate) < score(snapshot):
                    snapshot = candidate
            output['phase5b_round_ns'] = perf_counter_ns() - start
        snapshots[method] = stable(snapshot)
    assert snapshots['live'] == snapshots['fresh_core'] == snapshots['phase5b']
    output['selected_tree'] = snapshots['live']['tree']
    output['selected_size'] = snapshots['live']['sdd_size']
    return output


def summarize(rows, rounds):
    result = []
    for case in timing_cases():
        subset = [r for r in rows if r['case'] == case['name']]
        round_subset = [r for r in rounds if r['case'] == case['name']]
        metrics = ['live_native_ns', 'inverse_native_ns', 'live_move_ns', 'live_extract_score_ns',
                   'live_move_score_undo_ns', 'fresh_core_compile_ns', 'fresh_core_eval_ns',
                   'fresh_cnf_apply_ns', 'phase5b_compile_ns', 'phase5b_eval_ns']
        row = {'case': case['name'], 'n': case['n'], 'clauses': len(case['clauses']),
               'candidates_per_repeat': len(subset) // REPEATS,
               'median_microseconds': {k.removesuffix('_ns'): statistics.median(r[k] for r in subset) / 1000
                                       for k in metrics}}
        row['round_median_ms'] = {k.removesuffix('_ns'): statistics.median(r[k] for r in round_subset) / 1e6
                                 for k in ('live_round_ns', 'fresh_core_round_ns', 'phase5b_round_ns')}
        # Pair by exact target tree, collapse temporal replicates first, then gmean.
        ratios_core, ratios_full = [], []
        for target in sorted({repr(r['target_tree']) for r in subset}):
            paired = [r for r in subset if repr(r['target_tree']) == target]
            live = statistics.median(r['live_move_score_undo_ns'] for r in paired)
            ratios_core.append(live / statistics.median(r['fresh_core_eval_ns'] for r in paired))
            ratios_full.append(live / statistics.median(r['phase5b_eval_ns'] for r in paired))
        row['paired_gmean_live_over_core'] = math.exp(statistics.mean(map(math.log, ratios_core)))
        row['paired_gmean_live_over_phase5b'] = math.exp(statistics.mean(map(math.log, ratios_full)))
        result.append(row)
    return result


def run():
    assert json.loads((ROOT / 'correctness.json').read_text())['status'] == 'PASS'
    cases = timing_cases()
    plan = {'cases': cases, 'repetitions': REPEATS, 'warmup_repetitions': 1,
            'timing_order_seed': 2026092914,
            'objective': 'Unchanged Phase 5B M2; no semantic truth',
            'scope': 'All one-hop neighbors, synthetic balanced-tree parents; no campaign runs',
            'timers': 'perf_counter_ns; correctness and target-vtree preload outside candidate timers',
            'rollback': 'Every timed live candidate includes uncapped inverse; full rounds include winner replay',
            'fresh_core': 'Preloaded target vtree; fresh manager, CNF Apply, extraction and score; no final GC',
            'phase5b': 'Byte-identical archived compile_extract; temp vtree I/O, manager, CNF, extraction, score',
            'rounds': 'Include initial compilation, all neighbors, selection, winner commit, close; preloaded vtrees for live/core',
            'limitations': 'Single process, seven temporal repetitions, tiny synthetic cases; no inference about held-out or industrial workloads'}
    write_json('timing_plan.json', plan)
    write_json('timing_environment.json', {'python': sys.version, 'executable': sys.executable,
        'platform': platform.platform(), 'pysdd': importlib.metadata.version('pysdd'),
        'timer': str(get_clock_info('perf_counter')),
        'gc_enabled': gc.isenabled(),
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(ROOT.glob('*.py'))}})
    rows, rounds, setups = [], [], []
    rng = random.Random(2026092914)
    for case in cases:
        tree = balanced_tree(range(1, case['n'] + 1))
        descriptors = candidates(tree)
        templates = {t: prepare(t) for t in [tree] + [d[2] for d in descriptors]}
        for repeat in range(-1, REPEATS):
            with LiveSession(case['n'], case['clauses'], prepared_vtree=templates[tree]) as session:
                parent = session.snapshot()
                batch = descriptors[:]
                rng.shuffle(batch)
                for descriptor in batch:
                    row = measure_candidate(session, case, descriptor, templates[descriptor[2]], rng)
                    assert session.snapshot() == parent
                    row['repeat'] = repeat
                    if repeat >= 0:
                        rows.append(row)
                assert session.compile_count == 1
                if repeat >= 0:
                    setups.append({'case': case['name'], 'repeat': repeat,
                                   'initial_core_compile_ns': session.compile_core_ns,
                                   'initial_gc_ns': session.initial_gc_ns})
            row = measure_round(case, tree, templates, rng)
            row['repeat'] = repeat
            if repeat >= 0:
                rounds.append(row)
        print(f'Measured {case["name"]}: {len(descriptors)} candidates x {REPEATS}', flush=True)
    write_json('timing_raw.json', {'candidates': rows, 'rounds': rounds, 'initial_setup': setups})
    summary = {'status': 'PASS', 'candidate_triplets': len(rows), 'round_triplets': len(rounds),
               'structural_disagreements': 0, 'per_case': summarize(rows, rounds)}
    write_json('timing_summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    run()
