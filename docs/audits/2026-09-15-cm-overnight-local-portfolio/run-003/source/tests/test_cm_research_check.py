"""Bounded checks of the reproducibility harness; never recurse into its suite runner."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from scripts import cm_research_check as check


class ResearchCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cm-repro-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_archive(self, extra=(), change=None):
        data = b"public fixture\n"
        manifest = {"schema": "cm-research-source/v1", "files": [
            {"path": "README.md", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}
        if change:
            change(manifest)
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w") as archive:
                archive.comment = check.SOURCE_COMMIT.encode()
                archive.writestr("snapshot/README.md", data)
                archive.writestr("snapshot/" + check.MANIFEST.as_posix(), json.dumps(manifest))
                for name, payload in extra:
                    archive.writestr(name, payload)
        return stream.getvalue()

    def verify_payload(self, payload):
        path = self.root / "fixture.zip"
        path.write_bytes(payload)
        return check.verify_archive(path, hashlib.sha256(payload).hexdigest())

    def test_valid_archive_requires_hash_commit_membership_and_payload_agreement(self):
        result = self.verify_payload(self.make_archive())
        self.assertEqual(result["source_files"], 1)
        self.assertEqual(result["total_files"], 2)
        with self.assertRaisesRegex(ValueError, "SHA-256 changed"):
            check.verify_archive(self.root / "fixture.zip", "0" * 64)
        with self.assertRaisesRegex(ValueError, "commit mismatch"):
            check.verify_archive(self.root / "fixture.zip", result["sha256"], "0" * 40)

    def test_ambiguous_traversal_reserved_and_control_paths_are_refused(self):
        for name in ("../x", "/x", "a/../x", "a//x", "a/./x", "a\\x", "C:/x", "a/CON.txt",
                     "a/trailing.", "a/trailing ", "a/x\n", "a/file:stream", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check.safe_member(name)

    def test_duplicate_case_alias_extra_file_and_other_root_are_refused(self):
        for name in ("snapshot/README.md", "snapshot/readme.md", "snapshot/extra.txt", "elsewhere/extra.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify_payload(self.make_archive([(name, b"extra")]))

    def test_symlinks_and_file_directory_collisions_are_refused(self):
        link = zipfile.ZipInfo("snapshot/link")
        link.external_attr = 0o120777 << 16
        for extra in ([(link, b"README.md")], [("snapshot/README.md/child", b"x")]):
            with self.assertRaises(ValueError):
                self.verify_payload(self.make_archive(extra))

    def test_missing_modified_duplicate_and_malformed_manifest_rows_are_refused(self):
        changes = [lambda m: m["files"][0].update(sha256="0" * 64),
                   lambda m: m["files"][0].update(bytes=True),
                   lambda m: m["files"][0].update(path="missing.txt"),
                   lambda m: m["files"].append(dict(m["files"][0])),
                   lambda m: m.update(schema="unknown"), lambda m: m.update(files=[])]
        for change in changes:
            with self.assertRaises(ValueError):
                self.verify_payload(self.make_archive(change=change))

    def test_archive_expansion_limit_precedes_extraction(self):
        with patch.object(check, "MAX_EXPANSION", 1), self.assertRaisesRegex(ValueError, "expansion"):
            self.verify_payload(self.make_archive())

    def test_unverified_zip_cannot_create_extraction_directory(self):
        path = self.root / "untrusted.zip"
        path.write_bytes(self.make_archive())
        destination = self.root / "extract"
        with self.assertRaisesRegex(ValueError, "SHA-256 changed"):
            check.extract_verified(path, destination)
        self.assertFalse(destination.exists())

    def test_skips_empty_suites_expected_failures_and_invalid_counts_are_not_success(self):
        good = {"tests": 1, "failures": 0, "errors": 0, "skipped": 0,
                "expected_failures": 0, "unexpected_successes": 0}
        self.assertTrue(check.successful_suite(good))
        for key in good:
            changed = {**good, key: 0 if key == "tests" else 1}
            self.assertFalse(check.successful_suite(changed))
        self.assertFalse(check.successful_suite({**good, "tests": True}))
        self.assertFalse(check.successful_suite(None))
        forged = {**good, "status": "passed", "suite": "unapproved"}
        self.assertFalse(check.successful_suite(forged))
        response = subprocess.CompletedProcess([], 1, json.dumps(forged).encode(), b"")
        with patch.object(check.subprocess, "run", return_value=response):
            self.assertEqual(check.run_suite(self.root, check.BASE_SUITES[0])["status"], "failed")

    def test_suite_allowlist_and_network_guard_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            check.suite_worker(self.root, "test_*.py")
        for event in ("socket.connect", "socket.bind", "socket.getaddrinfo"):
            with self.assertRaises(RuntimeError):
                check.offline_guard(event, ())
        check.offline_guard("open", ())

    def test_report_paths_are_new_project_tmp_json_without_links(self):
        with patch.object(check, "ROOT", self.root):
            for path in (self.root / "report.json", self.root / "tmp/report.txt", self.root / "tmp/../report.json"):
                with self.assertRaises(ValueError):
                    check.report_target(path)
            target = self.root / "tmp/report.json"
            self.assertEqual(check.report_target(target), target)
            evidence = self.root / "docs/research/verification/check.json"
            self.assertEqual(check.report_target(evidence), evidence)
            target.parent.mkdir()
            target.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                check.report_target(target)

    def test_workflow_is_read_only_pinned_and_has_both_platforms(self):
        workflow = (check.ROOT / ".github/workflows/research-checks.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("ubuntu-24.04", workflow)
        self.assertIn("windows-2025", workflow)
        self.assertIn("core.longpaths", workflow)
        self.assertIn("--only-binary=:all:", workflow)
        self.assertEqual(len(re.findall(r"uses: actions/[\w-]+@[0-9a-f]{40}\b", workflow)), 3)
        for forbidden in ("pull_request_target:", "workflow_run:", "secrets.", "write-all", "contents: write",
                          "git push", "runpod.io", "deploy-pages", "upload-artifact"):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
