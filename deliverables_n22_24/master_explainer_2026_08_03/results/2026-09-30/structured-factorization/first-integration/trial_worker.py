"""Fresh-process entry point for one non-oracle integration trial.

On Linux, the runner supplies LIVE_VTREE_RLIMIT_AS_BYTES. Apply the limit
before importing PySDD or PySAT so native allocations are covered too.
"""
import json
import os
import sys

if os.environ.get('LIVE_VTREE_RLIMIT_AS_BYTES'):
    if sys.platform != 'linux':
        raise RuntimeError('Hard worker memory limit requires Linux')
    import resource
    cap = int(os.environ['LIVE_VTREE_RLIMIT_AS_BYTES'])
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    if resource.getrlimit(resource.RLIMIT_AS) != (cap, cap):
        raise RuntimeError('Worker address-space limit did not take effect')

from integrated_pipeline import run_trial


if __name__ == '__main__':
    payload = json.load(sys.stdin)
    print(json.dumps(run_trial(payload['method'], payload['instance']),
                     separators=(',', ':')), flush=True)
