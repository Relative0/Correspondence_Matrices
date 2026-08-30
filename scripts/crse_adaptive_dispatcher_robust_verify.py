"""Independent artifact and semantic replay for robust adaptive run 002."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.adaptive_dispatcher_experiment import (
    _adaptive_solve, _fixed_solve, summarize,
)
from cmbench.recognition.adaptive_dispatcher_robust_experiment import (
    SPLITS, freeze_robust_policy, measured_criteria, source_fingerprints,
)
from cmbench.recognition.source_anf_hybrid import ProductCache
from cmbench.recognition.staged_dispatcher_experiment import _staged_solve
from cmbench.recognition.yosys_composed_holdout2_data import make_yosys_composed_holdout2

RUN = ROOT / "docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002"
OUTPUT = ROOT / "docs/recognition/verification/adaptive-exact-dispatcher-robust-20260830-002.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest, summary = load(RUN / "manifest.json"), load(RUN / "summary.json")
    if manifest.get("schema") != "crse-adaptive-robust-artifacts/v1":
        raise SystemExit("wrong robust artifact schema")
    for name, digest in manifest["files_sha256"].items():
        if sha(RUN / name) != digest:
            raise SystemExit(f"changed robust artifact: {name}")
    if source_fingerprints() != manifest["source_sha256"]:
        raise SystemExit("robust source seal changed")
    policy, _candidates = freeze_robust_policy(
        ROOT / "docs/recognition/runs/staged-exact-dispatcher-20260830-001")
    if policy != load(RUN / "frozen_robust_dispatcher.json") or sha(RUN / "frozen_robust_dispatcher.json") != summary["frozen_policy_sha256"]:
        raise SystemExit("robust policy did not rederive")
    c12, provenance = make_yosys_composed_holdout2()
    if c12 != load(RUN / "c12_dataset.json") or provenance != load(RUN / "c12_provenance.json"):
        raise SystemExit("C12 did not regenerate")
    if sha(RUN / "c12_dataset.json") != summary["c12_dataset_sha256"]:
        raise SystemExit("C12 dataset hash changed")

    evaluation, benchmark = load(RUN / "evaluation_dataset.json"), load(RUN / "evaluation_benchmark.json")
    by_id = {row["case_id"]: row for row in evaluation}
    if len(by_id) != 188 or len(benchmark) != 940:
        raise SystemExit("unexpected evaluation row cardinality")
    semantic_fields = ("predicted", "accepted", "row_variables",
                       "canonical_partition_match", "semantic_mismatch")
    replays = 0
    for measured in benchmark:
        row, method = by_id[measured["case_id"]], measured["method"]
        if len(measured["total_samples_ns"]) != 15 or measured["total_ns"] < 0 or any(
                type(value) is not int or value < 0 for value in measured["total_samples_ns"]):
            raise SystemExit("invalid retained timing samples")
        cache = ProductCache(1024) if method != "set_source_anf" else None
        if method == "adaptive_one_pass":
            replay = _adaptive_solve(row, cache, policy["product_pair_budget"])
        elif method == "staged_restart":
            staged = _staged_solve(row, cache, policy["product_pair_budget"])
            replay = {key: staged[key] for key in semantic_fields}
        else:
            replay = _fixed_solve(method, row, cache)
        if any(replay[field] != measured[field] for field in semantic_fields):
            raise SystemExit(f"semantic replay mismatch: {method}/{row['case_id']}")
        replays += 1
    method_summary, split_summary = summarize(benchmark, SPLITS)
    if method_summary != summary["method_summary"] or split_summary != summary["split_summary"]:
        raise SystemExit("robust timing summary did not rederive")
    criteria = measured_criteria(benchmark, split_summary, provenance, True)
    if criteria != summary["criteria"]:
        raise SystemExit("robust criteria did not rederive")
    if (criteria != {"exact": True, "leakage_safe_freeze": True,
            "fresh_holdout_disjoint": True, "sealed_no_material_regret": False,
            "development_tail_guard": True, "safety": True,
            "production_promotion": False} or summary.get("source_unchanged") is not True
            or summary.get("semantic_mismatches") != 0):
        raise SystemExit("unexpected robust confirmation conclusion")
    verification = {"schema": "crse-adaptive-robust-independent-verification/v1",
        "status": "pass", "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha(RUN / "manifest.json"), "files_verified": len(manifest["files_sha256"]),
        "source_files_verified": len(manifest["source_sha256"]),
        "evaluation_cases": len(evaluation), "method_case_rows": len(benchmark),
        "timing_samples_checked": sum(len(row["total_samples_ns"]) for row in benchmark),
        "semantic_rows_replayed": replays, "c12_rows_regenerated": len(c12),
        "c12_prior_semantic_overlap": provenance["audit"]["prior_semantic_overlap"],
        "c12_prior_alpha_overlap": provenance["audit"]["prior_alpha_overlap"],
        "criteria": criteria, "semantic_mismatches": 0,
        "production_promotion": False}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(json.dumps(verification, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(verification, sort_keys=True))


if __name__ == "__main__":
    main()
