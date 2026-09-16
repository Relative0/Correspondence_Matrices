"""Prospectively frozen public-corpus phase benchmark for C15/C16 GF(2)."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

from .blif import BlifConeMetadata, parse_blif
from .gf2_decomposition import (
    ExactGF2Analysis,
    GF2PhaseRecorder,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from .gf2_decomposition_experiment import make_gf2_controls


ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCHEMA = "crse-c39-gf2-phase-public-freeze/v1"
RUN_SCHEMA = "crse-c39-gf2-phase-public-run/v1"
METHODS = ("c15_exhaustive", "c16_screened")
EPFL_RELATIVE = Path("external/epfl-benchmarks")
SOURCE_CLOSURE_PATHS = (
    "cmbench/recognition/blif.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/gf2_phase_benchmark.py",
)


@dataclass(frozen=True)
class GF2PhaseBenchmarkConfig:
    seed: int = 20260916
    case_count: int = 19
    rounds: int = 5
    phase_rounds: int = 3
    max_partitions: int = 64
    materialize_budget: int = 4
    min_support: int = 3
    max_support: int = 8
    min_source_nodes: int = 8
    max_source_nodes: int = 256
    max_wall_seconds: float = 900.0

    def validate(self) -> None:
        if (
            type(self.seed) is not int
            or type(self.case_count) is not int or not 1 <= self.case_count <= 19
            or type(self.rounds) is not int or not 3 <= self.rounds <= 9
            or type(self.phase_rounds) is not int or not 1 <= self.phase_rounds <= 9
            or type(self.max_partitions) is not int or not 8 <= self.max_partitions <= 128
            or type(self.materialize_budget) is not int or not 1 <= self.materialize_budget <= 16
            or type(self.min_support) is not int or type(self.max_support) is not int
            or not 2 <= self.min_support <= self.max_support <= 10
            or type(self.min_source_nodes) is not int or type(self.max_source_nodes) is not int
            or not 1 <= self.min_source_nodes <= self.max_source_nodes <= 4096
            or type(self.max_wall_seconds) not in (int, float)
            or not 60 <= self.max_wall_seconds <= 3600
        ):
            raise ValueError("invalid C39 GF(2) phase benchmark config")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _write_json_x(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl_x(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n")


def _epfl_commit(root: Path) -> str:
    epfl = root / EPFL_RELATIVE
    try:
        return subprocess.check_output(
            ["git", "-C", str(epfl), "rev-parse", "HEAD"], text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("EPFL benchmark checkout has no readable Git revision") from exc


def _source_closure(root: Path) -> list[dict[str, Any]]:
    result = []
    for relative in SOURCE_CLOSURE_PATHS:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"C39 source closure path is missing: {relative}")
        result.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    return result


def _metadata_document(metadata: BlifConeMetadata) -> dict[str, Any]:
    return {
        "source_nodes": metadata.source_nodes,
        "source_edges": metadata.source_edges,
        "depth": metadata.depth,
        "local_fanin": metadata.local_fanin,
        "local_cubes": metadata.local_cubes,
        "local_literals": metadata.local_literals,
    }


def _candidate_key(seed: int, source_sha256: str, metadata: BlifConeMetadata) -> str:
    return _digest({
        "selection_schema": "c39-epfl-one-cone-per-source/v1",
        "seed": seed,
        "source_sha256": source_sha256,
        "root_node": metadata.node,
        "support": list(metadata.support),
        "metadata": _metadata_document(metadata),
    })


def _schedule(cases: list[Mapping[str, Any]], config: GF2PhaseBenchmarkConfig) -> list[dict[str, Any]]:
    result = []
    for round_index in range(config.rounds):
        ordered_cases = sorted(
            cases,
            key=lambda row: _digest({"seed": config.seed, "round": round_index,
                                     "case_id": row["case_id"], "lane": "primary"}),
        )
        for position, case in enumerate(ordered_cases):
            methods = METHODS if (round_index + position) % 2 == 0 else tuple(reversed(METHODS))
            for within_case_order, method in enumerate(methods):
                core = {
                    "round": round_index,
                    "case_id": case["case_id"],
                    "method": method,
                    "within_case_order": within_case_order,
                    "case_position": position,
                }
                result.append({**core, "schedule_sha256": _digest(core)})
    return result


def _freeze_controls(seed: int) -> list[dict[str, Any]]:
    return [
        {
            "case_id": control["case_id"],
            "n_vars": control["n_vars"],
            "required_kind": control["required_kind"],
            "row_partitions": control["row_partitions"],
            "source_sha256": truth_sha256(control["bits"], control["n_vars"]),
        }
        for control in make_gf2_controls(seed)
    ]


def build_freeze(*, project_root: str | Path, config: GF2PhaseBenchmarkConfig,
                 created_utc: str | None = None) -> dict[str, Any]:
    """Select one bounded cone per EPFL source before inspecting C39 timing."""
    config.validate()
    root = Path(project_root).resolve()
    epfl = root / EPFL_RELATIVE
    source_paths = sorted(
        path for family in ("arithmetic", "random_control") for path in (epfl / family).glob("*.blif")
    )
    if len(source_paths) != 20:
        raise ValueError("C39 expects the 20-file public EPFL arithmetic/random-control slice")

    source_rows = []
    selected = []
    for path in source_paths:
        source_sha256 = _sha256_file(path)
        netlist = parse_blif(path)
        eligible = [
            metadata for metadata in netlist.candidate_metadata(
                min_support=config.min_support,
                max_support=config.max_support,
                max_source_nodes=config.max_source_nodes,
            )
            if metadata.source_nodes >= config.min_source_nodes
        ]
        source_rows.append({
            "path": _relative(root, path),
            "bytes": path.stat().st_size,
            "sha256": source_sha256,
            "eligible_cones": len(eligible),
        })
        if not eligible:
            continue
        metadata = min(eligible, key=lambda row: (_candidate_key(config.seed, source_sha256, row), row.node))
        bits, support = netlist.packed_value(metadata.node)
        if tuple(support) != metadata.support:
            raise RuntimeError("EPFL cone support identity disagrees with packed evaluation")
        candidate_key = _candidate_key(config.seed, source_sha256, metadata)
        selected.append({
            "case_id": f"epfl-c39-{candidate_key[:16]}",
            "selection_sha256": candidate_key,
            "source": _relative(root, path),
            "source_sha256": source_sha256,
            "root_node": metadata.node,
            "support": list(metadata.support),
            "n_vars": len(metadata.support),
            "truth_bits_hex": hex(bits),
            "truth_sha256": truth_sha256(bits, len(metadata.support)),
            "cone": _metadata_document(metadata),
        })
    if len(selected) < config.case_count:
        raise ValueError("insufficient public EPFL sources with a bounded eligible C39 cone")
    cases = sorted(selected, key=lambda row: (row["selection_sha256"], row["case_id"]))[:config.case_count]
    if len({row["case_id"] for row in cases}) != len(cases):
        raise RuntimeError("C39 case identifier collision")

    created = created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    core = {
        "schema": FREEZE_SCHEMA,
        "status": "frozen_before_timing",
        "created_utc": created,
        "timing_results_inspected": False,
        "config": asdict(config),
        "corpus": {
            "collection": "EPFL arithmetic and random-control BLIF benchmark slice",
            "public_repository": "https://github.com/lsils/benchmarks",
            "upstream_commit": _epfl_commit(root),
            "one_cone_per_source_file": True,
            "selection_policy": "Hash-ranked bounded cone per source file, then hash-ranked source representatives; no timing or decomposition result enters selection.",
            "prospective_boundary": {
                "selection_frozen_before_c39_timing": True,
                "new_to_c15_c16_c21_cohorts": True,
                "independent_of_prior_project_development": False,
                "limitation": "The local EPFL mirror was previously inspected in other project work, so this is a public prospective confirmation slice, not a development-blind corpus.",
            },
            "source_files": source_rows,
        },
        "cases": cases,
        "schedule": _schedule(cases, config),
        "controls": _freeze_controls(config.seed),
        "analysis_contract": {
            "input": "Frozen packed truth vector; source parsing and truth construction are excluded from the primary analysis-only timing.",
            "c15_control": "analyze_exact_gf2 with all accepted artifacts materialized",
            "c16_candidate": "analyze_screened_exact_gf2 with complete descriptor evaluation and the frozen materialize budget",
            "canonical_result": "C15 and C16 best artifact documents must be byte-identical on every public case and every structured control.",
            "phase_measurement": "A separate instrumented pass records direct non-additive wall-clock phase scopes. It is not included in the primary C15/C16 timing ratio.",
            "primary_statistic": "Sum of per-case medians across balanced analysis-only calls.",
        },
        "source_closure": _source_closure(root),
    }
    freeze = {**core, "source_closure_sha256": _digest(core["source_closure"])}
    freeze["freeze_sha256"] = _digest(freeze)
    validate_freeze(freeze)
    return freeze


def validate_freeze(freeze: Mapping[str, Any]) -> None:
    expected = {
        "schema", "status", "created_utc", "timing_results_inspected", "config", "corpus", "cases",
        "schedule", "controls", "analysis_contract", "source_closure", "source_closure_sha256", "freeze_sha256",
    }
    if not isinstance(freeze, Mapping) or set(freeze) != expected:
        raise ValueError("invalid C39 freeze fields")
    if freeze["schema"] != FREEZE_SCHEMA or freeze["status"] != "frozen_before_timing":
        raise ValueError("invalid C39 freeze identity")
    if freeze["timing_results_inspected"] is not False:
        raise ValueError("C39 freeze must precede timing inspection")
    config = GF2PhaseBenchmarkConfig(**freeze["config"])
    config.validate()
    core = {key: freeze[key] for key in expected if key != "freeze_sha256"}
    if freeze["freeze_sha256"] != _digest(core):
        raise ValueError("C39 freeze digest mismatch")
    if freeze["source_closure_sha256"] != _digest(freeze["source_closure"]):
        raise ValueError("C39 source closure digest mismatch")
    cases = freeze["cases"]
    if not isinstance(cases, list) or len(cases) != config.case_count:
        raise ValueError("C39 case count mismatch")
    case_ids = [row.get("case_id") for row in cases if isinstance(row, Mapping)]
    if len(case_ids) != len(cases) or len(set(case_ids)) != len(cases):
        raise ValueError("C39 duplicate or invalid case identifiers")
    for row in cases:
        expected_case = {"case_id", "selection_sha256", "source", "source_sha256", "root_node", "support",
                         "n_vars", "truth_bits_hex", "truth_sha256", "cone"}
        if set(row) != expected_case or not isinstance(row["support"], list):
            raise ValueError("invalid C39 case fields")
        if row["n_vars"] != len(row["support"]) or not config.min_support <= row["n_vars"] <= config.max_support:
            raise ValueError("C39 support bounds mismatch")
        bits = int(row["truth_bits_hex"], 16)
        if truth_sha256(bits, row["n_vars"]) != row["truth_sha256"]:
            raise ValueError("C39 truth identity mismatch")
    if freeze["schedule"] != _schedule(cases, config):
        raise ValueError("C39 balanced schedule mismatch")
    if len(freeze["controls"]) != 12:
        raise ValueError("C39 control freeze mismatch")


def verify_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Verify code, BLIF source, selected cone metadata, and truth identities."""
    validate_freeze(freeze)
    root = Path(project_root).resolve()
    closure = _source_closure(root)
    source_closure_match = closure == freeze["source_closure"]
    source_rows = {row["path"]: row for row in freeze["corpus"]["source_files"]}
    source_checks = []
    for relative, expected in sorted(source_rows.items()):
        path = root / relative
        source_checks.append({
            "path": relative,
            "present": path.is_file(),
            "bytes_match": path.is_file() and path.stat().st_size == expected["bytes"],
            "sha256_match": path.is_file() and _sha256_file(path) == expected["sha256"],
        })
    case_checks = []
    for case in freeze["cases"]:
        path = root / case["source"]
        match = False
        detail = None
        try:
            netlist = parse_blif(path)
            metadata = netlist.bounded_metadata(
                case["root_node"], min_support=1, max_support=16, max_source_nodes=4096
            )
            bits, support = netlist.packed_value(case["root_node"])
            match = (
                metadata is not None
                and tuple(support) == tuple(case["support"])
                and _metadata_document(metadata) == case["cone"]
                and truth_sha256(bits, case["n_vars"]) == case["truth_sha256"]
                and _candidate_key(freeze["config"]["seed"], case["source_sha256"], metadata)
                == case["selection_sha256"]
            )
        except (OSError, ValueError, RuntimeError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
        case_checks.append({"case_id": case["case_id"], "match": match, "detail": detail})
    return {
        "schema": "crse-c39-gf2-phase-freeze-verification/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "source_closure_match": source_closure_match,
        "source_files": source_checks,
        "cases": case_checks,
        "verified": source_closure_match and all(
            row["present"] and row["bytes_match"] and row["sha256_match"] for row in source_checks
        ) and all(row["match"] for row in case_checks),
    }


def _load_cases(freeze: Mapping[str, Any], root: Path) -> dict[str, tuple[int, int]]:
    cases = {}
    for row in freeze["cases"]:
        netlist = parse_blif(root / row["source"])
        bits, support = netlist.packed_value(row["root_node"])
        if tuple(support) != tuple(row["support"]) or truth_sha256(bits, row["n_vars"]) != row["truth_sha256"]:
            raise ValueError(f"C39 frozen source changed for {row['case_id']}")
        cases[row["case_id"]] = (bits, row["n_vars"])
    return cases


def _best_document(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best is not None else None


def _analyze(method: str, bits: int, n_vars: int, config: GF2PhaseBenchmarkConfig,
             recorder: GF2PhaseRecorder | None = None) -> ExactGF2Analysis:
    if method == "c15_exhaustive":
        return analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions,
                                 phase_recorder=recorder)
    if method == "c16_screened":
        return analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget, phase_recorder=recorder,
        )
    raise ValueError("unknown C39 analysis method")


