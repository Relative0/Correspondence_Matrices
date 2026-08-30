"""Circuit-disjoint natural EPFL dataset for exact XOR decomposition."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_expr_serde import expr_from_json, expr_to_json_dag

from .blif import parse_blif
from .decomposition_data import canonical, packed_sha256
from .features import structural_digest
from .natural_decomposition import (
    analyze_decomposition, compose_partition_witness, interaction_target, semantic_variables,
)
from .portfolio import admit, reference_bits
from .variable_graph_inputs import graph_from_document

ROOT = Path(__file__).resolve().parents[2]
EPFL_ROOT = ROOT / "external" / "epfl-benchmarks"
EPFL_LICENSE = EPFL_ROOT / "LICENSE"
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"
EPFL_URL = "https://github.com/lsils/benchmarks.git"
SPLITS = ("train", "validation", "test", "confirmatory")
SPLIT_CIRCUITS = {
    "train": ("adder", "hyp", "mem_ctrl", "multiplier", "router"),
    "validation": ("div",),
    "test": ("square",),
    "confirmatory": ("sin", "sqrt", "voter"),
}
PER_LABEL_COUNTS = {"train": 48, "validation": 12, "test": 16, "confirmatory": 18}
DATASET_SCHEMA = "crse-natural-epfl-decomposition-dataset/v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rank(seed: int, split: str, row: dict[str, Any]) -> str:
    identity = ":".join((str(seed), split, str(int(row["decomposable"])), row["variant"],
                         row["circuit"], row["root"], row["truth_sha256"]))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _round_robin(rows: list[dict[str, Any]], circuits: tuple[str, ...], seed: int, split: str):
    buckets = {circuit: sorted((row for row in rows if row["circuit"] == circuit),
                               key=lambda row: (_rank(seed, split, row), row["variant"], row["root"]))
               for circuit in circuits}
    offsets = {circuit: 0 for circuit in circuits}
    while any(offsets[circuit] < len(buckets[circuit]) for circuit in circuits):
        for circuit in circuits:
            offset = offsets[circuit]
            if offset < len(buckets[circuit]):
                yield buckets[circuit][offset]
                offsets[circuit] += 1


def make_natural_decomposition_documents(scout_path: Path, *, seed: int = 20260829,
                                         check=lambda: None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("invalid natural dataset seed")
    scout_path = Path(scout_path).resolve()
    scout = json.loads(scout_path.read_text(encoding="utf-8"))
    if (scout.get("schema") != "crse-natural-decomposition-scout/v1" or scout.get("status") != "complete"
            or scout.get("source", {}).get("commit") != EPFL_COMMIT
            or scout.get("source", {}).get("license") != "MIT License"
            or type(scout.get("rows")) is not list or len(scout["rows"]) > 20_000):
        raise ValueError("invalid or changed natural decomposition scout")
    allowed_circuits = {circuit for circuits in SPLIT_CIRCUITS.values() for circuit in circuits}
    if len(allowed_circuits) != sum(len(circuits) for circuits in SPLIT_CIRCUITS.values()):
        raise ValueError("natural circuit split overlap")
    sources: dict[str, Any] = {}
    documents: list[dict[str, Any]] = []
    semantic_seen: set[tuple[int, int]] = set()
    alpha_seen: set[str] = set()
    rejection = Counter()
    for split in SPLITS:
        circuits = SPLIT_CIRCUITS[split]
        candidate_rows = [row for row in scout["rows"] if row.get("circuit") in circuits]
        for label in (1, 0):
            accepted = 0
            for row in _round_robin([row for row in candidate_rows if int(row["decomposable"]) == label],
                                    circuits, seed, split):
                check()
                if accepted == PER_LABEL_COUNTS[split]:
                    break
                try:
                    relative = row["source_path"]
                    path = (ROOT / relative).resolve()
                    if path != EPFL_ROOT and EPFL_ROOT not in path.parents:
                        raise ValueError("natural source escapes pinned EPFL root")
                    if sha(path) != row["source_sha256"]:
                        raise ValueError("natural source hash changed")
                    if relative not in sources:
                        sources[relative] = parse_blif(path)
                    netlist = sources[relative]
                    expr, support = netlist.build_expr(row["root"], max_identity_nodes=4096)
                    bits, packed_support = netlist.packed_value(row["root"])
                    if support != packed_support or list(support) != row["support"] or len(support) != row["n_vars"]:
                        raise ValueError("natural source support disagreement")
                    admit(expr, len(support), 1)
                    reference = reference_bits(expr, len(support))
                    direct = eval_expr_bitset(expr, build_bitset_env(tuple(f"x{i}" for i in range(len(support)))))
                    if reference != bits or direct != bits or packed_sha256(bits, len(support)) != row["truth_sha256"]:
                        raise ValueError("independent natural truth disagreement")
                    if semantic_variables(bits, len(support)) != tuple(range(len(support))):
                        raise ValueError("natural source has inactive declared variables")
                    analysis = analyze_decomposition(bits, len(support))
                    if int(analysis.decomposable) != label:
                        raise ValueError("natural decomposition label changed")
                    if analysis.witness is not None and compose_partition_witness(analysis.witness, len(support)) != bits:
                        raise ValueError("natural factor witness did not recompose")
                    semantic = (len(support), bits)
                    document = expr_to_json_dag(expr)
                    alpha = structural_digest(expr, alpha_rename=True)
                    if semantic in semantic_seen:
                        rejection["semantic_duplicate"] += 1
                        continue
                    if alpha in alpha_seen:
                        rejection["alpha_structural_duplicate"] += 1
                        continue
                    graph_from_document(document, len(support))
                    targets, target_mask = interaction_target(bits, len(support))
                    identity = hashlib.sha256(canonical({"source": relative, "root": row["root"],
                        "truth": row["truth_sha256"]})).hexdigest()[:16]
                    documents.append({"schema": DATASET_SCHEMA,
                        "case_id": f"{split}-{row['variant']}-{row['circuit']}-{identity}",
                        "split": split, "natural": True, "training_use": split == "train",
                        "circuit": row["circuit"], "variant": row["variant"],
                        "source_path": relative, "source_sha256": row["source_sha256"], "root": row["root"],
                        "support_names": list(support), "n_vars": len(support), "label": label,
                        "family": "natural_xor_partition" if label else "natural_indecomposable",
                        "source_nodes": row["source_nodes"], "source_edges": row["source_edges"],
                        "depth": row["depth"], "components": [list(component) for component in analysis.components],
                        "interaction_target": list(targets), "interaction_mask": list(target_mask),
                        "witness": analysis.witness, "semantic_sha256": packed_sha256(bits, len(support)),
                        "structural_sha256": structural_digest(expr), "alpha_sha256": alpha,
                        "expression_v2": document})
                    semantic_seen.add(semantic)
                    alpha_seen.add(alpha)
                    accepted += 1
                except (ValueError, TypeError, RecursionError):
                    rejection["admission_or_identity"] += 1
            if accepted != PER_LABEL_COUNTS[split]:
                raise ValueError(f"insufficient admitted natural examples for {split}/label-{label}: {accepted}")
    audit = validate_natural_decomposition_documents(documents)
    provenance = {"schema": "crse-natural-epfl-decomposition-provenance/v1",
        "source": "EPFL combinational benchmark suite", "upstream_url": EPFL_URL,
        "upstream_commit": EPFL_COMMIT, "license": "MIT License", "license_sha256": sha(EPFL_LICENSE),
        "scout_path": str(scout_path.relative_to(ROOT)).replace("\\", "/"), "scout_sha256": sha(scout_path),
        "selection_seed": seed, "selection": "circuit-disjoint, label-balanced deterministic hash order with round-robin circuits",
        "split_circuits": {key: list(value) for key, value in SPLIT_CIRCUITS.items()},
        "per_label_counts": PER_LABEL_COUNTS, "rejected": dict(rejection), "audit": audit,
        "external_download_performed": False}
    return documents, provenance


def validate_natural_decomposition_documents(documents: list[dict[str, Any]], check=lambda: None):
    expected = {split: 2 * PER_LABEL_COUNTS[split] for split in SPLITS}
    if type(documents) is not list or len(documents) != sum(expected.values()):
        raise ValueError("natural decomposition dataset row count mismatch")
    counts = Counter()
    label_counts = Counter()
    circuits_by_split = defaultdict(set)
    semantics, alphas, ids = set(), set(), set()
    variants = Counter()
    sizes = Counter()
    for row in documents:
        check()
        if (type(row) is not dict or row.get("schema") != DATASET_SCHEMA or row.get("split") not in SPLITS
                or row.get("circuit") not in SPLIT_CIRCUITS[row["split"]] or row.get("natural") is not True
                or row.get("training_use") != (row["split"] == "train")
                or type(row.get("label")) is not int or row["label"] not in (0, 1)
                or type(row.get("n_vars")) is not int or not 4 <= row["n_vars"] <= 10
                or row.get("family") != ("natural_xor_partition" if row["label"] else "natural_indecomposable")):
            raise ValueError("invalid natural decomposition metadata")
        if row["case_id"] in ids:
            raise ValueError("duplicate natural case ID")
        ids.add(row["case_id"])
        expr = expr_from_json(row["expression_v2"])
        admit(expr, row["n_vars"], 1)
        if expr_to_json_dag(expr) != row["expression_v2"]:
            raise ValueError("noncanonical natural expression")
        bits = reference_bits(expr, row["n_vars"])
        analysis = analyze_decomposition(bits, row["n_vars"])
        targets, mask = interaction_target(bits, row["n_vars"])
        semantic = (row["n_vars"], bits)
        alpha = structural_digest(expr, alpha_rename=True)
        if (int(analysis.decomposable) != row["label"] or analysis.witness != row["witness"]
                or [list(component) for component in analysis.components] != row["components"]
                or list(targets) != row["interaction_target"] or list(mask) != row["interaction_mask"]
                or packed_sha256(bits, row["n_vars"]) != row["semantic_sha256"]
                or structural_digest(expr) != row["structural_sha256"] or alpha != row["alpha_sha256"]):
            raise ValueError("natural decomposition semantics or targets changed")
        if semantic in semantics or alpha in alphas:
            raise ValueError("cross-split semantic or alpha-structural duplicate")
        semantics.add(semantic); alphas.add(alpha)
        counts[row["split"]] += 1
        label_counts[(row["split"], row["label"])] += 1
        circuits_by_split[row["split"]].add(row["circuit"])
        variants[row["variant"]] += 1
        sizes[row["n_vars"]] += 1
    if dict(counts) != expected or any(label_counts[(split, label)] != PER_LABEL_COUNTS[split]
                                       for split in SPLITS for label in (0, 1)):
        raise ValueError("natural dataset split or label balance mismatch")
    observed = {circuit for circuits in circuits_by_split.values() for circuit in circuits}
    if len(observed) != sum(len(circuits) for circuits in circuits_by_split.values()):
        raise ValueError("natural circuit leakage")
    return {"rows": len(documents), "split_counts": dict(counts),
        "label_counts": {f"{split}/{label}": label_counts[(split, label)] for split in SPLITS for label in (0, 1)},
        "circuits_by_split": {key: sorted(value) for key, value in circuits_by_split.items()},
        "variant_counts": dict(variants), "size_counts": {str(key): value for key, value in sorted(sizes.items())},
        "semantic_duplicates": 0, "alpha_structural_duplicates": 0,
        "circuit_overlap": 0, "natural_positive_count": sum(row["label"] for row in documents)}
