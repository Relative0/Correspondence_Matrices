"""Freeze the C38 second-machine package around the confirmed C37 workload."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cm_c38_linux_replication import (
    EXPECTED_PARENT_DATASET_SHA256,
    EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
    EXPECTED_PARENT_FREEZE_SHA256,
    PARENT_DATASET,
    PARENT_DATASET_VERIFICATION,
    PARENT_FREEZE,
    POSIX_FLAGS,
)


OUT = ROOT / "docs/recognition/c38_linux_confirmation"
MANIFEST = OUT / "c38_linux_upload_manifest.json"
PROTOCOL = OUT / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
CONTRACT = OUT / "c38_c37_native_replication_contract.json"
LOCAL_RUN = ROOT / "docs/recognition/runs/c37-native-exact-confirmation-windows-20260903-001"
IMAGE_TAG = "python:3.13.15-bookworm"
IMAGE_AMD64_DIGEST = (
    "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8"
)
IMAGE = f"{IMAGE_TAG}@{IMAGE_AMD64_DIGEST}"
NUMPY_REQUIREMENT = (
    "numpy==2.3.2 "
    "--hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
)
RUN_NAME = "c38-c37-native-linux-gcc-20260903-001"
RESULT_CAP_BYTES = 24 << 20

EXTRA_PROJECT_FILES = (
    "cm_ir.py",
    "cmbench/__init__.py",
    "cmbench/output_budget.py",
    "cmbench/comparative/__init__.py",
    "cmbench/expr/__init__.py",
    "cmbench/expr/eval.py",
    "cmbench/recognition/__init__.py",
    "cmbench/recognition/features.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/recognition/natural_decomposition.py",
    "cmbench/recognition/proved_rules.py",
    "scripts/cm_c38_linux_replication.py",
    "scripts/crse_c38_linux_replication_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
    "docs/recognition/c37_native_exact_confirmation/freeze_v3.json",
    "docs/recognition/c37_native_exact_confirmation_dataset.json",
    "docs/recognition/c37_native_exact_confirmation_dataset_verification.json",
)

COMMANDS = (
    [
        "python", "-B", "scripts/cm_c38_linux_replication.py",
        "--run-id", RUN_NAME, "--output", f"run-output/{RUN_NAME}",
        "--compiler", "cc", "--max-seconds", "1200",
    ],
    [
        "python", "-B", "scripts/crse_native_exact_confirmation_verify.py",
        "--run-dir", f"run-output/{RUN_NAME}",
    ],
    [
        "python", "-B", "scripts/crse_c38_linux_replication_verify.py",
        "--run-dir", f"run-output/{RUN_NAME}",
    ],
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path: Path) -> dict[str, int | str]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        if isinstance(value, str):
            stream.write(value.encode("utf-8"))
        else:
            stream.write(
                json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
                + b"\n"
            )


def main() -> int:
    if any(path.exists() for path in (MANIFEST, PROTOCOL, CONTRACT)):
        raise SystemExit("refusing to overwrite frozen C38 package artifacts")
    if (
        sha256(PARENT_FREEZE) != EXPECTED_PARENT_FREEZE_SHA256
        or sha256(PARENT_DATASET) != EXPECTED_PARENT_DATASET_SHA256
        or sha256(PARENT_DATASET_VERIFICATION)
        != EXPECTED_PARENT_DATASET_VERIFICATION_SHA256
    ):
        raise ValueError("C38 parent C37 inputs changed before package freeze")
    parent = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    local_result = json.loads((LOCAL_RUN / "results.json").read_text(encoding="utf-8"))
    local_verification = json.loads(
        (LOCAL_RUN / "independent_verification.json").read_text(encoding="utf-8")
    )
    if (
        local_result.get("status") != "complete"
        or local_result.get("decision", {}).get("all_predeclared_gates_passed") is not True
        or local_verification.get("status") != "verified"
        or local_verification.get("results_sha256") != sha256(LOCAL_RUN / "results.json")
        or local_verification.get("raw_sessions_checked") != 954
    ):
        raise ValueError("C38 cannot bind unverified local C37 evidence")

    contract = {
        "schema": "crse-c38-c37-native-replication-contract/v1",
        "created_date": "2026-09-03",
        "purpose": (
            "Rebuild the exact C37 native source with the execution host's GCC-family "
            "C11 compiler and repeat the unchanged C37 dataset, schedule, outputs, and gates."
        ),
        "parent_c37": {
            "freeze_sha256": EXPECTED_PARENT_FREEZE_SHA256,
            "dataset_sha256": EXPECTED_PARENT_DATASET_SHA256,
            "dataset_verification_sha256": EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
            "windows_results_sha256": sha256(LOCAL_RUN / "results.json"),
            "windows_manifest_sha256": sha256(LOCAL_RUN / "manifest.json"),
            "windows_independent_verification_sha256": sha256(
                LOCAL_RUN / "independent_verification.json"
            ),
            "windows_native_library_sha256": local_result["native_library"]["sha256"],
        },
        "unchanged_scientific_contract": {
            "single_root_cases": 18,
            "single_root_blocks": 12,
            "single_root_methods": 3,
            "multi_root_workloads": 6,
            "multi_root_blocks": 20,
            "multi_root_methods": 2,
            "restrictions_per_session": 64,
            "raw_sessions": 954,
            "single_root_exact_query_checks": 44928,
            "multi_root_exact_output_query_checks": 48384,
            "gates": {
                "single_aggregate_minimum": 1.10,
                "single_case_minimum": 0.95,
                "single_width_minimum": 1.00,
                "single_p95_minimum": 0.95,
                "single_workspace_max_bytes": 64 << 20,
                "multi_aggregate_minimum": 1.10,
                "multi_workload_minimum": 1.00,
                "multi_p95_minimum": 0.95,
                "multi_node_reduction_each_workload": True,
                "multi_workspace_no_larger_each_workload": True,
            },
        },
        "host_variation": {
            "required_os": "Linux",
            "required_architecture": "amd64",
            "compiler_family": "GCC-family cc from the pinned buildpack-deps image",
            "compiler_flags": list(POSIX_FLAGS),
            "compiler_executable_and_version_recorded": True,
            "compiler_binary_sha256_recorded": True,
            "native_binary_sha256_recorded": True,
        },
        "decision": {
            "failed_performance_gate_is_retained_as_valid_replication_evidence": True,
            "method_substitution": False,
            "gate_refit": False,
            "policy_refit": False,
            "training": False,
            "production_write": False,
            "website_update": False,
            "production_promotion": False,
        },
    }
    write_new(CONTRACT, contract)

    sources: dict[str, str] = {relative: "c37_frozen_source" for relative in parent["sources"]}
    for relative in EXTRA_PROJECT_FILES:
        sources.setdefault(relative, "replication_runtime")
    rows = []
    for target in sorted(sources):
        path = ROOT.joinpath(*Path(target).parts)
        if not path.is_file():
            raise FileNotFoundError(f"C38 package source missing: {target}")
        rows.append({
            "source": target,
            "target": target,
            "kind": sources[target],
            **identity(path),
        })
    total_bytes = sum(int(row["bytes"]) for row in rows)
    protocol = f"""# C38 C37-native second-machine replication protocol

