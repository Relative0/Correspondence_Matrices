"""Freeze balanced immutable shards for the principal P7 W5 development run."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = next(
    parent
    for parent in (HERE, *HERE.parents)
    if (parent / "cmbench").is_dir() and (parent / "docs").is_dir()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze, verify_sources


PARENT_PATH = (
    PROJECT_ROOT
    / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
)
W3_AUDIT_PATH = HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
W4_NOISE_PATH = HERE / "P7-W4-TIMING-NOISE-ANALYSIS.json"
DESTINATION = (
    PROJECT_ROOT
    / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01"
)
PARENT_SHA256 = "54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd"
TYPED_EXCLUSION = "development-epfl-sqrt-31cdaf5d0213"
ANCHOR_CASE_IDS = (
    "development-e3-e3c-k12-xor_dom-shared-2-8f5e66e2839b",
    "development-epfl-dec-ac01ccb8dc43",
)
POLICY_BLOCKS = {"p7-ir": 8, "p7-relation": 20}
ANCHOR_BLOCKS = {"p7-ir": 8, "p7-relation": 10}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ordered_policy_cases(parent: dict, policy_id: str) -> list[str]:
    cases = {case["case_id"]: case for case in parent["cases"]}
    policy = next(row for row in parent["schedule_policies"] if row["policy_id"] == policy_id)
    ordered = []
    for row in policy["order_ledger"]:
        case_id = row["case_id"]
        case = cases[case_id]
        if (
            case["role"] in {"development", "regression"}
            and policy["task"] in case["tasks"]
            and case_id not in ordered
        ):
            ordered.append(case_id)
    return ordered


def balanced_partitions(parent: dict, eligible: list[str]) -> tuple[list[str], list[str], list[dict]]:
    """Split pre-timing cases evenly within role/source-kind strata."""
    cases = {case["case_id"]: case for case in parent["cases"]}
    groups: dict[tuple[str, str], list[str]] = {}
    for case_id in eligible:
        case = cases[case_id]
        groups.setdefault((case["role"], case["kind"]), []).append(case_id)

    selected = {"a": [], "b": []}
    ledger = []
    for stratum in sorted(groups):
        ordered = sorted(groups[stratum], key=lambda value: hashlib.sha256(value.encode()).hexdigest())
        for position, case_id in enumerate(ordered):
            shard = "a" if position % 2 == 0 else "b"
            selected[shard].append(case_id)
            ledger.append(
                {
                    "case_id": case_id,
                    "cluster_id": cases[case_id]["cluster_id"],
                    "role": cases[case_id]["role"],
                    "kind": cases[case_id]["kind"],
                    "stratum": list(stratum),
                    "selection_key": hashlib.sha256(case_id.encode()).hexdigest(),
                    "shard": shard,
                }
            )
    parent_position = {case_id: position for position, case_id in enumerate(eligible)}
    shard_a = sorted(selected["a"], key=parent_position.__getitem__)
    shard_b = sorted(selected["b"], key=parent_position.__getitem__)
    if len(shard_a) != 29 or len(shard_b) != 28 or set(shard_a).intersection(shard_b):
        raise RuntimeError("W5 balanced partition cardinality changed")
    if set(shard_a).union(shard_b) != set(eligible):
        raise RuntimeError("W5 balanced partition coverage changed")
    return shard_a, shard_b, ledger


def derive(parent: dict, *, policy_id: str, case_ids: list[str], partition_id: str) -> dict:
    selected = set(case_ids)
    if len(selected) != len(case_ids):
        raise RuntimeError("duplicate W5 derived case")
    policy = next(row for row in parent["schedule_policies"] if row["policy_id"] == policy_id)
    derived = copy.deepcopy(parent)
    derived["cases"] = [case for case in parent["cases"] if case["case_id"] in selected]
    if len(derived["cases"]) != len(selected):
        raise RuntimeError("W5 derived case unavailable")
    normalized = {field: value for field, value in policy.items() if field != "order_ledger"}
    normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
    derived["schedule_policies"] = [normalized]
    provenance = dict(derived["provenance"])
    provenance["w5_development_partition"] = {
        "schema": "cm-comparative-p7-w5-development-partition/v1",
        "parent_freeze_sha256": parent["freeze_sha256"],
        "partition_id": partition_id,
        "policy_id": policy_id,
        "case_count": len(case_ids),
        "selected_case_ids_in_parent_order": case_ids,
        "selected_case_ids_sha256": digest(case_ids),
        "typed_feasibility_exclusion": TYPED_EXCLUSION,
        "case_selection_uses_comparative_timing": False,
        "shard_size_uses_w4_resource_timing": True,
    }
    derived["provenance"] = provenance
    core = {field: value for field, value in derived.items() if field != "freeze_sha256"}
    derived["freeze_sha256"] = digest(core)
    validate_freeze(derived)
    check = verify_sources(derived, PROJECT_ROOT)
    if check.get("verified") is not True:
        raise RuntimeError("W5 derived sources do not verify")
    return derived


def validate_inputs(parent: dict, w3: dict, w4: dict) -> tuple[list[str], list[str], list[str], list[dict]]:
    validate_freeze(parent)
    if parent.get("freeze_sha256") != PARENT_SHA256:
        raise RuntimeError("P6 parent freeze identity changed")
    if (
        w3.get("status") != "passed_with_one_shared_oracle_feasibility_exclusion"
        or w3.get("combined", {}).get("excluded_case") != TYPED_EXCLUSION
        or w3.get("sqrt_exclusion", {}).get("policy_independent_oracle_generator") is not True
        or w3.get("policies", {}).get("p7-ir", {}).get("verified_cases") != 57
        or w3.get("policies", {}).get("p7-relation", {}).get("verified_cases") != 57
    ):
        raise RuntimeError("W3 typed feasibility evidence changed")
    relation_noise = w4.get("policies", {}).get("p7-relation", {})
    ir_noise = w4.get("policies", {}).get("p7-ir", {})
    if (
        w4.get("verified") is not True
        or relation_noise.get("conditional_extension_indicated_by_frozen_rule") is not True
        or ir_noise.get("conditional_extension_indicated_by_frozen_rule") is not False
    ):
        raise RuntimeError("W4 frozen extension decision changed")
    ir_cases = ordered_policy_cases(parent, "p7-ir")
    relation_cases = ordered_policy_cases(parent, "p7-relation")
    if ir_cases != relation_cases or len(ir_cases) != 58 or TYPED_EXCLUSION not in ir_cases:
        raise RuntimeError("P7 eligible case identity changed")
    eligible = [case_id for case_id in ir_cases if case_id != TYPED_EXCLUSION]
    shard_a, shard_b, ledger = balanced_partitions(parent, eligible)
    return eligible, shard_a, shard_b, ledger


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError(f"W5 freeze already exists: {DESTINATION}")
    parent = load(PARENT_PATH)
    w3 = load(W3_AUDIT_PATH)
    w4 = load(W4_NOISE_PATH)
    eligible, shard_a, shard_b, selection_ledger = validate_inputs(parent, w3, w4)
    case_map = {case["case_id"]: case for case in parent["cases"]}
    if not all(case_id in eligible for case_id in ANCHOR_CASE_IDS):
        raise RuntimeError("W5 diagnostic anchor disappeared")
    if {case_map[case_id]["kind"] for case_id in ANCHOR_CASE_IDS} != {"expression_jsonl_member", "blif"}:
        raise RuntimeError("W5 diagnostic anchors no longer cover synthetic and natural cases")

    definitions = []
    derived_freezes = {}
    for policy_id in ("p7-ir", "p7-relation"):
        arms = 4 if policy_id == "p7-ir" else 5
        for suffix, case_ids in (("a", shard_a), ("b", shard_b)):
            partition_id = f"{policy_id}-{suffix}"
            freeze = derive(parent, policy_id=policy_id, case_ids=case_ids, partition_id=partition_id)
            derived_freezes[partition_id] = freeze
            definitions.append(
                {
                    "partition_id": partition_id,
                    "policy_id": policy_id,
                    "kind": "primary",
                    "case_count": len(case_ids),
                    "blocks": POLICY_BLOCKS[policy_id],
                    "arms": arms,
                    "planned_cells": len(case_ids) * POLICY_BLOCKS[policy_id] * arms,
                    "freeze_sha256": freeze["freeze_sha256"],
                    "case_ids": case_ids,
                }
            )
        anchor_id = f"{policy_id}-anchor"
        anchor_freeze = derive(
            parent,
            policy_id=policy_id,
            case_ids=list(ANCHOR_CASE_IDS),
            partition_id=anchor_id,
        )
        derived_freezes[anchor_id] = anchor_freeze
        definitions.append(
            {
                "partition_id": anchor_id,
                "policy_id": policy_id,
                "kind": "diagnostic_anchor",
                "case_count": len(ANCHOR_CASE_IDS),
                "blocks": ANCHOR_BLOCKS[policy_id],
                "arms": arms,
                "planned_cells": len(ANCHOR_CASE_IDS) * ANCHOR_BLOCKS[policy_id] * arms,
                "freeze_sha256": anchor_freeze["freeze_sha256"],
                "case_ids": list(ANCHOR_CASE_IDS),
            }
        )

    primary = [row for row in definitions if row["kind"] == "primary"]
    anchors = [row for row in definitions if row["kind"] == "diagnostic_anchor"]
    expected_primary = {
        "p7-ir-a": 928,
        "p7-ir-b": 896,
        "p7-relation-a": 2900,
        "p7-relation-b": 2800,
    }
    if {row["partition_id"]: row["planned_cells"] for row in primary} != expected_primary:
        raise RuntimeError("W5 primary cell contract changed")
    if {row["partition_id"]: row["planned_cells"] for row in anchors} != {
        "p7-ir-anchor": 64,
        "p7-relation-anchor": 100,
    }:
        raise RuntimeError("W5 anchor cell contract changed")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=DESTINATION.name + ".tmp-", dir=DESTINATION.parent))
    for partition_id, freeze in derived_freezes.items():
        folder = temporary / partition_id
        folder.mkdir()
        write_json(folder / "freeze.json", freeze)
        write_json(folder / "source-check.json", verify_sources(freeze, PROJECT_ROOT))

    campaign = {
        "schema": "cm-comparative-p7-w5-development-campaign/v1",
        "parent_freeze_sha256": parent["freeze_sha256"],
        "w3_audit_sha256": sha256(W3_AUDIT_PATH),
        "w4_noise_analysis_sha256": sha256(W4_NOISE_PATH),
        "parent_eligible_cases": 58,
        "principal_cases": len(eligible),
        "typed_retained_exclusions": [
            {
                "case_id": TYPED_EXCLUSION,
                "reason": "W3 policy-independent oracle generation exceeded its 780-second stage limit",
                "rerun_in_w5": False,
                "counts_as_success": False,
                "retained_in_completion_frontier": True,
            }
        ],
        "case_partition_rule": "within each frozen role x source-kind stratum, sort by SHA-256(case_id) and alternate A/B",
        "case_partition_uses_comparative_timing": False,
        "shard_sizing_uses_w4_resource_timing": True,
        "relation_extension_triggered_by_w4_frozen_noise_rule": True,
        "ir_extension_triggered": False,
        "definitions": definitions,
        "diagnostic_anchor_case_ids": list(ANCHOR_CASE_IDS),
        "primary_cells": sum(row["planned_cells"] for row in primary),
        "diagnostic_cells_per_ir_allocation": 64,
        "diagnostic_cells_per_relation_allocation": 100,
        "total_cells_including_repeated_per_allocation_anchors": (
            sum(row["planned_cells"] for row in primary) + 2 * 64 + 2 * 100
        ),
    }
    write_json(temporary / "campaign.json", campaign)
    write_json(
        temporary / "selection-ledger.json",
        {
            "schema": "cm-comparative-p7-w5-development-selection/v1",
            "parent_freeze_sha256": parent["freeze_sha256"],
            "typed_exclusion": TYPED_EXCLUSION,
            "eligible_case_ids_in_parent_order": eligible,
            "selection_ledger": selection_ledger,
            "selection_ledger_sha256": digest(selection_ledger),
        },
    )
    verification = {
        "schema": "cm-comparative-p7-w5-development-freeze-verification/v1",
        "verified": True,
        "parent_eligible_cases": 58,
        "principal_cases": 57,
        "independent_clusters": len({case_map[case_id]["cluster_id"] for case_id in eligible}),
        "shard_case_counts": {"a": len(shard_a), "b": len(shard_b)},
        "primary_cells": campaign["primary_cells"],
        "total_cells_including_diagnostics": campaign["total_cells_including_repeated_per_allocation_anchors"],
        "typed_exclusion_retained": True,
        "relation_maximum_blocks_frozen": True,
        "ir_minimum_blocks_frozen": True,
        "all_sources_verified": True,
        "complete_counterbalance_cycles": True,
        "partition_coverage_exact": set(shard_a).union(shard_b) == set(eligible),
        "partition_overlap_empty": not set(shard_a).intersection(shard_b),
        "freeze_hashes": {key: value["freeze_sha256"] for key, value in derived_freezes.items()},
    }
    write_json(temporary / "verification.json", verification)
    readme = f"""# P7 W5 development freeze v1

This package freezes the principal P7A/P7B development ablation as four
sequential Runpod allocations. It projects the original pre-timing V4 corpus
into two balanced shards per policy without changing cases, arms, metrics, or
within-case schedules.

The W3 `sqrt` case remains a typed feasibility exclusion: its policy-independent
oracle generation exceeded 780 seconds, so repeating it inside a 20-minute W5
allocation would prevent any measured cells from running. It is retained in
completion/frontier reporting and is not counted as a success. The remaining
57 cases are partitioned 29/28 within role and source-kind strata.

IR uses the frozen 8-block minimum. W4's predeclared 5% noise rule triggered the
relation extension, so both relation shards run the frozen 20-block maximum.
Each allocation also runs the same two-case synthetic/natural diagnostic anchor
as a separately labeled output; anchors are not independent primary formulas.

Primary cells: {campaign['primary_cells']}. Cells including repeated diagnostic
anchors: {campaign['total_cells_including_repeated_per_allocation_anchors']}.
"""
    (temporary / "README.md").write_text(readme, encoding="utf-8")
    os.replace(temporary, DESTINATION)
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
