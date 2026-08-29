"""Simulated adapters test contracts, not native performance or availability."""
import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import cm_native_contracts as native
from scripts import cm_measurement_verify as verify


class ScalarSolver:
    def __init__(self):
        self.clauses, self.n, self.closed = [], 0, False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def add_clause(self, clause):
        self.clauses.append(clause)
        self.n = max(self.n, max(map(abs, clause), default=0))

    def solve(self, assumptions):
        self.assumptions = assumptions
        self.matches = [a for a in range(1 << self.n) if all(
            any(((a // (2 ** (abs(lit) - 1))) % 2 == 1) == (lit > 0) for lit in clause)
            for clause in self.clauses + [[lit] for lit in assumptions])]
        return bool(self.matches)

    def get_model(self):
        return [i + 1 if self.matches[0] & (1 << i) else -i - 1 for i in range(self.n)]

    def get_core(self):
        return list(self.assumptions)


class Node:
    def __init__(self, manager, value):
        self.manager, self.value = manager, value

    def __and__(self, other):
        return Node(self.manager, self.value & other.value)

    def __or__(self, other):
        return Node(self.manager, self.value | other.value)

    def __invert__(self):
        return Node(self.manager, self.value ^ self.manager.true.value)


class SimulatedBDD:
    def __init__(self, k):
        self.k, self.events, self.var_levels = k, [], {}
        self.auto, self.reorders = True, 0
        self.true, self.false = Node(self, (1 << (1 << k)) - 1), Node(self, 0)

    def configure(self, **kwargs):
        if kwargs:
            self.events.append("disable_reordering")
            self.auto = kwargs["reordering"]
        return {"reordering": self.auto}

    def declare(self, *names):
        self.events.append("declare")
        if self.auto:
            raise AssertionError("declared before disabling automatic reordering")
        self.var_levels = {name: i for i, name in enumerate(names)}

    def var(self, name):
        i = int(name[1:])
        return Node(self, sum(1 << a for a in range(1 << self.k) if a & (1 << i)))

    def statistics(self):
        return {"n_reorderings": self.reorders}

    def reorder(self):
        self.events.append("group_sift")
        self.reorders += 1
        self.var_levels = {name: self.k - 1 - level for name, level in self.var_levels.items()}


def export_simulated(manager, root):
    manager.events.append("export_measured_graph")
    assert root.manager is manager
    graph = {"level_of_var": dict(manager.var_levels)}
    levels = {level: int(name[1:]) for name, level in manager.var_levels.items()}

    def visit(level, assignment):
        if level == manager.k:
            return "T" if (root.value >> assignment) & 1 else "F"
        low = visit(level + 1, assignment)
        high = visit(level + 1, assignment | (1 << levels[level]))
        if low == high:
            return low
        identifier = len(graph) + 1
        graph[str(identifier)] = [level, low, high]
        return identifier

    graph["roots"] = [visit(0, 0)]
    return graph


class NativeContractTests(unittest.TestCase):
    def test_source_only_binding_is_not_native_availability(self):
        with patch.object(native.importlib.metadata, "version", return_value="0.6.0"), \
                patch.object(native.importlib.util, "find_spec", return_value=SimpleNamespace(origin="cudd.py")):
            row = native.binding_identity("dd", "dd.cudd", "0.6.0")
        self.assertEqual(row["status"], "refused")
        self.assertEqual(row["reason"], "module_is_not_compiled_extension")
        self.assertFalse(row["fallback_used"])

    def test_missing_binding_and_unreviewed_version_are_explicit_refusals(self):
        suffix = native.importlib.machinery.EXTENSION_SUFFIXES[0]
        for spec, version, reason in ((None, "0.6.0", "compiled_binding_missing"),
                                      (SimpleNamespace(origin="cudd" + suffix), "0.7.0", "unreviewed_wrapper_version")):
            with patch.object(native.importlib.metadata, "version", return_value=version), \
                    patch.object(native.importlib.util, "find_spec", return_value=spec):
                self.assertEqual(native.binding_identity("dd", "dd.cudd", "0.6.0")["reason"], reason)

    def test_binding_records_actual_file_hash_not_just_package_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ("fixture" + native.importlib.machinery.EXTENSION_SUFFIXES[0])
            path.write_bytes(b"not executed: simulated extension")
            with patch.object(native.importlib.metadata, "version", return_value="0.6.0"), \
                    patch.object(native.importlib.util, "find_spec", return_value=SimpleNamespace(origin=str(path))):
                row = native.binding_identity("dd", "dd.cudd", "0.6.0")
            self.assertEqual(row["status"], "available")
            self.assertEqual(row["binding"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(row["complete_build_identity"])

    def test_sat_complete_vector_and_undo_sessions_cover_boundaries(self):
        for item in native.probe_cases():
            created = []

            def factory():
                solver = ScalarSolver()
                created.append(solver)
                return solver

            with self.subTest(case=item["case"]["id"]):
                row = native.sat_contract(item["case"], item["sessions"], factory)
                self.assertEqual(row["packed_hex"], hex(verify.scalar_vector(item["case"])))
                self.assertEqual(len(created), 2)
                self.assertTrue(all(solver.closed for solver in created))
                self.assertEqual(row["sessions"][0], row["sessions"][-1])
                self.assertFalse(row["count_task_measured"])

    def test_all_generated_cases_match_simulated_sat_contract(self):
        for case in verify.fixtures():
            row = native.sat_contract(case, [[]], ScalarSolver)
            self.assertEqual(row["packed_hex"], hex(verify.scalar_vector(case)))

    def test_unused_variables_expand_output_and_witness_universe(self):
        row = native.sat_contract({"k": 3, "clauses": [[1]]}, [[], [-3], [3], []], ScalarSolver)
        self.assertEqual(row["packed_hex"], "0xaa")
        self.assertEqual(len(row["sessions"][0]["witness"]), 3)
        self.assertEqual(row["vector_solve_calls"], 8)

    def test_controller_rechecks_native_result_identity_counts_sessions_witness_and_core(self):
        case = {"k": 2, "clauses": [[1]]}
        request = {"identity": {"test": "simulated"}, "cases": [{"case": case, "sessions": [[], [-1], [1]]}]}
        result = {"schema": "cm-native-sat-contract/v1", "status": "passed", "pid": 123,
                  "request_sha256": native.digest(request), "identity": request["identity"],
                  "adapter": "pysat.Cadical195", "rows": [native.sat_contract(case, [[], [-1], [1]], ScalarSolver)],
                  "performance_ranking_permitted": False, "native_execution": True, "source_root": str(native.ROOT)}
        native.validate_sat_result(result, request, native.ROOT, [123])
        changes = [lambda r: r.update(pid=True), lambda r: r.update(pid=124),
                   lambda r: r.update(extra="unaccounted"), lambda r: r.update(rows=[]),
                   lambda r: r.update(performance_ranking_permitted=True),
                   lambda r: r["rows"][0].update(vector_solve_calls=True),
                   lambda r: r["rows"][0].update(solver_instances=1),
                   lambda r: r["rows"][0].update(packed_hex="0x0"),
                   lambda r: r["rows"][0]["sessions"][0].update(witness=[-1, 2]),
                   lambda r: r["rows"][0]["sessions"][1].update(core=[]),
                   lambda r: r["rows"][0]["sessions"][2].update(assumptions=[True]),
                   lambda r: r["rows"][0]["sessions"][1].update(core_minimality_claimed=True)]
        for change in changes:
            changed = copy.deepcopy(result)
            change(changed)
            with self.assertRaises(ValueError):
                native.validate_sat_result(changed, request, native.ROOT, [123])

    def test_invalid_sessions_refuse_before_solver_construction(self):
        with patch.object(native, "ScalarSolver", create=True) as factory:
            for sessions in ([], [[0]], [[True]], [[3]], [[1, -1]], [[1, 1]], [[1]] * 17):
                with self.subTest(sessions=sessions), self.assertRaises(ValueError):
                    native.sat_contract({"k": 2, "clauses": []}, sessions, factory)
        factory.assert_not_called()

    def test_sat_unknown_answer_is_not_false_or_success(self):
        class Unknown(ScalarSolver):
            def solve(self, assumptions):
                return None

        with self.assertRaisesRegex(ValueError, "unknown"):
            native.sat_contract({"k": 0, "clauses": []}, [[]], Unknown)

    def test_wrong_sat_vector_is_refused(self):
        class Wrong(ScalarSolver):
            def solve(self, assumptions):
                return False

        with self.assertRaisesRegex(ValueError, "vector disagrees"):
            native.sat_contract({"k": 0, "clauses": []}, [[]], Wrong)

    def test_partial_invalid_or_duplicate_witness_is_refused(self):
        for model in ([], [1, 1], [0, 2], [True, 2], [-1, 2]):
            with patch.object(ScalarSolver, "get_model", return_value=model), self.assertRaises(ValueError):
                native.sat_contract({"k": 2, "clauses": [[1]]}, [[]], ScalarSolver)

    def test_core_must_be_subset_and_really_unsatisfiable(self):
        for core in ([2], [True], [], [-1, -1]):
            with patch.object(ScalarSolver, "get_core", return_value=core), self.assertRaises(ValueError):
                native.sat_contract({"k": 2, "clauses": [[1]]}, [[-1]], ScalarSolver)

    def test_cudd_fixed_order_disables_before_construction_and_exports_same_manager(self):
        manager = SimulatedBDD(2)
        times = iter((0, 11, 31, 38))
        row = native.cudd_order_contract({"k": 2, "clauses": [[-1, 2]]}, "fixed", lambda: manager,
                                         export_simulated, clock=lambda: next(times))
        self.assertEqual(manager.events, ["disable_reordering", "declare", "export_measured_graph"])
        self.assertEqual(row["reorder_method"], "none")
        self.assertEqual(row["cold_total_ns"], 38)
        self.assertEqual(row["manager_and_build_ns"] + row["order_search_ns"] + row["export_ns"], 38)

    def test_cudd_group_sifting_records_actual_reordered_graph_not_fixed_rebuild(self):
        manager = SimulatedBDD(3)
        row = native.cudd_order_contract({"k": 3, "clauses": [[1], [-2, 3]]}, "group_sift", lambda: manager,
                                         export_simulated)
        self.assertEqual(row["reorder_method"], "CUDD_REORDER_GROUP_SIFT")
        self.assertEqual(row["reorderings_after"], 1)
        self.assertNotEqual(row["order_before"], row["order_after"])
        self.assertEqual(row["graph"]["level_of_var"], row["order_after"])
        self.assertEqual(manager.events[-2:], ["group_sift", "export_measured_graph"])

    def test_cudd_wrong_graph_order_or_answer_is_refused(self):
        for corruption in ("order", "answer"):
            def broken(manager, root):
                graph = export_simulated(manager, root)
                if corruption == "order":
                    graph["level_of_var"] = {"x0": 0, "x1": 1}
                else:
                    graph["roots"] = ["F"]
                return graph

            with self.assertRaises(ValueError):
                native.cudd_order_contract({"k": 2, "clauses": [[1]]}, "group_sift", lambda: SimulatedBDD(2), broken)

    def test_cudd_hidden_construction_search_and_unknown_reorder_modes_refused(self):
        manager = SimulatedBDD(2)
        manager.reorders = 1
        with self.assertRaisesRegex(ValueError, "unexpected construction"):
            native.cudd_order_contract({"k": 2, "clauses": []}, "fixed", lambda: manager, export_simulated)
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            native.cudd_order_contract({"k": 2, "clauses": []}, "sift", lambda: manager, export_simulated)

    def test_d4_count_is_not_a_complete_vector_or_resident_query(self):
        for k, value in ((0, 0), (0, 1), (8, 256)):
            row = native.parse_d4_count(f"c exact integer\ns {value}\n".encode(), k)
            self.assertEqual(row["count"], value)
            self.assertEqual(row["lifecycle"], "cold_cli_including_process_start")
            self.assertFalse(row["complete_vector_measured"])
            self.assertFalse(row["ddnnf_serialization_measured"])

    def test_d4_duplicate_conflicting_noninteger_and_oversized_output_refused(self):
        for raw in (b"", b"s 1\ns 1\n", b"s 1\ns 0\n", b"s -1\n", b"s 1.0\n", b"s 01\n",
                    b"s 1e2\n", b"s mc 1\n", b"s 257\n", b"s SATISFIABLE\n", b"x" * (verify.MAX_RECORD + 1)):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                native.parse_d4_count(raw, 8)
        with self.assertRaises(ValueError):
            native.parse_d4_count(b"s 2\n", 0)

    def test_d4_command_requires_exact_binary_and_declared_cnf_universe(self):
        with tempfile.TemporaryDirectory() as directory:
            binary, cnf = Path(directory) / "d4-fixture.exe", Path(directory) / "input.cnf"
            binary.write_bytes(b"not executable, never launched")
            cnf.write_bytes(b"p cnf 3 1\n1 0\n")
            binary_hash = native.file_identity(binary)["sha256"]
            input_hash = native.file_identity(cnf)["sha256"]
            case = {"k": 3, "clauses": [[1]]}
            row = native.d4_count_command(binary, binary_hash, cnf, input_hash, case)
            self.assertEqual(row["command"], [str(binary), "-mc", str(cnf)])
            self.assertFalse(row["execution_authorized_by_this_function"])
            for changed in ({"k": 1, "clauses": [[1]]}, {"k": 3, "clauses": [[-1]]}):
                with self.assertRaises(ValueError):
                    native.d4_count_command(binary, binary_hash, cnf, input_hash, changed)
            binary.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "binary changed"):
                native.d4_count_command(binary, binary_hash, cnf, input_hash, case)


if __name__ == "__main__":
    unittest.main()