Upload only the frozen **{len(rows)}-file, {total_bytes:,}-byte package** described by
`c38_linux_upload_manifest.json`. It contains the exact C37 source map, fresh sealed
18-case/six-workload dataset, independent verifiers, and the minimal transitive runtime
needed to rebuild the C11 native library. It excludes the Windows DLL, credentials,
local timing artifacts, unrelated dirty work, persistent storage, and website files.

On one new Secure CPU Pod, use the pinned amd64 Python 3.13.15 Bookworm image. Resolve
the image's `cc`, record its executable path, full version text, and SHA-256, then build
`fused_slot_executor.c` with exactly `{chr(32).join(POSIX_FLAGS)}`. Record the resulting
shared-library hash and ABI. Rebind only the environment-specific freeze and dataset
hash references; independently prove that the cases, expressions, traces, expected
outputs, schedules, gates, and original C37 source map are otherwise byte-equivalent.

Run the unchanged 12-block single-root and 20-block multi-root C37 schedule: 954 raw
sessions, 44,928 single-root exact query checks, and 48,384 multi-root output-query
checks. Run both the packaged C37 verifier and the C38 rebinding/compiler verifier.
A failed performance gate is a valid cross-machine outcome and must be retained; it
does not permit rerunning with changed methods, schedules, flags, cases, or thresholds.

No upload or paid action is authorized by this freeze. A later exact authorization is
limited to one Secure CPU Pod, one creation attempt and no replacement, 2 vCPU, at least
4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, one HTTPS port, a
$0.25/hour rate ceiling, a $0.05 controller cost ceiling, deletion within ten minutes,
and twelve-minute inventory reconciliation. Setup may download only the pinned image
and hash-locked NumPy wheel. Workload execution uses no network. No training, website
write, deployment, shadow promotion, production change, commit, or push is authorized.
"""
    write_new(PROTOCOL, protocol)

    manifest = {
        "schema": "crse-c38-c37-native-linux-replication-upload-manifest/v1",
        "authorization_status": "upload_not_authorized_exact_approval_pending",
        "created_date": "2026-09-03",
        "file_count": len(rows),
        "bytes": total_bytes,
        "files": rows,
        "commands": list(COMMANDS),
        "run_name": RUN_NAME,
        "protocol_sha256": sha256(PROTOCOL),
        "replication_contract_sha256": sha256(CONTRACT),
        "runtime": {
            "architecture": "amd64",
            "image": IMAGE,
            "image_tag": IMAGE_TAG,
            "image_amd64_digest": IMAGE_AMD64_DIGEST,
            "python": "3.13.15",
            "numpy": "2.3.2",
            "numpy_requirement": NUMPY_REQUIREMENT,
            "posix_compiler": "cc from pinned buildpack-deps:bookworm-derived image",
        },
        "network_during_setup": "pinned container image and hash-checked NumPy wheel only",
        "network_during_workload": False,
        "result_cap_bytes": RESULT_CAP_BYTES,
        "scientific_contract": contract["unchanged_scientific_contract"],
        "decision_boundary": contract["decision"],
        "excluded": [
            ".env*", ".git/", "tokens", "credentials", "Windows DLL and object files",
            "local C37 timings", "unrelated dirty work", "website files",
        ],
    }
    write_new(MANIFEST, manifest)
    print(json.dumps({
        "file_count": len(rows),
        "bytes": total_bytes,
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "contract_sha256": sha256(CONTRACT),
        "authorization_status": manifest["authorization_status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
