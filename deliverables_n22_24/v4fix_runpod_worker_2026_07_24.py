"""Temporary RunPod worker for the same-box V4 corpus campaigns."""
from __future__ import annotations

import base64
import json
import subprocess
import threading
import traceback
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/workspace/cm")
REPO = ROOT / "repo"
OUT_NAMES = (
    "CM_v4audit_symbolic_build_raw.csv",
    "CM_v4audit_symbolic_build_summary.csv",
    "CM_v4audit_packed_eval_raw.csv",
    "CM_v4audit_packed_eval_summary.csv",
)
STATE = {"done": False, "stage": "starting", "error": None, "commands": []}


def campaign() -> None:
    try:
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ROOT / "repo.zip") as archive:
            archive.extractall(REPO)
        STATE["stage"] = "install-dd"
        install = subprocess.run(
            ["python", "-m", "pip", "install", "--no-cache-dir", "dd"],
            text=True, capture_output=True, timeout=600,
        )
        STATE["commands"].append({"name": "install-dd", "returncode": install.returncode})
        if install.returncode:
            raise RuntimeError(install.stderr[-2000:])
        for script in (
            "deliverables_n22_24/v4audit_symbolic_build_2026_07_24.py",
            "deliverables_n22_24/v4audit_packed_eval_2026_07_24.py",
        ):
            STATE["stage"] = script
            result = subprocess.run(
                ["python", script], cwd=REPO, text=True, capture_output=True, timeout=3600
            )
            STATE["commands"].append({
                "name": script, "returncode": result.returncode,
                "stdout_tail": result.stdout[-1000:], "stderr_tail": result.stderr[-1000:],
            })
            if result.returncode:
                raise RuntimeError(f"{script}: {result.stderr[-2000:]}")
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
            self.send_json({"ok": True, "service": "cm-remote-worker", **STATE})
        elif self.path == "/progress":
            self.send_json(STATE)
        elif self.path == "/results":
            files = {}
            for name in OUT_NAMES:
                path = REPO / "deliverables_n22_24" / name
                if path.exists():
                    files[name] = base64.b64encode(path.read_bytes()).decode()
            self.send_json({"state": STATE, "files": files})
        else:
            self.send_error(404)

    def log_message(self, *_args):
        pass


threading.Thread(target=campaign, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
