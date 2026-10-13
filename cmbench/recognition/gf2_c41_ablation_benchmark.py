"""Prospectively frozen C41 ablations for the C16 exact analyzer.

The freeze command writes the complete source/input/control/schedule contract.
The run command refuses to measure unless that closure still verifies.  Each
ablation must reproduce the reference selected artifact byte-for-byte and must
reconstruct the frozen truth vector; invalid lanes are reported, never timed as
evidence.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Iterable, Mapping

from .gf2_decomposition_experiment import make_gf2_controls
from .natural_decomposition import partitioned_bits
from .gf2_decomposition import (
    ExactGF2Analysis,
    ExactGF2Artifact,
    GF2CandidateDescriptor,
    _cofactor_descriptors,
    _kronecker_descriptors,
    _rank_descriptor,
    analyze_screened_exact_gf2,
    candidate_partitions,
    truth_sha256,
    xor_component_artifact,
)


ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCHEMA = "crse-c41-gf2-ablation-freeze/v1"
RUN_SCHEMA = "crse-c41-gf2-ablation-run/v1"
METHODS = (
    "c16_reference",
    "no_shared_layout",
    "eager_all_descriptors",
    "linear_min_no_dedup_sort",
    "unchecked_partition_admission",
)
SOURCE_CLOSURE_PATHS = (
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/proved_rules.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/gf2_decomposition_experiment.py",
    "cmbench/recognition/gf2_c41_ablation_benchmark.py",
    "docs/recognition/c41_gf2_ablation_freeze_20260916/README.md",
    "docs/recognition/c41_gf2_ablation_freeze_20260916/EXTERNAL_PRODUCER_SEARCH.md",
)


@dataclass(frozen=True)
class C41Config:
    seed: int = 2026091641
    rounds: int = 5
    max_partitions: int = 64
    materialize_budget: int = 1
    max_wall_seconds: float = 1200.0

    def validate(self) -> None:
        if (
            type(self.seed) is not int
            or type(self.rounds) is not int or not 3 <= self.rounds <= 9
            or type(self.max_partitions) is not int or not 8 <= self.max_partitions <= 128
            or self.materialize_budget != 1
            or type(self.max_wall_seconds) not in (int, float)
            or not 60 <= self.max_wall_seconds <= 3600
        ):
            raise ValueError("invalid C41 ablation config")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_x(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl_x(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n")


def _source_closure(root: Path) -> list[dict[str, Any]]:
    result = []
    for relative in SOURCE_CLOSURE_PATHS:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"C41 source closure path is missing: {relative}")
        result.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    return result


def _control_documents(seed: int) -> list[dict[str, Any]]:
    return [
        {
            "case_id": row["case_id"],
            "n_vars": row["n_vars"],
            "truth_bits_hex": hex(row["bits"]),
            "truth_sha256": truth_sha256(row["bits"], row["n_vars"]),
            "required_kind": row["required_kind"],
            "row_partitions": row["row_partitions"],
        }
        for row in make_gf2_controls(seed)
    ]


def _schedule(cases: list[Mapping[str, Any]], config: C41Config) -> list[dict[str, Any]]:
    result = []
    for round_index in range(config.rounds):
        ordered_cases = sorted(cases, key=lambda row: _digest({
            "seed": config.seed, "round": round_index, "case_id": row["case_id"]
        }))
        for case_position, case in enumerate(ordered_cases):
            rotation = (round_index + case_position) % len(METHODS)
            methods = METHODS[rotation:] + METHODS[:rotation]
            if (round_index + case_position) % 2:
                methods = tuple(reversed(methods))
            for method_position, method in enumerate(methods):
                core = {
                    "round": round_index,
                    "case_id": case["case_id"],
                    "case_position": case_position,
                    "method": method,
                    "method_position": method_position,
                }
                result.append({**core, "schedule_sha256": _digest(core)})
    return result


def build_freeze(*, project_root: str | Path, c40_freeze_path: str | Path,
                 config: C41Config = C41Config(), created_utc: str) -> dict[str, Any]:
    """Freeze C41 completely before any C41 timing is collected."""
    config.validate()
    root = Path(project_root).resolve()
    c40_path = Path(c40_freeze_path)
    if not c40_path.is_absolute():
        c40_path = root / c40_path
    c40_raw = c40_path.read_bytes()
    c40 = json.loads(c40_raw)
    cases = [
        {
            "case_id": row["case_id"].replace("c40", "c41", 1),
            "source_case_id": row["case_id"],
            "n_vars": row["n_vars"],
            "truth_bits_hex": row["truth_bits_hex"],
            "truth_sha256": row["truth_sha256"],
        }
        for row in c40["cases"]
    ]
    controls = _control_documents(config.seed)
    closure = _source_closure(root)
    body = {
        "schema": FREEZE_SCHEMA,
        "status": "frozen_before_c41_measurement",
        "created_utc": created_utc,
        "config": asdict(config),
        "methods": list(METHODS),
        "ablation_contract": {
            "c16_reference": "Production C16 with budget one.",
            "no_shared_layout": "Repeat partition layout independently for rank, cofactor, and Kronecker descriptor construction; retain descriptor-first admission, canonical deduplication/order, and strict checks.",
            "eager_all_descriptors": "Retain shared layout and canonical deduplication/order, but strictly admit and reconstruct every unique descriptor.",
            "linear_min_no_dedup_sort": "Retain shared layout and strict budget-one admission, but select the minimum descriptor by a linear scan without bulk sort or digest deduplication.",
            "unchecked_partition_admission": "Retain shared layout and canonical deduplication/order, but construct the leading partition artifact without ExactGF2Artifact.from_dict or in-lane reconstruction. Post-timing validation remains mandatory.",
            "validity_gate": "Every method/case selected artifact document must equal c16_reference byte-for-byte and must reconstruct the frozen truth vector. Any failure invalidates that ablation and excludes its timing from claims.",
        },
        "input_provenance": {
            "source": "C40 prospectively frozen public confirmation truth vectors, copied into this independent C41 freeze.",
            "c40_freeze_path": c40_path.resolve().relative_to(root).as_posix(),
            "c40_freeze_file_sha256": hashlib.sha256(c40_raw).hexdigest(),
            "c40_declared_freeze_sha256": c40["freeze_sha256"],
            "selection_uses_c41_outcomes": False,
        },
        "cases": cases,
        "controls": controls,
        "schedule": _schedule(cases, config),
        "source_closure": closure,
        "source_closure_sha256": _digest(closure),
        "measurement_scope": "Warm-process Python analysis_ns only; frozen truth vectors are already loaded; post-timing validity checks are excluded.",
        "aggregation": "For each case and method, take the median analysis_ns over frozen rounds; sum case medians. Ratios are c16_reference sum divided by ablation sum and are descriptive, not causal estimates outside this implementation.",
    }
    return {**body, "freeze_sha256": _digest(body)}


def validate_freeze(freeze: Mapping[str, Any]) -> None:
    required = {
        "schema", "status", "created_utc", "config", "methods", "ablation_contract",
        "input_provenance", "cases", "controls", "schedule", "source_closure",
        "source_closure_sha256", "measurement_scope", "aggregation", "freeze_sha256",
    }
    if set(freeze) != required or freeze["schema"] != FREEZE_SCHEMA:
        raise ValueError("invalid C41 freeze fields or schema")
    if freeze["status"] != "frozen_before_c41_measurement" or freeze["methods"] != list(METHODS):
        raise ValueError("invalid C41 freeze status or methods")
    C41Config(**freeze["config"]).validate()
    body = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    if _digest(body) != freeze["freeze_sha256"]:
        raise ValueError("C41 freeze self-hash mismatch")
    if _digest(freeze["source_closure"]) != freeze["source_closure_sha256"]:
        raise ValueError("C41 source-closure aggregate mismatch")
    ids = [row["case_id"] for row in freeze["cases"]]
    expected_rows = len(ids) * C41Config(**freeze["config"]).rounds * len(METHODS)
    if len(ids) != len(set(ids)) or len(freeze["schedule"]) != expected_rows:
        raise ValueError("invalid C41 cases or schedule size")
    for row in freeze["cases"] + freeze["controls"]:
        bits, n_vars = int(row["truth_bits_hex"], 16), row["n_vars"]
        if truth_sha256(bits, n_vars) != row["truth_sha256"]:
            raise ValueError(f"C41 frozen truth identity mismatch: {row['case_id']}")


def verify_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    errors = []
    try:
        validate_freeze(freeze)
    except (TypeError, ValueError, KeyError) as exc:
        errors.append(f"freeze: {type(exc).__name__}: {exc}")
    for row in freeze.get("source_closure", []):
        path = root / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
            errors.append(f"source closure mismatch: {row['path']}")
    provenance = freeze.get("input_provenance", {})
    c40_path = root / provenance.get("c40_freeze_path", "__missing__")
    if not c40_path.is_file() or _sha256_file(c40_path) != provenance.get("c40_freeze_file_sha256"):
        errors.append("C40 source freeze file mismatch")
    return {"schema": "crse-c41-freeze-verification/v1", "verified": not errors, "errors": errors}


def _partitions(bits: int, n_vars: int, config: C41Config,
                row_partitions: Iterable[Iterable[int]] | None = None) -> tuple[tuple[int, ...], ...]:
    return (candidate_partitions(bits, n_vars, config.max_partitions) if row_partitions is None
            else tuple(tuple(row) for row in row_partitions))


def _shared_descriptors(bits: int, n_vars: int,
                        partitions: Iterable[tuple[int, ...]]) -> list[GF2CandidateDescriptor]:
    result = []
    for row in partitions:
        arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
        rank = _rank_descriptor(arranged, 1 << row_count, 1 << column_count, row)
        if rank is not None:
            result.append(rank)
        result.extend(_cofactor_descriptors(arranged, 1 << row_count, 1 << column_count, row))
        result.extend(_kronecker_descriptors(arranged, row_count, column_count, row))
    return result


def _repeated_layout_descriptors(bits: int, n_vars: int,
                                 partitions: Iterable[tuple[int, ...]]) -> list[GF2CandidateDescriptor]:
    result = []
    for row in partitions:
        arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
        rank = _rank_descriptor(arranged, 1 << row_count, 1 << column_count, row)
        if rank is not None:
            result.append(rank)
        arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
        result.extend(_cofactor_descriptors(arranged, 1 << row_count, 1 << column_count, row))
        arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
        result.extend(_kronecker_descriptors(arranged, row_count, column_count, row))
    return result


def _ordered_unique(descriptors: Iterable[GF2CandidateDescriptor], bits: int,
                    n_vars: int) -> list[GF2CandidateDescriptor]:
    unique: dict[str, GF2CandidateDescriptor] = {}
    for descriptor in descriptors:
        unique.setdefault(descriptor.digest(bits, n_vars), descriptor)
    return sorted(unique.values(), key=lambda item: item.sort_key(bits, n_vars))


def _analysis(method: str, bits: int, n_vars: int, config: C41Config, *,
              row_partitions: Iterable[Iterable[int]] | None = None) -> ExactGF2Analysis:
    if method == "c16_reference":
        return analyze_screened_exact_gf2(
            bits, n_vars, row_partitions=row_partitions, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
    partitions = _partitions(bits, n_vars, config, row_partitions)
    descriptors = (_repeated_layout_descriptors(bits, n_vars, partitions)
                   if method == "no_shared_layout" else _shared_descriptors(bits, n_vars, partitions))
    xor = xor_component_artifact(bits, n_vars)
    admitted: list[ExactGF2Artifact]
    descriptor_count: int
    if method == "linear_min_no_dedup_sort":
        keyed = [(descriptor.sort_key(bits, n_vars), index, descriptor)
                 for index, descriptor in enumerate(descriptors)]
        leading = [] if not keyed else [min(keyed, key=lambda row: (row[0], row[1]))[2]]
        admitted = [descriptor.materialize(bits, n_vars) for descriptor in leading]
        descriptor_count = len(descriptors)
    else:
        ordered = _ordered_unique(descriptors, bits, n_vars)
        descriptor_count = len(ordered)
        selected = ordered if method == "eager_all_descriptors" else ordered[:config.materialize_budget]
        if method == "unchecked_partition_admission":
            admitted = [ExactGF2Artifact(descriptor.document(bits, n_vars)) for descriptor in selected]
        else:
            admitted = [descriptor.materialize(bits, n_vars) for descriptor in selected]
    candidates = ([] if xor is None else [xor]) + admitted
    if method != "unchecked_partition_admission":
        if any(candidate.reconstruct() != bits for candidate in candidates):
            raise RuntimeError("C41 ablation candidate escaped exact reconstruction")
    candidates.sort(key=lambda item: (
        item.document["factor_bits"], item.kind, item.document["row_variables"], item.digest
    ))
    return ExactGF2Analysis(
        n_vars=n_vars, source_sha256=truth_sha256(bits, n_vars), partitions_tested=len(partitions),
        candidates=tuple(candidates), descriptors_screened=descriptor_count,
        artifacts_materialized=len(candidates),
    )


def _best_document(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best is not None else None


def _validity_rows(freeze: Mapping[str, Any], config: C41Config) -> list[dict[str, Any]]:
    rows = []
    all_inputs = list(freeze["cases"]) + list(freeze["controls"])
    for case in all_inputs:
        bits, n_vars = int(case["truth_bits_hex"], 16), case["n_vars"]
        row_partitions = case.get("row_partitions")
        reference = _analysis("c16_reference", bits, n_vars, config, row_partitions=row_partitions)
        expected = _best_document(reference)
        for method in METHODS:
            analysis = _analysis(method, bits, n_vars, config, row_partitions=row_partitions)
            selected = analysis.best
            rows.append({
                "case_id": case["case_id"],
                "input_class": "control" if "required_kind" in case else "public",
                "method": method,
                "selected_document_byte_identical": _canonical(_best_document(analysis)) == _canonical(expected),
                "selected_exact_reconstruction": selected is None if expected is None else (
                    selected is not None and selected.reconstruct() == bits
                ),
                "best_digest": selected.digest if selected is not None else None,
                "candidate_count": len(analysis.candidates),
                "descriptors_screened": analysis.descriptors_screened,
                "artifacts_materialized": analysis.artifacts_materialized,
            })
    return rows


def _summarize(rows: list[Mapping[str, Any]], validity: list[Mapping[str, Any]]) -> dict[str, Any]:
    validity_by_method = {
        method: all(row["selected_document_byte_identical"] and row["selected_exact_reconstruction"]
                    for row in validity if row["method"] == method)
        for method in METHODS
    }
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["method"])].append(row["analysis_ns"])
    sums = {
        method: sum(int(statistics.median(grouped[(case_id, method)]))
                    for case_id in sorted({row["case_id"] for row in rows}))
        for method in METHODS
    }
    reference = sums["c16_reference"]
    return {
        "validity_by_method": validity_by_method,
        "all_ablations_valid": all(validity_by_method.values()),
        "sum_case_median_analysis_ns": sums,
        "reference_over_ablation_ratio": {
            method: (reference / sums[method] if validity_by_method[method] else None)
            for method in METHODS if method != "c16_reference"
        },
        "interpretation": "Ratios below one mean the ablation was slower than C16. These individually scoped implementation ablations attribute effects only on this frozen host/workload and are not additive causal shares of the C15-to-C16 speedup.",
    }


def run_benchmark(*, project_root: str | Path, freeze_path: str | Path,
                  output: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    freeze_file = Path(freeze_path)
    if not freeze_file.is_absolute():
        freeze_file = root / freeze_file
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    freeze = json.loads(freeze_file.read_text(encoding="utf-8"))
    config = C41Config(**freeze["config"])
    verification = verify_freeze(freeze, root)
    if not verification["verified"]:
        raise ValueError("C41 freeze verification failed before measurement")
    validity = _validity_rows(freeze, config)
    invalid = sorted({row["method"] for row in validity
                      if not row["selected_document_byte_identical"] or not row["selected_exact_reconstruction"]})
    if invalid:
        result = {
            "schema": RUN_SCHEMA, "status": "invalid_ablation", "freeze_sha256": freeze["freeze_sha256"],
            "invalid_methods": invalid, "environment": {"python": sys.version, "platform": platform.platform()},
        }
        output_path.mkdir(parents=True, exist_ok=False)
        _write_json_x(output_path / "freeze_verification.json", verification)
        _write_jsonl_x(output_path / "validity.jsonl", validity)
        _write_json_x(output_path / "results.json", result)
        return result
    started = time.perf_counter()
    rows = []
    cases = {row["case_id"]: row for row in freeze["cases"]}
    for planned in freeze["schedule"]:
        if time.perf_counter() - started > config.max_wall_seconds:
            raise TimeoutError("C41 benchmark exceeded frozen wall budget")
        case = cases[planned["case_id"]]
        bits, n_vars = int(case["truth_bits_hex"], 16), case["n_vars"]
        measured = time.perf_counter_ns()
        analysis = _analysis(planned["method"], bits, n_vars, config)
        elapsed = max(1, time.perf_counter_ns() - measured)
        selected = analysis.best
        rows.append({
            "schema": "crse-c41-gf2-ablation-measurement/v1", **planned,
            "analysis_ns": elapsed, "n_vars": n_vars,
            "best_digest": selected.digest if selected is not None else None,
            "candidate_count": len(analysis.candidates),
            "descriptors_screened": analysis.descriptors_screened,
            "artifacts_materialized": analysis.artifacts_materialized,
        })
    summary = _summarize(rows, validity)
    result = {
        "schema": RUN_SCHEMA, "status": "complete", "freeze_path": freeze_file.relative_to(root).as_posix(),
        "freeze_sha256": freeze["freeze_sha256"], "environment": {
            "python": sys.version, "platform": platform.platform(),
        }, "measurement_rows": len(rows), "summary": summary,
    }
    output_path.mkdir(parents=True, exist_ok=False)
    _write_json_x(output_path / "freeze_verification.json", verification)
    _write_jsonl_x(output_path / "validity.jsonl", validity)
    _write_jsonl_x(output_path / "measurements.jsonl", rows)
    _write_json_x(output_path / "results.json", result)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--project-root", type=Path, default=ROOT)
    freeze.add_argument("--c40-freeze", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    freeze.add_argument("--created-utc", required=True)
    run = sub.add_parser("run")
    run.add_argument("--project-root", type=Path, default=ROOT)
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "freeze":
        document = build_freeze(
            project_root=args.project_root, c40_freeze_path=args.c40_freeze,
            created_utc=args.created_utc,
        )
        _write_json_x(args.output, document)
        print(json.dumps({"status": document["status"], "freeze_sha256": document["freeze_sha256"]}))
    else:
        result = run_benchmark(project_root=args.project_root, freeze_path=args.freeze, output=args.output)
        print(json.dumps({"status": result["status"], "summary": result.get("summary")}, sort_keys=True))


if __name__ == "__main__":
    main()
