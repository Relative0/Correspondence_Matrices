from __future__ import annotations

import sys
from pathlib import Path


BENCH = (
    Path(__file__).resolve().parents[1]
    / "deliverables_n22_24"
    / "master_explainer_2026_08_03"
    / "use_case_benchmarks_2026-08-27"
)
sys.path.insert(0, str(BENCH))

import cm_feature_model_history_pilot as history  # noqa: E402
import cm_feature_model_version_delta as delta  # noqa: E402


def test_joint_witness_shares_named_features_but_not_auxiliaries() -> None:
    earlier = history.ParsedCNF(3, [(1,), (-1, 2), (3,)], {1: "root", 2: "earlier-only"})
    later = history.ParsedCNF(3, [(1,), (-1, -2), (-3,)], {1: "root", 2: "later-only"})

    clauses, earlier_map, later_map, unified = delta.remap_joint(earlier, later)
    earlier_product, later_product, stats = delta.joint_witness(earlier, later)

    assert earlier_map[1] == later_map[1]
    assert earlier_map[2] != later_map[2]
    assert earlier_map[3] != later_map[3]
    assert len(clauses) == 6
    assert unified == stats["joint_variables"] == 5
    assert history.scalar_cnf(earlier.clauses, earlier_product)
    assert history.scalar_cnf(later.clauses, later_product)


def test_selector_sat_vectors_reconstruct_both_relations() -> None:
    earlier = ((1,), (-1, 2))
    later = ((-1,), (2,))

    earlier_value, later_value, metrics = delta.selector_sat_vectors(earlier, later, 2)

    assert earlier_value == 0b1000
    assert later_value == 0b0100
    assert metrics["cadical_selector_queries"] == 8
    assert delta.packed_sha(earlier_value ^ later_value, 2)
