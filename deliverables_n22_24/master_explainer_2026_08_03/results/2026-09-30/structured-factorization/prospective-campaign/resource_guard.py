"""Apply the Linux address-space limit before importing native solvers."""
import os
import sys


def apply_from_environment():
    raw = os.environ.get('LIVE_VTREE_RLIMIT_AS_BYTES')
    if not raw:
        return None
    if sys.platform != 'linux':
        raise RuntimeError('Hard worker memory limit requires Linux')
    import resource
    cap = int(raw)
    if cap <= 0:
        raise ValueError('Memory cap must be positive')
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    if resource.getrlimit(resource.RLIMIT_AS) != (cap, cap):
        raise RuntimeError('Worker address-space limit did not take effect')
    return cap
