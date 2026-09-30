"""Frozen sequential integration gate. Linux only; no historical campaign runs.

Usage: python -B campaign_runner.py freeze|validation|select|heldout|analyze
The independent evaluator stays in this parent process, never in a worker
payload or non-oracle objective. Run only after the Linux hard-cap self-test.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys

from bounded_trial import MEMORY_CAP_BYTES, TIMEOUT_SECONDS, run_bounded, test_hard_cap
from campaign_inputs import FAMILIES, ROOT, compare_archived, generate_manifest
from integrated_pipeline import METHODS
from reference.benchmark import exact_baseline, lcc
from reference.hybrid_core import canonical

REPETITIONS = (0, 1, 2)
PAR2_NS = 40 * 10**9
CAMPAIGN_CEILING_SECONDS = 90 * 60
SEED = 2026093019
FILES = ('CAMPAIGN_PROTOCOL.md', 'candidate_manifest.json',
         'requirements-lock.txt', 'bounded_trial.py', 'campaign_inputs.py',
         'campaign_runner.py', 'trial_worker.py', 'integrated_pipeline.py',
         'live_moves.py', 'reference/benchmark.py', 'reference/hybrid_core.py')
FREEZE = ROOT / 'campaign_freeze.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    data = json.loads((ROOT / 'candidate_manifest.json').read_text())
    if data != generate_manifest():
        raise RuntimeError('Manifest differs from deterministic generator')
    compare_archived(data)
    records = data['records']
    if Counter(r['split'] for r in records) != {'validation': 12, 'heldout': 24}:
        raise RuntimeError('Unexpected split counts')
    for split, families in FAMILIES.items():
        if {r['family'] for r in records if r['split'] == split} != set(families):
            raise RuntimeError('Unexpected family reservation')
    return records


def source_hashes():
    return {name: digest(ROOT / name) for name in FILES}


def freeze():
    if sys.platform != 'linux':
        raise RuntimeError('Freeze requires the intended Linux execution host')
    if FREEZE.exists() or any((ROOT / f'{s}_results.jsonl').exists()
                              for s in ('validation', 'heldout')):
        raise RuntimeError('Freeze/results already exist; do not overwrite')
    records = load_manifest()
    cap_test = test_hard_cap()
    if cap_test['status'] != 'PASS':
        raise RuntimeError(f'Hard memory cap self-test failed: {cap_test}')
    from dev_fixtures import planted
    smoke = {'id': 'linux_cap_smoke_n8', 'n': 8,
             'clauses': planted(8, 24, 2026093021),
             'carrier': [[v] for v in range(1, 9)]}
    smoke_result = run_bounded('L1', smoke)
    semantic, final = truth_for(smoke)
    if (smoke_result['status'] != 'ok' or
        canonical(smoke_result['exact']['semantic_partition']) != semantic or
        canonical(smoke_result['exact']['partition']) != final):
        raise RuntimeError(f'2 GiB PySDD smoke failed: {smoke_result}')
    pip = subprocess.run([sys.executable, '-m', 'pip', 'freeze'],
                         text=True, capture_output=True, check=True)
    environment = {'python': sys.version, 'platform': platform.platform(),
                   'machine': platform.machine(), 'pip_freeze': pip.stdout,
                   'memory_cap_self_test': cap_test,
                   'capped_pysdd_smoke_peak_bytes': smoke_result['peak_memory_bytes']}
    receipt = {'utc': datetime.now(timezone.utc).isoformat(),
               'source_hashes': source_hashes(), 'environment': environment,
               'worker_cap_bytes': MEMORY_CAP_BYTES,
               'watchdog_seconds': TIMEOUT_SECONDS, 'par2_ns': PAR2_NS,
               'campaign_ceiling_seconds': CAMPAIGN_CEILING_SECONDS,
               'seed': SEED, 'methods': METHODS, 'repetitions': REPETITIONS,
               'instance_ids': [r['id'] for r in records]}
    FREEZE.write_text(json.dumps(receipt, indent=2) + '\n')
    return {'status': 'FROZEN', 'receipt_sha256': digest(FREEZE),
            'instance_count': len(records), 'environment': environment}


def verify_freeze():
    if sys.platform != 'linux' or not FREEZE.exists():
        raise RuntimeError('Frozen Linux receipt is required')
    receipt = json.loads(FREEZE.read_text())
    if receipt['source_hashes'] != source_hashes():
        raise RuntimeError('Source/protocol/manifest hash drift')
    pip = subprocess.run([sys.executable, '-m', 'pip', 'freeze'],
                         text=True, capture_output=True, check=True)
    if (receipt['environment']['python'] != sys.version or
        receipt['environment']['platform'] != platform.platform() or
        receipt['environment']['machine'] != platform.machine() or
        receipt['environment']['pip_freeze'] != pip.stdout):
        raise RuntimeError('Execution environment changed since freeze')
    if receipt['instance_ids'] != [r['id'] for r in load_manifest()]:
        raise RuntimeError('Manifest membership drift')
    if (receipt['worker_cap_bytes'], receipt['watchdog_seconds'],
        receipt['par2_ns'], receipt['campaign_ceiling_seconds']) != (
            MEMORY_CAP_BYTES, TIMEOUT_SECONDS, PAR2_NS, CAMPAIGN_CEILING_SECONDS):
        raise RuntimeError('Resource limits changed')
    return receipt


def truth_for(instance):
    semantic = exact_baseline(instance['n'], instance['clauses'])
    if semantic is None:
        raise RuntimeError(f'False input outside nonfalse campaign: {instance["id"]}')
    return canonical(semantic), canonical(lcc(instance['n'], semantic,
                                               instance['carrier']))


def jobs(split, records):
    work = [(r, method, rep) for r in records if r['split'] == split
            for method in METHODS for rep in REPETITIONS]
    random.Random(SEED + (0 if split == 'validation' else 1)).shuffle(work)
    return work


def read_rows(split):
    path = ROOT / f'{split}_results.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def run_split(split):
    verify_freeze()
    if split == 'heldout':
        selection = load_selection()
        if selection['validation_results_sha256'] != digest(ROOT / 'validation_results.jsonl'):
            raise RuntimeError('Validation rows changed since method selection')
    elif (ROOT / 'heldout_results.jsonl').exists():
        raise RuntimeError('Validation may not run after held-out starts')
    records = load_manifest()
    expected = jobs(split, records)
    path = ROOT / f'{split}_results.jsonl'
    old = read_rows(split)
    done = {(x['id'], x['method'], x['rep']) for x in old}
    if len(done) != len(old) or not done.issubset(
            {(r['id'], m, rep) for r, m, rep in expected}):
        raise RuntimeError('Duplicate or unexpected existing row')
    spent_ns = sum(x['process_wall_ns'] for x in
                   read_rows('validation') + read_rows('heldout'))
    truth_cache = {}
    for instance, method, rep in expected:
        key = instance['id'], method, rep
        if key in done:
            continue
        if spent_ns >= CAMPAIGN_CEILING_SECONDS * 10**9:
            print(json.dumps({'status': 'CENSORED', 'split': split,
                              'reason': 'campaign wall ceiling'}), flush=True)
            return
        result = run_bounded(method, instance)
        spent_ns += result['process_wall_ns']
        result.update(split=split, family=instance['family'], rep=rep)
        if result['status'] == 'ok':
            if instance['id'] not in truth_cache:
                truth_cache[instance['id']] = truth_for(instance)
            semantic, final = truth_cache[instance['id']]
            result['semantic_correct'] = (canonical(result['exact']['semantic_partition'])
                                          == semantic)
            result['carrier_correct'] = canonical(result['exact']['partition']) == final
        else:
            result.update(semantic_correct=None, carrier_correct=None)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result, separators=(',', ':')) + '\n')
        done.add(key)
        if result['semantic_correct'] is False or result['carrier_correct'] is False:
            raise RuntimeError(f'Independent exactness failure at {key}; stopped')
        if len(done) % 25 == 0:
            print(json.dumps({'split': split, 'completed': len(done),
                              'expected': len(expected)}), flush=True)
    print(json.dumps({'split': split, 'completed': len(done),
                      'expected': len(expected), 'status': 'COMPLETE'}), flush=True)


def complete_rows(split):
    records = load_manifest()
    rows = read_rows(split)
    if len(rows) != len(jobs(split, records)):
        raise RuntimeError(f'{split} results incomplete')
    if any(row.get('semantic_correct') is False or
           row.get('carrier_correct') is False for row in rows):
        raise RuntimeError(f'{split} has exactness discrepancies')
    return rows


def cost_ns(row):
    return (row['timing_ns']['total_ns'] if row['status'] == 'ok' else PAR2_NS)


def per_instance_costs(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['method'], row['id']].append(cost_ns(row))
    if any(len(x) != len(REPETITIONS) for x in grouped.values()):
        raise RuntimeError('Missing repetitions')
    return {key: statistics.median(values) for key, values in grouped.items()}


def geometric(values):
    return math.exp(statistics.mean(math.log(x) for x in values))


def select():
    verify_freeze()
    if (ROOT / 'baseline_selection.json').exists():
        raise RuntimeError('Selection already locked')
    rows = complete_rows('validation')
    medians = per_instance_costs(rows)
    ids = sorted({x['id'] for x in rows})
    estimates = {m: geometric([medians[m, i] for i in ids])
                 for m in METHODS}
    baseline = min(('B2', 'B3', 'B4'), key=lambda m: (estimates[m], m))
    challenger = min(('L1', 'L2'), key=lambda m: (estimates[m], m))
    choice = {'utc': datetime.now(timezone.utc).isoformat(),
              'validation_results_sha256': digest(ROOT / 'validation_results.jsonl'),
              'baseline': baseline, 'challenger': challenger,
              'validation_geometric_total_ns': estimates}
    (ROOT / 'baseline_selection.json').write_text(json.dumps(choice, indent=2) + '\n')
    return choice


def load_selection():
    choice = json.loads((ROOT / 'baseline_selection.json').read_text())
    if choice['baseline'] not in ('B2', 'B3', 'B4') or choice['challenger'] not in ('L1', 'L2'):
        raise RuntimeError('Invalid locked method selection')
    return choice


def bootstrap_upper(ratios, *, seed):
    rng = random.Random(seed)
    logs = [math.log(x) for x in ratios]
    draws = [math.exp(statistics.mean(rng.choices(logs, k=len(logs))))
             for _ in range(10000)]
    return sorted(draws)[9499]


def analyze():
    verify_freeze()
    choice = load_selection()
    if choice['validation_results_sha256'] != digest(ROOT / 'validation_results.jsonl'):
        raise RuntimeError('Validation results changed')
    rows = complete_rows('heldout')
    costs = per_instance_costs(rows)
    ids = sorted({x['id'] for x in rows})
    baseline, challenger = choice['baseline'], choice['challenger']
    ratios = [costs[challenger, i] / costs[baseline, i] for i in ids]
    failures = Counter(x['method'] for x in rows if x['status'] != 'ok')
    primary_ratio = geometric(ratios)
    primary_upper = bootstrap_upper(ratios, seed=SEED + 2)
    pair_parity = {}
    search_ratios = {}
    for f, live in (('F1', 'L1'), ('F2', 'L2')):
        paired = defaultdict(dict)
        for x in rows:
            if x['method'] in (f, live):
                paired[x['id'], x['rep']][x['method']] = x
        mismatches = []
        search = defaultdict(list)
        for (id_, rep), pair in paired.items():
            a, b = pair[f], pair[live]
            if a['status'] != 'ok' or b['status'] != 'ok':
                continue
            fields = ('tree', 'direct_partition', 'rounds')
            if any(a[k] != b[k] for k in fields):
                mismatches.append((id_, rep))
            if (canonical(a['exact']['semantic_partition']) !=
                canonical(b['exact']['semantic_partition']) or
                canonical(a['exact']['partition']) !=
                canonical(b['exact']['partition'])):
                mismatches.append((id_, rep))
            signature = lambda row: [
                (t['round'], t['parent_tree'], t['tree'], t['score'],
                 t['became_best'], t['sdd_size'], t['sdd_count'],
                 t['direct_partition']) for t in row['trace']]
            if signature(a) != signature(b):
                mismatches.append((id_, rep))
            search[id_].append(b['timing_ns']['search_stage_ns'] /
                               a['timing_ns']['search_stage_ns'])
        means = [statistics.median(search[i]) for i in ids if len(search[i]) == 3]
        pair_parity[live] = {'mismatches': mismatches,
                             'complete_pairs': len(means)}
        search_ratios[live] = {'geometric_ratio': geometric(means) if means else None,
                               'upper_95': bootstrap_upper(means, seed=SEED + int(live[-1]) + 3)
                               if means else None}
    no_excess_failures = failures[challenger] <= failures[baseline]
    result = {'baseline': baseline, 'challenger': challenger,
              'heldout_instances': len(ids), 'heldout_rows': len(rows),
              'failure_counts': dict(failures),
              'paired_geometric_total_ratio': primary_ratio,
              'paired_bootstrap_upper_95': primary_upper,
              'per_instance_ratios': dict(zip(ids, ratios)),
              'mechanism_parity': pair_parity,
              'mechanism_search_ratios': search_ratios,
              'algorithmic_go': no_excess_failures and primary_ratio <= .90 and
                                primary_upper < 1 and not any(
                                    x.get('semantic_correct') is False or
                                    x.get('carrier_correct') is False for x in rows),
              'freeze_sha256': digest(FREEZE),
              'validation_sha256': digest(ROOT / 'validation_results.jsonl'),
              'heldout_sha256': digest(ROOT / 'heldout_results.jsonl')}
    (ROOT / 'campaign_analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) == 2 else ''
    if command == 'freeze':
        print(json.dumps(freeze(), indent=2))
    elif command in ('validation', 'heldout'):
        run_split(command)
    elif command == 'select':
        print(json.dumps(select(), indent=2))
    elif command == 'analyze':
        print(json.dumps(analyze(), indent=2))
    else:
        raise SystemExit('Usage: campaign_runner.py freeze|validation|select|heldout|analyze')
