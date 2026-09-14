"""Strict successor contracts; frozen campaign adapters remain unchanged."""
from __future__ import annotations

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from cmbench.backends.native_count import run_d4, run_ganak, EXACT_COUNT, STATUS, NativeCountResult
from cmbench.backends.native_sat import run_cryptominisat, parse_xor_dimacs
from cmbench.backends.projected_count import ProjectedCNF, parse_counting_dimacs


def read_regular_source(path):
    source = Path(path).absolute()
    if any(p.is_symlink() for p in (source, *source.parents)) or not source.is_file():
        raise ValueError("input missing or linked")
    return source.read_text(encoding="utf-8")


def parse_counting_v2(text, *, mode):
    """c ind is a support hint; c p show is projection. Never conflate them.

    Projected mode requires explicit c p show (including an empty set).
    Historical c ind-as-projection requires an explicit caller conversion.
    Exact mode ignores support hints and rejects a projection directive.
    """
    if not isinstance(text, str) or not 0 < len(text.encode("utf-8")) <= 16 << 20:
        raise ValueError("DIMACS outside byte limit")
    clean, declarations = [], {"ind": [], "show": []}
    present = set()
    for line in text.splitlines():
        fields = line.split()
        if fields[:3] in (["c", "p", "weight"], ["c", "p", "weights"]):
            raise ValueError("weighted counting is not this exact unweighted contract")
        kind = None
        if fields[:2] == ["c", "ind"]:
            kind, values = "ind", fields[2:]
        elif fields[:3] == ["c", "p", "show"]:
            kind, values = "show", fields[3:]
        if kind:
            present.add(kind)
            if not values or values[-1] != "0":
                raise ValueError("unterminated support/projection")
            declarations[kind].extend(int(v) for v in values[:-1])
        else:
            clean.append(line)
    base = parse_counting_dimacs("\n".join(clean), mode="exact")
    for values in declarations.values():
        if len(values) != len(set(values)) or any(v < 1 or v > base.variables for v in values):
            raise ValueError("invalid support/projection variables")
    if mode not in {"exact", "projected"}:
        raise ValueError("invalid counting mode")
    if mode == "exact" and "show" in present:
        raise ValueError("projection directive conflicts with exact mode")
    if mode == "projected" and "show" not in present:
        raise ValueError("projected mode requires explicit c p show")
    projection = tuple(declarations["show"]) if mode == "projected" else base.projection
    return ProjectedCNF(base.variables, base.clauses, projection, mode, tuple(declarations["ind"]))


def run_exact_counter_v2(path, *, backend, executable, timeout_seconds=60):
    """Normalize exact CNF, stripping untrusted independent-support hints.

    The caller pins the executable hash. Projected native counting is not
    admitted here until its solver-specific contract is independently verified.
    """
    if backend not in {"d4", "ganak"}:
        raise ValueError("unsupported exact backend")
    instance = parse_counting_v2(read_regular_source(path), mode="exact")
    text = f"p cnf {instance.variables} {len(instance.clauses)}\n" + "".join(
        " ".join(map(str, c)) + " 0\n" for c in instance.clauses)
    with TemporaryDirectory(prefix="cm-exact-v2-") as folder:
        normalized = Path(folder) / "normalized.cnf"
        normalized.write_text(text, encoding="utf-8")
        kwargs = dict(executable=executable, timeout_seconds=timeout_seconds)
        result = (run_d4(normalized, **kwargs) if backend == "d4" else
                  run_ganak(normalized, mode="exact", **kwargs))
    if result.count > 1 << instance.variables:
        raise ValueError("count exceeds declared universe")
    return result


