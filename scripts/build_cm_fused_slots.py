"""Build the local fused-slot C library without downloading dependencies."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native/cm_fused_slots/fused_slot_executor.c"


def build(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(ROOT.resolve()):
        raise ValueError("native build output must stay inside the project")
    output_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        candidates = (
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"),
            Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
        )
        vcvars = next((path for path in candidates if path.is_file()), None)
        if vcvars is None:
            raise RuntimeError("MSVC x64 environment script was not found")
        library = output_dir / "cm_fused_slots.dll"
        build_command = ROOT / "native/cm_fused_slots/build_msvc.cmd"
        subprocess.run([
            "cmd.exe", "/d", "/c", str(build_command),
            str(vcvars), str(SOURCE), str(output_dir),
        ], cwd=ROOT, check=True)
    else:
        compiler = shutil.which("cc")
        if compiler is None:
            raise RuntimeError("a C11 compiler was not found")
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        library = output_dir / f"libcm_fused_slots{suffix}"
        subprocess.run([
            compiler, "-std=c11", "-O3", "-Wall", "-Wextra", "-Wpedantic",
            "-shared", "-fPIC", str(SOURCE), "-o", str(library),
        ], cwd=ROOT, check=True)
    if not library.is_file():
        raise RuntimeError("native fused-slot library was not produced")
    return library


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "build/cm_fused_slots",
    )
    args = parser.parse_args()
    print(build(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
