"""Offline contract, schedule, evidence, and tiny-arm controls; no speed claims."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest

from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir
from cmbench.comparative import contracts
from cmbench.comparative.arms import execute_arm, scalar_relation, semantic_sha256
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile, resume_cells
from cmbench.comparative.ir import cm_dag_signature, cm_ir_stats, expression_stats
from cmbench.comparative.schedule import balanced_orders, build_plan, case_order, validate_plan


def relation_contract(
    contract_id,
    kind,
    variables,
    expected,
    *,
    output=None,
    fixed=(),
    scope="full",
    restoration="none",
):
    return {
        "schema": contracts.CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "task": "complete_relation",
        "artifact": {
            "kind": kind,
            "variable_order": list(variables),
            "output_order": list(variables if output is None else output),
            "fixed": [{"variable": name, "value": value} for name, value in fixed],
            "output_scope": scope,
            "restoration": restoration,
            "stream": None,
        },
        "lifecycle": "fresh_engine",
        "queries": 1,
        "validation": {
            "oracle": "independent_scalar_assignment/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": expected,
        },
    }


def scalar_contract(contract_id="count"):
    return {
        "schema": contracts.CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "task": "exact_count",
        "artifact": {
            "kind": "scalar_count",
            "variable_order": ["x0"],
            "output_order": [],
            "fixed": [],
            "output_scope": "not_applicable",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "fresh_process",
        "queries": 1,
        "validation": {
            "oracle": "enumeration/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": None,
        },
    }


class ComparativeContractTests(unittest.TestCase):
    def test_full_reduced_scalar_and_stream_contracts_are_explicit(self):
        expected = "0" * 64
        full = relation_contract("full", "packed_bigint", ("x0", "x1"), expected)
        self.assertEqual(contracts.validate_contract(full)["output_scope"], "full")
        reduced = relation_contract(
            "reduced",
            "reduced_bigint",
            ("x0", "x1", "x2"),
            expected,
            output=("x0", "x2"),
            fixed=(("x1", 0),),
            scope="reduced",
        )
        self.assertEqual(contracts.validate_contract(reduced)["fixed"], {"x1": 0})
        self.assertEqual(contracts.validate_contract(scalar_contract())["kind"], "scalar_count")
        stream = relation_contract("stream", "streamed_chunks", ("x0",), expected)
        stream["task"] = "streamed_relation"
        stream["artifact"]["stream"] = {"chunk_bits": 64, "ordering": "assignment_msb_first"}
        self.assertEqual(contracts.validate_contract(stream)["kind"], "streamed_chunks")

    def test_contract_refuses_task_artifact_axis_restoration_and_validation_confusion(self):
        good = relation_contract("good", "packed_bigint", ("x0", "x1"), "0" * 64)
        variants = []
        changed = copy.deepcopy(good)
        changed["task"] = "exact_count"
        variants.append(changed)
        changed = copy.deepcopy(good)
        changed["artifact"]["output_order"] = ["x1", "x0"]
        variants.append(changed)
        changed = copy.deepcopy(good)
        changed["artifact"]["restoration"] = "included"
        variants.append(changed)
        changed = copy.deepcopy(good)
        changed["validation"]["validation_in_timed_span"] = True
        variants.append(changed)
        changed = copy.deepcopy(good)
        changed["artifact"]["fixed"] = [{"variable": "x0", "value": True}]
        variants.append(changed)
        changed = copy.deepcopy(good)
        changed["queries"] = 0
        variants.append(changed)
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(contracts.ContractError):
                contracts.validate_contract(variant)

    def test_canonical_json_rejects_nonfinite_and_contract_digest_is_order_stable(self):
        with self.assertRaises(contracts.ContractError):
            contracts.canonical_bytes({"value": float("nan")})
        contract = relation_contract("stable", "packed_bigint", ("x0",), "0" * 64)
        reordered = {key: contract[key] for key in reversed(contract)}
        self.assertEqual(contracts.contract_digest(contract), contracts.contract_digest(reordered))

    def test_result_validation_keeps_failures_and_checks_success_artifact(self):
        contract = relation_contract("result", "packed_bigint", ("x0",), "a" * 64)
        base = {
            "schema": contracts.RESULT_SCHEMA,
            "contract_sha256": contracts.contract_digest(contract),
            "case_id": "case-1",
            "arm": "cm_flat_bigint",
            "status": "ok",
            "reason": "completed",
            "timings_ns": {"prepare_ns": 2, "task_total_ns": 3},
            "artifact": {
                "kind": "packed_bigint",
                "output_scope": "full",
                "output_order": ["x0"],
                "bytes": 1,
                "sha256": "a" * 64,
            },
            "resources": {},
            "identity": {},
        }
        self.assertEqual(contracts.validate_result(base, contract)["status"], "ok")
        failed = {**base, "status": "timeout", "reason": "worker_deadline", "artifact": None}
        self.assertEqual(contracts.validate_result(failed, contract)["status"], "timeout")
        for change in (
            {"contract_sha256": "0" * 64},
            {"reason": ""},
            {"artifact": {**base["artifact"], "sha256": "b" * 64}},
            {"timings_ns": {"prepare_ns": 4, "task_total_ns": 3}},
        ):
            with self.subTest(change=change), self.assertRaises(contracts.ContractError):
                contracts.validate_result({**base, **change}, contract)


class ComparativeStructuralTests(unittest.TestCase):
    def test_expression_stats_distinguish_object_and_structural_sharing(self):
        shared = Xor(Var(0), Var(1))
        identity_shared = And(shared, shared)
        distinct_equal = And(Xor(Var(0), Var(1)), Xor(Var(0), Var(1)))
        a = expression_stats(identity_shared)
        b = expression_stats(distinct_equal)
        self.assertLess(a["object_dag_nodes"], b["object_dag_nodes"])
        self.assertEqual(a["structural_dag_nodes"], b["structural_dag_nodes"])
        self.assertEqual(a["expression_v2_sha256"], b["expression_v2_sha256"])
        self.assertEqual(a["unfolded_occurrences"], b["unfolded_occurrences"])

    def test_unfolding_cap_and_cm_signature_are_bounded_and_exact(self):
        expr = Var(0)
        for _ in range(20):
            expr = And(expr, expr)
        stats = expression_stats(expr, unfolded_limit=1000)
        self.assertTrue(stats["unfolded_capped"])
        self.assertIsNone(stats["unfolded_occurrences"])
        first = compile_expr_to_cm_ir(expr)
        second = compile_expr_to_cm_ir(expr)
        self.assertEqual(cm_dag_signature(first), cm_dag_signature(second))
        self.assertEqual(cm_ir_stats(first)["cm_ir_signature_sha256"], cm_ir_stats(second)["cm_ir_signature_sha256"])


class ComparativeScheduleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cm-comparative-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def contracts(self):
        expected = "0" * 64
        return {
            "a": relation_contract("a", "packed_bigint", ("x0",), expected),
            "b": relation_contract("b", "packed_bigint", ("x0",), expected),
        }

    def cases(self):
        return [
            {"case_id": "one", "cluster_id": "cluster-1", "input_sha256": "1" * 64},
            {"case_id": "two", "cluster_id": "cluster-2", "input_sha256": "2" * 64},
            {"case_id": "three", "cluster_id": "cluster-3", "input_sha256": "3" * 64},
        ]

    def test_arm_and_case_schedules_preserve_cardinality(self):
        orders = balanced_orders(("a", "b", "c"))
        self.assertEqual(len(orders), 6)
        for arm in ("a", "b", "c"):
            self.assertEqual(Counter(row.index(arm) for row in orders), Counter({0: 2, 1: 2, 2: 2}))
        for mode in ("blocked", "round_robin", "sliding_window", "zipf"):
            sequence = case_order(("a", "b", "c", "d", "e"), mode, seed=7, repetitions=5)
            self.assertEqual(Counter(sequence), Counter({case: 5 for case in "abcde"}))
            self.assertEqual(sequence, case_order(("a", "b", "c", "d", "e"), mode, seed=7, repetitions=5))

    def test_plan_is_deterministic_counterbalanced_sharded_and_tamper_evident(self):
        kwargs = dict(
            campaign_id="pilot-1",
            cases=self.cases(),
            arms=("a", "b"),
            contracts=self.contracts(),
            blocks=4,
            locality="round_robin",
            seed=11,
            shard_cells=5,
        )
        plan = build_plan(**kwargs)
        self.assertEqual(plan, build_plan(**kwargs))
        validate_plan(plan)
        self.assertEqual(len(plan["cells"]), 24)
        for case in ("one", "two", "three"):
            rows = [row for row in plan["cells"] if row["case_id"] == case]
            for arm in ("a", "b"):
                self.assertEqual(Counter(row["arm_position"] for row in rows if row["arm"] == arm), Counter({0: 2, 1: 2}))
        changed = copy.deepcopy(plan)
        changed["cells"][0]["arm_position"] = 99
        with self.assertRaises(ValueError):
            validate_plan(changed)
        with self.assertRaisesRegex(ValueError, "counterbalance"):
            build_plan(**{**kwargs, "blocks": 3})

    def test_append_resume_reconcile_partial_and_nonoverwriting_publication(self):
        plan = build_plan(
            campaign_id="ledger",
            cases=self.cases()[:1],
            arms=("a", "b"),
            contracts=self.contracts(),
            blocks=4,
            locality="blocked",
            seed=1,
            shard_cells=8,
        )
        ledger = self.root / "cells.jsonl"
        first = plan["cells"][0]
        append_record(ledger, {"cell_id": first["cell_id"], "status": "running", "request_sha256": first["contract_sha256"]})
        append_record(ledger, {"cell_id": first["cell_id"], "status": "ok", "request_sha256": first["contract_sha256"]})
        state = read_ledger(ledger)
        self.assertEqual(len(resume_cells(plan, state)), len(plan["cells"]) - 1)
        self.assertFalse(reconcile(plan, state)["complete"])
        append_record(ledger, {"cell_id": first["cell_id"], "status": "ok", "request_sha256": first["contract_sha256"]})
        with self.assertRaises(ValueError):
            read_ledger(ledger)

        partial = self.root / "partial.jsonl"
        partial.write_bytes(b'{"cell_id":"x","status":"running","request_sha256":"a"}\n{"cell')
        state = read_ledger(partial)
        self.assertTrue(state["partial_tail"])
        with self.assertRaisesRegex(ValueError, "audit"):
            resume_cells(plan, state)

        target = self.root / "plan.json"
        publish_json(target, plan)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), plan)
        with self.assertRaises(FileExistsError):
            publish_json(target, {"replacement": True})


class ComparativeArmTests(unittest.TestCase):
    def test_all_core_arms_deliver_the_same_scalar_oracle_relation(self):
        variables = tuple(f"x{i}" for i in range(6))
        shared = Xor(Var(0), Var(1))
        expr = Eqv(And(shared, shared), Imp(Var(4), Or(Var(2), Var(5))))
        expected_bits = scalar_relation(expr, variables, {})
        expected = semantic_sha256(expected_bits, len(variables))
        kinds = {
            "cm_dense": "dense_cm",
            "cm_flat_bigint": "packed_bigint",
            "cm_flat_words": "packed_words",
            "cm_no_reinflate": "packed_bigint",
            "cse_flat": "packed_bigint",
            "raw_flat": "packed_bigint",
        }
        hashes = set()
        for arm, kind in kinds.items():
            with self.subTest(arm=arm):
                contract = relation_contract(arm, kind, variables, expected)
                result = execute_arm(expr=expr, contract=contract, case_id="shared-k6", arm=arm, smoke_bound=8)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["artifact"]["sha256"], expected)
                self.assertFalse(result["resources"]["rss_measured"])
                self.assertIn("task_total_ns", result["timings_ns"])
                hashes.add(result["artifact"]["sha256"])
        self.assertEqual(hashes, {expected})

    def test_reduced_no_reinflate_has_explicit_reduced_oracle_and_axes(self):
        variables = tuple(f"x{i}" for i in range(7))
        output = ("x0", "x6")
        fixed = tuple((f"x{i}", i % 2) for i in range(1, 6))
        expr = Xor(Var(0), Var(6))
        expected_bits = scalar_relation(expr, output, dict(fixed))
        expected = semantic_sha256(expected_bits, len(output))
        contract = relation_contract(
            "reduced",
            "reduced_bigint",
            variables,
            expected,
            output=output,
            fixed=fixed,
            scope="reduced",
        )
        result = execute_arm(expr=expr, contract=contract, case_id="reduced-k7", arm="cm_no_reinflate", smoke_bound=8)
        self.assertEqual(result["artifact"]["output_order"], list(output))
        self.assertEqual(result["artifact"]["sha256"], expected)

    def test_all_sixteen_binary_truth_functions_match_scalar_oracle(self):
        x, y = Var(0), Var(1)

        def formula(mask):
            terms = []
            for assignment in range(4):
                if mask & (1 << assignment):
                    left = x if assignment & 2 else Not(x)
                    right = y if assignment & 1 else Not(y)
                    terms.append(And(left, right))
            if not terms:
                return And(x, Not(x))
            result = terms[0]
            for term in terms[1:]:
                result = Or(result, term)
            return result

        variables = ("x0", "x1")
        for mask in range(16):
            expr = formula(mask)
            expected_bits = scalar_relation(expr, variables, {})
            self.assertEqual(expected_bits, mask)
            expected = semantic_sha256(mask, 2)
            for arm in ("cm_flat_bigint", "cm_no_reinflate", "cse_flat"):
                with self.subTest(mask=mask, arm=arm):
                    contract = relation_contract(f"truth-{mask}-{arm}", "packed_bigint", variables, expected)
                    result = execute_arm(expr=expr, contract=contract, case_id=f"truth-{mask}", arm=arm, smoke_bound=8)
                    self.assertEqual(result["artifact"]["sha256"], expected)

    def test_smoke_bound_and_arm_artifact_mismatch_refuse_before_execution(self):
        expr = Xor(Var(0), Var(1))
        expected = semantic_sha256(scalar_relation(expr, ("x0", "x1"), {}), 2)
        wrong = relation_contract("wrong", "dense_cm", ("x0", "x1"), expected)
        with self.assertRaisesRegex(ValueError, "cannot deliver"):
            execute_arm(expr=expr, contract=wrong, case_id="wrong", arm="cm_flat_bigint", smoke_bound=8)
        right = relation_contract("bound", "packed_bigint", tuple(f"x{i}" for i in range(9)), "0" * 64)
        with self.assertRaisesRegex(ValueError, "bound"):
            execute_arm(expr=expr, contract=right, case_id="bound", arm="cm_flat_bigint", smoke_bound=8)


if __name__ == "__main__":
    unittest.main()

