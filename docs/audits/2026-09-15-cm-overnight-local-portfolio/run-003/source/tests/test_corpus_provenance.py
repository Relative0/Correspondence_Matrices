import json

import pytest

from cmbench.corpus import (
    canonical_expression_sha256,
    load_expression_corpus,
    require_single_corpus_hash,
)


def _record(formula_id="f1"):
    expression = {"op": "var", "i": 0}
    return {
        "id": formula_id,
        "sha256": canonical_expression_sha256(expression),
        "nominal_n": 1,
        "expression": expression,
    }


def test_load_corpus_validates_formula_and_file_hash(tmp_path):
    path = tmp_path / "corpus.jsonl"
    path.write_text(json.dumps(_record(), sort_keys=True) + "\n", encoding="utf-8")
    corpus = load_expression_corpus(path)
    assert len(corpus.formulas) == 1
    assert corpus.formulas[0].to_expr().i == 0
    assert len(corpus.sha256) == 64


def test_load_corpus_rejects_formula_hash_mismatch(tmp_path):
    record = _record()
    record["sha256"] = "0" * 64
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="formula hash mismatch"):
        load_expression_corpus(path)


def test_load_corpus_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "duplicate.jsonl"
    line = json.dumps(_record())
    path.write_text(line + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_expression_corpus(path)


def test_aggregation_rejects_mixed_or_missing_corpus_hashes():
    assert require_single_corpus_hash([{"corpus_sha256": "a"}, {"corpus_sha256": "a"}]) == "a"
    with pytest.raises(ValueError, match="exactly one"):
        require_single_corpus_hash([{"corpus_sha256": "a"}, {"corpus_sha256": "b"}])
    with pytest.raises(ValueError, match="exactly one"):
        require_single_corpus_hash([{}])
