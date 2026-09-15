import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.crse_prepare_c7_linux_confirmation import FILES, IMAGE, NUMPY, OUTPUT
from scripts.crse_yosys_source_anf_linux_confirmation import EXPECTED_DATASET_SHA256, run

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs" / "recognition" / "runs" / "yosys-source-anf-confirmation-20260830-002" / "dataset.json"
PROTOCOL = ROOT / "docs" / "recognition" / "c7_linux_confirmation" / "C7_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"


class C7LinuxConfirmationTests(unittest.TestCase):
    def test_upload_manifest_is_exact_and_minimal(self):
        manifest = json.loads(OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "crse-c7-linux-confirmation-upload-manifest/v1")
        self.assertEqual(manifest["authorization_status"], "pending")
        self.assertEqual(manifest["file_count"], 14)
        self.assertEqual(manifest["bytes"], 322080)
        self.assertEqual(len(manifest["files"]), len(FILES))
        self.assertEqual(manifest["runtime"]["image"], IMAGE)
        self.assertEqual(manifest["runtime"]["numpy_requirement"], NUMPY)
        self.assertFalse(manifest["network_during_workload"])
        for row, (source, target) in zip(manifest["files"], FILES):
            self.assertEqual(row["source"], source)
            self.assertEqual(row["target"], target)
            self.assertGreater(row["bytes"], 0)
            self.assertEqual(len(row["sha256"]), 64)
            int(row["sha256"], 16)
        self.assertEqual(manifest["bytes"], sum(row["bytes"] for row in manifest["files"]))
        self.assertIn("322,080 source bytes", PROTOCOL.read_text(encoding="utf-8"))

    def test_portable_workload_replays_exactly(self):
        self.assertEqual(hashlib.sha256(DATASET.read_bytes()).hexdigest(), EXPECTED_DATASET_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            result = run(DATASET, output, repetitions=5)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertTrue(result["criteria"]["exact"])
            self.assertEqual(len(json.loads((output / "per_case.json").read_text())), 240)
            self.assertEqual(len((output / "measurements.jsonl").read_text().splitlines()), 1200)


if __name__ == "__main__":
    unittest.main()
