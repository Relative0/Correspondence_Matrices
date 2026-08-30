"""Structure-matched natural positive/negative EPFL decomposition pairs."""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_expr_serde import expr_to_json_dag

from .blif import parse_blif
from .decomposition_data import canonical, packed_sha256
from .features import structural_digest
from .natural_decomposition import analyze_decomposition, interaction_target, semantic_variables
from .natural_decomposition_data import (
    DATASET_SCHEMA, EPFL_ROOT, PER_LABEL_COUNTS, ROOT, SPLIT_CIRCUITS,
    make_natural_decomposition_documents, sha, validate_natural_decomposition_documents,
)
from .portfolio import admit, reference_bits
from .variable_graph_inputs import graph_from_document

MATCHED_SCHEMA = "crse-natural-epfl-decomposition-matched-dataset/v1"


def _rank(seed: int, positive: dict, candidate: dict):
    value = ":".join((str(seed), positive["case_id"], candidate["source_path"],
                      candidate["root"], candidate["truth_sha256"]))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _distance(positive: dict, candidate: dict, seed: int):
    return (int(candidate["n_vars"] != positive["n_vars"]),
            int(candidate["variant"] != positive["variant"]),
            abs(candidate["n_vars"] - positive["n_vars"]),
            abs(candidate["source_nodes"] - positive["source_nodes"]),
            abs(candidate["depth"] - positive["depth"]),
            abs(candidate["source_edges"] - positive["source_edges"]),
            _rank(seed, positive, candidate))


def _negative_document(candidate, split: str, pair_id: str, sources, semantic_seen, alpha_seen):
    relative = candidate["source_path"]
    path = (ROOT / relative).resolve()
    if path != EPFL_ROOT and EPFL_ROOT not in path.parents:
        raise ValueError("matched source escapes pinned EPFL root")
    if sha(path) != candidate["source_sha256"]:
        raise ValueError("matched source hash changed")
    if relative not in sources:
        sources[relative] = parse_blif(path)
    netlist = sources[relative]
    expr, support = netlist.build_expr(candidate["root"], max_identity_nodes=4096)
    bits, packed_support = netlist.packed_value(candidate["root"])
    if support != packed_support or list(support) != candidate["support"] or len(support) != candidate["n_vars"]:
        raise ValueError("matched source support disagreement")
    admit(expr, len(support), 1)
    environment = build_bitset_env(tuple(f"x{i}" for i in range(len(support))))
    if (reference_bits(expr, len(support)) != bits
            or eval_expr_bitset(expr, environment) != bits
            or semantic_variables(bits, len(support)) != tuple(range(len(support)))):
        raise ValueError("matched natural truth/support disagreement")
    analysis = analyze_decomposition(bits, len(support))
    if analysis.decomposable:
        raise ValueError("matched negative is decomposable")
    semantic = (len(support), packed_sha256(bits, len(support)))
    alpha = structural_digest(expr, alpha_rename=True)
    if semantic in semantic_seen or alpha in alpha_seen:
        raise ValueError("matched negative duplicates retained semantics or structure")
    document = expr_to_json_dag(expr); graph_from_document(document, len(support))
    targets, mask = interaction_target(bits, len(support))
    identity = hashlib.sha256(canonical({"source": relative, "root": candidate["root"],
                                        "truth": candidate["truth_sha256"]})).hexdigest()[:16]
    return {"schema": MATCHED_SCHEMA, "case_id": f"{split}-{candidate['variant']}-{candidate['circuit']}-{identity}",
        "matched_pair_id": pair_id, "split": split, "natural": True, "training_use": split == "train",
        "circuit": candidate["circuit"], "variant": candidate["variant"],
        "source_path": relative, "source_sha256": candidate["source_sha256"], "root": candidate["root"],
        "support_names": list(support), "n_vars": len(support), "label": 0,
        "family": "natural_indecomposable", "source_nodes": candidate["source_nodes"],
        "source_edges": candidate["source_edges"], "depth": candidate["depth"],
        "components": [list(component) for component in analysis.components],
        "interaction_target": list(targets), "interaction_mask": list(mask), "witness": None,
        "semantic_sha256": packed_sha256(bits, len(support)), "structural_sha256": structural_digest(expr),
        "alpha_sha256": alpha, "expression_v2": document}


