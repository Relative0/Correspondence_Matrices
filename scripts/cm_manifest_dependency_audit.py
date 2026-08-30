"""Audit that a source manifest contains the local Python import closure."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path, PurePosixPath


def _module_candidates(root: Path, module: tuple[str, ...]) -> set[str]:
    if not module:
        return set()
    relative = Path(*module)
    candidates = set()
    module_file = root / relative.with_suffix(".py")
    package_file = root / relative / "__init__.py"
    if module_file.is_file():
        candidates.add(module_file.relative_to(root).as_posix())
    if package_file.is_file():
        candidates.add(package_file.relative_to(root).as_posix())
    for index in range(1, len(module)):
        initializer = root / Path(*module[:index]) / "__init__.py"
        if initializer.is_file():
            candidates.add(initializer.relative_to(root).as_posix())
    return candidates


def _source_package(target: str) -> tuple[str, ...]:
    pure = PurePosixPath(target)
    if pure.suffix != ".py":
        return ()
    parts = pure.with_suffix("").parts
    return tuple(parts[:-1] if parts[-1] != "__init__" else parts)


def imported_local_files(root: Path, target: str, data: bytes) -> set[str]:
    tree = ast.parse(data, filename=target)
    package = _source_package(target)
    required = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                required.update(_module_candidates(root, tuple(alias.name.split("."))))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.level > len(package) + 1:
                    continue
                base = package[:len(package) - node.level + 1]
            else:
                base = ()
            module = base + tuple((node.module or "").split(".")) if node.module else base
            required.update(_module_candidates(root, module))
            for alias in node.names:
                if alias.name != "*":
                    required.update(_module_candidates(root, module + tuple(alias.name.split("."))))
    return required


def audit_manifest(root: Path, manifest_path: Path) -> dict:
    root = root.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise ValueError("manifest files must be a list")
    targets = {row.get("target") for row in rows}
    if None in targets or len(targets) != len(rows):
        raise ValueError("manifest targets must be unique strings")
    missing = {}
    checked = 0
    for row in rows:
        target = row["target"]
        if not target.endswith(".py"):
            continue
        source = (root / row["source"]).resolve()
        source.relative_to(root)
        required = imported_local_files(root, target, source.read_bytes())
        absent = sorted(required - targets)
        if absent:
            missing[target] = absent
        checked += 1
    return {
        "schema": "cm-manifest-python-closure/v1",
        "manifest": str(manifest_path),
        "python_files_checked": checked,
        "missing": missing,
        "complete": not missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = audit_manifest(args.root, args.manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(not result["complete"])


if __name__ == "__main__":
    raise SystemExit(main())
