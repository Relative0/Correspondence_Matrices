import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from scripts import cm_comparative_native_scout as scout


LOCAL_LOCK = Path(
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214/"
    "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json"
)
REMOTE_LOCK = Path("study/RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json")
LOCK = LOCAL_LOCK if LOCAL_LOCK.is_file() else REMOTE_LOCK


class Node:
    def __init__(self, manager, name, negated=False):
        self.bdd = manager
        self.name = name
        self.negated = negated

    def __hash__(self):
        return id(self)

    def __invert__(self):
        return self.bdd.negations[self]


class Manager:
    def __init__(self):
        self.var_levels = {"x0": 0, "x1": 1}
        self.true = Node(self, "true")
        self.false = Node(self, "false")
        self.low = Node(self, "low")
        self.root = Node(self, "root")
        self.low_negated = Node(self, "low-negated", True)
        self.root_negated = Node(self, "root-negated", True)
        self.negations = {
            self.true: self.false, self.false: self.true,
            self.low: self.low_negated, self.low_negated: self.low,
            self.root: self.root_negated, self.root_negated: self.root,
        }

    def succ(self, node):
        if node is self.low:
            return 1, self.false, self.true
        if node is self.root:
            return 0, self.low, self.low
        raise AssertionError("terminal passed to succ")


