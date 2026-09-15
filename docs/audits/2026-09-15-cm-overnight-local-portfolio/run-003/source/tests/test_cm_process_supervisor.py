"""Tiny owned-process controls; Windows enforcement or explicit OS refusal."""
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import cm_process_supervisor as supervisor


class ProcessSupervisorTests(unittest.TestCase):
    def command(self, code, base=False):
        executable = getattr(sys, "_base_executable", sys.executable) if base else sys.executable
        return [executable, "-B", "-c", code]

    def probe(self, code, *, base=False, **kwargs):
        result = supervisor.run(self.command(code, base), **kwargs)
        if os.name != "nt":
            self.assertEqual(result.status, "refused")
            self.assertFalse(result.resources["launched"])
            return None
        self.assertTrue(result.resources["cleanup_verified"], result)
        self.assertTrue(result.resources["streams_closed"], result)
        self.assertEqual(result.resources["active_processes"], 0, result)
        self.assertFalse(result.resources["whole_tree_rss_measured"])
        return result

    def test_limits_reject_booleans_nonfinite_unbounded_or_too_small_values(self):
        for key, value in (("timeout_seconds", True), ("timeout_seconds", float("nan")),
                           ("timeout_seconds", 61), ("timeout_seconds", 0), ("memory_bytes", 1),
                           ("memory_bytes", 3 << 30), ("processes", 0), ("processes", 33),
                           ("stdout_bytes", 0), ("stderr_bytes", 1 << 21), ("input_bytes", -1)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                replace(supervisor.Limits(), **{key: value}).validate()

    def test_command_and_input_refuse_before_creation(self):
        with patch.object(supervisor.subprocess, "Popen") as launch:
            for command in ([], "python", ["python", "-c", "pass"], [sys.executable, None], [sys.executable, "\0"]):
                with self.assertRaises(ValueError):
                    supervisor.run(command)
            for data in ("text", b"x" * (256 * 1024 + 1)):
                with self.assertRaises(ValueError):
                    supervisor.run(self.command("pass"), input=data)
        launch.assert_not_called()

    def test_bounded_reader_accepts_exact_limit_and_keeps_only_limit_on_overflow(self):
        for data, exceeded in ((b"abcd", False), (b"abcde", True)):
            with tempfile.TemporaryFile() as pipe:
                pipe.write(data)
                pipe.seek(0)
                event = threading.Event()
                reader = supervisor.BoundedStream(4, event)
                reader.read(pipe)
            self.assertEqual(reader.data, b"abcd")
            self.assertEqual(reader.exceeded, exceeded)
            self.assertEqual(event.is_set(), exceeded)

    def test_reader_error_is_retained(self):
        reader = supervisor.BoundedStream(4, threading.Event())
        reader.read(io.BytesIO(b"x"))
        self.assertEqual(reader.error, "UnsupportedOperation")
        self.assertTrue(reader.stop.is_set())

    def test_other_platform_refuses_without_process_or_job(self):
        # Patch only the platform predicate, not pathlib's operating-system choice.
        with patch.object(supervisor, "platform_supported", return_value=False), \
                patch.object(supervisor.subprocess, "Popen") as launch:
            result = supervisor.run(self.command("raise RuntimeError('must not execute')"))
        self.assertEqual(result.status, "refused")
        self.assertEqual(result.reason, "hard_process_tree_limits_unavailable")
        self.assertFalse(result.resources["launched"])
        launch.assert_not_called()

    def test_real_echo_binds_worker_to_job_and_caps_committed_memory(self):
        data = b"x" * (128 * 1024)
        result = self.probe("import json,os,sys; d=sys.stdin.buffer.read(); print(json.dumps([os.getpid(),len(d)]))", input=data)
        if result is None:
            return
        self.assertEqual(result.status, "ok", result)
        pid, length = json.loads(result.stdout)
        self.assertEqual(length, len(data))
        self.assertIn(pid, result.resources["observed_job_pids"])
        self.assertTrue(result.resources["attached_before_resume"])
        self.assertGreater(result.resources["peak_job_committed_bytes"], 0)
        self.assertLessEqual(result.resources["peak_job_committed_bytes"], result.resources["job_memory_limit_bytes"])

    def test_real_stdout_flood_is_bounded_and_tree_cleaned(self):
        result = self.probe("import os; " + "\nwhile True: os.write(1,b'x'*8192)",
                            limits=replace(supervisor.Limits(), stdout_bytes=4096))
        if result is not None:
            self.assertEqual(result.status, "output_limit", result)
            self.assertEqual(len(result.stdout), 4096)
            self.assertTrue(result.resources["stdout_truncated"])

    def test_real_stderr_flood_is_bounded_and_tree_cleaned(self):
        result = self.probe("import os; " + "\nwhile True: os.write(2,b'x'*8192)",
                            limits=replace(supervisor.Limits(), stderr_bytes=2048))
        if result is not None:
            self.assertEqual(result.status, "output_limit", result)
            self.assertEqual(len(result.stderr), 2048)
            self.assertTrue(result.resources["stderr_truncated"])

    def test_nonzero_exit_is_not_success(self):
        result = self.probe("raise SystemExit(7)")
        if result is not None:
            self.assertEqual(result.status, "error", result)
            self.assertEqual(result.reason, "worker_nonzero_exit")
            self.assertEqual(result.returncode, 7)

    def test_blocked_stdin_cannot_block_timeout_and_cleanup(self):
        result = self.probe("import time; time.sleep(30)", input=b"x" * (256 * 1024),
                            limits=replace(supervisor.Limits(), timeout_seconds=2))
        if result is not None:
            self.assertEqual(result.status, "timeout", result)
            self.assertLess(result.wall_ns, 10_000_000_000)

    def test_timeout_cleans_child_and_grandchild(self):
        leaf = "import time; time.sleep(30)"
        child = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-B','-c',{leaf!r}]); time.sleep(30)"
        parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-B','-c',{child!r}]); time.sleep(30)"
        result = self.probe(parent, base=True, limits=replace(supervisor.Limits(), timeout_seconds=3))
        if result is not None:
            self.assertEqual(result.status, "timeout", result)
            self.assertGreaterEqual(result.resources["total_processes"], 3)
            self.assertGreaterEqual(len(result.resources["observed_job_pids"]), 3)

    def test_parent_exit_does_not_leave_child_running(self):
        code = "import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'])"
        result = self.probe(code, base=True)
        if result is not None:
            self.assertEqual(result.status, "error", result)
            self.assertEqual(result.reason, "descendants_survived_root_exit")
            self.assertGreaterEqual(result.resources["total_processes"], 2)

    def test_job_commit_limit_rejects_large_reservation_with_small_positive_control(self):
        code = """import ctypes,json
dll=ctypes.WinDLL('kernel32',use_last_error=True)
dll.VirtualAlloc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong,ctypes.c_ulong]
dll.VirtualAlloc.restype=ctypes.c_void_p
dll.VirtualFree.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong]
dll.VirtualFree.restype=ctypes.c_int
small=dll.VirtualAlloc(None,1<<20,0x3000,4)
if small: dll.VirtualFree(small,0,0x8000)
large=dll.VirtualAlloc(None,64<<20,0x3000,4)
error=ctypes.get_last_error()
if large: dll.VirtualFree(large,0,0x8000)
print(json.dumps({'small_succeeded':bool(small),'large_refused':not bool(large),'error':error}))
"""
        result = self.probe(code, base=True, limits=replace(supervisor.Limits(), memory_bytes=32 << 20))
        if result is not None:
            self.assertEqual(result.status, "ok", result)
            value = json.loads(result.stdout)
            self.assertTrue(value["small_succeeded"], result)
            self.assertTrue(value["large_refused"], result)
            self.assertGreater(value["error"], 0)
            # Windows can report a peak above the cap even when VirtualAlloc
            # refused the request. Keep the raw counter, not a clamped value.
            self.assertGreater(result.resources["peak_job_committed_bytes"], 0)
            larger = self.probe(code, base=True, limits=replace(supervisor.Limits(), memory_bytes=128 << 20))
            self.assertEqual(larger.status, "ok", larger)
            positive = json.loads(larger.stdout)
            self.assertTrue(positive["small_succeeded"], larger)
            self.assertFalse(positive["large_refused"], larger)

    def test_job_setup_failure_never_launches(self):
        def refuse(_limits):
            raise OSError("injected job setup failure")

        with patch.object(supervisor.subprocess, "Popen") as launch:
            result = supervisor.run(self.command("pass"), job_factory=refuse)
        self.assertEqual(result.status, "refused")
        self.assertFalse(result.resources["launched"])
        launch.assert_not_called()

    def test_assignment_failure_kills_suspended_process_without_releasing_workload(self):
        if os.name != "nt":
            self.assertEqual(supervisor.run(self.command("pass")).status, "refused")
            return

        class FailedAssignment(supervisor.WindowsJob):
            def attach(self, process):
                raise OSError("injected assignment failure")

            def resume(self, pid):
                raise AssertionError("must never resume")

        result = supervisor.run(self.command("print('must not execute')"), job_factory=FailedAssignment)
        self.assertEqual(result.status, "refused", result)
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.resources["cleanup_verified"])
        self.assertFalse(result.resources["attached_before_resume"])


if __name__ == "__main__":
    unittest.main()
