"""Generate three continuation authorizations after the V4 no-create refusal."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECORDED_UTC = "2026-08-30T07:45:00Z"
PARTITIONS = {
    "ir-development-b": ("p7-ir", 17, 17, 68, "b25abec6d7a706e78a41eb42c779083a4551add99816634992409089267beecf"),
    "relation-development-a": ("p7-relation", 0, 17, 85, "728697114eb1cd9a9bbc231b3395462db97f1a5692a93d75a6764fbe3a6c29e8"),
    "relation-development-b": ("p7-relation", 17, 17, 85, "a6e5369b43d73679f46e69304b63c2e1369e4b4cc66e5075c96798981157187c"),
}


def main() -> int:
    for partition_id, (policy, offset, cases, cells, remote_sha256) in PARTITIONS.items():
        record = {
            "schema": "cm-runpod-p7-w3-split-authorization/v5",
            "authorized": True,
            "recorded_utc": RECORDED_UTC,
            "authorization_basis": (
                "User standing authorization for necessary comparative runs and retries under USD 5; "
                "the exact 96-file payload remains unchanged; V4 ir-development-b issued no create "
                "because unrelated inventory appeared after preflight"
            ),
            "one_create": True,
            "no_replacement_within_this_controller": True,
            "external_source_upload_approved": True,
            "source_files": 96,
            "source_bytes": 19484163,
            "source_bundle_bytes": 3197013,
            "focused_tests": 42,
            "shard_id": partition_id,
            "shard_policy": policy,
            "shard_role": "development",
            "shard_cases": cases,
            "shard_cells": cells,
            "fresh_cell_processes": cells,
            "blocks": 1,
            "campaign_shards": 3,
            "case_offset": offset,
            "case_limit": cases,
            "partition_validation_ready": True,
            "sequential_shards_only": True,
            "performance_ranking": False,
            "source_builds_allowed": [],
            "system_packages_allowed": [],
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "lifetime_seconds": 1200,
            "phase_cap_usd": 0.1,
            "campaign_cap_usd": 0.2,
            "same_exact_external_payload_authorization": True,
            "payload_previously_disclosed_to_runpod": True,
            "prior_attempt_pod_ids": [
                "1xh6csc4oxy067", "2fzt8mu6ji6nmw", "r044pqp2vgp7cy",
                "6mlqn19hnco1b0", "d9z39u7pzvbju8", "pnpc0c0t6gu358",
                "9xjz22tif2ctrv", "alu08d0mlf02ba", "1uqsgeb7vpzihb",
            ],
            "prior_no_create_attempts": [
                "p7-functional-scout-v4-freeze-closed-001",
                "p7-w3-split-ir-development-b-v4-001",
            ],
            "chunk_bytes": 262144,
            "proposal_sha256": "77ac918b3dc9304f9e1b5b199e80230e36f666ced46f1ebf0ff1f5bf1b69a6fb",
            "upload_manifest_sha256": "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74",
            "upload_bundle_sha256": "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
            "controller_sha256": "c06a0cc3cffb43452d1644bc4494efd4100ef3d4627a50343c213848ee138d9f",
            "preflight_sha256": "d7954de8d0c8f2becfb28ba95341cb1e9854295a34bc4c5addf8536676e886e5",
            "remote_program_sha256": remote_sha256,
            "bootstrap_sha256": "ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9",
            "partition_validation_sha256": "4f2779fd5d5a96a9ba5dd7e0e4ceafb730dc4f75e8bde68e3f6b288ade9ff056",
        }
        path = HERE / ("HTTP-P7-W3-SPLIT-" + partition_id.upper() + "-V5-AUTHORIZED-20260830.json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
