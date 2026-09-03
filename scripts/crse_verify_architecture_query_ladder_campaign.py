"""Independent verifier for the corrected architecture query-ladder run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import architecture_comparison_campaign as parent
from cmbench.comparative.architecture_query_ladder_followup import (
    MEMORY_METHOD,
    RAW_SCHEMA,
    RESULT_SCHEMA,
    STAGES,
    VERIFICATION_SCHEMA,
    expected_schedule_rows,
    verify_followup_freeze,
)


DEFAULT_FREEZE = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
)
DEFAULT_ORACLES = (
    ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def verify(run_dir: Path, freeze_path: Path, oracles_path: Path) -> dict[str, Any]:
    run = run_dir.resolve()
    _require(run.is_relative_to(ROOT) and run.is_dir(), "query-ladder run directory")
    verification_path = run / "independent_verification.json"
    _require(not verification_path.exists(), "refusing to overwrite query-ladder verification")
    freeze = _load(freeze_path)
    verify_followup_freeze(freeze, ROOT)
    parent_freeze = _load(ROOT / freeze["parent_freeze"]["path"])
    oracles = _load(oracles_path)
    parent.validate_oracles(oracles, ROOT, parent_freeze)
    results_path = run / "results.json"
    raw_path = run / "raw_measurements.jsonl"
    results = _load(results_path)
    _require(results.get("schema") == RESULT_SCHEMA and results.get("status") == "complete", "query-ladder result")
    _require(
        results.get("freeze_sha256") == _sha256(freeze_path)
        and results.get("oracles_sha256") == _sha256(oracles_path)
        and results.get("raw_measurements_sha256") == _sha256(raw_path),
        "query-ladder result bindings",
    )
    expected = expected_schedule_rows(freeze)
    query_rows = {str(query_count): 0 for query_count in freeze["schedule"]["query_counts"]}
    rows = 0
    with raw_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                planned = next(expected)
            except StopIteration as exc:
                raise ValueError("unexpected extra query-ladder row") from exc
            row = json.loads(line)
            _require(row.get("schema") == RAW_SCHEMA, "query-ladder raw schema")
            for key, value in planned.items():
                _require(row.get(key) == value, f"query-ladder schedule mismatch at row {rows}: {key}")
            timings = row.get("timings_ns", {})
            _require(
                set(timings) == {*STAGES, "accounted_total_ns"}
                and all(type(timings[stage]) is int and timings[stage] >= 0 for stage in STAGES)
                and timings["accounted_total_ns"] == sum(timings[stage] for stage in STAGES)
                and timings["accounted_total_ns"] > 0,
                "query-ladder timing accounting",
            )
            expected_output = oracles["lanes"]["B"][row["case_id"]]["checkpoints"][str(row["query_count"])]
            _require(
                row.get("status") == "ok" and row.get("reason") == "completed"
                and row.get("exact_check_passed") is True
                and row.get("output_sha256") == expected_output
                and row.get("resources", {}).get("queries") == row["query_count"],
                "query-ladder exact output",
            )
            memory = row.get("memory_measurement", {})
            peak = memory.get("peak_rss_bytes")
            baseline = memory.get("inherited_baseline_rss_bytes")
            _require(
                memory.get("method") == MEMORY_METHOD
                and memory.get("interpretation_permitted") is True
                and memory.get("child_exit_code") == 0
                and type(memory.get("isolation_lifecycle_ns")) is int
                and memory["isolation_lifecycle_ns"] >= timings["accounted_total_ns"]
                and memory.get("isolation_lifecycle_in_accounted_timing") is False
                and type(peak) is int and peak > 0
                and type(baseline) is int and baseline > 0
                and memory.get("incremental_peak_rss_bytes") == max(0, peak - baseline),
                "query-ladder isolated memory measurement",
            )
            _require(
                row.get("cleanup_method") == "cache_clear_then_isolated_child_exit",
                "query-ladder isolated cleanup method",
            )
            query_rows[str(row["query_count"])] += 1
            rows += 1
    try:
        next(expected)
    except StopIteration:
        pass
    else:
        raise ValueError("query-ladder output ended before schedule")
    planned_rows = freeze["schedule"]["planned_cells"]
    per_query = planned_rows // len(freeze["schedule"]["query_counts"])
    _require(
        rows == planned_rows == results["expected_rows"]
        and results["counts"] == {"ok": planned_rows, "refused": 0, "failed": 0}
        and all(value == per_query for value in query_rows.values()),
        "query-ladder cardinality",
    )
    binding = _load(run / "runtime_binding.json")
    _require(
        binding.get("role") == "decision_bearing_linux_query_ladder_followup"
        and binding.get("native_library_sha256") == results["native_library_sha256"],
        "query-ladder runtime binding",
    )
    decision = results.get("decision", {})
    _require(
        decision.get("performance_interpretation_deferred_to_independent_verifier") is True
        and decision.get("memory_interpretation_deferred_to_independent_verifier") is True
        and all(decision.get(key) is False for key in (
            "selector_fitted", "neural_training", "production_routing_changed", "website_updated"
        )),
        "query-ladder decision boundary",
    )
    document = {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified_complete",
        "freeze_sha256": _sha256(freeze_path),
        "oracles_sha256": _sha256(oracles_path),
        "results_sha256": _sha256(results_path),
        "raw_measurements_sha256": _sha256(raw_path),
        "runtime_binding_sha256": _sha256(run / "runtime_binding.json"),
        "rows_checked": rows,
        "query_rows": query_rows,
        "counts": results["counts"],
        "semantic_mismatches": 0,
        "schedule_mismatches": 0,
        "source_or_artifact_mismatches": 0,
        "memory_measurement_mismatches": 0,
        "all_query_counts_separately_timed": True,
        "all_cells_isolated_for_memory": True,
        "performance_interpretation_permitted": True,
        "descriptive_host_memory_interpretation_permitted": True,
        "cross_machine_claim_permitted": False,
        "website_update_permitted": False,
        "selector_or_neural_claim_permitted": False,
    }
    _write_json(verification_path, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--oracles", type=Path, default=DEFAULT_ORACLES)
    args = parser.parse_args()
    result = verify(args.run_dir, args.freeze.resolve(), args.oracles.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
