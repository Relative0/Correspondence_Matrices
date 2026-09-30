"""Launch hostile native moves in capped child processes."""
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep

import psutil

ROOT = Path(__file__).resolve().parent
WORKERS = [(12, 100), (16, 80)]
WALL_CAP_SECONDS = 30
MEMORY_CHECK_BYTES = 1024 ** 3


def run_worker(n, steps):
    started = perf_counter()
    child = subprocess.Popen([sys.executable, '-B', str(ROOT / 'stress_worker.py'),
                              str(n), str(steps)], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    process = psutil.Process(child.pid)
    max_rss = 0
    reason = None
    while child.poll() is None:
        if perf_counter() - started > WALL_CAP_SECONDS:
            reason = 'watchdog_timeout'
            child.kill()
            break
        try:
            max_rss = max(max_rss, process.memory_info().rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        # External RSS on this managed Windows host reports the child's
        # initial ~6 MB throughout execution. Retain it as advisory only;
        # the worker checks its own peak high-water mark after every step.
        sleep(0.05)
    stdout, stderr = child.communicate(timeout=5)
    if reason or child.returncode != 0:
        return {'status': 'FAIL', 'n': n, 'steps': steps,
                'reason': reason or 'child_error', 'exit_code': child.returncode,
                'max_observed_rss_bytes': max_rss, 'stderr_tail': stderr[-3000:],
                'stdout_tail': stdout[-1000:]}
    result = json.loads(stdout)
    result['max_observed_rss_bytes'] = max_rss
    result['wall_seconds'] = perf_counter() - started
    assert result['status'] == 'PASS'
    assert result['counts']['limited_failures'] > 0
    assert result['counts']['forward_successes'] > 0
    assert result['counts']['long_sequence_restorations'] > 0
    assert result['max_peak_wset_bytes'] <= MEMORY_CHECK_BYTES
    return result


def run():
    rows = []
    for n, steps in WORKERS:
        row = run_worker(n, steps)
        rows.append(row)
        print(json.dumps(row), flush=True)
        if row['status'] != 'PASS':
            break
    output = {'status': 'PASS' if len(rows) == len(WORKERS) and
              all(r['status'] == 'PASS' for r in rows) else 'FAIL',
              'wall_cap_seconds_per_worker': WALL_CAP_SECONDS,
              'worker_sampled_peak_limit_bytes': MEMORY_CHECK_BYTES,
              'memory_limit_is_hard': False,
              'external_rss_advisory_only': True,
              'workers': rows}
    (ROOT / 'stress_summary.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'workers': len(rows)}), flush=True)
    if output['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    run()
