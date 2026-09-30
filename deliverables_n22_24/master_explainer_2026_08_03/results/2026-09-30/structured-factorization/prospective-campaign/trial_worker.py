"""Fresh-process entry point for one non-oracle integration trial.

On Linux, the runner supplies LIVE_VTREE_RLIMIT_AS_BYTES. Apply the limit
before importing PySDD or PySAT so native allocations are covered too.
"""
import json
import sys

from resource_guard import apply_from_environment

cap = apply_from_environment()


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--cap-selftest':
        if cap is None:
            raise RuntimeError('Cap self-test requires an active Linux cap')
        print(json.dumps({'effective_cap_bytes': cap}), flush=True)
        allocation = bytearray(cap * 2)
        raise RuntimeError(f'Cap failed to prevent allocation: {len(allocation)}')
    if len(sys.argv) == 2 and sys.argv[1] == '--sleep-selftest':
        if cap is None:
            raise RuntimeError('Watchdog self-test requires an active Linux cap')
        import time
        time.sleep(5)
        raise RuntimeError('Watchdog failed to stop sleeping worker')
    if len(sys.argv) == 2 and sys.argv[1] == '--signal-selftest':
        if cap is None:
            raise RuntimeError('Signal self-test requires an active Linux cap')
        import os
        import resource
        import signal
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.kill(os.getpid(), signal.SIGSEGV)
        raise RuntimeError('Signal self-test unexpectedly returned')
    if len(sys.argv) != 1:
        raise SystemExit('Unexpected worker argument')
    from integrated_pipeline import run_trial
    payload = json.load(sys.stdin)
    result = run_trial(payload['method'], payload['instance'])
    result['effective_cap_bytes'] = cap
    print(json.dumps(result, separators=(',', ':')), flush=True)
