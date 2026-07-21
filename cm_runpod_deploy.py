"""Provision/deploy tooling for the CM RunPod worker (no SSH required).

The pod is created with an inline, token-gated bootstrap HTTP server on port 8080
(`CM_BOOTSTRAP_TOKEN` env). Worker files are pushed through the RunPod HTTPS proxy
(`POST /put`), and `POST /deploy` launches `cm_remote_worker.py` on port 8081 —
the port `CM_RUNPOD_BASE_URL` points at.

Container disk (and the boot-time `pip install numpy`) is wiped on every stop;
`/workspace/cm` (the pushed files) persists on the pod volume. So after a pod
restart, run `--deploy` again to relaunch the worker (files are re-pushed too,
which doubles as the update path after local code changes).

Usage:
  python cm_runpod_deploy.py --provision   # create pod + push files + start worker
                                           #   (writes .env.runpod.local)
  python cm_runpod_deploy.py --deploy      # (re)push files + start worker on the
                                           #   configured, already-running pod
  python cm_runpod_deploy.py --status      # pod + bootstrap + worker health

Credentials come from .env.runpod / .env.runpod.local (see cm_runpod_config.py);
--provision also accepts RUNPOD_API_KEY from the environment when no env file exists.
"""
from __future__ import annotations

import argparse
import base64
import json
import secrets
import sys
import time
from pathlib import Path

import requests

from cm_runpod_config import load_runpod_config

REST = "https://rest.runpod.io/v1"
POD_NAME = "cm-computation-worker"
WORKER_FILES = [
    "cm_exprlib.py",
    "cm_expr_serde.py",
    "bitset_backend.py",
    "cm_ir.py",
    "cm_runpod_protocol.py",
    "cm_remote_worker.py",
]
REPO = Path(__file__).resolve().parent

BOOTSTRAP = r'''
import base64, json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
TOK = os.environ.get("CM_BOOTSTRAP_TOKEN", "")
class H(BaseHTTPRequestHandler):
    def _j(self, o, s=200):
        b = json.dumps(o).encode()
        self.send_response(s)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            self._j({"ok": True, "service": "cm-bootstrap"})
        else:
            self.send_error(404)
    def do_POST(self):
        if TOK and self.headers.get("X-CM-Token") != TOK:
            self._j({"ok": False, "error": "bad token"}, 403)
            return
        n = int(self.headers.get("Content-Length", "0"))
        d = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/put":
            os.makedirs("/workspace/cm", exist_ok=True)
            fn = os.path.basename(d["name"])
            with open("/workspace/cm/" + fn, "wb") as f:
                f.write(base64.b64decode(d["b64"]))
            self._j({"ok": True, "name": fn})
        elif self.path == "/deploy":
            import subprocess
            subprocess.Popen(["python", "-u", "cm_remote_worker.py", "--port", "8081"],
                             cwd="/workspace/cm")
            self._j({"ok": True})
        else:
            self.send_error(404)
    def log_message(self, *a):
        pass
ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
'''

# sh does not unescape \n inside a quoted string, so a multi-line `python -c`
# argument would crash-loop the container; ship the bootstrap as base64 instead.
_BOOT_B64 = base64.b64encode(BOOTSTRAP.encode()).decode()
START_CMD = (
    "pip install --no-cache-dir numpy > /tmp/pip.log 2>&1; "
    'python -u -c "import base64;exec(base64.b64decode(\'' + _BOOT_B64 + "'))\""
)


def _session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {api_key}"})
    return s