def projected_count_v2(instance, *, max_projection=20, max_solutions=1 << 20):
    """Explicitly register free visible axes; handle empty clauses before PySAT.

    python-sat 1.8.dev20's Cadical195 bootstrap indexes empty clauses; logical
    UNSAT is handled here without substituting a different solver.
    """
    from pysat.solvers import Cadical195
    if (type(instance.variables) is not int or instance.variables < 0 or
            len(set(instance.projection)) != len(instance.projection) or
            any(type(v) is not int or not 1 <= v <= instance.variables for v in instance.projection) or
            any(type(v) is not int or not 1 <= abs(v) <= instance.variables for c in instance.clauses for v in c)):
        raise ValueError("invalid projected CNF")
    if len(instance.projection) > max_projection or type(max_solutions) is not int or max_solutions < 1:
        raise ValueError("invalid local enumeration bounds")
    if any(not clause for clause in instance.clauses):
        return 0
    count = 0
    with Cadical195(bootstrap_with=instance.clauses) as solver:
        for variable in instance.projection:
            solver.add_clause([variable, -variable])
        while solver.solve():
            count += 1
            if count > max_solutions:
                raise ValueError("solution enumeration limit exceeded")
            if not instance.projection:
                return 1
            model = {abs(v): v > 0 for v in solver.get_model()}
            solver.add_clause([-v if model[v] else v for v in instance.projection])
    return count


def run_projected_ganak_v2(path, *, executable, timeout_seconds=60, max_output_bytes=1 << 20):
    """Pinned Ganak c p show semantics, including empty visible sets.

    Normalize away all support hints, which cannot accompany c p show in the
    verified Ganak binary. No oracle or alternative solver is substituted.
    """
    if not 0 < timeout_seconds <= 900:
        raise ValueError("invalid Ganak timeout")
    instance = parse_counting_v2(read_regular_source(path), mode="projected")
    text = "c p show " + " ".join(map(str, instance.projection)) + " 0\n"
    text += f"p cnf {instance.variables} {len(instance.clauses)}\n" + "".join(
        " ".join(map(str, c)) + " 0\n" for c in instance.clauses)
    with TemporaryDirectory(prefix="cm-projected-v2-") as folder:
        normalized = Path(folder) / "projected.cnf"
        normalized.write_text(text, encoding="utf-8")
        command = (str(executable), "--verb", "0", "--prob", "0", "--appmct", "-1", "--threads", "1", str(normalized))
        try:
            process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", check=False, timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Ganak projected-count deadline exceeded") from exc
    if len(process.stdout.encode()) + len(process.stderr.encode()) > max_output_bytes:
        raise ValueError("Ganak diagnostic output exceeds limit")
    if process.returncode != 0:
        raise RuntimeError(f"Ganak exited with code {process.returncode}")
    counts, statuses = EXACT_COUNT.findall(process.stdout), STATUS.findall(process.stdout)
    if len(counts) != 1 or len(statuses) != 1:
        raise ValueError("Ganak output lacks one exact count and status")
    count, status = int(counts[0]), statuses[0]
    if count > 1 << len(instance.projection) or (status == "UNSATISFIABLE") != (count == 0):
        raise ValueError("Ganak projected universe/status mismatch")
    return NativeCountResult(count, status, "projected", command, process.stdout, process.stderr)


def run_sat_v2(path, *, executable, timeout_seconds=60):
    text = read_regular_source(path)
    instance = parse_xor_dimacs(text)
    # Freeze the checked bytes so a changed source cannot reach the solver.
    with TemporaryDirectory(prefix="cm-sat-v2-") as folder:
        normalized = Path(folder) / "input.cnf"
        normalized.write_text(text, encoding="utf-8")
        result = run_cryptominisat(normalized, executable=executable, timeout_seconds=timeout_seconds)
    seen, terminated, has_witness = {}, False, False
    for line in result.stdout.splitlines():
        if not line.startswith("v "):
            continue
        has_witness = True
        for token in line[2:].split():
            literal = int(token)
            if terminated:
                raise ValueError("witness tokens after final terminator")
            if not literal:
                terminated = True
                continue
            if abs(literal) > instance.variables or (abs(literal) in seen and seen[abs(literal)] != (literal > 0)):
                raise ValueError("contradictory or out-of-range witness literal")
            seen[abs(literal)] = literal > 0
    if result.status == "UNSATISFIABLE" and has_witness:
        raise ValueError("UNSAT output contains a witness")
    if result.status == "SATISFIABLE" and not terminated:
        raise ValueError("witness lacks final terminator")
    return result
