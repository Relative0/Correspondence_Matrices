"""Independent integrity and exactness verifier for the C21 GF(2) table."""
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
from cmbench.comparative.gf2_decomposition import delivered_sha256
from cmbench.comparative.gf2_method_table import METHODS, TIMING_FIELDS
from cmbench.comparative.gf2_table_experiment import C21Config, _memory_cases, build_oracles, summarize
from cmbench.recognition.gf2_decomposition import candidate_partitions, truth_sha256
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy

DATASET = ROOT / "docs/recognition/c21_decomposition_table_dataset.json"
DATASET_VERIFY = ROOT / "docs/recognition/c21_decomposition_table_dataset_verification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the C21 task-matched GF(2) method table")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json")
    policy_path = ROOT / spec["policy_path"]
    if (
        sha256(DATASET) != manifest["dataset_sha256"]
        or sha256(DATASET) != spec["dataset_sha256"]
        or sha256(policy_path) != manifest["policy_file_sha256"]
        or sha256(policy_path) != spec["policy_file_sha256"]
    ):
        raise ValueError("C21 frozen dataset or policy fingerprint mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C21 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C21 artifact fingerprint mismatch: {name}")
    dataset_verification = load(DATASET_VERIFY)
    if (
        dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 96
        or dataset_verification.get("truth_mismatches") != 0
        or dataset_verification.get("expression_mismatches") != 0
        or dataset_verification.get("source_record_mismatches") != 0
        or dataset_verification.get("split_cluster_overlap") != 0
    ):
        raise ValueError("C21 dataset source replay incomplete")
    dataset, policy = load(DATASET), load_policy(policy_path)
    compiled = compile_work_policy(policy)
    if (
        compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
        or policy["policy_sha256"] != spec["policy_sha256"]
    ):
        raise ValueError("C21 compiled policy contract mismatch")
    cases = dataset["cases"]
    case_by_id = {case["case_id"]: case for case in cases}
    if len(cases) != 96 or len(case_by_id) != 96:
        raise ValueError("C21 case count or identity mismatch")
    config = C21Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(cases, config)
    if functional != load(run / "functional.json") or oracles != load(run / "oracles.json"):
        raise ValueError("C21 exhaustive oracle replay mismatch")
    contracts = load(run / "contracts.json")
    if set(contracts) != set(case_by_id):
        raise ValueError("C21 contract identity mismatch")
    for case_id, contract in contracts.items():
        normalized = validate_contract(contract)
        if (
            normalized["task"] != "gf2_decomposition"
            or normalized["lifecycle"] != "fresh_engine"
            or normalized["queries"] != 1
            or len(normalized["variable_order"]) != case_by_id[case_id]["n_vars"]
            or contract["validation"]["validation_in_timed_span"] is not False
            or contract["validation"]["required_output_sha256"] != oracles[case_id]["delivered_sha256"]
        ):
            raise ValueError("C21 task contract mismatch")

    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(cases) * len(METHODS) * config.rounds:
        raise ValueError("C21 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row.get("case_id"), row.get("method"), row.get("round"))
        if identity in identities or row.get("method") not in METHODS:
            raise ValueError("C21 duplicate or unknown measurement")
        identities.add(identity)
        case = case_by_id.get(row["case_id"])
        oracle = oracles.get(row["case_id"])
        timings = row.get("timings_ns")
        expected_arm = EXHAUSTIVE if row["method"] == "cm_exhaustive" else SCREENED
        expected_proposal_status = "not_applicable" if row["method"] in {
            "cm_exhaustive", "cm_screened", "cm_compiled_screened"} else None
        if (
            case is None
            or oracle is None
            or row.get("split") != case["split"]
            or row.get("cluster_id") != case["cluster_id"]
            or row.get("n_vars") != case["n_vars"]
            or row.get("status") != "ok"
            or row.get("selected_exact_arm") != expected_arm
            or row.get("artifact_sha256") != oracle["delivered_sha256"]
            or row.get("best_artifact_sha256") != (
                oracle["best_artifact"]["payload_sha256"] if oracle["best_artifact"] else None)
            or row.get("source_sha256") != truth_sha256(int(case["truth_bits_hex"], 16), case["n_vars"])
            or row.get("partitions_tested") != len(candidate_partitions(
                int(case["truth_bits_hex"], 16), case["n_vars"], config.max_partitions))
            or row.get("exact_check_passed") is not True
            or type(timings) is not dict
            or set(timings) != {*TIMING_FIELDS, "task_total_ns"}
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["task_total_ns"] != sum(value for key, value in timings.items() if key != "task_total_ns")
            or (expected_proposal_status is not None and row["proposal"]["status"] != expected_proposal_status)
        ):
            raise ValueError("C21 exactness, contract, metadata, or timing invariant mismatch")

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
        raise ValueError("C21 memory diagnostic mismatch")
    summary = summarize(rows, memory_rows, functional)
    if summary != result["summary"]:
        raise ValueError("C21 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_rows") != 3360
        or result.get("memory_measurement_rows") != 84
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["claims"].get("same_requested_artifact") is not True
        or result["claims"].get("proposal_is_not_certificate") is not True
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or result["dataset"].get("retrospective") is not True
        or result["dataset"].get("policy_refit") is not False
        or result["runpod"].get("used") is not False
    ):
        raise ValueError("C21 final claim mismatch")
    verification = {
        "schema": "crse-c21-task-matched-gf2-method-table-verification/v1",
        "status": "verified",
        "functional_cases_replayed": 96,
        "contracts_checked": len(contracts),
        "measurement_rows_checked": len(rows),
        "memory_rows_checked": len(memory_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "dataset_source_replay_required_and_present": True,
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "policy_refit": False,
        "fresh_confirmation": False,
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
