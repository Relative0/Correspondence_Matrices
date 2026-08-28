"""Repeat transport checks and verify Windows venv watchdog process binding."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import uuid

import check_http_transport as checks
import runpod_http_smoke_controller_v2 as controller


def main():
    c = controller
    compile(Path(c.__file__).read_text(encoding="utf-8"), c.__file__, "exec")
    checks.controller = c
    with patch.object(c, "windows_pid_running", lambda pid: True):
        checks.main()
        direct = SimpleNamespace(pid=101, poll=lambda: None)
        assert c.bind_watchdog(direct, {"pid": 101, "parent_pid": 99})["venv_redirector_observed"] is False
        redirector = SimpleNamespace(pid=101, poll=lambda: None)
        assert c.bind_watchdog(redirector, {"pid": 102, "parent_pid": 101})["venv_redirector_observed"] is True
        try:
            c.bind_watchdog(SimpleNamespace(pid=101, poll=lambda: None), {"pid": 102, "parent_pid": 999})
            raise AssertionError("unrelated worker accepted")
        except RuntimeError:
            pass
    with patch.object(c, "windows_pid_running", lambda pid: False):
        try:
            c.bind_watchdog(SimpleNamespace(pid=101, poll=lambda: None), {"pid": 102, "parent_pid": 101})
            raise AssertionError("dead worker accepted")
        except RuntimeError:
            pass
    # A real, trivial local child verifies the runtime-specific redirector and
    # read-only Windows handle mechanism; no network, secrets or workload.
    code = 'import os,json,time;print(json.dumps({"pid":os.getpid(),"parent_pid":os.getppid()}),flush=True);time.sleep(2)'
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    proc = subprocess.Popen([sys.executable, "-B", "-c", code], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=flags, close_fds=True)
    ready = json.loads(proc.stdout.readline())
    binding = c.bind_watchdog(proc, ready)
    assert c.windows_pid_running(ready["pid"])
    proc.communicate(timeout=5)
    assert proc.returncode == 0 and not c.windows_pid_running(ready["pid"])
    report = {"status": "passed", "base_transport_cases": 25, "additional_binding_cases": 4,
              "real_trivial_child_binding": binding, "worker_exit_observed": True,
              "network_requests": 0, "credentials_read": False, "workload_executed": False,
              "controller_sha256": __import__("hashlib").sha256(Path(c.__file__).read_bytes()).hexdigest()}
    c.write(c.HERE / ("HTTP-WINDOWS-WATCHDOG-CHECK-" + uuid.uuid4().hex[:8] + ".json"), report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
