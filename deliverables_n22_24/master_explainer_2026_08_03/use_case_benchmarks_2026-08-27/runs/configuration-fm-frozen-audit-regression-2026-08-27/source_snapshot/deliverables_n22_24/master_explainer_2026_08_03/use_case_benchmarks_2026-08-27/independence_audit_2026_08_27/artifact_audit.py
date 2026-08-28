"""Replay saved artifacts without importing any CM producer or prior auditor.

This is a correctness audit, not a performance experiment.  All writes go to a
new output directory; the historical benchmark directories remain untouched.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = BASE.parents[2]
CORE = BASE / "runs/configuration-fm-history-shootout-cudd-full40-2026-08-27"
SUPPLEMENT = BASE / "runs/configuration-fm-history-shootout-supplement-2026-08-27"
DELTA = BASE / "runs/configuration-fm-version-delta-full21-2026-08-27"
PILOT = BASE / "runs/configuration-fm-history-pilot-full40-2026-08-27"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AssertionError(message)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), f"no rows for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest_packed(value: int, k: int) -> str:
    return hashlib.sha256(value.to_bytes(max(1, ((1 << k) + 7) // 8), "little")).hexdigest()


def verify_run(run: Path) -> dict:
    checksum = run / "CHECKSUMS.sha256"
    before = sha(checksum)
    entries = checksum.read_text(encoding="ascii").splitlines()
    for line in entries:
        expected, relative = line.split("  ", 1)
        path = (run / relative).resolve()
        require(path.is_relative_to(run.resolve()), f"unsafe checksum path: {relative}")
        require(path.is_file() and sha(path) == expected, f"changed/missing saved artifact: {path}")
    require(sha(checksum) == before, f"checksum manifest changed while reading {run}")
    return {"run": str(run), "checksum_sha256": before, "files_verified": len(entries)}


def source_paths() -> list[Path]:
    # Explicit allowlist: never walk secrets, credentials, local databases or .git.
    core = [REPO / name for name in (
        "cm_ir.py", "bitset_backend.py", "cm_exprlib.py", "cmbench/output_budget.py",
        "cmbench/backends/robdd_dd.py", "cmbench/expr/eval.py",
    )]
    bench = [path for pattern in ("cm_feature_model*.py", "CONFIGURATION-*PROTOCOL*.md", "Dockerfile.feature-model-shootout")
             for path in BASE.glob(pattern)]
    return sorted(set(core + bench + list(HERE.glob("*.py"))))


def snapshot(output: Path) -> dict:
    rows = []
    for path in source_paths():
        relative = path.relative_to(REPO)
        initial = path.stat()
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        require(sha(path) == digest, f"source changed during snapshot: {path}")
        target = output / "source_snapshot" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        rows.append({"path": str(path), "relative_path": relative.as_posix(), "sha256": digest,
                     "bytes": len(content), "mtime_ns": initial.st_mtime_ns})
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True)
    result = {"observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "purpose": "current audit observation, NOT a reconstruction of historical benchmark source",
              "git_head": head.stdout.strip() if head.returncode == 0 else "unavailable", "files": rows}
    write_json(output / "source-observed-before.json", result)
    return result


def finalize(output: Path, observed: dict, runs: list[dict]) -> None:
    source_changes = []
    for row in observed["files"]:
        path = Path(row["path"])
        current = sha(path) if path.is_file() else None
        if current != row["sha256"]:
            source_changes.append({"path": row["path"], "before": row["sha256"], "after": current})
    # Recheck every artifact, not just the manifest: concurrent edits must be visible.
    final_runs = [verify_run(Path(row["run"])) for row in runs]
    require(final_runs == runs, "saved run checksum identity changed during audit")
    write_json(output / "concurrent-change-check.json", {
        "observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_changes": source_changes, "saved_runs_unchanged": True,
        "scope": "allowlisted sources and historical result artifacts; other task files not inspected",
    })
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (output / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha(path)}  {path.relative_to(output).as_posix()}\n" for path in files), encoding="ascii")


@lru_cache(maxsize=None)
def columns(k: int) -> tuple[int, ...]:
    """Closed-form variable columns, not the producer's enumerative mask builder."""
    full = (1 << (1 << k)) - 1
    return tuple((full // ((1 << (1 << variable)) + 1)) << (1 << variable) for variable in range(k))


def read_residual(path: Path) -> tuple[int, tuple[tuple[int, ...], ...]]:
    lines = path.read_text(encoding="ascii").splitlines()
    header = lines[0].split()
    require(len(header) == 4 and header[:2] == ["p", "cnf"], f"bad residual header: {path}")
    k, declared = int(header[2]), int(header[3])
    clauses = []
    for line in lines[1:]:
        parts = [int(token) for token in line.split()]
        require(parts and parts[-1] == 0 and 0 not in parts[:-1], f"bad residual clause: {path}")
        require(all(1 <= abs(lit) <= k for lit in parts[:-1]), "residual variable outside width")
        clauses.append(tuple(parts[:-1]))
    require(len(clauses) == declared, "residual clause-count mismatch")
    return k, tuple(clauses)


def scalar_cnf_vector(clauses, k: int) -> int:
    """Exhaustive assignment evaluator; never calls packed CNF/CM/CUDD code."""
    masks = [(sum(1 << (v - 1) for v in set(clause) if v > 0),
              sum(1 << (-v - 1) for v in set(clause) if v < 0)) for clause in clauses]
    result = bytearray(max(1, ((1 << k) + 7) // 8))
    for assignment in range(1 << k):
        if all((assignment & positive) or (~assignment & negative) for positive, negative in masks):
            result[assignment >> 3] |= 1 << (assignment & 7)
    return int.from_bytes(result, "little")


def replay_flat(data: dict) -> int:
    require(data["schema"] == "cm-flat-packed/v1", "unsupported flat schema")
    k, n_slots, root = int(data["k"]), int(data["n_slots"]), int(data["root_slot"])
    require(0 <= root < n_slots, "invalid flat root")
    full = (1 << (1 << k)) - 1
    values: dict[int, int] = {}

    def put(slot: int, value: int) -> None:
        require(0 <= slot < n_slots and slot not in values, "duplicate/out-of-range flat slot")
        values[slot] = value & full

    for slot, kind, payload in data["loads"]:
        if kind == "const":
            require(payload in (0, 1), "non-Boolean constant")
            put(slot, full if payload else 0)
        elif kind == "var":
            require(isinstance(payload, str) and payload.startswith("x") and payload[1:].isdigit(), "bad flat variable")
            variable = int(payload[1:])
            require(0 <= variable < k, "flat variable outside width")
            put(slot, columns(k)[variable])
        else:
            raise ValueError(f"unsupported flat load: {kind}")
    for slot, opcode, args in data["ops"]:
        require(all(arg in values for arg in args), "flat dependency before definition")
        operands = [values[arg] for arg in args]
        if opcode == 0:
            require(len(operands) == 1, "NOT arity")
            result = full ^ operands[0]
        elif opcode in (1, 2, 3):
            require(bool(operands), "empty n-ary operation")
            result = operands[0]
            for operand in operands[1:]:
                result = result & operand if opcode == 1 else result | operand if opcode == 2 else result ^ operand
        elif opcode in (4, 5):
            require(len(operands) == 2, "binary operation arity")
            result = (full ^ operands[0]) | operands[1] if opcode == 4 else full ^ (operands[0] ^ operands[1])
        else:
            raise ValueError(f"unsupported flat opcode: {opcode}")
        put(slot, result)
    require(len(values) == n_slots and root in values, "incomplete flat program")
    # packed_hex is intentionally ignored by the evaluator.
    return values[root]


def replay_bdd(data: dict, k: int) -> int:
    full = (1 << (1 << k)) - 1
    levels = {int(level): int(name[1:]) for name, level in data["level_of_var"].items()}
    require(len(levels) == k and set(levels.values()) == set(range(k)), "BDD variable map")
    roots = data["roots"]
    require(isinstance(roots, list) and len(roots) == 1, "unsupported BDD roots")
    cache = {}
    active = set()

    def visit(ref):
        if ref == "T":
            return full
        if ref == "F":
            return 0
        require(isinstance(ref, int) and ref != 0, "invalid BDD reference")
        identifier = abs(ref)
        if identifier not in cache:
            require(identifier not in active, "cyclic BDD")
            active.add(identifier)
            level, low, high = data[str(identifier)]
            require(int(level) in levels, "unknown BDD level")
            for child in (low, high):
                if isinstance(child, int):
                    require(int(data[str(abs(child))][0]) > int(level), "BDD order violation")
            selector = columns(k)[levels[int(level)]]
            cache[identifier] = ((full ^ selector) & visit(low)) | (selector & visit(high))
            active.remove(identifier)
        return cache[identifier] if ref > 0 else full ^ cache[identifier]

    return visit(roots[0])


def parse_nnf(text: str, k: int) -> tuple[dict[int, str], dict[int, list[tuple[int, tuple[int, ...]]]]]:
    """Non-certified d4 arc-literal format, as documented in pinned d4 README."""
    nodes = {}
    edges = {}
    for number, line in enumerate(text.splitlines(), start=1):
        fields = line.split()
        require(fields and fields[-1] == "0", f"NNF missing terminator line {number}")
        if fields[0] in ("a", "o", "t", "f"):
            require(len(fields) == 3, "certified/extended NNF node not admitted")
            identifier = int(fields[1])
            require(identifier > 0 and identifier not in nodes, "duplicate/invalid NNF node")
            nodes[identifier] = fields[0]
        else:
            integers = [int(field) for field in fields]
            require(len(integers) >= 3 and integers[0] > 0 and integers[1] > 0, "invalid NNF arc")
            literals = tuple(integers[2:-1])
            require(all(1 <= abs(lit) <= k for lit in literals), "NNF literal outside declared residual universe")
            require(len(set(map(abs, literals))) == len(literals), "duplicate/conflicting NNF arc literals")
            edges.setdefault(integers[0], []).append((integers[1], literals))
    require(1 in nodes, "missing d4 root 1")
    for parent, children in edges.items():
        require(parent in nodes and nodes[parent] in ("a", "o"), "invalid NNF arc source")
        require(all(child in nodes for child, _ in children), "dangling NNF arc")
    return nodes, edges


def replay_nnf(text: str, k: int) -> tuple[int, dict]:
    nodes, edges = parse_nnf(text, k)
    full = (1 << (1 << k)) - 1
    cache = {}
    active = set()
    deterministic_nodes = 0
    decomposable_nodes = 0

    def visit(identifier):
        nonlocal deterministic_nodes, decomposable_nodes
        if identifier in cache:
            return cache[identifier]
        require(identifier not in active, "cyclic NNF")
        active.add(identifier)
        kind = nodes[identifier]
        if kind in ("t", "f"):
            result = (full if kind == "t" else 0, frozenset(), 1 if kind == "t" else 0)
        else:
            branches = []
            for child, literals in edges.get(identifier, []):
                value, support, count = visit(child)
                guard_support = frozenset(abs(lit) - 1 for lit in literals)
                require(not support & guard_support, "NNF guard/child support overlap")
                for lit in literals:
                    column = columns(k)[abs(lit) - 1]
                    value &= column if lit > 0 else full ^ column
                branches.append((value, support | guard_support, count))
            require(bool(branches), "NNF internal node without arcs")
            support = frozenset().union(*(branch[1] for branch in branches))
            if kind == "o":
                value, count = 0, 0
                for branch_value, branch_support, branch_count in branches:
                    require(not value & branch_value, "NNF OR branches are not deterministic")
                    value |= branch_value
                    count += branch_count << (len(support) - len(branch_support))
                deterministic_nodes += 1
            else:
                value, count, used = full, 1, frozenset()
                for branch_value, branch_support, branch_count in branches:
                    require(not used & branch_support, "NNF AND children are not decomposable")
                    used |= branch_support
                    value &= branch_value
                    count *= branch_count
                decomposable_nodes += 1
            result = (value, support, count)
        active.remove(identifier)
        cache[identifier] = result
        return result

    value, support, root_count = visit(1)
    require(set(cache) == set(nodes), "unreachable NNF nodes")
    full_count = root_count << (k - len(support))
    require(value.bit_count() == full_count, "NNF structural count/exhaustive relation mismatch")
    return value, {"serialized_nodes": len(nodes), "serialized_edges": sum(map(len, edges.values())),
                   "support_variables": len(support), "independent_count": full_count,
                   "deterministic_or_nodes_checked": deterministic_nodes,
                   "decomposable_and_nodes_checked": decomposable_nodes}


def clustered_ratio(rows: list[dict], numerator: str, denominator: str | None = None) -> dict:
    histories = sorted({row["history"] for row in rows})
    logs = []
    for history in histories:
        group = [row for row in rows if row["history"] == history]
        logs.append(statistics.fmean(math.log(float(row[numerator]) / float(row[denominator]) if denominator else float(row[numerator])) for row in group))
    rng = random.Random(2026082709)
    bootstrap = sorted(math.exp(statistics.fmean(rng.choices(logs, k=len(logs)))) for _ in range(4000))
    leave_one_out = [math.exp(statistics.fmean(logs[:i] + logs[i + 1:])) for i in range(len(logs))]
    return {"equal_history_geomean": math.exp(statistics.fmean(logs)), "history_count": len(histories),
            "cluster_bootstrap_ci95": [bootstrap[100], bootstrap[3899]],
            "leave_one_history_out_range": [min(leave_one_out), max(leave_one_out)],
            "per_history": dict(zip(histories, map(math.exp, logs)))}


def audit(output: Path) -> dict:
    require(not output.exists(), f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    observed = snapshot(output)
    runs = [verify_run(run) for run in (PILOT, CORE, SUPPLEMENT, DELTA)]
    write_json(output / "historical-run-identities.json", runs)
    rows = csv_rows(CORE / "cases.csv")
    supplement = {row["case_id"]: row for row in csv_rows(SUPPLEMENT / "supplement.csv")}
    require(len(rows) == len(supplement) == 240, "unexpected endpoint coverage")
    audits = []
    total_assignments = 0
    for index, row in enumerate(rows, start=1):
        case_id = row["case_id"]
        key = hashlib.sha256(case_id.encode()).hexdigest()[:16]
        artifact_dir = CORE / "serialized" / key
        k, clauses = read_residual(artifact_dir / "residual.dimacs")
        expected = scalar_cnf_vector(clauses, k)
        cm = read_json(artifact_dir / "cm-flat-packed.json")
        cm_without_answer = {name: value for name, value in cm.items() if name != "packed_hex"}
        flat = replay_flat(cm_without_answer)
        bdd = replay_bdd(read_json(artifact_dir / "robdd.json"), k)
        nnf, nnf_metrics = replay_nnf((SUPPLEMENT / "ddnnf" / f"{key}.nnf").read_text(encoding="ascii"), k)
        require(expected == flat == bdd == nnf, f"artifact semantic mismatch: {case_id}")
        require(int.from_bytes(bytes.fromhex(cm["packed_hex"]), "little") == expected, f"stored CM answer mismatch: {case_id}")
        require(digest_packed(expected, k) == row["packed_sha256"], f"saved digest mismatch: {case_id}")
        require(expected.bit_count() == int(row["packed_true_count"]) == int(supplement[case_id]["d4_count"]), f"saved count mismatch: {case_id}")
        total_assignments += 1 << k
        audits.append({"case_id": case_id, "k": k, "all_replays_equal": True,
                       "assignments_checked": 1 << k, "count": expected.bit_count(),
                       **nnf_metrics,
                       "d4_reported_internal_nodes": int(supplement[case_id]["ddnnf_nodes"]),
                       "d4_reported_internal_edges": int(supplement[case_id]["ddnnf_edges"]),
                       "reported_nodes_equal_serialized": int(supplement[case_id]["ddnnf_nodes"]) == nnf_metrics["serialized_nodes"]})
        if index % 40 == 0:
            print(f"artifact replay {index}/{len(rows)}", flush=True)
    write_csv(output / "artifact-replay.csv", audits)
    delta_rows = csv_rows(DELTA / "version-delta.csv")
    statistics_by_width = {}
    for k in (8, 12, 16):
        selected = [row for row in rows if int(row["k"]) == k]
        transitions = [row for row in delta_rows if int(row["k"]) == k]
        statistics_by_width[str(k)] = {
            "endpoint_cm_over_cnf": clustered_ratio(selected, "cm_over_cnf_packed"),
            "endpoint_cm_over_cudd_extraction": clustered_ratio(selected, "cm_over_robdd_enumerate"),
            "delta_cm_over_cudd_DIAGNOSTIC_ONLY": clustered_ratio(transitions, "cm_extract_pair_ns_median", "cudd_extract_pair_ns_median"),
            "delta_comparison_warning": "asymmetric materialization and first-touch work; not a fair warm kernel ranking",
            "unique_endpoint_relation_digests": len({row["packed_sha256"] for row in selected}),
            "median_solution_density": statistics.median(float(row["solution_density"]) for row in selected),
            "delta_unchanged_cases": sum(int(row["changed_assignments"]) == 0 for row in transitions),
            "delta_cases": len(transitions),
        }
    write_json(output / "clustered-statistics.json", statistics_by_width)
    summary = {"schema": "cm-fm-deep-artifact-audit/v1", "status": "passed",
               "endpoint_cases": len(audits), "assignments_per_representation": total_assignments,
               "cm_instruction_replays_without_saved_answer": len(audits),
               "bdd_json_replays_without_CUDD": len(audits), "ddnnf_semantic_replays_without_d4": len(audits),
               "scalar_CNF_oracle_cases": len(audits),
               "ddnnf_internal_vs_serialized_node_disagreements": sum(not row["reported_nodes_equal_serialized"] for row in audits),
               "producer_modules_imported": [], "performance_claims_certified": False,
               "historical_source_reconstruction_claimed": False}
    write_json(output / "summary.json", summary)
    finalize(output, observed, runs)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    audit(arguments.output.resolve())
