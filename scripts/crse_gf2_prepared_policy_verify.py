"""Independently verify C30 prepared-policy safety, exactness, and charged timing."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_policy_experiment import (
    BASELINE,
    CANDIDATE,
    C30Config,
    METHODS,
    QUERY_COUNT,
    build_schedule,
    summarize,
)
from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    N_VARS,
    case_sequence,
)
from cmbench.comparative.gf2_table_experiment import build_oracles
from cmbench.recognition.gf2_prepared_support_context import (
    prepare_support_policy_context,
    verify_prepared_policy_sources,
)
from cmbench.recognition.gf2_source_portfolio import load_source_portfolio_policy
from cmbench.recognition.gf2_support_aware_policy import (
    load_support_aware_policy,
    select_support_arm,
)
from cmbench.recognition.gf2_support_aware_session import SupportAwareGF2Session
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
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
    if manifest.get("schema") != "crse-c30-run-manifest/v1":
        raise ValueError("C30 manifest schema mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C30 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C30 artifact fingerprint mismatch: {name}")

    input_fields = {
        "dataset_sha256": "dataset_path",
        "dataset_verification_sha256": "dataset_verification_path",
        "c27_policy_file_sha256": "c27_policy_path",
        "c22_policy_file_sha256": "c22_policy_path",
        "c19_policy_file_sha256": "c19_policy_path",
    }
    paths = {}
    for digest_field, path_field in input_fields.items():
        path = ROOT / spec[path_field]
        paths[path_field] = path
        if (
            sha256(path) != spec[digest_field]
            or sha256(path) != manifest["inputs"][digest_field]
        ):
            raise ValueError(f"C30 frozen input mismatch: {digest_field}")
    c29_run = ROOT / spec["c29_run_path"]
    if (
        sha256(c29_run / "results.json") != spec["c29_results_sha256"]
        or sha256(c29_run / "results.json") != manifest["inputs"]["c29_results_sha256"]
        or sha256(c29_run / "independent_verification.json")
        != spec["c29_independent_verification_sha256"]
        or sha256(c29_run / "independent_verification.json")
        != manifest["inputs"]["c29_independent_verification_sha256"]
        or load(c29_run / "independent_verification.json").get("status") != "verified"
    ):
        raise ValueError("C30 C29 source evidence changed")
    if (
        spec.get("methods") != list(METHODS)
        or spec.get("query_count") != QUERY_COUNT
        or spec.get("lifecycle_preparation_fully_charged") is not True
        or spec.get("unchanged_c29_schedule") is not True
        or spec.get("unchanged_exact_query_path") is not True
        or spec.get("policy_refit") is not False
        or spec.get("training") is not False
        or spec.get("shadow_promotion") is not False
        or spec.get("production_promotion") is not False
    ):
        raise ValueError("C30 lifecycle contract mismatch")

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
        raise ValueError("C30 corpus verification mismatch")
    c27_policy = load_support_aware_policy(paths["c27_policy_path"])
    c22_policy = load_source_portfolio_policy(paths["c22_policy_path"])
    if (
        c27_policy["policy_sha256"] != spec["c27_policy_sha256"]
        or c22_policy["policy_sha256"] != spec["c22_policy_sha256"]
    ):
        raise ValueError("C30 policy identity mismatch")
    prepared = prepare_support_policy_context(
        paths["c27_policy_path"], paths["c22_policy_path"])
    verify_prepared_policy_sources(prepared)
    recorded_prepared = load(run / "prepared_context.json")
    if (
        recorded_prepared.get("schema") != prepared.schema
        or recorded_prepared.get("context_sha256") != prepared.context_sha256
        or recorded_prepared.get("c27_policy_sha256") != prepared.c27_policy_sha256
        or recorded_prepared.get("c22_policy_sha256") != prepared.c22_policy_sha256
        or recorded_prepared.get("c27_file_sha256") != prepared.c27_file_sha256
        or recorded_prepared.get("c22_file_sha256") != prepared.c22_file_sha256
        or recorded_prepared.get("preparation_ns") != spec["lifecycle_preparation_ns"]
        or recorded_prepared.get("context_sha256") != spec["prepared_context_sha256"]
    ):
        raise ValueError("C30 prepared context identity mismatch")

    controls = load(run / "functional_controls.json")
    changed_c27 = run / "control_changed_source_c27.json"
    changed_c22 = run / "control_changed_source_c22.json"
    if (
        controls.get("schema") != "crse-c30-prepared-context-controls/v1"
        or controls.get("all_passed") is not True
        or controls.get("exact_controls_passed") is not True
        or controls.get("refusal_controls_passed") is not True
        or set(controls.get("refusals", {}).values()) != {"refused"}
        or sha256(changed_c27) == prepared.c27_file_sha256
        or sha256(changed_c22) != prepared.c22_file_sha256
        or load(changed_c27) != c27_policy
        or load(changed_c22) != c22_policy
    ):
        raise ValueError("C30 changed-source control mismatch")
    for path, loader in (
        (run / "control_tampered_c27.json", load_support_aware_policy),
        (run / "control_tampered_c22.json", load_source_portfolio_policy),
    ):
        try:
            loader(path)
        except ValueError:
            pass
        else:
            raise ValueError("C30 tampered policy control was accepted")
    try:
        SupportAwareGF2Session(
            "c30-independent-wrong-bind", None, None,
            prepared_context=prepared, required_prepared_context_sha256="0" * 64)
    except ValueError:
        pass
    else:
        raise ValueError("C30 wrong prepared-context binding was accepted")

    config = C30Config(**spec["config"])
    config.validate()
    schedule = build_schedule(config)
    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(schedule):
        raise ValueError("C30 measurement count mismatch")
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
        raise ValueError("C30 independent oracle replay failed")

    timed_query_records = 0
    contexts_replayed = 0
    for row, planned in zip(rows, schedule):
        if any(row.get(field) != value for field, value in planned.items()):
            raise ValueError("C30 counterbalanced schedule mismatch")
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
            raise ValueError("C30 batch timing, schedule, or exactness mismatch")
        if row["method"] == CANDIDATE:
            if row.get("prepared_context_sha256") != prepared.context_sha256:
                raise ValueError("C30 candidate context binding mismatch")
            setup = row.get("setup_detail")
            if (
                not isinstance(setup, dict)
                or set(setup) != {
                    "prepared_context_bind_ns", "session_initialize_ns", "setup_total_ns"}
                or setup["setup_total_ns"]
                != setup["prepared_context_bind_ns"] + setup["session_initialize_ns"]
            ):
                raise ValueError("C30 prepared setup decomposition mismatch")
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
                raise ValueError("C30 exact artifact or selected-arm mismatch")
            if row["method"] == CANDIDATE:
                context = build_verified_gf2_context(
                    case, require_source_packed=row["n_vars"] >= 5)
                verify_verified_gf2_context(context.to_dict(), case, replay_semantics=True)
                if (
                    record.get("context_sha256") != context.context_sha256
                    or record.get("expression_sha256") != context.expression_sha256
                    or record.get("truth_sha256") != context.truth_sha256
                ):
                    raise ValueError("C30 verified context mismatch")
                contexts_replayed += 1
            timed_query_records += 1

    summary = summarize(rows, lifecycle_preparation_ns=spec["lifecycle_preparation_ns"])
    c29_result = load(c29_run / "results.json")
    expected_comparison = {
        "source_run": spec["c29_run_path"],
        "source_results_sha256": spec["c29_results_sha256"],
        "by_width": {
            str(n_vars): {
                "c29_total_speedup": c29_result["summary"]["by_width"][str(n_vars)][
                    "ratio_of_median_total_speedup"],
                "c30_charged_total_speedup": summary["by_width"][str(n_vars)][
                    "ratio_of_median_charged_total_speedup"],
                "relative_speedup_improvement": (
                    summary["by_width"][str(n_vars)][
                        "ratio_of_median_charged_total_speedup"]
                    / c29_result["summary"]["by_width"][str(n_vars)][
                        "ratio_of_median_total_speedup"]),
            }
            for n_vars in N_VARS
        },
    }
    if (
        result.get("schema") != "crse-c30-prepared-support-policy-experiment/v1"
        or result.get("status") != "complete"
        or result.get("dataset_cases") != 48
        or result.get("summary") != summary
        or result.get("c29_comparison") != expected_comparison
        or result.get("functional_controls_passed") is not True
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("development_evidence") is not True
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or summary.get("measurement_batches") != 128
        or summary.get("paired_batches") != 64
        or summary.get("timed_queries") != 1024
        or summary.get("lifecycle_preparation_charge_conserved") is not True
        or summary.get("arm_order_balanced") is not True
        or summary.get("width_position_balanced") is not True
        or summary.get("exactness_gate") is not True
    ):
        raise ValueError("C30 result or recomputed summary mismatch")

    verification = {
        "schema": "crse-c30-independent-verification/v1",
        "status": "verified",
        "input_files_checked": len(input_fields) + 2,
        "source_files_checked": len(manifest["sources"]),
        "artifact_files_checked": len(manifest["artifacts"]),
        "measurement_batches_checked": len(rows),
        "paired_batches_checked": summary["paired_batches"],
        "timed_query_records_checked": timed_query_records,
        "verified_context_records_replayed": contexts_replayed,
        "preparation_charge_recomputed_ns": summary["lifecycle_preparation_ns"],
        "preparation_charge_conserved": True,
        "functional_controls_replayed": 6,
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
