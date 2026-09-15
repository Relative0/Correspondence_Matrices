"""Read-only source review; writes only a new requested local JSON record."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTECTED = [ROOT.parent.parent, ROOT.parent / "cm-consolidation-20260914"]
EVIDENCE = ROOT.parent / "cm-time-attribution-20260915"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    rows = []
    for root in PROTECTED:
        cmd = ["git", "-c", f"safe.directory={root.as_posix()}"]
        status = subprocess.check_output(
            cmd + ["status", "--porcelain", "--untracked-files=no"], cwd=root
        ).decode().splitlines()
        paths = subprocess.check_output(cmd + ["diff", "--name-only", "HEAD"], cwd=root).decode().splitlines()
        hashes = {p: sha(root / p) for p in paths if (root / p).is_file()}
        rows.append({"root": str(root), "status": status, "dirty_hashes": hashes})
    evidence = {}
    for name in ["2026-09-15-cm-time-attribution-deep-dive", "2026-09-15-cm-family-lifecycle-code-dive"]:
        folder = EVIDENCE / "docs/audits" / name
        evidence[name] = {str(p.relative_to(folder)): sha(p) for p in folder.rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts}
    return {"protected": rows, "evidence": evidence}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    path = HERE / "PRESERVATION.json"
    data = snapshot()
    if args.verify:
        assert data == json.loads(path.read_text()), "protected worktree or evidence changed"
        print("Protected tracked files and both evidence directories unchanged")
    else:
        with path.open("x", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        print("Preservation checkpoint written")
