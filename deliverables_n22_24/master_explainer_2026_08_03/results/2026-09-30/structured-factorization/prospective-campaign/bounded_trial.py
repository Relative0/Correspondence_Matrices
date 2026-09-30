"""Linux-only isolated trial and an adversarial hard-cap self-test.

RLIMIT_AS is a hard limit on each worker's virtual address space. A fresh
process and wall watchdog also bound failures in native PySDD code. RSS is
reported separately; it is not used as a substitute for an enforced cap.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parent
WORKER = ROOT / 'trial_worker.py'
MEMORY_CAP_BYTES = 2 * 1024 ** 3
TIMEOUT_SECONDS = 20


def run_bounded(method, instance, *, cap_bytes=MEMORY_CAP_BYTES,
                timeout_seconds=TIMEOUT_SECONDS, _worker_args=()):
    if sys.platform != 'linux':
        raise RuntimeError('Formal bounded trials require Linux')
    env = os.environ.copy()
    env['LIVE_VTREE_RLIMIT_AS_BYTES'] = str(cap_bytes)
    started = perf_counter_ns()
    try:
        proc = subprocess.run(
            [sys.executable, '-B', str(WORKER), *_worker_args],
            input=json.dumps({'method': method, 'instance': instance}),
            text=True, capture_output=True, timeout=timeout_seconds,
            env=env, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'method': method, 'id': instance['id'],
                'process_wall_ns': perf_counter_ns() - started,
                'cap_bytes': cap_bytes, 'timeout_seconds': timeout_seconds}
    wall = perf_counter_ns() - started
    if proc.returncode != 0:
        stderr = proc.stderr[-2000:]
        status = ('memory_cap' if 'MemoryError' in stderr else
                  'killed' if proc.returncode == -9 else
                  'native_crash' if proc.returncode < 0 else 'error')
        return {'status': status, 'method': method, 'id': instance['id'],
                'returncode': proc.returncode, 'stderr_tail': stderr,
                'process_wall_ns': wall, 'cap_bytes': cap_bytes,
                'timeout_seconds': timeout_seconds}
    try:
        row = json.loads(proc.stdout)
        if (not isinstance(row, dict) or row.get('status') != 'ok' or
            row.get('method') != method or row.get('id') != instance['id'] or
            row.get('n') != instance['n'] or
            row.get('effective_cap_bytes') != cap_bytes):
            raise ValueError('Worker identity, status or effective cap mismatch')
    except (json.JSONDecodeError, ValueError) as exc:
        return {'status': 'bad_output', 'method': method, 'id': instance['id'],
                'error': str(exc), 'stdout_tail': proc.stdout[-1000:],
                'process_wall_ns': wall, 'cap_bytes': cap_bytes,
                'timeout_seconds': timeout_seconds}
    row.update(process_wall_ns=wall, cap_bytes=cap_bytes,
               timeout_seconds=timeout_seconds)
    return row


def test_hard_cap():
    """Prove that an allocation above a small cap fails in a child process."""
    if sys.platform != 'linux':
        raise RuntimeError('Hard-cap self-test requires Linux')
    cap = 256 * 1024 ** 2
    env = os.environ.copy()
    env['LIVE_VTREE_RLIMIT_AS_BYTES'] = str(cap)
    proc = subprocess.run([sys.executable, '-B', str(WORKER), '--cap-selftest'],
                          text=True, capture_output=True, env=env, cwd=ROOT,
                          timeout=5)
    try:
        observed = json.loads(proc.stdout)['effective_cap_bytes']
    except (json.JSONDecodeError, KeyError, TypeError):
        observed = None
    passed = (proc.returncode != 0 and 'MemoryError' in proc.stderr and
              observed == cap)
    return {'status': 'PASS' if passed else 'FAIL', 'cap_bytes': cap,
            'observed_limit_bytes': observed,
            'returncode': proc.returncode,
            'memory_error': 'MemoryError' in proc.stderr}


if __name__ == '__main__':
    print(json.dumps(test_hard_cap(), indent=2))
