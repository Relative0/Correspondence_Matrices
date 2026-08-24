"""Three-pod guarded replication of the frozen k=13..15 selector study."""
from __future__ import annotations

from pathlib import Path

import cm_selector_runpod_campaign_2026_08_24 as campaign

BASE = Path(__file__).resolve().parent
campaign.OUT_DIR = BASE / "selector_gap_runpod_2026_08_24"
campaign.CAMPAIGN_NAME = "CM k=13..15 selector-gap Runpod replication 2026-08-24"
campaign.WORKER_FILENAME = "cm_selector_gap_runpod_worker_2026_08_24.py"
campaign.AUDIT_FILENAME = "selector_gap_runpod_audit_2026_08_24.json"
campaign.PRIOR_ATTEMPT_COST_RESERVE_USD = 0.016774
campaign.ARCHIVE_PATHS += (
    "scripts/cm_selector_gap_study.py",
    "deliverables_n22_24/followups_2026_08_24/selector_gap/selector_gap_corpus.jsonl",
)


if __name__ == "__main__":
    raise SystemExit(campaign.main())
