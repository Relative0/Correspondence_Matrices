"""Build and hash-close the C37 native confirmation before dataset creation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_cm_fused_slots import build


PROTOCOL = "docs/recognition/c37_native_exact_confirmation/FROZEN_PROTOCOL_V3_2026_09_03.md"
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_root.py",
    "cmbench/comparative/gf2_multi_root_experiment.py",
    "cmbench/comparative/gf2_native_confirmation.py",
    "cmbench/comparative/gf2_native_slot_experiment.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_projection_optimization_experiment.py",
    "cmbench/comparative/gf2_projection_optimized.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/portfolio.py",
    "cmbench/recognition/yosys_native_confirmation_data.py",
    "cmbench/recognition/yosys_unused_gf2_data.py",
    "cmbench/recognition/yosys_wide_restriction_data.py",
    "native/cm_fused_slots/build_msvc.cmd",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/build_cm_fused_slots.py",
    "scripts/cm_native_exact_confirmation.py",
    "scripts/crse_freeze_c37_native_confirmation.py",
    "scripts/crse_native_exact_confirmation_verify.py",
    "scripts/crse_prepare_c37_native_confirmation_dataset.py",
    "scripts/crse_verify_c37_native_confirmation_dataset.py",
    PROTOCOL,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compiler_identity() -> dict[str, str | None]:
    if os.name != "nt":
        compiler = subprocess.run(
            ["cc", "--version"], check=True, capture_output=True, text=True
        )
        return {"kind": "cc", "version": (compiler.stdout + compiler.stderr).strip()}
    candidates = (
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"),
        Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
    )
    vcvars = next((path for path in candidates if path.is_file()), None)
    if vcvars is None:
        raise RuntimeError("MSVC x64 environment script was not found")
    tool_root = vcvars.parents[2] / "Tools" / "MSVC"
    compiler_paths = sorted(
        tool_root.glob("*/bin/Hostx64/x64/cl.exe"), reverse=True
    )
    if not compiler_paths:
        raise RuntimeError("MSVC x64 compiler executable was not found")
    compiler_path = compiler_paths[0]
    result = subprocess.run(
        [str(compiler_path), "/Bv"], cwd=ROOT, check=False,
        capture_output=True, text=True,
    )
    if result.returncode not in (0, 2):
        raise RuntimeError("could not identify MSVC compiler")
    return {
        "kind": "msvc_x64",
        "vcvars": str(vcvars),
        "compiler_executable": str(compiler_path),
        "compiler_executable_sha256": sha256(compiler_path),
        "version": (result.stdout + result.stderr).strip(),
    }


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze-dir", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation/frozen_native_v3",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation/freeze_v3.json",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    freeze_dir = args.freeze_dir.resolve()
    if not output.is_relative_to(ROOT) or not freeze_dir.is_relative_to(ROOT):
        raise ValueError("C37 freeze paths must stay inside the project")
    if output.exists() or freeze_dir.exists():
        raise FileExistsError("C37 freeze is immutable and already exists")
    missing = [relative for relative in SOURCE_PATHS if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"C37 freeze source missing: {missing}")
    compiler = compiler_identity()
    library = build(freeze_dir)
    from cmbench.comparative.gf2_native_slots import load_native_slot_library
    loaded = load_native_slot_library(library)
    if loaded.abi_version != 1 or not loaded.supports_multi_root:
        raise RuntimeError("C37 native ABI capability mismatch")
    document = {
        "schema": "crse-c37-native-confirmation-freeze/v1",
        "status": "frozen_before_dataset_and_timing",
        "date": "2026-09-03",
        "protocol": {
            "path": PROTOCOL,
            "sha256": sha256(ROOT / PROTOCOL),
        },
        "sources": {
            relative: {"bytes": (ROOT / relative).stat().st_size,
                       "sha256": sha256(ROOT / relative)}
            for relative in SOURCE_PATHS
        },
        "native_library": {
            "path": library.relative_to(ROOT).as_posix(),
            "bytes": library.stat().st_size,
            "sha256": loaded.sha256,
            "abi_version": loaded.abi_version,
            "supports_multi_root": loaded.supports_multi_root,
        },
        "compiler": compiler,
        "build_contract": (
            "Windows: cl.exe /nologo /O2 /W4 /LD fused_slot_executor.c; "
            "POSIX: cc -std=c11 -O3 -Wall -Wextra -Wpedantic -shared -fPIC"
        ),
        "environment": {
            "python": sys.version,
            "python_executable": sys.executable,
            "python_executable_sha256": sha256(Path(sys.executable)),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "scientific_boundary": {
            "dataset_created": False,
            "prospective_timing_run": False,
            "timing_results_inspected": False,
            "training": False,
            "policy_refit": False,
            "gate_refit": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new(output, document)
    print(json.dumps({
        "status": "frozen", "freeze": str(output),
        "library": str(library), "library_sha256": loaded.sha256,
        "sources": len(SOURCE_PATHS),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
