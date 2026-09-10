"""Seal two verified q64 hosts into the normalized decision-surface package.

This command is intentionally unavailable with fewer than two distinct physical
machine identities.  It derives joint labels only after both raw streams and both
independent host verifications are complete.  It never fits or invokes a model.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import query_ladder_decision_surface as surface
from cmbench.recognition import query_ladder_learning_freeze as learning
from cmbench.recognition import query_ladder_q64_execution as q64


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _block_table(frozen: dict, rows: list[dict]) -> dict:
    table = {
        case["case_id"]: {arm: [None] * q64.BLOCKS for arm in learning.EXACT_ARMS}
        for case in frozen["cohort"]["cases"]
    }
    for row in rows:
        values = table[row["case_id"]][row["arm"]]
        block = row["block"]
        if values[block] is not None:
            raise ValueError(f"duplicate block cell:{row['case_id']}:{row['arm']}:{block}")
        values[block] = row["timings_ns"]["accounted_total_ns"]
    if any(value is None for by_arm in table.values() for values in by_arm.values()
           for value in values):
        raise ValueError("incomplete block table")
    return table


def _host_economics(table: dict, costs: dict) -> dict:
    medians = {
        case_id: {arm: float(statistics.median(values)) for arm, values in by_arm.items()}
        for case_id, by_arm in table.items()
    }
    sums = {arm: sum(row[arm] for row in medians.values()) for arm in learning.EXACT_ARMS}
    best = min(learning.EXACT_ARMS, key=lambda arm: (sums[arm], learning.EXACT_ARMS.index(arm)))
    oracle = sum(min(row.values()) for row in medians.values())
    total_cost = sum(costs.values())
    return {
        "best_fixed_arm": best,
        "best_fixed_sum_ns": sums[best],
        "oracle_sum_ns": oracle,
        "gross_speedup": sums[best] / oracle,
        "fully_charged_speedup": sums[best] / (oracle + len(medians) * total_cost),
        "per_case_arm_medians_ns": medians,
    }


def package(run_dir: Path, host_ids: list[str]) -> dict:
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(ROOT) or len(host_ids) != 2 or len(set(host_ids)) != 2:
        raise ValueError("exactly two host IDs in the project run directory are required")
    frozen = q64.load_verified_parent(ROOT)
    oracles = q64.load_json(run_dir / "ORACLES.json")
    q64.validate_oracles(oracles, frozen)
    baseline_path = run_dir / "BASELINE_CLOSURE.json"
    replications = []
    host_inputs = []
    tables = {}
    charged_documents = {}
    machine_ids = set()
    host_verification_shas = set()
    for host_id in host_ids:
        host = run_dir / host_id
        verification_path = host / "INDEPENDENT_VERIFICATION.json"
        verification = q64.load_json(verification_path)
        if verification.get("status") != "verified_complete":
            raise ValueError(f"host verification incomplete:{host_id}")
        if any(verification.get(name) != 0 for name in (
            "schedule_mismatches", "semantic_mismatches", "timing_mismatches",
            "source_or_artifact_mismatches", "charged_cost_mismatches",
        )):
            raise ValueError(f"host verification mismatch:{host_id}")
        machine_ids.add(verification["physical_machine_sha256"])
        verification_sha = q64.file_sha256(verification_path)
        host_verification_shas.add(verification_sha)
        rows = _rows(host / "RAW.jsonl")
        audit = q64.verify_raw_rows(frozen, oracles, rows)
        if audit["status"] != "verified_complete":
            raise ValueError(f"raw replay incomplete:{host_id}")
        tables[host_id] = _block_table(frozen, rows)
        charged = q64.load_json(host / "CHARGED_COSTS.json")
        charged_documents[host_id] = charged
        preflight = q64.load_json(host / "HOST_PREFLIGHT.json")
        host_inputs.append({
            "replication_id": host_id,
            "physical_machine_sha256": verification["physical_machine_sha256"],
            "compiler_sha256": verification["compiler_sha256"],
            "raw_file_sha256": q64.file_sha256(host / "RAW.jsonl"),
            "charged_cost_file_sha256": q64.file_sha256(host / "CHARGED_COSTS.json"),
            "result_file_sha256": q64.file_sha256(host / "RESULT.json"),
            "host_preflight_file_sha256": q64.file_sha256(host / "HOST_PREFLIGHT.json"),
            "host_verification_file_sha256": verification_sha,
            "native_library_sha256": preflight["native"]["native_library_sha256"],
        })
    if len(machine_ids) != 2 or len(host_verification_shas) != 2:
        raise ValueError("two distinct physical machines and verifications are required")

    labels = {
        case["case_id"]: learning.label_from_cross_host_blocks({
            host_id: tables[host_id][case["case_id"]] for host_id in host_ids
        })
        for case in frozen["cohort"]["cases"]
    }
    for host_input in host_inputs:
        host_id = host_input["replication_id"]
        medians = {
            case_id: {arm: float(statistics.median(values)) for arm, values in by_arm.items()}
            for case_id, by_arm in tables[host_id].items()
        }
        fixed_sums = {
            arm: sum(values[arm] for values in medians.values()) for arm in learning.EXACT_ARMS
        }
        best = min(learning.EXACT_ARMS,
                   key=lambda arm: (fixed_sums[arm], learning.EXACT_ARMS.index(arm)))
        charged = charged_documents[host_id]
        fallback = learning.expected_fallback_cost_ns_per_case(
            labels=labels, per_case_arm_medians_ns=medians, best_fixed_arm=best,
            fallback_dispatch_p95_ns=charged["p95_ns_per_case"]["fallback_dispatch"],
        )
        costs = {
            name: charged["p95_ns_per_case"][name]
            for name in ("feature_extraction_and_control", "model_inference", "exact_verification")
        }
        costs["expected_fallback"] = fallback
        replications.append({
            "replication_id": host_id,
            "physical_machine_sha256": host_input["physical_machine_sha256"],
            "compiler_sha256": host_input["compiler_sha256"],
            "independent_verification_sha256": host_input["host_verification_file_sha256"],
            "verification_status": "verified_complete",
            "case_set_sha256": q64.CASE_SET_SHA256,
            "block_timings_ns": tables[host_id],
            "block_timings_sha256": surface.digest(tables[host_id]),
            "p95_costs_ns_per_case": costs,
            "p95_costs_measured_same_host": True,
            "schedule_mismatches": 0, "semantic_mismatches": 0,
            "source_or_artifact_mismatches": 0,
        })
    evidence_without_verification = {
        "schema": surface.EVIDENCE_SCHEMA, "status": "verified_complete",
        "surface_id": surface.SURFACE_ID,
        "freeze_file_sha256": q64.PARENT_FILE_SHA256,
        "task_contract_sha256": q64.TASK_SHA256,
        "case_set_sha256": q64.CASE_SET_SHA256,
        "label_policy_sha256": q64.LABEL_POLICY_SHA256,
        "baseline_closure": {
            "status": "verified_complete", "sha256": q64.file_sha256(baseline_path),
            "all_relevant_exact_baselines_included": True,
        },
        "prospective_cases_consumed": 0,
        "claim_boundary": {
            "development_training_eligibility_permitted": True,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
        "replications": replications,
    }
    split_by_case = {row["case_id"]: row["split"] for row in frozen["cohort"]["cases"]}
    non_abstain = {case_id: label for case_id, label in labels.items()
                   if label != learning.ABSTAIN_LABEL}
    counts = Counter(non_abstain.values())
    split_counts = Counter(split_by_case[case_id] for case_id in non_abstain)
    economics = {
        replication["replication_id"]: _host_economics(
            replication["block_timings_ns"], replication["p95_costs_ns_per_case"]
        ) for replication in replications
    }
    for value in economics.values():
        value.pop("per_case_arm_medians_ns")
    verification_core = {
        "schema": q64.SURFACE_VERIFICATION_SCHEMA, "status": "verified_complete",
        "host_inputs": host_inputs,
        "physical_machine_sha256s": sorted(machine_ids),
        "parent_freeze_file_sha256": q64.PARENT_FILE_SHA256,
        "child_freeze_file_sha256": q64.file_sha256(run_dir / "CHILD_FREEZE.json"),
        "baseline_closure_file_sha256": q64.file_sha256(baseline_path),
        "oracles_file_sha256": q64.file_sha256(run_dir / "ORACLES.json"),
        "normalized_evidence_without_surface_verification_sha256": surface.digest(
            evidence_without_verification
        ),
        "label_table_sha256": surface.digest(labels),
        "source_groups_per_label": dict(sorted(counts.items())),
        "abstentions": len(labels) - len(non_abstain),
        "coverage": len(non_abstain) / len(labels),
        "coverage_by_split": {
            split: split_counts[split] / size
            for split, size in frozen["cohort"]["source_group_counts_by_split"].items()
        },
        "economics_by_host": economics,
        "label_rule_replayed_after_both_hosts_sealed": True,
        "p10_rule": "sorted_16_ratios_index_1",
        "prospective_cases_consumed": 0, "models_trained": 0,
    }
    verification_path = run_dir / "SURFACE_INDEPENDENT_VERIFICATION.json"
    q64.write_json_exclusive(verification_path, verification_core)
    evidence = {
        **evidence_without_verification,
        "surface_independent_verification_sha256": q64.file_sha256(verification_path),
    }
    evidence_path = run_dir / "NORMALIZED_EVIDENCE.json"
    q64.write_json_exclusive(evidence_path, evidence)
    assessment = surface.assess_decision_surface(
        evidence, frozen, freeze_file_sha256=q64.PARENT_FILE_SHA256,
    )
    q64.write_json_exclusive(run_dir / "SURFACE_ASSESSMENT.json", assessment)
    return {
        "status": assessment["status"], "evidence": str(evidence_path),
        "surface_verification_sha256": q64.file_sha256(verification_path),
        "label_table_sha256": assessment["label_table_sha256"],
        "coverage": assessment["non_abstain_coverage"],
        "blockers": assessment["blockers"], "models_trained": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--host", action="append", required=True)
    args = parser.parse_args()
    result = package(args.run_dir, args.host)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "verified_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
