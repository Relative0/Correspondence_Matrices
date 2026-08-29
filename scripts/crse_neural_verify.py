"""Independent artifact and exact-output verifier for the CRSE neural run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.models.torch_models import load_model, parameter_count
from cmbench.recognition.motif_data import validate_documents
from cmbench.recognition.teacher import teach


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, limit=32 * 1024 * 1024):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key in {path}: {key}")
            result[key] = value
        return result
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError(f"bounded JSON limit exceeded: {path}")
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_jsonl(path: Path, expected_max: int):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
        if len(rows) > expected_max:
            raise ValueError(f"row cap exceeded: {path}")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-neural-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("run artifact manifest is not complete")
    actual_files = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual_files:
        raise SystemExit("artifact inventory differs from manifest")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-neural-representation-experiment/v1" or summary.get("status") != "complete":
        raise SystemExit("summary is not a complete neural experiment")
    if (spec.get("schema") != "crse-neural-run-spec/v1" or spec.get("status") != "planned"
            or spec.get("resource_limits", {}).get("cooperative_wall_seconds") != 120.0
            or spec.get("resource_limits", {}).get("cpu_threads") != 2):
        raise SystemExit("pre-run finite specification missing or altered")

    documents = read_json(run / "generated_corpus.json")
    validate_documents(documents)
    exact_bits = {}
    for document in documents:
        expr = expr_from_json(document["expression"])
        exact_bits[document["case_id"]] = teach(expr, 8).bits
    epfl_manifest = read_json(run / "epfl_evaluation_manifest.json")
    corpus_path = ROOT / epfl_manifest["corpus_path"]
    if sha(corpus_path) != epfl_manifest["corpus_sha256"]:
        raise SystemExit("EPFL corpus changed")
    epfl_records = {record["id"]: record for record in
                    (json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines()[1:] if line)
                    if record.get("status") == "admitted"}
    for case_id in epfl_manifest["selected_ids"]:
        exact_bits[case_id] = teach(expr_from_json(epfl_records[case_id]["expression_v2"]), 8).bits
    expected_dataset_rows = sum(spec["config"]["parent_counts"]) * 2 + epfl_manifest["selected_count"]
    if len(exact_bits) != expected_dataset_rows:
        raise SystemExit("dataset identity/count mismatch")

    model_cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    expected_models = {(architecture, seed) for architecture in spec["architectures"]
                       for seed in spec["config"]["training_seeds"]}
    if set(model_cards) != expected_models:
        raise SystemExit("trained model inventory mismatch")
    for key, card in model_cards.items():
        name, model, training, _metadata, digest = load_model(run / card["file"])
        if (name != key[0] or training["seed"] != key[1] or digest != card["artifact_sha256"]
                or parameter_count(model) != card["parameters"] or not 50_000 <= card["parameters"] <= 250_000
                or not training["parameters_updated"]):
            raise SystemExit(f"model provenance mismatch: {key}")

    classification = read_jsonl(run / "classification_raw.jsonl", 10_000)
    expected_class_rows = 4 * 2 * (32 + 32 + 16 + epfl_manifest["selected_count"]) * spec["config"]["rounds"]
    if len(classification) != expected_class_rows:
        raise SystemExit("classification raw row count mismatch")
    class_groups = Counter()
    deterministic_scores = {}
    reasons = Counter()
    for row in classification:
        bits = exact_bits[row["case_id"]]
        bit_sha = hashlib.sha256(bits.to_bytes(32, "little")).hexdigest()
        if (row["original_bits_sha256"] != bit_sha or row["final_bits_sha256"] != bit_sha
                or row["semantic_mismatch"] or row["predicted"] != int(row["score"] >= 0.5)
                or row["proposed"] != bool(row["predicted"])
                or row["accepted"] and row["check_reason"] != "exact_instance_equivalence_and_node_reduction"
                or row["accepted"] and row["label"] != 1):
            raise SystemExit(f"classification exactness mismatch: {row['case_id']}")
        key = (row["architecture"], row["seed"], row["split"], row["case_id"])
        if deterministic_scores.setdefault(key, row["score"]) != row["score"]:
            raise SystemExit("nondeterministic repeated score")
        class_groups[(row["architecture"], row["seed"], row["split"], row["round"])] += 1
        reasons[row["check_reason"]] += 1
    for architecture in ("matrix_mlp", "matrix_cnn", "graph_gnn", "fused"):
        for seed in spec["config"]["training_seeds"]:
            for split, count in (("validation", 32), ("test", 32), ("confirmatory", 16),
                                 ("epfl", epfl_manifest["selected_count"])):
                for round_index in range(spec["config"]["rounds"]):
                    if class_groups[(architecture, seed, split, round_index)] != count:
                        raise SystemExit("classification cell incomplete")

    retrieval = read_jsonl(run / "retrieval_raw.jsonl", 2_000)
    expected_retrieval = 2 * (32 + 32 + 16 + epfl_manifest["selected_count"])
    if len(retrieval) != expected_retrieval:
        raise SystemExit("retrieval raw row count mismatch")
    retrieval_groups = Counter()
    for row in retrieval:
        base_query = row["query_id"].removesuffix(":equivalent")
        exact = exact_bits[base_query] == exact_bits[row["retrieved_id"]]
        if (row["top1_exact_function"] != exact or row["accepted"] != exact
                or row["fallback_used"] == exact or row["semantic_mismatch"]
                or row["top1_same_case"] != (base_query == row["retrieved_id"])):
            raise SystemExit(f"retrieval exactness mismatch: {row['query_id']}")
        retrieval_groups[(row["seed"], row["split"])] += 1
    for seed in spec["config"]["training_seeds"]:
        for split, count in (("validation", 32), ("test", 32), ("confirmatory", 16),
                             ("epfl", epfl_manifest["selected_count"])):
            if retrieval_groups[(seed, split)] != count:
                raise SystemExit("retrieval cell incomplete")

    bypass = read_json(run / "learned_bypass_audit.json")
    bypass_mismatches = sum(teach(expr_from_json(document["expression"]), 8).bits
                            != exact_bits[document["case_id"]] for document in documents)
    if (bypass != summary["learned_bypass"] or bypass["cases"] != len(exact_bits)
            or bypass["model_calls"] != 0 or bypass["output_mismatches"] != bypass_mismatches):
        raise SystemExit("learned bypass audit mismatch")
    if (summary["row_counts"] != {"classification": len(classification), "retrieval": len(retrieval)}
            or summary["accepted_semantic_mismatches"] != 0
            or summary["proposal_reasons"] != dict(reasons)
            or not summary["source_unchanged"]):
        raise SystemExit("summary/raw consistency mismatch")

    result = {"schema": "crse-neural-independent-verification/v1", "status": "pass",
              "run": str(run), "manifest_sha256": sha(run / "manifest.json"),
              "models_loaded": len(model_cards), "dataset_functions_recomputed": len(exact_bits),
              "classification_rows_checked": len(classification), "retrieval_rows_checked": len(retrieval),
              "semantic_mismatches": 0, "bypass_mismatches": bypass_mismatches,
              "epfl_cases": epfl_manifest["selected_count"], "epfl_circuits": len(set(epfl_manifest["selected_circuits"])),
              "limits": {"variables": 8, "threads": 2, "wall_seconds": summary["wall_seconds"],
                         "max_parameters": max(card["parameters"] for card in model_cards.values())}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
