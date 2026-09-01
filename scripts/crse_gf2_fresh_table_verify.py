"""Independent integrity and exactness verifier for the C23 fresh GF(2) table."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import validate_contract
from cmbench.comparative.gf2_fresh_table_experiment import (
    C23Config,
    _memory_cases,
    build_oracles,
    fresh_summary,
)
from cmbench.comparative.gf2_method_table import METHODS, TIMING_FIELDS
from cmbench.recognition.gf2_decomposition import candidate_partitions, truth_sha256
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_unused_gf2_data import validate_dataset


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the C23 fresh GF(2) table")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = (
        load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json"))
    dataset_path = ROOT / spec["dataset_path"]
    dataset_verification_path = ROOT / spec["dataset_verification_path"]
    policy_path = ROOT / spec["policy_path"]
    if (
        sha256(dataset_path) != manifest["dataset_sha256"]
        or sha256(dataset_path) != spec["dataset_sha256"]
        or sha256(dataset_verification_path) != manifest["dataset_verification_sha256"]
        or sha256(dataset_verification_path) != spec["dataset_verification_sha256"]
        or sha256(policy_path) != manifest["policy_file_sha256"]
        or sha256(policy_path) != spec["policy_file_sha256"]
    ):
        raise ValueError("C23 frozen input fingerprint mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C23 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C23 artifact fingerprint mismatch: {name}")
    dataset, dataset_verification = load(dataset_path), load(dataset_verification_path)
    validate_dataset(dataset)
    if (
        dataset.get("revision", {}).get("id") != "task-complete-v2"
        or dataset.get("provenance", {}).get("partition_contract_complete") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("dataset_reconstruction_mismatches") != 0
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset_verification.get("out_of_task_support_cases") != 0
    ):
        raise ValueError("C23 dataset replay incomplete")
    policy = load_policy(policy_path)
    compiled = compile_work_policy(policy)
    if (
        compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
        or policy["policy_sha256"] != spec["policy_sha256"]
    ):
        raise ValueError("C23 compiled policy mismatch")
    cases = dataset["cases"]
    case_by_id = {case["case_id"]: case for case in cases}
    if len(cases) != 48 or len(case_by_id) != 48:
        raise ValueError("C23 case identity mismatch")
    config = C23Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(cases, config.oracle_config())
    if functional != load(run / "functional.json") or oracles != load(run / "oracles.json"):
        raise ValueError("C23 exhaustive oracle replay mismatch")
    contracts = load(run / "contracts.json")
    if set(contracts) != set(case_by_id):
        raise ValueError("C23 contract identity mismatch")
    for case_id, contract in contracts.items():
        normalized = validate_contract(contract)
        if (
            normalized["task"] != "gf2_decomposition"
            or normalized["lifecycle"] != "fresh_engine"
            or normalized["queries"] != 1
            or len(normalized["variable_order"]) != case_by_id[case_id]["n_vars"]
            or contract["validation"]["validation_in_timed_span"] is not False
            or contract["validation"]["required_output_sha256"]
            != oracles[case_id]["delivered_sha256"]
        ):
            raise ValueError("C23 task contract mismatch")

    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(cases) * len(METHODS) * config.rounds:
        raise ValueError("C23 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row.get("case_id"), row.get("method"), row.get("round"))
        if identity in identities or row.get("method") not in METHODS:
            raise ValueError("C23 duplicate or unknown measurement")
        identities.add(identity)
        case = case_by_id.get(row["case_id"])
        oracle = oracles.get(row["case_id"])
        timings = row.get("timings_ns")
        expected_arm = EXHAUSTIVE if row["method"] == "cm_exhaustive" else SCREENED
        expected_proposal_status = "not_applicable" if row["method"] in {
            "cm_exhaustive", "cm_screened", "cm_compiled_screened"} else None
        if (
            case is None or oracle is None
            or row.get("split") != "fresh_confirmation"
            or row.get("cluster_id") != case["cluster_id"]
            or row.get("n_vars") != case["n_vars"]
            or row.get("status") != "ok"
            or row.get("selected_exact_arm") != expected_arm
            or row.get("artifact_sha256") != oracle["delivered_sha256"]
            or row.get("best_artifact_sha256") != (
                oracle["best_artifact"]["payload_sha256"] if oracle["best_artifact"] else None)
            or row.get("source_sha256")
            != truth_sha256(int(case["truth_bits_hex"], 16), case["n_vars"])
            or row.get("partitions_tested") != len(candidate_partitions(
                int(case["truth_bits_hex"], 16), case["n_vars"], config.max_partitions))
            or row.get("exact_check_passed") is not True
            or type(timings) is not dict
            or set(timings) != {*TIMING_FIELDS, "task_total_ns"}
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["task_total_ns"]
            != sum(value for key, value in timings.items() if key != "task_total_ns")
            or (expected_proposal_status is not None
                and row["proposal"]["status"] != expected_proposal_status)
        ):
            raise ValueError("C23 exactness, contract, metadata, or timing invariant mismatch")

    memory_rows = load_rows(run / "memory_measurements.jsonl")
    memory_cases = _memory_cases(cases, config.memory_cases_per_width)
    expected_memory = {(case["case_id"], method) for case in memory_cases for method in METHODS}
    if (
        len(memory_rows) != len(expected_memory)
        or {(row.get("case_id"), row.get("method")) for row in memory_rows} != expected_memory
        or any(type(row.get("peak_bytes")) is not int or row["peak_bytes"] < 1
               or type(row.get("current_bytes")) is not int or row["current_bytes"] < 0
               or row.get("exact_check_passed") is not True for row in memory_rows)
    ):
        raise ValueError("C23 memory diagnostic mismatch")
    summary = fresh_summary(rows, memory_rows, functional)
    if summary != result["summary"]:
        raise ValueError("C23 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_rows") != 1680
        or result.get("memory_measurement_rows") != len(expected_memory)
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["claims"].get("same_requested_artifact") is not True
        or result["claims"].get("unchanged_c21_methods") is not True
        or result["claims"].get("fresh_confirmation") is not True
        or result["claims"].get("production_promotion") is not False
        or result["dataset"].get("fresh_confirmation") is not True
        or result["dataset"].get("policy_refit") is not False
    ):
        raise ValueError("C23 final claim mismatch")
    verification = {
        "schema": "crse-c23-fresh-task-matched-gf2-table-verification/v1",
        "status": "verified",
        "functional_cases_replayed": len(cases),
        "contracts_checked": len(contracts),
        "measurement_rows_checked": len(rows),
        "memory_rows_checked": len(memory_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "policy_refit": False,
        "fresh_confirmation": True,
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