class ComparativeNativeScoutTests(unittest.TestCase):
    def test_native_worker_has_explicit_nonperformance_measurement_fence(self):
        payload = {"status": "passed", "native_execution": True}
        stream = io.BytesIO()
        with patch.object(scout, "probe_sat", return_value=dict(payload)), \
                patch.object(scout.time, "sleep") as sleep, \
                patch.object(scout.sys, "stdout", SimpleNamespace(buffer=stream)):
            self.assertEqual(scout.native_worker("sat"), 0)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(sleep.call_args_list[0].args, (0.05,))
        self.assertEqual(sleep.call_args_list[1].args, (0.05,))
        written = stream.getvalue()
        self.assertIn(b'"measurement_fence_ms":100', written)
        executable = str(Path(scout.sys.executable).resolve())
        command = scout.fenced_native_command([executable, "--version"])
        self.assertEqual(command[:3], [executable, "-B", "-c"])
        self.assertEqual(command[-2:], [executable, "--version"])

    def load_lock(self):
        return json.loads(LOCK.read_text(encoding="utf-8"))

    def test_frozen_dependency_lock_is_exact_and_bounded(self):
        rows = scout.validate_dependency_lock(self.load_lock())
        self.assertEqual(set(rows), {
            "setuptools", "wheel", "ply", "astutils", "networkx", "dd", "six", "python-sat",
        })
        self.assertLessEqual(sum(row["bytes"] for row in rows.values()), scout.MAX_TOTAL_DOWNLOAD_BYTES)
        self.assertEqual(rows["dd"]["kind"], "wheel")
        self.assertEqual(rows["python-sat"]["kind"], "wheel")

    def test_dependency_lock_refuses_ambiguous_or_unbounded_locations(self):
        mutations = []
        for replacement in (
            "http://files.pythonhosted.org/packages/a.whl",
            "https://example.com/packages/a.whl",
            "https://files.pythonhosted.org/packages/../a.whl",
            "https://files.pythonhosted.org/packages/a.whl?download=1",
        ):
            lock = self.load_lock()
            lock["artifacts"][0]["url"] = replacement
            mutations.append(lock)
        lock = self.load_lock()
        lock["artifacts"][0]["filename"] = "../setuptools.whl"
        mutations.append(lock)
        lock = self.load_lock()
        lock["artifacts"][0]["bytes"] = True
        mutations.append(lock)
        lock = self.load_lock()
        for row in lock["artifacts"]:
            row["bytes"] = 3 << 20
        mutations.append(lock)
        for value in mutations:
            with self.subTest(url=value["artifacts"][0].get("url")), self.assertRaises(ValueError):
                scout.validate_dependency_lock(value)

    def test_fetch_requires_exact_payload_identity(self):
        payload = b"locked"
        row = {
            "url": "https://files.pythonhosted.org/packages/aa/locked.whl",
            "filename": "locked.whl",
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

        class Response:
            status = 200
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return row["url"]

            def read(self, limit):
                self.limit = limit
                return payload

        response = Response()
        opener = unittest.mock.Mock()
        opener.open.return_value = response
        with tempfile.TemporaryDirectory(prefix="cm-fetch-") as directory, \
                patch.object(scout, "validate_dependency_lock", return_value={"locked": row}), \
                patch.object(scout.urllib.request, "build_opener", return_value=opener):
            paths = scout.fetch_dependencies(LOCK, Path(directory) / "new")
            self.assertEqual(paths["locked"].read_bytes(), payload)
        self.assertEqual(response.limit, len(payload) + 1)

        bad = copy.deepcopy(row)
        bad["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(prefix="cm-fetch-") as directory, \
                patch.object(scout, "validate_dependency_lock", return_value={"locked": bad}), \
                patch.object(scout.urllib.request, "build_opener", return_value=opener), \
                self.assertRaises(RuntimeError):
            scout.fetch_dependencies(LOCK, Path(directory) / "new")

    def test_built_wheel_metadata_is_checked(self):
        with tempfile.TemporaryDirectory(prefix="cm-wheel-") as directory:
            wheel = Path(directory) / "ply-3.10-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("ply-3.10.dist-info/METADATA", "Metadata-Version: 2.1\nName: ply\nVersion: 3.10\n")
            identity = scout.wheel_metadata(wheel, "ply", "3.10")
            self.assertEqual(identity["sha256"], hashlib.sha256(wheel.read_bytes()).hexdigest())
            with self.assertRaises(ValueError):
                scout.wheel_metadata(wheel, "ply", "3.11")

    def test_cudd_export_preserves_manager_and_shared_dag(self):
        manager = Manager()
        graph = scout.export_cudd_graph(manager, manager.root)
        self.assertEqual(graph["level_of_var"], manager.var_levels)
        self.assertEqual(graph["roots"], [1])
        self.assertEqual(graph["1"], [0, 2, 2])
        self.assertEqual(graph["2"], [1, "F", "T"])
        complemented = scout.export_cudd_graph(manager, manager.root_negated)
        self.assertEqual(complemented["1"], [0, 2, 2])
        self.assertEqual(complemented["2"], [1, "T", "F"])
        foreign = Manager()
        with self.assertRaises(ValueError):
            scout.export_cudd_graph(manager, foreign.root)

    def test_zero_width_cudd_skips_meaningless_reorder(self):
        self.assertEqual(scout.cudd_modes(0), ("fixed",))
        self.assertEqual(scout.cudd_modes(3), ("fixed", "group_sift"))
        for value in (True, -1, 17):
            with self.assertRaises(ValueError):
                scout.cudd_modes(value)

    def test_dimacs_zero_width_and_empty_clause_are_unambiguous(self):
        self.assertEqual(scout._cnf_bytes({"k": 0, "clauses": []}), b"p cnf 0 0\n")
        self.assertEqual(scout._cnf_bytes({"k": 0, "clauses": [[]]}), b"p cnf 0 1\n0\n")
        self.assertEqual(scout._cnf_bytes({"k": 3, "clauses": [[1, -2]]}), b"p cnf 3 1\n1 -2 0\n")

    def test_pinned_d4_is_identified_as_static_elf_without_ldd(self):
        binary = scout.ROOT / scout.D4
        self.assertEqual(scout.sha256_file(binary), scout.D4_SHA256)
        self.assertEqual(scout.elf_linkage_identity(binary), {
            "status": "identified",
            "linkage": "static",
            "program_headers": 10,
            "has_pt_dynamic": False,
            "has_pt_interp": False,
        })
        with tempfile.TemporaryDirectory(prefix="cm-bad-elf-") as directory:
            malformed = Path(directory) / "d4"
            malformed.write_bytes(b"not an ELF")
            with self.assertRaises(ValueError):
                scout.elf_linkage_identity(malformed)

    def test_non_linux_refusal_writes_bounded_evidence_without_setup(self):
        with tempfile.TemporaryDirectory(dir=scout.ROOT, prefix="cm-native-refuse-") as parent:
            output = Path(parent) / "result"
            with patch.object(scout.sys, "platform", "win32"), \
                    patch.object(scout, "install_dependencies") as install:
                summary = scout.run(output, LOCK)
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["error"], "Linux x86-64 required")
            self.assertTrue((output / "summary.json").is_file())
            self.assertTrue((output / "checksums.json").is_file())
            install.assert_not_called()


if __name__ == "__main__":
    unittest.main()
