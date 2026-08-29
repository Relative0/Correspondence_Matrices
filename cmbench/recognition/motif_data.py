"""Exact hidden-affine/one-bit-near fixtures with disjoint generating templates.

All variable-permuted and output-complemented variants of a parent affine
support size belong to one split. Each near-match has a unique nearest affine
function (distance one versus affine code minimum distance 128 at eight vars).
This is intentionally a difficult, narrow mechanism dataset, not natural data.
"""
from __future__ import annotations

import hashlib
import random
from functools import lru_cache
from typing import Any

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Not, Or, Var, Xor

from .corpus import Case
from .features import structural_digest
from .portfolio import admit, reference_bits
from .teacher import teach, is_affine

SPLITS = ("train", "validation", "test", "confirmatory")
SUPPORTS = {"train": (1, 2, 3, 5), "validation": (4,), "test": (6,), "confirmatory": (7,)}
TEMPLATES = {"train": "xor-dnf-absorption/v1", "validation": "xor-cnf-absorption/v1",
             "test": "negated-equivalence-absorption/v1", "confirmatory": "equivalence-negated-left-absorption/v1"}


@lru_cache(maxsize=1)
def _affine_tables():
    columns = [reference_bits(Var(i), 8) for i in range(8)]
    full = (1 << 256) - 1
    result = []
    for coefficients in range(256):
        bits = 0
        for i in range(8):
            if (coefficients >> i) & 1:
                bits ^= columns[i]
        for constant in (0, 1):
            result.append((bits ^ (full if constant else 0), coefficients.bit_count()))
    return tuple(result)


def semantic_group(bits: int) -> str:
    distance, support = min(((bits ^ affine).bit_count(), support) for affine, support in _affine_tables())
    if distance > 1:
        raise ValueError("not an admitted affine/one-bit-near fixture")
    return f"affine-near-permutation-complement-support-{support}"


def _hidden(variables, split):
    if len(variables) == 1:
        return Var(variables[0])
    mid = len(variables) // 2
    a, b = _hidden(variables[:mid], split), _hidden(variables[mid:], split)
    if split == "train":
        return Or(And(a, Not(b)), And(Not(a), b))
    if split == "validation":
        return And(Or(a, b), Not(And(a, b)))
    if split == "test":
        return Not(Eqv(a, b))
    return Eqv(Not(a), b)


def make_motif_documents(seed: int, counts=(64, 16, 16, 8), check=lambda: None) -> list[dict[str, Any]]:
    if (type(seed) is not int or not 0 <= seed <= 2**32 - 1 or type(counts) is not tuple
            or len(counts) != 4 or any(type(n) is not int or not 1 <= n <= limit
                for n, limit in zip(counts, (128, 64, 48, 16)))):
        raise ValueError("invalid finite motif corpus size")
    documents = []
    seen = set()
    for split, count in zip(SPLITS, counts):
        rng = random.Random(f"{seed}:{split}:hidden-affine-v1")
        accepted = 0
        for attempt in range(count * 200):
            check()
            if accepted == count:
                break
            support = rng.choice(SUPPORTS[split])
            variables = rng.sample(range(8), support)
            base = _hidden(variables, split)
            if rng.randrange(2):
                base = Not(base)
            # Same output, different source work; no random model-generated code.
            base = Or(base, And(base, Var(rng.randrange(8))))
            positive = teach(base, 8)
            if positive.bits in seen:
                continue
            flip_assignment = rng.randrange(256)
            literals = [Var(i) if (flip_assignment >> (7 - i)) & 1 else Not(Var(i)) for i in range(8)]
            minterm = literals[0]
            for literal in literals[1:]:
                minterm = And(minterm, literal)
            negative = Xor(base, minterm)
            for label, expr in ((1, base), (0, negative)):
                cm = teach(expr, 8)
                if is_affine(cm) != bool(label):
                    raise ValueError("teacher label disagreement")
                if cm.bits in seen:
                    raise ValueError("duplicate semantic function")
                seen.add(cm.bits)
                group = semantic_group(cm.bits)
                documents.append({"case_id": f"{split}-{accepted:03d}-{label}", "split": split,
                    "family": "hidden_affine" if label else "one_bit_near", "n_vars": 8,
                    "queries": (1, 8, 64)[accepted % 3], "label": label,
                    "source_id": f"generated:{TEMPLATES[split]}", "template": TEMPLATES[split],
                    "parent_id": f"{split}-{accepted:03d}", "group_digest": group,
                    "digest": structural_digest(expr), "alpha_digest": structural_digest(expr, alpha_rename=True),
                    "semantic_sha256": hashlib.sha256(cm.bits.to_bytes(32, "little")).hexdigest(),
                    "teacher": cm.to_dict(), "expression": expr_to_json_dag(expr)})
            accepted += 1
        if accepted != count:
            raise ValueError("finite generator could not satisfy corpus request")
    validate_documents(documents, check=check)
    return documents


