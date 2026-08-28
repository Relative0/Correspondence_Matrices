"""Exact affected-assignment benchmark for adjacent real feature-model versions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import cm_feature_model_history_pilot as pilot  # noqa: E402
import cm_feature_model_representation_battery as battery  # noqa: E402
from bitset_backend import _eval_words, get_flat_program  # noqa: E402
from cm_ir import clear_cm_ir_persistent_cache, compile_expr_to_cm_ir  # noqa: E402
from cmbench.backends.robdd_dd import expr_to_dd_bdd, safe_bdd_node_count  # noqa: E402


SCHEMA = "cm-fm-version-delta/v1"
PROTOCOL = "CONFIGURATION-FM-HISTORY-SHOOTOUT-PROTOCOL.md"
DEFAULT_PILOT_RUN = HERE / "runs" / "configuration-fm-history-pilot-full40-2026-08-27"
DEFAULT_OUTPUT = HERE / "runs" / "configuration-fm-version-delta-full21-2026-08-27"
WIDTHS = (8, 12, 16)
SLICE_KINDS = ("incidence", "hash")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packed_sha(value: int, k: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, k - 3), "little")).hexdigest()


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_checksums(output: Path) -> None:
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (output / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}\n" for path in files),
        encoding="ascii",
    )


def unique_name_map(parsed: pilot.ParsedCNF) -> dict[str, int]:
    result: dict[str, int] = {}
    for variable, name in parsed.feature_names.items():
        if name in result and result[name] != variable:
            raise ValueError(f"duplicate feature name {name!r}")
        result[name] = variable
    return result


def remap_joint(
    earlier: pilot.ParsedCNF, later: pilot.ParsedCNF
) -> tuple[list[tuple[int, ...]], list[int], list[int], int]:
    """Share variables only when the two DIMACS files give the same feature name."""
    key_to_id: dict[tuple[str, str], int] = {}

    def identifier(key: tuple[str, str]) -> int:
        if key not in key_to_id:
            key_to_id[key] = len(key_to_id) + 1
        return key_to_id[key]

    earlier_map = [0] * (earlier.n_vars + 1)
    later_map = [0] * (later.n_vars + 1)
    for variable in range(1, earlier.n_vars + 1):
        name = earlier.feature_names.get(variable)
        earlier_map[variable] = identifier(("feature", name) if name is not None else ("earlier-aux", str(variable)))
    for variable in range(1, later.n_vars + 1):
        name = later.feature_names.get(variable)
        later_map[variable] = identifier(("feature", name) if name is not None else ("later-aux", str(variable)))

    clauses = [
        tuple(mapping[abs(literal)] if literal > 0 else -mapping[abs(literal)] for literal in clause)
        for parsed, mapping in ((earlier, earlier_map), (later, later_map))
        for clause in parsed.clauses
    ]
    return clauses, earlier_map, later_map, len(key_to_id)


def joint_witness(
    earlier: pilot.ParsedCNF, later: pilot.ParsedCNF
) -> tuple[dict[int, bool], dict[int, bool], dict]:
    from pysat.solvers import Solver

    construct_started = time.perf_counter_ns()
    clauses, earlier_map, later_map, unified_variables = remap_joint(earlier, later)
    solver = Solver(name="cadical195", bootstrap_with=clauses)
    construct_ns = time.perf_counter_ns() - construct_started
    solve_started = time.perf_counter_ns()
    satisfiable = solver.solve()
    solve_ns = time.perf_counter_ns() - solve_started
    if not satisfiable:
        solver.delete()
        raise ValueError("adjacent versions have no joint satisfying assignment over shared feature names")
    model = {abs(literal): literal > 0 for literal in (solver.get_model() or [])}
    earlier_product = {variable: model.get(earlier_map[variable], False) for variable in range(1, earlier.n_vars + 1)}
    later_product = {variable: model.get(later_map[variable], False) for variable in range(1, later.n_vars + 1)}
    solver.delete()
    if not pilot.scalar_cnf(earlier.clauses, earlier_product):
        raise AssertionError("joint witness fails earlier model")
    if not pilot.scalar_cnf(later.clauses, later_product):
        raise AssertionError("joint witness fails later model")
    return earlier_product, later_product, {
        "joint_variables": unified_variables,
        "joint_clauses": len(clauses),
        "joint_solver_construct_ns": construct_ns,
        "joint_solver_solve_ns": solve_ns,
    }


def choose_names(
    transition_id: str,
    kind: str,
    k: int,
    earlier: pilot.ParsedCNF,
    later: pilot.ParsedCNF,
) -> tuple[str, ...]:
    earlier_names = unique_name_map(earlier)
    later_names = unique_name_map(later)
    common = set(earlier_names) & set(later_names)
    if len(common) < k:
        raise ValueError(f"only {len(common)} shared named features for k={k}")
    if kind == "hash":
        return tuple(sorted(common, key=lambda name: hashlib.sha256(f"{transition_id}|{name}".encode()).digest())[:k])
    if kind == "incidence":
        earlier_incidence = Counter(abs(literal) for clause in earlier.clauses for literal in clause)
        later_incidence = Counter(abs(literal) for clause in later.clauses for literal in clause)
        return tuple(sorted(
            common,
            key=lambda name: (-(earlier_incidence[earlier_names[name]] + later_incidence[later_names[name]]), name),
        )[:k])
    raise ValueError(kind)


def cm_pair(earlier_expr, later_expr, k: int, rounds: int) -> tuple[int, int, dict]:
    samples = []
    result = None
    for _ in range(rounds):
        clear_cm_ir_persistent_cache()
        earlier_diag: dict = {}
        started = time.perf_counter_ns()
        earlier_node = compile_expr_to_cm_ir(earlier_expr, diagnostics=earlier_diag, persistent_cache=True, reuse_cache=False)
        earlier_compile_ns = time.perf_counter_ns() - started
        later_diag: dict = {}
        started = time.perf_counter_ns()
        later_node = compile_expr_to_cm_ir(later_expr, diagnostics=later_diag, persistent_cache=True, reuse_cache=False)
        later_reuse_compile_ns = time.perf_counter_ns() - started
        started = time.perf_counter_ns()
        earlier_value = _eval_words(get_flat_program(earlier_node), tuple(f"x{i}" for i in range(k - 1, -1, -1)), {})
        later_value = _eval_words(get_flat_program(later_node), tuple(f"x{i}" for i in range(k - 1, -1, -1)), {})
        extract_ns = time.perf_counter_ns() - started
        result = (earlier_value, later_value)
        samples.append({
            "earlier_compile_ns": earlier_compile_ns,
            "later_reuse_compile_ns": later_reuse_compile_ns,
            "extract_pair_ns": extract_ns,
            "later_persistent_hits": int(later_diag.get("ir_persistent_cache_hits", 0)),
            "later_persistent_misses": int(later_diag.get("ir_persistent_cache_misses", 0)),
        })
    assert result is not None
    return result[0], result[1], {
        "cm_earlier_compile_ns_median": statistics.median(row["earlier_compile_ns"] for row in samples),
        "cm_later_reuse_compile_ns_median": statistics.median(row["later_reuse_compile_ns"] for row in samples),
        "cm_extract_pair_ns_median": statistics.median(row["extract_pair_ns"] for row in samples),
        "cm_later_persistent_hits_median": statistics.median(row["later_persistent_hits"] for row in samples),
        "cm_later_persistent_misses_median": statistics.median(row["later_persistent_misses"] for row in samples),
        "cm_samples_json": json.dumps(samples, separators=(",", ":")),
    }


def cudd_pair(earlier_expr, later_expr, k: int, rounds: int) -> tuple[int, int, dict]:
    from dd import cudd

    samples = []
    result = None
    order = [f"x{index}" for index in range(k)]
    for _ in range(rounds):
        earlier_bdd = battery.build_bdd(earlier_expr, k, cudd, order)
        started = time.perf_counter_ns()
        later_root = expr_to_dd_bdd(later_expr, earlier_bdd.manager, {name: name for name in order})
        later_shared_build_ns = time.perf_counter_ns() - started
        later_nodes = int(safe_bdd_node_count(earlier_bdd.manager, later_root) or 0)
        later_bdd = battery.BDDArtifact(
            earlier_bdd.manager, later_root, 0, later_shared_build_ns, later_nodes, tuple(order), earlier_bdd.backend
        )
        started = time.perf_counter_ns()
        earlier_value = battery.bdd_extract_enumerate(earlier_bdd, k)
        later_value = battery.bdd_extract_enumerate(later_bdd, k)
        extract_ns = time.perf_counter_ns() - started
        result = (earlier_value, later_value)
        samples.append({
            "setup_ns": earlier_bdd.setup_ns,
            "earlier_build_ns": earlier_bdd.build_ns,
            "later_shared_build_ns": later_shared_build_ns,
            "earlier_nodes": earlier_bdd.nodes,
            "later_nodes": later_nodes,
            "extract_pair_ns": extract_ns,
        })
    assert result is not None
    return result[0], result[1], {
        f"cudd_{key}_median": statistics.median(row[key] for row in samples)
        for key in samples[0]
    } | {"cudd_samples_json": json.dumps(samples, separators=(",", ":"))}


def selector_sat_vectors(
    earlier_residual: tuple[tuple[int, ...], ...], later_residual: tuple[tuple[int, ...], ...], k: int
) -> tuple[int, int, dict]:
    from pysat.solvers import Solver

    earlier_selector, later_selector = k + 1, k + 2
    clauses = [tuple([-earlier_selector, *clause]) for clause in earlier_residual]
    clauses.extend(tuple([-later_selector, *clause]) for clause in later_residual)
    started = time.perf_counter_ns()
    solver = Solver(name="cadical195", bootstrap_with=clauses)
    construct_ns = time.perf_counter_ns() - started
    values = []
    query_counts = []
    started = time.perf_counter_ns()
    for selector, disabled in ((earlier_selector, later_selector), (later_selector, earlier_selector)):
        value = 0
        for assignment in range(1 << k):
            assumptions = [selector, -disabled]
            assumptions.extend(variable + 1 if (assignment >> variable) & 1 else -(variable + 1) for variable in range(k))
            if solver.solve(assumptions=assumptions):
                value |= 1 << assignment
        values.append(value)
        query_counts.append(1 << k)
    enumerate_ns = time.perf_counter_ns() - started
    solver.delete()
    return values[0], values[1], {
        "cadical_selector_construct_ns": construct_ns,
        "cadical_selector_enumerate_pair_ns": enumerate_ns,
        "cadical_selector_queries": sum(query_counts),
    }


def first_set(value: int) -> int:
    return -1 if value == 0 else (value & -value).bit_length() - 1


def current_git_head() -> str:
    if os.environ.get("CM_BATTERY_GIT_HEAD"):
        return os.environ["CM_BATTERY_GIT_HEAD"]
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def run(pilot_run: Path, source: Path, output: Path, rounds: int, limit_transitions: int) -> int:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    provenance_path = pilot_run / "SOURCE-PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    payloads = {item["model_id"]: item for item in provenance["selected_payloads"]}
    parsed_models: dict[str, pilot.ParsedCNF] = {}
    input_rows = []
    for model_id, item in payloads.items():
        path = source / "selected_payloads" / item["cache_filename"]
        if not path.is_file() or sha256_file(path) != item["dimacs_sha256"]:
            raise SystemExit(f"missing or changed official input: {path}")
        parsed_models[model_id] = pilot.parse_dimacs(path)
        input_rows.append({"model_id": model_id, "path": str(path), "sha256": item["dimacs_sha256"], "bytes": path.stat().st_size})

    output.mkdir(parents=True)
    rows = []
    case_rows = []
    admissions = []
    transitions = [
        (history_row["history"], transition)
        for history_row in provenance["transitions"]
        for transition in history_row["transitions"]
    ]
    if limit_transitions:
        transitions = transitions[:limit_transitions]
    transition_total = len(transitions)
    for transition_index, (history, transition) in enumerate(transitions, start=1):
        earlier_id = f"{history}@{transition['earlier_version']}"
        later_id = f"{history}@{transition['later_version']}"
        transition_id = f"{earlier_id}->{transition['later_version']}"
        print(f"[{transition_index}/{transition_total}] {transition_id}", flush=True)
        earlier = parsed_models[earlier_id]
        later = parsed_models[later_id]
        common_names = set(unique_name_map(earlier)) & set(unique_name_map(later))
        try:
            earlier_product, later_product, joint_stats = joint_witness(earlier, later)
        except ValueError as exc:
            admissions.append({"transition_id": transition_id, "history": history, "admitted": False, "reason": str(exc)})
            continue
        admissions.append({
                "transition_id": transition_id,
                "history": history,
                "label": transition["label"],
                "admitted": True,
                "reason": "",
                "shared_named_features": len(common_names),
                **joint_stats,
        })
        earlier_by_name = unique_name_map(earlier)
        later_by_name = unique_name_map(later)
        for k in WIDTHS:
            for kind in SLICE_KINDS:
                    names = choose_names(transition_id, kind, k, earlier, later)
                    earlier_variables = tuple(earlier_by_name[name] for name in names)
                    later_variables = tuple(later_by_name[name] for name in names)
                    earlier_residual, earlier_condition = pilot.condition_cnf(earlier.clauses, earlier_product, earlier_variables)
                    later_residual, later_condition = pilot.condition_cnf(later.clauses, later_product, later_variables)
                    earlier_direct = battery.cnf_bitset(earlier_residual, k)
                    later_direct = battery.cnf_bitset(later_residual, k)
                    earlier_expr = battery.expression_from_residual(earlier_residual, k)
                    later_expr = battery.expression_from_residual(later_residual, k)
                    earlier_cm, later_cm, cm_stats = cm_pair(earlier_expr, later_expr, k, rounds)
                    earlier_bdd, later_bdd, bdd_stats = cudd_pair(earlier_expr, later_expr, k, rounds)
                    earlier_sat, later_sat, sat_stats = selector_sat_vectors(earlier_residual, later_residual, k)
                    if len({earlier_direct, earlier_cm, earlier_bdd, earlier_sat}) != 1:
                        raise AssertionError(f"earlier relation mismatch: {transition_id} {kind} k={k}")
                    if len({later_direct, later_cm, later_bdd, later_sat}) != 1:
                        raise AssertionError(f"later relation mismatch: {transition_id} {kind} k={k}")
                    xor_started = time.perf_counter_ns()
                    changed = earlier_direct ^ later_direct
                    changed_count = changed.bit_count()
                    xor_ns = time.perf_counter_ns() - xor_started
                    union_count = (earlier_direct | later_direct).bit_count()
                    case_id = f"{transition_id}|{kind}|k{k}"
                    row = {
                        "case_id": case_id,
                        "transition_id": transition_id,
                        "history": history,
                        "label": transition["label"],
                        "earlier_model_id": earlier_id,
                        "later_model_id": later_id,
                        "slice_kind": kind,
                        "k": k,
                        "shared_named_features": len(common_names),
                        "slice_feature_names_json": json.dumps(names, ensure_ascii=False, separators=(",", ":")),
                        "earlier_residual_clauses": len(earlier_residual),
                        "later_residual_clauses": len(later_residual),
                        "earlier_residual_literals": earlier_condition["residual_literals"],
                        "later_residual_literals": later_condition["residual_literals"],
                        "earlier_count": earlier_direct.bit_count(),
                        "later_count": later_direct.bit_count(),
                        "earlier_witness_assignment": first_set(earlier_direct),
                        "later_witness_assignment": first_set(later_direct),
                        "changed_assignments": changed_count,
                        "changed_fraction": changed_count / (1 << k),
                        "relation_jaccard": (earlier_direct & later_direct).bit_count() / max(1, union_count),
                        "added_assignments": (later_direct & ~earlier_direct).bit_count(),
                        "removed_assignments": (earlier_direct & ~later_direct).bit_count(),
                        "xor_extract_ns": xor_ns,
                        "earlier_packed_sha256": packed_sha(earlier_direct, k),
                        "later_packed_sha256": packed_sha(later_direct, k),
                        "changed_packed_sha256": packed_sha(changed, k),
                        **cm_stats,
                        **bdd_stats,
                        **sat_stats,
                        "relations_equal_all_arms": True,
                    }
                    rows.append(row)
                    case_rows.append({
                        "case_id": case_id,
                        "k": k,
                        "slice_kind": kind,
                        "feature_names": names,
                        "earlier_residual": earlier_residual,
                        "later_residual": later_residual,
                        "earlier_packed_sha256": row["earlier_packed_sha256"],
                        "later_packed_sha256": row["later_packed_sha256"],
                        "changed_packed_sha256": row["changed_packed_sha256"],
                    })

    write_csv(output / "version-delta.csv", rows)
    write_csv(output / "admissions.csv", admissions)
    write_jsonl(output / "cases.jsonl", case_rows)
    write_jsonl(output / "inputs.jsonl", input_rows)
    by_k = {}
    for k in WIDTHS:
        selected = [row for row in rows if row["k"] == k]
        by_k[str(k)] = {
            "n": len(selected),
            "nonzero_delta_cases": sum(row["changed_assignments"] > 0 for row in selected),
            "identical_relation_cases": sum(row["changed_assignments"] == 0 for row in selected),
            "changed_fraction_median": statistics.median(row["changed_fraction"] for row in selected),
            "relation_jaccard_median": statistics.median(row["relation_jaccard"] for row in selected),
            "cm_over_cudd_pair_extraction_geomean": battery.geomean(
                row["cm_extract_pair_ns_median"] / row["cudd_extract_pair_ns_median"] for row in selected
            ),
            "cadical_over_cm_pair_extraction_geomean": battery.geomean(
                row["cadical_selector_enumerate_pair_ns"] / row["cm_extract_pair_ns_median"] for row in selected
            ),
        }
    summary = {
        "schema_version": SCHEMA,
        "status": "diagnostic" if limit_transitions else "completed",
        "transition_count": len(admissions),
        "admitted_transitions": sum(str(row["admitted"]).lower() == "true" or row["admitted"] is True for row in admissions),
        "case_count": len(rows),
        "correctness_mismatches": 0,
        "by_k": by_k,
        "claim_boundary": "exact bounded differences under a joint satisfying context and shared named features; not whole-model semantic equivalence",
    }
    json_dump(output / "summary.json", summary)
    json_dump(output / "manifest.json", {
        "schema_version": SCHEMA,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": PROTOCOL,
        "pilot_run": str(pilot_run),
        "source_root": str(source),
        "source_commit": provenance["source_commit"],
        "source_provenance_sha256": sha256_file(provenance_path),
        "rounds": rounds,
        "diagnostic_limit_transitions": limit_transitions,
        "widths": WIDTHS,
        "slice_kinds": SLICE_KINDS,
        "container_image_id": os.environ.get("CM_SHOOTOUT_IMAGE_ID", "unavailable"),
        "python": sys.version,
        "git_head": current_git_head(),
    })
    write_checksums(output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-run", type=Path, default=DEFAULT_PILOT_RUN)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--limit-transitions", type=int, default=0)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("rounds must be positive")
    if args.limit_transitions < 0:
        parser.error("limit-transitions must be nonnegative")
    return run(
        args.pilot_run.resolve(), args.source_root.resolve(), args.output.resolve(), args.rounds, args.limit_transitions
    )


if __name__ == "__main__":
    raise SystemExit(main())
