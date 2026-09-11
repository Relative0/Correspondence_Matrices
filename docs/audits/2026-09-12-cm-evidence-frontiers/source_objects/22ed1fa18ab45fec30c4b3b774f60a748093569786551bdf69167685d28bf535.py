"""Token-gated transport for one sealed q64 second-host replication."""
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
import tempfile
import threading
import time


UPLOAD_CAP = 32 << 20
LOG_CAP = 32 << 20
REMOTE_CODE_B64 = "__CM_REMOTE_CODE_B64__"
TOKEN = ""
EXPECTED_HASH = ""
EXPECTED_SIZE = 0
DEADLINE = 0.0
LOCK = threading.Lock()
PAYLOAD_PATH = None
MACHINE_ID = None
LOG = bytearray()
STATE = {
    "uploaded": False,
    "started": False,
    "done": False,
    "stage": "awaiting-upload",
    "error": None,
}


def authenticated(headers):
    supplied = headers.get("X-CM-Token", "")
    return bool(TOKEN) and hmac.compare_digest(supplied, TOKEN)


def kill_worker(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def child_environment():
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "RUNPOD_POD_ID")
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment.update({
        "CM_BUNDLE_PATH": str(PAYLOAD_PATH),
        "CM_BUNDLE_SHA256": EXPECTED_HASH,
        "CM_IMAGE_TAG": os.environ["CM_IMAGE_TAG"],
        "CM_IMAGE_DIGEST": os.environ["CM_IMAGE_DIGEST"],
        "CM_RUNPOD_MACHINE_ID": MACHINE_ID,
        "PYTHONUNBUFFERED": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })
    return environment


def run_worker():
    process = None
    try:
        code = base64.b64decode(REMOTE_CODE_B64, validate=True).decode("utf-8")
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            env=child_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        def read_output():
            pending = b""
            while True:
                chunk = process.stdout.read1(4096)
                if not chunk:
                    return
                with LOCK:
                    if len(LOG) + len(chunk) > LOG_CAP:
                        STATE["error"] = "worker log cap exceeded"
                        kill_worker(process)
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
            returncode = process.wait(timeout=max(0.01, DEADLINE - time.time()))
        except subprocess.TimeoutExpired:
            kill_worker(process)
            returncode = process.wait(timeout=5)
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
        if process is not None and process.poll() is None:
            kill_worker(process)
        with LOCK:
            STATE["done"] = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

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
            self.reply(200, {"service": "cm-q64-second-host", "ready": True})
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
        global MACHINE_ID, PAYLOAD_PATH
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
                machine_id = self.headers.get("X-CM-Machine-ID", "")
                if not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", machine_id):
                    raise ValueError("invalid physical-machine placement identity")
                if length != EXPECTED_SIZE:
                    raise ValueError("payload length mismatch")
                raw = self.rfile.read(length)
                if len(raw) != EXPECTED_SIZE or hashlib.sha256(raw).hexdigest() != EXPECTED_HASH:
                    raise ValueError("payload integrity failure")
                with LOCK:
                    if STATE["started"]:
                        self.reply(409, {"error": "already started"})
                        return
                    if PAYLOAD_PATH is not None:
                        self.reply(409, {"error": "payload already accepted"})
                        return
                    path = Path(tempfile.gettempdir()) / "cm-q64-second-host-source.zip"
                    with path.open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    PAYLOAD_PATH = path
                    MACHINE_ID = machine_id
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
                        threading.Thread(target=run_worker, daemon=True).start()
                self.reply(202, {"started": True})
            else:
                self.reply(404, {"error": "unknown endpoint"})
        except (ValueError, UnicodeError, KeyError, TypeError, OSError):
            self.reply(400, {"error": "invalid request"})

    def log_message(self, *args):
        pass


def main():
    global TOKEN, EXPECTED_HASH, EXPECTED_SIZE, DEADLINE
    TOKEN = os.environ.pop("CM_BOOTSTRAP_TOKEN")
    EXPECTED_HASH = os.environ.pop("CM_PAYLOAD_SHA256")
    EXPECTED_SIZE = int(os.environ.pop("CM_PAYLOAD_BYTES"))
    DEADLINE = float(os.environ.pop("CM_HARD_DEADLINE"))
    if (
        len(TOKEN) < 24
        or len(EXPECTED_HASH) != 64
        or not 0 < EXPECTED_SIZE <= UPLOAD_CAP
        or ("__CM_REMOTE_" + "CODE_B64__") in REMOTE_CODE_B64
    ):
        raise ValueError("invalid bootstrap configuration")
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    while time.time() < DEADLINE:
        time.sleep(min(1, max(0.01, DEADLINE - time.time())))
    server.shutdown()


if __name__ == "__main__":
    main()
