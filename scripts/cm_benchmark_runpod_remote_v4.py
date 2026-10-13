"""Run the bounded counting/biology/affine results screen on RunPod."""
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
import urllib.request
import time
import zipfile


ROOT = Path("/workspace/cm-benchmark")
OUT = Path("/workspace/cm-benchmark-probe")
SHARDS = Path(os.environ["CM_SHARD_DIR"])
EXPECTED = json.loads(os.environ["CM_SHARDS"])
RESULT = Path(os.environ["CM_RESULT_PATH"])


def stage(name):
    print("CM_STAGE " + name, flush=True)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def run(name, command, timeout):
    stage(name)
    started = time.monotonic()
    stdout, stderr = OUT / (name + ".stdout.txt"), OUT / (name + ".stderr.txt")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=timeout,
                                env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                                     "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    record = {"command": command, "returncode": result.returncode,
              "wall_seconds": time.monotonic() - started,
              "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr)}
    (OUT / (name + ".json")).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if result.returncode:
        stdout_tail = stdout.read_text(errors="replace")[-4000:]
        stderr_tail = stderr.read_text(errors="replace")[-4000:]
        raise RuntimeError(name + " failed:\nSTDOUT:\n" + stdout_tail + "\nSTDERR:\n" + stderr_tail)


def extract_shards():
    ROOT.mkdir(exist_ok=False)
    seen = {}
    for row in EXPECTED:
        path = SHARDS / row["path"]
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise RuntimeError("shard identity mismatch")
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                pure = PurePosixPath(info.filename)
                if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                    raise RuntimeError("unsafe shard member")
                if info.filename in {"BUNDLE_README.md", "BUNDLE_CONTENTS.json"}:
                    continue
                data = archive.read(info)
                target_name = info.filename.removeprefix("source/")
                target = ROOT.joinpath(*PurePosixPath(target_name).parts)
                prior = seen.get(target_name)
                current = hashlib.sha256(data).hexdigest()
                if prior is not None and prior != current:
                    raise RuntimeError("conflicting shard member")
                seen[target_name] = current
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
    (OUT / "SHARD-VERIFICATION.json").write_text(json.dumps({
        "status": "passed", "shards": len(EXPECTED), "files": len(seen),
        "compressed_bytes": sum(row["bytes"] for row in EXPECTED),
    }, indent=2, sort_keys=True) + "\n")


