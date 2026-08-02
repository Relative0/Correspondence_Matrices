"""B6 pod worker: cross-platform replication of the corrected E3 (B1) run.

Pushed to each pod as ``cm_remote_worker.py`` so the standard bootstrap's
``/deploy`` launches it. Stages: unpack repo.zip; record environment
provenance (CPU model, cgroup cpu/memory limits, python/numpy, RunPod env);
verify the CURRENT cm_remote_worker protocol end-to-end in-process (a
words_eval request must echo ``remote_words_eval`` — the fix-2 provenance
gate); then run the frozen corrected-E3 driver on the frozen corpus and
serve results. No local-fallback path exists: everything runs on this pod.
"""
from __future__ import annotations

import base64
import json
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
STATE = {"done": False, "stage": "starting", "error": None,
         "env": {}, "worker_echo_verified": None, "driver": {}}


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def collect_env():
    import os
    env = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "cgroup_cpu_max": read_text("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": read_text("/sys/fs/cgroup/memory.max"),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
        "runpod_cpu_count": os.cpu_count(),
    }
    cpuinfo = read_text("/proc/cpuinfo") or ""
    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            env["cpu_model"] = line.split(":", 1)[1].strip()
            break
    try:
        import numpy
        env["numpy"] = numpy.__version__
    except Exception as exc:
        env["numpy"] = f"ERROR {exc}"
    return env


def verify_worker_echo():
    """In-process verification of the current worker protocol: a words_eval
    request must produce the remote_words_eval echo (latent fix 2)."""
    import sys
    sys.path.insert(0, str(REPO))
    from cm_runpod_protocol import CMRemoteRequest
    import cm_remote_worker as worker
    from cm_exprlib import And, Or, Var, Xor
    expr = Xor(And(Var(0), Var(1)), Or(Var(2), And(Var(3), Xor(Var(4), Var(5)))))
    req = CMRemoteRequest.from_expr(
        expr, vars_all=tuple(f"x{i}" for i in range(8)), words_eval=True)
    resp = worker.execute_cm_request(req)
    echo = (resp.diagnostics or {}).get("remote_words_eval")
    return {"ok": bool(resp.ok), "remote_words_eval_echo": echo,
            "verified": bool(resp.ok) and echo is True}


def campaign():
    try:
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ROOT / "repo.zip") as archive:
            archive.extractall(REPO)
        STATE["stage"] = "env"
        STATE["env"] = collect_env()
        STATE["stage"] = "verify-worker-echo"
        STATE["worker_echo_verified"] = verify_worker_echo()
        if not STATE["worker_echo_verified"]["verified"]:
            raise RuntimeError("current-worker words echo verification failed "
                               "(fail closed; no evidence collected)")
        STATE["stage"] = "driver"
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python", "deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py",
             "--corpus", "deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl",
             "--out-dir", "deliverables_n22_24/pod_out"],
            cwd=REPO, text=True, capture_output=True, timeout=1800)
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
                            "role": "b6-replication", "stage": STATE["stage"]})
        elif self.path == "/progress":
            self.send_json(STATE)
        elif self.path == "/results":
            files = {}
            out_dir = REPO / "deliverables_n22_24" / "pod_out"
            for name in ("cm_gap_e3_corrected_results_2026_08_02.json",
                         "CM_gap_e3_corrected_summary_2026_08_02.csv"):
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
