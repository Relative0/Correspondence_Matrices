"""Disposable Runpod worker for pinned optional-dependency feasibility checks."""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import itertools
import json
import os
import platform
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path("/workspace/cm")
OUT = ROOT / "out"
WHEELS = OUT / "wheels"
RESULT = OUT / "dependency_feasibility.json"
EXPECTED = {
    "python": "3.13.5",
    "numpy": "2.3.2",
    "numba": "0.67.0",
    "llvmlite": "0.49.0",
    "dd": "0.6.0",
}
STATE: dict[str, object] = {
    "done": False,
    "stage": "starting",
    "error": None,
    "commands": {},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(name: str, command: list[str], timeout_s: int) -> None:
    started = time.perf_counter()
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout_s)
    commands = STATE["commands"]
    assert isinstance(commands, dict)
    commands[name] = {
        "command": command,
        "returncode": result.returncode,
        "wall_s": time.perf_counter() - started,
        "stdout_tail": result.stdout[-8000:],
        "stderr_tail": result.stderr[-8000:],
    }
    if result.returncode:
        raise RuntimeError(f"{name} failed with return code {result.returncode}: {result.stderr[-4000:]}")


def _cpu_environment() -> dict[str, object]:
    cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    model = None
    flags: list[str] = []
    for line in cpuinfo.splitlines():
        if model is None and line.lower().startswith("model name"):
            model = line.split(":", 1)[1].strip()
        if not flags and line.lower().startswith(("flags", "features")):
            flags = sorted(set(line.split(":", 1)[1].strip().split()))
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "logical_cpu_count": os.cpu_count(),
        "cpu_model": model,
        "cpu_flags": flags,
        "cgroup_cpu_max": _read_optional("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": _read_optional("/sys/fs/cgroup/memory.max"),
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
    }


