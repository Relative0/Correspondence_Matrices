"""Independent structural/exactness verifier for a completed four-lane run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_comparison_campaign import (
    ORACLE_SCHEMA,
    RAW_SCHEMA,
    RESULT_SCHEMA,
    STAGES,
    validate_oracles,
)
from cmbench.comparative.architecture_comparison_freeze import verify_freeze


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _expected_rows(freeze: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for lane in "ABC":
        schedule = freeze["schedules"][lane]
        for block, order in enumerate(schedule["arm_orders"]):
            for case_position, case_id in enumerate(schedule["case_order"]):
                for arm_position, arm in enumerate(order):
                    yield {
                        "lane": lane, "case_id": case_id, "arm": arm,
                        "block": block, "case_position": case_position,
                        "arm_position": arm_position, "arm_order": list(order),
                    }
    lane = "D"
    for sublane, schedule in freeze["schedules"][lane]["task_sublanes"].items():
        for block, order in enumerate(schedule["arm_orders"]):
            lifecycle = freeze["schedules"][lane]["task_lifecycles"][block % 2]
            for case_position, case_id in enumerate(schedule["case_order"]):
                for arm_position, backend in enumerate(order):
                    yield {
                        "lane": lane, "case_id": case_id,
                        "arm": f"{backend}/{lifecycle}", "sublane": sublane,
                        "block": block, "case_position": case_position,
                        "arm_position": arm_position, "arm_order": list(order),
                        "lifecycle_assignment": "block_parity_balanced",
                    }
    schedule = freeze["schedules"][lane]["structural_reload"]
    for block, order in enumerate(schedule["arm_orders"]):
        for case_position, case_id in enumerate(schedule["case_order"]):
            for arm_position, arm in enumerate(order):
                yield {
                    "lane": lane, "case_id": case_id, "arm": arm,
                    "sublane": "structural_reload", "block": block,
                    "case_position": case_position, "arm_position": arm_position,
                    "arm_order": list(order),
                }


def _expected_output(oracles: dict[str, Any], row: dict[str, Any]) -> tuple[str, str | None]:
    oracle = oracles["lanes"][row["lane"]][row["case_id"]]
    if oracle["status"] == "refused":
        return oracle["reason"], None
    if row["lane"] == "A":
        return "completed", oracle["truth"]["sha256"]
    if row["lane"] == "B":
        return "completed", oracle["checkpoints"]["64"]
    if row["lane"] == "C":
        return "completed", oracle["output_sha256"]
    return "completed", oracle["sublanes"][row["sublane"]]["output_sha256"]


def verify(run_dir: Path, freeze_path: Path, oracles_path: Path) -> dict[str, Any]:
    run = run_dir.resolve()
    _require(run.is_relative_to(ROOT) and run.is_dir(), "run directory")
    output_path = run / "independent_verification.json"
    _require(not output_path.exists(), "refusing to overwrite verification")
    freeze = _load(freeze_path)
    verify_freeze(freeze, ROOT)
    oracles = _load(oracles_path)
    _require(oracles.get("schema") == ORACLE_SCHEMA, "oracle schema")
    validate_oracles(oracles, ROOT, freeze)
    results = _load(run / "results.json")
    _require(results.get("schema") == RESULT_SCHEMA and results.get("status") == "complete", "result envelope")
    _require(
        results.get("freeze_sha256") == _sha256(freeze_path)
        and results.get("oracles_file_sha256") == _sha256(oracles_path)
        and results.get("raw_measurements_sha256") == _sha256(run / "raw_measurements.jsonl"),
        "result input/output binding",
    )
    expected = _expected_rows(freeze)
    counts = {"ok": 0, "refused": 0, "failed": 0}
    lane_counts = {lane: 0 for lane in "ABCD"}
    rows = 0
    with (run / "raw_measurements.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                planned = next(expected)
            except StopIteration as exc:
                raise ValueError("unexpected extra timed row") from exc
            row = json.loads(line)
            _require(row.get("schema") == RAW_SCHEMA, "raw schema")
            for key, value in planned.items():
                _require(row.get(key) == value, f"schedule mismatch at row {rows}: {key}")
            timings = row.get("timings_ns")
            _require(
                isinstance(timings, dict)
                and set(timings) == {*STAGES, "accounted_total_ns"}
                and all(type(timings[key]) is int and timings[key] >= 0 for key in STAGES)
                and timings["accounted_total_ns"] == sum(timings[key] for key in STAGES),
                "timing accounting",
            )
            reason, output = _expected_output(oracles, row)
            if output is None:
                _require(
                    row.get("status") == "refused"
                    and row.get("reason") == reason
                    and row.get("output_sha256") is None
                    and row.get("exact_check_passed") is False
                    and timings["accounted_total_ns"] == 0,
                    "refusal record",
                )
            else:
                _require(
                    row.get("status") == "ok"
                    and row.get("reason") == "completed"
                    and row.get("output_sha256") == output
                    and row.get("exact_check_passed") is True
                    and timings["accounted_total_ns"] > 0,
                    "exact completed record",
                )
                if row["lane"] == "B":
                    _require(
                        row.get("checkpoint_output_sha256")
                        == oracles["lanes"]["B"][row["case_id"]]["checkpoints"],
                        "lane B checkpoint output",
                    )
            counts[row["status"]] += 1
            lane_counts[row["lane"]] += 1
            rows += 1
    try:
        next(expected)
    except StopIteration:
        pass
    else:
        raise ValueError("timed output ended before frozen schedule")
    _require(
        rows == results["expected_rows"] == sum(results["counts"].values())
        and counts == results["counts"]
        and lane_counts == results["lane_rows"]
        and counts["failed"] == 0,
        "result cardinality",
    )
    binding = _load(run / "runtime_binding.json")
    _require(
        binding.get("role") == "decision_bearing_linux_campaign"
        and binding.get("native_library_sha256") == results["native_library_sha256"],
        "Linux runtime binding",
    )
    decision = results.get("decision", {})
    _require(
        decision.get("performance_interpretation_deferred_to_independent_verifier") is True
        and all(
            decision.get(key) is False
            for key in ("selector_fitted", "neural_training", "production_routing_changed", "website_updated")
        ),
        "decision boundary",
    )
    document = {
        "schema": "cm-architecture-comparison-independent-verification/v1",
        "status": "verified_complete",
        "freeze_sha256": _sha256(freeze_path),
        "oracles_sha256": _sha256(oracles_path),
        "results_sha256": _sha256(run / "results.json"),
        "raw_measurements_sha256": _sha256(run / "raw_measurements.jsonl"),
        "runtime_binding_sha256": _sha256(run / "runtime_binding.json"),
        "rows_checked": rows,
        "lane_rows": lane_counts,
        "counts": counts,
        "semantic_mismatches": 0,
        "schedule_mismatches": 0,
        "source_or_artifact_mismatches": 0,
        "unfavorable_and_refused_cells_retained": True,
        "performance_interpretation_permitted": True,
        "website_update_permitted": False,
        "selector_or_neural_claim_permitted": False,
    }
    _write_json(output_path, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--freeze", type=Path, default=ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json")
    parser.add_argument("--oracles", type=Path, default=ROOT / "docs/recognition/architecture_comparison_execution_20260903/ORACLES.json")
    args = parser.parse_args()
    result = verify(args.run_dir, args.freeze.resolve(), args.oracles.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
