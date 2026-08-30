"""Offline validation for the four derived W3 functional partitions."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import linux_supervisor, p7_runner
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze


HERE = Path(__file__).resolve().parent
FREEZE_PATH = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
BUNDLE_PATH = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
OUTPUT = HERE / "P7-W3-SPLIT-V4-OFFLINE-VALIDATION.json"
PARTITIONS = {
    "ir-development-a": ("p7-ir", 0, 17, 68),
    "ir-development-b": ("p7-ir", 17, 17, 68),
    "relation-development-a": ("p7-relation", 0, 17, 85),
    "relation-development-b": ("p7-relation", 17, 17, 85),
}


def ordered_development_ids(freeze: dict, policy_id: str) -> list[str]:
    cases = {row["case_id"]: row for row in freeze["cases"]}
    policy = next(row for row in freeze["schedule_policies"] if row["policy_id"] == policy_id)
    ordered = []
    for row in policy["order_ledger"]:
        case = cases[row["case_id"]]
        if case["role"] == "development" and row["case_id"] not in ordered:
            ordered.append(row["case_id"])
    return ordered


def derive(freeze: dict, partition_id: str, policy_id: str, offset: int, limit: int) -> dict:
    selected = ordered_development_ids(freeze, policy_id)[offset:offset + limit]
    selected_set = set(selected)
    policy = next(row for row in freeze["schedule_policies"] if row["policy_id"] == policy_id)
    derived = copy.deepcopy(freeze)
    derived["cases"] = [row for row in freeze["cases"] if row["case_id"] in selected_set]
    normalized = {key: value for key, value in policy.items() if key != "order_ledger"}
    normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
    derived["schedule_policies"] = [normalized]
    provenance = dict(derived["provenance"])
    provenance["functional_partition"] = {
        "schema": "cm-comparative-p7-functional-partition/v1",
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "partition_id": partition_id,
        "policy_id": policy_id,
        "role": "development",
        "case_offset": offset,
        "case_limit": limit,
        "selected_case_ids_in_parent_order": selected,
        "performance_measurement": False,
    }
    derived["provenance"] = provenance
    core = {key: value for key, value in derived.items() if key != "freeze_sha256"}
    derived["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
    validate_freeze(derived)
    return derived


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    validate_freeze(freeze)
    limits = linux_supervisor.Limits(
        timeout_seconds=30.0,
        rss_stop_bytes=1 << 30,
        stdout_bytes=p7_runner.MAX_WORKER_BYTES,
        stderr_bytes=256 << 10,
        input_bytes=p7_runner.MAX_REQUEST_BYTES,
        processes=4,
    )
    rows = []
    selected_by_policy: dict[str, list[set[str]]] = {"p7-ir": [], "p7-relation": []}
    for partition_id, (policy_id, offset, limit, cells) in PARTITIONS.items():
        derived = derive(freeze, partition_id, policy_id, offset, limit)
        plan = p7_runner.build_plan(
            derived,
            policy_id=policy_id,
            roles=("development",),
            blocks=1,
            worker_source_manifest_sha256="0" * 64,
            resource_limits=p7_runner.limits_record(limits),
            profile="functional",
        )
        remote = HERE / ("runpod_p7_w3_split_remote_v4_" + partition_id.replace("-", "_") + ".py")
        remote_text = remote.read_text(encoding="utf-8")
        selected = plan["case_ids"]
        parent_selected = ordered_development_ids(freeze, policy_id)[offset:offset + limit]
        selected_by_policy[policy_id].append(set(selected))
        rows.append({
            "partition_id": partition_id,
            "policy_id": policy_id,
            "offset": offset,
            "cases": len(selected),
            "cells": len(plan["cells"]),
            "derived_freeze_sha256": derived["freeze_sha256"],
            "parent_case_set_matches": set(selected) == set(parent_selected),
            "remote_sha256": hashlib.sha256(remote.read_bytes()).hexdigest(),
            "remote_constants_match": all((
                f'SHARD_ID = "{partition_id}"' in remote_text,
                f"CASE_OFFSET = {offset}" in remote_text,
                f"CASE_LIMIT = {limit}" in remote_text,
                '"--profile", "functional"' in remote_text,
                "derive_freeze_partition(parent_freeze_path)" in remote_text,
            )),
            "performance_measurement": plan["performance_measurement"],
            "counts_match": len(selected) == limit and len(plan["cells"]) == cells,
        })

    coverage = {}
    for policy_id, halves in selected_by_policy.items():
        parent = set(ordered_development_ids(freeze, policy_id))
        coverage[policy_id] = {
            "parent_cases": len(parent),
            "partition_cases": [len(value) for value in halves],
            "disjoint": halves[0].isdisjoint(halves[1]),
            "union_matches_parent": halves[0] | halves[1] == parent,
        }
    report = {
        "schema": "cm-runpod-p7-w3-split-offline-validation/v1",
        "parent_freeze_sha256": freeze["freeze_sha256"],
        "source_bundle_sha256": hashlib.sha256(BUNDLE_PATH.read_bytes()).hexdigest(),
        "partitions": rows,
        "coverage": coverage,
    }
    report["ready"] = bool(
        report["source_bundle_sha256"]
        == "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"
        and all(row["parent_case_set_matches"] and row["remote_constants_match"]
                and row["counts_match"] and row["performance_measurement"] is False for row in rows)
        and all(value["parent_cases"] == 34 and value["disjoint"]
                and value["union_matches_parent"] for value in coverage.values())
    )
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
