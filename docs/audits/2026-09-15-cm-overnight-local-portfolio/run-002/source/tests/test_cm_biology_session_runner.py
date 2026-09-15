from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("biology_runner_test", ROOT / "scripts/cm_biology_sessions.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.skipif(os.name != "nt", reason="Windows hard-limit pilot")
def test_three_real_workers_admit_rows_and_agree_end_to_end(tmp_path):
    output = tmp_path / "smoke"
    runner.prepare(output)
    plan = json.loads((output / "PLAN.json").read_text())
    from cmbench.biology_bnet import parse_bnet
    smallest = min(plan["cells"], key=lambda c: len(parse_bnet(Path(c["path"]).read_text())))["instance_id"]
    plan["cells"] = [c for c in plan["cells"] if c["instance_id"] == smallest and c["queries"] == 1
                     and c["reuse_mode"] == "retained" and c["representation_mode"] == "matched"
                     and c["arm"] in {"raw_factorized", "prepared_cm_factorized", "bnet_scalar_oracle"}]
    assert len(plan["cells"]) == 3
    runner.write(output / "PLAN.json", plan)
    runner.execute(output)
    run = json.loads((output / "RUN.json").read_text())
    assert run["status"] == "complete" and run["status_counts"] == {"ok": 3}
    assert run["correctness_mismatches"] == []
    rows = [json.loads(line) for line in (output / "ledger.jsonl").read_text().splitlines()]
    assert all(r["supervisor"]["cleanup_verified"] and r["supervisor"]["cpu_seconds"] is not None for r in rows)
    assert all(r["timing_seconds"]["total_session"] >= r["worker_total_seconds"] for r in rows)
    with pytest.raises(ValueError, match="overwrite"):
        runner.execute(output)


def test_plan_refuses_changed_source_manifest_before_launch(tmp_path):
    output = tmp_path / "refusal"
    runner.prepare(output)
    (output / "SOURCE_MANIFEST.json").write_text("{}")
    with pytest.raises(ValueError, match="manifest mismatch"):
        runner.execute(output)
    assert not (output / "ledger.jsonl").exists()
