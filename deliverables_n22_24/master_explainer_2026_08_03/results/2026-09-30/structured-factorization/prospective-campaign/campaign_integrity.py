"""Strict, non-oracle validation for a prospective campaign's saved records."""
from collections import defaultdict
import math
import statistics

FAILURES = frozenset({'timeout', 'memory_cap', 'killed', 'native_crash',
                      'error', 'bad_output'})


def positive_int(value):
    return type(value) is int and value > 0


def partition(value, n):
    return (isinstance(value, list) and
            all(isinstance(b, list) and b and all(type(v) is int for v in b) for b in value)
            and sorted(v for b in value for v in b) == list(range(1, n + 1)))


def validate_row(row, instance, split, methods, repetitions, cap_bytes,
                 timeout_seconds, freeze_sha256, selection_sha256=None):
    if not isinstance(row, dict):
        raise ValueError('Result is not an object')
    key = (row.get('id'), row.get('method'), row.get('rep'))
    if (row.get('id') != instance['id'] or row.get('method') not in methods or
        row.get('rep') not in repetitions or row.get('split') != split or
        row.get('family') != instance['family'] or
        row.get('freeze_sha256') != freeze_sha256 or
        row.get('cap_bytes') != cap_bytes or
        row.get('timeout_seconds') != timeout_seconds or
        (split == 'heldout' and row.get('selection_sha256') != selection_sha256) or
        not positive_int(row.get('process_wall_ns'))):
        raise ValueError(f'Row identity, provenance or resource mismatch: {key}')
    status = row.get('status')
    if status == 'ok':
        if (row.get('n') != instance['n'] or row.get('satisfiable') is not True or
            row.get('semantic_correct') is not True or
            row.get('carrier_correct') is not True or
            row.get('effective_cap_bytes') != cap_bytes or
            not partition(row.get('direct_partition'), instance['n']) or
            not isinstance(row.get('exact'), dict) or
            not partition(row['exact'].get('semantic_partition'), instance['n']) or
            not partition(row['exact'].get('partition'), instance['n']) or
            not isinstance(row.get('trace'), list) or
            not isinstance(row.get('rounds'), list)):
            raise ValueError(f'Malformed successful result: {key}')
        costs = row.get('timing_ns')
        if (not isinstance(costs, dict) or
            not all(type(x) is int and x >= 0 for x in costs.values()) or
            not all(positive_int(costs.get(k)) for k in
                    ('total_ns', 'search_stage_ns', 'exact_stage_ns')) or
            costs['total_ns'] != costs['search_stage_ns'] + costs['exact_stage_ns'] or
            costs['total_ns'] > row['process_wall_ns'] or
            not positive_int(row.get('peak_memory_bytes')) or
            not (type(row['exact'].get('sat_calls')) is int and
                 row['exact']['sat_calls'] >= 0)):
            raise ValueError(f'Malformed timing or SAT accounting: {key}')
    elif status in FAILURES:
        if row.get('semantic_correct') is not None or row.get('carrier_correct') is not None:
            raise ValueError(f'Failed row has correctness claims: {key}')
    else:
        raise ValueError(f'Unknown result status: {key}')


def validate_rows(rows, instances, split, expected_order, methods,
                  repetitions, cap_bytes, timeout_seconds, freeze_sha256,
                  selection_sha256=None, *, complete):
    if not isinstance(rows, list) or len(rows) > len(expected_order):
        raise ValueError('Too many result rows')
    if any(not isinstance(r, dict) for r in rows):
        raise ValueError('Result row is not an object')
    keys = [(r.get('id'), r.get('method'), r.get('rep')) for r in rows]
    if len(set(keys)) != len(keys) or keys != expected_order[:len(keys)]:
        raise ValueError('Result keys are duplicated, missing, or out of order')
    if complete and len(keys) != len(expected_order):
        raise ValueError(f'{split} results incomplete')
    for row in rows:
        validate_row(row, instances[row['id']], split, methods, repetitions,
                     cap_bytes, timeout_seconds, freeze_sha256, selection_sha256)
    return rows


def selection_values(rows, instance_ids, methods, repetitions, par2_ns):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row['method'], row['id']][row['rep']] = (
            row['timing_ns']['total_ns'] if row['status'] == 'ok' else par2_ns)
    medians = {}
    for method in methods:
        for id_ in instance_ids:
            values = grouped[method, id_]
            if set(values) != set(repetitions):
                raise ValueError(f'Missing selection observations for {(method, id_)}')
            medians[method, id_] = statistics.median(values.values())
    estimates = {method: math.exp(statistics.mean(
        math.log(medians[method, id_]) for id_ in instance_ids)) for method in methods}
    baseline = min(('B2', 'B3', 'B4'), key=lambda method: (estimates[method], method))
    challenger = min(('L1', 'L2'), key=lambda method: (estimates[method], method))
    return estimates, baseline, challenger
