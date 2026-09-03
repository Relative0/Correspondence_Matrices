"""Prepare the corrected query-ladder execution contract and upload manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_query_ladder_followup import verify_followup_freeze


HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
FREEZE = ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
FREEZE_VERIFICATION = FREEZE.parent / "VERIFICATION.json"
PARENT_ANALYSIS = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json"
PARENT_MANIFEST = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/UPLOAD_MANIFEST.json"
ORACLES = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
CONTRACT = HERE / "EXECUTION_CONTRACT.json"
PROTOCOL = HERE / "PROTOCOL.md"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
RUN_NAME = "architecture-query-ladder-linux-gcc-20260903-001"
IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
RESULT_CAP_BYTES = 48 << 20
TOTAL_CELLS = 27_648
PER_QUERY_CELLS = 6_912

NUMPY = {
    "name": "numpy", "version": "2.3.2",
    "requirement": "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f",
    "sha256": "938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f",
}
SIX = {
    "name": "six", "version": "1.17.0", "filename": "six-1.17.0-py2.py3-none-any.whl",
    "bytes": 11_050, "sha256": "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274",
    "url": "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl",
}
NETWORKX = {
    "name": "networkx", "version": "3.6.1", "filename": "networkx-3.6.1-py3-none-any.whl",
    "bytes": 2_068_504, "sha256": "d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762",
    "url": "https://files.pythonhosted.org/packages/9e/c9/b2622292ea83fbb4ec318f5b9ab867d0a28ab43c5717bb85b0a5f6b3b0a4/networkx-3.6.1-py3-none-any.whl",
}
PYTHON_SAT = {
    "name": "python-sat", "version": "1.9.dev15",
    "filename": "python_sat-1.9.dev15-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
    "bytes": 3_943_142, "sha256": "fd55285f4ef679aaa62699660121423ec35b97324095ae34db4edb0356422a45",
    "url": "https://files.pythonhosted.org/packages/cf/96/4290b2af2853f81061b9aa6ddf118523bc9b1d922842ee78124844ee35d9/python_sat-1.9.dev15-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
}

NEW_RUNTIME_SOURCES = (
    "cmbench/comparative/architecture_query_ladder_followup.py",
    "cmbench/comparative/architecture_query_ladder_freeze.py",
    "scripts/cm_architecture_query_ladder_campaign.py",
    "scripts/crse_verify_architecture_query_ladder_freeze.py",
    "scripts/crse_verify_architecture_query_ladder_campaign.py",
    "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json",
    "docs/recognition/architecture_query_ladder_followup_freeze_20260903/VERIFICATION.json",
    "docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")


def main() -> int:
    if HERE.exists():
        raise SystemExit("refusing to overwrite query-ladder execution package")
    freeze = _load(FREEZE)
    verified = verify_followup_freeze(freeze, ROOT)
    recorded_verification = _load(FREEZE_VERIFICATION)
    if verified != recorded_verification or verified["planned_cells"] != TOTAL_CELLS:
        raise ValueError("query-ladder freeze verification mismatch")
    parent_analysis = _load(PARENT_ANALYSIS)
    if parent_analysis.get("status") != "verified_interpretation_complete":
        raise ValueError("parent architecture analysis is not complete")
    contract = {
        "schema": "cm-architecture-query-ladder-execution-contract/v1",
        "status": "prepared_not_authorized",
        "date": "2026-09-03",
        "run_name": RUN_NAME,
        "source_checkpoint": freeze["source_checkpoint"],
        "freeze_file_sha256": _sha256(FREEZE),
        "freeze_canonical_sha256": freeze["freeze_sha256"],
        "freeze_verification_sha256": _sha256(FREEZE_VERIFICATION),
        "oracles_sha256": _sha256(ORACLES),
        "parent_analysis_sha256": _sha256(PARENT_ANALYSIS),
        "schedule": {
            "total_cells": TOTAL_CELLS,
            "query_counts": [1, 4, 16, 64],
            "cells_per_query_count": PER_QUERY_CELLS,
            "runnable_cases": 54,
            "arms": 8,
            "counterbalance_blocks": 16,
            "expected_counts": {"ok": TOTAL_CELLS, "refused": 0, "failed": 0},
        },
        "memory": freeze["measurement_contract"]["memory"],
        "runtime": {
            "image": IMAGE,
            "python": "3.13.15",
            "compiler": "GCC-family cc",
            "compiler_flags": ["-std=c11", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-shared", "-fPIC"],
            "dependencies": [NUMPY, SIX, NETWORKX, PYTHON_SAT],
        },
        "limits": {
            "workload_wall_seconds": 420,
            "remote_command_seconds": 480,
            "result_cap_bytes": RESULT_CAP_BYTES,
            "one_cloud_create": True,
            "automatic_replacement": False,
            "cleanup_seconds": 600,
            "reconciliation_seconds": 720,
        },
        "permissions": {
            "local_functional_validation": True,
            "local_timing": False,
            "runpod_authorization_request": True,
            "runpod_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_update": False,
            "publication": False,
        },
        "claim_boundary": freeze["publication_gates"],
    }
    _write_new(CONTRACT, contract)
    protocol = f"""# Corrected query-ladder and isolated-memory execution protocol

