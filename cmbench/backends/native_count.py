"""Fail-closed subprocess adapters for pinned native exact counters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from cmbench.backends.projected_count import parse_counting_dimacs


EXACT_COUNT = re.compile(r"^c s exact arb int ([0-9]+)$", re.MULTILINE)
STATUS = re.compile(r"^s (SATISFIABLE|UNSATISFIABLE)$", re.MULTILINE)
D4_COUNT = re.compile(r"^s ([0-9]+)$", re.MULTILINE)
D4_CACHE_FIRST_PAGE_BYTES = 256 << 20
D4_CACHE_ADDITIONAL_PAGE_BYTES = 64 << 20


@dataclass(frozen=True)
class NativeCountResult:
    count: int
    status: str
    mode: str
    command: tuple[str, ...]
    stdout: str
    stderr: str


def run_ganak(path: str | Path, *, mode: str, executable: str | Path = "ganak",
              timeout_seconds: float = 60.0, threads: int = 1,
              max_output_bytes: int = 1 << 20) -> NativeCountResult:
    """Run Ganak in deterministic exact mode, with approximation disabled.

    ``mode`` declares how ``c ind``/``c p show`` must be interpreted by the
    campaign. Exact-track independent supports preserve total model count;
    projected-track directives define the visible variables.
    """
    source = Path(path).resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError("native-count input missing or linked")
    instance = parse_counting_dimacs(source.read_text(encoding="utf-8"), mode=mode)
    if mode == "projected" and not instance.declared_support:
        raise ValueError("projected Ganak input lacks declared visible variables")
    if not isinstance(threads, int) or not 1 <= threads <= 256:
        raise ValueError("invalid Ganak thread count")
    if not 0 < timeout_seconds <= 900:
        raise ValueError("invalid Ganak timeout")
    command = (
        str(executable), "--verb", "0", "--prob", "0", "--appmct", "-1",
        "--threads", str(threads), str(source),
    )
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("Ganak exact-count deadline exceeded") from exc
    output_bytes = len(completed.stdout.encode("utf-8")) + len(completed.stderr.encode("utf-8"))
    if output_bytes > max_output_bytes:
        raise ValueError("Ganak diagnostic output exceeds limit")
    if completed.returncode != 0:
        raise RuntimeError(f"Ganak exited with code {completed.returncode}")
    counts = EXACT_COUNT.findall(completed.stdout)
    statuses = STATUS.findall(completed.stdout)
    if len(counts) != 1 or len(statuses) != 1:
        raise ValueError("Ganak output lacks one exact count and status")
    count = int(counts[0])
    status = statuses[0]
    if (status == "UNSATISFIABLE") != (count == 0):
        raise ValueError("Ganak status/count mismatch")
    return NativeCountResult(count, status, mode, command, completed.stdout, completed.stderr)


def run_d4(path: str | Path, *, executable: str | Path = "d4-counter",
           timeout_seconds: float = 60.0, max_output_bytes: int = 1 << 20,
           cache_first_page_bytes: int = D4_CACHE_FIRST_PAGE_BYTES,
           cache_additional_page_bytes: int = D4_CACHE_ADDITIONAL_PAGE_BYTES) -> NativeCountResult:
    """Run d4v2 with bounded cache pages and accept one integer result.

    d4v2 defaults its first cache page to 4 GiB.  Pinning smaller pages avoids
    an immediate allocation failure when the caller enforces a 4 GiB address
    space limit; later allocations remain governed by that external limit.
    """
    source = Path(path).resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError("native-count input missing or linked")
    instance = parse_counting_dimacs(source.read_text(encoding="utf-8"), mode="exact")
    if instance.declared_support:
        raise ValueError("d4 exact adapter does not accept support/projection directives")
    if not 0 < timeout_seconds <= 900:
        raise ValueError("invalid d4 timeout")
    if (type(cache_first_page_bytes) is not int or type(cache_additional_page_bytes) is not int
            or not 1 << 20 <= cache_first_page_bytes <= 1 << 30
            or not 1 << 20 <= cache_additional_page_bytes <= cache_first_page_bytes):
        raise ValueError("invalid d4 cache page bounds")
    command = (
        str(executable), "-i", str(source),
        "--cache-size-first-page", str(cache_first_page_bytes),
        "--cache-size-additional-page", str(cache_additional_page_bytes),
    )
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("d4 exact-count deadline exceeded") from exc
    output_bytes = len(completed.stdout.encode("utf-8")) + len(completed.stderr.encode("utf-8"))
    if output_bytes > max_output_bytes:
        raise ValueError("d4 diagnostic output exceeds limit")
    if completed.returncode != 0:
        raise RuntimeError(f"d4 exited with code {completed.returncode}")
    counts = D4_COUNT.findall(completed.stdout)
    if len(counts) != 1:
        raise ValueError("d4 output lacks one integer exact count")
    count = int(counts[0])
    status = "UNSATISFIABLE" if count == 0 else "SATISFIABLE"
    return NativeCountResult(count, status, "exact", command, completed.stdout, completed.stderr)
