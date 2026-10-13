"""Ephemeral token-gated receiver for the authorized CM benchmark shards."""
import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time


REMOTE_CODE_B64 = "__CM_REMOTE_CODE_B64__"
TOKEN = os.environ.pop("CM_BOOTSTRAP_TOKEN")
EXPECTED = json.loads(os.environ.pop("CM_SHARDS_JSON"))
DEADLINE = float(os.environ.pop("CM_HARD_DEADLINE"))
UPLOAD = Path("/workspace/cm-benchmark-upload")
RESULT = Path("/workspace/cm-benchmark-result.zip")
CAP = 256 << 20
LOCK = threading.Lock()
LOG = bytearray()
STATE = {"stage": "awaiting-shards", "done": False, "error": None, "uploaded": []}
UPLOAD.mkdir(parents=True, exist_ok=False)


def authenticated(headers):
    return bool(TOKEN) and hmac.compare_digest(headers.get("X-CM-Token", ""), TOKEN)


def run_worker():
    process = None
    try:
        with LOCK:
            STATE["stage"] = "environment-probe"
        code = base64.b64decode(REMOTE_CODE_B64, validate=True).decode("utf-8")
        env = {key: value for key, value in os.environ.items() if key not in {"CM_SHARDS_JSON", "CM_BOOTSTRAP_TOKEN"}}
        env.update({"CM_SHARD_DIR": str(UPLOAD), "CM_SHARDS": json.dumps(EXPECTED),
                    "CM_RESULT_PATH": str(RESULT), "PYTHONUNBUFFERED": "1"})
        process = subprocess.Popen([sys.executable, "-u", "-c", code], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        while True:
            chunk = process.stdout.read1(65536)
            if not chunk:
                break
            with LOCK:
                if len(LOG) + len(chunk) > CAP:
                    STATE["error"] = "worker log cap exceeded"
                    os.killpg(process.pid, signal.SIGKILL)
                    break
                LOG.extend(chunk)
                for line in chunk.decode("utf-8", "replace").splitlines():
                    if line.startswith("CM_STAGE "):
                        STATE["stage"] = line[9:][:120]
        remaining = max(0.01, DEADLINE - time.time())
        code = process.wait(timeout=remaining)
        with LOCK:
            if code != 0 and not STATE["error"]:
                STATE["error"] = "worker exit " + str(code)
            if code == 0 and not RESULT.is_file():
                STATE["error"] = "worker omitted result archive"
    except subprocess.TimeoutExpired:
        if process is not None:
            os.killpg(process.pid, signal.SIGKILL)
        with LOCK:
            STATE["error"] = "environment probe deadline exceeded"
    except Exception as exc:
        with LOCK:
            STATE["error"] = type(exc).__name__
    finally:
        with LOCK:
            STATE["done"] = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *_):
        return

    def reply(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.reply(200, {"service": "cm-benchmark-shards", "ready": True})
            return
        if not authenticated(self.headers):
            self.reply(403, {"error": "unauthorized"})
            return
        with LOCK:
            if self.path == "/progress":
                self.reply(200, {**STATE, "log_bytes": len(LOG)})
            elif self.path == "/log" and STATE["done"]:
                self.reply(200, bytes(LOG), "application/octet-stream")
            elif self.path == "/artifact" and STATE["done"] and RESULT.is_file():
                data = RESULT.read_bytes()
                self.reply(200, data, "application/zip")
            else:
                self.reply(425 if not STATE["done"] else 404, {"error": "not ready"})

    def do_POST(self):
        if not authenticated(self.headers):
            self.reply(403, {"error": "unauthorized"})
            return
        if time.time() >= DEADLINE:
            self.reply(410, {"error": "deadline passed"})
            return
        match = re.fullmatch(r"/shard/([0-9]{3})", self.path)
        if match:
            index = int(match.group(1)) - 1
            if index < 0 or index >= len(EXPECTED):
                self.reply(404, {"error": "unknown shard"})
                return
            row = EXPECTED[index]
            length = int(self.headers.get("Content-Length", "-1"))
            if self.headers.get("Transfer-Encoding") or length != row["bytes"] or length > 64 << 20:
                self.reply(400, {"error": "length mismatch"})
                return
            data = self.rfile.read(length)
            if len(data) != length or hashlib.sha256(data).hexdigest() != row["sha256"]:
                self.reply(400, {"error": "digest mismatch"})
                return
            target = UPLOAD / row["path"]
            with LOCK:
                if target.exists():
                    if hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
                        self.reply(409, {"error": "existing shard mismatch"})
                        return
                else:
                    target.write_bytes(data)
                if row["path"] not in STATE["uploaded"]:
                    STATE["uploaded"].append(row["path"])
                STATE["stage"] = "uploaded-%d-of-%d" % (len(STATE["uploaded"]), len(EXPECTED))
            self.reply(200, {"accepted_sha256": row["sha256"]})
            return
        if self.path == "/run":
            with LOCK:
                if STATE["done"] or STATE.get("started"):
                    self.reply(409, {"error": "already started"})
                    return
                if len(STATE["uploaded"]) != len(EXPECTED):
                    self.reply(409, {"error": "shards incomplete"})
                    return
                STATE["started"] = True
            threading.Thread(target=run_worker, daemon=True).start()
            self.reply(202, {"started": True})
            return
        self.reply(404, {"error": "unknown endpoint"})


server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever(poll_interval=0.5)
