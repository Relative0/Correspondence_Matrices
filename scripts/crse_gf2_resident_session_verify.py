"""Independent integrity and exactness verifier for C25 resident sessions."""
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
from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    C25Config,
    METHODS,
    N_VARS,
    QUERY_COUNTS,
    build_oracles,
    case_sequence,
    summarize,
)
from cmbench.recognition.gf2_source_portfolio import (
    SOURCE_PACKED_SCREENED,
    load_source_portfolio_policy,
)
from cmbench.recognition.gf2_source_portfolio_session import (
    ResidentSourcePortfolioSession,
    verify_resident_query_result,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED, canonical_sha256
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
    parser = argparse.ArgumentParser(description="Verify the C25 resident C22 session run")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = (
        load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json"))
    dataset_path = ROOT / spec["dataset_path"]
    dataset_verification_path = ROOT / spec["dataset_verification_path"]
    c22_policy_path = ROOT / spec["c22_policy_path"]
    c19_policy_path = ROOT / spec["c19_policy_path"]
    fingerprints = (
        (dataset_path, "dataset_sha256"),
        (dataset_verification_path, "dataset_verification_sha256"),
        (c22_policy_path, "c22_policy_file_sha256"),
        (c19_policy_path, "c19_policy_file_sha256"),
    )
    for path, field in fingerprints:
        if sha256(path) != spec[field] or sha256(path) != manifest[field]:
            raise ValueError(f"C25 frozen input fingerprint mismatch: {field}")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C25 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C25 artifact fingerprint mismatch: {name}")

    dataset = load(dataset_path)
    dataset_verification = load(dataset_verification_path)
    validate_dataset(dataset)
    if (
        dataset.get("revision", {}).get("id") != "task-complete-v2"
        or dataset.get("provenance", {}).get("partition_contract_complete") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset_verification.get("out_of_task_support_cases") != 0
    ):
        raise ValueError("C25 sealed C23 corpus verification mismatch")
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c22_policy["policy_sha256"] != spec["c22_policy_sha256"]
        or c22_policy["selected_arm"] != SOURCE_PACKED_SCREENED
        or c22_policy["training_use"] is not False
        or c22_policy["production_promotion"] is not False
        or c19_policy["policy_sha256"] != spec["c19_policy_sha256"]
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
        or spec.get("methods") != list(METHODS)
        or spec.get("immutable_policy_reuse") is not True
        or spec.get("compiled_state_reuse_by_support_width") is not True
        or spec.get("per_query_input_validation") is not True
        or spec.get("per_query_exact_delivery_verification") is not True
        or spec.get("policy_refit") is not False
        or spec.get("production_promotion") is not False
    ):
        raise ValueError("C25 frozen policy or lifecycle contract mismatch")

    cases = dataset["cases"]
    case_by_id = {case["case_id"]: case for case in cases}
    config = C25Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(cases, config.oracle_config())
    if functional != load(run / "functional.json") or oracles != load(run / "oracles.json"):
        raise ValueError("C25 exhaustive oracle replay mismatch")
    contracts = load(run / "contracts.json")
    if len(case_by_id) != 48 or set(contracts) != set(case_by_id):
        raise ValueError("C25 case or contract identity mismatch")
    for case_id, contract in contracts.items():
        normalized = validate_contract(contract)
        if (
            normalized["task"] != "gf2_decomposition"
            or normalized["lifecycle"] != "fresh_engine"
            or normalized["queries"] != 1
            or len(normalized["variable_order"]) != case_by_id[case_id]["n_vars"]
            or contract["validation"]["required_output_sha256"]
            != oracles[case_id]["delivered_sha256"]
        ):
            raise ValueError("C25 per-query contract mismatch")
    cases_by_width = {
        n_vars: sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    if any(not group for group in cases_by_width.values()):
        raise ValueError("C25 support-width coverage mismatch")

    controls = load(run / "functional_controls.json")
    fallback_by_id = {row["case_id"]: row for row in controls["fallback_cases"]}
    refusal_by_id = {row["control_id"]: row for row in controls["refusal_cases"]}
    expected_refusals = {
        "truth_mismatch", "unsupported_n7", "closed_session", "query_limit",
        "tampered_policy_at_setup",
    }
    if (
        controls.get("schema") != "crse-c25-resident-session-controls/v1"
        or controls.get("fallback_cases_checked") != 48
        or controls.get("refusal_cases_checked") != 5
        or controls.get("fallback_gate") is not True
        or controls.get("refusal_gate") is not True
        or controls.get("all_passed") is not True
        or set(fallback_by_id) != set(case_by_id)
        or set(refusal_by_id) != expected_refusals
        or any(row.get("status") != "refused" for row in refusal_by_id.values())
    ):
        raise ValueError("C25 recorded functional controls mismatch")
    fallback_replay = ResidentSourcePortfolioSession(
        "c25-independent-fallback", c22_policy_path, max_queries=len(cases))
    for case in cases:
        oracle = oracles[case["case_id"]]
        recorded = fallback_by_id[case["case_id"]]
        if (
            recorded.get("status") != "ok"
            or recorded.get("selected_arm") != EXHAUSTIVE
            or recorded.get("fallback_used") is not True
            or recorded.get("exact_check_passed") is not True
            or recorded.get("artifact_sha256") != canonical_sha256(oracle["best_artifact"])
        ):
            raise ValueError("C25 recorded exact fallback mismatch")
        replayed = fallback_replay.execute(case, force_source_refusal=True).to_dict()
        verify_resident_query_result(
            replayed, case, policy_sha256=c22_policy["policy_sha256"],
            required_best=oracle["best_artifact"])
        if replayed["selected_arm"] != EXHAUSTIVE or replayed["fallback_used"] is not True:
            raise ValueError("C25 independent exact fallback replay mismatch")
    fallback_replay.close()
    try:
        ResidentSourcePortfolioSession(
            "c25-invalid-policy", run / "control_policy_tampered.json")
    except ValueError:
        pass
    else:
        raise ValueError("C25 tampered policy setup was accepted")

    expected_selection = {
        "resident_direct_exhaustive": EXHAUSTIVE,
        "resident_direct_screened": SCREENED,
        "resident_direct_compiled_screened": SCREENED,
        "resident_direct_source_packed": SCREENED,
        "resident_c22_advice_on": SOURCE_PACKED_SCREENED,
        "resident_c22_advice_off": EXHAUSTIVE,
    }
    rows = load_rows(run / "measurements.jsonl")
    expected_batches = config.rounds * len(N_VARS) * len(QUERY_COUNTS) * len(METHODS)
    if len(rows) != expected_batches:
        raise ValueError("C25 measurement batch count mismatch")
    identities = set()
    timed_queries = 0
    cache_records_checked = 0
    for row in rows:
        identity = (
            row.get("round"), row.get("n_vars"), row.get("query_count"), row.get("method"))
        if (
            identity in identities
            or row.get("method") not in METHODS
            or row.get("n_vars") not in N_VARS
            or row.get("query_count") not in QUERY_COUNTS
        ):
            raise ValueError("C25 duplicate or unknown batch")
        identities.add(identity)
        expected_cases = case_sequence(
            cases_by_width, row["n_vars"], row["query_count"], row["round"])
        query_records = row.get("query_records")
        timings = row.get("timings_ns")
        if (
            row.get("status") != "ok"
            or row.get("exact_check_passed") is not True
            or type(query_records) is not list
            or len(query_records) != row["query_count"]
            or [record.get("case_id") for record in query_records]
            != [case["case_id"] for case in expected_cases]
            or type(timings) is not dict
            or set(timings) != {*BATCH_TIMING_FIELDS, "batch_total_ns"}
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["batch_total_ns"] != sum(timings[field] for field in BATCH_TIMING_FIELDS)
            or row.get("amortized_query_ns") != timings["batch_total_ns"] / row["query_count"]
        ):
            raise ValueError("C25 batch timing, schedule, or exactness mismatch")
        for index, (record, case) in enumerate(zip(query_records, expected_cases)):
            oracle = oracles[case["case_id"]]
            is_resident = row["method"].startswith("resident_c22_")
            expected_cache = (index > 0) if is_resident else None
            if (
                record.get("artifact_sha256") != oracle["delivered_sha256"]
                or record.get("best_artifact_sha256") != (
                    oracle["best_artifact"]["payload_sha256"] if oracle["best_artifact"] else None)
                or record.get("selected_arm") != expected_selection[row["method"]]
                or record.get("compile_cache_hit") is not expected_cache
                or record.get("exact_check_passed") is not True
                or type(record.get("elapsed_ns")) is not int
                or record["elapsed_ns"] < 1
            ):
                raise ValueError("C25 per-query identity or cache invariant mismatch")
            cache_records_checked += int(is_resident)
        snapshot = row.get("session_snapshot")
        if row["method"].startswith("resident_c22_"):
            if (
                type(snapshot) is not dict
                or snapshot.get("successful_queries") != row["query_count"]
                or snapshot.get("refused_queries") != 0
                or snapshot.get("compiled_widths") != [row["n_vars"]]
                or snapshot.get("closed") is not False
                or snapshot.get("policy_sha256") != c22_policy["policy_sha256"]
            ):
                raise ValueError("C25 resident session snapshot mismatch")
        elif snapshot is not None:
            raise ValueError("C25 direct control unexpectedly has a session snapshot")
        timed_queries += row["query_count"]

    memory_rows = load_rows(run / "memory_measurements.jsonl")
    expected_memory = {(n_vars, method) for n_vars in N_VARS for method in METHODS}
    if (
        len(memory_rows) != len(expected_memory)
        or {(row.get("n_vars"), row.get("method")) for row in memory_rows} != expected_memory
        or any(
            row.get("query_count") != config.memory_query_count
            or type(row.get("peak_bytes")) is not int or row["peak_bytes"] < 1
            or type(row.get("current_bytes")) is not int or row["current_bytes"] < 0
            or row.get("exact_check_passed") is not True
            for row in memory_rows
        )
    ):
        raise ValueError("C25 memory diagnostic mismatch")
    summary = summarize(rows, memory_rows, controls)
    if summary != result["summary"]:
        raise ValueError("C25 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or timed_queries != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("refusal_controls") != 5
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["claims"].get("unchanged_c22_policy") is not True
        or result["claims"].get("resident_policy_and_compiled_state_reused") is not True
        or result["claims"].get("every_query_exactly_verified") is not True
        or result["claims"].get("fallback_and_refusal_controls_passed") is not True
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or result["runpod"] != {"used": False, "cost_usd": 0.0}
    ):
        raise ValueError("C25 final claim mismatch")
    verification = {
        "schema": "crse-c25-resident-c22-session-verification/v1",
        "status": "verified",
        "functional_cases_replayed": len(cases),
        "contracts_checked": len(contracts),
        "fallback_controls_replayed": len(cases),
        "refusal_controls_checked": len(expected_refusals),
        "measurement_batches_checked": len(rows),
        "timed_query_records_checked": timed_queries,
        "resident_cache_records_checked": cache_records_checked,
        "memory_batches_checked": len(memory_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "policy_refit": False,
        "fresh_confirmation": False,
        "resident_promotion_gate": summary["resident_promotion_gate"],
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
