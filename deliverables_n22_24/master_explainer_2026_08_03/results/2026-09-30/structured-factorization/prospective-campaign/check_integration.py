"""Development-only exactness gate; no frozen campaign inputs or timing claims."""
from collections import Counter
import json
from pathlib import Path
import random
import subprocess
import sys
from time import perf_counter

from dev_fixtures import factor_exposure_cases, planted, table_cnf, timing_cases
from exact_miter import equivalent_to_cnf
from integrated_pipeline import METHODS, run_trial, separator_tree
from live_moves import LiveSession
from reference.benchmark import exact_baseline, lcc, syntax_tree
from reference.hybrid_core import balanced_tree, canonical, leaves

ROOT = Path(__file__).resolve().parent


def development_cases():
    rng = random.Random(2026093001)
    masks = [0, 1, (1 << 8) - 1, 0b10010110]
    masks += rng.sample([x for x in range(256) if x not in masks], 20)
    cases = [{'id': f'all_truth_n3_{m}', 'n': 3,
              'clauses': table_cnf(3, m), 'carrier': [[1, 3], [2]]}
             for m in masks]
    cases.extend([
        {'id': 'true_n6', 'n': 6, 'clauses': [],
         'carrier': [[1, 4], [2], [3], [5], [6]]},
        {'id': 'false_n6', 'n': 6, 'clauses': [[]],
         'carrier': [[1, 2], [3], [4], [5], [6]]},
        {'id': 'free_literal_n6', 'n': 6, 'clauses': [[-3]],
         'carrier': [[1, 2], [3, 5], [4], [6]]},
        {'id': 'tautology_n6', 'n': 6, 'clauses': [[1, -1]],
         'carrier': [[1, 3], [2, 5], [4], [6]]},
        {'id': 'crossing_n6', 'n': 6,
         'clauses': [[1, 3], [-3, 5], [2, 4], [-4, 6]],
         'carrier': [[1, 2], [3, 4], [5, 6]]},
        {'id': 'nested_n7', 'n': 7,
         'clauses': [[1, 2, 3], [-1, 4], [-4, 5], [2, -6], [3, 7]],
         'carrier': [[1, 7], [2, 6], [3], [4, 5]]},
    ])
    for source in timing_cases()[:5]:
        n = source['n']
        cases.append({'id': 'probe_regression_' + source['name'],
                      'n': n, 'clauses': source['clauses'],
                      'carrier': [[1, n], *[[v] for v in range(2, n)]]})
    cases.append({'id': 'new_planted_n8', 'n': 8,
                  'clauses': planted(8, 21, 2026093002),
                  'carrier': [[1, 8], [2, 7], [3, 6], [4, 5]]})
    cases.extend(factor_exposure_cases())
    return cases


def parity_signature(record):
    return [(x['round'], x['parent_tree'], x['tree'], x['score'],
             x['became_best'], x['sdd_size'], x['sdd_count'],
             x['direct_partition']) for x in record['trace']]


