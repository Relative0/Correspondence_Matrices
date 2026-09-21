"""Run checks against the isolated compiled source, saving commands and logs."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "build/dd-0.6.0"
environment = os.environ.copy()
environment["PYTHONPATH"] = str(SOURCE)


def run(label, command, allowed=(0,)):
    print(label, flush=True)
    start = time.monotonic()
    with (BASE / "results" / f"{label}.log").open("w") as log:
        completed = subprocess.run(command, cwd=BASE, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
    result = {"command": command, "exit_code": completed.returncode,
              "elapsed_seconds": time.monotonic() - start}
    (BASE / "results" / f"{label}.json").write_text(json.dumps(result, indent=2) + "\n")
    if completed.returncode not in allowed:
        print((BASE / "results" / f"{label}.log").read_text()[-12000:])
        raise SystemExit(completed.returncode)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=["tests", "benchmark", "memory", "memory-review"])
args = parser.parse_args()
if args.phase == "tests":
    run("prototype-tests", [sys.executable, "-m", "pytest", "-q", "test_count.py"])
    run("dd-count-support-reorder-tests", [sys.executable, "-m", "pytest", "-q",
        str(SOURCE / "tests/cudd_test.py"), str(SOURCE / "tests/autoref_test.py"),
        str(SOURCE / "tests/bdd_test.py"), "-k", "count or support or reorder"])
elif args.phase == "benchmark":
    run("benchmark-run", [sys.executable, "benchmark.py", "--rounds", "9", "--iterations", "200"])
else:
    deps = BASE / "build/deps"
    # Debian supplies build-ID files. Mirror them by object path so an
    # uninstalled Valgrind can find them via --extra-debuginfo-path.
    debug = BASE / "build/debug-objects"
    libraries = subprocess.check_output(["ldd", sys.executable], text=True)
    for filename in re.findall(r"(/[^\s]+)", libraries):
        library = Path(filename).resolve()
        notes = subprocess.check_output(["readelf", "-n", str(library)], text=True)
        match = re.search(r"Build ID: ([0-9a-f]+)", notes)
        if not match:
            continue
        identity = match[1]
        symbols = deps / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
        if symbols.exists():
            for location in (library, Path(filename)):
                destination = debug / str(location).lstrip("/")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(symbols, destination)
                shutil.copyfile(symbols, destination.with_name(symbols.name))
    environment["VALGRIND_LIB"] = str(deps / "usr/libexec/valgrind")
    environment["PYTHONMALLOC"] = "malloc"
    summaries = []
    for calls in (0, 20000):
        if args.phase == "memory":
            run(f"valgrind-{calls}", [str(deps / "usr/bin/valgrind"),
                "--tool=memcheck", "--leak-check=full", "--show-leak-kinds=definite",
                "--errors-for-leak-kinds=definite", "--error-exitcode=99",
                f"--extra-debuginfo-path={debug}",
                sys.executable, "memory_probe.py", "--calls", str(calls)], allowed=(0, 99))
        log = (BASE / "results" / f"valgrind-{calls}.log").read_text()
        summary = {"measured_calls": 2 * calls, "warmup_calls": 2}
        for kind in ("definitely", "indirectly", "possibly"):
            match = re.search(rf"{kind} lost:\s+([\d,]+) bytes in ([\d,]+) blocks", log)
            if not match:
                raise RuntimeError("Missing Valgrind leak summary")
            summary[kind + "_lost_bytes"] = int(match[1].replace(",", ""))
        summary["error_count"] = int(re.search(r"ERROR SUMMARY: ([\d,]+)", log)[1].replace(",", ""))
        summary["definite_leak_records"] = len(re.findall("are definitely lost in loss record", log))
        summary["apa_allocation_frames"] = len(re.findall(r"by 0x[0-9A-F]+: (?:Cudd_.*Apa|cuddApa|.*BDD_count\b)", log))
        if summary["error_count"] != summary["definite_leak_records"]:
            raise RuntimeError("Valgrind reported errors beyond baseline leak records")
        if summary["apa_allocation_frames"]:
            raise RuntimeError("APA allocation in Valgrind error report")
        summary["combined_lost_bytes"] = sum(summary[kind + "_lost_bytes"]
                                              for kind in ("definitely", "indirectly", "possibly"))
        summaries.append(summary)
    # Conservative pointer scanning can reclassify a baseline allocation from
    # definite to possible. Require no growth in combined lost
    # bytes as well as no growth in definite or indirect losses.
    for kind in ("definitely", "indirectly"):
        if summaries[1][kind + "_lost_bytes"] > summaries[0][kind + "_lost_bytes"]:
            raise RuntimeError(f"Increased {kind} lost bytes after repeated APA calls")
    if summaries[1]["combined_lost_bytes"] > summaries[0]["combined_lost_bytes"]:
        raise RuntimeError("Increased combined lost bytes after repeated APA calls")
    (BASE / "results/memory-summary.json").write_text(json.dumps({
        "status": "passed_differential_check", "runs": summaries,
        "limitation": "The system CPython 3.12 reports interpreter string allocation leaks even at baseline; these are not suppressed. This check requires no growth in combined, definite or indirect lost bytes, no APA allocation frames in the definite-leak reports, and no non-leak errors. It is not a claim that the entire interpreter is Valgrind-clean, and does not inject allocation failures."
    }, indent=2) + "\n")
