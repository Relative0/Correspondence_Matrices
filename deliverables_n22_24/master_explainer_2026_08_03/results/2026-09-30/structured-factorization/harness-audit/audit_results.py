"""Read-only audit of saved measurements; never compile or rerun a trial.

Writes only audit_results.json beside this script. Truth is evaluator-only.
Uses a fresh exhaustive projection-factor oracle, no experiment truth routine.
Run with the existing phase5b_output/.venv interpreter and -B.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SOURCE = PROJECT / 'live_integration_2026-09-30'
METHODS = ('B2', 'B3', 'B4', 'F1', 'F2', 'L1', 'L2')
sys.dont_write_bytecode = True


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): digest(p)
            for p in sorted(root.rglob('*')) if p.is_file()
            and '.git' not in p.parts and not p.name.startswith('.env')}


def canon(part):
    return sorted(sorted(b) for b in part)


def mask(block):
    return sum(1 << (v - 1) for v in block)


def relation(record):
    encoded = [(mask(set(x for x in c if x > 0)),
                mask(set(-x for x in c if x < 0))) for c in record['clauses']]
    return {a for a in range(1 << record['n'])
            if all((a & pos) or ((~a) & neg) for pos, neg in encoded)}


def factors(variables, rel):
    # R is always contained in the product of its two projections. Equality
    # therefore holds exactly when the cardinalities match. Try every anchored
    # proper cut; recursively factor both projections at the first equality.
    if len(variables) == 1:
        return [list(variables)]
    scope = mask(variables)
    for size in range(1, len(variables)):
        for extra in combinations(variables[1:], size - 1):
            left = (variables[0], *extra)
            lm = mask(left)
            rm = scope ^ lm
            lp = {a & lm for a in rel}
            rp = {a & rm for a in rel}
            if len(lp) * len(rp) == len(rel):
                right = tuple(v for v in variables if v not in left)
                return factors(left, lp) + factors(right, rp)
    return [list(variables)]


def coarsen(n, *partitions):
    blocks = [{v} for v in range(1, n + 1)]
    for part in partitions:
        for block in part:
            touching = [b for b in blocks if b.intersection(block)]
            blocks = [b for b in blocks if not b.intersection(block)]
            blocks.append(set().union(*touching))
    return canon(blocks)


def valid_factor_partition(n, rel, part):
    if any(not b for b in part) or sorted(v for b in part for v in b) != list(range(1, n + 1)):
        return False
    return math.prod(len({a & mask(b) for a in rel}) for b in part) == len(rel)


def tree(value):
    return value if isinstance(value, int) else tuple(tree(v) for v in value)


def neighborhood(t):
    if isinstance(t, int):
        return []
    a, b = t
    out = {(b, a)}
    if isinstance(a, tuple):
        out.add((a[0], (a[1], b)))
    if isinstance(b, tuple):
        out.add(((a, b[0]), b[1]))
    out.update((x, b) for x in neighborhood(a))
    out.update((a, x) for x in neighborhood(b))
    return sorted(out, key=repr)


def score(method, row):
    p = row['direct_partition']
    value = (-len(p) if method.endswith('1') else
             math.log2(1 + row['sdd_size']) +
             math.log2(1 + sum(2 ** (len(b) - 1) - 1 for b in p)))
    return value, repr(tree(row['tree']))


def geometric(values):
    return math.exp(statistics.mean(map(math.log, values)))


def upper(values, seed):
    rng = random.Random(seed)
    logs = list(map(math.log, values))
    return sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs))))
                  for _ in range(10000))[9499]


def guard_probes(records, rows):
    # In-memory faults only. Never invoke freeze/run_split/select/analyze.
    sys.path.insert(0, str(SOURCE))
    import campaign_runner as runner
    old_load, old_read = runner.load_manifest, runner.read_rows
    result = {}
    try:
        runner.load_manifest = lambda: records
        for fault in ('duplicate_repetition', 'missing_correctness_flags', 'negative_timing'):
            damaged = deepcopy(rows)
            if fault == 'duplicate_repetition':
                target = damaged[0]
                other = next(r for r in damaged if r['id'] == target['id'] and
                             r['method'] == target['method'] and r['rep'] != target['rep'])
                target['rep'] = other['rep']
            elif fault == 'missing_correctness_flags':
                for row in damaged:
                    row.pop('semantic_correct')
                    row.pop('carrier_correct')
            else:
                damaged[0]['timing_ns']['total_ns'] = -1
            runner.read_rows = lambda split: damaged
            try:
                accepted = runner.complete_rows('heldout')
                runner.per_instance_costs(accepted)
                result[fault] = 'ACCEPTED_BY_ROW_AND_REPETITION_GUARDS'
            except Exception as exc:
                result[fault] = 'REJECTED: ' + type(exc).__name__
    finally:
        runner.load_manifest, runner.read_rows = old_load, old_read
    return result


def main():
    # Independent controls for this auditor: every nonempty two-bit relation,
    # ternary parity, and a nontrivial product with a free variable.
    for bits in range(1, 16):
        rel = {a for a in range(4) if bits & (1 << a)}
        rectangular = len(rel) == len({a & 1 for a in rel}) * len({a & 2 for a in rel})
        assert canon(factors((1, 2), rel)) == ([[1], [2]] if rectangular else [[1, 2]])
    assert canon(factors((1, 2, 3), {0, 3, 5, 6})) == [[1, 2, 3]]
    assert canon(factors((1, 2, 3), {0, 3, 4, 7})) == [[1, 2], [3]]
    assert relation({'n': 2, 'clauses': [[]]}) == set()
    assert relation({'n': 2, 'clauses': [[1, -1]]}) == set(range(4))
    original_inventory = inventory(SOURCE)
    load = lambda name: json.loads((SOURCE / name).read_text())
    freeze = load('campaign_freeze.json')
    manifest = load('candidate_manifest.json')['records']
    records = {r['id']: r for r in manifest}
    analysis = load('campaign_analysis.json')
    choice = load('baseline_selection.json')
    rows = {split: [json.loads(line) for line in
                   (SOURCE / f'{split}_results.jsonl').read_text().splitlines()]
            for split in ('validation', 'heldout')}
    problems = []

    def check(ok, message):
        if not ok:
            problems.append(message)

    source_matches = {name: digest(SOURCE / name) == expected
                      for name, expected in freeze['source_hashes'].items()}
    check(all(source_matches.values()), 'Frozen source drift')
    for split in rows:
        work = [(r['id'], method, rep) for r in manifest if r['split'] == split
                for method in METHODS for rep in range(3)]
        random.Random(2026093019 + (split == 'heldout')).shuffle(work)
        actual = [(r['id'], r['method'], r['rep']) for r in rows[split]]
        check(actual == work, f'{split}: keys/order differ from registered jobs')
        check(len(actual) == len(set(actual)), f'{split}: duplicate keys')
        check(digest(SOURCE / f'{split}_results.jsonl') == analysis[f'{split}_sha256'],
              f'{split}: analysis row hash mismatch')
    check(digest(SOURCE / 'campaign_freeze.json') == analysis['freeze_sha256'], 'Freeze hash')
    check(choice['validation_results_sha256'] == analysis['validation_sha256'], 'Selection hash')

    truth, headroom, model_counts = {}, {}, {}
    allrows = rows['validation'] + rows['heldout']
    index = {(r['id'], r['method'], r['rep']): r for r in allrows}
    unique_direct_checks = 0
    for instance in manifest:
        id_, n = instance['id'], instance['n']
        rel = relation(instance)
        check(bool(rel), f'{id_}: false input')
        prime = canon(factors(tuple(range(1, n + 1)), rel))
        final = coarsen(n, prime, instance['carrier'])
        truth[id_] = prime
        model_counts[id_] = len(rel)
        partition_cache = set()
        for row in (r for r in allrows if r['id'] == id_):
            key = (id_, row['method'], row['rep'])
            check(row['status'] == 'ok', f'{key}: unsuccessful')
            check(row.get('semantic_correct') is True and row.get('carrier_correct') is True,
                  f'{key}: missing/false correctness flag')
            check(row['n'] == n and row['family'] == instance['family'] and
                  row['split'] == instance['split'], f'{key}: identity mismatch')
            check(canon(row['exact']['semantic_partition']) == prime and
                  canon(row['exact']['partition']) == final, f'{key}: independent truth mismatch')
            timing = row['timing_ns']
            check(timing['total_ns'] == timing['search_stage_ns'] + timing['exact_stage_ns'],
                  f'{key}: timing sum')
            check(all(isinstance(v, int) and v >= 0 for v in timing.values()) and
                  0 < timing['total_ns'] <= row['process_wall_ns'], f'{key}: invalid timing')
            check(row['cap_bytes'] == 2 * 1024**3 and row['timeout_seconds'] == 20,
                  f'{key}: cap metadata')
            for state in [row, *row['trace']]:
                part = tuple(tuple(b) for b in canon(state['direct_partition']))
                if part not in partition_cache:
                    check(valid_factor_partition(n, rel, part), f'{key}: invalid direct factorization')
                    partition_cache.add(part)
                    unique_direct_checks += 1
        baseline = index[id_, 'B3', 0]
        headroom[id_] = {'prime': prime, 'B3_direct': baseline['direct_partition'],
                         'missing_prime_blocks': len(prime) - len(baseline['direct_partition']),
                         'B3_already_finest': canon(baseline['direct_partition']) == prime}
        print(f'Checked {id_}; models={len(rel)}; B3_finest={headroom[id_]["B3_already_finest"]}', flush=True)

    trace_count = 0
    rounded_scores = 0
    max_score_difference_ulps = 0
    parity_pairs = Counter()
    for row in allrows:
        method, id_, rep = row['method'], row['id'], row['rep']
        if method[0] not in 'FL':
            continue
        current = index[id_, 'B3', rep]
        seen = {repr(tree(current['tree']))}
        for round_no, round_record in enumerate(row['rounds']):
            candidates = [t for t in neighborhood(tree(current['tree'])) if repr(t) not in seen][:6]
            entries = [t for t in row['trace'] if t['round'] == round_no]
            check([tree(t['tree']) for t in entries] == candidates, f'{id_}/{method}/{rep}: candidates')
            check(round_record['considered'] == len(candidates), f'{id_}/{method}/{rep}: batch count')
            best = current
            for t in entries:
                seen.add(repr(tree(t['tree'])))
                check(tree(t['parent_tree']) == tree(current['tree']), f'{id_}/{method}/{rep}: parent')
                computed = score(method, t)
                delta_ulps = abs(t['score'][0] - computed[0]) / math.ulp(float(computed[0]))
                rounded_scores += delta_ulps > 0
                max_score_difference_ulps = max(max_score_difference_ulps, delta_ulps)
                # Linux versus Windows libm may differ at the last bit. Keep
                # exact tree ties and acceptance checks; allow two score ULPs.
                check(t['score'][1] == computed[1] and delta_ulps <= 2,
                      f'{id_}/{method}/{rep}: score')
                better = score(method, t) < score(method, best)
                check(t['became_best'] == better, f'{id_}/{method}/{rep}: acceptance')
                if better:
                    best = t
                trace_count += 1
            check(tree(round_record['selected_tree']) == tree(best['tree']), f'{id_}/{method}/{rep}: winner')
            if tree(best['tree']) == tree(current['tree']):
                check(round_no == len(row['rounds']) - 1, f'{id_}/{method}/{rep}: stop')
            current = best
        check(len(row['rounds']) <= 2 and tree(row['tree']) == tree(current['tree']),
              f'{id_}/{method}/{rep}: final/round cap')
        check(row['timing_ns']['cnf_compilations'] == (1 if method[0] == 'L' else 1 + len(row['trace'])),
              f'{id_}/{method}/{rep}: compile count')
        if method[0] == 'L':
            fresh = index[id_, 'F' + method[-1], rep]
            fields = ('tree', 'direct_partition', 'rounds', 'sdd_size', 'sdd_count')
            sig = lambda r: [{k: t[k] for k in ('round', 'parent_tree', 'tree', 'score',
                                               'became_best', 'sdd_size', 'sdd_count', 'direct_partition')}
                             for t in r['trace']]
            check(all(row[k] == fresh[k] for k in fields) and sig(row) == sig(fresh),
                  f'{id_}/{method}/{rep}: fresh/live parity')
            parity_pairs[method] += 1

    medians = {}
    for metric in ('total_ns', 'process_wall_ns'):
        for instance in manifest:
            for method in METHODS:
                values = [index[instance['id'], method, rep] for rep in range(3)]
                medians[metric, method, instance['id']] = statistics.median(
                    r[metric] if metric == 'process_wall_ns' else r['timing_ns'][metric] for r in values)
    ids = {split: sorted(r['id'] for r in manifest if r['split'] == split) for split in rows}
    estimates = {m: geometric([medians['total_ns', m, id_] for id_ in ids['validation']]) for m in METHODS}
    selected = (min(METHODS[:3], key=lambda m: (estimates[m], m)),
                min(('L1', 'L2'), key=lambda m: (estimates[m], m)))
    check(selected == (choice['baseline'], choice['challenger']), 'Selection mismatch')
    check(all(math.isclose(estimates[m], choice['validation_geometric_total_ns'][m], rel_tol=1e-12)
              for m in METHODS), 'Selection estimates mismatch')
    ratios = [medians['total_ns', selected[1], i] / medians['total_ns', selected[0], i] for i in ids['heldout']]
    primary = {'geometric_ratio': geometric(ratios), 'upper_95': upper(ratios, 2026093021)}
    check(math.isclose(primary['geometric_ratio'], analysis['paired_geometric_total_ratio'], rel_tol=1e-12)
          and math.isclose(primary['upper_95'], analysis['paired_bootstrap_upper_95'], rel_tol=1e-12), 'Primary arithmetic')
    family_ratios = defaultdict(list)
    for id_, ratio in zip(ids['heldout'], ratios):
        family_ratios[records[id_]['family']].append(ratio)
    family_geometric = {k: geometric(v) for k, v in sorted(family_ratios.items())}
    sensitivities = {'family_cluster_bootstrap_upper_95': upper(list(family_geometric.values()), 2026093021),
                     'family_geometric_ratios': family_geometric,
                     'process_wall_ratio': geometric([medians['process_wall_ns', selected[1], i] /
                                                      medians['process_wall_ns', selected[0], i] for i in ids['heldout']])}
    mechanism = {}
    for digit in ('1', '2'):
        live, fresh = 'L' + digit, 'F' + digit
        values = [statistics.median(index[i, live, rep]['timing_ns']['search_stage_ns'] /
                                    index[i, fresh, rep]['timing_ns']['search_stage_ns'] for rep in range(3))
                  for i in ids['heldout']]
        mechanism[live] = {'geometric_ratio': geometric(values), 'upper_95': upper(values, 2026093022 + int(digit))}
        check(all(math.isclose(value, analysis['mechanism_search_ratios'][live][key], rel_tol=1e-12)
                  for key, value in mechanism[live].items()), f'{live}: mechanism arithmetic')

    before = json.loads((PROJECT / 'live_vtree_probe_2026-09-29/archive_before.json').read_text())
    archive_now = {}
    for directory in ('continuity_archive', 'phase5b_output'):
        archive_now.update({directory + '/' + k: v for k, v in inventory(PROJECT / directory).items()})
    changes = sorted(k for k in before.keys() | archive_now.keys() if before.get(k) != archive_now.get(k))
    check(not changes, 'Protected archive changes')
    probes = guard_probes(manifest, rows['heldout'])
    unchanged = original_inventory == inventory(SOURCE)
    check(unchanged, 'Audit modified integration files')
    result = {'audit_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'SAVED_DATA_CHECKS_PASS' if not problems else 'FAIL',
              'problems': problems, 'source_hashes_match': source_matches,
              'row_counts': {k: len(v) for k, v in rows.items()},
              'fresh_live_pairs_checked': dict(parity_pairs), 'trace_entries_checked': trace_count,
              'audit_oracle_controls': 19,
              'score_recomputations_with_roundoff': rounded_scores,
              'max_score_difference_ulps': max_score_difference_ulps,
              'unique_direct_factorizations_checked': unique_direct_checks,
              'headroom': headroom, 'model_counts': model_counts,
              'B3_already_finest_counts': {s: sum(headroom[i]['B3_already_finest'] for i in ids[s]) for s in ids},
              'selection_recomputed': selected, 'primary_recomputed': primary,
              'mechanism_recomputed': mechanism, 'exploratory_sensitivity_only': sensitivities,
              'harness_fault_injections': probes,
              'protected_archive_files': len(before), 'archive_changes': changes,
              'integration_files_unchanged_by_audit': unchanged,
              'integration_inventory': original_inventory,
              'trial_executions': 0, 'remote_resources_created': 0}
    (HERE / 'audit_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'problems', 'B3_already_finest_counts',
                                            'primary_recomputed', 'exploratory_sensitivity_only',
                                            'harness_fault_injections', 'trace_entries_checked')}, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
