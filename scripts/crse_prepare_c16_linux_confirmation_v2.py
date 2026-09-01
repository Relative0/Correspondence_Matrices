"""Freeze the import-path-corrected C16 Linux confirmation package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c16_linux_confirmation"
DATASET = OUT / "c16_dataset.json"
MANIFEST = OUT / "c16_linux_upload_manifest_v2.json"
PROTOCOL = OUT / "C16_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_31.md"
PREDECESSOR_MANIFEST = OUT / "c16_linux_upload_manifest.json"
FAILURE_VERIFICATION = OUT / "RUNPOD_C16_LINUX_FINAL_VERIFICATION_20260831.json"
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
COMMAND = [
    "python",
    "-B",
    "scripts/crse_gf2_screening_linux_confirmation.py",
    "--dataset",
    "study/c16-dataset.json",
    "--output",
    "run-output/c16-linux-confirmation",
    "--repetitions",
    "3",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if MANIFEST.exists() or PROTOCOL.exists():
        raise SystemExit("refusing to overwrite a frozen C16 v2 Linux package")
    for required in (DATASET, PREDECESSOR_MANIFEST, FAILURE_VERIFICATION):
        if not required.is_file():
            raise SystemExit(f"missing C16 v2 prerequisite: {required}")

    rows = []
    for source, target in FILES:
        path = ROOT / source
        rows.append(
            {
                "source": source,
                "target": target,
                "bytes": path.stat().st_size,
                "sha256": sha(path),
            }
        )
    manifest = {
        "schema": "crse-c16-linux-confirmation-upload-manifest/v2",
        "authorization_status": "exact_payload_approval_required",
        "created_date": "2026-08-31",
        "predecessor_manifest_sha256": sha(PREDECESSOR_MANIFEST),
        "predecessor_failure_verification_sha256": sha(FAILURE_VERIFICATION),
        "remediation": {
            "entry_point_adds_package_root_to_sys_path": True,
            "local_validation_injects_pythonpath": False,
        },
        "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "files": rows,
        "command": COMMAND,
        "runtime": {
            "architecture": "amd64",
            "image": IMAGE,
            "python": "3.13.15",
            "numpy": "2.3.2",
            "numpy_requirement": NUMPY,
        },
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False,
        "result_cap_bytes": 16 << 20,
        "excluded": [
            ".env*",
            ".git/",
            "tokens",
            "credentials",
            "source fixture checkout",
            "prior run outputs",
            "unrelated files",
        ],
    }
    MANIFEST.write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    PROTOCOL.write_text(
        """# C16 second-machine timing package v2 protocol

Upload only the frozen 18-file package described by
`c16_linux_upload_manifest_v2.json`. This package differs from the first C16
package only in the workload entry point: it adds the uploaded package root to
`sys.path`, matching the import contract already used by the other Linux
confirmation entry points. Package-only validation must not inject `PYTHONPATH`.

The workload compares the C16 exact-screened GF(2) tail with the original
exhaustive materializer on the unchanged 40-case Yosys family. It reruns three
balanced rounds and requires identical artifact identity and complete semantic
reconstruction; it performs no training and no production write.

A future run requires explicit approval of this v2 manifest and protocol.
Create one Secure RunPod CPU pod and no replacement. Use the pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, and a controller
$0.05 total ceiling within the user's $5 authorization. Retrieve at most 16
MiB, delete within ten minutes, and reconcile for twelve minutes.
""",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
                "file_count": len(rows),
                "bytes": manifest["bytes"],
                "manifest_sha256": sha(MANIFEST),
                "protocol_sha256": sha(PROTOCOL),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
