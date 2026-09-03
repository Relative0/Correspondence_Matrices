"""Build the native runtime and execute or smoke-test the frozen comparison."""
from __future__ import annotations

import argparse
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

from cmbench.comparative.architecture_comparison_campaign import (
    functional_smoke,
    run_campaign,
    validate_oracles,
)


POSIX_FLAGS = (
    "-std=c11", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-shared", "-fPIC",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _build_native(runtime: Path, compiler: str, local_validation: bool) -> tuple[Path, dict[str, Any]]:
    runtime.mkdir(parents=True, exist_ok=False)
    source = ROOT / "native/cm_fused_slots/fused_slot_executor.c"
    if local_validation:
        from scripts.build_cm_fused_slots import build
        library = build(runtime)
        identity = {
            "role": "local_functional_package_validation_only",
            "platform": platform.platform(),
            "command": ["host-native-build", str(source), str(library)],
        }
    else:
        if os.name == "nt" or sys.platform != "linux":
            raise RuntimeError("decision-bearing architecture campaign requires Linux")
        resolved = shutil.which(compiler)
        if resolved is None:
            raise RuntimeError(f"compiler unavailable: {compiler}")
        executable = Path(resolved).resolve()
        version = subprocess.run(
            [str(executable), "--version"], check=True, capture_output=True,
            text=True, timeout=20,
        )
        library = runtime / "libcm_fused_slots.so"
        command = [str(executable), *POSIX_FLAGS, str(source), "-o", str(library)]
        completed = subprocess.run(
            command, cwd=ROOT, check=True, capture_output=True, text=True, timeout=120,
        )
        if completed.stdout or completed.stderr:
            (runtime / "compiler-output.txt").write_text(
                completed.stdout + completed.stderr, encoding="utf-8", newline="\n"
            )
        identity = {
            "role": "decision_bearing_linux_campaign",
            "platform": platform.platform(),
            "compiler_executable": str(executable),
            "compiler_executable_sha256": _sha256(executable),
            "compiler_version": (version.stdout + version.stderr).strip(),
            "command": command,
        }
    identity.update(
        native_library=library.name,
        native_library_bytes=library.stat().st_size,
        native_library_sha256=_sha256(library),
    )
    return library, identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, default=ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json")
    parser.add_argument("--oracles", type=Path, default=ROOT / "docs/recognition/architecture_comparison_execution_20260903/ORACLES.json")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--max-seconds", type=float, default=1200.0)
    parser.add_argument("--functional-smoke", action="store_true")
    parser.add_argument("--local-platform-validation", action="store_true")
    args = parser.parse_args()
    freeze_path = args.freeze.resolve()
    oracle_path = args.oracles.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise SystemExit("output must be a new path inside the project")
    freeze = _load(freeze_path)
    oracles = _load(oracle_path)
    validate_oracles(oracles, ROOT, freeze)
    runtime = output.parent / f".{output.name}-native-runtime"
    if runtime.exists():
        raise SystemExit("native runtime path already exists")
    library, native_identity = _build_native(
        runtime, args.compiler, args.local_platform_validation
    )
    if args.functional_smoke:
        output.mkdir(parents=True)
        result = functional_smoke(ROOT, freeze, oracles, library)
        result["local_platform_validation_only"] = bool(args.local_platform_validation)
        result["native_runtime"] = native_identity
        result["freeze_file_sha256"] = _sha256(freeze_path)
        result["oracles_file_sha256"] = _sha256(oracle_path)
        _write_json(output / "functional_smoke.json", result)
    else:
        if args.local_platform_validation:
            raise SystemExit("local platform validation cannot emit campaign timing")
        result = run_campaign(
            project_root=ROOT,
            freeze_path=freeze_path,
            oracles_path=oracle_path,
            native_library_path=library,
            output_dir=output,
            max_seconds=args.max_seconds,
        )
        _write_json(output / "runtime_binding.json", native_identity)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
