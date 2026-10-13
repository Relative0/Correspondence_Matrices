"""Fail-closed subprocess adapters for pinned native exact counters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from cmbench.backends.projected_count import parse_counting_dimacs
from cmbench.backends.solver_process import (
    DEFAULT_SOLVER_MEMORY_BYTES, read_solver_input, run_solver, validate_solver_limits)


EXACT_COUNT = re.compile(r"^c s exact arb int ([0-9]+)$", re.MULTILINE)
STATUS = re.compile(r"^s (SATISFIABLE|UNSATISFIABLE)$", re.MULTILINE)
D4_COUNT = re.compile(r"^s ([0-9]+)$", re.MULTILINE)
D4_CACHE_FIRST_PAGE_BYTES = 256 << 20
D4_CACHE_ADDITIONAL_PAGE_BYTES = 64 << 20
DEFAULT_MAX_COUNT_DIGITS = 65_536
_DECIMAL_CHUNK_DIGITS = 9
_DECIMAL_CHUNK_BASE = 10 ** _DECIMAL_CHUNK_DIGITS


@dataclass(frozen=True)
class NativeCountResult:
    count: int
    status: str
    mode: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    resources: dict = field(default_factory=dict)


def parse_bounded_decimal_count(decimal_text: str, *, max_digits: int,
                                maximum_exponent: int) -> int:
    """Parse one canonical nonnegative decimal count without changing int limits.

    Native counters can legitimately emit more decimal digits than CPython's
    process-wide string-to-int guard permits.  This bounded base-10**9 parser
    keeps that guard intact while making the adapter's separate admission
    policy explicit.
    """
    if (type(max_digits) is not int or not 1 <= max_digits <= 1 << 20
            or type(maximum_exponent) is not int or not 0 <= maximum_exponent <= 2_000_000):
        raise ValueError("invalid exact count admission bounds")
    if (not isinstance(decimal_text, str) or not decimal_text
            or len(decimal_text) > max_digits
            or not decimal_text.isascii() or not decimal_text.isdecimal()
            or (len(decimal_text) > 1 and decimal_text[0] == "0")):
        raise ValueError("invalid or oversized exact decimal count")
    value = 0
    first = len(decimal_text) % _DECIMAL_CHUNK_DIGITS or _DECIMAL_CHUNK_DIGITS
    for start, width in ((0, first), *(
            (index, _DECIMAL_CHUNK_DIGITS)
            for index in range(first, len(decimal_text), _DECIMAL_CHUNK_DIGITS))):
        # At most nine ASCII digits are passed to int(), safely below its
        # configured decimal conversion guard on every supported runtime.
        value = value * (_DECIMAL_CHUNK_BASE if start else 1) + int(decimal_text[start:start + width])
    if value > (1 << maximum_exponent):
        raise ValueError("native count exceeds mathematical maximum")
    return value


def validate_count_admission(max_count_digits: int, max_output_bytes: int) -> None:
    # Stream capture independently bounds the actual accepted line.  A caller
    # may intentionally choose a smaller diagnostic-output budget than this
    # adapter's wider count policy; that must fail at capture, not by silently
    # changing the parser's configured admission boundary.
    if type(max_count_digits) is not int or not 1 <= max_count_digits <= 1 << 20:
        raise ValueError("invalid exact count digit limit")


def run_ganak(path: str | Path, *, mode: str, executable: str | Path = "ganak",
              timeout_seconds: float = 60.0, threads: int = 1,
              max_output_bytes: int = 1 << 20,
              max_memory_bytes: int = DEFAULT_SOLVER_MEMORY_BYTES,
              max_count_digits: int = DEFAULT_MAX_COUNT_DIGITS) -> NativeCountResult:
    """Run Ganak in deterministic exact mode, with approximation disabled.

    ``mode`` declares how ``c ind``/``c p show`` must be interpreted by the
    campaign. Exact-track independent supports preserve total model count;
    projected-track directives define the visible variables.
    """
    validate_solver_limits(timeout_seconds, max_output_bytes, max_memory_bytes)
    validate_count_admission(max_count_digits, max_output_bytes)
    source, text = read_solver_input(path)
    instance = parse_counting_dimacs(text, mode=mode)
    if mode == "projected" and not instance.declared_support:
        raise ValueError("projected Ganak input lacks declared visible variables")
    if type(threads) is not int or not 1 <= threads <= 256:
        raise ValueError("invalid Ganak thread count")
    command = (
        str(executable), "--verb", "0", "--prob", "0", "--appmct", "-1",
        "--threads", str(threads), str(source),
    )
    completed = run_solver(command, timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes, max_memory_bytes=max_memory_bytes)
    if completed.returncode != 0:
        raise RuntimeError(f"Ganak exited with code {completed.returncode}")
    counts = EXACT_COUNT.findall(completed.stdout)
    statuses = STATUS.findall(completed.stdout)
    if len(counts) != 1 or len(statuses) != 1:
        raise ValueError("Ganak output lacks one exact count and status")
    count = parse_bounded_decimal_count(counts[0], max_digits=max_count_digits,
                                       maximum_exponent=len(instance.projection))
    status = statuses[0]
    if (status == "UNSATISFIABLE") != (count == 0):
        raise ValueError("Ganak status/count mismatch")
    return NativeCountResult(count, status, mode, command, completed.stdout, completed.stderr, completed.resources)


def run_d4(path: str | Path, *, executable: str | Path = "d4-counter",
           timeout_seconds: float = 60.0, max_output_bytes: int = 1 << 20,
           max_memory_bytes: int = DEFAULT_SOLVER_MEMORY_BYTES,
           cache_first_page_bytes: int = D4_CACHE_FIRST_PAGE_BYTES,
           cache_additional_page_bytes: int = D4_CACHE_ADDITIONAL_PAGE_BYTES,
           max_count_digits: int = DEFAULT_MAX_COUNT_DIGITS) -> NativeCountResult:
    """Run d4v2 with bounded cache pages and accept one integer result.

    d4v2 defaults its first cache page to 4 GiB.  Pinning smaller pages avoids
    an immediate allocation failure when the caller enforces a 4 GiB address
    space limit; later allocations remain governed by that external limit.
    """
    validate_solver_limits(timeout_seconds, max_output_bytes, max_memory_bytes)
    validate_count_admission(max_count_digits, max_output_bytes)
    source, text = read_solver_input(path)
    instance = parse_counting_dimacs(text, mode="exact")
    if instance.declared_support:
        raise ValueError("d4 exact adapter does not accept support/projection directives")
    if (type(cache_first_page_bytes) is not int or type(cache_additional_page_bytes) is not int
            or not 1 << 20 <= cache_first_page_bytes <= 1 << 30
            or not 1 << 20 <= cache_additional_page_bytes <= cache_first_page_bytes):
        raise ValueError("invalid d4 cache page bounds")
    command = (
        str(executable), "-i", str(source),
        "--cache-size-first-page", str(cache_first_page_bytes),
        "--cache-size-additional-page", str(cache_additional_page_bytes),
    )
    completed = run_solver(command, timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes, max_memory_bytes=max_memory_bytes)
    if completed.returncode != 0:
        raise RuntimeError(f"d4 exited with code {completed.returncode}")
    counts = D4_COUNT.findall(completed.stdout)
    if len(counts) != 1:
        raise ValueError("d4 output lacks one integer exact count")
    count = parse_bounded_decimal_count(counts[0], max_digits=max_count_digits,
                                       maximum_exponent=instance.variables)
    status = "UNSATISFIABLE" if count == 0 else "SATISFIABLE"
    return NativeCountResult(count, status, "exact", command, completed.stdout, completed.stderr, completed.resources)
