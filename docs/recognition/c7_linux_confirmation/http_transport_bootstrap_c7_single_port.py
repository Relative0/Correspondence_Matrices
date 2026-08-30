"""Frozen, token-gated standard-library transport for one CM smoke payload."""
import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import signal
import subprocess
import sys
import threading
import time

LOG_CAP = 16 << 20
UPLOAD_CAP = 1 << 20
TOKEN = ""
EXPECTED_HASH = ""
EXPECTED_SIZE = 0
DEADLINE = 0.0
LOCK = threading.Lock()
PAYLOAD = None
LOG = bytearray()
STATE = {"uploaded": False, "started": False, "done": False, "stage": "awaiting-upload", "error": None}


def authenticated(headers):
    supplied = headers.get("X-CM-Token", "")
    return bool(TOKEN) and hmac.compare_digest(supplied, TOKEN)


def validate_payload(raw):
    if len(raw) != EXPECTED_SIZE or len(raw) > UPLOAD_CAP or hashlib.sha256(raw).hexdigest() != EXPECTED_HASH:
        raise ValueError("payload integrity failure")
    value = json.loads(raw)
    if set(value) != {"bundle", "manifest", "code", "environment"}:
        raise ValueError("payload schema mismatch")
    if not all(isinstance(value[key], str) for key in ("bundle", "manifest", "code")):
        raise ValueError("payload encoding mismatch")
    allowed = {"CM_BUNDLE_SHA256", "CM_IMAGE_TAG", "CM_IMAGE_DIGEST", "CM_SETUP_DEADLINE"}
    if set(value["environment"]) != allowed or not all(isinstance(item, str) for item in value["environment"].values()):
        raise ValueError("payload environment mismatch")
    base64.b64decode(value["bundle"], validate=True)
    base64.b64decode(value["manifest"], validate=True)
    base64.b64decode(value["code"], validate=True)
    return value


def child_environment(payload):
    # In particular, do not inherit provider API keys or the bootstrap token.
    env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "RUNPOD_POD_ID") if key in os.environ}
    env.update(payload["environment"])
    env.update({"CM_UPLOAD_MANIFEST": payload["manifest"], "PYTHONUNBUFFERED": "1",
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    encoded = payload["bundle"]
    env.update({"CM_BUNDLE_%03d" % index: encoded[start:start + 16000]
                for index, start in enumerate(range(0, len(encoded), 16000))})
    return env


def kill_worker(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_worker(payload):
    proc = None
    try:
        code = base64.b64decode(payload["code"], validate=True).decode("utf-8")
        proc = subprocess.Popen([sys.executable, "-u", "-c", code], env=child_environment(payload),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)

        def read_output():
            pending = b""
            while True:
                chunk = proc.stdout.read1(4096)
                if not chunk:
                    return
                with LOCK:
                    if len(LOG) + len(chunk) > LOG_CAP:
                        STATE["error"] = "worker log cap exceeded"
                        kill_worker(proc)
                        return
                    LOG.extend(chunk)
                    pending += chunk
                    lines = pending.split(b"\n")
                    pending = lines.pop()
                    for line in lines:
                        if not line.startswith(b"CM_EVENT "):
                            continue
                        try:
                            event = json.loads(line[9:])
                            if event.get("kind") == "stage":
                                STATE["stage"] = event.get("name")
                            if event.get("kind") == "done":
                                STATE["remote_status"] = event.get("status")
                        except (ValueError, UnicodeError):
                            STATE["error"] = "invalid worker event"

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            returncode = proc.wait(timeout=max(0.01, DEADLINE - time.time()))
        except subprocess.TimeoutExpired:
            kill_worker(proc)
            returncode = proc.wait(timeout=5)
            with LOCK:
                STATE["error"] = "worker lifetime exceeded"
        reader.join(timeout=5)
        with LOCK:
            STATE["returncode"] = returncode
            if reader.is_alive():
                STATE["error"] = "worker output did not close"
    except Exception as exc:
        with LOCK:
            STATE["error"] = type(exc).__name__
    finally:
        if proc is not None and proc.poll() is None:
            kill_worker(proc)
        with LOCK:
            STATE["done"] = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.reply(200, {"service": "cm-memory-http", "ready": True})
            return
        if not authenticated(self.headers):
            self.reply(403, {"error": "unauthorized"})
            return
        with LOCK:
            if self.path == "/progress":
                snapshot = dict(STATE)
                snapshot["log_bytes"] = len(LOG)
                self.reply(200, snapshot)
            elif self.path == "/results" and STATE["done"]:
                self.reply(200, bytes(LOG), "application/octet-stream")
            elif self.path == "/results":
                self.reply(425, {"error": "not finished"})
            else:
                self.reply(404, {"error": "unknown endpoint"})

    def do_POST(self):
        global PAYLOAD
        if not authenticated(self.headers):
            self.reply(403, {"error": "unauthorized"})
            return
        if time.time() >= DEADLINE:
            self.reply(410, {"error": "deadline passed"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if self.headers.get("Transfer-Encoding") or length < 0 or length > UPLOAD_CAP:
                raise ValueError("invalid request length")
            if self.path == "/payload":
                if length != EXPECTED_SIZE:
                    raise ValueError("payload length mismatch")
                raw = self.rfile.read(length)
                payload = validate_payload(raw)
                with LOCK:
                    if STATE["started"]:
                        self.reply(409, {"error": "already started"})
                        return
                    PAYLOAD = payload
                    STATE["uploaded"] = True
                    STATE["stage"] = "uploaded"
                self.reply(200, {"accepted_sha256": EXPECTED_HASH})
            elif self.path == "/run":
                if length != 0:
                    raise ValueError("run accepts no command or body")
                with LOCK:
                    if not STATE["uploaded"]:
                        self.reply(409, {"error": "upload required"})
                        return
                    if not STATE["started"]:
                        STATE["started"] = True
                        STATE["stage"] = "starting"
                        threading.Thread(target=run_worker, args=(PAYLOAD,), daemon=True).start()
                        PAYLOAD = None
                self.reply(202, {"started": True})
            else:
                self.reply(404, {"error": "unknown endpoint"})
        except (ValueError, UnicodeError, KeyError, TypeError):
            self.reply(400, {"error": "invalid request"})

    def log_message(self, *args):
        pass


def main():
    global TOKEN, EXPECTED_HASH, EXPECTED_SIZE, DEADLINE
    TOKEN = os.environ.pop("CM_BOOTSTRAP_TOKEN")
    EXPECTED_HASH = os.environ.pop("CM_PAYLOAD_SHA256")
    EXPECTED_SIZE = int(os.environ.pop("CM_PAYLOAD_BYTES"))
    DEADLINE = float(os.environ.pop("CM_HARD_DEADLINE"))
    if len(TOKEN) < 24 or len(EXPECTED_HASH) != 64 or not 0 < EXPECTED_SIZE <= UPLOAD_CAP:
        raise ValueError("invalid bootstrap configuration")
    servers = [ThreadingHTTPServer(("0.0.0.0", 8080), Handler)]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    # The provider lifecycle watchdog is independent; this only stops the server.
    while time.time() < DEADLINE:
        time.sleep(min(1, max(0.01, DEADLINE - time.time())))
    for server in servers:
        server.shutdown()


if __name__ == "__main__":
    main()