def _bootstrap_token(explicit: str = "") -> str:
    if explicit:
        return explicit
    import os

    for line in _env_file_lines():
        if line.startswith("CM_BOOTSTRAP_TOKEN="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("CM_BOOTSTRAP_TOKEN", "")


def _env_file_lines() -> list[str]:
    out: list[str] = []
    for name in (".env.runpod", ".env.runpod.local"):
        p = REPO / name
        if p.exists():
            out.extend(p.read_text(encoding="utf-8").splitlines())
    return out


def _wait_health(url: str, service: str, timeout_s: int, interval: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=10)
            if r.ok and r.json().get("service") == service:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def push_and_start(pod_id: str, token: str) -> None:
    boot_url = f"https://{pod_id}-8080.proxy.runpod.net"
    work_url = f"https://{pod_id}-8081.proxy.runpod.net"
    if not _wait_health(boot_url, "cm-bootstrap", 600, 8.0):
        raise SystemExit("bootstrap on port 8080 never became healthy (is the pod running?)")
    print("bootstrap up")
    hdr = {"X-CM-Token": token} if token else {}
    for name in WORKER_FILES:
        b64 = base64.b64encode((REPO / name).read_bytes()).decode()
        r = requests.post(f"{boot_url}/put", json={"name": name, "b64": b64}, headers=hdr, timeout=60)
        if not (r.ok and r.json().get("ok")):
            raise SystemExit(f"push {name} failed: {r.text[:200]}")
        print(f"pushed {name}")
    r = requests.post(f"{boot_url}/deploy", json={}, headers=hdr, timeout=60)
    if not (r.ok and r.json().get("ok")):
        raise SystemExit(f"deploy failed: {r.text[:200]}")
    if not _wait_health(work_url, "cm-remote-worker", 120, 4.0):
        raise SystemExit("worker on port 8081 never became healthy")
    print(f"worker healthy at {work_url}")


def provision(api_key: str) -> None:
    s = _session(api_key)
    token = secrets.token_urlsafe(24)
    existing = s.get(f"{REST}/pods", timeout=60).json()
    pods = existing.get("pods") if isinstance(existing, dict) else existing
    for p in pods or []:
        if p.get("name") == POD_NAME:
            raise SystemExit(
                f"pod named {POD_NAME!r} already exists (id={p.get('id')}); "
                "use --deploy, or terminate it first"
            )
    body = {
        "name": POD_NAME,
        "computeType": "CPU",
        "cpuFlavorIds": ["cpu3c"],
        "vcpuCount": 2,
        "cloudType": "SECURE",
        "imageName": "python:3.10-slim",
        "containerDiskInGb": 10,
        "volumeInGb": 10,
        "volumeMountPath": "/workspace",
        "ports": ["8080/http", "8081/http"],
        "env": {"CM_BOOTSTRAP_TOKEN": token},
        "dockerEntrypoint": ["sh", "-c"],
        "dockerStartCmd": [START_CMD],
    }
    r = s.post(f"{REST}/pods", json=body, timeout=120)
    if r.status_code >= 300:
        raise SystemExit(f"pod create failed: HTTP {r.status_code} {r.text[:500]}")
    pod = r.json()
    pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
    print(f"created pod id={pod_id} costPerHr={pod.get('costPerHr')}")
    push_and_start(pod_id, token)
    env_path = REPO / ".env.runpod.local"
    env_path.write_text(
        f"RUNPOD_API_KEY={api_key}\n"
        f"RUNPOD_POD_ID={pod_id}\n"
        f"CM_RUNPOD_BASE_URL=https://{pod_id}-8081.proxy.runpod.net\n"
        f"CM_RUNPOD_PERSISTENT_ROOT=/workspace/cm\n"
        f"CM_BOOTSTRAP_TOKEN={token}\n",
        encoding="utf-8",
    )
    print(f"wrote {env_path}")


def status() -> int:
    config = load_runpod_config()
    if not (config.pod_id and config.api_key):
        print("no RUNPOD_POD_ID/RUNPOD_API_KEY configured; run --provision first")
        return 2
    s = _session(config.api_key)
    r = s.get(f"{REST}/pods/{config.pod_id}", timeout=60)
    pod = r.json() if r.ok else {}
    print(f"pod {config.pod_id}: desiredStatus={pod.get('desiredStatus')} costPerHr={pod.get('costPerHr')}")
    boot_url = f"https://{config.pod_id}-8080.proxy.runpod.net"
    boot = _wait_health(boot_url, "cm-bootstrap", 1, 0.1)
    work = _wait_health(config.base_url, "cm-remote-worker", 1, 0.1) if config.base_url else False
    print(f"bootstrap (8080): {'OK' if boot else 'down'}")
    print(f"worker (8081):    {'OK' if work else 'down'}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--provision", action="store_true", help="create the pod, push files, start worker")
    g.add_argument("--deploy", action="store_true", help="push files + start worker on the configured pod")
    g.add_argument("--status", action="store_true", help="pod/bootstrap/worker health")
    args = ap.parse_args()

    if args.status:
        raise SystemExit(status())

    config = load_runpod_config()
    if args.provision:
        import os

        key = config.api_key or os.environ.get("RUNPOD_API_KEY", "")
        if not key:
            raise SystemExit("RUNPOD_API_KEY required (env or .env.runpod[.local])")
        provision(key)
        return

    # --deploy
    if not config.pod_id:
        raise SystemExit("RUNPOD_POD_ID not configured; run --provision first")
    token = _bootstrap_token()
    push_and_start(config.pod_id, token)


if __name__ == "__main__":
    main()
