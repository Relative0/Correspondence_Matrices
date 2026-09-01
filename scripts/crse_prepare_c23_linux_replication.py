"""Freeze the unchanged C23 seven-method Linux replication package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/recognition/c23_linux_confirmation"
MANIFEST = OUT / "c23_linux_upload_manifest.json"
PROTOCOL = OUT / "C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md"
IMAGE = "python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
NUMPY = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"

PROJECT_FILES = (
    "bitset_backend.py",
    "cm_exprlib.py",
    "cm_expr_serde.py",
    "cm_ir.py",
    "cmbench/__init__.py",
    "cmbench/output_budget.py",
    "cmbench/expr/__init__.py",
    "cmbench/expr/eval.py",
    "cmbench/backends/__init__.py",
    "cmbench/backends/robdd_dd.py",
    "cmbench/comparative/__init__.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_decomposition.py",
    "cmbench/comparative/gf2_method_table.py",
    "cmbench/comparative/gf2_table_experiment.py",
    "cmbench/comparative/gf2_fresh_table_experiment.py",
    "cmbench/recognition/__init__.py",
    "cmbench/recognition/features.py",
    "cmbench/recognition/portfolio.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/proved_rules.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/gf2_task_dispatcher.py",
    "cmbench/recognition/gf2_work_policy.py",
    "cmbench/recognition/gf2_work_policy_compiler.py",
    "cmbench/recognition/bdd_ordering.py",
    "cmbench/recognition/source_interaction.py",
    "cmbench/recognition/source_anf_hybrid.py",
    "cmbench/recognition/yosys_unused_gf2_data.py",
    "scripts/cm_comparative_c23_fresh_gf2_table.py",
    "scripts/crse_gf2_fresh_table_verify.py",
    "docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json",
    "docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json",
    "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json",
)

VENDORED_FILES = (
    (".venv/Lib/site-packages/dd/__init__.py", "dd/__init__.py"),
    (".venv/Lib/site-packages/dd/_version.py", "dd/_version.py"),
    (".venv/Lib/site-packages/dd/_abc.py", "dd/_abc.py"),
    (".venv/Lib/site-packages/dd/_copy.py", "dd/_copy.py"),
    (".venv/Lib/site-packages/dd/_utils.py", "dd/_utils.py"),
    (".venv/Lib/site-packages/dd/_parser.py", "dd/_parser.py"),
    (".venv/Lib/site-packages/dd/autoref.py", "dd/autoref.py"),
    (".venv/Lib/site-packages/dd/bdd.py", "dd/bdd.py"),
    (".venv/Lib/site-packages/astutils/__init__.py", "astutils/__init__.py"),
    (".venv/Lib/site-packages/astutils/_version.py", "astutils/_version.py"),
    (".venv/Lib/site-packages/astutils/ast.py", "astutils/ast.py"),
    (".venv/Lib/site-packages/astutils/ply.py", "astutils/ply.py"),
    (".venv/Lib/site-packages/ply/__init__.py", "ply/__init__.py"),
    (".venv/Lib/site-packages/ply/lex.py", "ply/lex.py"),
    (".venv/Lib/site-packages/ply/yacc.py", "ply/yacc.py"),
    (".venv/Lib/site-packages/dd-0.6.0.dist-info/METADATA", "dd-0.6.0.dist-info/METADATA"),
    (".venv/Lib/site-packages/astutils-0.0.6.dist-info/METADATA", "third_party_metadata/astutils-0.0.6.METADATA"),
    (".venv/Lib/site-packages/ply-3.10.dist-info/METADATA", "third_party_metadata/ply-3.10.METADATA"),
)

RUN_NAME = "c23-yosys-fresh-gf2-table-linux-20260831-001"
COMMANDS = (
    ["python", "-B", "scripts/cm_comparative_c23_fresh_gf2_table.py",
     "--output", f"run-output/{RUN_NAME}", "--rounds", "5", "--max-seconds", "1200"],
    ["python", "-B", "scripts/crse_gf2_fresh_table_verify.py", f"run-output/{RUN_NAME}"],
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if MANIFEST.exists() or PROTOCOL.exists():
        raise SystemExit("refusing to overwrite frozen C23 Linux package")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in PROJECT_FILES:
        path = ROOT / source
        rows.append({"source": source, "target": source, "bytes": path.stat().st_size,
                     "sha256": sha256(path), "kind": "project"})
    for source, target in VENDORED_FILES:
        path = ROOT / source
        rows.append({"source": source, "target": target, "bytes": path.stat().st_size,
                     "sha256": sha256(path), "kind": "vendored_runtime"})
    targets = [row["target"] for row in rows]
    if len(targets) != len(set(targets)):
        raise ValueError("duplicate C23 package target")
    manifest = {
        "schema": "crse-c23-linux-replication-upload-manifest/v1",
        "authorization_status": "authorized_by_current_user_request",
        "created_date": "2026-08-31",
        "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "files": rows,
        "commands": list(COMMANDS),
        "run_name": RUN_NAME,
        "runtime": {
            "architecture": "amd64",
            "image": IMAGE,
            "python": "3.13.15",
            "numpy": "2.3.2",
            "numpy_requirement": NUMPY,
            "dd": "0.6.0 pure-Python autoref subset vendored from the approved local environment",
            "astutils": "0.0.6 vendored dependency subset",
            "ply": "3.10 vendored dependency subset",
        },
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False,
        "result_cap_bytes": 16 << 20,
        "scientific_contract": {
            "cases": 48,
            "methods": 7,
            "rounds": 5,
            "measurement_rows": 1680,
            "memory_rows": 56,
            "unchanged_c23_dataset": True,
            "unchanged_c21_method_implementations": True,
            "policy_refit": False,
            "training": False,
            "production_write": False,
        },
        "excluded": [
            ".env*", ".git/", "tokens", "credentials", "external source checkout",
            "local run outputs", "unrelated dirty work", "compiled dd backends",
        ],
    }
    MANIFEST.write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    PROTOCOL.write_text(
        f"""# C23 unchanged second-machine replication protocol

Upload only the frozen {len(rows)}-file, {manifest['bytes']:,}-byte package in
`c23_linux_upload_manifest.json`. The package contains the sealed C23 v2
dataset, its independent verification, the unchanged seven C21 method adapters,
the C23 harness and verifier, the frozen screened-policy control, and bounded
pure-Python BDD dependencies. It excludes credentials, local timing results,
source checkouts, compiled BDD backends, and unrelated worktree files.

Run the same 48 cases, seven methods, five balanced rounds, 64-partition bound,
four-artifact materialization budget, fresh-engine single-query lifecycle, and
outside-timing correctness oracle used by the verified Windows run. Then run the
independent verifier on the same pod. No training, policy refit, production
write, or fallback to a changed method is permitted.

The current user request authorizes the following bounded RunPod action within
the standing $5 ceiling: one Secure CPU pod, no replacement, pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, zero persistent
volumes, one HTTPS port, $0.25/hour rate ceiling, and $0.05 controller cost
ceiling. Upload only this manifest, retrieve at most 16 MiB, delete the owned pod
within ten minutes, and reconcile inventories for twelve minutes.
""",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"file_count": len(rows), "bytes": manifest["bytes"],
                      "manifest_sha256": sha256(MANIFEST),
                      "protocol_sha256": sha256(PROTOCOL)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
