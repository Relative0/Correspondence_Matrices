"""Offline inventory must not turn setup diagnosis into credential/cloud access."""

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import cm_runpod_readiness as readiness


class NamesOnly:
    def __iter__(self):
        return iter(("RUNPOD_API_KEY", "RUNPOD_POD_ID"))

    def __getitem__(self, key):
        raise AssertionError("environment value accessed")


class RunpodReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def inventory(self, names=()):
        with patch.object(readiness, "git_identity", return_value={"head": "unavailable"}):
            return readiness.inventory(self.root, names)

    def test_credential_files_are_never_opened(self):
        for relative in readiness.CREDENTIAL_CANDIDATES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("RUNPOD_API_KEY=CANARY_NEVER_PRINT_ME\n", encoding="utf-8")
        # Distribution METADATA is an allowed read; mock it so the remaining
        # inventory can be held to an even stronger no-file-open assertion.
        with patch.object(readiness.importlib.metadata, "version", return_value="test"), patch.object(Path, "open", side_effect=AssertionError("file opened")):
            report = self.inventory()
        self.assertTrue(all(row["status"] == "regular_file" for row in report["credential_file_metadata_only"]))
        self.assertNotIn("CANARY_NEVER_PRINT_ME", json.dumps(report))
        self.assertFalse(report["credential_contents_read"])

    def test_environment_values_are_never_requested(self):
        report = self.inventory(NamesOnly())
        self.assertTrue(report["process_environment_names_present"]["RUNPOD_API_KEY"])
        self.assertFalse(report["process_environment_names_present"]["RP_TOKEN"])
        self.assertFalse(report["environment_values_read"])

    def test_default_environment_iteration_does_not_index_values(self):
        with patch.object(readiness.os, "environ", NamesOnly()):
            report = self.inventory(None)
        self.assertTrue(report["process_environment_names_present"]["RUNPOD_POD_ID"])

    def test_inventory_does_not_certify_connectivity(self):
        report = self.inventory()
        self.assertIn("not_connection_validation", report["assessment"])
        for field in ("network_requests_performed", "authenticated_connectivity_tested", "resource_mutations_performed"):
            self.assertIs(report[field], False)
        self.assertTrue(all(row["status"] == "missing" for row in report["credential_file_metadata_only"]))

    def test_distinct_workflows_keep_distinct_credential_locations(self):
        workflows = self.inventory()["workflow_configuration"]
        self.assertTrue(workflows["older_existing_worker_client"]["process_environment_overrides_files"])
        smoke = workflows["memory_smoke_controller"]
        self.assertEqual(smoke["credential_path"], str(self.root / readiness.CAMPAIGN / ".env.runpod.local"))
        self.assertFalse(smoke["uses_root_dotenv_or_process_environment_for_key"])
        self.assertFalse(smoke["existing_pod_id_required"])

    def test_source_hashes_are_allowlisted_code_only(self):
        relative = Path("cm_runpod_config.py")
        payload = b"# test source only\n"
        (self.root / relative).write_bytes(payload)
        row = readiness.source_record(self.root, relative)
        self.assertEqual(row["sha256"], hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError, "allowlist"):
            readiness.source_record(self.root, Path(".env.runpod"))

    def test_linked_source_is_not_read(self):
        relative = Path("cm_runpod_config.py")
        (self.root / relative).write_text("# source", encoding="utf-8")
        with patch.object(readiness, "_has_link_parent", return_value=True), patch.object(Path, "read_bytes", side_effect=AssertionError("read")):
            row = readiness.source_record(self.root, relative)
        self.assertEqual(row["status"], "linked_source_refused")
        self.assertNotIn("sha256", row)

    def test_sources_that_change_are_not_hashed_as_stable(self):
        relative = Path("cm_runpod_config.py")
        path = self.root / relative
        path.write_bytes(b"before")
        original = Path.read_bytes

        def changed(target):
            payload = original(target)
            target.write_bytes(b"after, with different size")
            return payload

        with patch.object(Path, "read_bytes", changed):
            row = readiness.source_record(self.root, relative)
        self.assertEqual(row["status"], "changed_during_read")
        self.assertNotIn("sha256", row)

    def test_report_is_created_exclusively(self):
        report = {"schema": "unit-test", "credential_contents_read": False}
        target = readiness.write_report(self.root, Path("reports/setup.json"), report)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
        with self.assertRaises(FileExistsError):
            readiness.write_report(self.root, target, {"replacement": True})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)

    def test_report_refuses_sensitive_and_outside_paths(self):
        for target in (Path(".env.runpod.json"), Path(".git/config.json"), Path("report.txt"), Path("../escape.json"), self.root.parent / "escape.json"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                readiness.write_report(self.root, target, {})

    def test_report_refuses_links(self):
        with patch.object(readiness, "_has_link_parent", return_value=True), self.assertRaises(ValueError):
            readiness.write_report(self.root, Path("report.json"), {})

    def test_package_metadata_is_not_native_backend_validation(self):
        with patch.object(readiness.importlib.metadata, "version", side_effect=readiness.importlib.metadata.PackageNotFoundError):
            report = self.inventory()
        self.assertFalse(report["runtime"]["native_backends_imported_or_tested"])
        self.assertTrue(all(value.startswith("not_installed") for value in report["runtime"]["package_metadata_versions"].values()))

    def test_git_only_runs_read_only_identity_commands(self):
        result = subprocess.CompletedProcess([], 0, "a" * 40, "ignored stderr")
        with patch.object(readiness.subprocess, "run", return_value=result) as run:
            readiness.git_identity(self.root)
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.args[0][:4], ["git", "-c", "core.fsmonitor=false", "rev-parse"])
            self.assertIn(call.args[0][-1], ("HEAD", "--show-toplevel"))
            self.assertEqual(call.kwargs["timeout"], 5)

    def test_git_errors_are_not_echoed(self):
        result = subprocess.CompletedProcess([], 1, "CANARY_SECRET", "CANARY_SECRET")
        with patch.object(readiness.subprocess, "run", return_value=result):
            self.assertNotIn("CANARY_SECRET", json.dumps(readiness.git_identity(self.root)))

    def test_cli_has_no_network_or_launch_switch(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            readiness.main(["--launch"])

    def test_cli_prints_valid_json_without_writing_by_default(self):
        with patch.object(readiness, "inventory", return_value={"safe": True}), patch.object(readiness, "write_report", side_effect=AssertionError("write")), contextlib.redirect_stdout(io.StringIO()) as stream:
            code = readiness.main(["--project-root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue()), {"safe": True})


if __name__ == "__main__":
    unittest.main()
