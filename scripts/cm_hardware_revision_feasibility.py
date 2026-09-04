"""Run the frozen, non-timed hardware-revision feasibility audit."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import hardware_revision_feasibility as audit  # noqa: E402


PROTOCOL = ROOT / "docs/research/CM_HARDWARE_REVISION_FEASIBILITY_PROTOCOL_2026_09_04.md"
PROGRAM_PATHS = (
    "cmbench/comparative/hardware_revision_feasibility.py",
    "scripts/cm_hardware_revision_feasibility.py",
    "scripts/cm_hardware_revision_feasibility_verify.py",
    "docs/research/CM_HARDWARE_REVISION_FEASIBILITY_PROTOCOL_2026_09_04.md",
)


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def checksum_rows(directory: Path) -> list[dict[str, object]]:
    names = ("AUDIT.json", "INDEPENDENT_VERIFICATION.json", "INVENTORY.json", "MANIFEST.json", "SUMMARY.json")
    return [{"path": name, "bytes": (directory / name).stat().st_size,
             "sha256": audit.sha256_file(directory / name)}
            for name in names if (directory / name).is_file()]


def write_checksums(directory: Path) -> None:
    path = directory / "CHECKSUMS.sha256"
    content = "".join(f"{row['sha256']}  {row['path']}\n" for row in checksum_rows(directory))
    if path.exists():
        path.write_text(content, encoding="utf-8", newline="\n")
    else:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repositories", type=Path,
                        default=ROOT / "tmp/cm-hardware-revision-feasibility/repositories")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    output = arguments.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "docs/research/verification"):
        raise ValueError("output must be a new directory under docs/research/verification")
    for name in PROGRAM_PATHS:
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--", name], cwd=ROOT, check=True)
    output.mkdir(parents=True)
    evidence = audit.run_audit(arguments.repositories.resolve())
    summary = audit.summarize(evidence)
    manifest = {
        "schema": "cm-hardware-revision-feasibility-manifest/v1",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
                     "sha256": audit.sha256_file(PROTOCOL)},
        "program_files": {name: audit.sha256_file(ROOT / name) for name in PROGRAM_PATHS},
        "candidate_repositories": list(audit.CANDIDATES),
        "cutoff": audit.CUTOFF,
        "maximum_transitions_per_repository": audit.MAX_TRANSITIONS,
        "clone_command": "git clone --filter=blob:none --no-checkout <public-url> <ignored-project-tmp-directory>",
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "git": subprocess.check_output(["git", "--version"], text=True).strip()},
        "performance_measurement": False,
        "network_during_audit": "partial-clone object acquisition permitted; independent replay disables lazy fetch",
    }
    write_json(output / "AUDIT.json", evidence)
    write_json(output / "SUMMARY.json", summary)
    write_json(output / "MANIFEST.json", manifest)
    inventory = {"schema": "cm-hardware-revision-feasibility-inventory/v1",
                 "files": checksum_rows(output)}
    write_json(output / "INVENTORY.json", inventory)
    write_checksums(output)
    print(json.dumps({"output": str(output), "status_without_replay": summary["status_without_replay"],
                      "repositories": len(evidence["repositories"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
