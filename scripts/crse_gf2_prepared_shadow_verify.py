"""Independently verify C32 served-baseline shadow evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_shadow_experiment import (
    DISABLED,
    ENABLED,
    C32Config,
    build_schedule,
    summarize,
)
from cmbench.comparative.gf2_resident_session_experiment import N_VARS, case_sequence
from cmbench.comparative.gf2_table_experiment import build_oracles
from cmbench.recognition.gf2_prepared_support_context import prepare_support_policy_context
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = load(run / "manifest.json")
    spec = load(run / "run_spec.json")
    result = load(run / "results.json")
    controls = load(run / "functional_controls.json")
    if manifest.get("schema") != "crse-c32-shadow-run-manifest/v1":
        raise ValueError("C32 manifest schema mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C32 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C32 artifact fingerprint mismatch: {name}")

    input_fields = {
        "dataset_sha256": "dataset_path",
        "dataset_verification_sha256": "dataset_verification_path",
        "c27_policy_file_sha256": "c27_policy_path",
        "c22_policy_file_sha256": "c22_policy_path",
        "c31_final_sha256": "c31_final_path",
        "c31_adjudication_sha256": "c31_adjudication_path",
    }
    paths = {}
    for digest_field, path_field in input_fields.items():
        path = ROOT / spec[path_field]
        paths[path_field] = path
        if (
            sha256(path) != spec[digest_field]
            or sha256(path) != manifest["inputs"][digest_field]
        ):
            raise ValueError(f"C32 frozen input mismatch: {digest_field}")
    c31_final = load(paths["c31_final_path"])
    c31_adjudication = load(paths["c31_adjudication_path"])
    if (
        c31_final.get("status") != "pass"
        or c31_final.get("scientific_replication_complete") is not True
        or c31_adjudication.get("replication_admissible") is not True
        or c31_adjudication.get("eligible_for_separate_shadow_review") is not True
        or c31_adjudication.get("shadow_promotion") is not False
        or c31_adjudication.get("production_promotion") is not False
    ):
        raise ValueError("C32 C31 admission evidence changed")
    if (
        spec.get("methods") != [DISABLED, ENABLED]
        or spec.get("served_method") != "exact_screened_baseline"
        or spec.get("candidate_method") != "support_aware_c30_prepared"
        or spec.get("candidate_observed_only") is not True
        or any(spec.get(field) is not False for field in (
            "policy_refit", "training", "production_write",
            "shadow_promotion", "production_promotion"))
    ):
        raise ValueError("C32 shadow lifecycle contract mismatch")

    dataset = load(paths["dataset_path"])
    dataset_verification = load(paths["dataset_verification_path"])
    validate_dataset(dataset)
    if (
        len(dataset.get("cases", [])) != 48
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("scalar_oracle_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
    ):
        raise ValueError("C32 corpus verification mismatch")
    config = C32Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(dataset["cases"], config.oracle_config())
    if not functional["all_exact"]:
        raise ValueError("C32 exhaustive oracle replay failed")
    prepared = prepare_support_policy_context(
        paths["c27_policy_path"], paths["c22_policy_path"])
    recorded_prepared = load(run / "prepared_context.json")
    if (
        prepared.context_sha256 != spec["prepared_context_sha256"]
        or recorded_prepared.get("context_sha256") != prepared.context_sha256
        or recorded_prepared.get("c27_policy_sha256") != prepared.c27_policy_sha256
        or recorded_prepared.get("c22_policy_sha256") != prepared.c22_policy_sha256
        or recorded_prepared.get("c27_file_sha256") != prepared.c27_file_sha256
        or recorded_prepared.get("c22_file_sha256") != prepared.c22_file_sha256
    ):
        raise ValueError("C32 prepared context identity mismatch")

    disabled = controls.get("disabled", {})
    exception = controls.get("candidate_exception", {})
    refusal = controls.get("candidate_refusal", {})
    divergence = controls.get("candidate_divergence", {})
    if (
        controls.get("schema") != "crse-c32-shadow-boundary-controls/v1"
        or controls.get("all_passed") is not True
        or disabled.get("candidate_status") != "disabled"
        or disabled.get("baseline_exact_check_passed") is not True
        or exception.get("candidate_status") != "error"
        or exception.get("shadow_failure_contained") is not True
        or refusal.get("candidate_status") != "refused"
        or refusal.get("shadow_failure_contained") is not True
        or divergence.get("candidate_status") != "observed"
        or divergence.get("candidate_best_identity_match") is not False
        or divergence.get("shadow_divergence_detected") is not True
        or divergence.get("shadow_failure_contained") is not True
        or controls.get("wrong_context_binding") != "refused"
        or controls.get("changed_policy_source") != "refused"
        or any(controls.get(field) != 0 for field in (
            "served_candidate_results", "production_writes",
            "shadow_promotions", "production_promotions"))
    ):
        raise ValueError("C32 functional controls mismatch")

    schedule = build_schedule(config)
    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(schedule):
        raise ValueError("C32 measurement cardinality mismatch")
    cases_by_width = {
        n_vars: sorted(
            (case for case in dataset["cases"] if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    served_queries = shadow_observations = 0
    for row, planned in zip(rows, schedule):
        if any(row.get(field) != value for field, value in planned.items()):
            raise ValueError("C32 counterbalanced schedule mismatch")
        expected_cases = case_sequence(
            cases_by_width, row["n_vars"], config.query_count, row["block"])
        records = row.get("query_records")
        if (
            not isinstance(records, list)
            or len(records) != config.query_count
            or [record.get("case_id") for record in records]
            != [case["case_id"] for case in expected_cases]
        ):
            raise ValueError("C32 query sequence mismatch")
        for request_index, (record, case) in enumerate(zip(records, expected_cases)):
            expected_digest = oracles[case["case_id"]]["delivered_sha256"]
            if (
                record.get("request_index") != request_index
                or record.get("n_vars") != case["n_vars"]
                or record.get("status") != "served_baseline"
                or record.get("served_output_source") != "exact_screened_baseline"
                or record.get("served_selected_arm") != "explicit_cm_screened"
                or record.get("served_artifact_sha256") != expected_digest
                or record.get("baseline_exact_check_passed") is not True
                or record.get("candidate_observed_only") is not True
                or record.get("production_write") is not False
                or record.get("shadow_promotion") is not False
                or record.get("production_promotion") is not False
                or record.get("shadow_divergence_detected") is not False
                or record.get("shadow_failure_contained") is not False
            ):
                raise ValueError("C32 served-baseline record mismatch")
            if row["method"] == DISABLED:
                if (
                    record.get("shadow_enabled") is not False
                    or record.get("candidate_status") != "disabled"
                    or any(record.get(field) is not None for field in (
                        "candidate_selected_arm", "candidate_artifact_sha256",
                        "candidate_context_sha256", "candidate_best_identity_match",
                        "candidate_error_type", "candidate_refusal_reason"))
                ):
                    raise ValueError("C32 disabled record performed shadow work")
            else:
                if (
                    record.get("shadow_enabled") is not True
                    or record.get("candidate_status") != "observed"
                    or record.get("candidate_artifact_sha256") != expected_digest
                    or record.get("candidate_context_sha256") is None
                    or record.get("candidate_best_identity_match") is not True
                    or record.get("candidate_error_type") is not None
                    or record.get("candidate_refusal_reason") is not None
                ):
                    raise ValueError("C32 enabled record mismatch")
                shadow_observations += 1
            served_queries += 1

    summary = summarize(rows, controls)
    if (
        result.get("schema") != "crse-c32-prepared-policy-shadow-experiment/v1"
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("summary") != summary
        or result.get("functional_controls_passed") is not True
        or result.get("semantic_or_artifact_mismatches") != 0
        or any(result.get(field) is not False for field in (
            "policy_refit", "training", "production_write",
            "shadow_promotion", "production_promotion"))
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or served_queries != 1024
        or shadow_observations != 512
        or summary.get("shadow_review_gate") is not True
        or summary.get("timing_is_observational_not_a_promotion_gate") is not True
    ):
        raise ValueError("C32 result or recomputed summary mismatch")

    verification = {
        "schema": "crse-c32-independent-verification/v1",
        "status": "verified",
        "input_files_checked": len(input_fields),
        "source_files_checked": len(manifest["sources"]),
        "artifact_files_checked": len(manifest["artifacts"]),
        "measurement_batches_checked": len(rows),
        "paired_batches_checked": summary["paired_batches"],
        "served_exact_queries_replayed": served_queries,
        "shadow_candidate_observations_replayed": shadow_observations,
        "functional_controls_replayed": 6,
        "semantic_or_artifact_mismatches": 0,
        "candidate_results_served": 0,
        "production_writes": 0,
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
