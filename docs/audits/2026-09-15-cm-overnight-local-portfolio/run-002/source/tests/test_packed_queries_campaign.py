"""Small independent-output preflight for every measured panel arm."""
import json

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Or, Var, Xor
from scripts import cm_packed_queries_campaign as campaign


@pytest.mark.parametrize("task", ("count", "stream", "cache"))
def test_every_panel_arm_matches_oracle_and_charges_session(task):
    expr = And(Or(Var(0), Var(1)), Eqv(Imp(Var(2), Var(3)), Xor(Var(4), Var(5))))
    document = expr_to_json_dag(expr)
    case = {"id": f"preflight-{task}", "task": task, "n": 6, "mode": "pressure",
            "document": document, "document_json": json.dumps(document)}
    for q in ((32,) if task == "cache" else (1, 16)):
        target = campaign.expected(case, q)
        for method in campaign.methods(case):
            result, timing = campaign.session(case, method, q)
            assert result == target, (task, q, method)
            assert timing["total_ns"] == sum(timing[key] for key in ("setup_ns", "query_delivery_ns", "cleanup_ns"))
            assert timing["cache"]["entry_bytes"] <= timing["cache"]["max_bytes"]
            assert timing["warm_ns"] > 0
            if task == "stream":
                assert 0 < timing["first_chunk_ns"] <= timing["total_ns"]


def test_fixture_serialized_ingress_matches_oracle_document():
    cohorts = campaign.cases()
    identities = set()
    for cases in cohorts.values():
        for case in cases:
            assert case["id"] not in identities
            identities.add(case["id"])
            if "document" in case:
                assert json.loads(case["document_json"]) == case["document"]
