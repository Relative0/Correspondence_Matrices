"""Local end-to-end validation of the corrected single-port bootstrap."""
from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "docs" / "recognition" / "c7_linux_confirmation" / "runpod_c7_linux_single_port_controller.py"


def request(method: str, path: str, token: str, body: bytes | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=2)
    try:
        headers = {"X-CM-Token": token}
        if body is not None:
            headers["Content-Type"] = "application/octet-stream"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        return response.status, json.loads(payload)
    finally:
        connection.close()


def main():
    spec = importlib.util.spec_from_file_location("c7_single_port_controller", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    manifest = controller.load(controller.MANIFEST_PATH)
    bundle = controller.base.make_bundle(manifest)
    created = time.time()
    payload = controller.prepare_payload(bundle, manifest, created)
    token = secrets.token_urlsafe(32)
    environment = dict(os.environ)
    environment.update({
        "CM_BOOTSTRAP_TOKEN": token,
        "CM_PAYLOAD_SHA256": hashlib.sha256(payload).hexdigest(),
        "CM_PAYLOAD_BYTES": str(len(payload)),
        "CM_HARD_DEADLINE": str(created + 30),
    })
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen([sys.executable, "-B", str(controller.BOOTSTRAP_PATH)],
                               env=environment, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=flags)
    try:
        deadline = time.time() + 10
        while True:
            if process.poll() is not None:
                raise RuntimeError("single-port bootstrap exited before health")
            try:
                health_status, health = request("GET", "/health", token)
                if health_status == 200 and health.get("ready") is True:
                    break
            except OSError:
                pass
            if time.time() >= deadline:
                raise RuntimeError("single-port bootstrap health timed out")
            time.sleep(.1)
        upload_status, upload = request("POST", "/payload", token, payload)
        progress_status, progress = request("GET", "/progress", token)
        if (upload_status != 200 or upload.get("accepted_sha256") != hashlib.sha256(payload).hexdigest()
                or progress_status != 200 or progress.get("uploaded") is not True
                or progress.get("stage") != "uploaded"):
            raise RuntimeError("single-port payload route failed local validation")
        print(json.dumps({"status": "pass", "health_http": health_status,
                          "payload_http": upload_status, "progress_http": progress_status,
                          "payload_bytes": len(payload), "source_files": len(manifest["files"])}))
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
