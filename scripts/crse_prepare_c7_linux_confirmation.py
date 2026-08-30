"""Freeze the minimal upload manifest for C7 second-machine timing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "recognition" / "c7_linux_confirmation" / "c7_linux_upload_manifest.json"
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
    ("scripts/crse_yosys_source_anf_linux_confirmation.py", "scripts/crse_yosys_source_anf_linux_confirmation.py"),
    ("docs/recognition/runs/yosys-source-anf-confirmation-20260830-002/dataset.json", "study/yosys-c7-dataset.json"),
)
COMMAND = ["python", "-B", "scripts/crse_yosys_source_anf_linux_confirmation.py",
           "--dataset", "study/yosys-c7-dataset.json", "--output",
           "run-output/yosys-c7-linux-confirmation", "--repetitions", "9"]


def main():
    rows = []
    for source, target in FILES:
        path = ROOT / source
        data = path.read_bytes()
        rows.append({"source": source, "target": target, "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "schema": "crse-c7-linux-confirmation-upload-manifest/v1",
        "authorization_status": "pending",
        "created_date": "2026-08-30",
        "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "files": rows,
        "command": COMMAND,
        "runtime": {"architecture": "amd64", "image": IMAGE, "python": "3.13.15",
                    "numpy": "2.3.2", "numpy_requirement": NUMPY},
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False,
        "result_cap_bytes": 16 << 20,
        "excluded": [".env*", ".git/", "tokens", "credentials", "source fixture checkout",
                     "prior run outputs", "unrelated tests and deliverables"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"path": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
                      "file_count": manifest["file_count"], "bytes": manifest["bytes"],
                      "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == "__main__":
    main()
