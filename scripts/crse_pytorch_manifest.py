"""Audit the approved CRSE PyTorch CPU wheel set and write its local manifest."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "filelock": "3.20.3", "fsspec": "2026.2.0", "Jinja2": "3.1.6",
    "MarkupSafe": "3.0.3", "mpmath": "1.3.0", "networkx": "3.5",
    "numpy": "2.3.2", "setuptools": "80.9.0", "sympy": "1.14.0",
    "torch": "2.10.0+cpu", "typing-extensions": "4.15.0",
}
LICENSES = {
    "torch": "BSD-3-Clause and bundled third-party notices", "numpy": "BSD-3-Clause and bundled notices",
    "sympy": "BSD-3-Clause", "mpmath": "BSD", "networkx": "BSD-3-Clause",
    "Jinja2": "BSD-3-Clause", "MarkupSafe": "BSD-3-Clause", "filelock": "Unlicense",
    "fsspec": "BSD-3-Clause", "typing-extensions": "PSF-2.0", "setuptools": "MIT",
}


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def wheel_record(path: Path):
    with zipfile.ZipFile(path) as archive:
        metadata_paths = [name for name in archive.namelist()
                          if name.endswith(".dist-info/METADATA") and name.count("/") == 1]
        if len(metadata_paths) != 1:
            raise ValueError(f"unexpected METADATA count in {path.name}")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
        license_files = sorted(name for name in archive.namelist()
                               if ".dist-info/license" in name.lower() and not name.endswith("/"))
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "metadata_name": metadata["Name"],
        "metadata_version": metadata["Version"],
        "metadata_license_expression": metadata["License-Expression"],
        "bundled_license_files": license_files,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path,
                        default=ROOT / "tmp" / "crse-neural-pytorch-2.10.0-cpu-wheelhouse")
    parser.add_argument("--environment", type=Path, default=ROOT / ".venv-crse-neural")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs" / "recognition" / "pytorch_cpu_2_10_0_manifest.json")
    args = parser.parse_args(argv)
    wheels = sorted(args.wheelhouse.glob("*.whl"))
    if len(wheels) != len(EXPECTED):
        raise SystemExit(f"expected {len(EXPECTED)} wheels; found {len(wheels)}")
    records = [wheel_record(path) for path in wheels]
    found = {record["metadata_name"].lower().replace("_", "-"): record["metadata_version"] for record in records}
    expected_normalized = {name.lower().replace("_", "-"): version for name, version in EXPECTED.items()}
    if found != expected_normalized:
        raise SystemExit(f"wheel metadata differs from approved pins: {found}")
    total = sum(record["bytes"] for record in records)
    if total > 250 * 1024 * 1024:
        raise SystemExit("approved wheel download cap exceeded")
    installed = {name: importlib.metadata.version(name) for name in EXPECTED}
    if installed != EXPECTED:
        raise SystemExit(f"installed versions differ from approved pins: {installed}")
    import torch
    torch.set_num_threads(2)
    x = torch.tensor([1.0, 2.0], requires_grad=True)
    (x * x).sum().backward()
    if torch.cuda.is_available() or x.grad.tolist() != [2.0, 4.0]:
        raise SystemExit("CPU/autograd smoke failed")
    environment_bytes = sum(path.stat().st_size for path in args.environment.rglob("*") if path.is_file())
    if environment_bytes + total > int(1.5 * 1024**3):
        raise SystemExit("approved environment plus wheelhouse disk cap exceeded")
    payload = {
        "schema": "crse-pytorch-dependency-manifest/v1",
        "status": "installed-and-verified",
        "approval_source": "docs/recognition/NEURAL_DEPENDENCY_REQUEST.md and explicit owner approval 2026-08-29",
        "sources": ["https://pypi.org/simple", "https://download.pytorch.org/whl/cpu"],
        "environment": str(args.environment.resolve()),
        "wheelhouse": str(args.wheelhouse.resolve()),
        "python": sys.version,
        "platform": platform.platform(),
        "wheels": records,
        "wheel_count": len(records),
        "wheel_bytes": total,
        "environment_bytes": environment_bytes,
        "combined_bytes": total + environment_bytes,
        "limits": {"wheel_bytes": 250 * 1024 * 1024, "combined_bytes": int(1.5 * 1024**3)},
        "declared_licenses": LICENSES,
        "installed_versions": installed,
        "verification": {"torch_version": torch.__version__, "cuda_available": False,
                         "cpu_threads": torch.get_num_threads(), "autograd_gradient": x.grad.tolist(),
                         "pip_check": "run separately: no broken requirements found"},
    }
    document = {**payload, "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(document, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"output": str(args.output), "wheels": len(records), "wheel_bytes": total,
                      "combined_bytes": total + environment_bytes, "torch": torch.__version__}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
