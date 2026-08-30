"""Fresh C11 holdout from unused Yosys-bench functions and XOR compositions.

Raw negative cases are source candidates not selected for C7. Positive cases
XOR two source functions over disjoint variable sets; this preserves their
source semantics and creates an exact, nontrivial decomposition boundary.
Selection is deterministic and independent of dispatcher timing.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .decomposition_data import canonical, packed_sha256
from .features import structural_digest
from .natural_decomposition import analyze_decomposition, semantic_variables
from .portfolio import admit, reference_bits
from .yosys_human_decomposition_data import (
    SOURCE_COMMIT, SOURCE_URL, Candidate, _identity, _scalar_bits, candidates,
    make_yosys_human_documents,
)

DATASET_SCHEMA = "crse-yosys-composed-holdout/v1"
SPLITS = ("sealed_a", "sealed_b")
CASES_PER_LABEL_PER_SPLIT = 10


@dataclass(frozen=True)
class Admitted:
    candidate: Candidate
    identity: str
    bits: int
    label: int
    alpha: str


def _shift(expression: Expr, offset: int) -> Expr:
    if isinstance(expression, Var):
        return Var(expression.i + offset)
    if isinstance(expression, Not):
        return Not(_shift(expression.a, offset))
    if isinstance(expression, (And, Or, Xor, Imp, Eqv)):
        return type(expression)(_shift(expression.a, offset), _shift(expression.b, offset))
    raise TypeError(expression)


def _admitted() -> list[Admitted]:
    result, semantics, alphas = [], set(), set()
    for candidate in candidates():
        n_vars = len(candidate.variable_specs)
        try:
            admit(candidate.expression, n_vars, 1)
            bits = reference_bits(candidate.expression, n_vars)
            if bits != _scalar_bits(candidate) or semantic_variables(bits, n_vars) != tuple(range(n_vars)):
                raise ValueError("candidate scalar oracle disagreement")
            alpha = structural_digest(candidate.expression, alpha_rename=True)
            semantic = (n_vars, bits)
            if semantic in semantics or alpha in alphas:
                continue
            analysis = analyze_decomposition(bits, n_vars)
            result.append(Admitted(candidate, _identity(candidate), bits,
                                   int(analysis.decomposable), alpha))
            semantics.add(semantic)
            alphas.add(alpha)
        except (ValueError, TypeError, RecursionError):
            continue
    return result


def _raw_row(item: Admitted) -> dict:
    candidate, n_vars = item.candidate, len(item.candidate.variable_specs)
    analysis = analyze_decomposition(item.bits, n_vars)
    return {
        "schema": DATASET_SCHEMA,
        "case_id": f"yosys-unused-{candidate.family}-{item.identity[:16]}",
        "split": None,
        "natural": True,
        "training_use": False,
        "source_repository": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_generator": candidate.source_generator,
        "source_kind": "unused_raw_generator_output",
        "family": candidate.family,
        "parameters": candidate.parameters,
        "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
        "n_vars": n_vars,
        "label": item.label,
        "components": [list(component) for component in analysis.components],
        "witness": analysis.witness,
        "semantic_sha256": packed_sha256(item.bits, n_vars),
        "structural_sha256": structural_digest(candidate.expression),
        "alpha_sha256": item.alpha,
        "expression_v2": expr_to_json_dag(candidate.expression),
        "selection_sha256": item.identity,
    }


def _composed_row(left: Admitted, right: Admitted, identity: str) -> dict:
    left_n = len(left.candidate.variable_specs)
    right_n = len(right.candidate.variable_specs)
    n_vars = left_n + right_n
    expression = Xor(left.candidate.expression, _shift(right.candidate.expression, left_n))
    admit(expression, n_vars, 1)
    bits = reference_bits(expression, n_vars)
    scalar = 0
    for assignment in range(1 << n_vars):
        left_assignment = assignment >> right_n
        right_assignment = assignment & ((1 << right_n) - 1)
        value = ((left.bits >> left_assignment) ^ (right.bits >> right_assignment)) & 1
        scalar |= value << assignment
    if bits != scalar or semantic_variables(bits, n_vars) != tuple(range(n_vars)):
        raise ValueError("composed Yosys scalar oracle disagreement")
    analysis = analyze_decomposition(bits, n_vars)
    if not analysis.decomposable:
        raise ValueError("disjoint XOR composition did not decompose")
    alpha = structural_digest(expression, alpha_rename=True)
    specs = [[f"left:{port}", bit] for port, bit in left.candidate.variable_specs]
    specs += [[f"right:{port}", bit] for port, bit in right.candidate.variable_specs]
    return {
        "schema": DATASET_SCHEMA,
        "case_id": f"yosys-composed-xor-{identity[:16]}",
        "split": None,
        "natural": True,
        "training_use": False,
        "source_repository": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_generator": [left.candidate.source_generator, right.candidate.source_generator],
        "source_kind": "disjoint_xor_of_generator_outputs",
        "family": f"xor_{left.candidate.family}_{right.candidate.family}",
        "parameters": {"left": left.candidate.parameters, "right": right.candidate.parameters},
        "component_source_ids": [left.identity, right.identity],
        "variable_specs": specs,
        "n_vars": n_vars,
        "label": 1,
        "components": [list(component) for component in analysis.components],
        "witness": analysis.witness,
        "semantic_sha256": packed_sha256(bits, n_vars),
        "structural_sha256": structural_digest(expression),
        "alpha_sha256": alpha,
        "expression_v2": expr_to_json_dag(expression),
        "selection_sha256": identity,
    }


def _round_robin(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(row)
    for values in grouped.values():
        values.sort(key=lambda row: row["selection_sha256"])
    result, offset = [], 0
    while any(offset < len(values) for values in grouped.values()):
        for family in sorted(grouped):
            if offset < len(grouped[family]):
                result.append(grouped[family][offset])
        offset += 1
    return result


def make_yosys_composed_holdout() -> tuple[list[dict], dict]:
    c7, c7_provenance = make_yosys_human_documents()
    c7_semantics = {(row["n_vars"], row["semantic_sha256"]) for row in c7}
    c7_alphas = {row["alpha_sha256"] for row in c7}
    c7_ids = {row["selection_sha256"] for row in c7}
    admitted = _admitted()

    raw_negatives = [_raw_row(item) for item in admitted if item.label == 0 and item.identity not in c7_ids]
    raw_negatives = [row for row in raw_negatives
                     if (row["n_vars"], row["semantic_sha256"]) not in c7_semantics
                     and row["alpha_sha256"] not in c7_alphas]
    negatives = _round_robin(raw_negatives)[:20]
    if len(negatives) != 20:
        raise ValueError("insufficient unused raw negative Yosys cases")

    descriptors = []
    for left_index, left in enumerate(admitted):
        for right in admitted[left_index + 1:]:
            if len(left.candidate.variable_specs) + len(right.candidate.variable_specs) > 10:
                continue
            identity = hashlib.sha256(canonical({"operation": "disjoint_xor",
                "left": left.identity, "right": right.identity})).hexdigest()
            descriptors.append((identity, left, right))
    positives, seen_semantics, seen_alphas = [], set(c7_semantics), set(c7_alphas)
    for identity, left, right in sorted(descriptors):
        try:
            row = _composed_row(left, right, identity)
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
        raise ValueError("insufficient unique composed positive Yosys cases")

    selected = []
    for label, values in ((0, negatives), (1, positives)):
        for index, row in enumerate(values):
            selected.append({**row, "split": SPLITS[index // CASES_PER_LABEL_PER_SPLIT]})
    selected.sort(key=lambda row: (SPLITS.index(row["split"]), row["selection_sha256"]))
    audit = validate_yosys_composed_holdout(selected, c7)
    provenance = {
        "schema": "crse-yosys-composed-holdout-provenance/v1",
        "source": "YosysHQ/yosys-bench generator semantics",
        "upstream_url": SOURCE_URL,
        "upstream_commit": SOURCE_COMMIT,
        "license": "ISC",
        "selection": "deterministic source-family round robin for unused raw negatives and hash order for disjoint-XOR positives",
        "positive_construction": "XOR of two source functions over disjoint variables; scalar-oracle checked",
        "timing_used_for_selection": False,
        "c7_excluded": True,
        "c7_provenance_schema": c7_provenance["schema"],
        "audit": audit,
        "network_access_performed": False,
        "source_checkout_modified": False,
    }
    return selected, provenance


def validate_yosys_composed_holdout(documents: list[dict], c7: list[dict] | None = None) -> dict:
    if len(documents) != 40:
        raise ValueError("invalid C11 holdout row count")
    c7 = make_yosys_human_documents()[0] if c7 is None else c7
    c7_semantics = {(row["n_vars"], row["semantic_sha256"]) for row in c7}
    c7_alphas = {row["alpha_sha256"] for row in c7}
    counts, semantics, alphas, identities = Counter(), set(), set(), set()
    for row in documents:
        if row.get("schema") != DATASET_SCHEMA or row.get("training_use") is not False:
            raise ValueError("invalid C11 holdout row")
        expression = __import__("cm_expr_serde").expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        analysis = analyze_decomposition(bits, row["n_vars"])
        semantic = (row["n_vars"], packed_sha256(bits, row["n_vars"]))
        alpha = structural_digest(expression, alpha_rename=True)
        if (row["case_id"] in identities or semantic in semantics or alpha in alphas
                or semantic in c7_semantics or alpha in c7_alphas):
            raise ValueError("duplicate C11 or C7 holdout identity")
        if (int(analysis.decomposable) != row["label"] or analysis.witness != row["witness"]
                or [list(component) for component in analysis.components] != row["components"]
                or semantic[1] != row["semantic_sha256"]
                or structural_digest(expression) != row["structural_sha256"]
                or alpha != row["alpha_sha256"]):
            raise ValueError("changed C11 holdout semantics")
        identities.add(row["case_id"])
        semantics.add(semantic)
        alphas.add(alpha)
        counts[(row["split"], row["label"])] += 1
    if any(counts[(split, label)] != 10 for split in SPLITS for label in (0, 1)):
        raise ValueError("unbalanced C11 holdout")
    return {
        "rows": len(documents),
        "split_label_counts": {f"{split}/{label}": counts[(split, label)]
                               for split in SPLITS for label in (0, 1)},
        "semantic_duplicates": 0,
        "alpha_structural_duplicates": 0,
        "c7_semantic_overlap": 0,
        "c7_alpha_overlap": 0,
        "source_kind_counts": dict(sorted(Counter(row["source_kind"] for row in documents).items())),
        "family_counts": dict(sorted(Counter(row["family"] for row in documents).items())),
        "size_counts": dict(sorted(Counter(str(row["n_vars"]) for row in documents).items())),
    }
