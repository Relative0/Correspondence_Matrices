"""Independent integrity and exactness verifier for the C18 transfer run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_independent_transfer_experiment import (
    C18TransferConfig, _functional)
from cmbench.recognition.gf2_task_dispatcher import load_gf2_dispatch_policy
from cmbench.recognition.gf2_task_dispatcher_experiment import METHODS, summarize


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify C18 independent GF(2) transfer")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json")
    dataset_path = ROOT / "docs/recognition/c18_independent_cone_dataset.json"
    policy_path = ROOT / spec["policy_path"]
    if (hashlib.sha256(dataset_path.read_bytes()).hexdigest() != manifest["dataset_sha256"]
            or hashlib.sha256(policy_path.read_bytes()).hexdigest() != manifest["policy_file_sha256"]):
        raise ValueError("C18 dataset or frozen policy fingerprint mismatch")
    for name, digest in manifest["sources"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"C18 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"C18 artifact fingerprint mismatch: {name}")
    corpus_verification = load(ROOT / "docs/recognition/c18_independent_corpus_verification.json")
    if (corpus_verification.get("status") != "verified"
            or corpus_verification.get("cases_replayed") != 73
            or corpus_verification.get("c16_truth_overlaps") != 0):
        raise ValueError("C18 source-corpus verification incomplete")
    dataset, policy = load(dataset_path), load_gf2_dispatch_policy(policy_path)
    config = C18TransferConfig(**spec["config"])
    config.validate()
    functional, expected_best, decisions = _functional(dataset["cases"], policy, config)
    if load(run / "functional.json") != {"summary": functional, "decisions": decisions}:
        raise ValueError("C18 functional replay mismatch")
    cases = {case["case_id"]: case for case in dataset["cases"]}
    rows = [json.loads(line) for line in (run / "measurements.jsonl").read_text().splitlines()]
    if len(rows) != len(cases) * len(METHODS) * config.rounds:
        raise ValueError("C18 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row["case_id"], row["method"], row["round"])
        case, best = cases[row["case_id"]], expected_best[row["case_id"]]
        if identity in identities or row["method"] not in METHODS:
            raise ValueError("C18 duplicate or unknown measurement")
        identities.add(identity)
        expected_arm = ("explicit_cm_exhaustive"
                        if row["method"] in ("direct_exhaustive", "c17_advice_off")
                        or row["method"] == "c17_dispatch" and row["n_vars"] <= 3
                        else "explicit_cm_screened")
        summed = sum(row[field] for field in ("representation_ns", "policy_ns", "analysis_ns",
                                              "exact_check_ns", "shadow_ns", "wrapper_ns"))
        if (row["n_vars"] != case["n_vars"] or row["truth_sha256"] != case["truth_sha256"]
                or row["selected_arm"] != expected_arm
                or row["best_artifact_sha256"] != (best["payload_sha256"] if best else None)
                or row["semantic_mismatches"] or row["artifact_mismatches"]
                or row["total_ns"] != summed):
            raise ValueError("C18 measured exactness, arm, or timing invariant mismatch")
    recomputed = summarize(rows, functional)
    if recomputed != result["summary"]:
        raise ValueError("C18 summary recomputation mismatch")
    if (result.get("status") != "complete" or result.get("semantic_or_artifact_mismatches") != 0
            or result["claims"].get("production_promotion") is not False
            or result["dataset"].get("policy_refit") is not False):
        raise ValueError("C18 final claim mismatch")
    verification = {
        "schema": "crse-c18-independent-gf2-dispatch-transfer-verification/v1",
        "status": "verified", "functional_cases_replayed": 73,
        "measurement_rows_checked": len(rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "corpus_source_replay_required_and_present": True,
        "semantic_or_artifact_mismatches": 0, "summary_recomputed": True,
        "timings_rerun": False, "policy_refit": False, "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
