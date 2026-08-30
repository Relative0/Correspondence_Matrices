"""Bounded supervision for trusted Linux benchmark workers.

Workers run in a new process group created before exec.  Descendants that keep
the inherited process group are sampled through procfs and killed as a unit.
This is suitable for reviewed benchmark adapters; it is not a security
sandbox and the sampled aggregate RSS stop is not a kernel-enforced cgroup
memory limit.  Container/cgroup limits are recorded separately by readiness.
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


MIB = 1024 * 1024
MAX_PROC_SCAN = 4096
TERMINAL_PROC_STATES = frozenset({"Z", "X", "x"})
RSS_APPEARANCE_RETRIES = 20
RSS_APPEARANCE_RETRY_SECONDS = 0.001


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 15
    rss_stop_bytes: int = 512 * MIB
    processes: int = 8
    input_bytes: int = 256 * 1024
    stdout_bytes: int = 256 * 1024
    stderr_bytes: int = 64 * 1024
    sample_seconds: float = 0.01

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
            scan_races += 1
            continue
        except (OSError, UnicodeError, ValueError):
            unreadable += 1
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
                    resolved_race = True
                    break
                if current_pid != pid or current_group != pgid or current_state in TERMINAL_PROC_STATES:
                    scan_races += 1
                    resolved_race = True
                    break
                try:
                    retried = parse_proc_status((entry / "status").read_text(encoding="ascii"))
                except FileNotFoundError:
                    scan_races += 1
                    resolved_race = True
                    break
                except (OSError, UnicodeError, ValueError):
                    unreadable += 1
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
        process = subprocess.Popen(
            command,
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
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                resources["cleanup_error"] = type(exc).__name__
        if process is not None:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                resources["cleanup_error"] = "root_wait_timeout"
        if pgid is not None:
            until = time.monotonic() + 2
            while time.monotonic() < until:
                try:
                    remaining = group_snapshot(proc_root, pgid)["pids"]
                except RuntimeError:
                    remaining = [pgid]
                if not remaining:
                    break
                time.sleep(0.005)
            resources["cleanup_verified"] = not remaining
        else:
            resources["cleanup_verified"] = process is None
        for thread in threads:
            thread.join(timeout=1)
        resources["streams_closed"] = not any(thread.is_alive() for thread in threads)
        if process is not None and resources["streams_closed"]:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None and not pipe.closed:
                    pipe.close()

    if not resources["cleanup_verified"] or not resources["streams_closed"]:
        result.status, result.reason = "error", "cleanup_or_streams_unverified"
    resources["observed_group_pids"] = sorted(observed)
    resources["stdout_truncated"] = stdout.exceeded
    resources["stderr_truncated"] = stderr.exceeded
    result.stdout, result.stderr = bytes(stdout.data), bytes(stderr.data)
    result.returncode = process.returncode if process is not None else None
    result.wall_ns = time.monotonic_ns() - started
    result.resources = resources
    return result