def _read_optional(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _distribution_identity(name: str) -> dict[str, object]:
    distribution = importlib.metadata.distribution(name)
    metadata = distribution.metadata
    license_files = []
    for relative in distribution.files or ():
        normalized = str(relative).lower()
        if "license" not in normalized and "copying" not in normalized:
            continue
        installed = Path(distribution.locate_file(relative))
        if installed.is_file():
            license_files.append(
                {
                    "path": str(relative),
                    "bytes": installed.stat().st_size,
                    "sha256": _sha256(installed),
                }
            )
    classifiers = metadata.get_all("Classifier") or []
    return {
        "name": metadata.get("Name", name),
        "version": distribution.version,
        "license_expression": metadata.get("License-Expression"),
        "license_field": metadata.get("License"),
        "license_classifiers": [item for item in classifiers if item.startswith("License ::")],
        "home_page": metadata.get("Home-page") or metadata.get("Project-URL"),
        "license_files": license_files,
    }


def _numba_smoke() -> dict[str, object]:
    import numba
    import numpy as np

    @numba.njit(cache=False)
    def packed_kernel(left, right, tail_mask):
        result = np.empty(left.shape[0], dtype=np.uint64)
        for index in range(left.shape[0]):
            result[index] = (left[index] & right[index]) ^ (~left[index])
        result[-1] = result[-1] & tail_mask
        return result

    left = np.array(
        [0x0000000000000000, 0x0123456789ABCDEF, 0xFFFFFFFFFFFFFFFF, 0xAAAAAAAAAAAAAAAA],
        dtype=np.uint64,
    )
    right = np.array(
        [0xFFFFFFFFFFFFFFFF, 0xFEDCBA9876543210, 0x0F0F0F0F0F0F0F0F, 0x5555555555555555],
        dtype=np.uint64,
    )
    tail_mask = np.uint64(0x000000000000FFFF)
    expected = np.bitwise_xor(np.bitwise_and(left, right), np.bitwise_not(left))
    expected[-1] = expected[-1] & tail_mask
    first_started = time.perf_counter()
    first = packed_kernel(left, right, tail_mask)
    first_s = time.perf_counter() - first_started
    second_started = time.perf_counter()
    second = packed_kernel(left, right, tail_mask)
    second_s = time.perf_counter() - second_started
    exact = bool(np.array_equal(first, expected) and np.array_equal(second, expected))
    return {
        "exact_ok": exact,
        "input_words": int(left.size),
        "first_call_s_includes_jit": first_s,
        "second_call_s_diagnostic_only": second_s,
        "signatures": [str(signature) for signature in packed_kernel.signatures],
        "timing_claim": False,
        "output_sha256": hashlib.sha256(first.tobytes()).hexdigest(),
    }


def _cudd_smoke() -> dict[str, object]:
    from dd import cudd

    bdd = cudd.BDD()
    bdd.declare("x", "y", "z")
    x = bdd.var("x")
    y = bdd.var("y")
    z = bdd.var("z")
    function = (x & y) | ~z
    failures = []
    rows = []
    for values in itertools.product((False, True), repeat=3):
        assignment = dict(zip(("x", "y", "z"), values))
        observed = bdd.let(assignment, function) == bdd.true
        expected = (values[0] and values[1]) or (not values[2])
        rows.append({"assignment": [int(value) for value in values], "result": bool(observed)})
        if bool(observed) != bool(expected):
            failures.append(assignment)
    restrict_x_false = bdd.let({"x": False}, function) == ~z
    restrict_z_true = bdd.let({"z": True}, function) == (x & y)
    canonical_rebuild = function == ((y & x) | ~z)
    exact = not failures and restrict_x_false and restrict_z_true and canonical_rebuild
    extension = Path(cudd.__file__).resolve()
    return {
        "exact_ok": bool(exact),
        "truth_rows": rows,
        "failures": failures,
        "restriction_x_false_ok": bool(restrict_x_false),
        "restriction_z_true_ok": bool(restrict_z_true),
        "canonical_rebuild_ok": bool(canonical_rebuild),
        "satisfying_assignment_count": int(bdd.count(function, nvars=3)),
        "manager_nodes": len(bdd),
        "extension_path_name": extension.name,
        "extension_sha256": _sha256(extension),
    }


def _campaign() -> None:
    try:
        OUT.mkdir(parents=True, exist_ok=False)
        WHEELS.mkdir()
        STATE["stage"] = "download-wheels"
        requirements = [
            f"numpy=={EXPECTED['numpy']}",
            f"llvmlite=={EXPECTED['llvmlite']}",
            f"numba=={EXPECTED['numba']}",
            f"dd=={EXPECTED['dd']}",
        ]
        _run(
            "pip_download",
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--dest",
                str(WHEELS),
                *requirements,
            ],
            8 * 60,
        )
        wheels = [
            {"filename": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(WHEELS.iterdir())
            if path.is_file()
        ]
        STATE["stage"] = "install-wheels"
        _run(
            "pip_install",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--find-links",
                str(WHEELS),
                "--force-reinstall",
                *requirements,
            ],
            8 * 60,
        )
        STATE["stage"] = "imports-and-exact-smokes"
        import dd
        import llvmlite
        import numba
        import numpy
        from dd import cudd

        observed_versions = {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "numba": numba.__version__,
            "llvmlite": llvmlite.__version__,
            "dd": importlib.metadata.version("dd"),
        }
        versions_ok = observed_versions == EXPECTED
        numba_result = _numba_smoke()
        cudd_result = _cudd_smoke()
        result = {
            "protocol": "CM-RP-D0-2026-08-26",
            "scope": "dependency feasibility and exact tiny smokes only",
            "environment": _cpu_environment(),
            "expected_versions": EXPECTED,
            "observed_versions": observed_versions,
            "versions_ok": versions_ok,
            "imports": {
                "numpy": True,
                "numba": True,
                "llvmlite": True,
                "dd": True,
                "dd.cudd": bool(cudd.__file__),
            },
            "distribution_identities": [
                _distribution_identity(name) for name in ("numpy", "numba", "llvmlite", "dd")
            ],
            "downloaded_distributions": wheels,
            "numba_smoke": numba_result,
            "cudd_smoke": cudd_result,
            "performance_claim": False,
        }
        result["acceptance_pass"] = bool(
            versions_ok
            and wheels
            and numba_result["exact_ok"]
            and cudd_result["exact_ok"]
            and all(result["imports"].values())
        )
        RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        STATE["stage"] = "complete"
        STATE["done"] = True
    except Exception:
        STATE["error"] = traceback.format_exc()
        STATE["stage"] = "failed"


def _result_files() -> dict[str, str]:
    if not OUT.is_dir():
        return {}
    return {
        path.relative_to(ROOT).as_posix(): base64.b64encode(path.read_bytes()).decode("ascii")
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.parent != WHEELS
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "service": "cm-dependency-worker", "stage": STATE["stage"]})
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
