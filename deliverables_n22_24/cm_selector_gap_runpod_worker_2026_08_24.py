"""Fail-closed Runpod worker for the frozen k=13..15 selector gap study."""
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
MANIFEST = REPO / "selector_runpod_snapshot_manifest_2026_08_24.json"
PREFIX = REPO / "deliverables_n22_24/pod_out/current"
B1_OUT = REPO / "deliverables_n22_24/pod_out/b1"
CORPUS = REPO / "deliverables_n22_24/followups_2026_08_24/selector_gap/selector_gap_corpus.jsonl"
STATE = {"done": False, "stage": "starting", "error": None, "environment": {},
         "input_verification": {}, "drivers": {}}
RESULT_FILES = (
    "deliverables_n22_24/pod_out/current_raw.csv",
    "deliverables_n22_24/pod_out/current_selector.csv",
    "deliverables_n22_24/pod_out/current_audit.json",
    "deliverables_n22_24/pod_out/current_environment.json",
    "deliverables_n22_24/pod_out/b1/cm_gap_e3_corrected_results_2026_08_02.json",
    "deliverables_n22_24/pod_out/b1/CM_gap_e3_corrected_summary_2026_08_02.csv",
)


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
        "platform": platform.platform(), "python": platform.python_version(),
        "machine": platform.machine(), "logical_cpu_count": os.cpu_count(),
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


def _verify() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mismatches = []
    for relative, expected in manifest["files_sha256"].items():
        path = REPO / relative
        if not path.is_file() or _sha(path) != expected:
            mismatches.append(relative)
    return {"ok": not mismatches, "mismatches": mismatches,
            "archive_source_file_count": len(manifest["files_sha256"])}


def _run(name: str, command: list[str], timeout: int) -> None:
    started = time.perf_counter()
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True, timeout=timeout)
    STATE["drivers"][name] = {
        "command": command, "returncode": result.returncode,
        "wall_s": time.perf_counter() - started,
        "stdout_tail": result.stdout[-4000:], "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode:
        raise RuntimeError(f"{name} failed: {result.stderr[-4000:]}")


def _campaign() -> None:
    try:
        STATE["stage"] = "unpack"
        with zipfile.ZipFile(ROOT / "repo.zip") as archive:
            archive.extractall(REPO)
        STATE["stage"] = "environment"
        STATE["environment"] = _environment()
        if STATE["environment"]["python"] != "3.13.5" or STATE["environment"]["numpy"] != "2.3.2":
            raise RuntimeError(f"runtime mismatch: {STATE['environment']}")
        STATE["stage"] = "verify-inputs"
        STATE["input_verification"] = _verify()
        if not STATE["input_verification"]["ok"]:
            raise RuntimeError("snapshot digest verification failed")
        STATE["stage"] = "selector-driver"
        _run("selector_gap", [
            "python", "scripts/cm_selector_gap_study.py", "--corpus", str(CORPUS.relative_to(REPO)),
            "--output-prefix", str(PREFIX.relative_to(REPO)), "--prep-repetitions", "3",
            "--kernel-rounds", "5", "--max-kernel-temporary-bytes", "16777216",
        ], 12 * 60)
        STATE["stage"] = "b1-control"
        _run("b1", [
            "python", "deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py",
            "--corpus", "deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl",
            "--out-dir", str(B1_OUT.relative_to(REPO)),
        ], 8 * 60)
        missing = [relative for relative in RESULT_FILES if not (REPO / relative).is_file()]
        if missing:
            raise RuntimeError("missing outputs: " + ", ".join(missing))
        STATE["stage"] = "complete"
        STATE["done"] = True
    except Exception:
        STATE["error"] = traceback.format_exc()
        STATE["stage"] = "failed"


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
            self._json({"ok": True, "service": "cm-remote-worker", "stage": STATE["stage"]})
        elif self.path == "/progress":
            self._json(STATE)
        elif self.path == "/results":
            files = {relative: base64.b64encode((REPO / relative).read_bytes()).decode()
                     for relative in RESULT_FILES if (REPO / relative).is_file()}
            self._json({"state": STATE, "files": files})
        else:
            self.send_error(404)

    def log_message(self, *_args: object) -> None:
        pass


threading.Thread(target=_campaign, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
