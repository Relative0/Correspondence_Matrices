"""Independent verifier for the C20 compiled-policy VTR tail study."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_compiled_policy_tail_experiment import (
    C20Config,
    METHODS,
    _functional,
    summarize,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy

DATASET = ROOT / "docs/recognition/c18_independent_cone_dataset.json"
POLICY = ROOT / "docs/recognition/runs/c19-logikbench-cheap-work-policy-windows-20260831-001/policy.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the C20 compiled-policy VTR tail run")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest, spec, result = load(run / "manifest.json"), load(run / "run_spec.json"), load(run / "results.json")
    if sha256(DATASET) != spec["dataset_sha256"] or sha256(POLICY) != spec["policy_file_sha256"]:
        raise ValueError("C20 frozen dataset or policy fingerprint mismatch")
    for name, digest in manifest["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"C20 source fingerprint mismatch: {name}")
    for name, digest in manifest["artifacts"].items():
        if sha256(run / name) != digest:
            raise ValueError(f"C20 artifact fingerprint mismatch: {name}")
    corpus = load(ROOT / "docs/recognition/c18_independent_corpus_verification.json")
    if corpus.get("status") != "verified" or corpus.get("cases_replayed") != 73 or corpus.get("c16_truth_overlaps") != 0:
        raise ValueError("C20 prerequisite C18 source replay is incomplete")

    dataset, policy = load(DATASET), load_policy(POLICY)
    compiled = compile_work_policy(policy)
    if (
        policy["policy_sha256"] != spec["policy_sha256"]
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != SCREENED
        or compiled.requires_features
    ):
        raise ValueError("C20 frozen compiled-policy contract mismatch")
    cases = {case["case_id"]: case for case in dataset["cases"] if case["n_vars"] <= 4}
    if len(cases) != 11 or {case["n_vars"] for case in cases.values()} != {3, 4}:
        raise ValueError("C20 VTR tail membership changed")
    config = C20Config(**spec["config"])
    config.validate()
    functional, expected = _functional(list(cases.values()), config)
    if functional != load(run / "functional.json") or not functional["all_exact"]:
        raise ValueError("C20 functional replay mismatch")

    rows = [json.loads(line) for line in (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(cases) * len(METHODS) * config.rounds:
        raise ValueError("C20 measurement count mismatch")
    identities = set()
    for row in rows:
        identity = (row.get("case_id"), row.get("method"), row.get("round"))
        if identity in identities or row.get("method") not in METHODS:
            raise ValueError("C20 duplicate or unknown measurement")
        identities.add(identity)
        case = cases.get(row["case_id"])
        best = expected.get(row["case_id"])
        expected_arm = EXHAUSTIVE if row["method"] == "direct_exhaustive" else SCREENED
        if (
            case is None
            or row.get("source_file") != case["source_file"]
            or row.get("n_vars") != case["n_vars"]
            or row.get("selected_arm") != expected_arm
            or row.get("best_artifact_sha256") != (best["payload_sha256"] if best else None)
            or row.get("semantic_mismatches") != 0
            or row.get("artifact_mismatches") != 0
            or any(type(row.get(field)) is not int or row[field] < 1
                   for field in ("analysis_ns", "exact_check_ns", "total_ns"))
            or type(row.get("decision_ns")) is not int
            or row["decision_ns"] < 0
            or row["total_ns"] != row["decision_ns"] + row["analysis_ns"] + row["exact_check_ns"]
        ):
            raise ValueError("C20 exactness, selection, metadata, or timing invariant mismatch")
    summary = summarize(rows, functional)
    if summary != result["summary"]:
        raise ValueError("C20 summary recomputation mismatch")
    if (
        result.get("status") != "complete"
        or result.get("measurement_rows") != 396
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["dataset"].get("retrospective") is not True
        or result["dataset"].get("policy_refit") is not False
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or result["runpod"].get("used") is not False
    ):
        raise ValueError("C20 final claim mismatch")
    verification = {
        "schema": "crse-c20-compiled-gf2-policy-vtr-tail-verification/v1",
        "status": "verified",
        "functional_cases_replayed": 11,
        "measurement_rows_checked": len(rows),
        "source_fingerprints_checked": len(manifest["sources"]),
        "artifact_fingerprints_checked": len(manifest["artifacts"]),
        "c18_source_replay_required_and_present": True,
        "compiled_policy_mode": compiled.mode,
        "compiled_policy_requires_features": compiled.requires_features,
        "summary_recomputed": True,
        "semantic_or_artifact_mismatches": 0,
        "timings_rerun": False,
        "retrospective": True,
        "policy_refit": False,
        "production_promotion": False,
    }
    with (run / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
