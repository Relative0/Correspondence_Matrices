"""Actual tiny subprocesses exercise Windows limits, accounting and cleanup."""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import pytest

from cmbench import biology_session_supervisor as supervisor


windows = pytest.mark.skipif(os.name != "nt", reason="Windows Job Objects required")


def child(source, **kwargs):
    return supervisor.run_worker([sys.executable, "-B", "-c", source], **kwargs)


def assert_clean(row):
    assert row["cleanup_verified"] is True
    assert row["active_processes_after_cleanup"] == 0


@windows
def test_success_job_accounting_affinity_and_cwd(tmp_path):
    row = child(
        "import ctypes,json,os; k=ctypes.windll.kernel32; "
        "k.GetCurrentProcess.restype=ctypes.c_void_p; "
        "k.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]; "
        "p=ctypes.c_size_t(); s=ctypes.c_size_t(); "
        "k.GetProcessAffinityMask(k.GetCurrentProcess(),ctypes.byref(p),ctypes.byref(s)); "
        "print(json.dumps({'cwd':os.getcwd(),'mask':p.value})); print('diagnostic',file=__import__('sys').stderr)",
        cwd=tmp_path,
    )
    assert row["status"] == "ok", row
    assert row["returncode"] == 0
    assert json.loads(row["stdout"]) == {"cwd": str(tmp_path), "mask": row["cpu_affinity_mask"]}
    assert row["cpu_affinity_mask"].bit_count() == 1
    assert row["stderr"].strip() == "diagnostic"
    assert row["cpu_seconds"] >= 0
    assert row["peak_memory_bytes"] > 0
    assert row["cpu_scope"] == "windows_job_all_processes"
    assert row["memory_scope"] == "windows_job_peak_committed_bytes"
    assert "not RSS" in row["accounting_limitation"]
    assert_clean(row)


@windows
def test_limits_installed_and_job_assigned_before_thread_resumes(monkeypatch):
    kernel = supervisor._api()
    events = []
    for name in ("SetInformationJobObject", "CreateProcessW", "AssignProcessToJobObject", "ResumeThread"):
        original = getattr(kernel, name)
        def wrapped(*args, _name=name, _original=original):
            if _name == "CreateProcessW":
                assert args[5] & 4  # CREATE_SUSPENDED.
            events.append(_name)
            return _original(*args)
        setattr(kernel, name, wrapped)
    monkeypatch.setattr(supervisor, "_api", lambda: kernel)
    row = child("print('bounded')")
    assert row["status"] == "ok", row
    assert events.index("SetInformationJobObject") < events.index("CreateProcessW")
    assert events.index("CreateProcessW") < events.index("AssignProcessToJobObject") < events.index("ResumeThread")
    assert_clean(row)


@windows
def test_nonzero_exit_and_missing_executable():
    row = child("import sys; print('bad',file=sys.stderr); sys.exit(7)")
    assert row["status"] == "backend_error" and row["returncode"] == 7
    assert row["stderr"].strip() == "bad"
    assert_clean(row)
    missing = supervisor.run_worker(["cm-supervisor-missing-executable-7bc2fc.exe"])
    assert missing["status"] == "backend_error" and missing["returncode"] is None
    assert_clean(missing)


@windows
def test_timeout_cleans_live_descendants_after_parent_exits():
    row = child(
        "import subprocess,sys; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        "print(p.pid,flush=True)", timeout_seconds=0.8,
    )
    assert row["status"] == "timeout", row
    assert row["reason"] == "wall_deadline"
    assert row["stdout"].strip().isdigit()
    assert row["total_processes"] >= 2
    assert row["wall_seconds"] < 8
    assert_clean(row)


@windows
def test_cpu_and_peak_include_descendant_work():
    row = child(
        "import subprocess,sys; subprocess.run([sys.executable,'-c',"
        "'import time; data=bytearray(48<<20); end=time.process_time()+0.25; exec(\"while time.process_time()<end: pass\")'],check=True)",
        memory_limit_bytes=256 << 20,
    )
    assert row["status"] == "ok", row
    assert row["cpu_seconds"] >= 0.2
    assert row["peak_memory_bytes"] >= 48 << 20
    assert row["total_processes"] >= 2
    assert_clean(row)


