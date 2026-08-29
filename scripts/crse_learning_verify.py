#!/usr/bin/env python3
"""Read-only artifact audit using the independent existing truth-table evaluator.

Does not retrain, execute model-generated code, or modify an experiment directory.
The optional audit record is exclusively created outside those directories.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from cm_expr_serde import expr_from_json
from cm_exprlib import Not, Var, Xor, eval_expr_tt
from cmbench.recognition.features import structural_digest
from cmbench.recognition.models.mlp import MotifMLP, canonical, read_json


def verify_run(directory: Path, max_seconds=60):
    deadline = time.perf_counter() + max_seconds
    manifest = read_json(directory / "manifest.json")
    if manifest["status"] != "complete":
        raise ValueError("incomplete run cannot be verified as complete")
    for name, digest in manifest["files_sha256"].items():
        allowed = {"summary.json", "corpus.json", "raw.csv", "report.md", "model.json",
                   "router_models.json", "run_spec.json", "router.json", "model_index.json", "training_raw.csv"}
        if (type(name) is not str or Path(name).name != name or "/" in name or "\\" in name
                or (name not in allowed and re.fullmatch(r"model-[0-9]{1,10}\.json", name) is None)):
            raise ValueError("unsafe artifact filename")
        path = directory / name
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("artifact exceeds audit bound")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    for name, digest in manifest["source_sha256"].items():
        if type(name) is not str or not name.endswith(".py"):
            raise ValueError("invalid execution source filename")
        path = (ROOT / name).resolve()
        path.relative_to(ROOT)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"execution source differs: {name}")
    summary = read_json(directory / "summary.json", 16 * 1024 * 1024)
    documents = read_json(directory / "corpus.json", 16 * 1024 * 1024)
    dataset_digest = hashlib.sha256(canonical(documents)).hexdigest()
    expected_digest = summary.get("dataset_sha256", summary.get("corpus_sha256"))
    if dataset_digest != expected_digest:
        raise ValueError("dataset digest mismatch")
    if not 1 <= len(documents) <= 512:
        raise ValueError("audit corpus row bound")
    functions, candidate_hashes = {}, {}
    for doc in documents:
        if time.perf_counter() >= deadline:
            raise TimeoutError("cooperative audit budget exhausted")
        if not 1 <= doc["n_vars"] <= 8 or len(doc["expression"]["nodes"]) > 4096:
            raise ValueError("audit input bound")
        expr = expr_from_json(doc["expression"])
        table = eval_expr_tt(expr, doc["n_vars"])
        bits = sum(int(v) << i for i, v in enumerate(table))
        if structural_digest(expr) != doc["digest"]:
            raise ValueError("expression identity disagreement")
        functions[doc["case_id"]] = (bits, table, doc)
        if "teacher" in doc:
            if bits != int(doc["teacher"]["bits_hex"], 16):
                raise ValueError("teacher disagrees with independent truth-table evaluator")
            terms = [Var(i) for i in range(doc["n_vars"])
                     if int(table[1 << (doc["n_vars"] - 1 - i)]) ^ int(table[0])]
            candidate = terms[0] if terms else Xor(Var(0), Var(0))
            for term in terms[1:]:
                candidate = Xor(candidate, term)
            if table[0]:
                candidate = Not(candidate)
            candidate_table = eval_expr_tt(candidate, doc["n_vars"])
            equivalent = np.array_equal(table, candidate_table)
            if int(equivalent) != doc["label"]:
                raise ValueError("label disagrees with independent affine reconstruction")
            candidate_hashes[doc["case_id"]] = (structural_digest(candidate), equivalent)
    cards = summary.get("model_cards", [])
    if len(cards) > 3 or any(card["file"] not in manifest["files_sha256"] for card in cards):
        raise ValueError("model file not covered by artifact manifest")
    models = {card["seed"]: MotifMLP.load(directory / card["file"]) for card in cards}
    scores = {}
    rows = accepted = rejected_mismatches = checked_queries = 0
    with (directory / "raw.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if time.perf_counter() >= deadline:
                raise TimeoutError("cooperative audit budget exhausted")
            rows += 1
            checked_queries += int(row["queries"])
            if row["status"] != "ok" or int(row["mismatches"]) != 0:
                raise ValueError("failed computation retained in purported complete run")
            if row.get("arm") in ("mlp", "mlp_cold") and row.get("score"):
                key = (int(row["seed"]), row["case_id"])
                if key not in scores:
                    values = np.zeros(512, dtype=np.float32)
                    values[:256] = functions[row["case_id"]][1]
                    values[256:] = 1
                    scores[key] = models[key[0]].score(values)
                if abs(scores[key] - float(row["score"])) > 1e-7:
                    raise ValueError("saved model prediction disagrees with raw row")
            if row.get("accepted") == "True":
                trace = json.loads(row["trace_json"])
                candidate_hash, equivalent = candidate_hashes[row["case_id"]]
                if not equivalent or candidate_hash != trace["candidate_sha256"] or not trace["evidence"]:
                    raise ValueError("accepted replacement failed independent audit")
                accepted += 1
            if row.get("reason") == "semantic_mismatch":
                if candidate_hashes[row["case_id"]][1]:
                    raise ValueError("rejection reason disagrees with independent audit")
                rejected_mismatches += 1
    return {"run": directory.name, "status": "verified", "files_hashed": len(manifest["files_sha256"]),
            "source_files_hashed": len(manifest["source_sha256"]), "dataset_sha256": dataset_digest,
            "independent_truth_functions": len(functions), "raw_measurements": rows,
            "recorded_checked_queries": checked_queries, "accepted_replacements_independently_rechecked": accepted,
            "semantic_rejections_independently_rechecked": rejected_mismatches,
            "unique_saved_model_scores_rechecked": len(scores),
            "limit": "Verifies artifacts, source identity, labels, model predictions and candidate equivalence; does not reproduce historical nanosecond timings or recover unstored raw output vectors."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if len(args.runs) > 3:
        parser.error("audit at most three runs")
    result = {"schema": "crse-learning-independent-audit/v1", "runs": [verify_run(p) for p in args.runs],
              "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