def make_matched_natural_documents(scout_path: Path, *, seed: int = 20260829, check=lambda: None):
    base, base_provenance = make_natural_decomposition_documents(scout_path, seed=seed, check=check)
    positives = [row for row in base if row["label"] == 1]
    scout = json.loads(Path(scout_path).read_text(encoding="utf-8"))
    negative_candidates = [row for row in scout["rows"] if not row["decomposable"]]
    sources = {}
    semantic_seen = {(row["n_vars"], row["semantic_sha256"]) for row in positives}
    alpha_seen = {row["alpha_sha256"] for row in positives}
    used_sources = set()
    documents = []
    rejection = Counter()
    distances = []
    for positive in positives:
        check()
        pair_id = "pair-" + hashlib.sha256(positive["case_id"].encode("utf-8")).hexdigest()[:16]
        positive_matched = {**positive, "schema": MATCHED_SCHEMA, "matched_pair_id": pair_id}
        candidates = [row for row in negative_candidates if row["circuit"] == positive["circuit"]
                      and row["source_path"] + "#" + row["root"] not in used_sources]
        candidates.sort(key=lambda row: _distance(positive, row, seed))
        negative = None
        for candidate in candidates:
            try:
                candidate_document = _negative_document(candidate, positive["split"], pair_id,
                    sources, semantic_seen, alpha_seen)
                semantic_key = (candidate_document["n_vars"], candidate_document["semantic_sha256"])
                semantic_seen.add(semantic_key); alpha_seen.add(candidate_document["alpha_sha256"])
                used_sources.add(candidate["source_path"] + "#" + candidate["root"])
                negative = candidate_document
                distance = _distance(positive, candidate, seed)
                distances.append({"pair_id": pair_id, "same_n_vars": distance[0] == 0,
                    "same_variant": distance[1] == 0, "n_vars_delta": distance[2],
                    "source_nodes_delta": distance[3], "depth_delta": distance[4],
                    "source_edges_delta": distance[5]})
                break
            except (ValueError, TypeError, RecursionError):
                rejection["candidate_rejected"] += 1
        if negative is None:
            raise ValueError(f"no admitted matched negative for {positive['case_id']}")
        documents.extend((positive_matched, negative))
    audit = validate_matched_documents(documents)
    provenance = {"schema": "crse-natural-epfl-decomposition-matched-provenance/v1",
        "base_selection": base_provenance, "matching": "one-to-one negative within the same circuit; lexicographic minimum of size, variant, node, depth and edge deltas",
        "selection_seed": seed, "rejected": dict(rejection), "pair_distances": distances, "audit": audit,
        "external_download_performed": False}
    return documents, provenance


def validate_matched_documents(documents, check=lambda: None):
    if type(documents) is not list or len(documents) != 2 * sum(PER_LABEL_COUNTS.values()):
        raise ValueError("matched natural row count mismatch")
    stripped = []
    pairs = {}
    for row in documents:
        check()
        if row.get("schema") != MATCHED_SCHEMA or type(row.get("matched_pair_id")) is not str:
            raise ValueError("invalid matched natural schema")
        pairs.setdefault(row["matched_pair_id"], []).append(row)
        stripped.append({key: value for key, value in row.items() if key != "matched_pair_id"} | {"schema": DATASET_SCHEMA})
    base_audit = validate_natural_decomposition_documents(stripped, check=check)
    metrics = []
    for pair_id, pair in pairs.items():
        if len(pair) != 2 or {row["label"] for row in pair} != {0, 1}:
            raise ValueError(f"invalid matched pair: {pair_id}")
        positive = next(row for row in pair if row["label"] == 1)
        negative = next(row for row in pair if row["label"] == 0)
        if positive["split"] != negative["split"] or positive["circuit"] != negative["circuit"]:
            raise ValueError("matched pair crosses split or circuit")
        metrics.append({"same_n_vars": positive["n_vars"] == negative["n_vars"],
            "same_variant": positive["variant"] == negative["variant"],
            "source_nodes_delta": abs(positive["source_nodes"] - negative["source_nodes"]),
            "depth_delta": abs(positive["depth"] - negative["depth"]),
            "source_edges_delta": abs(positive["source_edges"] - negative["source_edges"])})
    return {**base_audit, "matched_pairs": len(pairs),
        "same_n_vars_fraction": statistics.fmean(row["same_n_vars"] for row in metrics),
        "same_variant_fraction": statistics.fmean(row["same_variant"] for row in metrics),
        "median_source_nodes_delta": statistics.median(row["source_nodes_delta"] for row in metrics),
        "median_depth_delta": statistics.median(row["depth_delta"] for row in metrics),
        "median_source_edges_delta": statistics.median(row["source_edges_delta"] for row in metrics)}
