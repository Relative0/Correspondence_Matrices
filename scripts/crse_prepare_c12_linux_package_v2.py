"""Freeze the corrected dependency-complete C12 Linux package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c12_linux_confirmation"
MANIFEST = OUT / "c12_linux_upload_manifest_v2.json"
PROTOCOL = OUT / "C12_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_30.md"
IMAGE = "python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
NUMPY = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
FILES = (
    ("bitset_backend.py", "bitset_backend.py"),
    ("cm_exprlib.py", "cm_exprlib.py"),
    ("cm_expr_serde.py", "cm_expr_serde.py"),
    ("cm_ir.py", "cm_ir.py"),
    ("cmbench/__init__.py", "cmbench/__init__.py"),
    ("cmbench/output_budget.py", "cmbench/output_budget.py"),
    ("cmbench/recognition/__init__.py", "cmbench/recognition/__init__.py"),
    ("cmbench/recognition/features.py", "cmbench/recognition/features.py"),
    ("cmbench/recognition/portfolio.py", "cmbench/recognition/portfolio.py"),
    ("cmbench/recognition/natural_decomposition.py", "cmbench/recognition/natural_decomposition.py"),
    ("cmbench/recognition/source_interaction.py", "cmbench/recognition/source_interaction.py"),
    ("cmbench/recognition/source_anf_hybrid.py", "cmbench/recognition/source_anf_hybrid.py"),
    ("cmbench/recognition/staged_exact_dispatcher.py", "cmbench/recognition/staged_exact_dispatcher.py"),
    ("cmbench/recognition/adaptive_exact_dispatcher.py", "cmbench/recognition/adaptive_exact_dispatcher.py"),
    ("scripts/crse_adaptive_dispatcher_linux_confirmation.py", "scripts/crse_adaptive_dispatcher_linux_confirmation.py"),
    ("docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002/c12_dataset.json", "study/c12-dataset.json"),
)
COMMAND = ["python", "-B", "scripts/crse_adaptive_dispatcher_linux_confirmation.py",
           "--dataset", "study/c12-dataset.json", "--output",
           "run-output/yosys-c7-linux-confirmation", "--repetitions", "16"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for source, target in FILES:
        path = ROOT / source
        rows.append({"source": source, "target": target, "bytes": path.stat().st_size,
                     "sha256": sha(path)})
    manifest = {"schema": "crse-c12-linux-confirmation-upload-manifest/v2",
        "authorization_status": "pending_payload_specific_authorization",
        "created_date": "2026-08-30", "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows), "files": rows, "command": COMMAND,
        "runtime": {"architecture": "amd64", "image": IMAGE, "python": "3.13.15",
                    "numpy": "2.3.2", "numpy_requirement": NUMPY},
        "dependency_correction": ["cmbench/output_budget.py", "cmbench/recognition/features.py"],
        "isolated_local_workload_required_before_authorization": True,
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False, "result_cap_bytes": 16 << 20,
        "excluded": [".env*", ".git/", "tokens", "credentials", "source fixture checkout",
                     "prior run outputs", "C6/C7/C11 datasets", "unrelated files"]}
    MANIFEST.write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    PROTOCOL.write_text("""# C12 second-machine package-v2 protocol

Upload only the corrected 16-file C12 package. Relative to the failed 14-file
package it adds `cmbench/output_budget.py` and `cmbench/recognition/features.py`,
the two missing transitive imports. The full workload must first pass from an
isolated directory containing only these 16 files.

Create one Secure Runpod CPU pod and no replacement. Require two successful
health checks and allow at most six idempotent `POST /payload` attempts on that
same pod when the proxy returns HTTP 404. Use the pinned Python 3.13.15 image,
2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or network volume, one
HTTPS port, a $0.25/hour rate ceiling, and a controller-enforced $0.05 total
ceiling. Retrieve at most 16 MiB, delete within ten minutes, and reconcile for
twelve minutes. No training or production write is permitted.
""", encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "file_count": len(rows), "bytes": manifest["bytes"], "manifest_sha256": sha(MANIFEST),
        "protocol_sha256": sha(PROTOCOL)}, sort_keys=True))


if __name__ == "__main__":
    main()
