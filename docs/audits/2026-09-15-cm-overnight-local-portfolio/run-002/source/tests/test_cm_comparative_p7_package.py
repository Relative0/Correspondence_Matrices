from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import cm_comparative_p7_package as package


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"


class ComparativeP7PackageTests(unittest.TestCase):
    def test_dependency_closure_includes_known_runtime_imports(self):
        paths = package.dependency_closed_paths(ROOT, {"cmbench/comparative/p7.py", "cm_ir.py"})
        self.assertIn("cmbench/recognition/features.py", paths)
        self.assertIn("cmbench/recognition/__init__.py", paths)
        self.assertIn("cmbench/backends/bitset_engine.py", paths)
        self.assertIn("cmbench/backends/__init__.py", paths)

    def test_secret_like_and_escaping_paths_are_refused(self):
        for value in ("../outside.py", ".env", "keys/private.pem", "/absolute.py"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    package._safe_relative(value)

    def test_frozen_sources_are_unique_safe_project_files(self):
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        paths = package._freeze_sources(freeze)
        self.assertEqual(len(paths), 57)
        self.assertTrue(all((ROOT / value).is_file() for value in paths))


if __name__ == "__main__":
    unittest.main()
