"""Independent exactness, aggregation, provenance, and round-trip audit for the representation battery."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


WIDTHS = (8, 12, 16)
PARTIAL_FRACTIONS = (0.25, 0.5, 0.75)
PARTIAL_CONTEXTS = 64


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(run: Path) -> int:
    lines = (run / "CHECKSUMS.sha256").read_text(encoding="ascii").splitlines()
    for line in lines:
        expected, relative = line.split("  ", 1)
        path = run / relative
        require(path.is_file(), f"missing checksummed artifact: {relative}")
        require(sha256_file(path) == expected, f"checksum mismatch: {relative}")
    return len(lines)


@lru_cache(maxsize=None)
def patterns(k: int) -> tuple[int, ...]:
    width = 1 << k
    return tuple(sum(1 << assignment for assignment in range(width) if (assignment >> index) & 1) for index in range(k))


def cnf_bitset(residual: tuple[tuple[int, ...], ...], k: int) -> int:
    mask = (1 << (1 << k)) - 1
    pats = patterns(k)
    value = mask
    for clause in residual:
        clause_value = 0
        for literal in clause:
            pattern = pats[abs(literal) - 1]
            clause_value |= pattern if literal > 0 else (~pattern) & mask
        value &= clause_value
    return value


def packed_context_mask(k: int, context: dict[int, bool]) -> int:
    mask = (1 << (1 << k)) - 1
    pats = patterns(k)
    for variable, selected in context.items():
        mask &= pats[variable] if selected else ~pats[variable]
    return mask & ((1 << (1 << k)) - 1)


def contexts(case_id: str, k: int, fraction: float) -> tuple[dict[int, bool], ...]:
    rng = random.Random(int.from_bytes(hashlib.sha256(f"{case_id}|ctx|{fraction}".encode()).digest()[:8], "big"))
    fixed = max(1, round(k * fraction))
    return tuple({variable: bool(rng.getrandbits(1)) for variable in rng.sample(range(k), fixed)}
                 for _ in range(PARTIAL_CONTEXTS))


def geomean(values) -> float:
    vals = [float(value) for value in values]
    return math.exp(statistics.fmean(math.log(value) for value in vals))


def close(actual: float, expected: float, label: str) -> None:
    require(math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12),
            f"{label}: {actual} != {expected}")


def load_bdd(path: Path, backend: str):
    if backend == "dd.cudd":
        from dd import cudd as dd_module
    elif backend == "dd.autoref":
        from dd import autoref as dd_module
    else:
        raise ValueError(f"unsupported audited BDD backend: {backend}")
    manager = dd_module.BDD()
    roots = manager.load(str(path))
    root = roots["f"] if isinstance(roots, dict) else roots[0]
    return manager, root


def bdd_extract(manager, root, k: int) -> int:
    value = 0
    care = {f"x{index}" for index in range(k)}
    for assignment in manager.pick_iter(root, care_vars=care):
        index = sum(1 << variable for variable in range(k) if assignment[f"x{variable}"])
        value |= 1 << index
    return value


def sat_decisions(residual: tuple[tuple[int, ...], ...], context_rows: tuple[dict[int, bool], ...]) -> tuple[bool, ...]:
    from pysat.solvers import Solver
    solver = Solver(name="cadical195", bootstrap_with=residual)
    try:
        return tuple(solver.solve(assumptions=[variable + 1 if selected else -(variable + 1)
                                               for variable, selected in context.items()]) for context in context_rows)
    finally:
        solver.delete()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    checksum_count = verify_checksums(run)
    rows = list(csv.DictReader((run / "cases.csv").open(encoding="utf-8", newline="")))
    partial_rows = list(csv.DictReader((run / "partial-contexts.csv").open(encoding="utf-8", newline="")))
    family_rows = list(csv.DictReader((run / "families.csv").open(encoding="utf-8", newline=""))) if (run / "families.csv").exists() else []
    corpus = {item["case_id"]: item for item in (json.loads(line) for line in (run / "corpus.jsonl").read_text(encoding="utf-8").splitlines())}
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    require(len(rows) == summary["case_count"] == len(corpus), "case count mismatch")
    require(len(partial_rows) == summary["partial_row_count"], "partial count mismatch")
    require(len(family_rows) == summary["family_row_count"], "family count mismatch")
    partial_by_case: dict[str, list[dict]] = defaultdict(list)
    for row in partial_rows:
        partial_by_case[row["case_id"]].append(row)
    family_by_case = {row["case_id"]: row for row in family_rows}

    relation_checks = 0
    context_checks = 0
    roundtrip_checks = 0
    family_checks = 0
    for row in rows:
        case = corpus[row["case_id"]]
        k = int(case["k"])
        residual = tuple(tuple(int(literal) for literal in clause) for clause in case["residual"])
        packed = cnf_bitset(residual, k)
        packed_bytes = packed.to_bytes(1 << max(0, k - 3), "little")
        require(hashlib.sha256(packed_bytes).hexdigest() == row["packed_sha256"] == case["packed_sha256"],
                f"packed digest mismatch: {row['case_id']}")
        require(packed.bit_count() == int(row["packed_true_count"]) == int(case["packed_true_count"]),
                f"packed count mismatch: {row['case_id']}")
        require(bool((packed >> int(case["planted_bits"])) & 1), f"planted witness absent: {row['case_id']}")
        close(float(row["cm_over_cnf_packed"]), float(row["cm_packed_ns_median"]) / float(row["cnf_packed_ns_median"]), "CM/CNF")
        close(float(row["cm_over_cse_packed"]), float(row["cm_packed_ns_median"]) / float(row["cse_packed_ns_median"]), "CM/CSE")
        close(float(row["cm_over_robdd_enumerate"]), float(row["cm_packed_ns_median"]) / float(row["robdd_extract_enumerate_ns_median"]), "CM/ROBDD")
        artifact_dir = run / "serialized" / hashlib.sha256(row["case_id"].encode()).hexdigest()[:16]
        cm_json = json.loads((artifact_dir / "cm-flat-packed.json").read_text(encoding="utf-8"))
        require(int.from_bytes(bytes.fromhex(cm_json["packed_hex"]), "little") == packed, "CM serialized relation mismatch")
        dimacs_lines = (artifact_dir / "residual.dimacs").read_text(encoding="ascii").splitlines()
        roundtrip_residual = tuple(tuple(map(int, line.split()[:-1])) for line in dimacs_lines[1:])
        require(cnf_bitset(roundtrip_residual, k) == packed, "CNF serialized relation mismatch")
        manager, root = load_bdd(artifact_dir / "robdd.json", row["robdd_backend"])
        require(bdd_extract(manager, root, k) == packed, "ROBDD serialized relation mismatch")
        require(int(manager.count(root, nvars=k)) == packed.bit_count(), "ROBDD count mismatch")
        relation_checks += 1
        roundtrip_checks += 3

        for partial in partial_by_case[row["case_id"]]:
            fraction = float(partial["fixed_fraction"])
            ctx = contexts(row["case_id"], k, fraction)
            expected = tuple(bool(packed & packed_context_mask(k, item)) for item in ctx)
            bdd_values = tuple(manager.let({f"x{variable}": selected for variable, selected in item.items()}, root) != manager.false
                               for item in ctx)
            require(bdd_values == expected, f"audited BDD partial mismatch: {row['case_id']} {fraction}")
            require(sat_decisions(residual, ctx) == expected, f"audited SAT partial mismatch: {row['case_id']} {fraction}")
            close(float(partial["packed_over_robdd"]), float(partial["packed_session_ns_median"]) / float(partial["robdd_session_ns_median"]), "partial packed/BDD")
            close(float(partial["packed_over_cadical"]), float(partial["packed_session_ns_median"]) / float(partial["cadical_session_ns_median"]), "partial packed/SAT")
            context_checks += len(ctx)

        if case["edited_residual"] is not None:
            family = family_by_case[row["case_id"]]
            edited = tuple(tuple(int(literal) for literal in clause) for clause in case["edited_residual"])
            changed = (packed ^ cnf_bitset(edited, k)).bit_count()
            require(changed == int(family["changed_assignments"]), f"family delta mismatch: {row['case_id']}")
            close(float(family["changed_fraction"]), changed / (1 << k), "family changed fraction")
            close(float(family["cm_reuse_over_fresh"]), float(family["cm_edit_reuse_compile_ns"]) / float(family["cm_edit_fresh_compile_ns"]), "family CM reuse")
            close(float(family["robdd_shared_over_fresh_build"]), float(family["robdd_edit_shared_build_ns"]) / float(family["robdd_edit_fresh_build_ns"]), "family BDD reuse")
            family_checks += 1

    real_rows = [row for row in rows if row["corpus"] == "real"]
    for k in WIDTHS:
        selected = [row for row in real_rows if int(row["k"]) == k]
        published = summary["real_by_k"][str(k)]
        require(len(selected) == published["n"], f"real stratum count mismatch k={k}")
        if selected:
            close(published["cm_over_cnf_packed_geomean"], geomean(float(row["cm_over_cnf_packed"]) for row in selected), f"real CM/CNF k={k}")
            close(published["cm_over_cse_packed_geomean"], geomean(float(row["cm_over_cse_packed"]) for row in selected), f"real CM/CSE k={k}")
            close(published["cm_over_robdd_enumerate_geomean"], geomean(float(row["cm_over_robdd_enumerate"]) for row in selected), f"real CM/BDD k={k}")
    require(all(value == 0 for value in summary["correctness"].values()), "published correctness summary is not zero")
    audit = {
        "schema_version": "cm-representation-battery-audit/v1", "status": "passed",
        "checksum_files_verified_before_audit_output": checksum_count, "case_rows": len(rows),
        "relation_reconstructions": relation_checks, "partial_context_decisions_rechecked": context_checks,
        "serialization_roundtrips_rechecked": roundtrip_checks, "family_deltas_rechecked": family_checks,
        "published_aggregate_strata_rechecked": len([k for k in WIDTHS if any(int(row["k"]) == k for row in real_rows)]),
    }
    audit_path = run / "independent-audit.json"
    require(not audit_path.exists(), f"refusing to overwrite audit: {audit_path}")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in run.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (run / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(run).as_posix()}\n" for path in files), encoding="ascii"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
