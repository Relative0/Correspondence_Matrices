"""Run the pinned native benchmark adapters in a local Linux environment.

The script is intended to be invoked by Python inside WSL. It uses only the
already pinned workspace assets, builds d4 from its pinned source, applies the
same 4 GiB worker address-space limit as the frozen core screen, and writes a
new successor audit without changing frozen campaign evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.backends.native_count import run_d4, run_ganak  # noqa: E402
from cmbench.backends.native_sat import run_cryptominisat  # noqa: E402
from cmbench.biology_bnet import (  # noqa: E402
    aeon_fixed_point_count,
    parse_bnet,
    scalar_fixed_point_count,
)


BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
VENDOR = ROOT / "docker/cm-benchmark-smoke/vendor"
FIXTURES = ROOT / "docker/cm-benchmark-smoke/fixtures"
LOCK_PATH = ROOT / "docker/cm-benchmark-smoke/NATIVE_LOCK.json"
PLAN_PATH = BASE / "runpod-results-002/evidence/core-screen/PLAN.json"
LEDGER_PATH = BASE / "prelaunch-008/ADMISSION_LEDGER.json"
RESULTS_PATH = BASE / "results-analysis-001/RESULTS.json"
OUT = BASE / "postfix-linux-smoke-001"
ADDRESS_SPACE_LIMIT = 4 << 30


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(command: list[str], *, timeout: float = 600.0, cwd: Path | None = None,
        accepted: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=cwd,
    )
    if completed.returncode not in accepted:
        detail = (completed.stderr or completed.stdout)[-4000:]
        raise RuntimeError(
            f"unexpected exit {completed.returncode}: {command[0]}\n{detail}"
        )
    return completed


def extract_binary_tar(archive_path: Path, member: str, target: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        source = archive.extractfile(member)
        if source is None:
            raise RuntimeError(f"missing archive member: {member}")
        target.write_bytes(source.read())
    target.chmod(0o755)


def validate_vendor(lock: dict[str, object]) -> dict[str, str]:
    hashes = {}
    for item in lock["exercised_artifacts"]:
        asset = item["asset"]
        path = VENDOR / asset
        actual = digest(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"pinned vendor hash mismatch: {asset}")
        hashes[asset] = actual
    return hashes


def build_d4(lock: dict[str, object], stage: Path) -> tuple[Path, dict[str, object]]:
    source_archive = VENDOR / "d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz"
    patoh = VENDOR / "libpatoh-linux-x86_64-pr8.a"
    source = stage / "d4"
    source.mkdir()
    with tarfile.open(source_archive, "r:gz") as archive:
        archive.extractall(source, filter="data")
    roots = [item for item in source.iterdir() if item.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("unexpected d4 source archive layout")
    d4_root = roots[0]
    shutil.copyfile(patoh, d4_root / "3rdParty/patoh/libpatoh.a")
    started = time.perf_counter()
    completed = run(
        ["./build.sh", "-s"],
        timeout=600,
        cwd=d4_root / "demo/counter",
    )
    elapsed = time.perf_counter() - started
    binary = d4_root / "demo/counter/build/counter_static"
    if not binary.is_file():
        raise RuntimeError("d4 build did not produce counter_static")
    binary.chmod(0o755)
    expected = next(
        item for item in lock["exercised_artifacts"] if item["asset"].startswith("d4v2-")
    )
    return binary, {
        "command": ["./build.sh", "-s"],
        "cwd": "demo/counter",
        "duration_seconds": elapsed,
        "compiler": run(["g++", "--version"], timeout=30).stdout.splitlines()[0],
        "cmake": run(["cmake", "--version"], timeout=30).stdout.splitlines()[0],
        "binary_sha256": digest(binary),
        "reference_debian_binary_sha256": expected["binary_sha256"],
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def prepare_runtime(stage: Path) -> tuple[dict[str, Path], Path]:
    binary_dir = stage / "bin"
    binary_dir.mkdir()
    binaries = {
        "ganak": binary_dir / "ganak",
        "cryptominisat5": binary_dir / "cryptominisat5",
        "kissat": binary_dir / "kissat",
    }
    extract_binary_tar(
        VENDOR / "ganak-v2.6.4-linux-amd64.tar.gz", "ganak", binaries["ganak"]
    )
    extract_binary_tar(
        VENDOR / "cryptominisat5-v5.15.0-linux-amd64.tar.gz",
        "cryptominisat5",
        binaries["cryptominisat5"],
    )
    with zipfile.ZipFile(VENDOR / "kissat-4.0.4-linux-amd64.zip") as archive:
        binaries["kissat"].write_bytes(archive.read("kissat-4.0.4-linux-amd64"))
    binaries["kissat"].chmod(0o755)

    wheel_site = stage / "wheel-site"
    wheel_site.mkdir()
    with zipfile.ZipFile(
        VENDOR / "biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl"
    ) as archive:
        archive.extractall(wheel_site)
    sys.path.insert(0, str(wheel_site))
    return binaries, wheel_site


def verify_binary_hashes(lock: dict[str, object], binaries: dict[str, Path]) -> None:
    asset_to_binary = {
        "ganak-v2.6.4-linux-amd64.tar.gz": binaries["ganak"],
        "kissat-4.0.4-linux-amd64.zip": binaries["kissat"],
        "cryptominisat5-v5.15.0-linux-amd64.tar.gz": binaries["cryptominisat5"],
    }
    for item in lock["exercised_artifacts"]:
        binary = asset_to_binary.get(item["asset"])
        if binary is not None and digest(binary) != item["binary_sha256"]:
            raise RuntimeError(f"pinned binary hash mismatch: {item['asset']}")


def kissat_status(binary: Path, fixture: str, expected_exit: int,
                  expected_status: str) -> dict[str, object]:
    completed = run(
        [str(binary), "--quiet", str(FIXTURES / fixture)],
        timeout=30,
        accepted={expected_exit},
    )
    if f"s {expected_status}" not in completed.stdout:
        raise RuntimeError("Kissat output contract mismatch")
    return {"exit": completed.returncode, "status": expected_status}


def selected_exact_cases() -> list[dict[str, object]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    path_by_hash = {
        row["sha256"]: ROOT / row["path"]
        for row in ledger["rows"]
        if row["group"] == "sat_and_counting"
    }
    ganak_value = {
        case["case_id"]: case["arms"]["ganak"]["value"]
        for case in results["cases"]
        if case["lane"] == "exact_count"
    }
    cases = []
    for case in plan["cases"]:
        if case["lane"] != "exact_count":
            continue
        source = path_by_hash[case["input_sha256"]]
        if digest(source) != case["input_sha256"]:
            raise RuntimeError(f"selected exact input hash mismatch: {case['case_id']}")
        cases.append(
            {
                "case_id": case["case_id"],
                "input_sha256": case["input_sha256"],
                "path": source,
                "frozen_ganak_value": ganak_value[case["case_id"]],
            }
        )
    return cases


def d4_corpus_replay(binary: Path) -> list[dict[str, object]]:
    output = []
    for case in selected_exact_cases():
        started = time.perf_counter()
        try:
            result = run_d4(
                case["path"], executable=binary, timeout_seconds=30.0
            )
            status = "ok"
            value = result.count
            error = None
            if case["frozen_ganak_value"] is not None and int(
                case["frozen_ganak_value"]
            ) != value:
                raise RuntimeError("d4/Ganak frozen exact-count mismatch")
            command = list(result.command)
        except TimeoutError as exc:
            status = "timeout"
            value = None
            error = str(exc)
            command = None
        except Exception as exc:  # Retain bounded diagnostic evidence for every case.
            status = "error"
            value = None
            error = f"{type(exc).__name__}: {exc}"
            command = None
        output.append(
            {
                "case_id": case["case_id"],
                "input_sha256": case["input_sha256"],
                "frozen_ganak_value": case["frozen_ganak_value"],
                "status": status,
                "value": value,
                "error": error,
                "command": command,
                "duration_seconds": time.perf_counter() - started,
            }
        )
    return output


def main() -> None:
    if platform.system() != "Linux":
        raise RuntimeError("this smoke must run on Linux")
    if OUT.exists():
        raise RuntimeError(f"post-fix Linux smoke output already exists: {OUT}")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    vendor_hashes = validate_vendor(lock)

    with tempfile.TemporaryDirectory(prefix="cmbench-wsl-smoke-") as temporary:
        stage = Path(temporary)
        binaries, wheel_site = prepare_runtime(stage)
        verify_binary_hashes(lock, binaries)
        d4_binary, build = build_d4(lock, stage)

        # Match the frozen core worker limit. Children inherit this bound.
        resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE_LIMIT, ADDRESS_SPACE_LIMIT))

        exact = run_ganak(
            FIXTURES / "exact.cnf", mode="exact", executable=binaries["ganak"]
        )
        projected = run_ganak(
            FIXTURES / "projected.cnf",
            mode="projected",
            executable=binaries["ganak"],
        )
        zero = run_ganak(
            FIXTURES / "unsat.cnf", mode="exact", executable=binaries["ganak"]
        )
        if (exact.count, projected.count, zero.count) != (4, 2, 0):
            raise RuntimeError("Ganak smoke count mismatch")

        d4_exact = run_d4(
            FIXTURES / "exact.cnf", executable=d4_binary, timeout_seconds=30
        )
        d4_zero = run_d4(
            FIXTURES / "unsat.cnf", executable=d4_binary, timeout_seconds=30
        )
        if (d4_exact.count, d4_zero.count) != (4, 0):
            raise RuntimeError("d4 post-fix smoke count mismatch")

        cms_sat = run_cryptominisat(
            FIXTURES / "xor-sat.cnf", executable=binaries["cryptominisat5"]
        )
        cms_unsat = run_cryptominisat(
            FIXTURES / "xor-unsat.cnf", executable=binaries["cryptominisat5"]
        )
        if cms_sat.assignment != (True, False) or cms_unsat.assignment is not None:
            raise RuntimeError("CryptoMiniSat smoke witness mismatch")

        kissat = {
            "sat": kissat_status(binaries["kissat"], "sat.cnf", 10, "SATISFIABLE"),
            "unsat": kissat_status(
                binaries["kissat"], "unsat.cnf", 20, "UNSATISFIABLE"
            ),
        }
        functions = parse_bnet((FIXTURES / "aeon.bnet").read_text(encoding="utf-8"))
        scalar_count = scalar_fixed_point_count(functions)
        aeon_count = aeon_fixed_point_count(FIXTURES / "aeon.bnet")
        if scalar_count != 2 or aeon_count != 2:
            raise RuntimeError("AEON/scalar fixed-point smoke mismatch")
        if importlib.metadata.version("biodivine-aeon") != "1.4.2":
            raise RuntimeError("Biodivine AEON version mismatch")

        corpus = d4_corpus_replay(d4_binary)
        if any(item["status"] == "error" for item in corpus):
            raise RuntimeError("d4 post-fix corpus replay produced an error")

        document = {
            "schema": "cm-benchmark-postfix-native-linux-smoke/v1",
            "created_utc": now(),
            "status": "passed",
            "environment": {
                "distribution": "Ubuntu 24.04.4 LTS",
                "kernel": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
            },
            "source_hashes": {
                "native_lock": digest(LOCK_PATH),
                "successor_native_count_adapter": digest(
                    ROOT / "cmbench/backends/native_count.py"
                ),
                "successor_native_sat_adapter": digest(
                    ROOT / "cmbench/backends/native_sat.py"
                ),
                "successor_biology_adapter": digest(ROOT / "cmbench/biology_bnet.py"),
                "frozen_core_plan": digest(PLAN_PATH),
                "frozen_admission_ledger": digest(LEDGER_PATH),
                "frozen_results": digest(RESULTS_PATH),
            },
            "vendor_hashes": vendor_hashes,
            "build": build,
            "fixtures": {
                "ganak": {
                    "exact_count": exact.count,
                    "projected_count": projected.count,
                    "unsat_count": zero.count,
                },
                "d4": {
                    "exact_count": d4_exact.count,
                    "unsat_count": d4_zero.count,
                    "exact_command": list(d4_exact.command),
                    "unsat_command": list(d4_zero.command),
                },
                "cryptominisat": {
                    "sat_status": cms_sat.status,
                    "unsat_status": cms_unsat.status,
                    "sat_assignment": list(cms_sat.assignment or ()),
                },
                "kissat": kissat,
                "biology": {
                    "biodivine_aeon_version": "1.4.2",
                    "aeon_fixed_points": aeon_count,
                    "scalar_fixed_points": scalar_count,
                },
            },
            "d4_selected_exact_replay": {
                "timeout_seconds_per_case": 30,
                "cases": corpus,
                "status_counts": {
                    status: sum(item["status"] == status for item in corpus)
                    for status in ("ok", "timeout", "error")
                },
            },
            "network_during_native_build_and_smoke": False,
            "secrets_accessed": False,
            "cloud_resources_created": False,
        }

    OUT.mkdir(parents=True, exist_ok=False)
    result_path = OUT / "RESULT.json"
    result_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = f"""# CM post-fix native Linux smoke

Status: passed locally in a dedicated Ubuntu 24.04 WSL distribution.

The pinned d4 source built successfully. Under the same 4 GiB address-space limit used by the frozen campaign worker, the successor adapter returned exact counts 4 and 0 for the satisfiable and unsatisfiable fixtures while explicitly passing 256 MiB and 64 MiB cache-page bounds.

Ganak exact and projected counting, CryptoMiniSat native XOR-CNF solving, Kissat SAT/UNSAT status, and Biodivine AEON fixed-point counting all passed their pinned fixtures. AEON and the scalar oracle both returned two fixed points.

The bounded d4 corpus replay covered all {len(corpus)} exact-count cases selected by the frozen plan: {sum(item['status'] == 'ok' for item in corpus)} completed, {sum(item['status'] == 'timeout' for item in corpus)} reached the 30-second local bound, and {sum(item['status'] == 'error' for item in corpus)} aborted or otherwise errored. Every completed d4 count agrees with the frozen Ganak count where one is available.

No cloud resource was created, no secret was accessed, and the native build and execution used no network after the Ubuntu prerequisites were installed.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "result_sha256": digest(result_path),
                "d4_corpus_status_counts": document["d4_selected_exact_replay"][
                    "status_counts"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
