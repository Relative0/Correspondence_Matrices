"""Rebuild C37 natively and execute its unchanged confirmation schedule.

The Linux/RunPod path requires a POSIX C compiler.  The explicit local-validation
mode exercises the same rebinding and execution machinery with the host compiler,
but its timings are package validation only and are never C38 evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_native_confirmation import NativeConfirmationConfig, run


PARENT_FREEZE = ROOT / "docs/recognition/c37_native_exact_confirmation/freeze_v3.json"
PARENT_DATASET = ROOT / "docs/recognition/c37_native_exact_confirmation_dataset.json"
PARENT_DATASET_VERIFICATION = (
    ROOT / "docs/recognition/c37_native_exact_confirmation_dataset_verification.json"
)
EXPECTED_PARENT_FREEZE_SHA256 = (
    "5d7c9a98c92ac4c15250945f741219fe482019da6e2c94d257894fa38c47023c"
)
EXPECTED_PARENT_DATASET_SHA256 = (
    "f5ad98f83551b3abeb59f26c101408a445a2a2498817487db482356b88f08892"
)
EXPECTED_PARENT_DATASET_VERIFICATION_SHA256 = (
    "d32c0709db8a99e28c0df997f2a8125353ca1fe83270cbf838804ae16d7e6b44"
)
POSIX_FLAGS = (
    "-std=c11", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-shared", "-fPIC",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )


def file_identity(path: Path) -> dict[str, int | str]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def verify_parent_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected = {
        PARENT_FREEZE: EXPECTED_PARENT_FREEZE_SHA256,
        PARENT_DATASET: EXPECTED_PARENT_DATASET_SHA256,
        PARENT_DATASET_VERIFICATION: EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"C38 parent identity changed: {path.relative_to(ROOT)}")
    freeze = load(PARENT_FREEZE)
    dataset = load(PARENT_DATASET)
    verification = load(PARENT_DATASET_VERIFICATION)
    if (
        freeze.get("status") != "frozen_before_dataset_and_timing"
        or dataset.get("provenance", {}).get("freeze_sha256")
        != EXPECTED_PARENT_FREEZE_SHA256
        or verification.get("status") != "verified"
        or verification.get("dataset_sha256") != EXPECTED_PARENT_DATASET_SHA256
        or verification.get("freeze_sha256") != EXPECTED_PARENT_FREEZE_SHA256
        or verification.get("timing_or_method_output_used") is not False
    ):
        raise ValueError("C38 parent scientific boundary changed")
    for relative, identity in freeze["sources"].items():
        source = ROOT.joinpath(*Path(relative).parts)
        if (
            not source.is_file()
            or source.stat().st_size != identity["bytes"]
            or sha256(source) != identity["sha256"]
        ):
            raise ValueError(f"C38 frozen C37 source changed: {relative}")
    return freeze, dataset, verification


def _python_identity() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    return {
        "version": sys.version,
        "executable": str(executable),
        "executable_sha256": sha256(executable),
    }


def build_library(
    runtime_dir: Path, compiler_name: str, local_platform_validation: bool,
) -> tuple[Path, dict[str, Any], list[str]]:
    native_dir = runtime_dir / "native-build"
    native_dir.mkdir(parents=True, exist_ok=False)
    source = ROOT / "native/cm_fused_slots/fused_slot_executor.c"
    if local_platform_validation:
        from scripts.build_cm_fused_slots import build
        from scripts.crse_freeze_c37_native_confirmation import compiler_identity

        library = build(native_dir)
        identity = compiler_identity()
        identity["role"] = "local_package_validation_only"
        command = ["host-native-build", str(source), str(library)]
        return library, identity, command

    if os.name == "nt" or sys.platform != "linux":
        raise RuntimeError("C38 evidence execution requires Linux")
    resolved_name = shutil.which(compiler_name)
    if resolved_name is None:
        raise RuntimeError(f"C38 compiler was not found: {compiler_name}")
    executable = Path(resolved_name).resolve()
    version = subprocess.run(
        [str(executable), "--version"], check=True, capture_output=True, text=True,
        timeout=20,
    )
    library = native_dir / "libcm_fused_slots.so"
    command = [str(executable), *POSIX_FLAGS, str(source), "-o", str(library)]
    completed = subprocess.run(
        command, cwd=ROOT, check=True, capture_output=True, text=True, timeout=120,
    )
    if completed.stdout or completed.stderr:
        (runtime_dir / "compiler-output.txt").write_text(
            completed.stdout + completed.stderr, encoding="utf-8", newline="\n",
        )
    if not library.is_file():
        raise RuntimeError("C38 native Linux library was not produced")
    identity = {
        "kind": "posix_c11",
        "requested_name": compiler_name,
        "executable": str(executable),
        "executable_sha256": sha256(executable),
        "version": (version.stdout + version.stderr).strip(),
        "role": "decision_bearing_linux_replication",
    }
    return library, identity, command


def derive_bound_inputs(
    runtime_dir: Path,
    parent_freeze: dict[str, Any],
    parent_dataset: dict[str, Any],
    parent_verification: dict[str, Any],
    library: Path,
    compiler: dict[str, Any],
    build_command: list[str],
    local_platform_validation: bool,
) -> tuple[Path, Path, Path]:
    freeze_path = runtime_dir / "linux_freeze.json"
    dataset_path = runtime_dir / "linux_dataset.json"
    verification_path = runtime_dir / "linux_dataset_verification.json"

    freeze = copy.deepcopy(parent_freeze)
    freeze["schema"] = "crse-c38-c37-native-linux-replication-freeze/v1"
    freeze["date"] = "2026-09-03"
    freeze["build_contract"] = (
        "Linux: resolved cc -std=c11 -O3 -Wall -Wextra -Wpedantic -shared -fPIC"
    )
    freeze["compiler"] = compiler
    freeze["environment"] = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "python": _python_identity(),
        "local_platform_validation_only": local_platform_validation,
    }
    freeze["native_library"] = {
        **file_identity(library),
        "path": library.relative_to(ROOT).as_posix(),
        "abi_version": 1,
        "supports_multi_root": True,
    }
    freeze["parent_c37"] = {
        "freeze_path": PARENT_FREEZE.relative_to(ROOT).as_posix(),
        "freeze_sha256": EXPECTED_PARENT_FREEZE_SHA256,
        "dataset_path": PARENT_DATASET.relative_to(ROOT).as_posix(),
        "dataset_sha256": EXPECTED_PARENT_DATASET_SHA256,
        "dataset_verification_path": PARENT_DATASET_VERIFICATION.relative_to(ROOT).as_posix(),
        "dataset_verification_sha256": EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
        "schedule_and_gates_unchanged": True,
        "source_map_unchanged": freeze["sources"] == parent_freeze["sources"],
    }
    freeze["replication"] = {
        "build_command": build_command,
        "compiler_rebuilt_on_execution_host": True,
        "timings_inspected_before_rebuild": False,
        "method_substitution": False,
        "gate_refit": False,
        "policy_refit": False,
        "training": False,
        "production_promotion": False,
        "local_platform_validation_only": local_platform_validation,
    }
    write_new(freeze_path, freeze)
    freeze_digest = sha256(freeze_path)

    dataset = copy.deepcopy(parent_dataset)
    provenance = dataset["provenance"]
    provenance["parent_c37_freeze_path"] = provenance["freeze_path"]
    provenance["parent_c37_freeze_sha256"] = provenance["freeze_sha256"]
    provenance["freeze_path"] = freeze_path.relative_to(ROOT).as_posix()
    provenance["freeze_sha256"] = freeze_digest
    provenance["replication_rebinding_only"] = True
    write_new(dataset_path, dataset)

    verification = copy.deepcopy(parent_verification)
    verification["parent_c37_dataset_sha256"] = verification["dataset_sha256"]
    verification["parent_c37_freeze_sha256"] = verification["freeze_sha256"]
    verification["dataset_sha256"] = sha256(dataset_path)
    verification["freeze_sha256"] = freeze_digest
    verification["replication_rebinding_only"] = True
    write_new(verification_path, verification)
    return freeze_path, dataset_path, verification_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--max-seconds", type=float, default=1200.0)
    parser.add_argument("--local-platform-validation", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("C38 output must be a new directory inside the package root")
    runtime_dir = output.with_name(output.name + "-runtime")
    if runtime_dir.exists():
        raise FileExistsError("C38 runtime directory already exists")
    runtime_dir.mkdir(parents=True)

    parent_freeze, parent_dataset, parent_verification = verify_parent_inputs()
    library, compiler, build_command = build_library(
        runtime_dir, args.compiler, args.local_platform_validation,
    )
    freeze_path, dataset_path, verification_path = derive_bound_inputs(
        runtime_dir, parent_freeze, parent_dataset, parent_verification,
        library, compiler, build_command, args.local_platform_validation,
    )

    def progress(stage: str, current: int, total: int, identity: str) -> None:
        interval = 54 if stage == "single_performance" else 24
        if current == total or current % interval == 0:
            print(f"c38 {stage} {current}/{total} {identity}", flush=True)

    result = run(
        NativeConfirmationConfig(run_id=args.run_id, max_seconds=args.max_seconds),
        output,
        freeze_path,
        dataset_path,
        verification_path,
        ROOT,
        progress=progress,
    )
    binding = {
        "schema": "crse-c38-c37-native-linux-replication-binding/v1",
        "status": "complete",
        "run_id": args.run_id,
        "local_platform_validation_only": args.local_platform_validation,
        "parent": {
            "freeze_sha256": EXPECTED_PARENT_FREEZE_SHA256,
            "dataset_sha256": EXPECTED_PARENT_DATASET_SHA256,
            "dataset_verification_sha256": EXPECTED_PARENT_DATASET_VERIFICATION_SHA256,
        },
        "derived": {
            "freeze": {"path": freeze_path.relative_to(ROOT).as_posix(), **file_identity(freeze_path)},
            "dataset": {"path": dataset_path.relative_to(ROOT).as_posix(), **file_identity(dataset_path)},
            "dataset_verification": {
                "path": verification_path.relative_to(ROOT).as_posix(),
                **file_identity(verification_path),
            },
        },
        "compiler": compiler,
        "build_command": build_command,
        "native_library": {"path": library.relative_to(ROOT).as_posix(), **file_identity(library)},
        "c37_schedule_and_gates_unchanged": True,
        "all_predeclared_gates_passed": result["decision"]["all_predeclared_gates_passed"],
        "production_promotion": False,
    }
    write_new(output / "c38_runtime_binding.json", binding)
    print(json.dumps({
        "status": result["status"],
        "local_platform_validation_only": args.local_platform_validation,
        "compiler": compiler.get("version"),
        "single_root_speedup": result["single_root"]["native_speedup_over_python_r2"],
        "multi_root_speedup": result["multi_root"]["union_speedup_over_separate"],
        "all_predeclared_gates_passed": result["decision"]["all_predeclared_gates_passed"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
