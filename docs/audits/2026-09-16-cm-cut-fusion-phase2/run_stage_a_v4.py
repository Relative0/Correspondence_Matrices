"""Custody wrapper for the final Stage-A replay after exposing compiled plans."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("cm_cut_stage_a_v3_replay", HERE / "run_stage_a_v3.py")
v3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v3)

original_write = v3.stage.write_json


def redirected_write(path, value):
    if path.name == "source-manifest-v3.json":
        value = dict(value)
        value["schema"] = "cm-cut-fusion-stage-a-source-manifest/v4"
        value["supersedes"] = "source-manifest-v3.json"
        relpath = "docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v4.py"
        value["files_sha256"] = dict(value["files_sha256"])
        value["files_sha256"][relpath] = v3.stage.sha((ROOT / relpath).read_bytes())
        return original_write(path.with_name("source-manifest-v4.json"), value)
    if path.name == "stage-a-results-v3.json":
        value = dict(value)
        value["schema"] = "cm-cut-fusion-stage-a-results/v4"
        value["supersedes"] = "stage-a-results-v3.json"
        return original_write(path.with_name("stage-a-results-v4.json"), value)
    return original_write(path, value)


def main():
    v3.stage.write_json = redirected_write
    v3.main()


if __name__ == "__main__":
    main()