def run():
    started = perf_counter()
    counts = Counter()
    sample = []
    for case in development_cases():
        n, clauses, carrier = case['n'], case['clauses'], case['carrier']
        truth = exact_baseline(n, clauses)
        expected = None if truth is None else lcc(n, truth, carrier)
        records = {m: run_trial(m, case) for m in METHODS}
        assert set(records) == set(METHODS)
        for method, result in records.items():
            assert result['status'] == 'ok'
            assert result['satisfiable'] == (truth is not None)
            assert sorted(leaves(result['tree'])) == list(range(1, n + 1))
            if truth is None:
                assert result['exact'] is None and result['direct_partition'] is None
                counts['false_method_results'] += 1
            else:
                assert canonical(result['exact']['semantic_partition']) == truth
                assert canonical(result['exact']['partition']) == expected
                counts['nonfalse_method_results'] += 1
            assert result['timing_ns']['total_ns'] >= result['timing_ns']['search_stage_ns']
        assert (records['F1']['tree'], records['F1']['direct_partition']) == (
            records['L1']['tree'], records['L1']['direct_partition'])
        assert (records['F2']['tree'], records['F2']['direct_partition']) == (
            records['L2']['tree'], records['L2']['direct_partition'])
        assert parity_signature(records['F1']) == parity_signature(records['L1'])
        assert parity_signature(records['F2']) == parity_signature(records['L2'])
        assert records['F1']['rounds'] == records['L1']['rounds']
        assert records['F2']['rounds'] == records['L2']['rounds']
        if case['id'].startswith('exposure_'):
            assert truth is not None
            assert len(records['B3']['direct_partition']) < len(truth)
            for method in ('F1', 'L1', 'F2', 'L2'):
                assert records[method]['direct_partition'] == truth
                assert records[method]['exact']['sat_calls'] < records['B3']['exact']['sat_calls']
            counts['factor_exposure_controls'] += 1
        for suffix in ('1', '2'):
            assert records['L'+suffix]['timing_ns']['cnf_compilations'] == 1
            assert records['F'+suffix]['timing_ns']['cnf_compilations'] == 1 + len(records['F'+suffix]['trace'])
            assert len(records['L'+suffix]['trace']) <= 12
            counts['matched_candidate_evaluations'] += len(records['L'+suffix]['trace'])
        counts['cases'] += 1
        counts['method_runs'] += len(records)
        item = {'id': case['id'], 'method_runs': len(records),
                'nonfalse': truth is not None,
                'm1_candidates': len(records['L1']['trace']),
                'm2_candidates': len(records['L2']['trace']),
                'm1_final_tree': records['L1']['tree'],
                'm2_final_tree': records['L2']['tree']}
        if case['id'].startswith('exposure_'):
            item['semantic_partition'] = truth
            item['B3_direct_partition'] = records['B3']['direct_partition']
            item['L1_direct_partition'] = records['L1']['direct_partition']
            item['L2_direct_partition'] = records['L2']['direct_partition']
            item['residual_sat_calls'] = {m: records[m]['exact']['sat_calls']
                                          for m in ('B3', 'F1', 'L1', 'F2', 'L2')}
        sample.append(item)
        print('PASS', case['id'], flush=True)

    # Validate the SAT miter itself in both mismatch directions.
    with LiveSession(4, [[1]], balanced_tree(range(1, 5))) as session:
        assert equivalent_to_cnf(4, [[1]], session.root)
        assert not equivalent_to_cnf(4, [[-1]], session.root)
        assert not equivalent_to_cnf(4, [[]], session.root)
        counts['miter_positive_control'] += 1
        counts['miter_negative_controls'] += 2
    with LiveSession(4, [[]], balanced_tree(range(1, 5))) as session:
        assert equivalent_to_cnf(4, [[]], session.root)
        assert not equivalent_to_cnf(4, [], session.root)
        counts['miter_negative_controls'] += 1

    # B4 must be deterministic, syntax-only and component-preserving.
    separated = [[1, 4], [2, 5], [3, 6]]
    tree = separator_tree(6, separated)
    assert tree == separator_tree(6, separated)
    assert sorted(leaves(tree)) == list(range(1, 7))
    def has_cluster(t, required):
        if set(leaves(t)) == required:
            return True
        return not isinstance(t, int) and (has_cluster(t[0], required) or
                                           has_cluster(t[1], required))
    assert all(has_cluster(tree, set(block)) for block in separated)
    counts['separator_checks'] += 1

    # The intended fresh-process API must serialize each non-oracle method
    # without importing an evaluator or loading any campaign manifest.
    worker_case = development_cases()[-1]
    for method in METHODS:
        process = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'trial_worker.py')],
            input=json.dumps({'method': method, 'instance': worker_case}),
            text=True, capture_output=True, timeout=15, check=True)
        worker = json.loads(process.stdout)
        assert worker['method'] == method
        assert worker['status'] == 'ok'
        assert worker['exact'] is not None
        assert canonical(worker['exact']['partition']) == lcc(
            worker_case['n'], exact_baseline(worker_case['n'], worker_case['clauses']),
            worker_case['carrier'])
        counts['fresh_process_worker_checks'] += 1

    result = {'status': 'PASS', 'counts': dict(counts), 'seconds': perf_counter() - started,
              'cases': sample, 'campaign_inputs_executed': 0,
              'semantic_truth_supplied_to_workers': False}
    (ROOT / 'integration_correctness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'counts': dict(counts),
                      'seconds': result['seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    run()
