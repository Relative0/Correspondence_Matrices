"""Independent integrity and exactness verifier for the C27 confirmation."""
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
from cmbench.comparative.gf2_support_aware_experiment import (
    C27Config, DIRECT_METHODS, METHODS, build_oracles, summarize,
)
from cmbench.comparative.gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS, N_VARS, QUERY_COUNTS, case_sequence,
)
from cmbench.recognition.gf2_decomposition import candidate_partitions
from cmbench.recognition.gf2_support_aware_session import (
    SupportAwareGF2Session,
)
from cmbench.recognition.gf2_source_portfolio import (
    SOURCE_PACKED_SCREENED, load_source_portfolio_policy,
)
from cmbench.recognition.gf2_support_aware_policy import (
    TRUTH_SCREENED, load_support_aware_policy, select_support_arm,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED, canonical_sha256
from cmbench.recognition.gf2_verified_context import (
    build_verified_gf2_context, verify_verified_gf2_context,
)
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the C27 support-aware run")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = (
        load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json"))
    dataset_path = ROOT / spec["dataset_path"]
    dataset_verification_path = ROOT / spec["dataset_verification_path"]
    c27_policy_path = ROOT / spec["c27_policy_path"]
    c22_policy_path = ROOT / spec["c22_policy_path"]
    c19_policy_path = ROOT / spec["c19_policy_path"]
    for path, field in (
        (dataset_path, "dataset_sha256"),
        (dataset_verification_path, "dataset_verification_sha256"),
        (c27_policy_path, "c27_policy_file_sha256"),
        (c22_policy_path, "c22_policy_file_sha256"),
        (c19_policy_path, "c19_policy_file_sha256"),
    ):
        if sha256(path) != spec[field] or sha256(path) != manifest[field]:
            raise ValueError(f"C27 frozen input fingerprint mismatch: {field}")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C27 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C27 artifact fingerprint mismatch: {name}")

    dataset = load(dataset_path)
    dataset_verification = load(dataset_verification_path)
    validate_dataset(dataset)
    if (
        dataset.get("provenance", {}).get("policy_frozen_before_dataset") is not True
        or dataset.get("provenance", {}).get("fresh_confirmation") is not True
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("scalar_oracle_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset_verification.get("dataset_reconstruction_mismatches") != 0
    ):
        raise ValueError("C27 sealed corpus verification mismatch")
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c27_policy["policy_sha256"] != spec["c27_policy_sha256"]
        or c27_policy["tiny_support_max_n_vars"] != 4
        or c27_policy["tiny_support_arm"] != TRUTH_SCREENED
        or c27_policy["large_support_arm"] != SOURCE_PACKED_SCREENED
        or c27_policy["fresh_confirmation_complete"] is not False
        or c27_policy["training_use"] is not False
        or c22_policy["policy_sha256"] != spec["c22_policy_sha256"]
        or c22_policy["selected_arm"] != SOURCE_PACKED_SCREENED
        or c22_policy["training_use"] is not False
        or c19_policy["policy_sha256"] != spec["c19_policy_sha256"]
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
        or spec.get("methods") != list(METHODS)
        or spec.get("unchanged_c25_direct_controls") is not True
        or spec.get("single_expression_evaluation_per_fused_query") is not True
        or spec.get("context_digest_binds_expression_width_truth_and_source") is not True
        or spec.get("final_artifact_reconstruction_charged") is not True
        or spec.get("policy_frozen_before_fresh_corpus") is not True
        or spec.get("fresh_confirmation") is not True
        or spec.get("policy_refit") is not False
        or spec.get("production_promotion") is not False
    ):
        raise ValueError("C27 frozen policy or lifecycle contract mismatch")

    cases = dataset["cases"]
    case_by_id = {case["case_id"]: case for case in cases}
    config = C27Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(cases, config.oracle_config())
    if functional != load(run / "functional.json") or oracles != load(run / "oracles.json"):
        raise ValueError("C27 exhaustive oracle replay mismatch")
    contracts = load(run / "contracts.json")
    if len(case_by_id) != 48 or set(contracts) != set(case_by_id):
        raise ValueError("C27 case or contract identity mismatch")
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
            raise ValueError("C27 per-query contract mismatch")
    cases_by_width = {
        n: sorted((case for case in cases if case["n_vars"] == n),
                  key=lambda case: (case["truth_sha256"], case["case_id"]))
        for n in N_VARS
    }

    controls = load(run / "functional_controls.json")
    fallback_by_id = {row["case_id"]: row for row in controls["fallback_cases"]}
    path_by_id = {row["case_id"]: row for row in controls["selected_path_cases"]}
    refusal_by_id = {row["control_id"]: row for row in controls["refusal_cases"]}
    expected_refusals = {
        "truth_mismatch", "unsupported_n7", "closed_session", "query_limit",
        "tampered_c22_policy_at_setup", "tampered_c27_policy_at_setup",
        "tampered_context_expression", "tampered_context_truth",
        "tampered_context_width", "tampered_context_digest",
    }
    if (
        controls.get("schema") != "crse-c27-support-aware-session-controls/v1"
        or controls.get("fallback_cases_checked") != 48
        or controls.get("selected_path_cases_checked") != 48
        or controls.get("tiny_truth_path_cases_checked") != 24
        or controls.get("large_packed_path_cases_checked") != 24
        or controls.get("refusal_cases_checked") != 10
        or controls.get("context_tamper_controls_checked") != 4
        or controls.get("all_passed") is not True
        or set(fallback_by_id) != set(case_by_id)
        or set(path_by_id) != set(case_by_id)
        or set(refusal_by_id) != expected_refusals
        or any(row.get("status") != "refused" for row in refusal_by_id.values())
    ):
        raise ValueError("C27 recorded functional controls mismatch")
    fallback_session = SupportAwareGF2Session(
        "c27-independent-fallback", c27_policy_path, c22_policy_path,
        max_queries=len(cases))
    for case in cases:
        oracle = oracles[case["case_id"]]
        recorded = fallback_by_id[case["case_id"]]
        context = build_verified_gf2_context(case, require_source_packed=False)
        if (
            recorded.get("status") != "ok"
            or recorded.get("selected_arm") != EXHAUSTIVE
            or recorded.get("fallback_used") is not True
            or recorded.get("exact_check_passed") is not True
            or recorded.get("artifact_sha256") != canonical_sha256(oracle["best_artifact"])
            or recorded.get("context_sha256") != context.context_sha256
        ):
            raise ValueError("C27 recorded fallback mismatch")
        expected_path = select_support_arm(
            c27_policy, case["n_vars"], advice_enabled=True)
        path_record = path_by_id[case["case_id"]]
        if (
            path_record.get("n_vars") != case["n_vars"]
            or path_record.get("expected_arm") != expected_path
            or path_record.get("selected_arm") != expected_path
            or path_record.get("status") != "ok"
            or path_record.get("exact_check_passed") is not True
        ):
            raise ValueError("C27 recorded selected-path mismatch")
        replay = fallback_session.execute(
            case, force_selected_refusal=True).to_dict()
        if (
            replay["selected_arm"] != EXHAUSTIVE
            or replay["fallback_used"] is not True
            or replay["best_artifact"] != oracle["best_artifact"]
        ):
            raise ValueError("C27 independent fallback replay mismatch")
    fallback_session.close()
    try:
        SupportAwareGF2Session(
            "bad-c22", c27_policy_path, run / "control_c22_policy_tampered.json")
    except ValueError:
        pass
    else:
        raise ValueError("C27 tampered C22 policy was accepted")
    try:
        SupportAwareGF2Session(
            "bad-c27", run / "control_c27_policy_tampered.json", c22_policy_path)
    except ValueError:
        pass
    else:
        raise ValueError("C27 tampered C27 policy was accepted")

    expected_selection = {
        "resident_direct_exhaustive": EXHAUSTIVE,
        "resident_direct_screened": SCREENED,
        "resident_direct_compiled_screened": SCREENED,
        "resident_direct_source_packed": SCREENED,
        "support_aware_c27_advice_off": EXHAUSTIVE,
    }
    rows = load_rows(run / "measurements.jsonl")
    expected_batches = config.rounds * len(N_VARS) * len(QUERY_COUNTS) * len(METHODS)
    if len(rows) != expected_batches:
        raise ValueError("C27 measurement batch count mismatch")
    identities = set()
    timed_queries = fused_contexts_replayed = cache_records_checked = 0
    for row in rows:
        identity = (row.get("round"), row.get("n_vars"), row.get("query_count"), row.get("method"))
        if (
            identity in identities or row.get("method") not in METHODS
            or row.get("n_vars") not in N_VARS or row.get("query_count") not in QUERY_COUNTS
        ):
            raise ValueError("C27 duplicate or unknown batch")
        identities.add(identity)
        expected_cases = case_sequence(
            cases_by_width, row["n_vars"], row["query_count"], row["round"])
        query_records = row.get("query_records")
        timings = row.get("timings_ns")
        if (
            row.get("status") != "ok" or row.get("exact_check_passed") is not True
            or type(query_records) is not list or len(query_records) != row["query_count"]
            or [record.get("case_id") for record in query_records]
            != [case["case_id"] for case in expected_cases]
            or type(timings) is not dict
            or set(timings) != {*BATCH_TIMING_FIELDS, "batch_total_ns"}
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["batch_total_ns"] != sum(timings[field] for field in BATCH_TIMING_FIELDS)
            or row.get("amortized_query_ns") != timings["batch_total_ns"] / row["query_count"]
        ):
            raise ValueError("C27 batch timing, schedule, or exactness mismatch")
        fused = row["method"] not in DIRECT_METHODS
        for index, (record, case) in enumerate(zip(query_records, expected_cases)):
            oracle = oracles[case["case_id"]]
            expected_cache = (index > 0) if fused else None
            selected_arm = expected_selection.get(row["method"])
            if row["method"] == "support_aware_c27_advice_on":
                selected_arm = select_support_arm(
                    c27_policy, row["n_vars"], advice_enabled=True)
            if (
                record.get("artifact_sha256") != oracle["delivered_sha256"]
                or record.get("best_artifact_sha256") != (
                    oracle["best_artifact"]["payload_sha256"] if oracle["best_artifact"] else None)
                or record.get("selected_arm") != selected_arm
                or record.get("compile_cache_hit") is not expected_cache
                or record.get("exact_check_passed") is not True
                or type(record.get("elapsed_ns")) is not int or record["elapsed_ns"] < 1
            ):
                raise ValueError("C27 per-query identity or cache mismatch")
            if fused:
                context = build_verified_gf2_context(
                    case, require_source_packed=(
                        row["method"] == "support_aware_c27_advice_on"
                        and row["n_vars"] >= 5))
                verify_verified_gf2_context(context.to_dict(), case, replay_semantics=True)
                if (
                    record.get("context_sha256") != context.context_sha256
                    or record.get("expression_sha256") != context.expression_sha256
                    or record.get("truth_sha256") != context.truth_sha256
                    or record.get("partitions_tested") != len(candidate_partitions(
                        context.truth_bits, context.n_vars, config.max_partitions))
                    or type(record.get("descriptors_screened")) is not int
                    or type(record.get("artifacts_materialized")) is not int
                ):
                    raise ValueError("C27 verified-context replay mismatch")
                fused_contexts_replayed += 1
                cache_records_checked += 1
            elif any(key in record for key in (
                    "context_sha256", "expression_sha256", "truth_sha256",
                    "partitions_tested", "descriptors_screened", "artifacts_materialized")):
                raise ValueError("C27 unchanged direct control gained fused metadata")
        snapshot = row.get("session_snapshot")
        if fused:
            if (
                type(snapshot) is not dict
                or snapshot.get("successful_queries") != row["query_count"]
                or snapshot.get("refused_queries") != 0
                or snapshot.get("compiled_widths") != [row["n_vars"]]
                or snapshot.get("closed") is not False
                or snapshot.get("c27_policy_sha256") != c27_policy["policy_sha256"]
                or snapshot.get("c22_policy_sha256") != c22_policy["policy_sha256"]
                or snapshot.get("compiled_arms") != {
                    str(row["n_vars"]): (
                        select_support_arm(
                            c27_policy, row["n_vars"], advice_enabled=True)
                        if row["method"] == "support_aware_c27_advice_on"
                        else EXHAUSTIVE)}
            ):
                raise ValueError("C27 fused session snapshot mismatch")
        elif snapshot is not None:
            raise ValueError("C27 direct control unexpectedly has fused snapshot")
        timed_queries += row["query_count"]

    memory_rows = load_rows(run / "memory_measurements.jsonl")
    expected_memory = {(n, method) for n in N_VARS for method in METHODS}
    if (
        len(memory_rows) != len(expected_memory)
        or {(row.get("n_vars"), row.get("method")) for row in memory_rows} != expected_memory
        or any(row.get("query_count") != config.memory_query_count
               or type(row.get("peak_bytes")) is not int or row["peak_bytes"] < 1
               or type(row.get("current_bytes")) is not int or row["current_bytes"] < 0
               or row.get("exact_check_passed") is not True for row in memory_rows)
    ):
        raise ValueError("C27 memory diagnostic mismatch")
    summary = summarize(rows, memory_rows, controls)
    if summary != result["summary"]:
        raise ValueError("C27 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560 or timed_queries != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("selected_path_controls") != 48
        or result.get("tiny_truth_path_controls") != 24
        or result.get("large_packed_path_controls") != 24
        or result.get("refusal_controls") != 10
        or result.get("context_tamper_controls") != 4
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["claims"].get("unchanged_c25_direct_controls") is not True
        or result["claims"].get("support_policy_frozen_before_corpus") is not True
        or result["claims"].get("transparent_support_rule") is not True
        or result["claims"].get(
            "single_expression_evaluation_per_support_aware_query") is not True
        or result["claims"].get("hash_bound_verified_context") is not True
        or result["claims"].get("every_query_exactly_verified") is not True
        or result["claims"].get("fallback_and_refusal_controls_passed") is not True
        or result["claims"].get("fresh_confirmation") is not True
        or result["claims"].get("policy_refit") is not False
        or result["claims"].get("production_promotion") is not False
        or result["runpod"] != {"used": False, "cost_usd": 0.0}
    ):
        raise ValueError("C27 final claim mismatch")
    verification = {
        "schema": "crse-c27-support-aware-fresh-confirmation-verification/v1",
        "status": "verified",
        "functional_cases_replayed": len(cases),
        "contracts_checked": len(contracts),
        "fallback_controls_replayed": len(cases),
        "selected_path_controls_checked": len(path_by_id),
        "tiny_truth_path_controls_checked": 24,
        "large_packed_path_controls_checked": 24,
        "refusal_controls_checked": len(expected_refusals),
        "context_tamper_controls_checked": 4,
        "measurement_batches_checked": len(rows),
        "timed_query_records_checked": timed_queries,
        "support_aware_contexts_semantically_replayed": fused_contexts_replayed,
        "support_aware_cache_records_checked": cache_records_checked,
        "memory_batches_checked": len(memory_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "policy_refit": False,
        "fresh_confirmation": True,
        "support_aware_confirmation_gate": summary["support_aware_confirmation_gate"],
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