def _functional_rows(cases: Mapping[str, tuple[int, int]], config: GF2PhaseBenchmarkConfig
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    for case_id, (bits, n_vars) in sorted(cases.items()):
        exhaustive = _analyze("c15_exhaustive", bits, n_vars, config)
        screened = _analyze("c16_screened", bits, n_vars, config)
        rows.append({
            "case_id": case_id,
            "n_vars": n_vars,
            "exact_best_identity_match": _best_document(exhaustive) == _best_document(screened),
            "exhaustive_exact": all(item.reconstruct() == bits for item in exhaustive.candidates),
            "screened_exact": all(item.reconstruct() == bits for item in screened.candidates),
            "exhaustive_candidate_count": len(exhaustive.candidates),
            "screened_unique_descriptors": screened.descriptors_screened,
            "screened_artifacts_materialized": screened.artifacts_materialized,
            "best_digest": screened.best.digest if screened.best else None,
        })
    controls = []
    for row in make_gf2_controls(config.seed):
        kwargs = {"row_partitions": row["row_partitions"]} if row["row_partitions"] else {"max_partitions": 32}
        exhaustive = analyze_exact_gf2(row["bits"], row["n_vars"], **kwargs)
        screened = analyze_screened_exact_gf2(
            row["bits"], row["n_vars"], materialize_budget=config.materialize_budget, **kwargs
        )
        controls.append({
            "case_id": row["case_id"],
            "required_kind": row["required_kind"],
            "exact_best_identity_match": _best_document(exhaustive) == _best_document(screened),
            "screened_exact": all(item.reconstruct() == row["bits"] for item in screened.candidates),
            "required_kind_recovered": (row["required_kind"] in screened.kinds
                                        if row["required_kind"] else not screened.candidates),
        })
    return rows, controls


def _primary_measurements(freeze: Mapping[str, Any], cases: Mapping[str, tuple[int, int]],
                          config: GF2PhaseBenchmarkConfig, started: float) -> list[dict[str, Any]]:
    rows = []
    for planned in freeze["schedule"]:
        if time.perf_counter() - started > config.max_wall_seconds:
            raise TimeoutError("C39 primary benchmark exceeded wall budget")
        bits, n_vars = cases[planned["case_id"]]
        measure_started = time.perf_counter_ns()
        analysis = _analyze(planned["method"], bits, n_vars, config)
        elapsed_ns = max(1, time.perf_counter_ns() - measure_started)
        rows.append({
            "schema": "crse-c39-gf2-primary-measurement/v1",
            **planned,
            "n_vars": n_vars,
            "analysis_ns": elapsed_ns,
            "partitions_tested": analysis.partitions_tested,
            "descriptors_screened": analysis.descriptors_screened,
            "artifacts_materialized": analysis.artifacts_materialized,
            "candidate_count": len(analysis.candidates),
            "best_digest": analysis.best.digest if analysis.best else None,
        })
    return rows


def _phase_measurements(cases: Mapping[str, tuple[int, int]], config: GF2PhaseBenchmarkConfig,
                        started: float) -> list[dict[str, Any]]:
    rows = []
    for round_index in range(config.phase_rounds):
        case_ids = sorted(cases, key=lambda case_id: _digest(
            {"seed": config.seed, "round": round_index, "case_id": case_id, "lane": "phase"}
        ))
        for case_id in case_ids:
            for method in (METHODS if round_index % 2 == 0 else tuple(reversed(METHODS))):
                if time.perf_counter() - started > config.max_wall_seconds:
                    raise TimeoutError("C39 phase benchmark exceeded wall budget")
                bits, n_vars = cases[case_id]
                recorder = GF2PhaseRecorder()
                analysis = _analyze(method, bits, n_vars, config, recorder)
                rows.append({
                    "schema": "crse-c39-gf2-phase-measurement/v1",
                    "round": round_index,
                    "case_id": case_id,
                    "method": method,
                    "n_vars": n_vars,
                    "best_digest": analysis.best.digest if analysis.best else None,
                    "phases": recorder.snapshot(),
                })
    return rows


def _summary(primary: list[Mapping[str, Any]], phase: list[Mapping[str, Any]],
             functional: list[Mapping[str, Any]], controls: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in primary:
        grouped[(row["case_id"], row["method"])].append(row["analysis_ns"])
    case_ids = sorted({row["case_id"] for row in primary})
    medians = {
        (case_id, method): statistics.median(grouped[(case_id, method)])
        for case_id in case_ids for method in METHODS
    }
    totals = {method: sum(medians[(case_id, method)] for case_id in case_ids) for method in METHODS}
    phase_totals: dict[str, dict[str, int]] = {method: defaultdict(int) for method in METHODS}
    phase_calls: dict[str, dict[str, int]] = {method: defaultdict(int) for method in METHODS}
    for row in phase:
        for item in row["phases"]["phases"]:
            phase_totals[row["method"]][item["name"]] += item["elapsed_ns"]
            phase_calls[row["method"]][item["name"]] += item["calls"]
    return {
        "primary_median_case_sum_ns": {method: int(total) for method, total in totals.items()},
        "screened_over_exhaustive_speedup": totals["c15_exhaustive"] / totals["c16_screened"],
        "phase_aggregate": {
            method: [
                {"name": name, "elapsed_ns": phase_totals[method][name], "calls": phase_calls[method][name]}
                for name in sorted(phase_totals[method])
            ] for method in METHODS
        },
        "phase_scope_note": "Phase scopes are direct and may be non-additive; primary timing uses an uninstrumented separate pass.",
        "functional": {
            "public_cases_exact_best_identity": all(row["exact_best_identity_match"] for row in functional),
            "public_cases_exact_reconstruction": all(row["exhaustive_exact"] and row["screened_exact"] for row in functional),
            "controls_exact_best_identity": all(row["exact_best_identity_match"] for row in controls),
            "controls_expected_behavior": all(row["required_kind_recovered"] for row in controls),
        },
    }


def run_benchmark(*, project_root: str | Path, freeze_path: str | Path,
                  output: str | Path) -> dict[str, Any]:
    """Run only a verified pre-timing C39 freeze and write immutable results."""
    root = Path(project_root).resolve()
    freeze_file = Path(freeze_path)
    if not freeze_file.is_absolute():
        freeze_file = root / freeze_file
    output_path = Path(output)
    freeze = json.loads(freeze_file.read_text(encoding="utf-8"))
    config = GF2PhaseBenchmarkConfig(**freeze["config"])
    verification = verify_freeze(freeze, root)
    if not verification["verified"]:
        raise ValueError("C39 freeze verification failed before timing")
    output_path.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cases = _load_cases(freeze, root)
    functional, controls = _functional_rows(cases, config)
    primary = _primary_measurements(freeze, cases, config, started)
    phase = _phase_measurements(cases, config, started)
    summary = _summary(primary, phase, functional, controls)
    status = "complete" if all(summary["functional"].values()) else "failed"
    result = {
        "schema": RUN_SCHEMA,
        "status": status,
        "freeze_path": _relative(root, freeze_file),
        "freeze_sha256": freeze["freeze_sha256"],
        "config": asdict(config),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "wall_seconds": time.perf_counter() - started,
        "summary": summary,
    }
    _write_json_x(output_path / "freeze_verification.json", verification)
    _write_json_x(output_path / "functional.json", {"public_cases": functional, "controls": controls})
    _write_jsonl_x(output_path / "primary_measurements.jsonl", primary)
    _write_jsonl_x(output_path / "phase_measurements.jsonl", phase)
    _write_json_x(output_path / "results.json", result)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze", help="create an immutable pre-timing EPFL selection")
    freeze.add_argument("--project-root", type=Path, default=ROOT)
    freeze.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run", help="verify and execute a frozen benchmark")
    run.add_argument("--project-root", type=Path, default=ROOT)
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "freeze":
        freeze = build_freeze(project_root=args.project_root, config=GF2PhaseBenchmarkConfig())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _write_json_x(args.output, freeze)
        print(f"wrote frozen C39 public corpus: {args.output}")
    else:
        result = run_benchmark(project_root=args.project_root, freeze_path=args.freeze, output=args.output)
        print(json.dumps({"status": result["status"], "speedup": result["summary"]["screened_over_exhaustive_speedup"]},
                         sort_keys=True))


if __name__ == "__main__":
    main()
