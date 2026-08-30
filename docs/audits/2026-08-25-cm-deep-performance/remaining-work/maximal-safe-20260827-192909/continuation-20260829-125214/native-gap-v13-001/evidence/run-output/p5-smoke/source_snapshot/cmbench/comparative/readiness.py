"""Read-only Linux/allocation and native-adapter readiness records.

The functions in this module do not launch binaries, install packages, or
make network requests.  They separate host CPU visibility from the affinity
actually available to the benchmark process and retain missing cgroup fields
as evidence rather than guessing a quota.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any, Mapping


READINESS_SCHEMA = "cm-comparative-readiness/v1"
MAX_NATIVE_BYTES = 64 << 20
SHA256 = re.compile(r"[0-9a-f]{64}")


def parse_cpu_list(value: str) -> tuple[int, ...]:
    """Parse the Linux cpulist grammar used by procfs and cgroup v2."""
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("invalid CPU list")
    text = value.strip()
    if not text:
        return ()
    cpus: list[int] = []
    for item in text.split(","):
        if re.fullmatch(r"[0-9]+", item):
            first = last = int(item)
        else:
            match = re.fullmatch(r"([0-9]+)-([0-9]+)", item)
            if match is None:
                raise ValueError("invalid CPU list segment")
            first, last = map(int, match.groups())
            if last < first:
                raise ValueError("descending CPU range")
        if last > 1_000_000 or last - first > 1_000_000:
            raise ValueError("CPU list bound")
        cpus.extend(range(first, last + 1))
    if len(cpus) != len(set(cpus)) or cpus != sorted(cpus):
        raise ValueError("CPU list must be sorted and unique")
    return tuple(cpus)


def parse_cpu_max(value: str) -> dict[str, int | None]:
    fields = value.strip().split()
    if len(fields) != 2 or (fields[0] != "max" and not fields[0].isdigit()) or not fields[1].isdigit():
        raise ValueError("invalid cgroup cpu.max")
    quota = None if fields[0] == "max" else int(fields[0])
    period = int(fields[1])
    if period <= 0 or (quota is not None and quota <= 0):
        raise ValueError("invalid cgroup CPU quota")
    return {"quota_us": quota, "period_us": period}


def parse_limit(value: str) -> int | None:
    text = value.strip()
    if text == "max":
        return None
    if not re.fullmatch(r"[0-9]+", text):
        raise ValueError("invalid cgroup limit")
    return int(text)


def parse_key_values(value: str) -> dict[str, int]:
    output: dict[str, int] = {}
    for line in value.splitlines():
        fields = line.split()
        if len(fields) != 2 or not re.fullmatch(r"[A-Za-z0-9_.-]+", fields[0]) or not fields[1].isdigit():
            raise ValueError("invalid cgroup key/value record")
        if fields[0] in output:
            raise ValueError("duplicate cgroup key")
        output[fields[0]] = int(fields[1])
    return output


def cgroup_v2_relative(value: str) -> str:
    rows = [line for line in value.splitlines() if line]
    matches = [line.split(":", 2)[2] for line in rows if line.startswith("0::") and line.count(":") == 2]
    if len(matches) != 1 or not matches[0].startswith("/") or "\x00" in matches[0]:
        raise ValueError("unrecognized cgroup v2 membership")
    parts = Path(matches[0]).parts
    if ".." in parts:
        raise ValueError("cgroup traversal")
    return matches[0].lstrip("/")


def _bounded_text(path: Path, maximum: int = 64 << 10) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > maximum:
            return None
        return path.read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return None


def read_cgroup_v2(*, proc_root: Path = Path("/proc"), cgroup_root: Path = Path("/sys/fs/cgroup")) -> dict[str, Any]:
    membership = _bounded_text(proc_root / "self" / "cgroup")
    if membership is None:
        return {"version": None, "reason": "membership_unavailable"}
    try:
        relative = cgroup_v2_relative(membership)
    except ValueError:
        return {"version": None, "reason": "not_unified_v2"}
    base = cgroup_root.joinpath(*Path(relative).parts)
    try:
        if not base.resolve().is_relative_to(cgroup_root.resolve()):
            return {"version": None, "reason": "cgroup_path_escape"}
    except OSError:
        return {"version": None, "reason": "cgroup_path_unavailable"}

    raw = {name: _bounded_text(base / name) for name in (
        "cpu.max", "cpuset.cpus.effective", "memory.max", "memory.current",
        "memory.peak", "pids.max", "pids.current", "cgroup.events", "cpu.stat",
    )}
    record: dict[str, Any] = {"version": 2, "relative_path": "/" + relative, "fields": {}}
    parsers = {
        "cpu.max": parse_cpu_max,
        "cpuset.cpus.effective": lambda item: list(parse_cpu_list(item)),
        "memory.max": parse_limit,
        "memory.current": parse_limit,
        "memory.peak": parse_limit,
        "pids.max": parse_limit,
        "pids.current": parse_limit,
        "cgroup.events": parse_key_values,
        "cpu.stat": parse_key_values,
    }
    for name, text in raw.items():
        if text is None:
            record["fields"][name] = {"status": "unavailable", "value": None}
            continue
        try:
            value = parsers[name](text)
        except ValueError:
            record["fields"][name] = {"status": "malformed", "value": None}
        else:
            record["fields"][name] = {"status": "observed", "value": value}
    return record


def file_identity(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    path = Path(path)
    if expected_sha256 is not None and (not isinstance(expected_sha256, str) or SHA256.fullmatch(expected_sha256) is None):
        raise ValueError("invalid expected SHA-256")
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_NATIVE_BYTES:
        return {"status": "unavailable", "reason": "missing_linked_or_oversized"}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    actual = digest.hexdigest()
    record = {"status": "identified", "file": path.name, "bytes": path.stat().st_size, "sha256": actual}
    if expected_sha256 is not None and actual != expected_sha256:
        record.update(status="refused", reason="hash_mismatch")
    return record


def extension_identity(distribution: str, module: str, required_version: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "distribution": distribution,
        "module": module,
        "required_version": required_version,
        "status": "unavailable",
        "fallback_used": False,
    }
    try:
        installed = importlib.metadata.version(distribution)
        spec = importlib.util.find_spec(module)
        record["installed_version"] = installed
        if spec is None or not spec.origin:
            record["reason"] = "module_missing"
        elif not any(spec.origin.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES):
            record["reason"] = "not_compiled_extension"
        elif installed != required_version:
            record["reason"] = "version_mismatch"
        else:
            record.update(status="identified_not_executed", binding=file_identity(Path(spec.origin)))
    except (importlib.metadata.PackageNotFoundError, ImportError, OSError, ValueError):
        record["reason"] = "identity_unavailable"
    return record


def environment_record(
    *,
    proc_root: Path = Path("/proc"),
    cgroup_root: Path = Path("/sys/fs/cgroup"),
    d4_path: Path | None = None,
    d4_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        affinity = tuple(sorted(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        affinity = ()
    cgroup = read_cgroup_v2(proc_root=proc_root, cgroup_root=cgroup_root) if sys.platform.startswith("linux") else {
        "version": None, "reason": "not_linux"
    }
    return {
        "schema": READINESS_SCHEMA,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "python": {"version": platform.python_version(), "implementation": platform.python_implementation()},
        "cpu": {
            "host_logical_visible": os.cpu_count(),
            "affinity": list(affinity),
            "allocated_logical_from_affinity": len(affinity) if affinity else None,
            "allocation_claim_source": "sched_getaffinity" if affinity else "unavailable",
        },
        "cgroup": cgroup,
        "native": {
            "cadical": extension_identity("python-sat", "pysolvers", "1.8.dev20"),
            "cudd": extension_identity("dd", "dd.cudd", "0.6.0"),
            "zdd": extension_identity("dd", "dd.cudd_zdd", "0.6.0"),
            "d4": ({"status": "unconfigured", "reason": "no_path"} if d4_path is None else
                   file_identity(d4_path, expected_sha256=d4_sha256)),
        },
        "native_execution_performed": False,
        "performance_ranking_permitted": False,
    }


def validate_allocation(record: Mapping[str, Any], *, expected_affinity_cpus: int) -> None:
    if type(expected_affinity_cpus) is not int or expected_affinity_cpus <= 0:
        raise ValueError("invalid expected CPU allocation")
    if record.get("schema") != READINESS_SCHEMA:
        raise ValueError("readiness schema")
    cpu = record.get("cpu")
    if not isinstance(cpu, Mapping) or cpu.get("allocation_claim_source") != "sched_getaffinity":
        raise ValueError("CPU affinity unavailable")
    affinity = cpu.get("affinity")
    if not isinstance(affinity, list) or len(affinity) != expected_affinity_cpus or len(set(affinity)) != len(affinity):
        raise ValueError("CPU affinity does not match allocation")
    if cpu.get("allocated_logical_from_affinity") != expected_affinity_cpus:
        raise ValueError("allocated CPU accounting mismatch")
