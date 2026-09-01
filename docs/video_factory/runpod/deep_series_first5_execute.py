"""Execute the exactly approved 17-chapter first-five visual batch on RunPod."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import deep_series_smoke_execute as controller


HERE = Path(__file__).resolve().parent
RUN_ROOT = HERE / "deep_series_first5_v1"
PROPOSAL_ID = "cm-video-deep-series-first5-production-remote-v1"


def configure() -> None:
    record = json.loads((RUN_ROOT / "bundle_record.json").read_text("utf-8"))
    controller.SMOKE_ROOT = RUN_ROOT
    controller.PROPOSAL_ID = PROPOSAL_ID
    controller.AUTHORIZATION_ID = PROPOSAL_ID + "-auth"
    controller.APPROVAL_PATH = (
        HERE.parent / "deep_series" / "first_five_review" / "approval.json"
    )
    controller.APPROVAL_SCOPE = "production_planning_for_first_five_only"
    controller.PROPOSAL_STATUS = "exact_authorization_requested_after_scoped_content_approval"
    controller.POD_NAME_PREFIX = "cm-video-first5-production-v1-"
    controller.RUN_ID_PREFIX = "runpod-first5-production-v1-"
    controller.TOTAL_CAP = 2.0
    controller.MAX_CREATES = 1
    controller.MAX_RUNTIME_SECONDS = 21600
    controller.EXPECTED_JOBS = tuple(record["ordered_job_ids"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run"))
    args = parser.parse_args()
    configure()
    if args.command == "preflight":
        print(json.dumps(controller.preflight(), indent=2))
    else:
        raise SystemExit(controller.run())


if __name__ == "__main__":
    main()