@windows
def test_combined_output_cap_and_invalid_utf8_are_bounded():
    row = child("import os; os.write(1,b'x'*800); os.write(2,b'\\xff'*3000)", max_output_bytes=1024)
    assert row["status"] == "resource_limit", row
    assert row["reason"] == "output_limit" and row["output_truncated"]
    assert row["output_bytes_captured"] == 1024
    assert len(row["stdout"].encode()) + len(row["stderr"].encode()) <= 1024
    assert_clean(row)


@windows
def test_job_memory_limit_notification_and_cleanup():
    row = child("data=bytearray(256<<20)", memory_limit_bytes=64 << 20)
    assert row["status"] == "resource_limit", row
    assert row["reason"] == "job_memory_limit"
    assert row["memory_limit_bytes"] == 64 << 20
    assert_clean(row)


@windows
def test_memory_is_denied_by_os_even_without_notification_observer(monkeypatch):
    # Disable only the observer. Job limits remain installed and enforced by
    # Windows, demonstrating that the memory cap does not depend on polling.
    kernel = supervisor._api()
    kernel.GetQueuedCompletionStatus = lambda *args: False
    monkeypatch.setattr(supervisor, "_api", lambda: kernel)
    row = child(
        "try:\n data=bytearray(256<<20)\n print('allocation_succeeded')\n"
        "except MemoryError:\n print('allocation_denied')", memory_limit_bytes=64 << 20,
    )
    assert row["status"] == "ok", row
    assert row["stdout"].strip() == "allocation_denied"
    assert_clean(row)


@windows
def test_memory_cap_is_shared_by_descendants():
    row = child(
        "import subprocess,sys,time; code='import time; data=bytearray(64<<20); time.sleep(30)'; "
        "children=[subprocess.Popen([sys.executable,'-c',code]) for _ in range(2)]; time.sleep(30)",
        memory_limit_bytes=128 << 20,
    )
    assert row["status"] == "resource_limit", row
    assert row["reason"] == "job_memory_limit"
    assert row["total_processes"] >= 3
    assert_clean(row)


@windows
def test_assignment_failure_never_executes_suspended_worker(monkeypatch):
    kernel = supervisor._api()
    kernel.AssignProcessToJobObject = lambda *args: False
    monkeypatch.setattr(supervisor, "_api", lambda: kernel)
    row = child("print('must never execute',flush=True)")
    assert row["status"] == "backend_error"
    assert "assign suspended worker" in row["reason"]
    assert row["stdout"] == row["stderr"] == ""
    assert_clean(row)


@windows
def test_invalid_affinity_does_not_start_worker():
    row = child("raise RuntimeError('must not run')", cpu_affinity_mask=1 << 100)
    assert row["status"] == "backend_error" and row["returncode"] is None
    assert "affinity" in row["reason"]
    assert row["stdout"] == row["stderr"] == ""
    assert_clean(row)


def test_unsupported_platform_does_not_launch(monkeypatch):
    monkeypatch.setattr(supervisor, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(supervisor, "_api", lambda: pytest.fail("must not load native API"))
    row = supervisor.run_worker(["unused"])
    assert row["status"] == "backend_error" and row["reason"] == "unsupported_platform"
    assert row["cpu_seconds"] is None and row["peak_memory_bytes"] is None
    assert_clean(row)


@pytest.mark.parametrize("kwargs", [{"timeout_seconds": float("nan")}, {"timeout_seconds": 0},
                                    {"memory_limit_bytes": True}, {"max_output_bytes": 0}])
def test_invalid_configuration_rejected_before_launch(kwargs):
    with pytest.raises(ValueError):
        supervisor.run_worker(["unused"], **kwargs)
