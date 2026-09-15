import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214"
)
PACKAGE = ROOT / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01"
SCRIPT = BASE / "freeze_p7_w5_development_v1.py"
SPEC = importlib.util.spec_from_file_location("freeze_p7_w5", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class W5FreezeTests(unittest.TestCase):
    def test_balanced_partition_is_complete_and_timing_independent(self):
        parent = MODULE.load(MODULE.PARENT_PATH)
        w3 = MODULE.load(MODULE.W3_AUDIT_PATH)
        w4 = MODULE.load(MODULE.W4_NOISE_PATH)
        eligible, shard_a, shard_b, ledger = MODULE.validate_inputs(parent, w3, w4)
        self.assertEqual((len(eligible), len(shard_a), len(shard_b)), (57, 29, 28))
        self.assertEqual(set(shard_a) | set(shard_b), set(eligible))
        self.assertFalse(set(shard_a) & set(shard_b))
        self.assertNotIn(MODULE.TYPED_EXCLUSION, eligible)
        self.assertEqual({row["shard"] for row in ledger}, {"a", "b"})

    def test_frozen_package_contract(self):
        campaign = json.loads((PACKAGE / "campaign.json").read_text(encoding="utf-8"))
        verification = json.loads((PACKAGE / "verification.json").read_text(encoding="utf-8"))
        self.assertTrue(verification["verified"])
        self.assertEqual(campaign["parent_eligible_cases"], 58)
        self.assertEqual(campaign["principal_cases"], 57)
        self.assertEqual(campaign["primary_cells"], 7524)
        self.assertEqual(campaign["total_cells_including_repeated_per_allocation_anchors"], 7852)
        primary = {
            row["partition_id"]: row["planned_cells"]
            for row in campaign["definitions"]
            if row["kind"] == "primary"
        }
        self.assertEqual(
            primary,
            {"p7-ir-a": 928, "p7-ir-b": 896, "p7-relation-a": 2900, "p7-relation-b": 2800},
        )

    def test_all_derived_freezes_validate_and_bind_campaign_hashes(self):
        from cmbench.comparative.corpus_freeze import validate_freeze, verify_sources

        campaign = json.loads((PACKAGE / "campaign.json").read_text(encoding="utf-8"))
        for row in campaign["definitions"]:
            freeze = json.loads(
                (PACKAGE / row["partition_id"] / "freeze.json").read_text(encoding="utf-8")
            )
            validate_freeze(freeze)
            self.assertEqual(freeze["freeze_sha256"], row["freeze_sha256"])
            self.assertTrue(verify_sources(freeze, ROOT)["verified"])
            self.assertEqual(len(freeze["cases"]), row["case_count"])
            self.assertEqual(len(freeze["schedule_policies"]), 1)
            self.assertEqual(freeze["schedule_policies"][0]["policy_id"], row["policy_id"])


if __name__ == "__main__":
    unittest.main()
