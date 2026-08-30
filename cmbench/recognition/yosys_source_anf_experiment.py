"""Sealed independent-family confirmation for the C6 packed ANF core."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from cm_expr_serde import expr_from_json

from .natural_decomposition import analyze_decomposition, partition_witness
from .natural_decomposition_experiment import Budget
from .natural_source_anf_experiment import percentile, sha
from .portfolio import reference_bits
from .source_anf_hybrid import ProductCache, source_packed_partition
from .source_interaction import OPS, _validate_document, source_exact_partition
from .yosys_human_decomposition_data import (
    FIXTURE_ROOT,
    SOURCE_MANIFEST,
    make_yosys_human_documents,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C6_RUN = ROOT / "docs" / "recognition" / "runs" / "natural-source-anf-hybrid-20260830-004"
METHODS = (
    "set_source_anf",
    "packed_source_anf",
    "cached_packed_source_anf",
    "numpy_truth_vector_anf",
    "bitset_truth_vector_anf",
)
RUN_SCHEMA = "crse-yosys-source-anf-confirmation/v1"


@dataclass(frozen=True)
class YosysSourceAnfConfig:
    repetitions: int = 9
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self):
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 15
                or type(self.cache_capacity) is not int or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid Yosys source ANF confirmation configuration")

    def manifest(self, output: Path, base: Path):
        return {"schema": "crse-yosys-source-anf-confirmation-run-spec/v1",
            "purpose": "sealed independent-family and stronger-baseline confirmation of the C6 packed exact core",
            "methods": list(METHODS), "repetitions": self.repetitions,
            "cache_capacity": self.cache_capacity, "threads": self.threads,
            "max_seconds": self.max_seconds, "estimated_memory_mib": 128,
            "dataset_source": "YosysHQ/yosys-bench@52ff6fa991f2ab509618d8aaad02f307aac78848",
            "dataset_training_use": False, "retained_c6": relative(base), "output": relative(output),
            "network": False, "production_write": False,
            "criteria": {
                "exact": "all five methods reproduce all labels and canonical partitions with zero mismatches",
                "c6_baseline_cost": "packed and cached cores are at least 1.10x faster at median and no slower at p95 than NumPy truth-vector ANF on both sealed splits",
                "strong_baseline_cost": "cached packed core is no slower at median or p95 than bigint truth-vector ANF on both sealed splits",
                "legacy_set_cost": "cached packed core is no slower at median or p95 than the retained exact set-ANF path on both sealed splits",
                "independent_source": "all cases come from the pre-C7 Yosys fixture with no EPFL or C3-C6 training use",
            }}


def relative(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)).replace("\\", "/") if ROOT in path.parents or path == ROOT else str(path)


def write_json(path: Path, value: Any):
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def verify_retained_c6(base: Path):
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    if (manifest.get("schema") != "crse-natural-source-anf-hybrid-artifacts/v1"
            or manifest.get("status") != "complete" or summary.get("status") != "complete"
            or not summary.get("criteria", {}).get("packed_core")
            or not summary.get("criteria", {}).get("cached_packed_core")
            or summary.get("semantic_mismatches") != 0):
        raise ValueError("invalid retained C6 dependency")
    for name, expected in manifest["files_sha256"].items():
        if sha(base / name) != expected:
            raise ValueError(f"retained C6 artifact changed: {name}")
    changed_sources = [name for name, expected in manifest["source_sha256"].items()
                       if sha(ROOT / name) != expected]
    return {"path": relative(base), "manifest_sha256": sha(base / "manifest.json"),
        "packed_core": True, "cached_packed_core": True,
        "source_hybrid": summary["criteria"]["source_hybrid"],
        "historical_source_unchanged": not changed_sources,
        "historical_source_changes": changed_sources}


def source_fingerprints() -> dict[str, str]:
    paths = [
        ROOT / "cmbench/recognition/source_anf_hybrid.py",
        ROOT / "cmbench/recognition/source_interaction.py",
        ROOT / "cmbench/recognition/natural_decomposition.py",
        ROOT / "cmbench/recognition/yosys_human_decomposition_data.py",
        ROOT / "cmbench/recognition/yosys_source_anf_experiment.py",
        SOURCE_MANIFEST,
    ] + sorted(path for path in FIXTURE_ROOT.rglob("*") if path.is_file() and path != SOURCE_MANIFEST)
    return {relative(path): sha(path) for path in paths}


@lru_cache(maxsize=9)
def _variable_masks(n_vars: int) -> tuple[int, ...]:
    """Return the reusable packed input columns for one variable count."""
    rows = 1 << n_vars
    result = []
    for variable in range(n_vars):
        mask = 0
        for assignment in range(rows):
            mask |= ((assignment >> (n_vars - 1 - variable)) & 1) << assignment
        result.append(mask)
    return tuple(result)


def document_truth_bits(document: dict[str, Any], n_vars: int) -> int:
    """Evaluate a canonical source DAG into one exact packed truth vector."""
    nodes, root = _validate_document(document, n_vars)
    rows = 1 << n_vars
    full_mask = (1 << rows) - 1
    variable_masks = _variable_masks(n_vars)
    values: list[int] = []
    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported bigint truth-vector node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid bigint truth-vector variable")
            value = variable_masks[variable]
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological bigint truth-vector reference")
            if op == "not":
                value = ~values[references[0]] & full_mask
            else:
                left, right = (values[reference] for reference in references)
                if op == "and": value = left & right
                elif op == "or": value = left | right
                elif op == "xor": value = left ^ right
                elif op == "imp": value = (~left | right) & full_mask
                elif op == "eqv": value = ~(left ^ right) & full_mask
                else: raise ValueError("unreachable bigint truth-vector operation")
        values.append(value)
    return values[root]


def _execute(method: str, row: dict[str, Any], cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    started = time.perf_counter_ns()
    stats = None
    witness = None
    if method == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
    elif method == "packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars)
    elif method == "cached_packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars, cache=cache)
    elif method == "numpy_truth_vector_anf":
        bits = reference_bits(expr_from_json(document), n_vars)
        analysis = analyze_decomposition(bits, n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    elif method == "bitset_truth_vector_anf":
        bits = document_truth_bits(document, n_vars)
        analysis = analyze_decomposition(bits, n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    else:
        raise ValueError("unknown Yosys source ANF confirmation method")
    proposed_at = time.perf_counter_ns()
    if method in {"set_source_anf", "packed_source_anf", "cached_packed_source_anf"} and partition is not None:
        bits = document_truth_bits(document, n_vars)
        witness = partition_witness(bits, n_vars, partition)
    checked = time.perf_counter_ns()
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {"method": method, "split": row["split"], "case_id": row["case_id"],
        "family": row["family"], "n_vars": n_vars, "label": row["label"],
        "row_variables": list(partition) if partition is not None else None,
        "predicted": int(partition is not None), "accepted": accepted,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "signature_ns": proposed_at - started, "exact_check_ns": checked - proposed_at,
        "total_ns": checked - started, "truth_sha256": row["semantic_sha256"],
        "instrumentation": stats.to_dict() if stats is not None else None}


def benchmark(documents: list[dict], config: YosysSourceAnfConfig, check):
    samples: dict[tuple[str, str], list[dict]] = defaultdict(list)
    cache_telemetry = []
    for split in ("sealed_a", "sealed_b"):
        split_rows = [row for row in documents if row["split"] == split]
        for repetition in range(config.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                check()
                cache = ProductCache(config.cache_capacity) if method == "cached_packed_source_anf" else None
                for row in split_rows:
                    samples[(method, row["case_id"])].append(_execute(method, row, cache))
                if cache is not None:
                    cache_telemetry.append({"method": method, "split": split, "repetition": repetition,
                        "final_entries": len(cache), "evictions": cache.evictions})
    rows = []
    for key in sorted(samples):
        values = samples[key]
        if len(values) != config.repetitions:
            raise ValueError("incomplete Yosys source ANF timing repetitions")
        representative = values[0]
        for field in ("row_variables", "predicted", "accepted", "canonical_partition_match",
                      "semantic_mismatch", "truth_sha256", "instrumentation"):
            if any(value[field] != representative[field] for value in values[1:]):
                raise ValueError(f"nondeterministic Yosys source ANF result: {key}/{field}")
        rows.append({**representative,
            "signature_ns": int(statistics.median(value["signature_ns"] for value in values)),
            "exact_check_ns": int(statistics.median(value["exact_check_ns"] for value in values)),
            "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "timing_repetitions": config.repetitions})
    return rows, cache_telemetry


def summarize(rows: list[dict]):
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["split"])].append(row)
    result = {}
    for (method, split), values in sorted(grouped.items()):
        totals = [row["total_ns"] for row in values]
        result[f"{method}/{split}"] = {"cases": len(values),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "accepted": sum(row["accepted"] for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values),
            "median_total_ns": statistics.median(totals), "p95_total_ns": percentile(totals, .95),
            "maximum_total_ns": max(totals),
            "median_signature_ns": statistics.median(row["signature_ns"] for row in values)}
    return result


def criteria(summary: dict[str, Any], rows: list[dict], source_unchanged: bool):
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    def cost(method: str, baseline: str, minimum_speed: float):
        return all(summary[f"{baseline}/{split}"]["median_total_ns"] /
                   summary[f"{method}/{split}"]["median_total_ns"] >= minimum_speed
                   and summary[f"{method}/{split}"]["p95_total_ns"] <=
                   summary[f"{baseline}/{split}"]["p95_total_ns"]
                   for split in ("sealed_a", "sealed_b"))
    c6_baseline = all(cost(method, "numpy_truth_vector_anf", 1.10)
                      for method in ("packed_source_anf", "cached_packed_source_anf"))
    strong = cost("cached_packed_source_anf", "bitset_truth_vector_anf", 1.0)
    legacy_set = cost("cached_packed_source_anf", "set_source_anf", 1.0)
    return {"exact": exact, "independent_source": source_unchanged,
        "c6_baseline_cost": c6_baseline, "strong_baseline_cost": strong,
        "legacy_set_cost": legacy_set, "safety": exact,
        "production_promotion": exact and c6_baseline and strong and legacy_set}


def run_yosys_source_anf_experiment(config: YosysSourceAnfConfig, output: Path,
                                    base: Path = DEFAULT_C6_RUN, progress=print):
    config.validate()
    output, base = output.resolve(), base.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_spec.json", config.manifest(output, base))
    before = source_fingerprints()
    retained = verify_retained_c6(base)
    budget, started = Budget(config.max_seconds), time.perf_counter()
    progress("regenerating sealed Yosys human-authored family")
    documents, provenance = make_yosys_human_documents()
    write_json(output / "dataset.json", documents)
    write_json(output / "dataset_provenance.json", provenance)
    for n_vars in sorted({row["n_vars"] for row in documents}):
        _variable_masks(n_vars)
    progress("benchmarking packed source ANF and two truth-vector controls")
    rows, cache_telemetry = benchmark(documents, config, budget.check)
    method_summary = summarize(rows)
    unchanged = before == source_fingerprints()
    measured = criteria(method_summary, rows, unchanged)
    result = {"schema": RUN_SCHEMA, "status": "complete", "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c6": retained, "dataset_audit": provenance["audit"],
        "source_provenance": {key: provenance[key] for key in (
            "source", "upstream_url", "upstream_commit", "license", "source_manifest",
            "source_manifest_sha256", "network_access_performed", "source_checkout_modified")},
        "method_summary": method_summary, "cache_telemetry": cache_telemetry,
        "criteria": measured, "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows),
        "source_unchanged": unchanged}
    with (output / "benchmark_raw.jsonl").open("wb") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ["run_spec.json", "dataset.json", "dataset_provenance.json", "benchmark_raw.jsonl",
             "summary.json", "report.md"]
    manifest = {"schema": "crse-yosys-source-anf-confirmation-artifacts/v1", "status": "complete",
        "files_sha256": {name: sha(output / name) for name in files}, "source_sha256": before,
        "retained_c6_manifest_sha256": retained["manifest_sha256"]}
    write_json(output / "manifest.json", manifest)
    return result


def render_report(result):
    lines = ["# Yosys independent source-ANF confirmation", "", f"Status: **{result['status']}**", "",
        "| Method / split | Median total ns | p95 total ns | Maximum total ns |", "| --- | ---: | ---: | ---: |"]
    for key, values in result["method_summary"].items():
        lines.append(f"| {key} | {values['median_total_ns']:.0f} | {values['p95_total_ns']:.0f} | {values['maximum_total_ns']:.0f} |")
    lines += ["", "The NumPy path preserves the C6 reference contract. The bigint path is a stronger production-style truth-vector control.", "",
        f"Criteria: `{json.dumps(result['criteria'], sort_keys=True)}`", ""]
    return "\n".join(lines)
