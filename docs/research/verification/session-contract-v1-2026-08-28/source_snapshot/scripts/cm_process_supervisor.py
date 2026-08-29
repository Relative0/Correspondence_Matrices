"""Bounded, owned-process supervision for trusted benchmark workers.

Windows Job Objects enforce aggregate committed-memory/process limits. This
is not an RSS bound or a security sandbox. Other platforms currently refuse
before launching; no process-group-only fallback claims equivalent limits.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace


MIB = 1024 * 1024


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 15
    memory_bytes: int = 512 * MIB
    processes: int = 8
    input_bytes: int = 256 * 1024
    stdout_bytes: int = 256 * 1024
    stderr_bytes: int = 64 * 1024

    def validate(self):
        if type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds) or not 0.05 <= self.timeout_seconds <= 60:
            raise ValueError("supervisor deadline must be 0.05..60 seconds")
        for value, minimum, maximum in ((self.memory_bytes, 16 * MIB, 2 * 1024 * MIB),
                                        (self.processes, 1, 32), (self.input_bytes, 0, MIB),
                                        (self.stdout_bytes, 1, MIB), (self.stderr_bytes, 1, MIB)):
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
    resources: dict = field(default_factory=dict)


class BoundedStream:
    def __init__(self, limit, stop):
        self.limit, self.stop = limit, stop
        self.data = bytearray()
        self.exceeded = False
        self.error = None

    def read(self, pipe):
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


def _windows_api():
    from ctypes import wintypes as w
    size = ctypes.c_size_t

    class BasicLimits(ctypes.Structure):
        _fields_ = [("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64), ("Flags", w.DWORD),
                    ("MinWorkingSet", size), ("MaxWorkingSet", size), ("ActiveLimit", w.DWORD),
                    ("Affinity", size), ("Priority", w.DWORD), ("Scheduling", w.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("Basic", BasicLimits), ("IO", IO), ("ProcessMemoryLimit", size), ("JobMemoryLimit", size),
                    ("PeakProcessMemoryUsed", size), ("PeakJobMemoryUsed", size)]

    class Accounting(ctypes.Structure):
        _fields_ = [(name, ctypes.c_int64) for name in ("UserTime", "KernelTime", "PeriodUser", "PeriodKernel")] + [
            (name, w.DWORD) for name in ("PageFaults", "TotalProcesses", "ActiveProcesses", "TerminatedProcesses")]

    class ProcessList(ctypes.Structure):
        _fields_ = [("Assigned", w.DWORD), ("Listed", w.DWORD), ("Pids", size * 64)]

    class ThreadEntry(ctypes.Structure):
        _fields_ = [("Size", w.DWORD), ("Usage", w.DWORD), ("Tid", w.DWORD), ("Pid", w.DWORD),
                    ("BasePriority", w.LONG), ("DeltaPriority", w.LONG), ("Flags", w.DWORD)]

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        "QueryInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "IsProcessInJob": ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
        "Thread32First": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        "Thread32Next": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "ResumeThread": ([w.HANDLE], w.DWORD),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = arguments, result
    return SimpleNamespace(dll=api, ExtendedLimits=ExtendedLimits, Accounting=Accounting,
                           ProcessList=ProcessList, ThreadEntry=ThreadEntry, BOOL=w.BOOL)


def _ok(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


class WindowsJob:
    FLAGS = 0x2000 | 0x200 | 0x8  # KILL_ON_JOB_CLOSE | JOB_MEMORY | ACTIVE_PROCESS

    def __init__(self, limits):
        self.api = _windows_api()
        self.handle = _ok(self.api.dll.CreateJobObjectW(None, None))
        try:
            info = self.api.ExtendedLimits()
            info.Basic.Flags = self.FLAGS
            info.Basic.ActiveLimit = limits.processes
            info.JobMemoryLimit = limits.memory_bytes
            _ok(self.api.dll.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)))
            observed = self.query(9, self.api.ExtendedLimits)
            if (observed.Basic.Flags != self.FLAGS or observed.Basic.ActiveLimit != limits.processes
                    or observed.JobMemoryLimit != limits.memory_bytes):
                raise RuntimeError("job limits did not match request")
        except BaseException:
            self.close()
            raise

    def query(self, kind, structure):
        value = structure()
        _ok(self.api.dll.QueryInformationJobObject(self.handle, kind, ctypes.byref(value), ctypes.sizeof(value), None))
        return value

    def attach(self, process):
        handle = int(process._handle)  # CPython Windows Popen retains this owned handle.
        _ok(self.api.dll.AssignProcessToJobObject(self.handle, handle))
        present = self.api.BOOL()
        _ok(self.api.dll.IsProcessInJob(handle, self.handle, ctypes.byref(present)))
        if not present.value:
            raise RuntimeError("worker not in owned job")

    def resume(self, pid):
        # Popen closes the primary thread handle. Find only our still-suspended
        # process's thread, using documented Toolhelp/OpenThread/ResumeThread APIs.
        snapshot = self.api.dll.CreateToolhelp32Snapshot(0x4, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        tids = []
        try:
            item = self.api.ThreadEntry()
            item.Size = ctypes.sizeof(item)
            more = self.api.dll.Thread32First(snapshot, ctypes.byref(item))
            while more:
                if item.Pid == pid:
                    tids.append(item.Tid)
                more = self.api.dll.Thread32Next(snapshot, ctypes.byref(item))
            if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            _ok(self.api.dll.CloseHandle(snapshot))
        if len(tids) != 1:
            raise RuntimeError("unexpected suspended worker thread count")
        thread = _ok(self.api.dll.OpenThread(0x2, False, tids[0]))
        try:
            previous = self.api.dll.ResumeThread(thread)
            if previous != 1:
                raise RuntimeError("worker suspend count was not one")
        finally:
            _ok(self.api.dll.CloseHandle(thread))

    def sample(self):
        memory = self.query(9, self.api.ExtendedLimits)
        accounting = self.query(1, self.api.Accounting)
        processes = self.query(3, self.api.ProcessList)
        if processes.Listed > 64:
            raise RuntimeError("job process list exceeded bound")
        return {"peak_job_committed_bytes": memory.PeakJobMemoryUsed,
                "peak_process_committed_bytes": memory.PeakProcessMemoryUsed,
                "active_processes": accounting.ActiveProcesses,
                "total_processes": accounting.TotalProcesses,
                "pids": list(processes.Pids[:processes.Listed])}

    def terminate(self):
        _ok(self.api.dll.TerminateJobObject(self.handle, 125))

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            _ok(self.api.dll.CloseHandle(handle))


def platform_supported():
    return os.name == "nt"


def run(command, *, input=b"", cwd=None, limits=Limits(), job_factory=WindowsJob):
    limits.validate()
    if (not isinstance(command, (list, tuple)) or not command or
            not all(isinstance(arg, str) and "\0" not in arg for arg in command) or
            not Path(command[0]).is_absolute()):
        raise ValueError("explicit absolute executable and argument list required")
    if not isinstance(input, bytes) or len(input) > limits.input_bytes:
        raise ValueError("supervisor input limit")
    if not platform_supported():
        return Result("refused", "hard_process_tree_limits_unavailable", resources={"launched": False})
    started = time.monotonic_ns()
    deadline = time.monotonic() + limits.timeout_seconds
    process = job = None
    attached = resumed = False
    threads = []
    stop = threading.Event()
    stdout, stderr = BoundedStream(limits.stdout_bytes, stop), BoundedStream(limits.stderr_bytes, stop)
    result = Result("error", "supervisor_initialization")
    observed_pids = set()
    resources = {"backend": "windows_job_object", "memory_metric": "job_committed_high_water_not_rss",
                 "job_memory_limit_bytes": limits.memory_bytes, "process_limit": limits.processes,
                 "stdout_limit_bytes": limits.stdout_bytes, "stderr_limit_bytes": limits.stderr_bytes,
                 "peak_job_committed_bytes": 0, "peak_process_committed_bytes": 0,
                 "whole_tree_rss_measured": False, "cleanup_verified": False, "launched": False}

    def sample():
        row = job.sample()
        observed_pids.update(row["pids"])
        for field in ("peak_job_committed_bytes", "peak_process_committed_bytes"):
            resources[field] = max(resources[field], row[field])
        resources["total_processes"] = row["total_processes"]
        resources["active_processes"] = row["active_processes"]
        return row["active_processes"]

    def write_input():
        try:
            remaining = memoryview(input)
            while remaining:
                written = process.stdin.write(remaining)
                if not written:
                    raise OSError("worker input write made no progress")
                remaining = remaining[written:]
        except (BrokenPipeError, OSError):
            pass  # A worker may exit without consuming all bounded input.
        finally:
            process.stdin.close()

    try:
        job = job_factory(limits)
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0, close_fds=True,
                                   creationflags=0x4 | 0x08000000)  # CREATE_SUSPENDED | CREATE_NO_WINDOW
        result.pid = process.pid
        resources["launched"] = True
        job.attach(process)
        attached = True
        sample()
        resources["pre_resume_job_peak_committed_bytes"] = resources["peak_job_committed_bytes"]
        if time.monotonic() >= deadline:
            result.status, result.reason = "timeout", "startup_deadline"
        else:
            for reader, pipe in ((stdout, process.stdout), (stderr, process.stderr)):
                thread = threading.Thread(target=reader.read, args=(pipe,), daemon=True)
                thread.start()
                threads.append(thread)
            job.resume(process.pid)
            resumed = True
            writer = threading.Thread(target=write_input, daemon=True)
            writer.start()
            threads.append(writer)
            exit_at = None
            while True:
                active = sample()
                now = time.monotonic()
                if stop.is_set():
                    result.status = "output_limit" if stdout.exceeded or stderr.exceeded else "error"
                    result.reason = "bounded_stream_limit" if result.status == "output_limit" else "stream_read_error"
                    break
                if now >= deadline:
                    result.status, result.reason = "timeout", "worker_deadline"
                    break
                if process.poll() is not None:
                    exit_at = exit_at or now
                    if active == 0:
                        result.status = "ok" if process.returncode == 0 else "error"
                        result.reason = "completed" if process.returncode == 0 else "worker_nonzero_exit"
                        break
                    if now - exit_at >= 0.1:
                        result.status, result.reason = "error", "descendants_survived_root_exit"
                        break
                stop.wait(min(0.005, max(0, deadline - now)))
    except (OSError, RuntimeError) as exc:
        result.status, result.reason = ("error" if resumed else "refused"), type(exc).__name__
        resources["system_error_code"] = getattr(exc, "winerror", None)
    finally:
        try:
            if process is not None:
                if attached:
                    job.terminate()  # Only this unnamed, owned job and its descendants.
                elif process.poll() is None:
                    process.kill()  # Owned suspended process; no workload was released.
                process.wait(timeout=2)
                if attached:
                    until = time.monotonic() + 2
                    while sample() and time.monotonic() < until:
                        time.sleep(0.005)
                    resources["cleanup_verified"] = resources["active_processes"] == 0
                else:
                    resources["cleanup_verified"] = process.returncode is not None
            else:
                resources["cleanup_verified"] = True
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            resources["cleanup_error"] = type(exc).__name__
        finally:
            if job is not None:
                try:
                    job.close()  # KILL_ON_JOB_CLOSE is also a fail-safe on exceptions.
                except OSError:
                    resources["cleanup_verified"] = False
            for thread in threads:
                thread.join(timeout=1)
            resources["streams_closed"] = not any(thread.is_alive() for thread in threads)
            if process is not None and resources["streams_closed"]:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    pipe.close()
    if stdout.exceeded or stderr.exceeded:
        result.status, result.reason = "output_limit", "bounded_stream_limit"
    elif stdout.error or stderr.error:
        result.status, result.reason = "error", "stream_read_error"
    if not resources["cleanup_verified"] or not resources["streams_closed"]:
        result.status, result.reason = "error", "cleanup_or_streams_unverified"
    resources.update(observed_job_pids=sorted(observed_pids), attached_before_resume=attached and resumed,
                     stdout_truncated=stdout.exceeded, stderr_truncated=stderr.exceeded,
                     job_peak_exceeds_configured_limit=resources["peak_job_committed_bytes"] > limits.memory_bytes,
                     memory_limit_hit_attribution="unknown_without_violation_notification")
    result.stdout, result.stderr = bytes(stdout.data), bytes(stderr.data)
    result.returncode = process.returncode if process else None
    result.wall_ns = time.monotonic_ns() - started
    result.resources = resources
    return result
