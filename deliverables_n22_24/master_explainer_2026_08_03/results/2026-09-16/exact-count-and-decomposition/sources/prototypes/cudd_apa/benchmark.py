"""Count-only timings: build once, retain roots, rotate method order per round."""
import argparse
import datetime
import gc
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

from dd import cudd

ROOT = Path(__file__).resolve().parents[2]
from reference import exact_cudd_count


def cases():
    manager = cudd.BDD()
    manager.configure(reordering=False)
    manager.declare(*(f"x{i}" for i in range(128)))
    yield "true_128", manager, manager.true, 128, 1 << 128
    yield "false_128", manager, manager.false, 128, 0
    yield "sparse_support_128", manager, manager.add_expr("x3 & ~x97"), 128, 1 << 126
    root = manager.false
    for i in range(64):
        root |= manager.var(f"x{i}")
    yield "or_64_padded_128", manager, root, 128, ((1 << 64) - 1) << 64
    root = manager.false
    for i in range(128):
        root = manager.apply("xor", root, manager.var(f"x{i}"))
    yield "parity_128", manager, root, 128, 1 << 127
    # Compact dynamic program for at least 24 of the first 48 variables.
    counts = [manager.true] + [manager.false] * 24
    for i in range(48):
        variable = manager.var(f"x{i}")
        counts = [manager.true] + [manager.ite(variable, counts[k-1], counts[k])
                                  for k in range(1, 25)]
    expected = sum(math.comb(48, k) for k in range(24, 49)) << 80
    yield "threshold_24_of_48_padded_128", manager, counts[24], 128, expected
    # This width intentionally exercises failure in the original double API.
    yield "literal_padded_1100", manager, manager.var("x97"), 1100, 1 << 1099


def run(rounds=7, iterations=100):
    resident = list(cases())  # all construction is outside all timed regions
    records = []
    for name, manager, root, width, expected in resident:
        native_width = len(manager.vars)
        assert exact_cudd_count(manager, root) << (width - native_width) == expected
        methods = {
            "apa_int": lambda: manager.count(root, width),
            "existing_double": lambda: manager.count_double(root, width),
            "python_exact": lambda: exact_cudd_count(manager, root) << (width - native_width),
        }
        row = {"case": name, "manager_variables": native_width, "nvars": width,
               "support_size": len(manager.support(root)), "dag_nodes": root.dag_size,
               "expected_decimal": str(expected), "methods": {}}
        active = {}
        for method, call in methods.items():
            try:
                value = call()
            except RuntimeError as exc:
                if method != "existing_double":
                    raise
                row["methods"][method] = {"status": "error", "error": str(exc)}
                continue
            exact = value == expected
            if method != "existing_double" and not exact:
                raise AssertionError((name, method, value, expected))
            active[method] = call
            row["methods"][method] = {"status": "ok", "exact": exact,
                                      "result_type": type(value).__name__, "samples_ns": []}
            for _ in range(3):
                call()
        old_gc = gc.isenabled()
        gc.disable()
        try:
            order = list(active)
            random.Random(19).shuffle(order)
            for round_index in range(rounds):
                rotated = order[round_index % len(order):] + order[:round_index % len(order)]
                for method in rotated:
                    call = active[method]
                    start = time.perf_counter_ns()
                    for _ in range(iterations):
                        call()
                    elapsed = time.perf_counter_ns() - start
                    row["methods"][method]["samples_ns"].append(elapsed / iterations)
        finally:
            if old_gc:
                gc.enable()
        for result in row["methods"].values():
            if result["status"] == "ok":
                result["median_ns"] = statistics.median(result["samples_ns"])
                result["min_ns"] = min(result["samples_ns"])
        records.append(row)
    return {
        "schema_version": 1,
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "cpu": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                     if line.startswith("model name")), "unknown"),
        "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
        "dd_version": importlib.metadata.version("dd"), "cudd_version": cudd.__version__,
        "extension": cudd.__file__,
        "extension_sha256": hashlib.sha256(Path(cudd.__file__).read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256((ROOT / "cmbench/comparative/exact_cudd_count.py").read_bytes()).hexdigest(),
        "source_hashes": {str(path.relative_to(Path(__file__).parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (Path(__file__), Path(__file__).with_name("dd-0.6.0-apa.patch"),
                                       Path(__file__).parent / "build/downloads/dd-0.6.0.tar.gz",
                                       Path(__file__).parent / "build/downloads/cudd-3.0.0.tar.gz")},
        "rounds": rounds, "iterations": iterations,
        "contract": "Resident roots; construction excluded; reordering disabled; count-only; no inter-call result cache; support discovery included in native APIs; Python reference counts all manager variables and shifts for wider nvars; methods rotated; Python GC disabled during timing.",
        "cases": records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("results/benchmark.json"))
    args = parser.parse_args()
    if min(args.rounds, args.iterations) < 1:
        parser.error("rounds and iterations must be positive")
    report = run(args.rounds, args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in report["cases"]:
        print(row["case"], {name: round(value["median_ns"]) if value["status"] == "ok" else value["error"]
                            for name, value in row["methods"].items()})
