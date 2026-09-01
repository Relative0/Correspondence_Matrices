"""Build the exact local-only 17-chapter first-five RunPod visual bundle."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

import deep_series_smoke_package as package


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
DEEP_ROOT = FACTORY / "deep_series"
OUTPUT_ROOT = HERE / "deep_series_first5_v1"
PROPOSAL_ID = "cm-video-deep-series-first5-production-remote-v1"
BATCH_ID = "cm-video-deep-series-first5-production-v1"
PACKAGE_ID = "cm-video-deep-series-first5-production-linux-v1"
BUNDLE_STEM = "cm-video-deep-series-first5-production-v1"
FIRST_FIVE = (
    "conceptual-vs-measured",
    "why-boolean-computation",
    "expression-truth-function",
    "live-support-ambient",
    "what-is-explicit-cm",
)
PACKAGE_CONFIGURATION_FIELDS = (
    "OUTPUT_ROOT",
    "PROPOSAL_ID",
    "BATCH_ID",
    "PACKAGE_ID",
    "BUNDLE_STEM",
    "JOB_SUFFIX",
    "REVIEW_PATH",
    "REQUIRED_REVIEW_STATUS",
    "TARGETS",
)


def configure() -> None:
    targets = []
    for video_id in FIRST_FIVE:
        chapter_root = DEEP_ROOT / "episodes" / video_id / "chapters"
        targets.extend((video_id, path.name) for path in sorted(chapter_root.iterdir()) if path.is_dir())
    package.OUTPUT_ROOT = OUTPUT_ROOT
    package.PROPOSAL_ID = PROPOSAL_ID
    package.BATCH_ID = BATCH_ID
    package.PACKAGE_ID = PACKAGE_ID
    package.BUNDLE_STEM = BUNDLE_STEM
    package.JOB_SUFFIX = "production"
    package.REVIEW_PATH = DEEP_ROOT / "first_five_review" / "manifest.json"
    package.REQUIRED_REVIEW_STATUS = "review_requested_first_five_only"
    package.TARGETS = tuple(targets)


@contextmanager
def configured() -> Iterator[None]:
    prior = {name: getattr(package, name) for name in PACKAGE_CONFIGURATION_FIELDS}
    configure()
    try:
        yield
    finally:
        for name, value in prior.items():
            setattr(package, name, value)


def build(pop_root: Path) -> dict:
    with configured():
        return package.build(pop_root.resolve(), OUTPUT_ROOT)


def validate() -> None:
    with configured():
        package.validate(OUTPUT_ROOT)
    record = json.loads((OUTPUT_ROOT / "bundle_record.json").read_text("utf-8"))
    if len(record["ordered_job_ids"]) != 17:
        raise ValueError("first-five production bundle must contain 17 chapters")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--pop-root", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        if args.pop_root is None:
            parser.error("build requires --pop-root")
        print(json.dumps(build(args.pop_root), indent=2))
    else:
        validate()


if __name__ == "__main__":
    main()