This package is a source-bound Lane-B follow-up to architecture comparison retry 002.
It preserves the same 54 cases, eight exact residual-relation arms, and 16 balanced arm
orders, but creates a distinct timed cell at q1, q4, q16, and q64. The schedule therefore
contains {TOTAL_CELLS:,} rows ({PER_QUERY_CELLS:,} per query count). It does not rerun or
revise the complete-vector, multi-root, or smaller-task lanes.

Every decision-bearing cell runs inside a fresh Linux fork child. Timing starts and ends
inside that child, so process-isolation launch cost is excluded from backend task time.
The parent records the child's total peak RSS from `wait4` and the inherited baseline
from `/proc/self/statm`, then reports their nonnegative difference. These are descriptive
per-cell host-memory measurements; publication still requires a second machine.

The required artifact at every query count is the ordered explicit residual-relation
prefix, including exact count, SAT flag, canonical witness, and digest. An independent
verifier must match every schedule position, timing sum, oracle digest, and memory field
before interpretation. The workload uses no network after dependency setup.

A later exact approval is limited to one Secure CPU Pod, one create and no replacement,
2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, a
$0.25/hour rate ceiling, a $0.05 total ceiling, cleanup within ten minutes, and inventory
reconciliation within twelve minutes. It authorizes no selector fitting, neural training,
production routing, website update, publication, commit, push, or reuse of an earlier
authorization.
"""
    _write_new(PROTOCOL, protocol)
    parent_manifest = _load(PARENT_MANIFEST)
    sources = {row["source"] for row in parent_manifest["files"]}
    sources.update(NEW_RUNTIME_SOURCES)
    sources.update(row["path"] for row in freeze["source_closure"])
    sources.update({CONTRACT.relative_to(ROOT).as_posix(), PROTOCOL.relative_to(ROOT).as_posix()})
    files = []
    for relative in sorted(sources):
        path = ROOT.joinpath(*Path(relative).parts)
        if not path.is_file():
            raise FileNotFoundError(relative)
        files.append({
            "source": relative,
            "target": relative,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    manifest = {
        "schema": "cm-architecture-query-ladder-runpod-upload-manifest/v1",
        "authorization_status": "upload_not_authorized_exact_approval_pending",
        "created_date": "2026-09-03",
        "run_name": RUN_NAME,
        "file_count": len(files),
        "bytes": sum(row["bytes"] for row in files),
        "files": files,
        "commands": [
            ["python", "-B", "scripts/cm_architecture_query_ladder_campaign.py",
             "--output", f"run-output/{RUN_NAME}", "--compiler", "cc",
             "--freeze", FREEZE.relative_to(ROOT).as_posix(),
             "--oracles", ORACLES.relative_to(ROOT).as_posix(), "--max-seconds", "420"],
            ["python", "-B", "scripts/crse_verify_architecture_query_ladder_campaign.py",
             "--run-dir", f"run-output/{RUN_NAME}",
             "--freeze", FREEZE.relative_to(ROOT).as_posix(),
             "--oracles", ORACLES.relative_to(ROOT).as_posix()],
        ],
        "execution_contract_sha256": _sha256(CONTRACT),
        "protocol_sha256": _sha256(PROTOCOL),
        "freeze_sha256": _sha256(FREEZE),
        "freeze_verification_sha256": _sha256(FREEZE_VERIFICATION),
        "oracles_sha256": _sha256(ORACLES),
        "runtime": contract["runtime"],
        "limits": contract["limits"],
        "network_during_setup": "pinned image plus four hash-locked wheels only",
        "network_during_workload": False,
        "result_cap_bytes": RESULT_CAP_BYTES,
        "excluded": [
            ".env*", ".git/", "credentials", "tokens", "Windows DLLs", "website files",
            "unrelated dirty work", "prior RunPod evidence",
        ],
    }
    _write_new(MANIFEST, manifest)
    print(json.dumps({
        "status": manifest["authorization_status"],
        "planned_cells": TOTAL_CELLS,
        "files": manifest["file_count"],
        "bytes": manifest["bytes"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
