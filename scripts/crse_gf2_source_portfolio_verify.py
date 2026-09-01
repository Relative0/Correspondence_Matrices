"""Independent integrity and exactness verifier for the C24 C22 boundary run."""
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
from cmbench.comparative.gf2_source_portfolio_experiment import (
    BOUNDARY_SWITCHES,
    C24Config,
    DEPLOYABLE_METHODS,
    DIRECT_METHODS,
    METHODS,
    TIMING_FIELDS,
    _memory_cases,
    build_oracles,
    summarize,
)
from cmbench.comparative.gf2_method_table import TIMING_FIELDS as DIRECT_TIMING_FIELDS
from cmbench.recognition.gf2_source_portfolio import (
    load_source_portfolio_policy,
    SOURCE_PACKED_SCREENED,
)
from cmbench.recognition.gf2_source_portfolio_boundary import (
    TIMING_FIELDS as BOUNDARY_TIMING_FIELDS,
    execute_source_portfolio_boundary,
    verify_source_portfolio_boundary_result,
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


def _check_timings(timings: dict, fields: tuple[str, ...], label: str) -> None:
    if (
        type(timings) is not dict
        or set(timings) != {*fields, "task_total_ns"}
        or any(type(value) is not int or value < 0 for value in timings.values())
        or timings["task_total_ns"] != sum(timings[field] for field in fields)
    ):
        raise ValueError(f"C24 invalid {label} timing record")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the C24 frozen C22 boundary run")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = load(run / "manifest.json")
    spec = load(run / "run_spec.json")
    result = load(run / "results.json")
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
            raise ValueError(f"C24 frozen input fingerprint mismatch: {field}")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C24 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C24 artifact fingerprint mismatch: {name}")

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
        raise ValueError("C24 sealed C23 corpus verification mismatch")
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c22_policy["policy_sha256"] != spec["c22_policy_sha256"]
        or c22_policy["selected_arm"] != SOURCE_PACKED_SCREENED
        or c22_policy["advice_off_arm"] != EXHAUSTIVE
        or c22_policy["exact_fallback_arm"] != EXHAUSTIVE
        or c22_policy["training_use"] is not False
        or c22_policy["production_promotion"] is not False
        or c19_policy["policy_sha256"] != spec["c19_policy_sha256"]
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
        or spec.get("methods") != list(METHODS)
        or spec.get("deployable_methods") != list(DEPLOYABLE_METHODS)
        or spec.get("policy_refit") is not False
        or spec.get("production_promotion") is not False
    ):
        raise ValueError("C24 frozen policy or experiment contract mismatch")

    cases = dataset["cases"]
    case_by_id = {case["case_id"]: case for case in cases}
    if len(cases) != 48 or len(case_by_id) != 48:
        raise ValueError("C24 case identity mismatch")
    config = C24Config(**spec["config"])
    config.validate()
    functional, oracles = build_oracles(cases, config.oracle_config())
    if functional != load(run / "functional.json") or oracles != load(run / "oracles.json"):
        raise ValueError("C24 exhaustive oracle replay mismatch")
    contracts = load(run / "contracts.json")
    if set(contracts) != set(case_by_id):
        raise ValueError("C24 contract identity mismatch")
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
            raise ValueError("C24 task contract mismatch")

    controls = load(run / "functional_controls.json")
    fallback_by_id = {row["case_id"]: row for row in controls["fallback_cases"]}
    if (
        controls.get("schema") != "crse-c24-c22-boundary-controls/v1"
        or controls.get("fallback_cases_checked") != 48
        or controls.get("refusal_cases_checked") != 5
        or controls.get("fallback_gate") is not True
        or controls.get("refusal_gate") is not True
        or controls.get("all_passed") is not True
        or set(fallback_by_id) != set(case_by_id)
    ):
        raise ValueError("C24 recorded functional control gate mismatch")
    fallback_replayed = 0
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
            raise ValueError("C24 recorded exact fallback mismatch")
        replayed = execute_source_portfolio_boundary(
            case, c22_policy_path, force_source_refusal=True).to_dict()
        verify_source_portfolio_boundary_result(
            replayed, case, required_best=oracle["best_artifact"])
        if replayed["selected_arm"] != EXHAUSTIVE or replayed["fallback_used"] is not True:
            raise ValueError("C24 independent exact fallback replay mismatch")
        fallback_replayed += 1

    refusal_by_id = {row["control_id"]: row for row in controls["refusal_cases"]}
    expected_refusals = {
        "unsupported_n7", "malformed_expression", "truth_mismatch",
        "tampered_policy", "duplicate_policy_key",
    }
    if set(refusal_by_id) != expected_refusals or any(
        row.get("status") != "refused"
        or row.get("exact_check_passed") is not False
        or row.get("selected_arm") is not None
        for row in refusal_by_id.values()
    ):
        raise ValueError("C24 recorded fail-closed refusal mismatch")
    for invalid_policy in (run / "control_policy_tampered.json", run / "control_policy_duplicate.json"):
        try:
            load_source_portfolio_policy(invalid_policy)
        except ValueError:
            pass
        else:
            raise ValueError("C24 invalid control policy was accepted")

    expected_selection = {
        "direct_exhaustive": ("cm_exhaustive", EXHAUSTIVE, None),
        "direct_screened": ("cm_screened", SCREENED, None),
        "direct_compiled_screened": ("cm_compiled_screened", SCREENED, None),
        "direct_source_packed": ("source_packed_anf", SCREENED, None),
        "c22_advice_on": (SOURCE_PACKED_SCREENED, SOURCE_PACKED_SCREENED, None),
        "c22_advice_off": (EXHAUSTIVE, EXHAUSTIVE, None),
        "c22_advice_on_shadow": (SOURCE_PACKED_SCREENED, SOURCE_PACKED_SCREENED, True),
        "c22_advice_off_shadow": (EXHAUSTIVE, EXHAUSTIVE, True),
    }
    rows = load_rows(run / "measurements.jsonl")
    if len(rows) != len(cases) * len(METHODS) * config.rounds:
        raise ValueError("C24 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row.get("case_id"), row.get("method"), row.get("round"))
        if identity in identities or row.get("method") not in METHODS:
            raise ValueError("C24 duplicate or unknown measurement")
        identities.add(identity)
        case = case_by_id.get(row["case_id"])
        oracle = oracles.get(row["case_id"])
        requested, selected, shadow_match = expected_selection[row["method"]]
        if (
            case is None
            or oracle is None
            or row.get("split") != case["split"]
            or row.get("cluster_id") != case["cluster_id"]
            or row.get("n_vars") != case["n_vars"]
            or row.get("status") != "ok"
            or row.get("requested_arm") != requested
            or row.get("selected_arm") != selected
            or row.get("fallback_used") is not False
            or row.get("shadow_best_identity_match") is not shadow_match
            or row.get("exact_check_passed") is not True
            or row.get("artifact_sha256") != oracle["delivered_sha256"]
            or row.get("best_artifact_sha256") != (
                oracle["best_artifact"]["payload_sha256"] if oracle["best_artifact"] else None)
            or type(row.get("artifact_bytes")) is not int
            or row["artifact_bytes"] < 1
        ):
            raise ValueError("C24 exact identity or selection invariant mismatch")
        _check_timings(row.get("timings_ns"), TIMING_FIELDS, "outer")
        if row["method"] in DIRECT_METHODS:
            _check_timings(row.get("stage_timings_ns"), DIRECT_TIMING_FIELDS, "direct stage")
        else:
            _check_timings(row.get("stage_timings_ns"), BOUNDARY_TIMING_FIELDS, "boundary stage")

    memory_rows = load_rows(run / "memory_measurements.jsonl")
    memory_cases = _memory_cases(cases, config.memory_cases_per_width)
    expected_memory = {(case["case_id"], method) for case in memory_cases for method in METHODS}
    if (
        len(memory_rows) != len(expected_memory)
        or {(row.get("case_id"), row.get("method")) for row in memory_rows} != expected_memory
        or any(
            type(row.get("peak_bytes")) is not int or row["peak_bytes"] < 1
            or type(row.get("current_bytes")) is not int or row["current_bytes"] < 0
            or row.get("exact_check_passed") is not True
            for row in memory_rows
        )
    ):
        raise ValueError("C24 memory diagnostic mismatch")
    summary = summarize(rows, memory_rows, controls)
    if summary != result["summary"]:
        raise ValueError("C24 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_rows") != 3456
        or result.get("memory_measurement_rows") != 64
        or result.get("fallback_controls") != 48
        or result.get("refusal_controls") != 5
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["claims"].get("unchanged_c22_policy") is not True
        or result["claims"].get("all_boundary_costs_charged") is not True
        or result["claims"].get("fallback_and_refusal_controls_passed") is not True
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or result["dataset"].get("retrospective_boundary_evaluation") is not True
        or result["dataset"].get("policy_refit") is not False
        or result["runpod"] != {"used": False, "cost_usd": 0.0}
    ):
        raise ValueError("C24 final claim mismatch")
    verification = {
        "schema": "crse-c24-c22-boundary-verification/v1",
        "status": "verified",
        "functional_cases_replayed": len(cases),
        "contracts_checked": len(contracts),
        "fallback_controls_replayed": fallback_replayed,
        "refusal_controls_checked": len(expected_refusals),
        "measurement_rows_checked": len(rows),
        "memory_rows_checked": len(memory_rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "policy_refit": False,
        "fresh_confirmation": False,
        "local_promotion_gate": summary["local_promotion_gate"],
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
