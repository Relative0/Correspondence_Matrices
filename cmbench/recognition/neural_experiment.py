"""Bounded PyTorch matrix/CNN/GNN/fused comparison with exact CM supervision."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.nn import functional as F

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Expr, Or, Var
from cm_ir import expr_structural_hash

from .contracts import Proposal, RequestBudget, Task, check_proposal
from .features import structural_digest
from .graph_inputs import GraphInput, graph_from_document, graph_schema_document
from .models.mlp import canonical
from .models.torch_models import (
    ARCHITECTURES, batch_graphs, build_model, load_model, parameter_count, save_model, state_sha256,
)
from .motif_data import SPLITS, case_from_document, make_motif_documents, validate_documents
from .portfolio import IneligibleExpression, admit, reference_bits
from .teacher import affine_candidate, is_affine, teach


ROOT = Path(__file__).resolve().parents[2]
EPFL_CORPUS = ROOT / "deliverables_n22_24" / "CM_gap_epfl_corpus_2026_08_03.jsonl"
EPFL_PROVENANCE = ROOT / "deliverables_n22_24" / "cm_gap_epfl_provenance_2026_08_03.json"
EPFL_CORPUS_SHA256 = "bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac"
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"
CLASSIFIERS = ("matrix_mlp", "matrix_cnn", "graph_gnn", "fused")
RUN_SCHEMA = "crse-neural-representation-experiment/v1"


class BudgetExhausted(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds: float):
        self.started = time.perf_counter()
        self.deadline = self.started + seconds

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise BudgetExhausted("cooperative experiment wall budget exhausted")


@dataclass(frozen=True)
class NeuralConfig:
    data_seed: int = 20260829
    training_seeds: tuple[int, int] = (173, 271)
    parent_counts: tuple[int, int, int, int] = (64, 16, 16, 8)
    epochs: int = 30
    retrieval_epochs: int = 20
    batch_size: int = 32
    learning_rate: float = 0.003
    retrieval_temperature: float = 0.1
    rounds: int = 3
    epfl_limit: int = 16
    threads: int = 2
    max_seconds: float = 120.0
    estimated_working_memory_bytes: int = 512 * 1024 * 1024

    def validate(self):
        if (type(self.data_seed) is not int or not 0 <= self.data_seed < 2**32
                or type(self.training_seeds) is not tuple or len(self.training_seeds) != 2
                or len(set(self.training_seeds)) != 2
                or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in self.training_seeds)
                or type(self.parent_counts) is not tuple or len(self.parent_counts) != 4
                or any(type(value) is not int for value in self.parent_counts)
                or not 1 <= self.epochs <= 100 or not 1 <= self.retrieval_epochs <= 100
                or not 1 <= self.batch_size <= 128 or not 0 < self.learning_rate <= 0.01
                or not 0 < self.retrieval_temperature <= 1 or not 1 <= self.rounds <= 5
                or not 1 <= self.epfl_limit <= 32 or self.threads != 2
                or not 0 < self.max_seconds <= 120
                or self.estimated_working_memory_bytes > 1024**3):
            raise ValueError("invalid approved neural experiment bounds")

    def manifest(self, output: Path):
        self.validate()
        return {
            "schema": "crse-neural-run-spec/v1", "status": "planned",
            "manual_experiment_number_under_approval": 1,
            "output_directory": str(output.resolve()), "config": asdict(self),
            "device": "cpu", "jit_or_native_compilation": False,
            "architectures": list(CLASSIFIERS) + ["graph_retrieval"],
            "parameter_limit_each": 250_000, "variables": 8,
            "data": {"generated_parent_counts": list(self.parent_counts),
                     "real_source": str(EPFL_CORPUS.relative_to(ROOT)),
                     "real_source_role": "held-out evaluation only"},
            "matched_comparison": {"task": "affine versus one-bit-near classification",
                                   "training_ids": "identical", "optimizer": "Adam",
                                   "epochs": self.epochs, "batch_size": self.batch_size,
                                   "seeds": list(self.training_seeds), "threshold": 0.5},
            "exactness": "CM labels plus independent full truth-vector proposal checks; fallback always retained",
            "materiality_criteria": {
                "representation_signal": "graph balanced accuracy exceeds matrix MLP by >=0.05 on both test and confirmation for both seeds",
                "retrieval_signal": "exact-checked top-1 retrieval >=0.80 on test and confirmation for both seeds",
                "safety": "zero accepted semantic mismatches and zero learned-bypass output mismatches",
                "scope": "smoke criteria only; satisfying them does not promote a runtime policy",
            },
            "resource_limits": {"cooperative_wall_seconds": self.max_seconds, "cpu_threads": self.threads,
                                "estimated_working_memory_bytes": self.estimated_working_memory_bytes,
                                "model_parameters_each": 250_000, "training_seeds": 2},
        }


@dataclass
class Example:
    case_id: str
    split: str
    family: str
    source_id: str
    expr: Expr
    document: dict[str, Any]
    label: int
    bits: int
    parent_id: str


def _write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints() -> dict[str, str]:
    paths = [
        Path(__file__), ROOT / "cmbench" / "recognition" / "graph_inputs.py",
        ROOT / "cmbench" / "recognition" / "models" / "torch_models.py",
        ROOT / "cmbench" / "recognition" / "motif_data.py",
        ROOT / "cmbench" / "recognition" / "teacher.py", EPFL_CORPUS, EPFL_PROVENANCE,
    ]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): _sha(path) for path in paths}


def _to_epfl_axis_order(bits: int, n_vars: int = 8) -> int:
    result = 0
    for epfl_index in range(1 << n_vars):
        crse_index = int(f"{epfl_index:0{n_vars}b}"[::-1], 2)
        result |= ((bits >> crse_index) & 1) << epfl_index
    return result


def _generated_examples(documents: list[dict[str, Any]]) -> list[Example]:
    result = []
    for data in documents:
        case = case_from_document(data)
        cm = teach(case.expr, 8)
        result.append(Example(case.case_id, case.split, case.family, data["source_id"], case.expr,
                              data["expression"], data["label"], cm.bits, data["parent_id"]))
    return result


def load_epfl_examples(limit: int) -> tuple[list[Example], dict[str, Any]]:
    if _sha(EPFL_CORPUS) != EPFL_CORPUS_SHA256:
        raise ValueError("frozen EPFL corpus hash mismatch")
    provenance = json.loads(EPFL_PROVENANCE.read_text(encoding="utf-8"))
    if (provenance.get("clone_commit_sha") != EPFL_COMMIT or provenance.get("license_name") != "MIT License"
            or provenance.get("remote_url") != "https://github.com/lsils/benchmarks.git"):
        raise ValueError("EPFL provenance identity mismatch")
    file_hashes = {Path(item["relpath"]).name: item["sha256"] for item in provenance["aig_files"]}
    lines = EPFL_CORPUS.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines[1:] if line]
    eligible = []
    rejected = Counter()
    for record in records:
        if record.get("status") != "admitted" or record.get("synt_support_size") != 8:
            continue
        try:
            expr = expr_from_json(record["expression_v2"])
            admit(expr, 8, 1)
            cm = teach(expr, 8)
            graph_from_document(record["expression_v2"], 8)
            truth_sha = hashlib.sha256(_to_epfl_axis_order(cm.bits).to_bytes(32, "little")).hexdigest()
            if (truth_sha != record["truth_sha256"] or expr_structural_hash(expr) != record["structural_hash"]
                    or file_hashes.get(record["circuit"]) != record["circuit_sha256"]):
                raise ValueError("record hash disagreement")
        except (ValueError, TypeError, IneligibleExpression, RecursionError):
            rejected["admission_or_identity"] += 1
            continue
        eligible.append((record, expr, cm))
    selected, seen_circuits = [], set()
    for item in eligible:
        circuit = item[0]["circuit"]
        if circuit not in seen_circuits:
            selected.append(item)
            seen_circuits.add(circuit)
        if len(selected) == limit:
            break
    if len(selected) < limit:
        selected_ids = {item[0]["id"] for item in selected}
        selected.extend(item for item in eligible if item[0]["id"] not in selected_ids)
        selected = selected[:limit]
    if not selected:
        raise ValueError("no eligible local EPFL case within neural bounds")
    examples = [Example(record["id"], "epfl", f"epfl_{record['category']}",
                        f"epfl:{record['circuit']}", expr, record["expression_v2"], int(is_affine(cm)),
                        cm.bits, record["id"])
                for record, expr, cm in selected]
    manifest = {
        "corpus_path": str(EPFL_CORPUS.relative_to(ROOT)).replace("\\", "/"),
        "corpus_sha256": EPFL_CORPUS_SHA256, "upstream_commit": EPFL_COMMIT,
        "upstream_url": provenance["remote_url"], "license": provenance["license_name"],
        "license_sha256": provenance["license_sha256"], "training_use": False,
        "eligibility": "admitted frozen records with syntactic support exactly 8 plus current CRSE admission",
        "eligible_count": len(eligible), "selected_count": len(examples),
        "selected_ids": [example.case_id for example in examples],
        "selected_circuits": [example.source_id.removeprefix("epfl:") for example in examples],
        "selection": "first eligible record per corpus-ordered circuit, then corpus-order fill",
        "rejected": dict(rejected), "labels": dict(Counter(example.label for example in examples)),
    }
    return examples, manifest


def equivalent_variant(example: Example, selector: int) -> Example:
    variable = Var(selector % 8)
    expr = (And(example.expr, Or(example.expr, variable)) if selector % 2 == 0
            else Or(example.expr, And(example.expr, variable)))
    admit(expr, 8, 1)
    cm = teach(expr, 8)
    if cm.bits != example.bits:
        raise ValueError("functional-equivalence augmentation failed exact check")
    document = expr_to_json_dag(expr)
    graph_from_document(document, 8)
    return Example(example.case_id + ":equivalent", example.split, example.family,
                   "generated:exact-absorption-augmentation/v1", expr, document,
                   example.label, cm.bits, example.parent_id)


def _graphs(examples: list[Example]) -> list[GraphInput]:
    return [graph_from_document(example.document, 8) for example in examples]


def _matrices(examples: list[Example]) -> torch.Tensor:
    return torch.from_numpy(np.stack([teach(example.expr, 8).tensor() for example in examples]))


def _forward(model, architecture: str, examples: list[Example]):
    matrix = _matrices(examples) if architecture in ("matrix_mlp", "matrix_cnn", "fused") else None
    graph = batch_graphs(_graphs(examples)) if architecture in ("graph_gnn", "fused", "graph_retrieval") else None
    return model(matrix, graph)


def _batch_schedule(rows: int, config: NeuralConfig, seed: int, epochs: int):
    rng = np.random.default_rng(seed)
    return [[indices[start:start + config.batch_size].tolist() for start in range(0, rows, config.batch_size)]
            for indices in (rng.permutation(rows) for _ in range(epochs))]


def train_classifier(architecture: str, training_examples: list[Example], seed: int,
                     config: NeuralConfig, budget: Budget, schedule):
    torch.manual_seed(seed)
    model = build_model(architecture)
    initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    losses, steps = [], 0
    started = time.perf_counter_ns()
    for epoch_batches in schedule:
        model.train()
        epoch_losses = []
        for indices in epoch_batches:
            budget.check()
            batch = [training_examples[index] for index in indices]
            labels = torch.tensor([example.label for example in batch], dtype=torch.float32)
            logits, _embedding = _forward(model, architecture, batch)
            loss = F.binary_cross_entropy_with_logits(logits, labels)
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite classification loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
            steps += 1
        losses.append(statistics.fmean(epoch_losses))
    fit_ns = time.perf_counter_ns() - started
    model.eval()
    final = state_sha256(model)
    if final == initial:
        raise RuntimeError("classification parameters did not update")
    return model, {"status": "complete", "task": "affine-classification", "seed": seed,
                   "epochs": config.epochs, "batch_size": config.batch_size, "steps": steps,
                   "rows": len(training_examples), "optimizer": "Adam", "learning_rate": config.learning_rate,
                   "loss": "binary-cross-entropy-with-logits", "loss_history": losses,
                   "initial_state_sha256": initial, "final_state_sha256": final,
                   "parameters_updated": True, "fit_ns": fit_ns}


def train_retrieval(training_examples: list[Example], augmented: list[Example], seed: int,
                    config: NeuralConfig, budget: Budget, schedule):
    torch.manual_seed(seed)
    model = build_model("graph_retrieval")
    initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    losses, steps = [], 0
    started = time.perf_counter_ns()
    for epoch_batches in schedule:
        model.train()
        epoch_losses = []
        for indices in epoch_batches:
            budget.check()
            originals = [training_examples[index] for index in indices]
            variants = [augmented[index] for index in indices]
            _, first = _forward(model, "graph_retrieval", originals)
            _, second = _forward(model, "graph_retrieval", variants)
            similarity = first @ second.T / config.retrieval_temperature
            target = torch.arange(len(indices), dtype=torch.int64)
            loss = (F.cross_entropy(similarity, target) + F.cross_entropy(similarity.T, target)) / 2
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite contrastive loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
            steps += 1
        losses.append(statistics.fmean(epoch_losses))
    fit_ns = time.perf_counter_ns() - started
    model.eval()
    final = state_sha256(model)
    if final == initial:
        raise RuntimeError("retrieval parameters did not update")
    return model, {"status": "complete", "task": "contrastive-functional-retrieval", "seed": seed,
                   "epochs": config.retrieval_epochs, "batch_size": config.batch_size, "steps": steps,
                   "rows": len(training_examples), "optimizer": "Adam", "learning_rate": config.learning_rate,
                   "temperature": config.retrieval_temperature, "loss": "symmetric-in-batch-NT-Xent",
                   "positive_pairs": "exact-checked absorption-equivalent graph views",
                   "loss_history": losses, "initial_state_sha256": initial,
                   "final_state_sha256": final, "parameters_updated": True, "fit_ns": fit_ns}


def _classification_row(model, architecture: str, example: Example, seed: int, round_index: int,
                        model_digest: str):
    started = time.perf_counter_ns()
    representation_started = started
    matrix = _matrices([example]) if architecture in ("matrix_mlp", "matrix_cnn", "fused") else None
    graph = batch_graphs(_graphs([example])) if architecture in ("graph_gnn", "fused") else None
    representation_ns = time.perf_counter_ns() - representation_started
    inference_started = time.perf_counter_ns()
    with torch.no_grad():
        logits, _ = model(matrix, graph)
        score = float(torch.sigmoid(logits)[0])
    inference_ns = time.perf_counter_ns() - inference_started
    proposal_started = time.perf_counter_ns()
    proposed = score >= 0.5
    accepted = False
    reason = "abstain_exact_fallback"
    check_ns = 0
    if proposed:
        cm = teach(example.expr, 8)
        proposal = Proposal(structural_digest(example.expr), affine_candidate(cm), "learned",
                            f"{architecture}:{model_digest[:16]}", score)
        check = check_proposal(example.expr, proposal, Task(8, 1, 2.0, True),
                               RequestBudget(Task(8, 1, 2.0, True)))
        accepted, reason, check_ns = check.accepted, check.reason, check.check_ns
    chosen = affine_candidate(teach(example.expr, 8)) if accepted else example.expr
    final_bits = reference_bits(chosen, 8)
    fallback_and_audit_ns = time.perf_counter_ns() - proposal_started
    return {"case_id": example.case_id, "split": example.split, "family": example.family,
            "source_id": example.source_id, "parent_id": example.parent_id,
            "architecture": architecture, "seed": seed, "round": round_index,
            "label": example.label, "score": score, "predicted": int(proposed),
            "proposed": proposed, "accepted": accepted, "check_reason": reason,
            "representation_ns": representation_ns, "inference_ns": inference_ns,
            "check_ns": check_ns, "fallback_and_audit_ns": fallback_and_audit_ns,
            "total_ns": time.perf_counter_ns() - started,
            "input_charged": "CM construction" if architecture.startswith("matrix") else
                             "CM construction plus graph encoding" if architecture == "fused" else "DAG graph encoding",
            "original_bits_sha256": hashlib.sha256(example.bits.to_bytes(32, "little")).hexdigest(),
            "final_bits_sha256": hashlib.sha256(final_bits.to_bytes(32, "little")).hexdigest(),
            "semantic_mismatch": final_bits != example.bits, "model_sha256": model_digest}


def evaluate_retrieval(model, seed: int, examples: list[Example], variants: list[Example], split: str,
                       model_digest: str):
    started = time.perf_counter_ns()
    with torch.no_grad():
        _, gallery = _forward(model, "graph_retrieval", examples)
        _, queries = _forward(model, "graph_retrieval", variants)
        similarities = queries @ gallery.T
    inference_ns = time.perf_counter_ns() - started
    rows = []
    for index, example in enumerate(examples):
        order = torch.argsort(similarities[index], descending=True).tolist()
        top = order[0]
        query_bits = reference_bits(variants[index].expr, 8)
        candidate_bits = reference_bits(examples[top].expr, 8)
        exact = candidate_bits == query_bits
        exact_rank = next((rank + 1 for rank, candidate in enumerate(order)
                           if reference_bits(examples[candidate].expr, 8) == query_bits), None)
        final_bits = candidate_bits if exact else query_bits
        rows.append({"case_id": example.case_id, "split": split, "seed": seed,
                     "query_id": variants[index].case_id, "retrieved_id": examples[top].case_id,
                     "top1_same_case": top == index, "top1_exact_function": exact,
                     "exact_match_rank": exact_rank, "accepted": exact,
                     "fallback_used": not exact, "semantic_mismatch": final_bits != query_bits,
                     "score": float(similarities[index, top]), "batch_inference_ns": inference_ns,
                     "gallery_size": len(examples), "model_sha256": model_digest,
                     "checker": "independent complete truth-vector equality"})
    return rows


def classification_summary(rows: list[dict[str, Any]]):
    groups = defaultdict(list)
    for row in rows:
        if row["round"] == 0:
            groups[(row["architecture"], row["seed"], row["split"])].append(row)
    result = {}
    for key, values in sorted(groups.items()):
        tp = sum(row["predicted"] == 1 and row["label"] == 1 for row in values)
        tn = sum(row["predicted"] == 0 and row["label"] == 0 for row in values)
        positives = sum(row["label"] == 1 for row in values)
        negatives = len(values) - positives
        recalls = [tp / positives if positives else None, tn / negatives if negatives else None]
        balanced = statistics.fmean(value for value in recalls if value is not None)
        medians = [statistics.median(r["total_ns"] for r in rows
                                     if r["architecture"] == key[0] and r["seed"] == key[1]
                                     and r["split"] == key[2] and r["case_id"] == value["case_id"])
                   for value in values]
        result["/".join(map(str, key))] = {
            "cases": len(values), "positives": positives, "negatives": negatives,
            "accuracy": (tp + tn) / len(values), "balanced_accuracy": balanced,
            "true_positive": tp, "true_negative": tn,
            "brier_score": statistics.fmean((row["score"] - row["label"]) ** 2 for row in values),
            "proposal_coverage": statistics.fmean(row["proposed"] for row in values),
            "accepted_coverage": statistics.fmean(row["accepted"] for row in values),
            "rejections": sum(row["proposed"] and not row["accepted"] for row in values),
            "accepted_false_positives": sum(row["accepted"] and row["label"] == 0 for row in values),
            "median_case_total_ns": statistics.median(medians),
            "calibration": "descriptive Brier score; no fitted calibration",
        }
    return result


def retrieval_summary(rows: list[dict[str, Any]]):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["seed"], row["split"])].append(row)
    return {f"{seed}/{split}": {"queries": len(values),
                                "top1_same_case": statistics.fmean(row["top1_same_case"] for row in values),
                                "top1_exact_function": statistics.fmean(row["top1_exact_function"] for row in values),
                                "top5_exact_function": statistics.fmean((row["exact_match_rank"] or 10**9) <= 5 for row in values),
                                "accepted": sum(row["accepted"] for row in values),
                                "fallbacks": sum(row["fallback_used"] for row in values)}
            for (seed, split), values in sorted(groups.items())}


def _criteria(classification: dict[str, Any], retrieval: dict[str, Any], seeds: tuple[int, int]):
    graph_signal = True
    retrieval_signal = True
    for seed in seeds:
        for split in ("test", "confirmatory"):
            graph = classification.get(f"graph_gnn/{seed}/{split}", {}).get("balanced_accuracy")
            matrix = classification.get(f"matrix_mlp/{seed}/{split}", {}).get("balanced_accuracy")
            graph_signal &= graph is not None and matrix is not None and graph >= matrix + 0.05
            retrieval_signal &= retrieval.get(f"{seed}/{split}", {}).get("top1_exact_function", 0) >= 0.8
    return {"representation_signal_met": bool(graph_signal), "retrieval_signal_met": bool(retrieval_signal),
            "interpretation": "predeclared smoke thresholds; not promotion or replication"}


def run_neural_experiment(config: NeuralConfig, output: Path, progress=print):
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    spec = config.manifest(output)
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**spec, "source_sha256": before})
    budget = Budget(config.max_seconds)
    status, error_type = "incomplete", ""
    model_cards: list[dict[str, Any]] = []
    classification_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    generated_documents: list[dict[str, Any]] = []
    epfl_manifest: dict[str, Any] = {}
    leakage: dict[str, Any] = {}
    dataset_sha = ""
    all_evaluation: list[Example] = []
    try:
        torch.set_num_threads(config.threads)
        torch.set_num_interop_threads(config.threads)
        torch.use_deterministic_algorithms(True)
        if torch.cuda.is_available():
            raise RuntimeError("CPU-only experiment refuses CUDA availability")
        progress("Dataset: exact generated labels, split audit, and frozen EPFL eligibility")
        generated_documents = make_motif_documents(config.data_seed, config.parent_counts, budget.check)
        leakage = validate_documents(generated_documents, budget.check)
        generated = _generated_examples(generated_documents)
        epfl, epfl_manifest = load_epfl_examples(config.epfl_limit)
        all_evaluation = generated + epfl
        dataset_identity = {"generated": generated_documents,
                            "epfl_selected_ids": epfl_manifest["selected_ids"],
                            "epfl_corpus_sha256": EPFL_CORPUS_SHA256}
        dataset_sha = hashlib.sha256(canonical(dataset_identity)).hexdigest()
        _write_json(output / "generated_corpus.json", generated_documents)
        _write_json(output / "epfl_evaluation_manifest.json", epfl_manifest)
        training_examples = [example for example in generated if example.split == "train"]
        retrieval_variants = {example.case_id: equivalent_variant(example, index)
                              for index, example in enumerate(all_evaluation)}
        augmentation_manifest = {
            "schema": "crse-exact-equivalence-augmentation/v1",
            "rule": "x AND (x OR v) = x or x OR (x AND v) = x",
            "rows": len(retrieval_variants), "all_exact_checked": True,
            "source_ids": [example.case_id for example in all_evaluation],
        }
        _write_json(output / "augmentation_manifest.json", augmentation_manifest)
        progress("Training: matched matrix MLP, CNN, GNN and fused classifiers")
        trained_classifiers = []
        training_ids_sha = hashlib.sha256(canonical([example.case_id for example in training_examples])).hexdigest()
        for seed in config.training_seeds:
            schedule = _batch_schedule(len(training_examples), config, seed, config.epochs)
            for architecture in CLASSIFIERS:
                budget.check()
                model, training = train_classifier(architecture, training_examples, seed, config, budget, schedule)
                training.update({"dataset_sha256": dataset_sha, "training_ids_sha256": training_ids_sha})
                path = output / f"{architecture}-{seed}.json"
                digest = save_model(model, architecture, training,
                                    {"torch": torch.__version__, "device": "cpu", "dtype": "float32",
                                     "graph_memory_bytes": sum(graph.memory_bytes for graph in _graphs(training_examples))
                                                           if architecture in ("graph_gnn", "fused") else None}, path)
                sample = training_examples[:4]
                with torch.no_grad():
                    expected = _forward(model, architecture, sample)[0]
                load_started = time.perf_counter_ns()
                loaded_name, loaded, loaded_training, metadata, loaded_digest = load_model(path)
                load_ns = time.perf_counter_ns() - load_started
                with torch.no_grad():
                    actual = _forward(loaded, architecture, sample)[0]
                if loaded_name != architecture or loaded_digest != digest or not torch.equal(expected, actual):
                    raise RuntimeError("saved/reloaded classification predictions disagree")
                trained_classifiers.append((architecture, seed, loaded, digest))
                model_cards.append({"architecture": architecture, "seed": seed, "file": path.name,
                                    "parameters": parameter_count(loaded), "architecture_document": ARCHITECTURES[architecture],
                                    "weights_dtype": "float32", "parameter_bytes": parameter_count(loaded) * 4,
                                    "serialized_bytes": path.stat().st_size, "artifact_sha256": digest,
                                    "reload_ns": load_ns, "reload_predictions_identical": True,
                                    "graph_memory_bytes": metadata["graph_memory_bytes"], "training": loaded_training})
        progress("Training: exact-pair contrastive graph retrieval")
        retrieval_models = []
        training_variants = [retrieval_variants[example.case_id] for example in training_examples]
        for seed in config.training_seeds:
            schedule = _batch_schedule(len(training_examples), config, seed, config.retrieval_epochs)
            model, training = train_retrieval(training_examples, training_variants, seed, config, budget, schedule)
            training.update({"dataset_sha256": dataset_sha, "training_ids_sha256": training_ids_sha})
            path = output / f"graph_retrieval-{seed}.json"
            digest = save_model(model, "graph_retrieval", training,
                                {"torch": torch.__version__, "device": "cpu", "dtype": "float32",
                                 "graph_memory_bytes": sum(graph.memory_bytes for graph in _graphs(training_examples + training_variants))}, path)
            sample = training_examples[:4]
            with torch.no_grad():
                expected = _forward(model, "graph_retrieval", sample)[1]
            load_started = time.perf_counter_ns()
            loaded_name, loaded, loaded_training, metadata, loaded_digest = load_model(path)
            load_ns = time.perf_counter_ns() - load_started
            with torch.no_grad():
                actual = _forward(loaded, "graph_retrieval", sample)[1]
            if loaded_name != "graph_retrieval" or loaded_digest != digest or not torch.equal(expected, actual):
                raise RuntimeError("saved/reloaded retrieval embeddings disagree")
            retrieval_models.append((seed, loaded, digest))
            model_cards.append({"architecture": "graph_retrieval", "seed": seed, "file": path.name,
                                "parameters": parameter_count(loaded), "architecture_document": ARCHITECTURES["graph_retrieval"],
                                "weights_dtype": "float32", "parameter_bytes": parameter_count(loaded) * 4,
                                "serialized_bytes": path.stat().st_size, "artifact_sha256": digest,
                                "reload_ns": load_ns, "reload_predictions_identical": True,
                                "graph_memory_bytes": metadata["graph_memory_bytes"], "training": loaded_training})
        progress("Evaluation: held-out structures/supports and real EPFL cones with exact fallback")
        evaluation = [example for example in all_evaluation if example.split != "train"]
        for architecture, seed, model, digest in trained_classifiers:
            for example in evaluation:
                for round_index in range(config.rounds):
                    budget.check()
                    classification_rows.append(_classification_row(model, architecture, example, seed,
                                                                   round_index, digest))
        progress("Evaluation: contrastive functional retrieval with exact candidate checks")
        for seed, model, digest in retrieval_models:
            for split in ("validation", "test", "confirmatory", "epfl"):
                selected = [example for example in all_evaluation if example.split == split]
                variants = [retrieval_variants[example.case_id] for example in selected]
                retrieval_rows.extend(evaluate_retrieval(model, seed, selected, variants, split, digest))
        budget.check()
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = ("interrupted" if isinstance(exc, KeyboardInterrupt) else
                  "budget_exhausted" if isinstance(exc, BudgetExhausted) else "failed")
        error_type = type(exc).__name__
        progress(f"Incomplete neural run retained: {error_type}: {exc}")
    after = source_fingerprints()
    if before != after:
        status = "source_changed_during_run"
    class_summary = classification_summary(classification_rows)
    retrieval_result = retrieval_summary(retrieval_rows)
    bypass_mismatches = sum(reference_bits(example.expr, 8) != example.bits for example in all_evaluation)
    bypass = {"switch": "learned_enabled=false", "cases": len(all_evaluation), "model_calls": 0,
              "output_mismatches": bypass_mismatches,
              "method": "original expression evaluated by independent exact fallback; learned models not invoked"}
    criteria = _criteria(class_summary, retrieval_result, config.training_seeds)
    criteria["safety_met"] = (not any(row["semantic_mismatch"] for row in classification_rows + retrieval_rows)
                              and bypass["output_mismatches"] == 0)
    result = {
        "schema": RUN_SCHEMA, "status": status, "error_type": error_type, "config": asdict(config),
        "dataset_sha256": dataset_sha, "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "torch": torch.__version__, "numpy": np.__version__,
                        "platform": platform.platform(), "device": "cpu", "cuda_available": torch.cuda.is_available(),
                        "threads": torch.get_num_threads(), "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()},
        "graph_schema": graph_schema_document(), "leakage_checks": leakage,
        "epfl_source": epfl_manifest, "model_cards": model_cards,
        "classification": class_summary, "retrieval": retrieval_result,
        "criteria": criteria, "learned_bypass": bypass,
        "row_counts": {"classification": len(classification_rows), "retrieval": len(retrieval_rows)},
        "accepted_semantic_mismatches": sum(row["semantic_mismatch"] for row in classification_rows + retrieval_rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in classification_rows)),
        "wall_seconds": time.perf_counter() - budget.started,
        "scientific_claim": "bounded generated mechanism and one-machine EPFL transfer smoke; no runtime promotion or independent replication",
    }
    _write_jsonl(output / "classification_raw.jsonl", classification_rows)
    _write_jsonl(output / "retrieval_raw.jsonl", retrieval_rows)
    _write_json(output / "learned_bypass_audit.json", bypass)
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-neural-artifacts/v1", "status": status,
        "files_sha256": {path.name: _sha(path) for path in files}, "source_sha256": before})
    return result


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE Milestone C: CM-supervised graph learning", "",
             f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
             f"Exact output mismatches: {result['accepted_semantic_mismatches']}", "",
             "## Representation comparison", "",
             "| Architecture / seed / split | Cases | Balanced accuracy | Brier | Median total ns |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result["classification"].items():
        lines.append(f"| {key} | {values['cases']} | {values['balanced_accuracy']:.3f} | "
                     f"{values['brier_score']:.3f} | {values['median_case_total_ns']:.0f} |")
    lines += ["", "Matrix and fused timing charges exact CM construction from the expression. Graph timing charges DAG encoding.",
              "Learned positive classifications only invoke an affine candidate; independent complete truth-vector equality and node reduction decide acceptance.",
              "Rejected or abstained proposals use the exact original-expression fallback. The learned-bypass switch invokes no model and preserves every result.",
              "", "## Contrastive retrieval", "",
              "| Seed / split | Queries | Top-1 exact | Top-5 exact | Fallbacks |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result["retrieval"].items():
        lines.append(f"| {key} | {values['queries']} | {values['top1_exact_function']:.3f} | "
                     f"{values['top5_exact_function']:.3f} | {values['fallbacks']} |")
    lines += ["", "Positive retrieval pairs are structurally changed absorption variants proved equivalent by exact CM semantics.",
              "A retrieved candidate is accepted only after an independent full truth-vector check; otherwise the query function is retained.",
              "", "## Scope", "",
              "All models were actually trained, serialized as inert hashed float32 JSON tensors, reloaded, and checked for identical predictions.",
              "The four classification representations share task, training IDs, minibatch order, optimizer, epochs, batch size, threshold, and seeds; parameter counts remain in the approved band.",
              "Held-out generated splits change source templates and support. The EPFL slice is provenance-reviewed, eight-variable, evaluation-only local hardware data.",
              "This is one bounded one-machine smoke experiment. It does not establish natural-domain generalization, calibration, speedup, or production readiness.",
              "All 18 research tracks remain in the experiment register; only the measured slices should change status.", ""]
    return "\n".join(lines)
