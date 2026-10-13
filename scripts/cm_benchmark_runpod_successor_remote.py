"""Run the bounded exact-count and closed-biology successor screen on RunPod."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile


ROOT = Path("/workspace/cm-benchmark")
OUT = Path("/workspace/cm-benchmark-successor")
SHARDS = Path(os.environ["CM_SHARD_DIR"])
EXPECTED = json.loads(os.environ["CM_SHARDS"])
RESULT = Path(os.environ["CM_RESULT_PATH"])


def stage(name: str) -> None:
    print("CM_STAGE " + name, flush=True)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def run(name: str, command: list[str], timeout: float) -> None:
    stage(name)
    started = time.monotonic()
    stdout = OUT / (name + ".stdout.txt")
    stderr = OUT / (name + ".stderr.txt")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=out,
            stderr=err,
            timeout=timeout,
            env={
                **os.environ,
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
            },
        )
    record = {
        "command": command,
        "returncode": result.returncode,
        "wall_seconds": time.monotonic() - started,
        "stdout_sha256": digest(stdout),
        "stderr_sha256": digest(stderr),
    }
    (OUT / (name + ".json")).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result.returncode:
        raise RuntimeError(
            name
            + " failed:\nSTDOUT:\n"
            + stdout.read_text(errors="replace")[-4000:]
            + "\nSTDERR:\n"
            + stderr.read_text(errors="replace")[-4000:]
        )


def extract_shards() -> None:
    ROOT.mkdir(exist_ok=False)
    seen = {}
    for row in EXPECTED:
        path = SHARDS / row["path"]
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise RuntimeError("shard identity mismatch")
        if row["bytes"] > 64 << 20 or row["expanded_bytes"] > 128 << 20:
            raise RuntimeError("shard bound mismatch")
        expanded = 0
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                pure = PurePosixPath(info.filename)
                if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                    raise RuntimeError("unsafe shard member")
                expanded += info.file_size
                if expanded > row["expanded_bytes"]:
                    raise RuntimeError("shard expansion mismatch")
                if info.filename in {"BUNDLE_README.md", "BUNDLE_CONTENTS.json"}:
                    continue
                data = archive.read(info)
                target_name = info.filename.removeprefix("source/")
                current = hashlib.sha256(data).hexdigest()
                if target_name in seen and seen[target_name] != current:
                    raise RuntimeError("conflicting shard member")
                seen[target_name] = current
                target = ROOT.joinpath(*PurePosixPath(target_name).parts)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
    (OUT / "SHARD-VERIFICATION.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "shards": len(EXPECTED),
                "files": len(seen),
                "compressed_bytes": sum(row["bytes"] for row in EXPECTED),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def verify_vendor() -> dict[str, str]:
    lock = json.loads(
        (ROOT / "docker/cm-benchmark-smoke/NATIVE_LOCK.json").read_text(
            encoding="utf-8"
        )
    )
    vendor = ROOT / "docker/cm-benchmark-smoke/vendor"
    hashes = {}
    for item in lock["exercised_artifacts"]:
        path = vendor / item["asset"]
        hashes[item["asset"]] = digest(path)
        if hashes[item["asset"]] != item["sha256"]:
            raise RuntimeError("native vendor identity mismatch")
    return hashes


def install_native() -> dict[str, str]:
    vendor = ROOT / "docker/cm-benchmark-smoke/vendor"
    hashes = verify_vendor()
    run("apt-update", ["apt-get", "update"], 300)
    run(
        "apt-packages",
        [
            "apt-get",
            "install",
            "-y",
            "--no-install-recommends",
            "build-essential",
            "cmake",
            "ninja-build",
            "libboost-program-options-dev",
            "libgmp-dev",
            "zlib1g-dev",
        ],
        600,
    )
    with tarfile.open(vendor / "ganak-v2.6.4-linux-amd64.tar.gz") as archive:
        Path("/usr/local/bin/ganak").write_bytes(archive.extractfile("ganak").read())
    with zipfile.ZipFile(vendor / "kissat-4.0.4-linux-amd64.zip") as archive:
        Path("/usr/local/bin/kissat").write_bytes(
            archive.read("kissat-4.0.4-linux-amd64")
        )
    with tarfile.open(
        vendor / "cryptominisat5-v5.15.0-linux-amd64.tar.gz"
    ) as archive:
        Path("/usr/local/bin/cryptominisat5").write_bytes(
            archive.extractfile("cryptominisat5").read()
        )
    for name in ("ganak", "kissat", "cryptominisat5"):
        Path("/usr/local/bin", name).chmod(0o755)

    source = Path("/tmp/d4-successor")
    source.mkdir()
    with tarfile.open(
        vendor / "d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz"
    ) as archive:
        members = archive.getmembers()
        prefix = PurePosixPath(members[0].name).parts[0]
        if any(
            PurePosixPath(member.name).is_absolute()
            or ".." in PurePosixPath(member.name).parts
            for member in members
        ):
            raise RuntimeError("unsafe d4 member")
        archive.extractall(source, filter="data")
    extracted = source / prefix
    shutil.copy2(
        vendor / "libpatoh-linux-x86_64-pr8.a",
        extracted / "3rdParty/patoh/libpatoh.a",
    )
    run(
        "d4-build",
        ["bash", "-lc", "cd /tmp/d4-successor/*/demo/counter && ./build.sh -s"],
        1200,
    )
    built = next(source.glob("*/demo/counter/build/counter_static"))
    shutil.copy2(built, "/usr/local/bin/d4-counter")
    Path("/usr/local/bin/d4-counter").chmod(0o755)
    run(
        "aeon-install",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--no-deps",
            str(vendor / "biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl"),
        ],
        300,
    )
    return hashes


def install_core_screen() -> tuple[Path, Path]:
    source = Path(os.environ["CM_CORE_SCREEN_SOURCE"])
    plan_source = Path(os.environ["CM_CORE_SCREEN_PLAN_SOURCE"])
    if (
        not source.is_file()
        or source.is_symlink()
        or not plan_source.is_file()
        or plan_source.is_symlink()
    ):
        raise RuntimeError("successor control file missing or linked")
    if digest(source) != os.environ["CM_CORE_SCREEN_SHA256"]:
        raise RuntimeError("successor runner identity mismatch")
    if digest(plan_source) != os.environ["CM_CORE_SCREEN_PLAN_SHA256"]:
        raise RuntimeError("successor plan identity mismatch")
    script = ROOT / "scripts/cm_benchmark_core_screen_v2.py"
    if script.exists():
        raise RuntimeError("successor runner unexpectedly present in shard")
    script.write_bytes(source.read_bytes())
    plan_path = Path("/workspace/cm-successor-PLAN.json")
    plan_path.write_bytes(plan_source.read_bytes())
    return script, plan_path


def runtime_record(vendor_hashes: dict[str, str]) -> None:
    memory = Path("/sys/fs/cgroup/memory.max")
    cpu = Path("/sys/fs/cgroup/cpu.max")
    record = {
        "schema": "cm-benchmark-runpod-successor-runtime/v1",
        "platform": platform.platform(),
        "python": sys.version,
        "logical_cpus": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)),
        "cgroup_memory_max": memory.read_text().strip() if memory.exists() else None,
        "cgroup_cpu_max": cpu.read_text().strip() if cpu.exists() else None,
        "biodivine_aeon": importlib.metadata.version("biodivine-aeon"),
        "native_sha256": {
            name: digest(Path("/usr/local/bin") / name)
            for name in ("ganak", "kissat", "cryptominisat5", "d4-counter")
        },
        "vendor_sha256": vendor_hashes,
        "workload_network": False,
    }
    (OUT / "RUNTIME.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUT.mkdir(exist_ok=False)
    stage("verify-and-extract-successor-shard")
    extract_shards()
    core_script, core_plan = install_core_screen()
    vendor_hashes = install_native()
    runtime_record(vendor_hashes)
    run(
        "native-linux-smoke-v3",
        [sys.executable, str(ROOT / "docker/cm-benchmark-smoke/smoke_v2.py")],
        180,
    )
    run(
        "successor-screen",
        [
            sys.executable,
            str(core_script),
            "run",
            "--plan",
            str(core_plan),
            "--root",
            str(ROOT),
            "--output",
            str(OUT / "core-screen"),
        ],
        3900,
    )
    run(
        "successor-screen-verify",
        [
            sys.executable,
            str(core_script),
            "verify",
            "--plan",
            str(core_plan),
            "--output",
            str(OUT / "core-screen"),
        ],
        300,
    )
    core_summary = json.loads(
        (OUT / "core-screen/SUMMARY.json").read_text(encoding="utf-8")
    )
    ok_measurements = int(core_summary.get("status_counts", {}).get("ok", 0))
    status = (
        "passed"
        if core_summary.get("status") == "complete"
        and not core_summary.get("correctness_mismatches")
        and ok_measurements
        else "failed"
    )
    summary = {
        "schema": "cm-benchmark-runpod-successor-screen/v1",
        "status": status,
        "shards": len(EXPECTED),
        "resource_writes": 1,
        "benchmark_measurements": ok_measurements,
        "core_screen": core_summary,
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if status != "passed":
        raise RuntimeError("successor screen did not pass")
    stage("archive-successor-results")
    with zipfile.ZipFile(RESULT, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUT).as_posix())
    if RESULT.stat().st_size > 256 << 20:
        raise RuntimeError("successor result archive exceeds cap")
    print(json.dumps(summary, sort_keys=True), flush=True)


main()
