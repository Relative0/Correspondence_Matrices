"""Frozen Linux/native readiness scout; never a performance ranking."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
import zipfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import linux_supervisor
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.readiness import environment_record, extension_identity, file_identity, validate_allocation
from scripts.cm_measurement_verify import independent_auditor, scalar_vector
from scripts.cm_native_contracts import (
    d4_competition_count_command,
    parse_d4_competition_count,
    probe_cases,
    sat_contract,
)


SCHEMA = "cm-comparative-native-scout/v1"
LOCK = Path("study/RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json")
D4 = Path("external/d4v2/scripts/d4ScriptsCompetition/bin/d4")
D4_SHA256 = "29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39"
MAX_DOWNLOAD_BYTES = 8 << 20
MAX_TOTAL_DOWNLOAD_BYTES = 16 << 20
MAX_SETUP_OUTPUT = 256 << 10


def write_new(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def validate_dependency_lock(lock: Any) -> dict[str, Any]:
    if not isinstance(lock, dict) or set(lock) != {
        "schema", "target", "source_builds_allowed", "source_builds_forbidden",
        "artifacts", "resolver_rule", "performance_measurement",
    }:
        raise ValueError("dependency lock fields")
    if lock["schema"] != "cm-runpod-native-scout-dependencies/v1" or lock["performance_measurement"] is not False:
        raise ValueError("dependency lock scope")
    if lock["source_builds_allowed"] != ["astutils==0.0.6", "ply==3.10"]:
        raise ValueError("source build allowlist")
    if lock["source_builds_forbidden"] != ["dd==0.6.0", "python-sat==1.9.dev15"]:
        raise ValueError("binary target boundary")
    expected = {
        "setuptools": ("84.0.0", "wheel"),
        "wheel": ("0.48.0", "wheel"),
        "ply": ("3.10", "source"),
        "astutils": ("0.0.6", "source"),
        "networkx": ("3.6.1", "wheel"),
        "dd": ("0.6.0", "wheel"),
        "six": ("1.17.0", "wheel"),
        "python-sat": ("1.9.dev15", "wheel"),
    }
    if not isinstance(lock["artifacts"], list) or len(lock["artifacts"]) != len(expected):
        raise ValueError("dependency artifact cardinality")
    observed = {}
    filenames: set[str] = set()
    total_bytes = 0
    for row in lock["artifacts"]:
        if not isinstance(row, dict) or set(row) != {"name", "version", "kind", "filename", "bytes", "sha256", "url"}:
            raise ValueError("dependency artifact fields")
        name = row["name"]
        if name in observed or expected.get(name) != (row["version"], row["kind"]):
            raise ValueError("dependency artifact identity")
        if not all(isinstance(row[field], str) for field in ("name", "version", "kind", "filename", "sha256", "url")):
            raise ValueError("dependency artifact types")
        parts = urlsplit(row["url"])
        if (
            type(row["bytes"]) is not int
            or not 1 <= row["bytes"] <= MAX_DOWNLOAD_BYTES
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", row["filename"]) is None
            or row["filename"] in filenames
            or parts.scheme != "https"
            or parts.netloc != "files.pythonhosted.org"
            or not parts.path.startswith("/packages/")
            or parts.query != ""
            or parts.fragment != ""
            or not row["url"].endswith("/" + row["filename"])
            or any(piece in {"", ".", ".."} for piece in parts.path.split("/")[1:])
        ):
            raise ValueError("dependency artifact bounds")
        filenames.add(row["filename"])
        total_bytes += row["bytes"]
        observed[name] = row
    if total_bytes > MAX_TOTAL_DOWNLOAD_BYTES:
        raise ValueError("dependency aggregate download bound")
    return observed


def fetch_dependencies(lock_path: Path, destination: Path) -> dict[str, Path]:
    rows = validate_dependency_lock(json.loads(lock_path.read_text(encoding="utf-8")))
    destination.mkdir(exist_ok=False)
    opener = urllib.request.build_opener(NoRedirect)
    paths = {}
    for name, row in rows.items():
        request = urllib.request.Request(row["url"], headers={"User-Agent": "cm-native-scout/1"})
        with opener.open(request, timeout=30) as response:
            if response.geturl() != row["url"] or response.status != 200:
                raise RuntimeError("dependency response identity")
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) != row["bytes"]:
                raise RuntimeError("dependency content length")
            payload = response.read(row["bytes"] + 1)
        if len(payload) != row["bytes"] or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise RuntimeError("dependency payload identity")
        target = destination / row["filename"]
        target.write_bytes(payload)
        paths[name] = target
    return paths


def setup_command(name: str, command: list[str], output: Path, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout, check=False,
                            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    if len(result.stdout) > MAX_SETUP_OUTPUT or len(result.stderr) > MAX_SETUP_OUTPUT:
        raise RuntimeError(name + " output exceeded bound")
    record = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "wall_s": time.monotonic() - started,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        "stdout_tail": result.stdout[-4000:].decode("utf-8", errors="replace"),
        "stderr_tail": result.stderr[-4000:].decode("utf-8", errors="replace"),
    }
    write_new(output / (name + ".json"), record)
    if result.returncode:
        raise RuntimeError(name + " failed")
    return record


def wheel_metadata(path: Path, expected_name: str, expected_version: str) -> dict[str, Any]:
    if not path.is_file() or not zipfile.is_zipfile(path):
        raise ValueError("built wheel missing")
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("wheel metadata cardinality")
        text = archive.read(names[0]).decode("utf-8")
    fields = dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)
    if fields.get("Name", "").lower() != expected_name.lower() or fields.get("Version") != expected_version:
        raise ValueError("built wheel metadata identity")
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "name": fields["Name"], "version": fields["Version"]}


def install_dependencies(output: Path, lock_path: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cm-native-dependencies-") as directory:
        temporary = Path(directory)
        downloads = fetch_dependencies(lock_path, temporary / "downloads")
        built = temporary / "built-wheels"
        built.mkdir()
        python = str(Path(sys.executable).resolve())
        commands = []
        commands.append(setup_command("install-build-tools", [python, "-m", "pip", "install", "--no-index", "--no-deps",
                                      str(downloads["setuptools"]), str(downloads["wheel"])], output, 120))
        for name, version in (("ply", "3.10"), ("astutils", "0.0.6")):
            commands.append(setup_command("build-" + name, [python, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                                          "--wheel-dir", str(built), str(downloads[name])], output, 120))
            matches = list(built.glob(name + "-*.whl"))
            if len(matches) != 1:
                raise RuntimeError("built wheel cardinality")
            wheel_metadata(matches[0], name, version)
            commands.append(setup_command("install-" + name, [python, "-m", "pip", "install", "--no-index", "--no-deps",
                                          str(matches[0])], output, 60))
        commands.append(setup_command("install-native-targets", [python, "-m", "pip", "install", "--no-index", "--no-deps",
                                      str(downloads["networkx"]), str(downloads["dd"]), str(downloads["six"]),
                                      str(downloads["python-sat"])], output, 180))
        commands.append(setup_command("pip-check", [python, "-m", "pip", "check"], output, 60))
        downloaded = {name: file_identity(path) for name, path in downloads.items()}
        built_identities = [wheel_metadata(path, "ply" if path.name.startswith("ply-") else "astutils",
                                           "3.10" if path.name.startswith("ply-") else "0.0.6")
                            for path in sorted(built.glob("*.whl"))]
    versions = {name: importlib.metadata.version(name) for name in (
        "setuptools", "wheel", "ply", "astutils", "networkx", "dd", "six", "python-sat"
    )}
    expected = {name: row["version"] for name, row in validate_dependency_lock(
        json.loads(lock_path.read_text(encoding="utf-8"))).items()}
    if versions != expected:
        raise RuntimeError("installed dependency versions")
    return {"versions": versions, "commands": len(commands),
            "downloaded": downloaded, "built": built_identities,
            "temporary_artifacts_retained": False}


def export_cudd_graph(manager: Any, root: Any) -> dict[str, Any]:
    if getattr(root, "bdd", None) is not manager:
        raise ValueError("CUDD root-manager identity")
    graph: dict[str, Any] = {"level_of_var": dict(manager.var_levels)}
    memo: dict[Any, int] = {}

    def visit(node: Any) -> str | int:
        if node == manager.true:
            return "T"
        if node == manager.false:
            return "F"
        if getattr(node, "bdd", None) is not manager:
            raise ValueError("foreign CUDD node")
        if node in memo:
            return memo[node]
        identifier = len(memo) + 1
        memo[node] = identifier
        if getattr(node, "negated", False):
            level, low, high = manager.succ(~node)
            low, high = ~low, ~high
        else:
            level, low, high = manager.succ(node)
        graph[str(identifier)] = [int(level), visit(low), visit(high)]
        return identifier

    graph["roots"] = [visit(root)]
    if len(canonical_bytes(graph)) > 1 << 20:
        raise ValueError("CUDD graph evidence bound")
    return graph


def cudd_modes(k: int) -> tuple[str, ...]:
    if type(k) is not int or not 0 <= k <= 16:
        raise ValueError("bounded CUDD width")
    return ("fixed",) if k == 0 else ("fixed", "group_sift")


def probe_sat() -> dict[str, Any]:
    identity = extension_identity("python-sat", "pysolvers", "1.9.dev15")
    if identity.get("status") != "identified_not_executed" or identity.get("binding", {}).get("status") != "identified":
        raise RuntimeError("CaDiCaL extension identity")
    from pysat.solvers import Cadical195
    rows = [sat_contract(item["case"], item["sessions"], Cadical195) for item in probe_cases()]
    return {"status": "passed", "identity": identity, "adapter": "pysat.Cadical195",
            "cases": len(rows), "rows": rows, "native_execution": True,
            "performance_ranking_permitted": False}


def probe_cudd() -> dict[str, Any]:
    identity = extension_identity("dd", "dd.cudd", "0.6.0")
    zdd = extension_identity("dd", "dd.cudd_zdd", "0.6.0")
    if identity.get("status") != "identified_not_executed" or identity.get("binding", {}).get("status") != "identified":
        raise RuntimeError("native CUDD extension identity")
    from dd.cudd import BDD
    from scripts.cm_native_contracts import cudd_order_contract
    cases = [
        {"k": 0, "clauses": []},
        {"k": 0, "clauses": [[]]},
        {"k": 3, "clauses": [[1]]},
        {"k": 4, "clauses": [[1, -2], [2, 3], [-4]]},
    ]
    rows = []
    for case in cases:
        for mode in cudd_modes(case["k"]):
            row = cudd_order_contract(case, mode, BDD, export_cudd_graph)
            if independent_auditor().replay_bdd(row["graph"], case["k"]) != scalar_vector(case):
                raise RuntimeError("CUDD independent replay")
            rows.append({key: value for key, value in row.items() if key != "graph"} |
                        {"graph_sha256": hashlib.sha256(canonical_bytes(row["graph"])).hexdigest()})
    manager = BDD()
    manager.configure(reordering=False)
    manager.declare("x0", "x1", "x2")
    root = manager.var("x0") & (~manager.var("x1") | manager.var("x2"))
    original = export_cudd_graph(manager, root)
    with tempfile.TemporaryDirectory(prefix="cm-cudd-") as directory:
        path = Path(directory) / "graph.json"
        manager.dump(str(path), roots={"root": root})
        loaded_manager = BDD()
        loaded = loaded_manager.load(str(path))
        replayed = export_cudd_graph(loaded_manager, loaded["root"])
    if independent_auditor().replay_bdd(original, 3) != independent_auditor().replay_bdd(replayed, 3):
        raise RuntimeError("CUDD dump/reload mismatch")
    return {"status": "passed", "identity": identity, "zdd_identity": zdd, "cases": len(cases),
            "mode_rows": rows, "dump_reload_exact": True, "root_manager_identity": True,
            "native_execution": True, "autoref_substituted": False, "performance_ranking_permitted": False}


def native_worker(kind: str) -> int:
    result = probe_sat() if kind == "sat" else probe_cudd()
    # This is a readiness probe, never a timing result.  Keep the short-lived
    # native process observable across at least several 10-ms procfs samples
    # before and after result emission so whole-tree RSS can be established.
    result["measurement_fence_ms"] = 100
    time.sleep(0.05)
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    sys.stdout.buffer.flush()
    time.sleep(0.05)
    return 0


def run_native_worker(kind: str) -> dict[str, Any]:
    result = linux_supervisor.run(
        [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve()), "--native-worker", kind],
        cwd=ROOT,
        limits=linux_supervisor.Limits(timeout_seconds=30, rss_stop_bytes=1024 << 20,
                                       processes=4, stdout_bytes=1 << 20, stderr_bytes=64 << 10),
    )
    if result.status != "ok" or not result.resources.get("cleanup_verified"):
        raise RuntimeError(kind + " native worker failed: " + result.reason)
    value = json.loads(result.stdout)
    if value.get("status") != "passed" or value.get("native_execution") is not True:
        raise RuntimeError(kind + " native result")
    return {"worker": value, "supervision": result.resources, "wall_ns": result.wall_ns}


def linux_control_probes() -> dict[str, Any]:
    python = str(Path(sys.executable).resolve())
    base = linux_supervisor.Limits(timeout_seconds=5, rss_stop_bytes=256 << 20, processes=6,
                                   stdout_bytes=32 << 10, stderr_bytes=32 << 10)
    echo = linux_supervisor.run([python, "-B", "-c", "import json,os;print(json.dumps({'pid':os.getpid()}))"], limits=base)
    flood = linux_supervisor.run([python, "-B", "-c", "import os\nwhile True: os.write(1,b'x'*8192)"],
                                 limits=linux_supervisor.Limits(timeout_seconds=5, rss_stop_bytes=256 << 20,
                                                               processes=4, stdout_bytes=4096, stderr_bytes=4096))
    leaf = "import time;time.sleep(30)"
    child = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-B','-c',{leaf!r}]);time.sleep(30)"
    tree = linux_supervisor.run([python, "-B", "-c", child],
                                limits=linux_supervisor.Limits(timeout_seconds=0.25, rss_stop_bytes=256 << 20,
                                                              processes=6, stdout_bytes=4096, stderr_bytes=4096))
    memory = linux_supervisor.run([python, "-B", "-c", "import time;x=bytearray(80<<20);time.sleep(2)"],
                                  limits=linux_supervisor.Limits(timeout_seconds=5, rss_stop_bytes=32 << 20,
                                                                processes=4, stdout_bytes=4096, stderr_bytes=4096))
    expected = {"echo": "ok", "flood": "output_limit", "tree": "timeout", "memory": "memory_limit"}
    rows = {"echo": echo, "flood": flood, "tree": tree, "memory": memory}
    for name, result in rows.items():
        if result.status != expected[name] or not result.resources.get("cleanup_verified") or not result.resources.get("streams_closed"):
            raise RuntimeError("Linux control probe failed: " + name)
    return {name: {"status": row.status, "reason": row.reason, "resources": row.resources,
                   "wall_ns": row.wall_ns} for name, row in rows.items()}


def _cnf_bytes(case: dict[str, Any]) -> bytes:
    return (f"p cnf {case['k']} {len(case['clauses'])}\n" + "".join(
        " ".join(map(str, clause)) + (" " if clause else "") + "0\n" for clause in case["clauses"]
    )).encode("ascii")


NATIVE_FENCE_CODE = (
    "import subprocess,sys,time;"
    "r=subprocess.run(sys.argv[1:],stdin=subprocess.DEVNULL,"
    "stdout=sys.stdout.buffer,stderr=sys.stderr.buffer,check=False);"
    "time.sleep(0.1);raise SystemExit(r.returncode)"
)


def fenced_native_command(command: list[str]) -> list[str]:
    """Keep an untimed native child observable after it exits."""
    if not command or not all(isinstance(item, str) and "\0" not in item for item in command):
        raise ValueError("native fence command")
    if not Path(command[0]).is_absolute():
        raise ValueError("native fence executable must be absolute")
    return [str(Path(sys.executable).resolve()), "-B", "-c", NATIVE_FENCE_CODE, *command]


def elf_linkage_identity(path: Path) -> dict[str, Any]:
    """Classify a bounded ELF64 program-header table without executing it."""
    size = path.stat().st_size
    with path.open("rb") as handle:
        header = handle.read(64)
        if len(header) != 64 or header[:6] != b"\x7fELF\x02\x01":
            raise ValueError("Linux x86-64 ELF64 little-endian binary required")
        if struct.unpack_from("<H", header, 18)[0] != 62:
            raise ValueError("x86-64 ELF machine required")
        program_offset = struct.unpack_from("<Q", header, 32)[0]
        entry_size = struct.unpack_from("<H", header, 54)[0]
        entry_count = struct.unpack_from("<H", header, 56)[0]
        if not 1 <= entry_count <= 128 or not 56 <= entry_size <= 1024:
            raise ValueError("bounded ELF program-header table required")
        table_bytes = entry_size * entry_count
        if program_offset < 64 or program_offset + table_bytes > size:
            raise ValueError("ELF program-header table outside file")
        handle.seek(program_offset)
        table = handle.read(table_bytes)
    if len(table) != table_bytes:
        raise ValueError("truncated ELF program-header table")
    types = [struct.unpack_from("<I", table, index * entry_size)[0] for index in range(entry_count)]
    has_dynamic = 2 in types
    has_interpreter = 3 in types
    return {
        "status": "identified",
        "linkage": "dynamic" if has_dynamic or has_interpreter else "static",
        "program_headers": entry_count,
        "has_pt_dynamic": has_dynamic,
        "has_pt_interp": has_interpreter,
    }


def probe_d4(output: Path) -> dict[str, Any]:
    binary = (ROOT / D4).resolve()
    identity = file_identity(binary, expected_sha256=D4_SHA256)
    if identity.get("status") != "identified":
        raise RuntimeError("d4 identity")
    linkage = elf_linkage_identity(binary)
    binary.chmod(0o700)
    dependency_check: dict[str, Any]
    if linkage["linkage"] == "static":
        dependency_check = {"status": "not_applicable_static", "ldd_executed": False}
    else:
        ldd = Path("/usr/bin/ldd")
        if not ldd.is_file():
            raise RuntimeError("ldd unavailable")
        deps = linux_supervisor.run(fenced_native_command([str(ldd), str(binary)]), limits=linux_supervisor.Limits(timeout_seconds=10,
            rss_stop_bytes=256 << 20, processes=8, stdout_bytes=64 << 10, stderr_bytes=32 << 10))
        dependency_check = {
            "status": deps.status,
            "reason": deps.reason,
            "returncode": deps.returncode,
            "stdout_sha256": hashlib.sha256(deps.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(deps.stderr).hexdigest(),
            "missing_dependency_marker": b"not found" in deps.stdout or b"not found" in deps.stderr,
            "supervision": deps.resources,
            "ldd_executed": True,
        }
        write_new(output / "d4-linkage.json", {"elf": linkage, "dependency_check": dependency_check})
        if deps.status != "ok" or dependency_check["missing_dependency_marker"]:
            raise RuntimeError("d4 dynamic dependencies")
    if not (output / "d4-linkage.json").exists():
        write_new(output / "d4-linkage.json", {"elf": linkage, "dependency_check": dependency_check})
    help_result = linux_supervisor.run(fenced_native_command([str(binary), "--help"]), limits=linux_supervisor.Limits(timeout_seconds=10,
        rss_stop_bytes=512 << 20, processes=8, stdout_bytes=64 << 10, stderr_bytes=32 << 10))
    cases = [
        {"id": "true-k1", "k": 1, "clauses": []},
        {"id": "false-k1", "k": 1, "clauses": [[1], [-1]]},
        {"id": "all-k3", "k": 3, "clauses": []},
        {"id": "unused-k3", "k": 3, "clauses": [[1]]},
        {"id": "conflict-k2", "k": 2, "clauses": [[1], [-1]]},
    ]
    rows = []
    cnfs = output / "d4-cnfs"
    cnfs.mkdir()
    for case in cases:
        path = cnfs / (case["id"] + ".cnf")
        data = _cnf_bytes(case)
        path.write_bytes(data)
        command = d4_competition_count_command(binary, D4_SHA256, path.resolve(), hashlib.sha256(data).hexdigest(), case)
        result = linux_supervisor.run(fenced_native_command(command["command"]), limits=linux_supervisor.Limits(timeout_seconds=15,
            rss_stop_bytes=1024 << 20, processes=8, stdout_bytes=64 << 10, stderr_bytes=32 << 10))
        if result.status != "ok":
            write_new(output / "d4-case-failure.json", {
                "case": case["id"], "status": result.status, "reason": result.reason,
                "returncode": result.returncode, "stdout_bytes": len(result.stdout),
                "stderr_bytes": len(result.stderr),
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "stdout_excerpt": result.stdout[:4096].decode("utf-8", "replace"),
                "stderr_excerpt": result.stderr[:4096].decode("utf-8", "replace"),
                "supervision": result.resources,
            })
            raise RuntimeError("d4 known-count execution: " + case["id"])
        try:
            parsed = parse_d4_competition_count(result.stdout, case["k"])
        except (UnicodeDecodeError, ValueError) as exc:
            write_new(output / "d4-parse-failure.json", {
                "case": case["id"], "error_type": type(exc).__name__, "error": str(exc),
                "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "stdout_excerpt": result.stdout[:8192].decode("utf-8", "replace"),
                "stderr_excerpt": result.stderr[:4096].decode("utf-8", "replace"),
            })
            raise
        expected = scalar_vector(case).bit_count()
        if parsed["count"] != expected:
            raise RuntimeError("d4 known-count mismatch")
        rows.append({"case": case["id"], "expected": expected, "parsed": parsed,
                     "supervision": result.resources, "wall_ns": result.wall_ns})
    return {"status": "passed", "identity": identity, "elf": {"class": 64, "endian": "little", "machine": "x86_64",
            "linkage": linkage, "dependency_check": dependency_check},
            "native_child_measurement_fence_ms": 100,
            "help": {"status": help_result.status,
            "returncode": help_result.returncode, "stdout_sha256": hashlib.sha256(help_result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(help_result.stderr).hexdigest()}, "cases": rows,
            "native_execution": True, "performance_ranking_permitted": False}


def perf_probe() -> dict[str, Any]:
    path = shutil.which("perf")
    if not path:
        return {"status": "unavailable", "reason": "perf_not_installed"}
    true_path = shutil.which("true")
    if not true_path:
        return {"status": "unavailable", "reason": "true_not_installed"}
    result = linux_supervisor.run([str(Path(path).resolve()), "stat", "-e", "cycles", "--", str(Path(true_path).resolve())],
        limits=linux_supervisor.Limits(timeout_seconds=10, rss_stop_bytes=256 << 20,
                                      processes=8, stdout_bytes=32 << 10, stderr_bytes=32 << 10))
    return {"status": "available" if result.status == "ok" else "refused", "supervisor_status": result.status,
            "returncode": result.returncode, "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(), "performance_ranking_permitted": False}


def run(output: Path, lock_path: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists() or not output.parent.exists() or not output.parent.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("new project-local output required")
    output.mkdir()
    started = time.monotonic()
    summary: dict[str, Any] = {"schema": SCHEMA, "status": "failed", "performance_measurement": False,
                               "performance_ranking_permitted": False}
    try:
        if not sys.platform.startswith("linux") or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("Linux x86-64 required")
        readiness = environment_record(d4_path=(ROOT / D4), d4_sha256=D4_SHA256)
        validate_allocation(readiness, expected_affinity_cpus=2)
        write_new(output / "environment.json", readiness)
        dependency = install_dependencies(output, lock_path)
        write_new(output / "dependencies.json", dependency)
        controls = linux_control_probes()
        write_new(output / "linux-controls.json", controls)
        sat = run_native_worker("sat")
        write_new(output / "cadical.json", sat)
        cudd = run_native_worker("cudd")
        write_new(output / "cudd.json", cudd)
        d4 = probe_d4(output)
        write_new(output / "d4.json", d4)
        perf = perf_probe()
        write_new(output / "perf.json", perf)
        summary.update(status="passed", dependencies="passed", linux_controls="passed",
                       cadical="passed", cudd="passed", d4="passed", perf=perf["status"],
                       zdd="identified_only_not_task_executed", elapsed_s=time.monotonic() - started,
                       native_failures=0, semantic_mismatches=0,
                       claims=["native and Linux readiness only", "no comparative timing"])
    except Exception as exc:
        summary.update(error_type=type(exc).__name__, error=str(exc) if type(exc) in {RuntimeError, ValueError} else None,
                       elapsed_s=time.monotonic() - started)
    write_new(output / "summary.json", summary)
    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "checksums.json"):
        files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_new(output / "checksums.json", {"schema": "cm-comparative-native-scout-checksums/v1", "files": files})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dependency-lock", type=Path, default=LOCK)
    parser.add_argument("--native-worker", choices=("sat", "cudd"))
    args = parser.parse_args()
    if args.native_worker:
        return native_worker(args.native_worker)
    if args.output_dir is None:
        parser.error("--output-dir is required")
    result = run(args.output_dir, args.dependency_lock)
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
