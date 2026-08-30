"""Offline validation for the final W3 development-tail partitions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import linux_supervisor, p7_runner
from validate_p7_w3_split_v4 import derive, ordered_development_ids


HERE = Path(__file__).resolve().parent
FREEZE_PATH = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
BUNDLE_PATH = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
OUTPUT = HERE / "P7-W3-TAIL-V6-OFFLINE-VALIDATION.json"
PARTITIONS = {
    "ir-development-b-light": ("p7-ir", 17, 15, 60),
    "ir-development-sqrt": ("p7-ir", 32, 1, 4),
    "ir-development-square": ("p7-ir", 33, 1, 4),
    "relation-development-a": ("p7-relation", 0, 17, 85),
    "relation-development-b-light": ("p7-relation", 17, 15, 75),
    "relation-development-sqrt": ("p7-relation", 32, 1, 5),
    "relation-development-square": ("p7-relation", 33, 1, 5),
}


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
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
        remote = HERE / ("runpod_p7_w3_tail_remote_v6_" + partition_id.replace("-", "_") + ".py")
        text = remote.read_text(encoding="utf-8")
        selected = set(plan["case_ids"])
        parent = ordered_development_ids(freeze, policy_id)[offset:offset + limit]
        selected_by_policy[policy_id].append(selected)
        rows.append({
            "partition_id": partition_id,
            "policy_id": policy_id,
            "offset": offset,
            "cases": len(plan["case_ids"]),
            "cells": len(plan["cells"]),
            "derived_freeze_sha256": derived["freeze_sha256"],
            "parent_case_set_matches": selected == set(parent),
            "remote_sha256": hashlib.sha256(remote.read_bytes()).hexdigest(),
            "remote_constants_match": all((
                f'SHARD_ID = "{partition_id}"' in text,
                f"CASE_OFFSET = {offset}" in text,
                f"CASE_LIMIT = {limit}" in text,
                '"--profile", "functional"' in text,
            )),
            "performance_measurement": plan["performance_measurement"],
            "counts_match": len(plan["case_ids"]) == limit and len(plan["cells"]) == cells,
        })

    ir_parent = set(ordered_development_ids(freeze, "p7-ir"))
    ir_prefix = set(ordered_development_ids(freeze, "p7-ir")[:17])
    ir_tail = set().union(*selected_by_policy["p7-ir"])
    relation_parent = set(ordered_development_ids(freeze, "p7-relation"))
    relation_all = set().union(*selected_by_policy["p7-relation"])
    coverage = {
        "p7-ir": {
            "parent_cases": len(ir_parent),
            "completed_prefix_cases": len(ir_prefix),
            "tail_cases": len(ir_tail),
            "tail_partitions_pairwise_disjoint": sum(map(len, selected_by_policy["p7-ir"])) == len(ir_tail),
            "prefix_disjoint_from_tail": ir_prefix.isdisjoint(ir_tail),
            "union_matches_parent": ir_prefix | ir_tail == ir_parent,
        },
        "p7-relation": {
            "parent_cases": len(relation_parent),
            "partition_cases": [len(value) for value in selected_by_policy["p7-relation"]],
            "partitions_pairwise_disjoint": sum(map(len, selected_by_policy["p7-relation"])) == len(relation_all),
            "union_matches_parent": relation_all == relation_parent,
        },
    }
    report = {
        "schema": "cm-runpod-p7-w3-tail-offline-validation/v1",
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
        and coverage["p7-ir"]["parent_cases"] == 34
        and coverage["p7-ir"]["tail_cases"] == 17
        and coverage["p7-ir"]["tail_partitions_pairwise_disjoint"]
        and coverage["p7-ir"]["prefix_disjoint_from_tail"]
        and coverage["p7-ir"]["union_matches_parent"]
        and coverage["p7-relation"]["parent_cases"] == 34
        and coverage["p7-relation"]["partitions_pairwise_disjoint"]
        and coverage["p7-relation"]["union_matches_parent"]
    )
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
