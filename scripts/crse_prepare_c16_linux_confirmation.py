"""Freeze the dependency-complete C16 Linux confirmation package."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c16_linux_confirmation"
SOURCE_DATASET = ROOT / "docs/recognition/runs/c16-gf2-screened-tail-windows-20260830-001/dataset.json"
DATASET = OUT / "c16_dataset.json"
MANIFEST = OUT / "c16_linux_upload_manifest.json"
PROTOCOL = OUT / "C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"
IMAGE = "python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
NUMPY = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
FILES = (
    ("bitset_backend.py", "bitset_backend.py"),
    ("cm_exprlib.py", "cm_exprlib.py"),
    ("cm_expr_serde.py", "cm_expr_serde.py"),
    ("cm_ir.py", "cm_ir.py"),
    ("cmbench/__init__.py", "cmbench/__init__.py"),
    ("cmbench/output_budget.py", "cmbench/output_budget.py"),
    ("cmbench/expr/__init__.py", "cmbench/expr/__init__.py"),
    ("cmbench/expr/eval.py", "cmbench/expr/eval.py"),
    ("cmbench/recognition/__init__.py", "cmbench/recognition/__init__.py"),
    ("cmbench/recognition/features.py", "cmbench/recognition/features.py"),
    ("cmbench/recognition/portfolio.py", "cmbench/recognition/portfolio.py"),
    ("cmbench/recognition/natural_decomposition.py", "cmbench/recognition/natural_decomposition.py"),
    ("cmbench/recognition/proved_rules.py", "cmbench/recognition/proved_rules.py"),
    ("cmbench/recognition/gf2_decomposition.py", "cmbench/recognition/gf2_decomposition.py"),
    ("cmbench/recognition/source_interaction.py", "cmbench/recognition/source_interaction.py"),
    ("cmbench/recognition/source_anf_hybrid.py", "cmbench/recognition/source_anf_hybrid.py"),
    ("scripts/crse_gf2_screening_linux_confirmation.py", "scripts/crse_gf2_screening_linux_confirmation.py"),
    ("docs/recognition/c16_linux_confirmation/c16_dataset.json", "study/c16-dataset.json"),
)
COMMAND = ["python", "-B", "scripts/crse_gf2_screening_linux_confirmation.py",
           "--dataset", "study/c16-dataset.json", "--output",
           "run-output/c16-linux-confirmation", "--repetitions", "3"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    if DATASET.exists() or MANIFEST.exists() or PROTOCOL.exists():
        raise SystemExit("refusing to overwrite a frozen C16 Linux package")
    shutil.copyfile(SOURCE_DATASET, DATASET)
    rows = []
    for source, target in FILES:
        path = ROOT / source
        rows.append({"source": source, "target": target, "bytes": path.stat().st_size,
                     "sha256": sha(path)})
    manifest = {
        "schema": "crse-c16-linux-confirmation-upload-manifest/v1",
        "authorization_status": "authorized_under_user_5_usd_ceiling",
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
                     "prior run outputs", "unrelated files"],
    }
    MANIFEST.write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    PROTOCOL.write_text("""# C16 second-machine timing protocol

Upload only the frozen 18-file package described by `c16_linux_upload_manifest.json`.
The workload compares the C16 exact-screened GF(2) tail with the original
exhaustive materializer on the unchanged 40-case Yosys family. It reruns three
balanced rounds and requires identical artifact identity and complete semantic
reconstruction; it performs no training and no production write.

Create one Secure Runpod CPU pod and no replacement. Use the pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, and a controller
$0.05 total ceiling within the user's $5 authorization. Retrieve at most 16
MiB, delete within ten minutes, and reconcile for twelve minutes.
""", encoding="utf-8", newline="\n")
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
                      "file_count": len(rows), "bytes": manifest["bytes"],
                      "manifest_sha256": sha(MANIFEST), "protocol_sha256": sha(PROTOCOL)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
