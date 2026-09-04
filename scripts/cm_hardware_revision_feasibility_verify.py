"""Independently replay a saved hardware-revision feasibility audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import hardware_revision_feasibility as audit  # noqa: E402
from scripts import cm_hardware_revision_feasibility as runner  # noqa: E402


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksums(directory: Path) -> int:
    rows = (directory / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    for row in rows:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Z_]+\.json)", row)
        if not match or audit.sha256_file(directory / match.group(2)) != match.group(1):
            raise ValueError("checksum verification failed")
    return len(rows)


def verify(directory: Path, repositories: Path) -> dict[str, object]:
    checksum_count = verify_checksums(directory)
    manifest = load(directory / "MANIFEST.json")
    for name, digest in manifest["program_files"].items():
        if audit.sha256_file(ROOT / name) != digest:
            raise ValueError("program source changed: " + name)
    replay = audit.run_audit(repositories.resolve(), offline=True)
    saved = load(directory / "AUDIT.json")
    if audit.canonical_bytes(replay) != audit.canonical_bytes(saved):
        raise ValueError("audit replay mismatch")
    summary = audit.summarize(replay)
    if audit.canonical_bytes(summary) != audit.canonical_bytes(load(directory / "SUMMARY.json")):
        raise ValueError("summary replay mismatch")
    final_status = "admissible" if summary["status_without_replay"] == "admissible_pending_replay" else summary["status_without_replay"]
    return {
        "schema": "cm-hardware-revision-feasibility-independent-verification/v1",
        "status": "passed",
        "checksum_files_verified": checksum_count,
        "repositories_replayed": len(replay["repositories"]),
        "transitions_replayed": sum(len(row.get("transitions", [])) for row in replay["repositories"]),
        "selection_hash_metric_mismatches": 0,
        "summary_reproduced": True,
        "final_admission_status": final_status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repositories", type=Path,
                        default=ROOT / "tmp/cm-hardware-revision-feasibility/repositories")
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args(argv)
    result = verify(arguments.run.resolve(), arguments.repositories.resolve())
    if arguments.write:
        path = arguments.run.resolve() / "INDEPENDENT_VERIFICATION.json"
        runner.write_json(path, result)
        runner.write_checksums(arguments.run.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
