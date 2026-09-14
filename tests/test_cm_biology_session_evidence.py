from __future__ import annotations
import hashlib
import json
from pathlib import Path

from cmbench.biology_session_analysis import analyze_sessions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/audits/2026-09-15-cm-biology-sessions"
PILOT = OUT / "pilot-002"


def load(path): return json.loads(path.read_text())
def lines(path): return [json.loads(s) for s in path.read_text().splitlines()]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_pilot_and_executed_source_snapshot():
    run = load(PILOT / "RUN.json")
    rows = lines(PILOT / "ledger.jsonl")
    assert run["status"] == "complete" and len(rows) == run["completed_cells"] == 288
    assert len({r["cell_id"] for r in rows}) == 288
    assert run["ledger_sha256"] == sha(PILOT / "ledger.jsonl")
    assert run["plan_sha256"] == sha(PILOT / "PLAN.json")
    assert run["status_counts"] == {"ok": 255, "timeout": 3, "unsupported": 30}
    assert run["not_run"] == run["correctness_mismatches"] == []
    assert run["elapsed_seconds"] < 900
    assert all(r["supervisor"]["cleanup_verified"] for r in rows)
    assert all(r["memory_scope"] == "windows_job_peak_committed_bytes" for r in rows)
    for name, digest in load(PILOT / "SOURCE_MANIFEST.json")["files"].items():
        assert sha(PILOT / "source" / name) == digest


def test_reporting_correction_never_changes_measurements_or_outputs():
    original = lines(PILOT / "ledger.jsonl")
    corrected = lines(OUT / "REPORTING_CORRECTED_LEDGER.jsonl")
    addendum = load(OUT / "REPORTING_ADDENDUM.json")
    assert len(addendum["amendments"]) == 57
    assert addendum["original_ledger_sha256"] == sha(PILOT / "ledger.jsonl")
    assert addendum["corrected_ledger_sha256"] == sha(OUT / "REPORTING_CORRECTED_LEDGER.jsonl")
    for old, new in zip(original, corrected):
        for key in old.keys() - {"preprocessing_policy", "mechanism_attribution"}:
            assert old[key] == new[key]
        if old != new:
            assert old["arm"] in {"bnet_scalar_oracle", "cadical195_enumeration"}
    assert analyze_sessions(corrected) == load(OUT / "ANALYSIS.json")


def test_no_go_and_future_plan_do_not_turn_pilot_into_heldout_acceptance():
    analysis = load(OUT / "ANALYSIS.json")
    assert analysis["heldout_acceptance"]["eligible"] is False
    primary = next(c for c in analysis["comparisons"] if c["queries"] == 64 and c["reuse_mode"] == "retained" and c["representation_mode"] == "matched")
    assert primary["summary"]["equal_family_geometric_mean_ratio"] > .95
    assert primary["summary"]["confidence_interval_95"] is None
    assert primary["plan_attribution_counts"] == {"identical_normalized_plans_same_declared_evaluator": 11}
    future = load(OUT / "NEXT_LOCAL_PLAN.json")
    assert future["status"] == "deferred_no_development_signal"
    assert future["execution_authorized_by_this_file"] is False
    assert future["paid_compute"] is False
    assert len(future["cells"]) == 396
    assert len({c["instance_id"] for c in future["cells"]}) == 22
    assert len({c["cell_id"] for c in future["cells"]}) == 396
    assert future["source_manifest_sha256"] == sha(OUT / "SOURCE_MANIFEST.json")
