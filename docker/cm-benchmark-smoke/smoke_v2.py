"""Post-fix Linux smoke for the pinned native benchmark adapters."""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import subprocess
import sys


ROOT = Path(os.environ.get("CM_BENCHMARK_ROOT", "/workspace/cm-benchmark"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURES = ROOT / "docker/cm-benchmark-smoke/fixtures"

from cmbench.backends.native_count import run_d4, run_ganak  # noqa: E402
from cmbench.backends.native_sat import run_cryptominisat  # noqa: E402
from cmbench.biology_bnet import (  # noqa: E402
    aeon_fixed_point_count,
    parse_bnet,
    scalar_fixed_point_count,
)


def kissat(executable: str, fixture: str, code: int, status: str) -> int:
    result = subprocess.run(
        [executable, "--quiet", str(FIXTURES / fixture)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != code or f"s {status}" not in result.stdout:
        raise RuntimeError("Kissat status contract mismatch")
    return result.returncode


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    ganak = os.environ.get("CM_GANAK", "/usr/local/bin/ganak")
    d4 = os.environ.get("CM_D4", "/usr/local/bin/d4-counter")
    cms = os.environ.get("CM_CRYPTOMINISAT", "/usr/local/bin/cryptominisat5")
    kissat_binary = os.environ.get("CM_KISSAT", "/usr/local/bin/kissat")

    exact = run_ganak(FIXTURES / "exact.cnf", mode="exact", executable=ganak)
    projected = run_ganak(
        FIXTURES / "projected.cnf", mode="projected", executable=ganak
    )
    zero = run_ganak(FIXTURES / "unsat.cnf", mode="exact", executable=ganak)
    d4_exact = run_d4(FIXTURES / "exact.cnf", executable=d4)
    d4_zero = run_d4(FIXTURES / "unsat.cnf", executable=d4)
    cms_sat = run_cryptominisat(FIXTURES / "xor-sat.cnf", executable=cms)
    cms_unsat = run_cryptominisat(FIXTURES / "xor-unsat.cnf", executable=cms)
    functions = parse_bnet((FIXTURES / "aeon.bnet").read_text(encoding="utf-8"))
    scalar = scalar_fixed_point_count(functions)
    aeon = aeon_fixed_point_count(FIXTURES / "aeon.bnet")
    values = {
        "ganak_exact": exact.count,
        "ganak_projected": projected.count,
        "ganak_unsat": zero.count,
        "d4_exact": d4_exact.count,
        "d4_unsat": d4_zero.count,
        "d4_command": list(d4_exact.command),
        "cryptominisat_sat": cms_sat.status,
        "cryptominisat_unsat": cms_unsat.status,
        "cryptominisat_assignment": list(cms_sat.assignment or ()),
        "kissat_sat_exit": kissat(kissat_binary, "sat.cnf", 10, "SATISFIABLE"),
        "kissat_unsat_exit": kissat(
            kissat_binary, "unsat.cnf", 20, "UNSATISFIABLE"
        ),
        "scalar_fixed_points": scalar,
        "aeon_fixed_points": aeon,
    }
    expected = {
        "ganak_exact": 4,
        "ganak_projected": 2,
        "ganak_unsat": 0,
        "d4_exact": 4,
        "d4_unsat": 0,
        "cryptominisat_sat": "SATISFIABLE",
        "cryptominisat_unsat": "UNSATISFIABLE",
        "cryptominisat_assignment": [True, False],
        "kissat_sat_exit": 10,
        "kissat_unsat_exit": 20,
        "scalar_fixed_points": 2,
        "aeon_fixed_points": 2,
    }
    if any(values[key] != value for key, value in expected.items()):
        raise RuntimeError("post-fix native smoke mismatch")
    print(
        json.dumps(
            {
                "schema": "cm-benchmark-linux-smoke/v3",
                "status": "passed",
                "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
                **values,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
