"""Audit invariants: independent units, censored results, and source custody."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from cmbench.biology_bnet import parse_bnet
from cmbench.biology_controls import is_fixed_point

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/audits/2026-09-14-cm-benchmark-attribution"
spec = importlib.util.spec_from_file_location("cm_attribution_statistics", AUDIT / "statistical_analysis.py")
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def load(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def test_measurement_repetition_cannot_manufacture_independent_families():
    rows = []
    for case, ratio, repeats in (("a", 0.5, 20), ("b", 2., 1)):
        for repeat in range(repeats):
            for arm, value in (("base", 100), ("candidate", 100 * ratio)):
                rows.append({"case": case, "repeat": repeat, "arm": arm, "total_ns": value, "status": "ok"})
    result = stats.compare(rows, "base", "candidate", lambda name: name)
    assert result["by_q"]["1"]["measurement_pairs"] == 21
    assert result["by_q"]["1"]["equal_cluster_geometric_mean"] == pytest.approx(1.)
    one_family = stats.compare(rows, "base", "candidate", lambda name: "shared")
    assert one_family["by_q"]["1"]["cluster_percentile_bootstrap_95"] is None
    assert one_family["by_q"]["1"]["heldout_gate"]["applicable"] is False
    with pytest.raises(ValueError, match="duplicate"):
        stats.compare(rows + [rows[0]], "base", "candidate", lambda name: name)


def test_censored_instance_is_retained_without_invented_time_ratio():
    rows = [{"case": "timeout", "arm": "base", "status": "timeout", "total_ns": 100},
            {"case": "timeout", "arm": "candidate", "status": "ok", "total_ns": 1}]
    result = stats.compare(rows, "base", "candidate", lambda name: "family")
    assert result["cases"][0]["paired_ratios"] == []
    assert len(result["cases"][0]["unpaired_or_failed"]) == 1
    assert result["by_q"]["1"]["instances"] == 1
    assert result["by_q"]["1"]["paired_instances"] == 0


def test_corpus_closure_family_partition_and_hash_bound_local_controls():
    corpus = load("BIOLOGY_CORPUS_AUDIT.json")
    assert corpus["summary"]["classification"] == {"closed": 22, "open": 190}
    models = {model["model_id"]: model for model in corpus["models"]}
    for cluster in corpus["clusters"]:
        assert {models[mid]["recommended_partition"] for mid in cluster["models"]} == {cluster["partition"]}
    local = load("LOCAL_CONTROL_RESULTS.json")
    native = load("NATIVE_CONTROL_RESULTS.json")
    assert native["correctness_mismatches"] == []
    assert len(local["cases"]) == len(native["cases"]) == 22
    observed = {case["model_id"]: case for case in native["cases"]}
    for case in local["cases"]:
        ident = case["model_id"]
        for suffix, key in (("bnet", "bnet_sha256"), ("cnf", "cnf_sha256")):
            path = AUDIT / "control-inputs" / f"{ident}.{suffix}"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == case[key]
        assert case["bnet_sha256"] == models[ident]["input_sha256"]
        functions = parse_bnet((AUDIT / "control-inputs" / f"{ident}.bnet").read_text())
        arms = observed[ident]["arms"]
        assert all(value["status"] == "ok" for value in arms.values())
        counts = {arms[arm]["count"] for arm in ("aeon", "d4", "ganak")}
        assert len(counts) == 1
        count = counts.pop()
        assert arms["cryptominisat"]["satisfiable"] == bool(count)
        for value in list(arms.values()) + [case[k] for k in ("scalar", "cadical195") if k in case]:
            if value.get("witness") is not None:
                assert is_fixed_point(functions, value["witness"])
        if "scalar" in case:
            assert case["scalar"]["count"] == case["cadical195"]["count"] == count


def test_claim_register_has_complete_contracts_and_no_isolated_claim():
    register = load("CLAIM_EVIDENCE_REGISTER.json")
    assert len({c["id"] for c in register["claims"]}) == len(register["claims"])
    for claim in register["claims"]:
        assert claim["classification"] in register["classification_vocabulary"]
        assert claim["classification"] != "attribution-isolated CM effect"
        for key in ("workload", "baselines", "artifact_ids", "limitations", "independence_unit", "permitted_wording"):
            assert claim[key]
        assert all(ref in register["artifacts"] for ref in claim["artifact_ids"])
    for artifact in register["artifacts"].values():
        # Retained source dependencies are checked by the reproduction script;
        # this portable test verifies every in-checkout referenced artifact.
        path = ROOT / artifact["path"]
        if path.is_file() and path.is_relative_to(ROOT):
            assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_frozen_query_schedules_are_distinct_valid_prefixes():
    result = load("QUERY_SCHEDULES.json")
    assert result["status"] == "prospective_not_executed"
    assert result["session_prefix_lengths"] == [1, 8, 64]
    assert len(result["models"]) == 22
    for model in result["models"]:
        source = AUDIT / "control-inputs" / (model["model_id"] + ".bnet")
        functions = parse_bnet(source.read_text(encoding="utf-8"))
        targets = {f.target for f in functions}
        queries = model["queries"]
        assert queries[0] == {} and len(queries) == 64
        assert len({tuple(sorted(q.items())) for q in queries}) == 64
        assert all(set(q) <= targets and len(q) <= 3 and set(q.values()) <= {0, 1} for q in queries)
        encoded = json.dumps(queries, sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(encoded).hexdigest() == model["query_schedule_sha256"]


def test_pinned_native_projection_probe_preserves_support_warning():
    cases = {case["case"]: case for case in load("PROJECTED_NATIVE_PROBE.json")["cases"]}
    assert len(cases) == 6
    assert "exact arb int 4" in cases["plain_exact_free_axes"]["stdout"]
    assert "exact arb int 1" in cases["invalid_independent_support_hint"]["stdout"]
    assert cases["projection_vs_support"]["returncode"] != 0
    assert cases["projection_vs_support"]["successor_wrapper_count"] == 2
    for name, expected in (("visible_hidden_multiplicity", 2), ("empty_projection_sat", 1), ("empty_projection_unsat", 0)):
        assert cases[name]["successor_wrapper_count"] == expected
