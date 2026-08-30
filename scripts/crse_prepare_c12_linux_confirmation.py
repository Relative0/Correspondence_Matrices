"""Freeze the authorized minimal C12 Runpod confirmation package."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c12_linux_confirmation"
MANIFEST = OUT / "c12_linux_upload_manifest.json"
AUTHORIZATION = OUT / "RUNPOD_C12_LINUX_AUTHORIZED_2026_08_30.json"
PROTOCOL = OUT / "C12_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"
IMAGE = "python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
NUMPY = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
FILES = (
    ("bitset_backend.py", "bitset_backend.py"),
    ("cm_exprlib.py", "cm_exprlib.py"),
    ("cm_expr_serde.py", "cm_expr_serde.py"),
    ("cm_ir.py", "cm_ir.py"),
    ("cmbench/__init__.py", "cmbench/__init__.py"),
    ("cmbench/recognition/__init__.py", "cmbench/recognition/__init__.py"),
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


def write(path: Path, value: dict) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for source, target in FILES:
        path = ROOT / source
        rows.append({"source": source, "target": target, "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {"schema": "crse-c12-linux-confirmation-upload-manifest/v1",
        "authorization_status": "authorized_by_user_2026_08_30", "created_date": "2026-08-30",
        "file_count": len(rows), "bytes": sum(row["bytes"] for row in rows), "files": rows,
        "command": COMMAND, "runtime": {"architecture": "amd64", "image": IMAGE,
            "python": "3.13.15", "numpy": "2.3.2", "numpy_requirement": NUMPY},
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False, "result_cap_bytes": 16 << 20,
        "excluded": [".env*", ".git/", "tokens", "credentials", "source fixture checkout",
                     "prior run outputs", "C6/C7/C11 datasets", "unrelated files"]}
    write(MANIFEST, manifest)
    PROTOCOL.write_text("""# C12 second-machine timing protocol

Run the frozen robust 4,096-pair one-pass dispatcher and exact controls on the
unchanged 40-case C12 dataset. Use one Secure Runpod CPU pod, no replacement,
Python 3.13.15, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, a controller-enforced
$0.05 total ceiling, ten-minute cleanup, and twelve-minute reconciliation.
Only the frozen 14-file package may be uploaded. Retrieve at most 16 MiB and
delete the owned pod. No training or production write is permitted.
""", encoding="utf-8")
    authorization = {"schema": "crse-runpod-c12-linux-authorization/v1", "authorized": True,
        "authorization_basis": "User explicitly pre-authorized up to USD 5 of Runpod work on 2026-08-30",
        "user_total_ceiling_usd": 5.0, "controller_total_ceiling_usd": 0.05,
        "one_create": True, "no_replacement": True, "source_files": len(rows),
        "source_bytes": manifest["bytes"], "cases": 40, "repetitions": 16, "methods": 4,
        "https_ports": ["8080/http"], "vcpu_count": 2, "minimum_ram_gb": 4,
        "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
        "cleanup_seconds": 600, "reconciliation_seconds": 720,
        "rate_cap_usd_per_hour": 0.25, "total_cost_cap_usd": 0.05,
        "proposal_sha256": sha(PROTOCOL), "upload_manifest_sha256": sha(MANIFEST),
        "recorded_utc": datetime.now(timezone.utc).isoformat()}
    write(AUTHORIZATION, authorization)
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "files": len(rows), "bytes": manifest["bytes"], "manifest_sha256": sha(MANIFEST),
        "authorization_sha256": sha(AUTHORIZATION)}, sort_keys=True))


if __name__ == "__main__":
    main()
