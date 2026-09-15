"""Cross-artifact checks for evidence conservation, not performance thresholds."""
from pathlib import Path
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent


def data():
    return json.loads((HERE/"PROFILE_RESULTS.json").read_text(encoding="utf-8"))


def test_every_declared_cell_survives_synthesis_and_uses_primary_run():
    d=data()
    assert d["scientific_disposition_changed"] is False
    assert len(d["ladder"]["cells"]) == 137
    assert len(d["tasks"]["cells"]) == 70
    assert all(r["status"] == "exact_complete_output_match" for r in d["ladder"]["cells"])
    assert all(r["correct"] for r in d["tasks"]["cells"])
    assert d["ladder"]["source"]["path"] == "ladder-run-002.json"
    for source in d["sources"]:
        assert hashlib.sha256((HERE/source["path"]).read_bytes()).hexdigest() == source["sha256"]


def test_all_exclusive_partitions_conserve_own_wall_without_cross_pass_addition():
    d=data()
    for row in d["ladder"]["cells"]:
        for part in row["phase"].values():
            assert math.isclose(sum(x["wall_s"] for x in part["exclusive_phases"].values()),part["sum_caller_wall_s"],abs_tol=1e-12)
            assert math.isclose(sum(x["percent_of_own_phase_pass_wall"] for x in part["exclusive_phases"].values()),100,abs_tol=1e-9)
    for row in d["tasks"]["cells"]:
        assert math.isclose(sum(x["mean_wall_ns"] for x in row["phases"].values()),row["phase_mean_caller_ns"],abs_tol=0.01)
        assert math.isclose(sum(x["percent_mean_caller"] for x in row["phases"].values()),100,abs_tol=1e-9)


def test_complete_packed_outputs_match_across_all_ladder_arms():
    groups={}
    for row in data()["ladder"]["cells"]:
        if row["arm"] == "dense_cm": continue
        groups.setdefault(row["case"],set()).add((row["output_bytes"],row["output_sha256"]))
    assert len(groups)==13
    assert all(len(values)==1 for values in groups.values())


def test_unknown_quantities_and_contract_differences_stay_unknown():
    d=data()
    assert all(x is None for x in d["unknown_measurements"].values())
    assert d["ladder"]["cpu_granularity"]["zero_whole_pass_samples"] > 0
    for row in d["slowdown_inventory"]:
        if row.get("comparison_class") == "different family delivery contract" or row["arm"] == "dense_cm":
            assert row["measured_slowdown_ratio"] is None
    assert all(x["matches"] for x in d["frozen_evidence"]["predecessor_binding_checks"])
