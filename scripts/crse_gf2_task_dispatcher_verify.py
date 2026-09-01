"""Independent replay and integrity verifier for a local C17 evidence run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2, truth_sha256
from cmbench.recognition.gf2_task_dispatcher import load_gf2_dispatch_policy
from cmbench.recognition.gf2_task_dispatcher_experiment import (
    GF2DispatcherConfig,
    METHODS,
    functional_replay,
    summarize,
)
from cmbench.recognition.portfolio import reference_bits


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify C17 exact GF(2) dispatcher evidence")
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = _load(run / "manifest.json")
    for name, digest in manifest["sources"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"C17 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"C17 artifact fingerprint mismatch: {name}")

    spec = _load(run / "run_spec.json")
    result = _load(run / "results.json")
    dataset_manifest = _load(run / "dataset_manifest.json")
    dataset_path = ROOT / dataset_manifest["source_path"]
    if (hashlib.sha256(dataset_path.read_bytes()).hexdigest() != dataset_manifest["source_sha256"]
            or dataset_manifest["independent_transfer"] is not False):
        raise ValueError("C17 reused dataset manifest mismatch")
    dataset = _load(dataset_path)
    config = GF2DispatcherConfig(**spec["config"])
    config.validate()
    policy = load_gf2_dispatch_policy(run / "policy.json")
    functional, decisions, expected_bits, replay_best = functional_replay(dataset["cases"], policy, config)
    stored_functional = _load(run / "functional.json")
    if stored_functional != {"summary": functional, "decisions": decisions}:
        raise ValueError("C17 functional replay mismatch")

    expected_best = {}
    expected_hashes = {}
    for case in dataset["cases"]:
        bits = reference_bits(expr_from_json(case["expression_v2"]), case["n_vars"])
        if bits != expected_bits[case["case_id"]]:
            raise ValueError("C17 truth-vector replay mismatch")
        analysis = analyze_exact_gf2(bits, case["n_vars"], max_partitions=config.max_partitions)
        expected_best[case["case_id"]] = analysis.best.to_dict() if analysis.best else None
        if expected_best[case["case_id"]] != replay_best[case["case_id"]]:
            raise ValueError("C17 functional/exhaustive best mismatch")
        expected_hashes[case["case_id"]] = truth_sha256(bits, case["n_vars"])

    rows = [json.loads(line) for line in (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    expected_count = len(dataset["cases"]) * config.rounds * len(METHODS)
    if len(rows) != expected_count:
        raise ValueError("C17 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row["case_id"], row["method"], row["round"])
        if identity in identities or row["method"] not in METHODS:
            raise ValueError("C17 duplicate or unknown measured row")
        identities.add(identity)
        best = expected_best[row["case_id"]]
        if (row["source_sha256"] != expected_hashes[row["case_id"]]
                or row["best_artifact_sha256"] != (best["payload_sha256"] if best else None)
                or row["semantic_mismatches"] or row["artifact_mismatches"]
                or any(type(row[field]) is not int or row[field] < 0 for field in
                       ("representation_ns", "policy_ns", "analysis_ns", "exact_check_ns",
                        "shadow_ns", "total_ns"))
                or row["total_ns"] != row["representation_ns"] + row["policy_ns"] + row["analysis_ns"] + row["exact_check_ns"] + row["shadow_ns"]):
            raise ValueError("C17 measured exactness or timing invariant mismatch")
        expected_arm = (
            "explicit_cm_exhaustive" if row["method"] in ("direct_exhaustive", "c17_advice_off")
            or row["method"] == "c17_dispatch" and row["n_vars"] <= 3
            else "explicit_cm_screened"
        )
        if row["selected_arm"] != expected_arm:
            raise ValueError("C17 measured policy-arm mismatch")
    recomputed = summarize(rows, functional)
    if recomputed != result["summary"]:
        raise ValueError("C17 summary recomputation mismatch")
    if (result["status"] != "complete" or result["semantic_or_artifact_mismatches"] != 0
            or result["claims"]["production_promotion"] is not False):
        raise ValueError("C17 result status or claim mismatch")

    verification = {
        "schema": "crse-c17-gf2-task-dispatcher-independent-verification/v1",
        "status": "verified", "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "functional_cases_replayed": len(dataset["cases"]),
        "measurement_rows_checked": len(rows), "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0, "timings_rerun": False,
        "production_promotion": False,
    }
    output = args.output or run / "independent_verification.json"
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
