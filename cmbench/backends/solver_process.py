"""Bounded supervision for trusted pinned solver executables.

Windows limits aggregate committed memory in an owned job. Linux limits each
process's address space and samples aggregate process-group RSS; a cgroup or
container is still needed for a hard aggregate Linux memory limit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import shutil
import sys


DEFAULT_SOLVER_MEMORY_BYTES = 2 << 30
MAX_INPUT_BYTES = 16 << 20


@dataclass(frozen=True)
class SolverProcessResult:
    returncode: int
    stdout: str
    stderr: str
    resources: dict


def validate_solver_limits(timeout_seconds, max_output_bytes, max_memory_bytes):
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 900):
        raise ValueError("invalid solver timeout")
    if type(max_output_bytes) is not int or not 1 <= max_output_bytes <= 1 << 20:
        raise ValueError("invalid solver output limit (1..1048576 bytes)")
    if type(max_memory_bytes) is not int or not 16 << 20 <= max_memory_bytes <= 2 << 30:
        raise ValueError("invalid solver memory limit (16 MiB..2 GiB)")


def read_solver_input(path):
    candidate = Path(path).absolute()
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("native solver input missing or linked")
    source = candidate.resolve()
    with source.open('rb') as handle:
        data = handle.read(MAX_INPUT_BYTES + 1)
    if not 0 < len(data) <= MAX_INPUT_BYTES:
        raise ValueError("DIMACS outside byte limit")
    return source, data.decode('utf-8')


def _text(data):
    return data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')


def raise_if_cgroup_oom(resources):
    if resources.get('cgroup_memory_events', {}).get('oom_group_kill', 0):
        # A group OOM invalidates every partial solver result.  Surface it as
        # a resource failure rather than making adapters interpret SIGKILL.
        raise MemoryError("solver cgroup memory limit exceeded")


def run_solver(command, *, timeout_seconds=60.0, max_output_bytes=1 << 20,
               max_memory_bytes=DEFAULT_SOLVER_MEMORY_BYTES):
    validate_solver_limits(timeout_seconds, max_output_bytes, max_memory_bytes)
    if (not isinstance(command, (list, tuple)) or not command
            or not all(isinstance(arg, str) and '\0' not in arg for arg in command)):
        raise ValueError("solver argument list required")
    executable = shutil.which(command[0])
    if executable is None:
        raise FileNotFoundError(f"solver executable unavailable: {command[0]}")
    executable = str(Path(executable).resolve())
    if os.name == 'nt' and Path(executable).suffix.lower() in {'.bat', '.cmd'}:
        raise ValueError("solver must be a native executable, not a shell script")
    executed = (executable, *command[1:])
    if os.name == 'nt':
        from scripts import cm_process_supervisor as supervisor
    elif sys.platform.startswith('linux'):
        from cmbench.comparative import linux_supervisor as supervisor
    else:
        raise RuntimeError("solver process supervision unavailable on this platform")

    # Solver deadlines retain the adapter's existing 900-second range.
    # Reuse the supervisor's resource-field validation without extending its
    # separate benchmark-worker deadline policy (0.05..60 seconds).
    class SolverLimits(supervisor.Limits):
        def validate(self):
            validate_solver_limits(self.timeout_seconds, max_output_bytes, max_memory_bytes)
            supervisor.Limits.validate(replace(self, timeout_seconds=60))

    if os.name == 'nt':
        limits = SolverLimits(timeout_seconds=timeout_seconds, memory_bytes=max_memory_bytes,
            stdout_bytes=max_output_bytes, stderr_bytes=max_output_bytes, input_bytes=0)
        result = supervisor.run(executed, limits=limits)
    else:
        limits = SolverLimits(timeout_seconds=timeout_seconds, rss_stop_bytes=max_memory_bytes,
            stdout_bytes=max_output_bytes, stderr_bytes=max_output_bytes, input_bytes=0,
            cgroup_memory_bytes=max_memory_bytes)
        # A fresh isolated interpreter installs the inherited kernel limit
        # before exec; no preexec_fn runs in a potentially threaded parent.
        wrapped = (sys.executable, '-I', '-B', str(Path(__file__).resolve()),
            '--limit-child', str(max_memory_bytes), *executed)
        result = supervisor.run(wrapped, limits=limits)
        result.resources['process_address_space_limit_bytes'] = max_memory_bytes
    resources = dict(result.resources, executed_command=list(executed))
    if not resources.get('cleanup_verified') or not resources.get('streams_closed'):
        raise RuntimeError(f"solver cleanup unverified: {result.reason}")
    raise_if_cgroup_oom(resources)
    if result.status == 'timeout':
        raise TimeoutError("solver deadline exceeded")
    if (result.status == 'output_limit' or resources.get('stdout_truncated')
            or resources.get('stderr_truncated')):
        raise ValueError("solver diagnostic output exceeds limit")
    # Native SAT uses conventional nonzero success statuses 10 and 20. The
    # adapter checks those; a supervisor lifecycle error is never parseable.
    if not (result.status == 'ok' or
            (result.status == 'error' and result.reason == 'worker_nonzero_exit')):
        raise RuntimeError(f"solver supervision failed: {result.reason}")
    if len(result.stdout) + len(result.stderr) > max_output_bytes:
        raise ValueError("solver diagnostic output exceeds combined limit")
    if result.returncode is None:
        raise RuntimeError("solver returned no exit status")
    return SolverProcessResult(result.returncode, _text(result.stdout), _text(result.stderr), resources)


if __name__ == '__main__':
    if len(sys.argv) < 4 or sys.argv[1] != '--limit-child':
        raise SystemExit('internal solver resource bootstrap only')
    import resource
    requested = int(sys.argv[2])
    validate_solver_limits(60, 1, requested)
    _, inherited_hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = requested if inherited_hard == resource.RLIM_INFINITY else min(requested, inherited_hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    os.execv(sys.argv[3], sys.argv[3:])