def decode_bounded_dag(dag, n_vars=8, max_nodes=4096):
    if type(n_vars) is not int or not 1 <= n_vars <= 8 or type(max_nodes) is not int or not 1 <= max_nodes <= 4096:
        raise ValueError("invalid DAG admission bounds")
    if (type(dag) is not dict or set(dag) != {"version", "nodes", "root"} or dag["version"] != 2
            or type(dag["nodes"]) is not list or not 1 <= len(dag["nodes"]) <= max_nodes
            or type(dag["root"]) is not int or not 0 <= dag["root"] < len(dag["nodes"])):
        raise ValueError("invalid bounded DAG")
    for index, node in enumerate(dag["nodes"]):
        if type(node) is not dict:
            raise ValueError("invalid DAG node")
        op = node.get("op")
        keys = {"op", "i"} if op == "var" else {"op", "a"} if op == "not" else {"op", "a", "b"}
        if op not in ("var", "not", "and", "or", "xor", "imp", "eqv") or set(node) != keys:
            raise ValueError("unsupported DAG operation")
        for key in keys - {"op"}:
            bound = n_vars if key == "i" else index
            if type(node[key]) is not int or not 0 <= node[key] < bound:
                raise ValueError("invalid variable or non-topological reference")
    expr = expr_from_json(dag)
    admit(expr, n_vars, 1)
    return expr


def case_from_document(data: dict[str, Any]) -> Case:
    expr = decode_bounded_dag(data["expression"])
    if type(data["n_vars"]) is not int or data["n_vars"] != 8:
        raise ValueError("motif dataset requires eight-variable universe")
    admit(expr, 8, data["queries"])
    return Case(data["case_id"], data["family"], data["split"], 8, data["queries"], expr,
                structural_digest(expr), data["group_digest"])


def validate_documents(documents, check=lambda: None):
    if type(documents) is not list or not 8 <= len(documents) <= 512:
        raise ValueError("invalid dataset row bound")
    ids, semantic_seen = set(), set()
    groups, alphas, templates = {}, {}, {}
    split_counts = {split: 0 for split in SPLITS}
    for data in documents:
        check()
        if (type(data) is not dict or data.get("split") not in SPLITS or type(data.get("label")) is not int
                or data["label"] not in (0, 1) or type(data.get("case_id")) is not str
                or not 1 <= len(data["case_id"]) <= 100):
            raise ValueError("invalid dataset metadata")
        if data["case_id"] in ids:
            raise ValueError("duplicate case ID")
        ids.add(data["case_id"])
        case = case_from_document(data)
        cm = teach(case.expr, 8)
        group = semantic_group(cm.bits)
        alpha = structural_digest(case.expr, alpha_rename=True)
        if (data["teacher"] != cm.to_dict() or data["label"] != int(is_affine(cm))
                or data["digest"] != case.digest or data["group_digest"] != group
                or data["alpha_digest"] != alpha or data["semantic_sha256"] != hashlib.sha256(cm.bits.to_bytes(32, "little")).hexdigest()
                or data["template"] != TEMPLATES[case.split] or data["source_id"] != f"generated:{TEMPLATES[case.split]}"
                or data["family"] != ("hidden_affine" if data["label"] else "one_bit_near")):
            raise ValueError("dataset identity, label, template, or layout disagreement")
        if cm.bits in semantic_seen:
            raise ValueError("duplicate semantic function")
        semantic_seen.add(cm.bits)
        for mapping, key in ((groups, group), (alphas, alpha), (templates, data["template"])):
            if mapping.setdefault(key, case.split) != case.split:
                raise ValueError("split leakage")
        split_counts[case.split] += 1
    if any(n == 0 for n in split_counts.values()):
        raise ValueError("missing required split")
    return {"split_counts": split_counts, "semantic_groups": len(groups), "exact_duplicates": 0,
            "cross_split_alpha_structural_duplicates": 0, "cross_split_templates": 0,
            "permutation_and_output_complement_groups": "exact nearest-affine support-size groups",
            "limitation": "Only affine/one-bit-near fixtures at ambient eight; very few independent support/template clusters."}
