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
                timeout_seconds=TIMEOUT_SECONDS):
    if sys.platform != 'linux':
        raise RuntimeError('Formal bounded trials require Linux')
    env = os.environ.copy()
    env['LIVE_VTREE_RLIMIT_AS_BYTES'] = str(cap_bytes)
    started = perf_counter_ns()
    try:
        proc = subprocess.run(
            [sys.executable, '-B', str(WORKER)],
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
                  'killed' if proc.returncode in (-9, -11) else 'error')
        return {'status': status, 'method': method, 'id': instance['id'],
                'returncode': proc.returncode, 'stderr_tail': stderr,
                'process_wall_ns': wall, 'cap_bytes': cap_bytes,
                'timeout_seconds': timeout_seconds}
    try:
        row = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
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
    code = ("import os,resource; c=int(os.environ['LIVE_VTREE_RLIMIT_AS_BYTES']);"
            "resource.setrlimit(resource.RLIMIT_AS,(c,c));"
            "print(resource.getrlimit(resource.RLIMIT_AS),flush=True);"
            "x=bytearray(c*2)")
    env = os.environ.copy()
    env['LIVE_VTREE_RLIMIT_AS_BYTES'] = str(cap)
    proc = subprocess.run([sys.executable, '-B', '-c', code],
                          text=True, capture_output=True, env=env, timeout=5)
    passed = proc.returncode != 0 and 'MemoryError' in proc.stderr
    return {'status': 'PASS' if passed else 'FAIL', 'cap_bytes': cap,
            'observed_limit': proc.stdout.strip(),
            'returncode': proc.returncode,
            'memory_error': 'MemoryError' in proc.stderr}


if __name__ == '__main__':
    print(json.dumps(test_hard_cap(), indent=2))
