"""Bounded supervision for trusted Linux benchmark workers.

Workers run in a new process group created before exec.  Descendants that keep
the inherited process group are sampled through procfs and killed as a unit.
This is suitable for reviewed benchmark adapters; it is not a security
sandbox and the sampled aggregate RSS stop is not a kernel-enforced cgroup
memory limit.  Callers may additionally request an owned cgroup-v2 memory
scope; its collector remains outside that scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any
import uuid


MIB = 1024 * 1024
MAX_PROC_SCAN = 4096
TERMINAL_PROC_STATES = frozenset({"Z", "X", "x"})
RSS_APPEARANCE_RETRIES = 20
RSS_APPEARANCE_RETRY_SECONDS = 0.001
CGROUP_ROOT = Path("/sys/fs/cgroup")
CGROUP_PREFIX = "cmbench-"


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 15
    rss_stop_bytes: int = 512 * MIB
    processes: int = 8
    input_bytes: int = 256 * 1024
    stdout_bytes: int = 256 * 1024
    stderr_bytes: int = 64 * 1024
    sample_seconds: float = 0.01
    cgroup_memory_bytes: int | None = None
    cgroup_cpu_max: tuple[int, int] | None = None

    def validate(self) -> None:
        if type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds) or not 0.05 <= self.timeout_seconds <= 60:
            raise ValueError("supervisor deadline must be 0.05..60 seconds")
        if type(self.sample_seconds) not in (int, float) or not math.isfinite(self.sample_seconds) or not 0.001 <= self.sample_seconds <= 0.1:
            raise ValueError("invalid RSS sample interval")
        for value, minimum, maximum in (
            (self.rss_stop_bytes, 16 * MIB, 64 * 1024 * MIB),
            (self.processes, 1, 64),
            (self.input_bytes, 0, MIB),
            (self.stdout_bytes, 1, MIB),
            (self.stderr_bytes, 1, MIB),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError("invalid supervisor limit")
        if self.cgroup_memory_bytes is not None and (
                type(self.cgroup_memory_bytes) is not int
                or not 16 * MIB <= self.cgroup_memory_bytes <= 2 * 1024 * MIB):
            raise ValueError("invalid cgroup memory limit")
        if self.cgroup_cpu_max is not None:
            if (self.cgroup_memory_bytes is None
                    or not isinstance(self.cgroup_cpu_max, tuple)
                    or len(self.cgroup_cpu_max) != 2
                    or any(type(v) is not int for v in self.cgroup_cpu_max)):
                raise ValueError("CPU quota requires an owned cgroup and integer quota/period")
            quota, period = self.cgroup_cpu_max
            if not 1000 <= period <= 1000000 or not 1000 <= quota <= 64 * period:
                raise ValueError("invalid cgroup CPU quota/period")


@dataclass
class Result:
    status: str
    reason: str
    returncode: int | None = None
    stdout: bytes = b""
    stderr: bytes = b""
    pid: int | None = None
    wall_ns: int = 0
    resources: dict[str, Any] = field(default_factory=dict)


class BoundedStream:
    def __init__(self, limit: int, stop: threading.Event):
        self.limit, self.stop = limit, stop
        self.data = bytearray()
        self.exceeded = False
        self.error: str | None = None

    def read(self, pipe: Any) -> None:
        try:
            while True:
                chunk = os.read(pipe.fileno(), min(4096, self.limit - len(self.data) + 1))
                if not chunk:
                    return
                room = self.limit - len(self.data)
                self.data.extend(chunk[:room])
                if len(chunk) > room:
                    self.exceeded = True
                    self.stop.set()
                    return
        except OSError as exc:
            self.error = type(exc).__name__
            self.stop.set()


def parse_proc_stat(value: str) -> tuple[int, int, str]:
    """Return PID, process group and state without trusting spaces in comm."""
    if not isinstance(value, str) or len(value) > 64 << 10:
        raise ValueError("invalid proc stat")
    opening, closing = value.find(" ("), value.rfind(") ")
    if opening <= 0 or closing <= opening:
        raise ValueError("invalid proc stat framing")
    pid_text = value[:opening]
    fields = value[closing + 2 :].split()
    if not pid_text.isdigit() or len(fields) < 3 or len(fields[0]) != 1 or not fields[1].isdigit() or not fields[2].isdigit():
        raise ValueError("invalid proc stat fields")
    return int(pid_text), int(fields[2]), fields[0]


def parse_proc_status(value: str) -> dict[str, int | None]:
    if not isinstance(value, str) or len(value) > 256 << 10:
        raise ValueError("invalid proc status")
    found: dict[str, int] = {}
    for line in value.splitlines():
        match = re.fullmatch(r"(VmRSS|VmHWM):\s+([0-9]+) kB", line)
        if match:
            if match[1] in found:
                raise ValueError("duplicate proc memory field")
            found[match[1]] = int(match[2]) * 1024
    return {"rss_bytes": found.get("VmRSS"), "hwm_bytes": found.get("VmHWM")}


def group_snapshot(proc_root: Path, pgid: int) -> dict[str, Any]:
    if type(pgid) is not int or pgid <= 1:
        raise ValueError("invalid owned process group")
    pids: list[int] = []
    rss = 0
    hwm: dict[int, int | None] = {}
    unreadable = 0
    scan_races = 0
    scan_errors = 0
    try:
        entries = list(proc_root.iterdir())
    except OSError as exc:
        raise RuntimeError("procfs unavailable") from exc
    numeric = [entry for entry in entries if entry.name.isdigit()]
    if len(numeric) > MAX_PROC_SCAN:
        raise RuntimeError("procfs process bound exceeded")
    for entry in numeric:
        try:
            stat = (entry / "stat").read_text(encoding="ascii")
            pid, process_group, state = parse_proc_stat(stat)
        except FileNotFoundError:
            scan_races += 1
            continue
        except (OSError, UnicodeError, ValueError):
            scan_errors += 1
            continue
        if process_group != pgid or state in TERMINAL_PROC_STATES:
            continue
        try:
            status = parse_proc_status((entry / "status").read_text(encoding="ascii"))
        except FileNotFoundError:
            # Status disappearance alone is not proof that the known live
            # owned member disappeared. Preserve it until stat proves exit.
            try:
                current_pid, current_group, current_state = parse_proc_stat(
                    (entry / "stat").read_text(encoding="ascii"))
                gone = current_pid != pid or current_group != pgid or current_state in TERMINAL_PROC_STATES
            except FileNotFoundError:
                gone = True
            except (OSError, UnicodeError, ValueError):
                gone = False
            if gone:
                scan_races += 1
            else:
                pids.append(pid)
                unreadable += 1
            continue
        except (OSError, UnicodeError, ValueError):
            unreadable += 1
            pids.append(pid)
            continue
        if status["rss_bytes"] is None:
            # A short-lived native worker can enter a terminal state between
            # the stat and status reads.  Reclassify only that proven
            # transition as a procfs race; a still-live entry without VmRSS
            # remains a fail-closed incomplete measurement.
            resolved_race = False
            for retry in range(RSS_APPEARANCE_RETRIES):
                try:
                    current = (entry / "stat").read_text(encoding="ascii")
                    current_pid, current_group, current_state = parse_proc_stat(current)
                except FileNotFoundError:
                    scan_races += 1
                    resolved_race = True
                    break
                except (OSError, UnicodeError, ValueError):
                    unreadable += 1
                    pids.append(pid)
                    resolved_race = True
                    break
                if current_pid != pid or current_group != pgid or current_state in TERMINAL_PROC_STATES:
                    scan_races += 1
                    resolved_race = True
                    break
                try:
                    retried = parse_proc_status((entry / "status").read_text(encoding="ascii"))
                except FileNotFoundError:
                    # Lost status alone does not prove the live stat's exit.
                    unreadable += 1
                    pids.append(pid)
                    resolved_race = True
                    break
                except (OSError, UnicodeError, ValueError):
                    unreadable += 1
                    pids.append(pid)
                    resolved_race = True
                    break
                if retried["rss_bytes"] is not None:
                    status = retried
                    break
                if retry + 1 < RSS_APPEARANCE_RETRIES:
                    time.sleep(RSS_APPEARANCE_RETRY_SECONDS)
            else:
                unreadable += 1
            if resolved_race:
                continue
        pids.append(pid)
        if status["rss_bytes"] is not None:
            rss += status["rss_bytes"]
        hwm[pid] = status["hwm_bytes"]
    return {
        "pids": sorted(pids),
        "rss_bytes": rss,
        "per_process_hwm_bytes": hwm,
        "unreadable_group_entries": unreadable,
        "proc_scan_races": scan_races,
        "proc_scan_errors": scan_errors,
    }


def platform_supported() -> bool:
    return sys.platform.startswith("linux") and Path("/proc/self/stat").is_file()


def _cgroup_values(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[1].isascii() or not fields[1].isdigit() or fields[0] in values:
            raise ValueError("invalid or duplicate cgroup event field")
        values[fields[0]] = int(fields[1])
    return values


class _CgroupScope:
    """An owned cgroup-v2 scope, with the collector deliberately outside it."""

    def __init__(self, memory_bytes: int, processes: int, cpu_max: tuple[int, int] | None = None):
        self.memory_bytes = memory_bytes
        self.processes = processes
        self.cpu_max = cpu_max
        self.path: Path | None = None
        self._closed_result: dict[str, Any] | None = None

    def create(self) -> dict[str, Any]:
        if not (CGROUP_ROOT / "cgroup.controllers").is_file():
            raise RuntimeError("cgroup_v2_unavailable")
        group = CGROUP_ROOT / f"{CGROUP_PREFIX}{uuid.uuid4()}"
        group.mkdir()
        self.path = group
        settings = {
            "memory.max": str(self.memory_bytes),
            "memory.swap.max": "0",
            "memory.oom.group": "1",
            "pids.max": str(self.processes),
        }
        if self.cpu_max is not None:
            settings["cpu.max"] = f"{self.cpu_max[0]} {self.cpu_max[1]}"
        try:
            for name, value in settings.items():
                (group / name).write_text(value, encoding="ascii")
            actual = {name: (group / name).read_text(encoding="ascii").strip()
                      for name in settings}
            if actual != settings:
                raise RuntimeError("cgroup_settings_readback_mismatch")
        except BaseException:
            self.close()
            raise
        return {
            "aggregate_memory_limit_is_kernel_enforced": True,
            "cgroup_path": str(group),
            "cgroup_settings": actual,
            "cgroup_requested_settings": settings,
        }

    def wrapped_command(self, command: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if self.path is None:
            raise RuntimeError("cgroup scope not created")
        # This fresh launcher enters the cgroup before exec.  Its target and
        # all subsequently forked workers inherit membership.
        bootstrap = (
            "import os,sys; "
            "open(sys.argv[1] + '/cgroup.procs', 'w', encoding='ascii').write(str(os.getpid())); "
            "os.execv(sys.argv[2], sys.argv[2:])"
        )
        return (sys.executable, "-I", "-B", "-c", bootstrap, str(self.path), *command)

    def close(self) -> dict[str, Any]:
        if self._closed_result is not None:
            return dict(self._closed_result)
        group = self.path
        if group is None:
            return {}
        result: dict[str, Any] = {}
        try:
            (group / "cgroup.kill").write_text("1", encoding="ascii")
            deadline = time.monotonic() + 2
            populated = 1
            while time.monotonic() < deadline:
                events = _cgroup_values(group / "cgroup.events")
                populated = events.get("populated")
                if populated not in (0, 1):
                    raise ValueError("cgroup population evidence unavailable")
                if not populated:
                    break
                time.sleep(0.005)
            result["cgroup_cleanup_verified"] = not populated
            try:
                result["cgroup_memory_events"] = _cgroup_values(group / "memory.events")
                result["cgroup_memory_peak_bytes"] = int(
                    (group / "memory.peak").read_text(encoding="ascii").strip())
                result["cgroup_pids_peak"] = int(
                    (group / "pids.peak").read_text(encoding="ascii").strip())
            except (OSError, UnicodeError, ValueError) as exc:
                # Telemetry failure must not prevent empty owned-group removal.
                result["cgroup_metrics_error"] = type(exc).__name__
            if not populated:
                group.rmdir()
                result["cgroup_removed"] = not group.exists()
            else:
                result["cgroup_removed"] = False
        except (OSError, UnicodeError, ValueError) as exc:
            result["cgroup_cleanup_verified"] = False
            result["cgroup_removed"] = False
            result["cgroup_cleanup_error"] = type(exc).__name__
        if result.get("cgroup_removed"):
            self._closed_result = dict(result)
        return result


def run(
    command: list[str] | tuple[str, ...],
    *,
    input: bytes = b"",
    cwd: str | Path | None = None,
    limits: Limits = Limits(),
    proc_root: Path = Path("/proc"),
) -> Result:
    limits.validate()
    if (
        not isinstance(command, (list, tuple))
        or not command
        or not all(isinstance(item, str) and "\0" not in item for item in command)
        or not Path(command[0]).is_absolute()
    ):
        raise ValueError("explicit absolute executable and argument list required")
    if not isinstance(input, bytes) or len(input) > limits.input_bytes:
        raise ValueError("supervisor input limit")
    if not platform_supported():
        return Result("refused", "linux_proc_process_group_unavailable", resources={"launched": False})

    started = time.monotonic_ns()
    deadline = time.monotonic() + limits.timeout_seconds
    process: subprocess.Popen[bytes] | None = None
    threads: list[threading.Thread] = []
    stop = threading.Event()
    stdout = BoundedStream(limits.stdout_bytes, stop)
    stderr = BoundedStream(limits.stderr_bytes, stop)
    result = Result("error", "supervisor_initialization")
    resources: dict[str, Any] = {
        "backend": "linux_owned_process_group",
        "ownership_scope": "trusted_descendants_retaining_inherited_process_group",
        "memory_metric": "sampled_simultaneous_process_group_VmRSS",
        "rss_stop_bytes": limits.rss_stop_bytes,
        "rss_stop_is_kernel_enforced": False,
        "aggregate_memory_limit_is_kernel_enforced": False,
        "whole_tree_rss_measured": True,
        "peak_sampled_tree_rss_bytes": 0,
        "observed_group_pids": [],
        "unreadable_group_entries": 0,
        "proc_scan_races": 0,
        "proc_scan_errors": 0,
        "process_limit": limits.processes,
        "cleanup_verified": False,
        "streams_closed": False,
        "launched": False,
    }
    observed: set[int] = set()
    cgroup = (_CgroupScope(limits.cgroup_memory_bytes, limits.processes, limits.cgroup_cpu_max)
              if limits.cgroup_memory_bytes is not None else None)

    def sample(pgid: int) -> dict[str, Any]:
        row = group_snapshot(proc_root, pgid)
        observed.update(row["pids"])
        resources["peak_sampled_tree_rss_bytes"] = max(resources["peak_sampled_tree_rss_bytes"], row["rss_bytes"])
        resources["unreadable_group_entries"] += row["unreadable_group_entries"]
        resources["proc_scan_races"] += row["proc_scan_races"]
        resources["proc_scan_errors"] += row["proc_scan_errors"]
        resources["last_per_process_hwm_bytes"] = row["per_process_hwm_bytes"]
        return row

    def write_input() -> None:
        try:
            remaining = memoryview(input)
            while remaining:
                written = process.stdin.write(remaining)  # type: ignore[union-attr]
                if not written:
                    raise OSError("worker input write made no progress")
                remaining = remaining[written:]
        except (BrokenPipeError, OSError):
            pass
        finally:
            process.stdin.close()  # type: ignore[union-attr]

    pgid: int | None = None
    exit_at: float | None = None
    try:
        launched_command = command
        if cgroup is not None:
            resources.update(cgroup.create())
            launched_command = cgroup.wrapped_command(command)
        process = subprocess.Popen(
            launched_command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            close_fds=True,
            start_new_session=True,
        )
        result.pid = process.pid
        resources["launched"] = True
        pgid = os.getpgid(process.pid)
        if pgid != process.pid:
            raise RuntimeError("worker process-group ownership mismatch")
        for reader, pipe in ((stdout, process.stdout), (stderr, process.stderr)):
            thread = threading.Thread(target=reader.read, args=(pipe,), daemon=True)
            thread.start()
            threads.append(thread)
        writer = threading.Thread(target=write_input, daemon=True)
        writer.start()
        threads.append(writer)
        while True:
            row = sample(pgid)
            now = time.monotonic()
            if row["unreadable_group_entries"]:
                resources["whole_tree_rss_measured"] = False
                result.status, result.reason = "error", "process_tree_measurement_incomplete"
                break
            if len(row["pids"]) > limits.processes:
                result.status, result.reason = "error", "process_limit"
                break
            if row["rss_bytes"] > limits.rss_stop_bytes:
                result.status, result.reason = "memory_limit", "sampled_tree_rss_stop"
                break
            if stdout.exceeded or stderr.exceeded:
                result.status, result.reason = "output_limit", "bounded_stream_limit"
                break
            if stdout.error or stderr.error:
                result.status, result.reason = "error", "stream_read_error"
                break
            if now >= deadline:
                result.status, result.reason = "timeout", "worker_deadline"
                break
            if process.poll() is not None:
                exit_at = exit_at or now
                if not row["pids"]:
                    result.status = "ok" if process.returncode == 0 else "error"
                    result.reason = "completed" if process.returncode == 0 else "worker_nonzero_exit"
                    break
                if now - exit_at >= 0.1:
                    result.status, result.reason = "error", "descendants_survived_root_exit"
                    break
            stop.wait(min(limits.sample_seconds, max(0.0, deadline - now)))
    except (OSError, RuntimeError) as exc:
        result.status, result.reason = ("error" if process is not None else "refused"), type(exc).__name__
        resources["system_errno"] = getattr(exc, "errno", None)
    finally:
        cleanup_interrupts: list[BaseException] = []

        def cleanup_attempt(action):
            # A second cancellation must not skip the remaining owned cleanup
            # stages. Retry the interrupted stage once, then propagate only
            # after all stages have had their bounded opportunity.
            for _ in range(2):
                try:
                    return action()
                except (KeyboardInterrupt, SystemExit) as exc:
                    cleanup_interrupts.append(exc)
            return None

        if cgroup is not None:
            resources.update(cleanup_attempt(cgroup.close) or {})
        if pgid is not None:
            def kill_group():
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    resources["cleanup_error"] = type(exc).__name__
            cleanup_attempt(kill_group)
        if process is not None:
            def wait_root():
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    resources["cleanup_error"] = "root_wait_timeout"
            cleanup_attempt(wait_root)
        if pgid is not None:
            def observe_group():
                remaining = [pgid]  # Unknown until an actual observation.
                until = time.monotonic() + 2
                while time.monotonic() < until:
                    try:
                        cleanup_row = group_snapshot(proc_root, pgid)
                        remaining = cleanup_row["pids"]
                        if cleanup_row["unreadable_group_entries"] or cleanup_row["proc_scan_errors"]:
                            remaining = remaining or [pgid]
                    except RuntimeError:
                        remaining = [pgid]
                    if not remaining:
                        break
                    time.sleep(0.005)
                return not remaining
            resources["cleanup_verified"] = bool(cleanup_attempt(observe_group))
        else:
            resources["cleanup_verified"] = process is None
        for thread in threads:
            cleanup_attempt(lambda: thread.join(timeout=1))
        resources["streams_closed"] = not any(thread.is_alive() for thread in threads)
        if process is not None and resources["streams_closed"]:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None and not pipe.closed:
                    cleanup_attempt(pipe.close)
        if cleanup_interrupts:
            raise cleanup_interrupts[0]

    # Readers can finish after the root-exit branch has selected "ok".
    # Recheck their final state after joining, before accepting any output.
    if stdout.exceeded or stderr.exceeded:
        result.status, result.reason = "output_limit", "bounded_stream_limit"
    elif stdout.error or stderr.error:
        result.status, result.reason = "error", "stream_read_error"
    if not resources["cleanup_verified"] or not resources["streams_closed"]:
        result.status, result.reason = "error", "cleanup_or_streams_unverified"
    if cgroup is not None and not resources.get("cgroup_cleanup_verified"):
        result.status, result.reason = "error", "cgroup_cleanup_unverified"
    if resources.get("cgroup_metrics_error"):
        result.status, result.reason = "error", "cgroup_metrics_unverified"
    resources["observed_group_pids"] = sorted(observed)
    resources["stdout_truncated"] = stdout.exceeded
    resources["stderr_truncated"] = stderr.exceeded
    result.stdout, result.stderr = bytes(stdout.data), bytes(stderr.data)
    result.returncode = process.returncode if process is not None else None
    result.wall_ns = time.monotonic_ns() - started
    result.resources = resources
    return result