def install_native():
    vendor = ROOT / "docker/cm-benchmark-smoke/vendor"
    run("apt-install", ["apt-get", "update"], 300)
    run("apt-packages", ["apt-get", "install", "-y", "--no-install-recommends", "build-essential",
                         "cmake", "ninja-build", "libboost-program-options-dev", "libgmp-dev", "zlib1g-dev"], 600)
    with tarfile.open(vendor / "ganak-v2.6.4-linux-amd64.tar.gz") as archive:
        Path("/usr/local/bin/ganak").write_bytes(archive.extractfile("ganak").read())
    with zipfile.ZipFile(vendor / "kissat-4.0.4-linux-amd64.zip") as archive:
        Path("/usr/local/bin/kissat").write_bytes(archive.read("kissat-4.0.4-linux-amd64"))
    with tarfile.open(vendor / "cryptominisat5-v5.15.0-linux-amd64.tar.gz") as archive:
        Path("/usr/local/bin/cryptominisat5").write_bytes(archive.extractfile("cryptominisat5").read())
    for name in ("ganak", "kissat", "cryptominisat5"):
        Path("/usr/local/bin", name).chmod(0o755)
    source = Path("/tmp/d4")
    source.mkdir()
    with tarfile.open(vendor / "d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz") as archive:
        members = archive.getmembers()
        prefix = PurePosixPath(members[0].name).parts[0]
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError("unsafe d4 member")
        archive.extractall(source, filter="data")
    extracted = source / prefix
    shutil.copy2(vendor / "libpatoh-linux-x86_64-pr8.a", extracted / "3rdParty/patoh/libpatoh.a")
    run("d4-build", ["bash", "-lc", "cd /tmp/d4/*/demo/counter && ./build.sh -s"], 1200)
    built = next(source.glob("*/demo/counter/build/counter_static"))
    shutil.copy2(built, "/usr/local/bin/d4-counter")
    Path("/usr/local/bin/d4-counter").chmod(0o755)
    sat_wheel = Path("/tmp/python_sat-1.8.dev21-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl")
    request = urllib.request.Request(
        "https://files.pythonhosted.org/packages/82/07/625eb2ded13cf5054c5ed910d30492e52fdd1f5c7208249680cbef6d4db9/"
        "python_sat-1.8.dev21-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl",
        headers={"User-Agent": "cm-benchmark-environment-probe/1"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        sat_data = response.read(2843373)
    if len(sat_data) != 2843372 or hashlib.sha256(sat_data).hexdigest() != "dc427377620258dc392051fd93e6887037cf273283d0533bcd4ac74d58517b85":
        raise RuntimeError("Python-SAT wheel identity mismatch")
    sat_wheel.write_bytes(sat_data)
    run("python-dependencies", [sys.executable, "-m", "pip", "install", "--no-cache-dir",
                                "numpy==2.3.2", "sympy==1.14.0", str(sat_wheel),
                                "dd==0.6.0", "pytest==9.1.1",
                                str(vendor / "biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl")], 900)
    run("pip-check", [sys.executable, "-m", "pip", "check"], 60)


def runtime_record():
    memory = Path("/sys/fs/cgroup/memory.max")
    cpu = Path("/sys/fs/cgroup/cpu.max")
    text = Path("/proc/cpuinfo").read_text(errors="replace")
    record = {
        "schema": "cm-benchmark-runpod-runtime/v1", "platform": platform.platform(),
        "python": sys.version, "logical_cpus": os.cpu_count(), "affinity": sorted(os.sched_getaffinity(0)),
        "cgroup_memory_max": memory.read_text().strip() if memory.exists() else None,
        "cgroup_cpu_max": cpu.read_text().strip() if cpu.exists() else None,
        "cpu_model": next((line.partition(":")[2].strip() for line in text.splitlines() if line.startswith("model name")), None),
        "packages": {name: importlib.metadata.version(name) for name in
                     ("numpy", "sympy", "python-sat", "dd", "pytest", "biodivine-aeon")},
        "native_sha256": {name: digest(Path("/usr/local/bin") / name) for name in
                          ("ganak", "kissat", "cryptominisat5", "d4-counter")},
        "workload_network": False,
    }
    (OUT / "RUNTIME.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def install_core_screen():
    source = Path(os.environ["CM_CORE_SCREEN_SOURCE"])
    plan_source = Path(os.environ["CM_CORE_SCREEN_PLAN_SOURCE"])
    if (not source.is_file() or source.is_symlink() or not plan_source.is_file()
            or plan_source.is_symlink()):
        raise RuntimeError("core-screen control file missing or linked")
    if digest(source) != os.environ["CM_CORE_SCREEN_SHA256"]:
        raise RuntimeError("core-screen runner identity mismatch")
    if digest(plan_source) != os.environ["CM_CORE_SCREEN_PLAN_SHA256"]:
        raise RuntimeError("core-screen plan file identity mismatch")
    script = ROOT / "scripts/cm_benchmark_core_screen.py"
    if script.exists():
        raise RuntimeError("core-screen runner unexpectedly present in frozen shards")
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_bytes(source.read_bytes())
    plan_path = Path("/workspace/cm-core-screen-PLAN.json")
    with plan_path.open("xb") as stream:
        stream.write(plan_source.read_bytes())
    return script, plan_path


def main():
    OUT.mkdir(exist_ok=False)
    stage("verify-and-extract-11-shards")
    extract_shards()
    core_script, core_plan = install_core_screen()
    install_native()
    runtime_record()
    smoke = ROOT / "docker/cm-benchmark-smoke"
    Path("/opt/cm-smoke").mkdir(parents=True)
    for name in ("smoke.py", "NATIVE_LOCK.json"):
        shutil.copy2(smoke / name, Path("/opt/cm-smoke") / name)
    shutil.copytree(smoke / "fixtures", "/opt/cm-smoke/fixtures")
    run("native-linux-smoke", [sys.executable, "/opt/cm-smoke/smoke.py"], 180)
    run("focused-tests", [sys.executable, "-m", "pytest", "-q", "tests/test_cm_comparative_tasks.py",
                          "tests/test_cm_comparative_task_pilot.py", "tests/test_cm_benchmark_prelaunch.py",
                          "tests/test_cm_campaign_new_adapters.py", "tests/test_cm_native_count_adapter.py",
                          "tests/test_cm_native_sat_adapter.py", "-p", "no:cacheprovider",
                          "--deselect", "tests/test_cm_benchmark_prelaunch.py::"
                          "test_source_identity_marks_dirty_or_untracked_files_and_hashes_exact_bytes",
                          "--basetemp", "/workspace/cm-pytest"], 600)
    run("core-screen", [sys.executable, str(core_script), "run", "--plan", str(core_plan),
                        "--root", str(ROOT), "--output", str(OUT / "core-screen")], 3900)
    run("core-screen-verify", [sys.executable, str(core_script), "verify", "--plan", str(core_plan),
                               "--output", str(OUT / "core-screen")], 300)
    core_summary = json.loads((OUT / "core-screen/SUMMARY.json").read_text(encoding="utf-8"))
    ok_measurements = int(core_summary.get("status_counts", {}).get("ok", 0))
    status = "passed" if core_summary.get("status") == "complete" and ok_measurements else "failed"
    summary = {"schema": "cm-benchmark-runpod-core-screen/v1", "status": status,
               "shards": 11, "resource_writes": 1,
               "benchmark_measurements": ok_measurements,
               "performance_claims": len(core_summary.get("comparisons", {})),
               "core_screen": core_summary,
               "stages": [path.stem for path in sorted(OUT.glob("*.json"))]}
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    stage("archive-results")
    with zipfile.ZipFile(RESULT, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUT).as_posix())
    if RESULT.stat().st_size > 256 << 20:
        raise RuntimeError("probe result archive exceeds cap")
    print(json.dumps(summary, sort_keys=True), flush=True)


main()
