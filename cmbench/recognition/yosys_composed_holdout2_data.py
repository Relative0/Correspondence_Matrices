"""C12 holdout excluding every C7 and C11 semantic and alpha structure."""
from __future__ import annotations

import hashlib
from collections import Counter

from cm_expr_serde import expr_from_json

from .decomposition_data import canonical, packed_sha256
from .features import structural_digest
from .natural_decomposition import analyze_decomposition
from .portfolio import reference_bits
from .yosys_composed_holdout_data import (
    _admitted, _composed_row, _raw_row, _round_robin, make_yosys_composed_holdout,
)
from .yosys_human_decomposition_data import SOURCE_COMMIT, SOURCE_URL, make_yosys_human_documents

DATASET_SCHEMA = "crse-yosys-composed-holdout2/v1"
SPLITS = ("sealed_a", "sealed_b")


def _reschema(row: dict) -> dict:
    prefix = "yosys-c12-composed" if row["source_kind"] == "disjoint_xor_of_generator_outputs" else "yosys-c12-unused"
    return {**row, "schema": DATASET_SCHEMA,
            "case_id": f"{prefix}-{row['selection_sha256'][:16]}"}


def make_yosys_composed_holdout2() -> tuple[list[dict], dict]:
    c7, _ = make_yosys_human_documents()
    c11, _ = make_yosys_composed_holdout()
    prior = [*c7, *c11]
    excluded_semantics = {(row["n_vars"], row["semantic_sha256"]) for row in prior}
    excluded_alphas = {row["alpha_sha256"] for row in prior}
    excluded_ids = {row["selection_sha256"] for row in prior}
    admitted = _admitted()

    negatives = [_reschema(_raw_row(item)) for item in admitted
                 if item.label == 0 and item.identity not in excluded_ids]
    negatives = [row for row in negatives
                 if (row["n_vars"], row["semantic_sha256"]) not in excluded_semantics
                 and row["alpha_sha256"] not in excluded_alphas]
    negatives = _round_robin(negatives)[:20]
    if len(negatives) != 20:
        raise ValueError("insufficient C12 unused raw negatives")

    descriptors = []
    for left_index, left in enumerate(admitted):
        for right in admitted[left_index + 1:]:
            if len(left.candidate.variable_specs) + len(right.candidate.variable_specs) > 10:
                continue
            identity = hashlib.sha256(canonical({"operation": "disjoint_xor",
                "left": left.identity, "right": right.identity})).hexdigest()
            descriptors.append((identity, left, right))
    positives, seen_semantics, seen_alphas = [], set(excluded_semantics), set(excluded_alphas)
    for identity, left, right in sorted(descriptors):
        try:
            row = _reschema(_composed_row(left, right, identity))
        except (ValueError, TypeError, RecursionError):
            continue
        semantic = (row["n_vars"], row["semantic_sha256"])
        if semantic in seen_semantics or row["alpha_sha256"] in seen_alphas:
            continue
        positives.append(row)
        seen_semantics.add(semantic)
        seen_alphas.add(row["alpha_sha256"])
        if len(positives) == 20:
            break
    if len(positives) != 20:
        raise ValueError("insufficient C12 composed positives")

    selected = []
    for label, values in ((0, negatives), (1, positives)):
        for index, row in enumerate(values):
            selected.append({**row, "split": SPLITS[index // 10]})
    selected.sort(key=lambda row: (SPLITS.index(row["split"]), row["selection_sha256"]))
    audit = validate_yosys_composed_holdout2(selected, prior)
    return selected, {"schema": "crse-yosys-composed-holdout2-provenance/v1",
        "source": "YosysHQ/yosys-bench generator semantics",
        "upstream_url": SOURCE_URL, "upstream_commit": SOURCE_COMMIT, "license": "ISC",
        "selection": "remaining source-family round robin negatives and next deterministic disjoint-XOR positives",
        "positive_construction": "XOR of two source functions over disjoint variables; scalar-oracle checked",
        "excluded_prior_datasets": ["C7", "C11"], "timing_used_for_selection": False,
        "audit": audit, "network_access_performed": False, "source_checkout_modified": False}


def validate_yosys_composed_holdout2(documents: list[dict], prior: list[dict] | None = None) -> dict:
    if len(documents) != 40:
        raise ValueError("invalid C12 row count")
    if prior is None:
        prior = [*make_yosys_human_documents()[0], *make_yosys_composed_holdout()[0]]
    prior_semantics = {(row["n_vars"], row["semantic_sha256"]) for row in prior}
    prior_alphas = {row["alpha_sha256"] for row in prior}
    counts, semantics, alphas, identities = Counter(), set(), set(), set()
    for row in documents:
        if row.get("schema") != DATASET_SCHEMA or row.get("training_use") is not False:
            raise ValueError("invalid C12 row")
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        analysis = analyze_decomposition(bits, row["n_vars"])
        semantic = (row["n_vars"], packed_sha256(bits, row["n_vars"]))
        alpha = structural_digest(expression, alpha_rename=True)
        if (row["case_id"] in identities or semantic in semantics or alpha in alphas
                or semantic in prior_semantics or alpha in prior_alphas):
            raise ValueError("duplicate C12 or prior identity")
        if (int(analysis.decomposable) != row["label"] or analysis.witness != row["witness"]
                or semantic[1] != row["semantic_sha256"] or alpha != row["alpha_sha256"]
                or structural_digest(expression) != row["structural_sha256"]):
            raise ValueError("changed C12 semantics")
        identities.add(row["case_id"]); semantics.add(semantic); alphas.add(alpha)
        counts[(row["split"], row["label"])] += 1
    if any(counts[(split, label)] != 10 for split in SPLITS for label in (0, 1)):
        raise ValueError("unbalanced C12 holdout")
    return {"rows": 40,
        "split_label_counts": {f"{split}/{label}": counts[(split, label)]
                               for split in SPLITS for label in (0, 1)},
        "semantic_duplicates": 0, "alpha_structural_duplicates": 0,
        "prior_semantic_overlap": 0, "prior_alpha_overlap": 0,
        "source_kind_counts": dict(sorted(Counter(row["source_kind"] for row in documents).items())),
        "family_counts": dict(sorted(Counter(row["family"] for row in documents).items())),
        "size_counts": dict(sorted(Counter(str(row["n_vars"]) for row in documents).items()))}
