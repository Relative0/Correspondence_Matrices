"""Verify a complete-task ANF-rank pre-screen development artifact."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_anf_full_screen_experiment import (
    METHODS, expected_artifact, prepare_c16_cases, summarize)
from cmbench.comparative.contracts import canonical_bytes

REQUIRED_SOURCES = {
    "cmbench/recognition/gf2_anf_rank.py",
    "cmbench/recognition/gf2_anf_screened.py",
    "cmbench/recognition/gf2_decomposition.py",
    "cmbench/comparative/gf2_anf_full_screen_experiment.py",
    "scripts/cm_comparative_anf_full_screen_development.py",
    "scripts/crse_anf_full_screen_development_verify.py",
    "docs/recognition/c16_linux_confirmation/c16_dataset.json",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def bound(relative: str) -> Path:
    path = ROOT.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("ANF full-screen verifier path")
    return path

def verify(run: Path) -> dict:
    run = run.resolve()
    if not run.is_relative_to(ROOT.resolve()) or not run.is_dir():
        raise ValueError("ANF full-screen run path")
    destination = run / "independent_verification.json"
    if destination.exists():
        raise FileExistsError(destination)
    if {path.name for path in run.iterdir() if path.is_file()} != {
        "protocol.md", "results.json", "raw_measurements.jsonl",
        "environment.json", "manifest.json", "report.md"}:
        raise ValueError("ANF full-screen layout")
    results, manifest = load(run / "results.json"), load(run / "manifest.json")
    if results.get("schema") != "crse-anf-rank-full-screen-development/v1" \
            or results.get("status") != "complete":
        raise ValueError("ANF full-screen schema")
    sources = manifest.get("local_sources", {})
    if not REQUIRED_SOURCES.issubset(sources):
        raise ValueError("ANF full-screen manifest closure")
    for relative, expected in sources.items():
        if sha256(bound(relative)) != expected:
            raise ValueError(f"ANF full-screen source changed: {relative}")
    for record in manifest.get("native_modules", {}).values():
        if sha256(Path(record["path"])) != record["sha256"]:
            raise ValueError("ANF full-screen native module")
    interpreter = manifest["interpreter"]
    if sha256(Path(interpreter["path"])) != interpreter["sha256"]:
        raise ValueError("ANF full-screen interpreter")
    for relative, expected in manifest["artifacts"].items():
        if sha256(run / relative) != expected:
            raise ValueError("ANF full-screen artifact")
    dataset_path = bound(results["dataset"]["path"])
    if sha256(dataset_path) != results["dataset"]["sha256"]:
        raise ValueError("ANF full-screen dataset")
    cases = prepare_c16_cases(load(dataset_path))
    expected = {case["case_id"]: expected_artifact(case)[0] for case in cases}
    rows = [json.loads(line) for line in (run / "raw_measurements.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    performance = [row for row in rows if row.get("role") == "performance"]
    memory = [row for row in rows if row.get("role") == "memory_profile"]
    expected_memory_sessions = len({case["n_vars"] for case in cases}) * len(METHODS)
    mismatches = {"measurement": 0, "output": 0, "stage": 0,
                  "schedule": 0, "summary": 0}
    if len(performance) != len(cases) * 3 * len(METHODS) \
            or len(memory) != expected_memory_sessions:
        mismatches["measurement"] += 1
    if set(Counter((row.get("case_id"), row.get("method"))
                   for row in performance).values()) != {3}:
        mismatches["measurement"] += 1
    for row in rows:
        if row.get("schema") != "crse-anf-rank-full-screen-raw-session/v1" \
                or row.get("method") not in METHODS or row.get("case_id") not in expected \
                or row.get("exact_check_passed") is not True:
            mismatches["measurement"] += 1
            continue
        if row["artifact_sha256"] != expected[row["case_id"]]:
            mismatches["output"] += 1
        timing = row["timings_ns"]
        if timing["accounted_total_ns"] != timing["compute_ns"] + timing["delivery_ns"]:
            mismatches["stage"] += 1
        order = row["method_order"]
        if set(order) != set(METHODS) or row["method_position"] != order.index(row["method"]):
            mismatches["schedule"] += 1
        if row["role"] == "performance":
            core = {key: row[key] for key in (
                "block", "cell_position", "case_id", "family", "n_vars", "method_order")}
            if row["order_sha256"] != hashlib.sha256(canonical_bytes(core)).hexdigest():
                mismatches["schedule"] += 1
    if summarize(rows, results["config"]["development_speedup_gate"]) != results["summary"]:
        mismatches["summary"] += 1
    if any(mismatches.values()):
        raise ValueError(f"ANF full-screen mismatches: {mismatches}")
    verification = {
        "schema": "crse-anf-rank-full-screen-independent-verification/v1",
        "status": "verified", "run_id": results["run_id"],
        "results_sha256": sha256(run / "results.json"),
        "manifest_sha256": sha256(run / "manifest.json"),
        "checked_performance_sessions": len(performance),
        "checked_memory_profile_sessions": len(memory),
        "checked_local_sources": len(sources), "mismatches": mismatches,
        "production_promotion": False,
    }
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return verification

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
