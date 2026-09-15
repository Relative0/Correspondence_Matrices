"""Standalone neural publication package: local preparation, never deployment."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("neural_export", ROOT / "scripts/cm_neural_site_export.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class NeuralSiteExportTests(unittest.TestCase):
    def test_self_contained_home_sources_and_no_overwrite(self):
        (ROOT / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="neural-export-test-", dir=ROOT / "build") as temporary:
            target = Path(temporary) / "package"
            result = exporter.export(target)
            public = target / "_site"
            page = (public / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page, (public / "learning-neural-evidence.html").read_text(encoding="utf-8"))
            self.assertNotIn("This source template is populated", page)
            self.assertIn('return "evidence/" + href.slice(6)', page)
            self.assertIn(exporter.MAIN + "index.html", page)
            self.assertIn(exporter.MAIN + "latest-results.html", page)
            self.assertIn(exporter.MAIN + "data-downloads.html#september-16-confirmation", page)
            self.assertIn("2026-09-11", page)
            manifest = json.loads((public / "publication-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["target"], exporter.TARGET)
            self.assertEqual(manifest["publication_status"], "prepared_not_published")
            for relative, record in manifest["files"].items():
                payload = (public / relative).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])
                self.assertEqual(len(payload), record["bytes"])
            evidence = json.loads((exporter.SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))["e22_learning_neural"]
            for relative in exporter.evidence_paths(evidence):
                self.assertEqual((public / "evidence" / relative).read_bytes(), (ROOT / relative).read_bytes())
            with self.assertRaisesRegex(ValueError, "new directory"):
                exporter.export(target)

    def test_export_refuses_outside_build(self):
        with self.assertRaisesRegex(ValueError, "new directory"):
            exporter.export(ROOT / "not-an-export-target")


if __name__ == "__main__":
    unittest.main()
