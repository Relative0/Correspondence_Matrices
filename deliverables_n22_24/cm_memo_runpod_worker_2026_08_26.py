"""Fail-closed Runpod worker for CM one-memo preparation replication."""

from __future__ import annotations

import base64
import hashlib
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
ARCHIVE = ROOT / "repo.zip"
ARCHIVE_SHA = ROOT / "repo.zip.sha256"
MANIFEST = REPO / "selector_runpod_snapshot_manifest_2026_08_24.json"
POD_OUT = REPO / "deliverables_n22_24/pod_out"
STATE = {
    "done": False,
    "stage": "starting",
    "error": None,
    "environment": {},
    "input_verification": {},
    "drivers": {},
}
EPFL_CHUNKS = ((0, 20), (20, 20), (40, 20), (60, 20), (80, 20), (100, 20), (120, 9))


def _text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _environment() -> dict:
    value = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "cgroup_cpu_max": _text("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": _text("/sys/fs/cgroup/memory.max"),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
    }
    cpuinfo = _text("/proc/cpuinfo") or ""
    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            value["cpu_model"] = line.split(":", 1)[1].strip()
            break
    import numpy

    value["numpy"] = numpy.__version__
    return value


def _verify_archive() -> dict:
    expected = ARCHIVE_SHA.read_text(encoding="ascii").strip().lower()
    actual = _sha(ARCHIVE)
    return {"expected": expected, "actual": actual, "ok": expected == actual}


def _verify_inputs() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mismatches = []
    for relative, expected in manifest["files_sha256"].items():
        path = REPO / relative
        if not path.is_file() or _sha(path) != expected:
            mismatches.append(relative)
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "archive_source_file_count": len(manifest["files_sha256"]),
    }


def _run(name: str, command: list[str], timeout: int) -> None:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    STATE["drivers"][name] = {
        "command": command,
        "returncode": result.returncode,
        "wall_s": time.perf_counter() - started,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode:
        raise RuntimeError(f"{name} failed: {result.stderr[-4000:]}")


def _required_results() -> list[str]:
    prefixes = ["memo_bx1_b2"] + [f"memo_epfl_{start:03d}" for start, _ in EPFL_CHUNKS]
    required = []
    for prefix in prefixes:
        root = f"deliverables_n22_24/pod_out/{prefix}"
        required.extend(
            (
                root + "_raw.csv",
                root + "_summary.json",
                root + "_environment.json",
                root + "_source_snapshot/source_manifest.json",
            )
        )
    return required


def _campaign() -> None:
    try:
        STATE["stage"] = "verify-archive"
        STATE["archive_verification"] = _verify_archive()
        if not STATE["archive_verification"]["ok"]:
            raise RuntimeError("archive SHA-256 verification failed")
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ARCHIVE) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("archive member CRC verification failed")
            archive.extractall(REPO)
        STATE["stage"] = "environment"
        STATE["environment"] = _environment()
        if (
            STATE["environment"]["python"] != "3.13.5"
            or STATE["environment"]["numpy"] != "2.3.2"
        ):
            raise RuntimeError(f"runtime mismatch: {STATE['environment']}")
        STATE["stage"] = "verify-inputs"
        STATE["input_verification"] = _verify_inputs()
        if not STATE["input_verification"]["ok"]:
            raise RuntimeError("source/corpus digest verification failed")

        STATE["stage"] = "selector-driver"
        _run(
            "memo_bx1_b2",
            [
                "python",
                "scripts/cm_prepare_memo_ablation.py",
                "--suite",
                "representative",
                "--corpora",
                "bx1,b2",
                "--repetitions",
                "11",
                "--skip-allocation",
                "--output-prefix",
                "deliverables_n22_24/pod_out/memo_bx1_b2",
            ],
            15 * 60,
        )
        for start, limit in EPFL_CHUNKS:
            name = f"memo_epfl_{start:03d}"
            STATE["stage"] = name
            _run(
                name,
                [
                    "python",
                    "scripts/cm_prepare_memo_ablation.py",
                    "--suite",
                    "representative",
                    "--corpora",
                    "epfl",
                    "--repetitions",
                    "5",
                    "--skip-allocation",
                    "--record-start",
                    str(start),
                    "--record-limit",
                    str(limit),
                    "--output-prefix",
                    f"deliverables_n22_24/pod_out/{name}",
                ],
                10 * 60,
            )
        missing = [relative for relative in _required_results() if not (REPO / relative).is_file()]
        if missing:
            raise RuntimeError("missing outputs: " + ", ".join(missing))
        STATE["stage"] = "complete"
        STATE["done"] = True
    except Exception:
        STATE["error"] = traceback.format_exc()
        STATE["stage"] = "failed"


def _result_files() -> dict[str, str]:
    if not POD_OUT.is_dir():
        return {}
    return {
        path.relative_to(REPO).as_posix(): base64.b64encode(path.read_bytes()).decode()
        for path in sorted(POD_OUT.rglob("*"))
        if path.is_file()
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "service": "cm-memo-worker", "stage": STATE["stage"]})
        elif self.path == "/progress":
            self._json(STATE)
        elif self.path == "/results":
            self._json({"state": STATE, "files": _result_files()})
        else:
            self.send_error(404)

    def log_message(self, *_args: object) -> None:
        pass


threading.Thread(target=_campaign, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
