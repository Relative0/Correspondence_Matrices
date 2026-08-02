"""B5 pod worker: install dd with CUDD, run the matched comparison, serve results.

Pushed as ``cm_remote_worker.py`` so the bootstrap's /deploy launches it.
Fail closed: if dd.cudd cannot be imported after install, the campaign
errors out — no autoref fallback is ever measured.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import subprocess
import threading
import time
import traceback
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/workspace/cm")
REPO = ROOT / "repo"
STATE = {"done": False, "stage": "starting", "error": None, "env": {},
         "install": {}, "driver": {}}


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def collect_env():
    env = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cgroup_cpu_max": read_text("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": read_text("/sys/fs/cgroup/memory.max"),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
        "cpu_count": os.cpu_count(),
    }
    for line in (read_text("/proc/cpuinfo") or "").splitlines():
        if line.lower().startswith("model name"):
            env["cpu_model"] = line.split(":", 1)[1].strip()
            break
    return env


def campaign():
    try:
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ROOT / "repo.zip") as archive:
            archive.extractall(REPO)
        STATE["stage"] = "env"
        STATE["env"] = collect_env()
        STATE["stage"] = "install-build-tools"
        apt = subprocess.run(
            ["sh", "-c", "apt-get update -qq && apt-get install -y -qq gcc make"],
            text=True, capture_output=True, timeout=900)
        STATE["install"]["apt_rc"] = apt.returncode
        STATE["stage"] = "install-dd-cudd"
        # dd 0.5.7 ignores the DD_CUDD env vars (observed run 2); use the
        # documented source route: setup.py install --fetch --cudd.
        script = (
            "set -e; pip install --no-cache-dir cython; "
            "mkdir -p /tmp/ddsrc && cd /tmp/ddsrc; "
            "pip download dd --no-deps --no-binary dd -d .; "
            "tar xzf dd-*.tar.gz; cd dd-*/; "
            "python setup.py install --fetch --cudd")
        inst = None
        for _attempt in range(3):  # the CUDD tarball host times out sometimes
            inst = subprocess.run(["sh", "-c", script],
                                  text=True, capture_output=True, timeout=1800)
            if inst.returncode == 0:
                break
            time.sleep(20)
        STATE["install"]["pip_rc"] = inst.returncode
        STATE["install"]["pip_tail"] = (inst.stdout + inst.stderr)[-1500:]
        check = subprocess.run(
            ["python", "-c", "import dd.cudd; print('cudd-ok')"],
            text=True, capture_output=True, timeout=120)
        STATE["install"]["cudd_import"] = check.stdout.strip() or check.stderr[-500:]
        if "cudd-ok" not in check.stdout:
            raise RuntimeError("dd.cudd unavailable after install — fail closed, "
                               "no autoref fallback: " + check.stderr[-1000:])
        pipver = subprocess.run(
            ["python", "-m", "pip", "show", "dd"], text=True,
            capture_output=True, timeout=120)
        STATE["install"]["dd_version_info"] = pipver.stdout[:400]
        STATE["stage"] = "driver"
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python", "deliverables_n22_24/cm_b5_cudd_matched_2026_08_03.py"],
            cwd=REPO, text=True, capture_output=True, timeout=2400)
        STATE["driver"] = {
            "returncode": result.returncode,
            "wall_s": time.perf_counter() - t0,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }
        if result.returncode:
            raise RuntimeError(f"driver failed: {result.stderr[-2000:]}")
        STATE["stage"] = "complete"
        STATE["done"] = True
    except Exception:
        STATE["error"] = traceback.format_exc()
        STATE["stage"] = "failed"


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json({"ok": True, "service": "cm-remote-worker",
                            "role": "b5-cudd", "stage": STATE["stage"]})
        elif self.path == "/progress":
            self.send_json(STATE)
        elif self.path == "/results":
            files = {}
            out_dir = REPO / "deliverables_n22_24" / "pod_out"
            for name in ("cm_b5_cudd_matched_results_2026_08_03.json",
                         "CM_b5_cudd_matched_summary_2026_08_03.csv"):
                p = out_dir / name
                if p.exists():
                    files[name] = base64.b64encode(p.read_bytes()).decode()
            self.send_json({"state": STATE, "files": files})
        else:
            self.send_error(404)

    def log_message(self, *_a):
        pass


threading.Thread(target=campaign, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
