"""Fail-closed CryptoMiniSat adapter with explicit XOR semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


STATUS = re.compile(r"^s (SATISFIABLE|UNSATISFIABLE)$", re.MULTILINE)


@dataclass(frozen=True)
class XorCNF:
    variables: int
    clauses: tuple[tuple[int, ...], ...]
    xor_clauses: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class NativeSatResult:
    status: str
    assignment: tuple[bool, ...] | None
    command: tuple[str, ...]
    stdout: str
    stderr: str


def parse_xor_dimacs(text: str, *, max_bytes: int = 16 << 20,
                     max_variables: int = 2_000_000,
                     max_clauses: int = 4_000_000) -> XorCNF:
    if not isinstance(text, str) or not 0 < len(text.encode("utf-8")) <= max_bytes:
        raise ValueError("DIMACS outside byte limit")
    header: tuple[int, int] | None = None
    clauses: list[tuple[int, ...]] = []
    xor_clauses: list[tuple[int, ...]] = []
    for raw in text.splitlines():
        fields = raw.split()
        if not fields or fields[0] == "c":
            continue
        if fields[0] == "p":
            if header is not None or len(fields) != 4 or fields[1] != "cnf":
                raise ValueError("invalid DIMACS header")
            variables, expected = int(fields[2]), int(fields[3])
            if not 0 <= variables <= max_variables or not 0 <= expected <= max_clauses:
                raise ValueError("DIMACS dimensions exceed limits")
            header = variables, expected
            continue
        if header is None:
            raise ValueError("DIMACS clause precedes header")
        is_xor = fields[0] == "x"
        values = fields[1:] if is_xor else fields
        if not values or values[-1] != "0" or "0" in values[:-1]:
            raise ValueError("unterminated or split DIMACS clause")
        literals = tuple(int(value) for value in values[:-1])
        if any(literal == 0 or abs(literal) > header[0] for literal in literals):
            raise ValueError("DIMACS literal outside variable range")
        (xor_clauses if is_xor else clauses).append(literals)
    if header is None or len(clauses) + len(xor_clauses) != header[1]:
        raise ValueError("incomplete DIMACS")
    return XorCNF(header[0], tuple(clauses), tuple(xor_clauses))


def _satisfies(instance: XorCNF, assignment: tuple[bool, ...]) -> bool:
    ordinary = all(any(assignment[abs(literal) - 1] == (literal > 0)
                       for literal in clause) for clause in instance.clauses)
    parity = all(sum(assignment[abs(literal) - 1] == (literal > 0)
                     for literal in clause) % 2 == 1 for clause in instance.xor_clauses)
    return ordinary and parity


def run_cryptominisat(path: str | Path, *, executable: str | Path = "cryptominisat5",
                      timeout_seconds: float = 60.0, threads: int = 1,
                      max_output_bytes: int = 1 << 20) -> NativeSatResult:
    source = Path(path).resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError("native SAT input missing or linked")
    instance = parse_xor_dimacs(source.read_text(encoding="utf-8"))
    if not isinstance(threads, int) or not 1 <= threads <= 256:
        raise ValueError("invalid CryptoMiniSat thread count")
    if not 0 < timeout_seconds <= 900:
        raise ValueError("invalid CryptoMiniSat timeout")
    command = (str(executable), "--verb", "0", "--threads", str(threads), str(source))
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("CryptoMiniSat deadline exceeded") from exc
    output_bytes = len(completed.stdout.encode("utf-8")) + len(completed.stderr.encode("utf-8"))
    if output_bytes > max_output_bytes:
        raise ValueError("CryptoMiniSat diagnostic output exceeds limit")
    statuses = STATUS.findall(completed.stdout)
    if len(statuses) != 1:
        raise ValueError("CryptoMiniSat output lacks one status")
    status = statuses[0]
    expected_exit = 10 if status == "SATISFIABLE" else 20
    if completed.returncode != expected_exit:
        raise RuntimeError("CryptoMiniSat status/exit mismatch")
    assignment = None
    if status == "SATISFIABLE":
        values: dict[int, bool] = {}
        for line in completed.stdout.splitlines():
            if not line.startswith("v "):
                continue
            for token in line[2:].split():
                literal = int(token)
                if literal:
                    values[abs(literal)] = literal > 0
        if set(values) != set(range(1, instance.variables + 1)):
            raise ValueError("CryptoMiniSat witness is incomplete")
        assignment = tuple(values[index] for index in range(1, instance.variables + 1))
        if not _satisfies(instance, assignment):
            raise ValueError("CryptoMiniSat witness does not satisfy input")
    return NativeSatResult(status, assignment, command, completed.stdout, completed.stderr)
