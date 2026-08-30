"""Frozen EPFL comparison for packed, cached, and budgeted source ANF."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from cm_expr_serde import expr_from_json

from .decomposition_data import canonical, packed_sha256
from .natural_decomposition import analyze_decomposition, partition_witness
from .natural_decomposition_experiment import DEFAULT_SCOUT, Budget
from .natural_decomposition_matched_data import make_matched_natural_documents
from .portfolio import reference_bits
from .source_anf_hybrid import (
    ProductCache,
    source_anf_packed,
    source_hybrid_partition,
    source_packed_partition,
)
from .source_interaction import source_exact_partition

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C5_RUN = ROOT / "docs" / "recognition" / "runs" / "natural-variable-cut-20260829-001"
RUN_SCHEMA = "crse-natural-source-anf-hybrid-experiment/v1"
METHODS = (
    "set_source_anf",
    "packed_source_anf",
    "cached_packed_source_anf",
    "budgeted_hybrid",
    "truth_vector_anf",
)
SOURCE_FILES = (
    "cmbench/recognition/source_anf_hybrid.py",
    "cmbench/recognition/natural_source_anf_experiment.py",
    "cmbench/recognition/source_interaction.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/natural_decomposition_data.py",
    "cmbench/recognition/natural_decomposition_matched_data.py",
    "docs/recognition/source_scouts/natural-decomposition-epfl-20260829-001.json",
    "external/epfl-benchmarks/LICENSE",
)


@dataclass(frozen=True)
class NaturalSourceAnfConfig:
    dataset_seed: int = 20260829
    repetitions: int = 5
    cache_capacity: int = 1024
    validation_gate_quantile: float = 0.90
    threads: int = 2
    max_seconds: int = 120

    def validate(self) -> None:
        if (type(self.dataset_seed) is not int or not 0 <= self.dataset_seed < 2**32
                or type(self.repetitions) is not int or not 3 <= self.repetitions <= 9
                or type(self.cache_capacity) is not int or not 1 <= self.cache_capacity <= 16_384
                or type(self.validation_gate_quantile) is not float
                or not 0.5 <= self.validation_gate_quantile <= 0.99
                or type(self.threads) is not int or not 1 <= self.threads <= 2
                or type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid natural source ANF configuration")

    def manifest(self, output: Path, scout: Path, base: Path) -> dict[str, Any]:
        return {
            "schema": "crse-natural-source-anf-hybrid-run-spec/v1",
            "purpose": "exact packed symbolic ANF, cache, and validation-frozen fallback comparison",
            "dataset_seed": self.dataset_seed,
            "methods": list(METHODS),
            "repetitions": self.repetitions,
            "cache_capacity": self.cache_capacity,
            "validation_gate_quantile": self.validation_gate_quantile,
            "gate_selection_data": ["validation"],
            "threads": self.threads,
            "max_seconds": self.max_seconds,
            "estimated_memory_mib": 192,
            "scout": _relative(scout),
            "retained_c5": _relative(base),
            "output": _relative(output),
            "network": False,
            "production_write": False,
            "criteria": {
                "exact": "all five methods reproduce every frozen label and canonical partition",
                "median_speed": "budgeted hybrid is at least 1.10x faster than truth-vector ANF on test and confirmatory medians",
                "p95_tail": "budgeted hybrid p95 does not exceed truth-vector ANF on test or confirmatory",
                "fallback": "every validation or held-out budget fallback exactly matches truth-vector ANF",
                "telemetry": "maximum cost, cache, and fallback counts are retained",
            },
        }
def _relative(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)).replace("\\", "/") if ROOT in path.parents or path == ROOT else str(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    path.write_bytes(payload + b"\n")


def source_fingerprints(scout: Path) -> dict[str, str]:
    paths = [ROOT / value for value in SOURCE_FILES]
    if scout.resolve() != (ROOT / SOURCE_FILES[-2]).resolve():
        paths[-2] = scout.resolve()
    return {_relative(path): sha(path) for path in paths}


def verify_retained_c5(base: Path) -> dict[str, Any]:
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    if (manifest.get("schema") != "crse-natural-variable-cut-artifacts/v1"
            or manifest.get("status") != "complete" or summary.get("status") != "complete"
            or summary.get("accepted_semantic_mismatches") != 0):
        raise ValueError("invalid retained C5 dependency")
    for relative, expected in manifest.get("files_sha256", {}).items():
        if sha(base / relative) != expected:
            raise ValueError(f"retained C5 artifact changed: {relative}")
    for relative, expected in manifest.get("source_sha256", {}).items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"retained C5 source changed: {relative}")
    return {"path": _relative(base), "manifest_sha256": sha(manifest_path),
            "dataset_sha256": manifest["files_sha256"]["dataset.json"]}


def percentile(values: list[int], quantile: float) -> int:
    if not values:
        raise ValueError("cannot take percentile of empty values")
    ordered = sorted(values)
    return ordered[round(quantile * (len(ordered) - 1))]


def _gate_selection(documents: list[dict[str, Any]], quantile: float, check: Callable[[], None]):
    rows = []
    for row in documents:
        if row["split"] not in {"train", "validation"}:
            continue
        check()
        polynomial, stats = source_anf_packed(row["expression_v2"], row["n_vars"])
        rows.append({"case_id": row["case_id"], "split": row["split"], "n_vars": row["n_vars"],
            "terms": polynomial.bit_count(), **stats.to_dict()})
    validation = [row["executed_product_pairs"] for row in rows if row["split"] == "validation"]
    threshold = max(1, percentile(validation, quantile))
    return {"schema": "crse-natural-source-anf-gate-selection/v1",
        "selection_split": "validation", "selection_quantile": quantile,
        "product_pair_budget": threshold, "profiles": rows,
        "validation_profile": {"cases": len(validation), "minimum": min(validation),
            "median": statistics.median(validation), "selected_quantile": threshold,
            "maximum": max(validation)}}


def _execute(method: str, row: dict[str, Any], cache: ProductCache | None, gate: int):
    document, n_vars = row["expression_v2"], row["n_vars"]
    started = time.perf_counter_ns()
    stats = None
    path = method
    witness = None
    if method == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
    elif method == "packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars)
    elif method == "cached_packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars, cache=cache)
    elif method == "budgeted_hybrid":
        partition, path, stats = source_hybrid_partition(
            document, n_vars, cache=cache, product_pair_budget=gate
        )
    elif method == "truth_vector_anf":
        bits = reference_bits(expr_from_json(document), n_vars)
        analysis = analyze_decomposition(bits, n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    else:
        raise ValueError("unknown natural source ANF method")
    proposed_at = time.perf_counter_ns()
    fallback_exact = method == "budgeted_hybrid" and path == "truth_vector_anf_fallback"
    if method != "truth_vector_anf" and not fallback_exact:
        if partition is not None:
            bits = reference_bits(expr_from_json(document), n_vars)
            witness = partition_witness(bits, n_vars, partition)
    checked = time.perf_counter_ns()
    canonical_partition = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and (witness is not None or fallback_exact)
    return {"method": method, "path": path, "split": row["split"], "case_id": row["case_id"],
        "matched_pair_id": row["matched_pair_id"], "circuit": row["circuit"], "variant": row["variant"],
        "n_vars": n_vars, "label": row["label"], "row_variables": list(partition) if partition is not None else None,
        "predicted": int(partition is not None), "accepted": accepted,
        "canonical_partition_match": partition == canonical_partition,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "signature_ns": proposed_at - started, "exact_check_ns": checked - proposed_at,
        "total_ns": checked - started,
        "truth_sha256": row["semantic_sha256"],
        "instrumentation": stats.to_dict() if stats is not None else None}


def _benchmark(documents: list[dict[str, Any]], config: NaturalSourceAnfConfig, gate: int,
               check: Callable[[], None]):
    samples: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    cache_telemetry = []
    for split in ("train", "validation", "test", "confirmatory"):
        split_rows = [row for row in documents if row["split"] == split]
        for repetition in range(config.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                check()
                cache = ProductCache(config.cache_capacity) if method in {
                    "cached_packed_source_anf", "budgeted_hybrid"} else None
                evictions_before = cache.evictions if cache is not None else 0
                for row in split_rows:
                    samples[(method, row["case_id"])].append(_execute(method, row, cache, gate))
                if cache is not None:
                    cache_telemetry.append({"method": method, "split": split, "repetition": repetition,
                        "final_entries": len(cache), "evictions": cache.evictions - evictions_before})
    aggregated = []
    for key in sorted(samples):
        values = samples[key]
        if len(values) != config.repetitions:
            raise ValueError("incomplete source ANF timing repetitions")
        representative = values[0]
        for field in ("path", "row_variables", "predicted", "accepted", "canonical_partition_match",
                      "semantic_mismatch", "truth_sha256", "instrumentation"):
            if any(value[field] != representative[field] for value in values[1:]):
                raise ValueError(f"nondeterministic source ANF result: {key}/{field}")
        aggregated.append({**representative,
            "signature_ns": int(statistics.median(value["signature_ns"] for value in values)),
            "exact_check_ns": int(statistics.median(value["exact_check_ns"] for value in values)),
            "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "timing_repetitions": config.repetitions})
    return aggregated, cache_telemetry


def _summaries(rows: list[dict[str, Any]]):
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["split"])].append(row)
    result = {}
    for (method, split), values in sorted(grouped.items()):
        totals = [row["total_ns"] for row in values]
        signatures = [row["signature_ns"] for row in values]
        result[f"{method}/{split}"] = {"cases": len(values),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "accepted": sum(row["accepted"] for row in values),
            "fallbacks": sum(row["path"] == "truth_vector_anf_fallback" for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values),
            "median_signature_ns": statistics.median(signatures), "p95_signature_ns": percentile(signatures, .95),
            "maximum_signature_ns": max(signatures), "median_total_ns": statistics.median(totals),
            "p95_total_ns": percentile(totals, .95), "maximum_total_ns": max(totals)}
    return result


def _criteria(summary: dict[str, Any], rows: list[dict[str, Any]], cache_telemetry: list[dict[str, Any]]):
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    median_speed = all(
        summary[f"truth_vector_anf/{split}"]["median_total_ns"] /
        summary[f"budgeted_hybrid/{split}"]["median_total_ns"] >= 1.10
        for split in ("test", "confirmatory"))
    p95_tail = all(summary[f"budgeted_hybrid/{split}"]["p95_total_ns"] <=
                   summary[f"truth_vector_anf/{split}"]["p95_total_ns"]
                   for split in ("test", "confirmatory"))
    fallback_rows = [row for row in rows if row["path"] == "truth_vector_anf_fallback"]
    fallback = bool(fallback_rows) and all(row["predicted"] == row["label"]
                                           and row["canonical_partition_match"] for row in fallback_rows)
    telemetry = bool(cache_telemetry) and all(
        all(field in values for field in ("maximum_total_ns", "p95_total_ns", "fallbacks"))
        for values in summary.values())
    def exact_cost(method: str) -> bool:
        return all(
            summary[f"truth_vector_anf/{split}"]["median_total_ns"] /
            summary[f"{method}/{split}"]["median_total_ns"] >= 1.10
            and summary[f"{method}/{split}"]["p95_total_ns"] <=
            summary[f"truth_vector_anf/{split}"]["p95_total_ns"]
            for split in ("test", "confirmatory")
        )
    return {"exact": exact, "median_speed": median_speed, "p95_tail": p95_tail,
        "fallback": fallback, "telemetry": telemetry,
        "packed_core": exact and exact_cost("packed_source_anf"),
        "cached_packed_core": exact and exact_cost("cached_packed_source_anf"),
        "source_hybrid": exact and median_speed and p95_tail and fallback,
        "safety": False, "production_promotion": False}


def run_natural_source_anf_experiment(
    config: NaturalSourceAnfConfig,
    output: Path,
    scout: Path = DEFAULT_SCOUT,
    base: Path = DEFAULT_C5_RUN,
    progress=print,
) -> dict[str, Any]:
    config.validate()
    output, scout, base = output.resolve(), scout.resolve(), base.resolve()
    if output.exists():
        existing = {path.name for path in output.iterdir()}
        if existing - {"run_spec.json", "dataset.json"}:
            raise FileExistsError(f"refusing to overwrite non-preflight run directory: {output}")
    else:
        output.mkdir(parents=True)
    write_json(output / "run_spec.json", config.manifest(output, scout, base))
    before = source_fingerprints(scout)
    retained = verify_retained_c5(base)
    budget, started = Budget(config.max_seconds), time.perf_counter()
    status = "running"
    try:
        progress("regenerating frozen matched EPFL dataset")
        documents, provenance = make_matched_natural_documents(
            scout, seed=config.dataset_seed, check=budget.check
        )
        write_json(output / "dataset.json", documents)
        if sha(output / "dataset.json") != retained["dataset_sha256"]:
            raise ValueError("regenerated dataset differs from retained C5 dataset")
        write_json(output / "dataset_provenance.json", provenance)
        progress("freezing product budget from validation complexity only")
        gate = _gate_selection(documents, config.validation_gate_quantile, budget.check)
        write_json(output / "gate_selection.json", gate)
        progress("benchmarking five exact paths with cold-start-charged repetitions")
        rows, cache_telemetry = _benchmark(
            documents, config, gate["product_pair_budget"], budget.check
        )
        summaries = _summaries(rows)
        criteria = _criteria(summaries, rows, cache_telemetry)
        criteria["safety"] = criteria["exact"] and sum(
            row["semantic_mismatch"] for row in rows) == 0
        status = "complete"
    except TimeoutError:
        documents, provenance, gate, rows, cache_telemetry, summaries = [], {}, {}, [], [], {}
        criteria = {"exact": False, "median_speed": False, "p95_tail": False,
            "fallback": False, "telemetry": False, "packed_core": False,
            "cached_packed_core": False, "source_hybrid": False,
            "safety": False, "production_promotion": False}
        status = "timeout"
    result = {"schema": RUN_SCHEMA, "status": status, "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c5": retained, "dataset_rows": len(documents), "gate_selection": gate,
        "method_summary": summaries, "cache_telemetry": cache_telemetry, "criteria": criteria,
        "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows),
        "source_unchanged": before == source_fingerprints(scout)}
    with (output / "benchmark_raw.jsonl").open("wb") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ["run_spec.json", "dataset.json", "dataset_provenance.json", "gate_selection.json",
             "benchmark_raw.jsonl", "summary.json", "report.md"]
    manifest = {"schema": "crse-natural-source-anf-hybrid-artifacts/v1", "status": status,
        "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before, "retained_c5_manifest_sha256": retained["manifest_sha256"]}
    write_json(output / "manifest.json", manifest)
    return result


def render_report(result: dict[str, Any]) -> str:
    lines = ["# Natural source ANF hybrid run", "", f"Status: **{result['status']}**", "",
        f"Validation-frozen product-pair budget: **{result.get('gate_selection', {}).get('product_pair_budget', 'n/a')}**.", "",
        "| Method / split | Median total ns | p95 total ns | Maximum total ns | Fallbacks |", "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result.get("method_summary", {}).items():
        lines.append(f"| {key} | {values['median_total_ns']:.0f} | {values['p95_total_ns']:.0f} | {values['maximum_total_ns']:.0f} | {values['fallbacks']} |")
    lines += ["", "All paths are exact. Source proposals are accepted only at the retained exact boundary; budget refusal switches to truth-vector ANF.", "",
        f"Criteria: `{json.dumps(result.get('criteria', {}), sort_keys=True)}`", ""]
    return "\n".join(lines)
