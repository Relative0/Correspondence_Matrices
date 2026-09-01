"""Independently verify C29 inputs, schedule, exact outputs, and timing summaries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    N_VARS,
    case_sequence,
)
from cmbench.comparative.gf2_table_experiment import build_oracles
from cmbench.comparative.gf2_variance_localization import (
    BASELINE,
    CANDIDATE,
    C29Config,
    METHODS,
    QUERY_COUNT,
    build_schedule,
    localize_frozen_executions,
    summarize_interleaved,
)
from cmbench.recognition.gf2_support_aware_policy import (
    load_support_aware_policy,
    select_support_arm,
)
from cmbench.recognition.gf2_task_dispatcher import SCREENED
from cmbench.recognition.gf2_verified_context import (
    build_verified_gf2_context,
    verify_verified_gf2_context,
)
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = load(run / "manifest.json")
    spec = load(run / "run_spec.json")
    result = load(run / "results.json")
    if manifest.get("schema") != "crse-c29-run-manifest/v1":
        raise ValueError("C29 manifest schema mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C29 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C29 artifact fingerprint mismatch: {name}")

    input_fields = {
        "dataset_sha256": "dataset_path",
        "dataset_verification_sha256": "dataset_verification_path",
        "c27_policy_file_sha256": "c27_policy_path",
        "c22_policy_file_sha256": "c22_policy_path",
        "c19_policy_file_sha256": "c19_policy_path",
        "c28_input_manifest_sha256": "c28_input_manifest_path",
    }
    paths = {}
    for digest_field, path_field in input_fields.items():
        path = ROOT / spec[path_field]
        paths[path_field] = path
        if (
            sha256(path) != spec[digest_field]
            or sha256(path) != manifest["inputs"][digest_field]
        ):
            raise ValueError(f"C29 frozen input fingerprint mismatch: {digest_field}")
    if (
        spec.get("methods") != list(METHODS)
        or spec.get("query_count") != QUERY_COUNT
        or spec.get("adjacent_pairing") is not True
        or spec.get("method_order_counterbalanced") is not True
        or spec.get("width_position_counterbalanced") is not True
        or spec.get("component_timing_retained") is not True
        or spec.get("policy_refit") is not False
        or spec.get("training") is not False
        or spec.get("shadow_promotion") is not False
        or spec.get("production_promotion") is not False
    ):
        raise ValueError("C29 diagnostic lifecycle contract mismatch")

    dataset = load(paths["dataset_path"])
    dataset_verification = load(paths["dataset_verification_path"])
    validate_dataset(dataset)
    if (
        len(dataset.get("cases", [])) != 48
        or dataset.get("provenance", {}).get("policy_frozen_before_dataset") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("scalar_oracle_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
    ):
        raise ValueError("C29 frozen corpus verification mismatch")
    c27_policy = load_support_aware_policy(paths["c27_policy_path"])
    if c27_policy["policy_sha256"] != spec["c27_policy_sha256"]:
        raise ValueError("C29 C27 policy identity mismatch")

    c28_manifest = load(paths["c28_input_manifest_path"])
    executions = []
    files_checked = 0
    frozen_rows_checked = 0
    for source in c28_manifest["executions"]:
        measurement_path = ROOT / source["path"] / "measurements.jsonl"
        frozen_file = source["files"]["measurements.jsonl"]
        if (
            sha256(measurement_path) != frozen_file["sha256"]
            or measurement_path.stat().st_size != frozen_file["bytes"]
        ):
            raise ValueError("C29 source C27 measurement changed")
        source_rows = load_rows(measurement_path)
        frozen_rows_checked += len(source_rows)
        files_checked += 1
        executions.append({
            "execution_id": source["execution_id"],
            "physical_machine_id": source["physical_machine_id"],
            "environment": source["environment"],
            "rows": source_rows,
        })
    frozen = localize_frozen_executions(executions)
    if frozen != load(run / "frozen_localization.json"):
        raise ValueError("C29 frozen q8 localization recomputation mismatch")

    config = C29Config(**spec["config"])
    config.validate()
    schedule = build_schedule(config)
    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(schedule):
        raise ValueError("C29 measurement count mismatch")
    cases = dataset["cases"]
    cases_by_width = {
        n_vars: sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise ValueError("C29 independent exhaustive oracle replay failed")

    timed_query_records = 0
    context_records_replayed = 0
    for row, planned in zip(rows, schedule):
        if any(row.get(field) != value for field, value in planned.items()):
            raise ValueError("C29 counterbalanced schedule mismatch")
        timings = row.get("timings_ns")
        records = row.get("query_records")
        expected_cases = case_sequence(
            cases_by_width, row["n_vars"], QUERY_COUNT, row["block"])
        if (
            row.get("status") != "ok"
            or row.get("exact_check_passed") is not True
            or row.get("query_count") != QUERY_COUNT
            or not isinstance(timings, dict)
            or set(timings) != {*BATCH_TIMING_FIELDS, "batch_total_ns"}
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["batch_total_ns"] != sum(timings[field] for field in BATCH_TIMING_FIELDS)
            or row.get("amortized_query_ns") != timings["batch_total_ns"] / QUERY_COUNT
            or not isinstance(records, list)
            or len(records) != QUERY_COUNT
            or [record.get("case_id") for record in records]
            != [case["case_id"] for case in expected_cases]
        ):
            raise ValueError("C29 batch timing, schedule, or exactness mismatch")
        for index, (record, case) in enumerate(zip(records, expected_cases)):
            oracle = oracles[case["case_id"]]
            expected_selected = (
                SCREENED if row["method"] == BASELINE
                else select_support_arm(c27_policy, row["n_vars"], advice_enabled=True)
            )
            expected_cache = None if row["method"] == BASELINE else index > 0
            if (
                record.get("artifact_sha256") != oracle["delivered_sha256"]
                or record.get("best_artifact_sha256") != (
                    oracle["best_artifact"]["payload_sha256"]
                    if oracle["best_artifact"] else None)
                or record.get("selected_arm") != expected_selected
                or record.get("compile_cache_hit") is not expected_cache
                or record.get("exact_check_passed") is not True
                or type(record.get("elapsed_ns")) is not int
                or record["elapsed_ns"] < 1
            ):
                raise ValueError("C29 per-query exact artifact or selected-arm mismatch")
            if row["method"] == CANDIDATE:
                context = build_verified_gf2_context(
                    case, require_source_packed=row["n_vars"] >= 5)
                verify_verified_gf2_context(context.to_dict(), case, replay_semantics=True)
                if (
                    record.get("context_sha256") != context.context_sha256
                    or record.get("expression_sha256") != context.expression_sha256
                    or record.get("truth_sha256") != context.truth_sha256
                ):
                    raise ValueError("C29 verified-context digest mismatch")
                context_records_replayed += 1
            elif any(field in record for field in (
                    "context_sha256", "expression_sha256", "truth_sha256")):
                raise ValueError("C29 direct control gained fused context metadata")
            timed_query_records += 1

    summary = summarize_interleaved(rows)
    if (
        result.get("schema") != "crse-c29-gf2-variance-localization/v1"
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("frozen_executions_localized") != 5
        or result.get("frozen_physical_machines") != 2
        or result.get("frozen_paired_q8_cells") != 100
        or result.get("summary") != summary
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("diagnostic_only") is not True
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or summary.get("timed_queries") != 1024
        or summary.get("arm_order_balanced") is not True
        or summary.get("width_position_balanced") is not True
        or summary.get("exactness_gate") is not True
    ):
        raise ValueError("C29 result or summary recomputation mismatch")

    verification = {
        "schema": "crse-c29-independent-verification/v1",
        "status": "verified",
        "input_files_checked": len(input_fields) + files_checked,
        "source_files_checked": len(manifest["sources"]),
        "artifact_files_checked": len(manifest["artifacts"]),
        "frozen_c27_measurement_rows_checked": frozen_rows_checked,
        "frozen_q8_paired_cells_recomputed": frozen["paired_cells"],
        "measurement_batches_checked": len(rows),
        "paired_batches_checked": summary["paired_batches"],
        "timed_query_records_checked": timed_query_records,
        "verified_context_records_replayed": context_records_replayed,
        "semantic_or_artifact_mismatches": 0,
        "schedule_recomputed": True,
        "summary_recomputed": True,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
    }
    write(run / "independent_verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
