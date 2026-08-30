"""Record the read-only, sparse LogikBench acquisition without executing corpus code."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[6]
SOURCE = ROOT / "external/logikbench-confirmation-20260830"
OUTPUT = Path(__file__).resolve().parent / "W8-LOGIKBENCH-ACQUISITION.json"
EXPECTED_COMMIT = "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
EXPECTED_REMOTE = "https://github.com/zeroasiccorp/logikbench.git"
EXPECTED_SPARSE = (
    "LICENSE",
    "README.md",
    "logikbench/benchmarks/arithmetic",
    "logikbench/benchmarks/basic",
    "logikbench/benchmarks/blocks",
    "pyproject.toml",
)
GROUPS = ("basic", "arithmetic", "blocks")
RTL_SUFFIXES = frozenset({".v", ".sv", ".vh", ".svh"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    environment = dict(os.environ)
    environment["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    return subprocess.check_output(
        ["git", "-C", str(SOURCE), *args],
        text=True,
        encoding="utf-8",
        env=environment,
    ).strip()


def row(path: Path) -> dict:
    relative = path.relative_to(SOURCE).as_posix()
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> int:
    if not SOURCE.is_dir():
        raise RuntimeError("pinned LogikBench checkout is absent")
    if git("rev-parse", "HEAD") != EXPECTED_COMMIT:
        raise RuntimeError("LogikBench commit mismatch")
    if git("remote", "get-url", "origin") != EXPECTED_REMOTE:
        raise RuntimeError("LogikBench remote mismatch")
    if git("status", "--porcelain"):
        raise RuntimeError("LogikBench checkout is not clean")
    sparse = tuple(sorted(git("sparse-checkout", "list").splitlines()))
    if sparse != EXPECTED_SPARSE:
        raise RuntimeError("LogikBench sparse-checkout paths changed")
    if (SOURCE / ".gitmodules").exists():
        raise RuntimeError("submodules are outside the acquisition contract")

    materialized = []
    for name in git("ls-files").splitlines():
        path = SOURCE / Path(name)
        if not path.exists():
            continue
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("non-regular materialized path: " + name)
        materialized.append(row(path))

    clusters = []
    for group in GROUPS:
        group_root = SOURCE / "logikbench/benchmarks" / group
        for directory in sorted((item for item in group_root.iterdir() if item.is_dir()),
                                key=lambda item: item.name.encode("utf-8")):
            files = sorted((item for item in directory.rglob("*") if item.is_file()),
                           key=lambda item: item.relative_to(directory).as_posix().encode("utf-8"))
            if any(item.is_symlink() for item in files):
                raise RuntimeError("cluster contains a symlink: " + directory.name)
            local_licenses = [
                item.relative_to(SOURCE).as_posix() for item in files
                if item.name.lower() in {"license", "license.txt", "copying", "notice"}
            ]
            rtl = [item.relative_to(SOURCE).as_posix() for item in files
                   if item.suffix.lower() in RTL_SUFFIXES
                   and item.relative_to(directory).parts[0] == "rtl"]
            clusters.append({
                "cluster_id": f"logikbench-{group}-{directory.name}",
                "group": group,
                "name": directory.name,
                "files": len(files),
                "bytes": sum(item.stat().st_size for item in files),
                "tree_sha256": hashlib.sha256("\n".join(
                    f"{item.relative_to(directory).as_posix()}\0{item.stat().st_size}\0{sha256(item)}"
                    for item in files
                ).encode("utf-8")).hexdigest(),
                "rtl_paths": rtl,
                "rtl_files": len(rtl),
                "readme_present": (directory / "README.md").is_file(),
                "ai_provenance_present": (directory / "ai.json").is_file(),
                "local_license_paths": local_licenses,
                "license_inheritance": "benchmark-local" if local_licenses else "repository-root-MIT",
            })

    counts = {group: sum(item["group"] == group for item in clusters) for group in GROUPS}
    report = {
        "schema": "cm-comparative-w8-logikbench-acquisition/v1",
        "repository": EXPECTED_REMOTE,
        "commit": EXPECTED_COMMIT,
        "detached_head": git("rev-parse", "--abbrev-ref", "HEAD") == "HEAD",
        "clean": True,
        "submodules_used": False,
        "repository_code_executed": False,
        "package_install_performed": False,
        "comparative_timing_inspected": False,
        "sparse_paths": list(sparse),
        "root_license": row(SOURCE / "LICENSE"),
        "root_readme": row(SOURCE / "README.md"),
        "materialized_files": materialized,
        "materialized_file_count": len(materialized),
        "materialized_bytes": sum(item["bytes"] for item in materialized),
        "clusters": clusters,
        "cluster_count": len(clusters),
        "cluster_counts_by_group": counts,
        "clusters_with_rtl": sum(bool(item["rtl_paths"]) for item in clusters),
        "clusters_with_ai_provenance": sum(item["ai_provenance_present"] for item in clusters),
        "clusters_with_local_license": sum(bool(item["local_license_paths"]) for item in clusters),
        "ready_for_static_admission_audit": len(clusters) >= 30,
    }
    if (
        len(materialized) != 643
        or report["materialized_bytes"] != 5_470_902
        or len(clusters) != 140
        or counts != {"basic": 26, "arithmetic": 71, "blocks": 43}
        or not report["ready_for_static_admission_audit"]
    ):
        raise RuntimeError("acquisition inventory differs from the reviewed checkout")

    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, OUTPUT)
    print(json.dumps({
        "commit": report["commit"],
        "materialized_files": report["materialized_file_count"],
        "materialized_bytes": report["materialized_bytes"],
        "clusters": report["cluster_count"],
        "counts": counts,
        "clusters_with_rtl": report["clusters_with_rtl"],
        "clusters_with_ai_provenance": report["clusters_with_ai_provenance"],
        "clusters_with_local_license": report["clusters_with_local_license"],
        "ready": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
