"""Fail-closed Runpod worker for the 2026-08-24 selector replication.

The worker verifies every packaged source/corpus digest, runs the current
selector harness and a frozen B1 control, and serves only a fixed allow-list of
evidence files.  There is no local fallback path.
"""
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
SNAPSHOT_MANIFEST = REPO / "selector_runpod_snapshot_manifest_2026_08_24.json"
SELECTOR_PREFIX = REPO / "deliverables_n22_24" / "pod_out" / "current"
B1_OUT = REPO / "deliverables_n22_24" / "pod_out" / "b1"
STATE = {
    "done": False,
    "stage": "starting",
    "error": None,
    "environment": {},
    "input_verification": {},
    "drivers": {},
}

RESULT_FILES = (
    "deliverables_n22_24/pod_out/current_raw.csv",
    "deliverables_n22_24/pod_out/current_summary.json",
    "deliverables_n22_24/pod_out/current_selector.csv",
    "deliverables_n22_24/pod_out/current_phases.csv",
    "deliverables_n22_24/pod_out/current_environment.json",
    "deliverables_n22_24/pod_out/b1/cm_gap_e3_corrected_results_2026_08_02.json",
    "deliverables_n22_24/pod_out/b1/CM_gap_e3_corrected_summary_2026_08_02.csv",
)


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _collect_environment() -> dict:
    environment = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "cgroup_cpu_max": _read_text("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": _read_text("/sys/fs/cgroup/memory.max"),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
    }
    cpuinfo = _read_text("/proc/cpuinfo") or ""
    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            environment["cpu_model"] = line.split(":", 1)[1].strip()
            break
    try:
        import numpy

        environment["numpy"] = numpy.__version__
    except Exception as exc:
        environment["numpy"] = f"ERROR: {exc}"
    return environment


def _verify_snapshot() -> dict:
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    mismatches = []
    verified = []
    for relative, expected in sorted(manifest["files_sha256"].items()):
        path = REPO / relative
        actual = _sha256(path) if path.is_file() else None
        verified.append({"path": relative, "expected": expected, "actual": actual})
        if actual != expected:
            mismatches.append(relative)
    return {
        "ok": not mismatches,
        "archive_source_file_count": len(verified),
        "mismatches": mismatches,
        "verified": verified,
    }


def _run_driver(name: str, command: list[str], timeout: int) -> None:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    record = {
        "command": command,
        "returncode": result.returncode,
        "wall_s": time.perf_counter() - started,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    STATE["drivers"][name] = record
    if result.returncode:
        raise RuntimeError(f"{name} failed: {result.stderr[-4000:]}")


def _campaign() -> None:
    try:
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ROOT / "repo.zip") as archive:
            archive.extractall(REPO)

        STATE["stage"] = "environment"
        STATE["environment"] = _collect_environment()
        if STATE["environment"].get("python") != "3.13.5":
            raise RuntimeError(
                "runtime mismatch: expected Python 3.13.5, got "
                f"{STATE['environment'].get('python')}"
            )
        if STATE["environment"].get("numpy") != "2.3.2":
            raise RuntimeError(
                "runtime mismatch: expected NumPy 2.3.2, got "
                f"{STATE['environment'].get('numpy')}"
            )

        STATE["stage"] = "verify-inputs"
        STATE["input_verification"] = _verify_snapshot()
        if not STATE["input_verification"]["ok"]:
            raise RuntimeError(
                "snapshot digest verification failed: "
                + ", ".join(STATE["input_verification"]["mismatches"])
            )

        STATE["stage"] = "selector-driver"
        _run_driver(
            "selector",
            [
                "python",
                "scripts/cm_deep_performance_audit.py",
                "--suite",
                "representative",
                "--corpora",
                "bx1,b2,epfl",
                "--prep-repetitions",
                "3",
                "--kernel-rounds",
                "5",
                "--max-kernel-temporary-bytes",
                "8388608",
                "--output-prefix",
                str(SELECTOR_PREFIX.relative_to(REPO)),
            ],
            timeout=12 * 60,
        )

        STATE["stage"] = "b1-control"
        _run_driver(
            "b1",
            [
                "python",
                "deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py",
                "--corpus",
                "deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl",
                "--out-dir",
                str(B1_OUT.relative_to(REPO)),
            ],
            timeout=8 * 60,
        )

        missing = [relative for relative in RESULT_FILES if not (REPO / relative).is_file()]
        if missing:
            raise RuntimeError("missing expected result files: " + ", ".join(missing))
        STATE["stage"] = "complete"
        STATE["done"] = True
    except Exception:
        STATE["error"] = traceback.format_exc()
        STATE["stage"] = "failed"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "cm-remote-worker",
                    "role": "selector-replication-2026-08-24",
                    "stage": STATE["stage"],
                }
            )
        elif self.path == "/progress":
            self._send_json(STATE)
        elif self.path == "/results":
            files = {}
            for relative in RESULT_FILES:
                path = REPO / relative
                if path.is_file():
                    files[relative] = base64.b64encode(path.read_bytes()).decode("ascii")
            self._send_json({"state": STATE, "files": files})
        else:
            self.send_error(404)

    def log_message(self, *_args: object) -> None:
        pass


threading.Thread(target=_campaign, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
