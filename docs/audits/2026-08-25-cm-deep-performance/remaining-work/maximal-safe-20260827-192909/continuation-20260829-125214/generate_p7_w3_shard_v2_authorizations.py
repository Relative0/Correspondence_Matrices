"""Generate the four exact W3 shard V2 authorization records once."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECORDED_UTC = "2026-08-30T06:48:08.1883253Z"
SHARDS = {
    "ir-regression": ("p7-ir", "regression", 24, 96,
                      "9a855f9fab6b37fe67bf021132f6481ce747cdfa42239937a7978d4279091c8c"),
    "ir-development": ("p7-ir", "development", 34, 136,
                       "0931cf320b05f44048f465283facfe86da59e310b303e65f9731d900e1ce49d6"),
    "relation-regression": ("p7-relation", "regression", 24, 120,
                            "34bbe5857249629e3199ec1b9588613247eaa726ae8bad1c865d27407f652286"),
    "relation-development": ("p7-relation", "development", 34, 170,
                             "4c65a640b53978e722e9ce196a6280105de1bd3514bed7d84c36423f5cd5cc8e"),
}


def main() -> int:
    for shard_id, (policy, role, cases, cells, remote_sha256) in SHARDS.items():
        record = {
            "schema": "cm-runpod-p7-w3-shard-authorization/v2",
            "authorized": True,
            "recorded_utc": RECORDED_UTC,
            "authorization_basis": (
                "User standing authorization for necessary comparative reruns under USD 5; "
                "unchanged exact payload already explicitly authorized and disclosed; V2 removes "
                "the reconciled bootstrap-environment mismatch"
            ),
            "one_create": True,
            "no_replacement_within_this_controller": True,
            "external_source_upload_approved": True,
            "source_files": 96,
            "source_bytes": 19484163,
            "source_bundle_bytes": 3197013,
            "focused_tests": 42,
            "shard_id": shard_id,
            "shard_policy": policy,
            "shard_role": role,
            "shard_cases": cases,
            "shard_cells": cells,
            "fresh_cell_processes": cells,
            "blocks": 1,
            "campaign_shards": 4,
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
            ],
            "prior_no_create_attempts": ["p7-functional-scout-v4-freeze-closed-001"],
            "chunk_bytes": 262144,
            "proposal_sha256": "441cc41bab026503e77193b701223d0523c1f52b135c9d451decde1cc57fd7ee",
            "upload_manifest_sha256": "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74",
            "upload_bundle_sha256": "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
            "controller_sha256": "e3fa8b75caae1202666de12c94fe158f8e5352d1eac8808a9af00ee0def7d6e9",
            "preflight_sha256": "93153bdb47f00f385757b08415c4738e9febb4e598c65853502bcdbb0bb9ff89",
            "remote_program_sha256": remote_sha256,
            "bootstrap_sha256": "ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9",
        }
        path = HERE / ("HTTP-P7-W3-SHARD-" + shard_id.upper() + "-V2-AUTHORIZED-20260830.json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
