"""Disposable RP-D0 retry worker with a pinned pure-Python astutils build."""

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
import urllib.parse
import urllib.request
import zipfile


ROOT = Path("/workspace/cm")
OUT = ROOT / "out"
WHEELS = OUT / "wheels"
SOURCES = OUT / "sources"
RESULT = OUT / "dependency_feasibility.json"
ASTUTILS_VERSION = "0.0.6"
ASTUTILS_SHA256 = "e9a6f31b243ecfc3c7c84dd2f145cf5de83e475b650d2a6b781cfa713ad15427"
EXPECTED = {
    "python": "3.13.5",
    "numpy": "2.3.2",
    "numba": "0.67.0",
    "llvmlite": "0.49.0",
    "dd": "0.6.0",
    "astutils": ASTUTILS_VERSION,
}
BUILD_TOOLS = ("setuptools==84.0.0", "wheel==0.48.0")
TARGETS = (
    "numpy==2.3.2",
    "llvmlite==0.49.0",
    "numba==0.67.0",
    "dd==0.6.0",
)
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


def _run(name: str, command: list[str], timeout_s: int) -> subprocess.CompletedProcess[str]:
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
    return result


def _read_optional(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _environment() -> dict[str, object]:
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


def _download_astutils_sdist() -> tuple[Path, dict[str, object]]:
    with urllib.request.urlopen(
        f"https://pypi.org/pypi/astutils/{ASTUTILS_VERSION}/json", timeout=60
    ) as response:
        release = json.load(response)
    candidates = [
        item
        for item in release.get("urls", [])
        if item.get("packagetype") == "sdist" and item.get("filename") == f"astutils-{ASTUTILS_VERSION}.tar.gz"
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one pinned astutils sdist, found {len(candidates)}")
    item = candidates[0]
    published_sha = str(item.get("digests", {}).get("sha256", "")).lower()
    if published_sha != ASTUTILS_SHA256:
        raise RuntimeError(f"PyPI astutils digest changed: {published_sha}")
    parsed = urllib.parse.urlparse(str(item["url"]))
    if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
        raise RuntimeError(f"unexpected astutils source host: {parsed.hostname!r}")
    target = SOURCES / str(item["filename"])
    with urllib.request.urlopen(str(item["url"]), timeout=60) as response:
        content = response.read(1 << 20)
        if response.read(1):
            raise RuntimeError("astutils source exceeds 1 MiB safety bound")
    target.write_bytes(content)
    actual_sha = _sha256(target)
    if actual_sha != ASTUTILS_SHA256:
        raise RuntimeError(f"downloaded astutils digest mismatch: {actual_sha}")
    return target, {
        "filename": target.name,
        "bytes": target.stat().st_size,
        "sha256": actual_sha,
        "url": str(item["url"]),
        "upload_time_iso_8601": item.get("upload_time_iso_8601"),
        "requires_python": item.get("requires_python"),
        "packagetype": item.get("packagetype"),
    }


def _artifact_inventory() -> list[dict[str, object]]:
    return [
        {
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "kind": "wheel" if path.suffix == ".whl" else "unexpected",
        }
        for path in sorted(WHEELS.iterdir())
        if path.is_file()
    ]


def _assert_dd_wheel_contains_cudd() -> dict[str, object]:
    matches = sorted(WHEELS.glob("dd-0.6.0-*.whl"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one dd 0.6.0 wheel, found {len(matches)}")
    wheel_path = matches[0]
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
    cudd_extensions = sorted(
        name for name in names if name.startswith("dd/cudd") and name.endswith(".so")
    )
    license_files = sorted(name for name in names if "license" in name.lower() or "copying" in name.lower())
    if not cudd_extensions:
        raise RuntimeError("pinned dd wheel does not contain a dd.cudd shared object")
    return {
        "filename": wheel_path.name,
        "sha256": _sha256(wheel_path),
        "cudd_extensions": cudd_extensions,
        "license_files": license_files,
    }


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
    truth_rows = []
    for values in itertools.product((False, True), repeat=3):
        assignment = dict(zip(("x", "y", "z"), values))
        observed = bdd.let(assignment, function) == bdd.true
        expected = (values[0] and values[1]) or (not values[2])
        truth_rows.append({"assignment": [int(value) for value in values], "result": bool(observed)})
        if bool(observed) != bool(expected):
            failures.append(assignment)
    restrict_x_false = bdd.let({"x": False}, function) == ~z
    restrict_z_true = bdd.let({"z": True}, function) == (x & y)
    canonical_rebuild = function == ((y & x) | ~z)
    extension = Path(cudd.__file__).resolve()
    ldd = _run("cudd_ldd", ["ldd", str(extension)], 30)
    exact = not failures and restrict_x_false and restrict_z_true and canonical_rebuild
    return {
        "exact_ok": bool(exact),
        "truth_rows": truth_rows,
        "failures": failures,
        "restriction_x_false_ok": bool(restrict_x_false),
        "restriction_z_true_ok": bool(restrict_z_true),
        "canonical_rebuild_ok": bool(canonical_rebuild),
        "satisfying_assignment_count": int(bdd.count(function, nvars=3)),
        "manager_nodes": len(bdd),
        "extension_path_name": extension.name,
        "extension_sha256": _sha256(extension),
        "ldd": ldd.stdout.splitlines(),
    }


def _campaign() -> None:
    try:
        OUT.mkdir(parents=True, exist_ok=False)
        WHEELS.mkdir()
        SOURCES.mkdir()
        for forbidden in ("DD_FETCH", "DD_CUDD", "DD_CUDD_ZDD", "DD_SYLVAN", "DD_BUDDY"):
            os.environ.pop(forbidden, None)

        STATE["stage"] = "download-build-tool-wheels"
        _run(
            "download_build_tools",
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--no-deps",
                "--dest",
                str(WHEELS),
                *BUILD_TOOLS,
            ],
            4 * 60,
        )
        _run(
            "install_build_tools",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--find-links",
                str(WHEELS),
                *BUILD_TOOLS,
            ],
            4 * 60,
        )

        STATE["stage"] = "download-and-verify-astutils-source"
        astutils_source, astutils_source_identity = _download_astutils_sdist()
        STATE["stage"] = "build-astutils-wheel"
        _run(
            "build_astutils_wheel",
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(WHEELS),
                str(astutils_source),
            ],
            4 * 60,
        )
        astutils_wheels = sorted(WHEELS.glob(f"astutils-{ASTUTILS_VERSION}-*.whl"))
        if len(astutils_wheels) != 1:
            raise RuntimeError(f"expected one built astutils wheel, found {len(astutils_wheels)}")

        STATE["stage"] = "resolve-binary-targets"
        _run(
            "download_binary_targets",
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--find-links",
                str(WHEELS),
                "--dest",
                str(WHEELS),
                *TARGETS,
            ],
            8 * 60,
        )
        artifacts = _artifact_inventory()
        if not artifacts or any(item["kind"] != "wheel" for item in artifacts):
            raise RuntimeError("resolved target directory contains a non-wheel artifact")
        dd_wheel = _assert_dd_wheel_contains_cudd()

        STATE["stage"] = "offline-install"
        _run(
            "offline_install",
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
                *TARGETS,
            ],
            8 * 60,
        )
        pip_check = _run("pip_check", [sys.executable, "-m", "pip", "check"], 60)

        STATE["stage"] = "imports-and-exact-smokes"
        import astutils
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
            "astutils": importlib.metadata.version("astutils"),
        }
        versions_ok = observed_versions == EXPECTED
        numba_result = _numba_smoke()
        cudd_result = _cudd_smoke()
        result: dict[str, object] = {
            "protocol": "CM-RP-D0-RUN2-2026-08-26",
            "scope": "dependency feasibility and exact tiny smokes only",
            "environment": _environment(),
            "expected_versions": EXPECTED,
            "observed_versions": observed_versions,
            "versions_ok": versions_ok,
            "source_build": {
                "package": "astutils",
                "source": astutils_source_identity,
                "built_wheel": {
                    "filename": astutils_wheels[0].name,
                    "bytes": astutils_wheels[0].stat().st_size,
                    "sha256": _sha256(astutils_wheels[0]),
                },
                "pure_python_wheel": "-py3-none-any.whl" in astutils_wheels[0].name,
            },
            "no_cudd_source_build": True,
            "dd_wheel_contents": dd_wheel,
            "pip_check": {"ok": True, "stdout": pip_check.stdout.strip()},
            "imports": {
                "numpy": True,
                "numba": True,
                "llvmlite": True,
                "dd": True,
                "dd.cudd": bool(cudd.__file__),
                "astutils": bool(astutils.__file__),
            },
            "distribution_identities": [
                _distribution_identity(name)
                for name in ("numpy", "numba", "llvmlite", "dd", "astutils", "setuptools", "wheel")
            ],
            "resolved_wheels": artifacts,
            "downloaded_distributions": artifacts,
            "numba_smoke": numba_result,
            "cudd_smoke": cudd_result,
            "performance_claim": False,
        }
        result["acceptance_pass"] = bool(
            versions_ok
            and result["source_build"]["pure_python_wheel"]
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
        if path.is_file() and path.parent not in {WHEELS, SOURCES}
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
            self._json({"ok": True, "service": "cm-dependency-worker-run2", "stage": STATE["stage"]})
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
