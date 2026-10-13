"""Bounded correctness smoke for the pinned Linux native tools."""

from __future__ import annotations

import json
import importlib.metadata
from pathlib import Path
import re
import subprocess


ROOT = Path("/opt/cm-smoke")


def run(command: list[str], *, codes: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode not in codes:
        raise RuntimeError(f"unexpected exit {completed.returncode}: {command[0]}")
    if len(completed.stdout.encode()) + len(completed.stderr.encode()) > (1 << 20):
        raise RuntimeError("native diagnostic output exceeded 1 MiB")
    return completed


def ganak_count(name: str) -> tuple[int, str]:
    completed = run([
        "/usr/local/bin/ganak", "--verb", "0", "--prob", "0", "--appmct", "-1",
        "--threads", "1", str(ROOT / "fixtures" / name),
    ])
    match = re.findall(r"^c s exact arb int ([0-9]+)$", completed.stdout, re.MULTILINE)
    status = re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)$", completed.stdout, re.MULTILINE)
    if len(match) != 1 or len(status) != 1:
        raise RuntimeError("Ganak exact-output contract mismatch")
    return int(match[0]), status[0]


def main() -> None:
    ganak_version = run(["/usr/local/bin/ganak", "--version"]).stdout
    if "7f03233c699e2a5bfa1534ca986c83bdc19ec3df" not in ganak_version:
        raise RuntimeError("Ganak source revision mismatch")
    kissat_version = run(["/usr/local/bin/kissat", "--version"]).stdout.strip()
    exact = ganak_count("exact.cnf")
    projected = ganak_count("projected.cnf")
    zero = ganak_count("unsat.cnf")
    if exact != (4, "SATISFIABLE") or projected != (2, "SATISFIABLE") or zero != (0, "UNSATISFIABLE"):
        raise RuntimeError("native exact/projected count mismatch")
    sat = run(["/usr/local/bin/kissat", "--quiet", str(ROOT / "fixtures" / "sat.cnf")], codes={10})
    unsat = run(["/usr/local/bin/kissat", "--quiet", str(ROOT / "fixtures" / "unsat.cnf")], codes={20})
    if "s SATISFIABLE" not in sat.stdout or "s UNSATISFIABLE" not in unsat.stdout:
        raise RuntimeError("Kissat status contract mismatch")
    d4 = run(["/usr/local/bin/d4-counter", "-i", str(ROOT / "fixtures" / "exact.cnf")])
    d4_counts = re.findall(r"^s ([0-9]+)$", d4.stdout, re.MULTILINE)
    if d4_counts != ["4"]:
        raise RuntimeError("d4 exact-count contract mismatch")
    cms_version = run(["/usr/local/bin/cryptominisat5", "--version"]).stdout.strip()
    cms_sat = run([
        "/usr/local/bin/cryptominisat5", "--verb", "0", "--threads", "1",
        str(ROOT / "fixtures" / "xor-sat.cnf"),
    ], codes={10})
    cms_unsat = run([
        "/usr/local/bin/cryptominisat5", "--verb", "0", "--threads", "1",
        str(ROOT / "fixtures" / "xor-unsat.cnf"),
    ], codes={20})
    if "s SATISFIABLE" not in cms_sat.stdout or "s UNSATISFIABLE" not in cms_unsat.stdout:
        raise RuntimeError("CryptoMiniSat XOR status contract mismatch")
    assignment = {abs(int(token)): int(token) > 0 for line in cms_sat.stdout.splitlines()
                  if line.startswith("v ") for token in line[2:].split() if token != "0"}
    if assignment.get(1) is not True or assignment.get(2) is not False:
        raise RuntimeError("CryptoMiniSat XOR witness mismatch")
    if importlib.metadata.version("biodivine-aeon") != "1.4.2":
        raise RuntimeError("Biodivine AEON package version mismatch")
    from biodivine_aeon import AsynchronousGraph, BooleanNetwork, FixedPoints
    network = BooleanNetwork.from_file(str(ROOT / "fixtures" / "aeon.bnet")).infer_valid_graph()
    fixed_points = FixedPoints.symbolic(AsynchronousGraph(network))
    aeon_count = int(fixed_points.vertices().cardinality())
    if aeon_count != 2:
        raise RuntimeError("Biodivine AEON fixed-point count mismatch")
    lock = json.loads((ROOT / "NATIVE_LOCK.json").read_text())
    print(json.dumps({
        "schema": "cm-benchmark-linux-smoke/v2", "status": "passed",
        "base_image": lock["base_image"], "ganak_version": ganak_version.splitlines()[0],
        "kissat_version": kissat_version, "exact_count": exact[0],
        "projected_count": projected[0], "unsat_count": zero[0],
        "kissat_sat_exit": sat.returncode, "kissat_unsat_exit": unsat.returncode,
        "d4_exact_count": int(d4_counts[0]),
        "cryptominisat_version": next(line[2:] for line in cms_version.splitlines()
                                          if line.startswith("c CryptoMiniSat version ")),
        "cryptominisat_xor_sat_exit": cms_sat.returncode,
        "cryptominisat_xor_unsat_exit": cms_unsat.returncode,
        "cryptominisat_xor_witness": {"1": True, "2": False},
        "biodivine_aeon_version": "1.4.2", "biodivine_aeon_fixed_points": aeon_count,
        "probabilistic_mode": False, "approximate_fallback": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
