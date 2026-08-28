"""Local publication checks: no credentials, network, cloud jobs or git writes."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
import warnings
import zipfile
import re
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_publication", ROOT / "scripts/cm_research_publication.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class ResearchPublicationTests(unittest.TestCase):
    def test_private_temporary_unrelated_and_traversal_paths_are_excluded(self):
        for path in (".env", "a/.env.runpod.local", "a/.env.example", "x/id_rsa", "keys/private.pem",
                     "tmp/run.json", "external/repo/file.py", ".claude/settings.json",
                     "a/.pytest_final/state.json", "a/http-fake-checks-123/RUN.json",
                     "a/pytest-tmp/temporary.json", "a/pytest-temp/temporary.json",
                     "a/controller-unit-fixtures/RUN.json", "a/RUNPOD-SUPPORT-DRAFT.md",
                     "a/The Broken Silence.html", "../secret.json", "C:/secret.json",
                     "docs/research/downloads/archive.zip"):
            with self.subTest(path=path):
                self.assertTrue(publication.excluded(path))

    def test_named_scientific_evidence_and_source_are_allowed(self):
        for path in ("docs/audits/run/focused.xml", "runs/summary.json", "runs/source_snapshot/cm_ir.py",
                     "docs/runpod/RUNPOD-SETUP-HANDOFF-2026-08-28.md", "tests/test_output_budget.py"):
            self.assertFalse(publication.excluded(path))

    def test_secret_signature_errors_do_not_echo_values(self):
        secret = b"rpa_" + b"X" * 36
        with self.assertRaises(ValueError) as error:
            publication.scan_bytes("report.txt", secret)
        self.assertNotIn(secret.decode(), str(error.exception))
        self.assertIn("report.txt", str(error.exception))

    def test_sensitive_json_fields_are_refused_but_fake_fixtures_are_allowed(self):
        for key in ("RUNPOD_API_KEY", "Authorization", "access_token", "CM_BOOTSTRAP_TOKEN"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                publication.scan_bytes("record.json", json.dumps({"nested": {key: "unapproved-value"}}).encode())
        publication.scan_bytes("fake.json", b'{"RUNPOD_API_KEY":"OFFLINE_SENTINEL"}')
        publication.scan_bytes("safe.json", b'{"api_key":null,"credential_available":true}')

    def test_excluded_file_refused_before_content_processing(self):
        with self.assertRaisesRegex(ValueError, "excluded publication path"):
            publication.scan_bytes(".env.runpod", b"never inspect")

    def archive(self, entries):
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w") as archive:
                for name, data in entries:
                    archive.writestr(name, data)
        return stream.getvalue()

    def test_archive_members_are_scanned_and_path_traversal_refused(self):
        publication.scan_bytes("evidence.zip", self.archive([("run/result.json", b'{"status":"ok"}')]))
        for entries in ([('../escape.txt', b'no')], [('a/.env', b'no')],
                        [('data.json', b'{"api_key":"unapproved"}')],
                        [('x.txt', b'first'), ('x.txt', b'second')]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                publication.scan_bytes("evidence.zip", self.archive(entries))

    def test_archive_symlinks_refused(self):
        info = zipfile.ZipInfo("link")
        info.external_attr = 0o120777 << 16
        with self.assertRaisesRegex(ValueError, "symlink"):
            publication.scan_bytes("evidence.zip", self.archive([(info, b"target")]))

    def test_nested_archive_limit(self):
        data = self.archive([("result.txt", b"ok")])
        for _ in range(3):
            data = self.archive([("nested.zip", data)])
        with self.assertRaisesRegex(ValueError, "depth"):
            publication.scan_bytes("evidence.zip", data)

    def test_html_prose_converts_to_readable_markdown_and_relative_links(self):
        parser = publication.InlineMarkdown(publication.SITE / "data.json", publication.READERS / "USE.md")
        parser.feed('A <em>bounded</em> <strong>test</strong> with <code>k</code> &amp; <a href="expert.html">detail</a>.')
        output = ''.join(parser.parts)
        self.assertIn('A *bounded* **test** with `k` &', output)
        self.assertIn('../../../deliverables_n22_24/master_explainer_2026_08_03/expert.html', output)

    def test_absolute_project_links_become_portable(self):
        target = "C:/Users/brian/Documents/CM_Computation/docs/runpod/report.md"
        self.assertEqual(publication.local_link(target, Path("docs/runpod/source.md"),
                                                publication.READERS / "OUT.md"), "../../runpod/report.md")

    def test_superscripts_and_spaces_in_links_are_preserved(self):
        parser = publication.InlineMarkdown(publication.SITE / "data.json", publication.READERS / "OUT.md")
        parser.feed('2<sup>k</sup> and x<sub>0</sub>; <a href="a file.pdf">paper</a>')
        text = ''.join(parser.parts)
        self.assertIn('2<sup>k</sup>', text)
        self.assertIn('x<sub>0</sub>', text)
        self.assertIn('a%20file.pdf', text)

    def test_research_index_and_readers_have_resolving_local_links(self):
        documents = publication.reading_editions()
        documents[Path('docs/research/README.md')] = (ROOT / 'docs/research/README.md').read_text(encoding='utf-8')
        for path, text in documents.items():
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if target.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                target = unquote(target.split('#')[0].split('?')[0])
                with self.subTest(path=path, target=target):
                    self.assertTrue(((ROOT / path).parent / target).exists())

    def test_number_formats_preserve_units(self):
        for fmt, value, expected in (("ratio3", 0.88765, "0.888"), ("int", 5591040, "5,591,040"),
                                     ("pctsign2", 2.25, "+2.25%"), ("num1s", 78, "78"),
                                     ("us0", 1234, "1.23 ms"), ("usd", 0.00167, "$0.0017")):
            self.assertEqual(publication.format_number({"value": value, "fmt": fmt}), expected)
        with self.assertRaises(ValueError):
            publication.format_number({"value": 1, "fmt": "unrecognized"})

    def test_unknown_number_token_refuses_generation(self):
        with self.assertRaises(KeyError):
            publication.reader("Test", {"evidence": "{{missing}}"}, {}, publication.READERS / "X.md")

    def test_reading_editions_cover_all_cases_and_preserve_provenance(self):
        editions = publication.reading_editions()
        self.assertEqual(len(editions), 6)
        cases = editions[publication.READERS / "CM-USE-CASES.md"]
        for title in ("Hardware verification", "Artificial intelligence", "Computational biology",
                      "Quantum-computing", "Compilers", "Security policy", "Configuration systems", "Regulated"):
            self.assertIn(title, cases)
        self.assertIn("real feature-model slices", cases)
        for text in editions.values():
            self.assertNotIn("{{", text)
            self.assertNotIn("](C:/Users/", text)
            self.assertFalse(re.search(r'[ \t]+$', text, flags=re.MULTILINE))
        self.assertIn("Named-number provenance", editions[publication.READERS / "MASTER-EXPLAINER.md"])


if __name__ == "__main__":
    unittest.main()
