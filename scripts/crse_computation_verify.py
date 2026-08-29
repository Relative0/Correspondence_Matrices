"""Independent artifact and exact-output verifier for CRSE Milestone D."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.computation_experiment import (
    EVALUATION_ARMS, EXACT_BACKENDS, RUN_SCHEMA, ComputationCase, ComputationTask,
    TaskCostPolicy, exact_motif_candidate, fit_task_policy, load_epfl_d_cases,
    make_workload, output_sha256, reference_task, sha256_file, source_fingerprints,
    task_rule, task_specs,
)
from cmbench.recognition.features import extract_features
from cmbench.recognition.motif_data import case_from_document, validate_documents
from cmbench.recognition.teacher import teach


def read_json(path: Path, limit: int = 32 * 1024 * 1024):
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError(f"bounded JSON limit exceeded: {path}")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key in {path}: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_jsonl(path: Path, limit: int):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
        if len(rows) > limit:
            raise ValueError(f"row cap exceeded: {path}")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-task-computation-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("Milestone D artifact manifest is not complete")
    actual_files = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual_files:
        raise SystemExit("artifact inventory differs from manifest")
    for name, digest in manifest["files_sha256"].items():
        if sha256_file(run / name) != digest:
            raise SystemExit(f"artifact hash mismatch: {name}")
    if summary.get("schema") != RUN_SCHEMA or summary.get("status") != "complete":
        raise SystemExit("summary is not a complete Milestone D experiment")
    current_sources = source_fingerprints()
    if (spec.get("source_sha256") != current_sources or summary.get("source_sha256") != current_sources
            or manifest.get("source_sha256") != current_sources):
        raise SystemExit("retained run source fingerprints differ from the verifier checkout")
    limits = spec.get("resource_limits", {})
    if (spec.get("schema") != "crse-task-computation-run-spec/v1" or spec.get("status") != "planned"
            or limits.get("variables") != 8 or limits.get("cpu_threads") != 1
            or limits.get("cooperative_wall_seconds") != spec.get("config", {}).get("max_seconds")
            or not 0 < limits.get("cooperative_wall_seconds", 0) <= 120
            or limits.get("network") is not False):
        raise SystemExit("finite pre-run specification missing or altered")

    documents = read_json(run / "generated_corpus.json")
    validate_documents(documents)
    cases = {}
    for document in documents:
        base = case_from_document(document)
        cases[base.case_id] = ComputationCase(base.case_id, base.split, base.family,
                                               document["source_id"], base.expr, document["expression"])
    epfl_cases, expected_epfl = load_epfl_d_cases(spec["config"]["epfl_limit"])
    recorded_epfl = read_json(run / "epfl_evaluation_manifest.json")
    if recorded_epfl != expected_epfl:
        raise SystemExit("EPFL D selection or provenance changed")
    cases.update((case.case_id, case) for case in epfl_cases)

    policy = TaskCostPolicy.load(run / "task_router.json")
    training = read_jsonl(run / "training_raw.jsonl", 10_000)
    evaluation = read_jsonl(run / "evaluation_raw.jsonl", 20_000)
    config = spec["config"]
    tasks = task_specs(config["fixed_variables"])
    tasks_by_id = {task.task_id: task for task in tasks}
    train_ids = {document["case_id"] for document in documents if document["split"] == "train"}
    evaluation_ids = set(cases) - train_ids
    expected_training = len(train_ids) * len(tasks) * len(EXACT_BACKENDS) * config["rounds"]
    expected_evaluation = len(evaluation_ids) * len(tasks) * len(EVALUATION_ARMS) * config["rounds"]
    if len(training) != expected_training or len(evaluation) != expected_evaluation:
        raise SystemExit("raw row count mismatch")
    rebuilt_policy = fit_task_policy(training)
    if rebuilt_policy.to_dict() != policy.to_dict():
        raise SystemExit("task router does not reproduce from retained training costs")

    reference_digests = {}
    counts = Counter()
    rewrite_expectations = {}
    for row in training + evaluation:
        case = cases.get(row.get("case_id"))
        task = tasks_by_id.get(row.get("task_id"))
        if case is None or task is None:
            raise SystemExit("row references unknown case or task")
        key = (case.case_id, task.task_id)
        if key not in reference_digests:
            workload = make_workload(case.case_id, task)
            reference_digests[key] = output_sha256(reference_task(case.expr, task, workload))
        expected_digest = reference_digests[key]
        if (row.get("status") != "ok" or row.get("mismatches") != 0
                or row.get("expected_sha256") != expected_digest or row.get("output_sha256") != expected_digest
                or row.get("selected_backend") not in EXACT_BACKENDS):
            raise SystemExit(f"exact task result mismatch: {case.case_id}/{task.task_id}/{row.get('arm')}")
        is_training = row in training
        expected_ids = train_ids if is_training else evaluation_ids
        expected_arms = EXACT_BACKENDS if is_training else EVALUATION_ARMS
        if case.case_id not in expected_ids or row["arm"] not in expected_arms:
            raise SystemExit("training/evaluation boundary mismatch")
        counts[("training" if is_training else "evaluation", case.case_id, task.task_id, row["arm"])] += 1
        if row["arm"] == "task_rule" and row["selected_backend"] != task_rule(task):
            raise SystemExit("deterministic task rule changed")
        if row["arm"] == "learned_router":
            selected, reason = policy.select(task)
            if row["selected_backend"] != selected or row["selection_reason"] != reason or row["model_calls"] != 1:
                raise SystemExit("learned router row disagrees with frozen model")
        if row["arm"] == "answer_cache":
            expected_hits = task.queries - 1 if task.kind == "repeated_vector" else 0
            if row["cache_hits"] != expected_hits:
                raise SystemExit("answer-cache accounting mismatch")
        if row["arm"] == "rewrite_once":
            if case.case_id not in rewrite_expectations:
                candidate, kind = exact_motif_candidate(teach(case.expr, 8))
                accepted = False
                if candidate is not None:
                    accepted = (teach(candidate, 8).bits == teach(case.expr, 8).bits
                                and extract_features(candidate, 8).structural_nodes
                                    < extract_features(case.expr, 8).structural_nodes)
                rewrite_expectations[case.case_id] = (kind, candidate is not None, accepted)
            kind, proposed, accepted = rewrite_expectations[case.case_id]
            if (row["proposal_kind"] != kind or row["proposed"] != proposed
                    or row["accepted"] != accepted):
                raise SystemExit("rewrite decision does not reproduce exactly")
    if any(value != config["rounds"] for value in counts.values()):
        raise SystemExit("incomplete repeated timing cell")

    bypass = read_json(run / "learned_bypass_audit.json")
    if (bypass != summary["learned_bypass"] or bypass["workloads"] != len(evaluation_ids) * len(tasks)
            or bypass["model_calls"] != 0 or bypass["output_mismatches"] != 0):
        raise SystemExit("learned bypass audit mismatch")
    if (summary["row_counts"] != {"training": len(training), "evaluation": len(evaluation)}
            or summary["semantic_mismatches"] != 0 or summary["failed_rows"] != 0
            or not summary["source_unchanged"] or not summary["criteria"]["safety_met"]):
        raise SystemExit("summary/raw consistency mismatch")
    result = {"schema": "crse-task-computation-independent-verification/v1", "status": "pass",
        "run": str(run), "manifest_sha256": sha256_file(run / "manifest.json"),
        "generated_cases_recomputed": len(documents), "epfl_cases_recomputed": len(epfl_cases),
        "task_workloads_recomputed": len(reference_digests), "training_rows_checked": len(training),
        "evaluation_rows_checked": len(evaluation), "semantic_mismatches": 0,
        "policy_cells": len(policy.cells), "rewrite_cases_recomputed": len(rewrite_expectations),
        "bypass_mismatches": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
