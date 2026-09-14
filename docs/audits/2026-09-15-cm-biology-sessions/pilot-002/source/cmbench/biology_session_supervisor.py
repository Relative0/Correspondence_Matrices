"""Bounded Windows workers using hard limits and whole-job accounting.

The job exists with its limits before a suspended worker is created. The
worker is assigned before its first thread resumes. Descendants inherit the
job; only that job is ever terminated. Other platforms fail without launching.
Peak memory is aggregate committed memory, not resident memory (RSS).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import os
import subprocess
import threading
import time


class _Security(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


class _Startup(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _StartupEx(ctypes.Structure):
    _fields_ = [("StartupInfo", _Startup), ("lpAttributeList", ctypes.c_void_p)]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _IOCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong), ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]


class _CompletionPort(ctypes.Structure):
    _fields_ = [("CompletionKey", ctypes.c_void_p), ("CompletionPort", wintypes.HANDLE)]


def _api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": (wintypes.HANDLE, [ctypes.c_void_p, wintypes.LPCWSTR]),
        "SetInformationJobObject": (wintypes.BOOL, [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]),
        "QueryInformationJobObject": (wintypes.BOOL, [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]),
        "AssignProcessToJobObject": (wintypes.BOOL, [wintypes.HANDLE, wintypes.HANDLE]),
        "TerminateJobObject": (wintypes.BOOL, [wintypes.HANDLE, wintypes.UINT]),
        "TerminateProcess": (wintypes.BOOL, [wintypes.HANDLE, wintypes.UINT]),
        "GetCurrentProcess": (wintypes.HANDLE, []),
        "GetProcessAffinityMask": (wintypes.BOOL, [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]),
        "CreatePipe": (wintypes.BOOL, [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(_Security), wintypes.DWORD]),
        "SetHandleInformation": (wintypes.BOOL, [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]),
        "CreateFileW": (wintypes.HANDLE, [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_Security), wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]),
        "InitializeProcThreadAttributeList": (wintypes.BOOL, [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]),
        "UpdateProcThreadAttribute": (wintypes.BOOL, [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]),
        "DeleteProcThreadAttributeList": (None, [ctypes.c_void_p]),
        "CreateProcessW": (wintypes.BOOL, [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                          wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
                                          ctypes.c_void_p, ctypes.POINTER(_ProcessInfo)]),
        "ResumeThread": (wintypes.DWORD, [wintypes.HANDLE]),
        "WaitForSingleObject": (wintypes.DWORD, [wintypes.HANDLE, wintypes.DWORD]),
        "GetExitCodeProcess": (wintypes.BOOL, [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]),
        "ReadFile": (wintypes.BOOL, [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]),
        "CloseHandle": (wintypes.BOOL, [wintypes.HANDLE]),
        "CreateIoCompletionPort": (wintypes.HANDLE, [wintypes.HANDLE, wintypes.HANDLE, ctypes.c_size_t, wintypes.DWORD]),
        "GetQueuedCompletionStatus": (wintypes.BOOL, [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
                                                     ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD]),
    }
    for name, (result, args) in signatures.items():
        function = getattr(kernel, name)
        function.restype, function.argtypes = result, args
    return kernel


def run_worker(command: list[str], *, timeout_seconds=10, memory_limit_bytes=1 << 30,
               max_output_bytes=1 << 20, cwd=None, cpu_affinity_mask=None) -> dict:
    """Execute one worker with hard job memory, output and elapsed boundaries.

    Default affinity is the lowest CPU allowed to this supervisor. Whole-job
    CPU includes exited descendants; peak memory is job committed bytes. The
    elapsed deadline includes setup and checks all descendants, not just the
    root process. Memory allocation denials are classified by job completion
    notifications; Windows does not guarantee delivery of every notification,
    so an unreported denial may appear as backend_error. The memory cap itself
    remains enforced. No worker is launched on unsupported platforms.
    """
    if (type(command) is not list or not command or not command[0] or
            any(type(arg) is not str or "\0" in arg for arg in command)):
        raise ValueError("expected a nonempty command argument list")
    if type(timeout_seconds) not in (float, int) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("invalid elapsed deadline")
    for name, value in (("memory_limit_bytes", memory_limit_bytes), ("max_output_bytes", max_output_bytes)):
        if type(value) is not int or value <= 0 or value > ctypes.c_size_t(-1).value:
            raise ValueError("invalid " + name)
    if cpu_affinity_mask is not None and (type(cpu_affinity_mask) is not int or cpu_affinity_mask <= 0):
        raise ValueError("invalid CPU affinity mask")
    started = time.perf_counter()
    result = {"status": "backend_error", "stdout": "", "stderr": "", "wall_seconds": 0.0,
              "cpu_seconds": None, "cpu_scope": "unavailable", "peak_memory_bytes": None,
              "memory_scope": "unavailable", "returncode": None, "reason": "unsupported_platform",
              "cleanup_verified": True, "cpu_affinity_mask": None,
              "cpu_affinity_scope": "windows_job_current_processor_group",
              "memory_limit_bytes": memory_limit_bytes, "max_output_bytes": max_output_bytes,
              "accounting_limitation": "Committed memory is not RSS. The Windows peak counter can include denied allocation attempts and exceed the cap; memory-limit notification delivery is best effort.",
              "total_processes": 0, "active_processes_after_cleanup": 0,
              "output_bytes_captured": 0, "output_truncated": False}
    if os.name != "nt":
        return result
    kernel = _api()
    handles, readers, buffers = [], [], {"stdout": bytearray(), "stderr": bytearray()}
    output_exceeded, reader_failed = threading.Event(), threading.Event()
    output_lock = threading.Lock()
    captured = 0
    job = port = None
    info = _ProcessInfo()
    attributes = None
    attributes_initialized = False
    assigned = False
    invalid_handle = ctypes.c_void_p(-1).value

    def checked(ok, operation):
        if not ok:
            raise OSError(ctypes.get_last_error(), operation + " failed")
        return ok

    def own(handle):
        checked(handle and handle != invalid_handle, "create handle")
        handles.append(handle)
        return handle

    def close(handle):
        if handle in handles:
            kernel.CloseHandle(handle)
            handles.remove(handle)

    def query(kind, structure):
        value = structure()
        checked(kernel.QueryInformationJobObject(job, kind, ctypes.byref(value), ctypes.sizeof(value), None), "job accounting")
        return value

    def memory_notification():
        message, key, overlap = wintypes.DWORD(), ctypes.c_size_t(), ctypes.c_void_p()
        limited = False
        while kernel.GetQueuedCompletionStatus(port, ctypes.byref(message), ctypes.byref(key), ctypes.byref(overlap), 0):
            limited |= message.value in (9, 10)  # JOB_MEMORY_LIMIT / NOTIFICATION_LIMIT.
        return limited

    def read_pipe(handle, stream):
        nonlocal captured
        block, received = ctypes.create_string_buffer(4096), wintypes.DWORD()
        try:
            while kernel.ReadFile(handle, block, len(block), ctypes.byref(received), None):
                if not received.value:
                    break
                with output_lock:
                    remaining = max_output_bytes - captured
                    keep = min(remaining, received.value)
                    buffers[stream].extend(block.raw[:keep])
                    captured += keep
                    if received.value > keep:
                        output_exceeded.set()
            if ctypes.get_last_error() not in (0, 109):  # ERROR_BROKEN_PIPE is EOF.
                reader_failed.set()
        finally:
            kernel.CloseHandle(handle)

    try:
        allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
        checked(kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(), ctypes.byref(allowed), ctypes.byref(system)), "CPU affinity query")
        chosen = cpu_affinity_mask if cpu_affinity_mask is not None else allowed.value & -allowed.value
        if not chosen or chosen & ~allowed.value:
            raise ValueError("CPU affinity is outside supervisor allowed set")
        result["cpu_affinity_mask"] = chosen
        job = own(kernel.CreateJobObjectW(None, None))
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000 | 0x200 | 0x10  # kill-on-close, job memory, affinity.
        limits.BasicLimitInformation.Affinity = chosen
        limits.JobMemoryLimit = memory_limit_bytes
        checked(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)), "job hard limits")
        port = own(kernel.CreateIoCompletionPort(invalid_handle, None, 0, 1))
        association = _CompletionPort(1, port)
        checked(kernel.SetInformationJobObject(job, 7, ctypes.byref(association), ctypes.sizeof(association)), "job notification port")
        security = _Security(ctypes.sizeof(_Security), None, True)
        pipes = []
        for _ in range(2):
            read_end, write_end = wintypes.HANDLE(), wintypes.HANDLE()
            checked(kernel.CreatePipe(ctypes.byref(read_end), ctypes.byref(write_end), ctypes.byref(security), 0), "output pipe")
            own(read_end.value)
            own(write_end.value)
            checked(kernel.SetHandleInformation(read_end, 1, 0), "pipe inheritance")
            pipes.append((read_end.value, write_end.value))
        stdin = own(kernel.CreateFileW("NUL", 0x80000000, 3, ctypes.byref(security), 3, 0x80, None))
        attribute_size = ctypes.c_size_t()
        kernel.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attribute_size))
        attributes = ctypes.create_string_buffer(attribute_size.value)
        checked(kernel.InitializeProcThreadAttributeList(attributes, 1, 0, ctypes.byref(attribute_size)), "process attribute list")
        attributes_initialized = True
        inherited = (wintypes.HANDLE * 3)(stdin, pipes[0][1], pipes[1][1])
        checked(kernel.UpdateProcThreadAttribute(attributes, 0, 0x20002, inherited, ctypes.sizeof(inherited), None, None), "explicit inherited handles")
        startup = _StartupEx()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.StartupInfo.dwFlags = 0x100 | 1  # standard handles and hidden window.
        startup.StartupInfo.hStdInput = stdin
        startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = pipes[0][1], pipes[1][1]
        startup.lpAttributeList = ctypes.addressof(attributes)
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        checked(kernel.CreateProcessW(None, command_line, None, None, True, 4 | 0x80000 | 0x08000000,
                                      None, os.fspath(cwd) if cwd is not None else None, ctypes.byref(startup), ctypes.byref(info)), "suspended process creation")
        own(info.hProcess)
        own(info.hThread)
        result["cleanup_verified"] = False
        checked(kernel.AssignProcessToJobObject(job, info.hProcess), "assign suspended worker to job")
        assigned = True
        for stream, (read_end, write_end) in zip(("stdout", "stderr"), pipes):
            close(write_end)
            thread = threading.Thread(target=read_pipe, args=(read_end, stream), daemon=True)
            thread.start()
            handles.remove(read_end)  # The reader owns this handle now.
            readers.append(thread)
        close(stdin)
        if kernel.ResumeThread(info.hThread) == 0xFFFFFFFF:
            checked(False, "resume bounded worker")
        close(info.hThread)
        result.update(status="ok", reason="completed", memory_scope="windows_job_peak_committed_bytes",
                      cpu_scope="windows_job_all_processes")
        while True:
            if memory_notification():
                result.update(status="resource_limit", reason="job_memory_limit")
                break
            if output_exceeded.is_set():
                result.update(status="resource_limit", reason="output_limit")
                break
            if reader_failed.is_set():
                result.update(status="backend_error", reason="output_pipe_error")
                break
            if query(1, _Accounting).ActiveProcesses == 0:
                break
            if time.perf_counter() - started >= timeout_seconds:
                result.update(status="timeout", reason="wall_deadline")
                break
            time.sleep(0.01)
    except (OSError, ValueError) as error:
        result.update(status="backend_error", reason=str(error))
    finally:
        if info.hProcess:
            if assigned:
                # Killing an already empty job is harmless; never target a PID tree.
                kernel.TerminateJobObject(job, 1)
            else:
                kernel.TerminateProcess(info.hProcess, 1)  # Only our still-suspended child.
            kernel.WaitForSingleObject(info.hProcess, 5000)
            cleanup_deadline = time.perf_counter() + 5
            if assigned:
                try:
                    accounting = query(1, _Accounting)
                    while accounting.ActiveProcesses and time.perf_counter() < cleanup_deadline:
                        time.sleep(0.01)
                        accounting = query(1, _Accounting)
                    result["cleanup_verified"] = accounting.ActiveProcesses == 0
                    result["total_processes"] = accounting.TotalProcesses
                    result["active_processes_after_cleanup"] = accounting.ActiveProcesses
                    result["cpu_seconds"] = (accounting.TotalUserTime + accounting.TotalKernelTime) / 10_000_000
                    result["peak_memory_bytes"] = query(9, _ExtendedLimits).PeakJobMemoryUsed
                    if memory_notification():
                        result.update(status="resource_limit", reason="job_memory_limit")
                except OSError:
                    result["cleanup_verified"] = False
            else:
                result["cleanup_verified"] = kernel.WaitForSingleObject(info.hProcess, 0) == 0
            code = wintypes.DWORD()
            if kernel.GetExitCodeProcess(info.hProcess, ctypes.byref(code)) and code.value != 259:
                result["returncode"] = code.value
        for reader in readers:
            reader.join(timeout=5)
        if output_exceeded.is_set() and result["status"] == "ok":
            result.update(status="resource_limit", reason="output_limit")
        if (reader_failed.is_set() or any(reader.is_alive() for reader in readers)) and result["status"] == "ok":
            result.update(status="backend_error", reason="output_pipe_incomplete")
        if not result["cleanup_verified"]:
            result.update(status="backend_error", reason="job_cleanup_unverified")
        if result["status"] == "ok" and result["returncode"] != 0:
            result.update(status="backend_error", reason="worker_nonzero_exit")
        if attributes_initialized:
            kernel.DeleteProcThreadAttributeList(attributes)
        for handle in handles[::-1]:
            kernel.CloseHandle(handle)
        with output_lock:
            result["output_bytes_captured"] = captured
            result["output_truncated"] = output_exceeded.is_set()
            for stream, raw in buffers.items():
                # Replacement characters cannot expand the returned UTF-8 byte cap.
                result[stream] = bytes(raw).decode("utf-8", errors="replace").encode("utf-8")[:len(raw)].decode("utf-8", errors="ignore")
        result["wall_seconds"] = time.perf_counter() - started
    return result
