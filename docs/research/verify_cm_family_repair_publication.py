"""Verify committed repair evidence without replaying its pre-commit Git state.

Read-only, standard-library verifier. Raw evidence bytes remain exact. Source
checkout bytes may differ solely by CRLF/LF conversion; the publication record
binds both the measurement hashes and committed source blobs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
RECORD = HERE / "CM_FAMILY_REPAIR_PUBLICATION_2026_09_15.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root, record, check_local_predecessors=False):
    root = Path(root).resolve()
    commit = record["repair_commit"]
    audit_name = record["audit_directory"]
    audit = root / audit_name

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    def blob(name):
        return git("show", f"{commit}:{name}")

    require(git("rev-parse", f"{commit}^{{commit}}").decode().strip() == commit,
            "repair commit must be an exact, available commit")
    require(git("rev-parse", f"{commit}^").decode().strip() == record["parent_commit"],
            "repair parent differs")
    manifest_bytes = blob(audit_name + "/AUDIT_MANIFEST.json")
    require(sha(manifest_bytes) == record["manifest_sha256"], "manifest hash differs")
    manifest = json.loads(manifest_bytes)
    seal = blob(audit_name + "/AUDIT_MANIFEST.sha256")
    require(seal.decode().split()[0] == sha(manifest_bytes), "detached seal differs")
    artifacts = manifest["artifacts"]
    expected = set(artifacts) | {"AUDIT_MANIFEST.json", "AUDIT_MANIFEST.sha256"}
    actual = {p.relative_to(audit).as_posix() for p in audit.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    require(actual == expected, "audit file inventory differs")
    for name in sorted(expected):
        data = blob(audit_name + "/" + name)
        require((audit / name).read_bytes() == data, f"checkout evidence differs: {name}")
        if name in artifacts:
            entry = artifacts[name]
            require(sha(data) == entry["sha256"] and len(data) == entry["bytes"],
                    f"sealed artifact differs: {name}")

    require(set(record["sources"]) == set(manifest["sources"]), "source inventory differs")
    source_treatments = {}
    for name, binding in record["sources"].items():
        require(binding["measurement_sha256"] == manifest["sources"][name],
                f"measurement binding differs: {name}")
        data = blob(name)
        require(sha(data) == binding["commit_blob_sha256"], f"committed source differs: {name}")
        normalized = data.replace(b"\r\n", b"\n")
        require(sha(normalized) == binding["lf_sha256"], f"normalized binding differs: {name}")
        working = (root / name).read_bytes()
        require(working.replace(b"\r\n", b"\n") == normalized, f"working source differs: {name}")
        source_treatments[name] = (
            "exact measurement bytes" if sha(working) == binding["measurement_sha256"]
            else "LF-equivalent to committed source; historical raw hash retained"
        )

    predecessor_files = 0
    if check_local_predecessors:
        for entry in manifest["predecessors"]:
            require(sha(Path(entry["path"]).read_bytes()) == entry["sha256"],
                    f"local predecessor differs: {entry['path']}")
            predecessor_files += 1
        checkpoint = json.loads(blob(audit_name + "/PRESERVATION.json"))
        evidence = Path(record["local_evidence_worktree"]) / "docs/audits"
        for folder, files in checkpoint["evidence"].items():
            for name, digest in files.items():
                require(sha((evidence / folder / name).read_bytes()) == digest,
                        f"local evidence differs: {folder}/{name}")
                predecessor_files += 1

    return {
        "repair_commit": commit, "verified_artifacts": len(artifacts),
        "manifest_and_seal": "exact committed and checkout bytes",
        "source_treatments": source_treatments,
        "local_predecessor_files_verified": predecessor_files,
        "local_predecessors": "verified" if check_local_predecessors else "not checked",
        "historical_git_checkpoint": "not replayed; preserved as historical evidence",
        "scientific_disposition_changed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=HERE.parents[1])
    parser.add_argument("--record", type=Path, default=RECORD)
    parser.add_argument("--check-local-predecessors", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.repo, json.loads(args.record.read_text(encoding="utf-8")),
                            args.check_local_predecessors), indent=2))
