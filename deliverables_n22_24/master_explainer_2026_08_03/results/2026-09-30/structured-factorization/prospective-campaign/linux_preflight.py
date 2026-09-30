"""Linux-only capped-worker and larger live-SDD correctness gate.

Runs developmental inputs only. It neither loads a campaign manifest nor
creates a freeze/selection/results file. Every native worker is isolated,
address-space capped and subject to a parent watchdog.
"""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

from bounded_trial import MEMORY_CAP_BYTES, run_bounded, test_hard_cap
from dev_fixtures import factor_exposure_cases
from reference.benchmark import exact_baseline, lcc
from reference.hybrid_core import canonical

ROOT = Path(__file__).resolve().parent
LIMIT = MEMORY_CAP_BYTES
STRESS = ((20, 100), (24, 80))
SOURCE_FILES = ('requirements-lock.txt', 'bounded_trial.py', 'trial_worker.py',
                'resource_guard.py', 'integrated_pipeline.py', 'live_moves.py',
                'stress_worker.py', 'dev_fixtures.py', 'exact_miter.py',
                'campaign_inputs.py', 'campaign_integrity.py', 'campaign_runner.py',
                'check_harness.py', 'check_integration.py', 'check_stress.py',
                'linux_preflight.py', 'linux_scale_probe.py',
                'reference/benchmark.py', 'reference/hybrid_core.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cgroup_memory():
    path = Path('/sys/fs/cgroup/memory.max')
    return path.read_text().strip() if path.exists() else None


def stage_result(method, row):
    out = {'method': method, 'status': row['status'],
           'process_wall_ns': row['process_wall_ns'],
           'effective_cap_bytes': row.get('effective_cap_bytes')}
    if row['status'] == 'ok':
        out.update({'direct_partition': row['direct_partition'],
                    'exact_partition': row['exact']['semantic_partition'],
                    'sat_calls': row['exact']['sat_calls'],
                    'sdd_size': row['sdd_size'],
                    'cnf_compilations': row['timing_ns']['cnf_compilations'],
                    'search_stage_ns': row['timing_ns']['search_stage_ns'],
                    'exact_stage_ns': row['timing_ns']['exact_stage_ns'],
                    'peak_memory_bytes': row['peak_memory_bytes']})
    else:
        out.update({'returncode': row.get('returncode'),
                    'stderr_tail': row.get('stderr_tail')})
    return out


def run_stress(n, steps):
    env = os.environ.copy()
    env['LIVE_VTREE_RLIMIT_AS_BYTES'] = str(LIMIT)
    env['LIVE_VTREE_STRESS_PROGRESS'] = '1'
    start = perf_counter()
    try:
        proc = subprocess.run([sys.executable, '-B', str(ROOT / 'stress_worker.py'),
                               str(n), str(steps)], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired as error:
        tail = error.stderr or b''
        if isinstance(tail, bytes):
            tail = tail.decode(errors='replace')
        return {'n': n, 'steps': steps, 'status': 'timeout',
                'watchdog_seconds': 45, 'wall_seconds': perf_counter() - start,
                'progress_tail': tail[-1200:]}
    if proc.returncode != 0:
        return {'n': n, 'steps': steps, 'status': 'error',
                'returncode': proc.returncode, 'stderr_tail': proc.stderr[-1500:],
                'wall_seconds': perf_counter() - start}
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {'n': n, 'steps': steps, 'status': 'bad_output',
                'wall_seconds': perf_counter() - start}
    result['wall_seconds'] = perf_counter() - start
    return result


def run():
    if sys.platform != 'linux':
        raise SystemExit('Linux preflight requires Linux')
    start = perf_counter()
    result = {'status': 'RUNNING', 'utc': datetime.now(timezone.utc).isoformat(),
              'purpose': 'developmental Linux preflight only',
              'formal_campaign_inputs_executed': 0,
              'source_hashes': {name: digest(ROOT / name) for name in SOURCE_FILES},
              'environment': {'python': sys.version, 'platform': platform.platform(),
                              'machine': platform.machine(),
                              'cgroup_memory_max': read_cgroup_memory(),
                              'packages': {name: version(name) for name in
                                           ('PySDD', 'python-sat', 'psutil')},
                              'worker_rlimit_as_bytes': LIMIT},
              'stages': {}}
    try:
        test = test_hard_cap()
        result['stages']['actual_worker_allocation_negative_control'] = test
        if test['status'] != 'PASS':
            raise RuntimeError('Actual worker did not enforce allocation cap')

        case = factor_exposure_cases()[0]
        semantic = canonical(exact_baseline(case['n'], case['clauses']))
        final = canonical(lcc(case['n'], semantic, case['carrier']))
        methods = {}
        for method in ('B3', 'F1', 'L1', 'F2', 'L2'):
            row = run_bounded(method, case)
            methods[method] = stage_result(method, row)
            if (row['status'] != 'ok' or row.get('effective_cap_bytes') != LIMIT or
                canonical(row['exact']['semantic_partition']) != semantic or
                canonical(row['exact']['partition']) != final):
                raise RuntimeError(f'Capped developmental worker failed: {method}')
        result['stages']['actual_capped_workers'] = methods
        if not (len(methods['B3']['direct_partition']) < len(semantic) and
                all(methods[m]['direct_partition'] == semantic for m in
                    ('F1', 'L1', 'F2', 'L2')) and
                all(methods[m]['sat_calls'] < methods['B3']['sat_calls'] for m in
                    ('F1', 'L1', 'F2', 'L2')) and
                methods['L1']['cnf_compilations'] == methods['L2']['cnf_compilations'] == 1):
            raise RuntimeError('Capped workers did not reproduce factor exposure')

        watchdog = run_bounded('L1', case, timeout_seconds=0.25,
                               _worker_args=('--sleep-selftest',))
        signal = run_bounded('L1', case, _worker_args=('--signal-selftest',))
        result['stages']['actual_worker_failure_paths'] = {
            'watchdog_status': watchdog['status'],
            'signal_status': signal['status'],
            'signal_returncode': signal.get('returncode')}
        if watchdog['status'] != 'timeout' or signal['status'] != 'native_crash':
            raise RuntimeError('Actual watchdog or signal classification failed')

        large = []
        result['stages']['larger_sdd_walks'] = large
        for n, steps in STRESS:
            row = run_stress(n, steps)
            large.append(row)
            count = row.get('counts', {})
            if (row.get('status') != 'PASS' or
                row.get('effective_cap_bytes') != LIMIT or
                row.get('baseline_live_size', 0) <= 486 or
                row.get('ending_live_size') != row.get('baseline_live_size') or
                count.get('later_limit_failures', 0) <= 0 or
                count.get('sat_miter_checks') != count.get('extra_root_miter_checks') or
                count.get('fresh_structure_checks', 0) <= 0 or
                row.get('max_rss_bytes', LIMIT) >= LIMIT):
                raise RuntimeError(f'Larger live-SDD stress failed at n={n}')
        result['status'] = 'PASS'
    except Exception as error:
        result['status'] = 'FAIL'
        result['error_type'] = type(error).__name__
        result['error'] = str(error)
    finally:
        result['wall_seconds'] = perf_counter() - start
        (ROOT / 'linux_preflight_results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'status': result['status'],
                          'wall_seconds': result['wall_seconds'],
                          'stages': list(result['stages']),
                          'error': result.get('error')}), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    run()
