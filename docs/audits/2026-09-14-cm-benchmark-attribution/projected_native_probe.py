"""Probe the existing pinned Ganak protocol on tiny synthetic controls only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from cmbench.backends.exact_controls_v2 import run_projected_ganak_v2
PIN = "c43a7d7c6d1e2ba438ee72541ceb15bc81b414bff5aa22038a9f6baa9f82bb61"


def main():
    binary = Path("/usr/local/bin/ganak")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != PIN:
        raise ValueError("Ganak binary identity mismatch")
    cases = [
        ("plain_exact_free_axes", "p cnf 3 1\n1 0\n", 4),
        ("invalid_independent_support_hint", "c ind 1 0\np cnf 3 1\n1 0\n", None),
        ("visible_hidden_multiplicity", "c p show 1 0\np cnf 3 1\n2 3 0\n", 2),
        ("projection_vs_support", "c ind 2 3 0\nc p show 1 0\np cnf 3 1\n2 3 0\n", None),
        ("empty_projection_sat", "c p show 0\np cnf 1 1\n1 0\n", 1),
        ("empty_projection_unsat", "c p show 0\np cnf 1 2\n1 0\n-1 0\n", 0),
    ]
    rows = []
    with TemporaryDirectory(prefix="cm-projection-probe-") as temp:
        for name, text, expected in cases:
            path = Path(temp) / (name + ".cnf")
            path.write_text(text)
            command = [str(binary), "--verb", "0", "--prob", "0", "--appmct", "-1", "--threads", "1", str(path)]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=5)
            rows.append({"case": name, "input": text, "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
                         "expected_projected_or_exact_count": expected, "returncode": proc.returncode,
                         "stdout": proc.stdout, "stderr": proc.stderr,
                         "interpretation": "adversarial ambiguity probe; no valid support promise" if expected is None else "clear unweighted semantic control"})
            if "c p show" in text:
                result = run_projected_ganak_v2(path, executable=binary, timeout_seconds=5)
                rows[-1]["successor_wrapper_count"] = result.count
                if expected is not None and result.count != expected:
                    raise ValueError("projected wrapper count mismatch")
    (HERE / "PROJECTED_NATIVE_PROBE.json").write_text(json.dumps({"schema": "cm-projected-native-probe/v1", "binary_sha256": PIN,
        "scope": "synthetic correctness/protocol evidence, not performance or CM attribution", "cases": rows}, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
