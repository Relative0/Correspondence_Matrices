from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from cm_expr_serde import expr_from_json


@dataclass(frozen=True)
class CorpusFormula:
    formula_id: str
    formula_sha256: str
    nominal_n: int
    expression_json: Mapping[str, Any]
    metadata: Mapping[str, Any]

    def to_expr(self):
        return expr_from_json(self.expression_json)


@dataclass(frozen=True)
class ExpressionCorpus:
    path: Path
    sha256: str
    formulas: tuple[CorpusFormula, ...]


def canonical_expression_sha256(expression_json: Mapping[str, Any]) -> str:
    payload = json.dumps(expression_json, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_expression_corpus(path: str | Path) -> ExpressionCorpus:
    corpus_path = Path(path)
    content = corpus_path.read_bytes()
    corpus_hash = hashlib.sha256(content).hexdigest()
    formulas = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        formula_id = str(record["id"])
        if formula_id in seen_ids:
            raise ValueError(f"duplicate corpus formula id: {formula_id}")
        seen_ids.add(formula_id)
        expression_json = record["expression"]
        actual = canonical_expression_sha256(expression_json)
        declared = str(record["sha256"])
        if actual != declared:
            raise ValueError(
                f"formula hash mismatch at line {line_number}: {declared} != {actual}"
            )
        formulas.append(
            CorpusFormula(
                formula_id=formula_id,
                formula_sha256=declared,
                nominal_n=int(record["nominal_n"]),
                expression_json=expression_json,
                metadata=record,
            )
        )
    if not formulas:
        raise ValueError("corpus is empty")
    return ExpressionCorpus(corpus_path, corpus_hash, tuple(formulas))


def require_single_corpus_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    hashes = {
        str(row["corpus_sha256"])
        for row in rows
        if row.get("corpus_sha256") is not None and str(row["corpus_sha256"]).strip()
    }
    if len(hashes) != 1:
        raise ValueError(f"expected exactly one corpus hash, found {sorted(hashes)}")
    return next(iter(hashes))
