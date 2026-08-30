"""Generate seven exact authorizations for the final W3 development tail."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECORDED_UTC = "2026-08-30T08:10:00Z"
PARTITIONS = {
    "ir-development-b-light": ("p7-ir", 17, 15, 60, "8d575cd31e667aa67a41fdde4614a43515ce942b4327bc583741cd1ad491d790"),
    "ir-development-sqrt": ("p7-ir", 32, 1, 4, "c2bac6031ffb3e849c3f896e94d072fc7e77d8a584c8b40514bfb6c859ca038f"),
    "ir-development-square": ("p7-ir", 33, 1, 4, "85c926d262e328f302d2abc82a0cae8c0648a9eae44804f0f7a7554518dcab78"),
    "relation-development-a": ("p7-relation", 0, 17, 85, "728697114eb1cd9a9bbc231b3395462db97f1a5692a93d75a6764fbe3a6c29e8"),
    "relation-development-b-light": ("p7-relation", 17, 15, 75, "a682f81919f9a67a5b99bbd32bc9b11eab1b709f58fcc00ded4d76bda7651ca1"),
    "relation-development-sqrt": ("p7-relation", 32, 1, 5, "b6f896f88482f9d7b3c2f6eb1c82bf207fd5a03235b2192434248822e592c682"),
    "relation-development-square": ("p7-relation", 33, 1, 5, "b78213a4252bac35ec692358a9072367fbdc5c44519643d67e71c50282c940ef"),
}


def main() -> int:
    for partition_id, (policy, offset, cases, cells, remote_sha256) in PARTITIONS.items():
        record = {
            "schema": "cm-runpod-p7-w3-tail-authorization/v6",
            "authorized": True,
            "recorded_utc": RECORDED_UTC,
            "authorization_basis": (
                "User standing authorization for necessary comparative runs and retries under USD 5; "
                "the exact 96-file payload remains unchanged; V6 isolates the final development tail "
                "after the reconciled 17-case V5 sizing timeout"
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
            "campaign_shards": 7,
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
                "dop3aggj7vsefp",
            ],
            "prior_no_create_attempts": [
                "p7-functional-scout-v4-freeze-closed-001",
                "p7-w3-split-ir-development-b-v4-001",
            ],
            "chunk_bytes": 262144,
            "proposal_sha256": "47bfffb9927bdda633e3871948a2f33887d0825d5408b9a98f4fb72ed03c4db5",
            "upload_manifest_sha256": "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74",
            "upload_bundle_sha256": "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
            "controller_sha256": "071629088e68c4b18c98ca9898afe95a17d8d504cc33aebaa1c24ecc120b97c8",
            "preflight_sha256": "0f0aa97febc89fb30ce4f52802dc534f86fbfc38173d16a828cc176bbb9c053f",
            "remote_program_sha256": remote_sha256,
            "bootstrap_sha256": "ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9",
            "partition_validation_sha256": "3f4baa72fca2eb71c93833142b166f81cf967cb8455dfe7988a82a8da32ac126",
        }
        path = HERE / ("HTTP-P7-W3-TAIL-" + partition_id.upper() + "-V6-AUTHORIZED-20260830.json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
