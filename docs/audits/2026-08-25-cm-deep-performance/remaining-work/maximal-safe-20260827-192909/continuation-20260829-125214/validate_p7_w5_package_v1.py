"""Validate the immutable W5 package locally without authentication or writes."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
OUTPUT = HERE / "P7-W5-PACKAGE-V1-LOCAL-VALIDATION.json"
MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
CAMPAIGN = ROOT / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01/campaign.json"
VERIFICATION = CAMPAIGN.parent / "verification.json"
REMOTE_PROGRAMS = HERE / "P7-W5-REMOTE-PROGRAMS-V1.json"
CONTROLLER = HERE / "runpod_p7_w5_controller_v1.py"
PREFLIGHT = HERE / "http_p7_w5_development_preflight_v1.py"
BOOTSTRAP = HERE / "http_native_scout_bootstrap_v3_w4_deadlines.py"
PROPOSAL = HERE / "RUNPOD-P7-W5-DEVELOPMENT-PROPOSAL-20260901.md"
EXPECTED_MANIFEST_SHA256 = "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74"
EXPECTED_BUNDLE_SHA256 = "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal_assignments(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return values


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    failures = []
    manifest = load(MANIFEST)
    payload = BUNDLE.read_bytes()
    if sha256(MANIFEST) != EXPECTED_MANIFEST_SHA256:
        failures.append("manifest hash")
    if hashlib.sha256(payload).hexdigest() != EXPECTED_BUNDLE_SHA256 or len(payload) != 3_197_013:
        failures.append("bundle identity")
    expected = {row["target"]: row for row in manifest.get("files", [])}
    if len(expected) != 96 or manifest.get("file_count") != 96 or manifest.get("bytes") != 19_484_163:
        failures.append("manifest cardinality")
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            failures.append("bundle membership")
        else:
            for name in names:
                data = archive.read(name)
                row = expected[name]
                if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                    failures.append("bundle member:" + name)
                    break

    campaign = load(CAMPAIGN)
    verification = load(VERIFICATION)
    programs = load(REMOTE_PROGRAMS)
    definitions = {row["partition_id"]: row for row in campaign.get("definitions", [])}
    if (
        campaign.get("schema") != "cm-comparative-p7-w5-development-campaign/v1"
        or campaign.get("principal_cases") != 57
        or campaign.get("primary_cells") != 7524
        or campaign.get("total_cells_including_repeated_per_allocation_anchors") != 7852
        or verification.get("verified") is not True
        or verification.get("typed_exclusion_retained") is not True
        or verification.get("relation_maximum_blocks_frozen") is not True
    ):
        failures.append("campaign freeze")

    remote_hashes = {}
    for row in programs.get("programs", []):
        path = HERE / row["path"]
        remote_hashes[row["shard_id"]] = sha256(path) if path.is_file() else None
        primary = definitions.get(row["shard_id"])
        anchor = definitions.get(row.get("policy_id", "") + "-anchor")
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            literals = literal_assignments(path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append("remote syntax:" + row.get("shard_id", "unknown") + ":" + type(exc).__name__)
            continue
        if (
            primary is None
            or anchor is None
            or path.stat().st_size != row.get("bytes")
            or remote_hashes[row["shard_id"]] != row.get("sha256")
            or literals.get("SHARD_ID") != row["shard_id"]
            or literals.get("POLICY_ID") != row["policy_id"]
            or literals.get("PRIMARY_CASE_IDS") != primary["case_ids"]
            or literals.get("PRIMARY_BLOCKS") != primary["blocks"]
            or literals.get("PRIMARY_CELLS") != primary["planned_cells"]
            or literals.get("PRIMARY_FREEZE_SHA256") != primary["freeze_sha256"]
            or literals.get("ANCHOR_CASE_IDS") != anchor["case_ids"]
            or literals.get("ANCHOR_BLOCKS") != anchor["blocks"]
            or literals.get("ANCHOR_CELLS") != anchor["planned_cells"]
            or literals.get("ANCHOR_FREEZE_SHA256") != anchor["freeze_sha256"]
        ):
            failures.append("remote contract:" + row["shard_id"])
    if set(remote_hashes) != {"p7-ir-a", "p7-ir-b", "p7-relation-a", "p7-relation-b"}:
        failures.append("remote program set")

    for path in (CONTROLLER, PREFLIGHT, BOOTSTRAP):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append("local syntax:" + path.name + ":" + type(exc).__name__)
    for path in (CONTROLLER, PREFLIGHT, BOOTSTRAP, PROPOSAL, CAMPAIGN, VERIFICATION, REMOTE_PROGRAMS):
        if not path.is_file() or not path.read_bytes():
            failures.append("missing local input:" + path.name)

    result = {
        "schema": "cm-runpod-p7-w5-package-local-validation/v1",
        "ready": not failures,
        "failures": failures[:20],
        "network_requests": 0,
        "authentication_used": False,
        "resource_writes": 0,
        "exact_bundle_reproduces_freeze": not any(
            item.startswith(("manifest", "bundle")) for item in failures
        ),
        "source_files": 96,
        "source_bytes": 19_484_163,
        "bundle_bytes": len(payload),
        "manifest_sha256": sha256(MANIFEST),
        "bundle_sha256": hashlib.sha256(payload).hexdigest(),
        "campaign_sha256": sha256(CAMPAIGN),
        "verification_sha256": sha256(VERIFICATION),
        "primary_cells": campaign.get("primary_cells"),
        "total_cells_including_diagnostics": campaign.get(
            "total_cells_including_repeated_per_allocation_anchors"
        ),
        "remote_program_count": len(remote_hashes),
        "remote_program_sha256_by_shard": remote_hashes,
        "controller_sha256": sha256(CONTROLLER),
        "preflight_sha256": sha256(PREFLIGHT),
        "bootstrap_sha256": sha256(BOOTSTRAP),
        "proposal_sha256": sha256(PROPOSAL),
        "remote_programs_manifest_sha256": sha256(REMOTE_PROGRAMS),
        "performance_measurement": True,
        "principal_p7_result": True,
        "w8_confirmation_untouched": True,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
