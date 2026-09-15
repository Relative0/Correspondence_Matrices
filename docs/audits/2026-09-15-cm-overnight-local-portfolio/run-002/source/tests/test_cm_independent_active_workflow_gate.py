import itertools

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.comparative import independent_active_workflow_gate as gate


def occurrence(expr, artifact, *, cohort="main", primitive="expression_matrix"):
    return {
        "occurrence_id": "test:c01:s001:" + primitive,
        "cohort": cohort,
        "primitive": primitive,
        "expression_v2": expr_to_json_dag(expr),
        "artifact": artifact,
        "artifact_sha256": gate._digest(artifact),
    }


def expected_payload(cohort="main", primitive="expression_matrix"):
    bits = "".join(
        str(int(bool(a and b) ^ (bool(c) if cohort == "ambient_control" else bool(c or d))))
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))
        for c, d in ((0, 0), (0, 1), (1, 0), (1, 1))
    )
    full = {
        "expression": "(A AND B) XOR C" if cohort == "ambient_control" else "(A AND B) XOR (C OR D)",
        "ambient_variables": ["A", "B", "C", "D"],
        "live_variables": ["A", "B", "C"] if cohort == "ambient_control" else ["A", "B", "C", "D"],
        "matrix": {"rows": 4, "columns": 4, "bits": bits,
                   "row_labels": ["AB=00", "AB=01", "AB=10", "AB=11"],
                   "column_labels": ["CD=00", "CD=01", "CD=10", "CD=11"]},
    }
    return full if primitive == "expression_matrix" else full["matrix"]


def test_admitted_payload_matches_cold_and_reused_current_source():
    a, b, c, d = (Var(index) for index in range(4))
    for cohort, expr in (("main", Xor(And(a, b), Or(c, d))), ("ambient_control", Xor(And(a, b), c))):
        for primitive in gate.PRIMITIVES:
            artifact = expected_payload(cohort, primitive)
            row = occurrence(expr, artifact, cohort=cohort, primitive=primitive)
            cold = gate._run_once(row, None)
            reused = gate._run_once(row, gate._prepare(row))
            assert cold["artifact"] == artifact == reused["artifact"]
            assert cold["output_sha256"] == reused["output_sha256"]
            assert cold["ordering_sha256"] == reused["ordering_sha256"]


def test_all_three_variable_functions_materialize_exactly():
    variables = [Var(index) for index in range(3)]
    for mask in range(256):
        terms = []
        for assignment in range(8):
            if not ((mask >> assignment) & 1):
                continue
            literals = [variables[index] if ((assignment >> (2 - index)) & 1) else Not(variables[index]) for index in range(3)]
            term = literals[0]
            for literal in literals[1:]: term = And(term, literal)
            terms.append(term)
        if not terms:
            expr = And(variables[0], Not(variables[0]))
        else:
            expr = terms[0]
            for term in terms[1:]: expr = Or(expr, term)
        row = {"expression_v2": expr_to_json_dag(expr)}
        state = gate._prepare(row)
        dense = gate.materialize_cm(state["node"], state["layout"][0], state["layout"][1], fixed={})
        actual = gate._pack_dense(dense)
        expected = "".join(str((mask >> (((a << 2) | (b << 1) | c))) & 1) for a, b, c, _d in itertools.product((0, 1), repeat=4))
        assert actual == expected


def test_identity_sharing_and_tree_expansion_are_exact_and_structure_distinct():
    a, b, c = Var(0), Var(1), Var(2)
    shared_subtree = And(a, b)
    shared = Xor(shared_subtree, Or(shared_subtree, c))
    expanded = Xor(And(Var(0), Var(1)), Or(And(Var(0), Var(1)), Var(2)))
    states = [gate._prepare({"expression_v2": expr_to_json_dag(expr)}) for expr in (shared, expanded)]
    bits = [gate._pack_dense(gate.materialize_cm(state["node"], state["layout"][0], state["layout"][1], fixed={})) for state in states]
    assert bits[0] == bits[1]
    assert gate._structure_sha(states[0]["node"]) == gate._structure_sha(states[1]["node"])
