from __future__ import annotations

import hashlib
from itertools import product
import json
from pathlib import Path
import random

import pytest

from cmbench.biology_bnet import parse_bnet
from cmbench.biology_controls import bnet_scalar_oracle, native_fixed_points, is_fixed_point
from cmbench.biology_sessions import PreparedBNet, canonical_json, execute_session, program_hash

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/audits/2026-09-14-cm-benchmark-attribution"


@pytest.mark.parametrize("seed", range(12))
def test_random_closed_networks_all_clamps_and_conditions(seed):
    rng = random.Random(seed)
    atoms = ["a", "b", "c", "0", "1"]
    def expression(depth):
        if depth == 0: return rng.choice(atoms)
        return rng.choice([f"!({expression(depth-1)})",
            f"({expression(depth-1)} & {expression(depth-1)})",
            f"({expression(depth-1)} | {expression(depth-1)})"])
    functions = parse_bnet("targets,factors\n" + "\n".join(f"{name}, {expression(2)}" for name in atoms[:3]))
    raw = PreparedBNet(functions)
    cm = PreparedBNet(functions, arm="prepared_cm_factorized")
    canonical = PreparedBNet(functions, arm="prepared_cm_factorized", representation_mode="cm_canonical")
    packed = PreparedBNet(functions, arm="explicit_packed_cm")
    assert program_hash(raw.program) == program_hash(cm.program)
    for values in product((None, 0, 1), repeat=3):
        fixed = {n: v for n, v in zip(atoms, values) if v is not None}
        for semantics in ("clamp", "condition"):
            expected = bnet_scalar_oracle(functions, fixed=fixed, semantics=semantics).count
            results = [p.query(fixed, semantics=semantics) for p in (raw, cm, canonical, packed)]
            assert results[0][1] == results[1][1]
            assert all(int(value["count"]) == expected for value, digest in results)
            for value, digest in results:
                if expected:
                    assert is_fixed_point(functions, value["witness"], fixed=fixed, semantics=semantics)


def test_raw_path_never_constructs_cm(monkeypatch):
    import cm_ir
    monkeypatch.setattr(cm_ir, "CMIRBuilder", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("CM construction")))
    model = PreparedBNet(parse_bnet("targets,factors\na, 1\nb, !a"))
    assert model.query({})[0]["count"] == "1"


def test_guards_clamp_all_and_canonical_structure_change():
    with pytest.raises(ValueError, match="undeclared"):
        PreparedBNet(parse_bnet("targets,factors\na, external"))
    functions = parse_bnet("targets,factors\na, a | a\nb, !b")
    raw = PreparedBNet(functions, max_width=1)
    cm = PreparedBNet(functions, arm="prepared_cm_factorized", representation_mode="cm_canonical", max_width=1)
    assert program_hash(raw.program) != program_hash(cm.program)
    assert raw.query({"a": 1, "b": 0})[0]["count"] == "1"
    assert raw.query({"a": 1, "b": 0}, semantics="condition")[0]["count"] == "0"
    with pytest.raises(ValueError, match="outside"):
        raw.query({"other": 1})
    with pytest.raises(ValueError, match="Boolean"):
        raw.query({"a": 2})
    wide = PreparedBNet(parse_bnet("targets,factors\na, b\nb, a"), max_width=1)
    with pytest.raises(ValueError, match="width"):
        wide.query({})


@pytest.mark.parametrize("reuse", ["retained", "rebuild"])
def test_session_timing_outputs_and_schedule_hash(tmp_path, reuse):
    source = tmp_path / "tiny.bnet"
    source.write_text("targets,factors\na, !a\nb, a\n")
    queries = [{}, {"a": 1}, {"a": 0}, {"b": 1}] * 2
    base = {"path": str(source), "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "query_schedule": queries, "query_schedule_sha256": hashlib.sha256(canonical_json(queries)).hexdigest(),
            "queries": 8, "reuse_mode": reuse, "representation_mode": "matched"}
    rows = [execute_session({**base, "arm": arm}) for arm in ("raw_factorized", "prepared_cm_factorized")]
    assert rows[0]["outputs"] == [{**o, "witness_backend": ("raw_factorized_self_reduction" if o["satisfiable"] else None)} for o in rows[1]["outputs"]]
    assert rows[0]["query_plan_sha256"] == rows[1]["query_plan_sha256"]
    for row in rows:
        timing = row["timing_seconds"]
        assert timing["total_session"] >= sum(timing[k] for k in ("cold_construction", "preparation", "warm_queries"))
        assert len(row["query_timings_seconds"]) == 8
        assert all(t["rebuild_preparation"] > 0 for t in row["query_timings_seconds"]) if reuse == "rebuild" else True
    with pytest.raises(ValueError, match="schedule hash"):
        execute_session({**base, "arm": "raw_factorized", "query_schedule_sha256": "0" * 64})


def test_frozen_small_models_all_64_queries_against_native_control():
    schedules = json.loads((AUDIT / "QUERY_SCHEDULES.json").read_text())
    checked = 0
    for entry in schedules["models"]:
        source = AUDIT / "control-inputs" / (entry["model_id"] + ".bnet")
        functions = parse_bnet(source.read_text())
        if len(functions) > 16:
            continue
        plans = [PreparedBNet(functions, arm=arm, max_width=16) for arm in ("raw_factorized", "prepared_cm_factorized")]
        for fixed in entry["queries"]:
            native = native_fixed_points(functions, fixed=fixed, max_targets=16)
            results = [p.query(fixed) for p in plans]
            assert all(int(output["count"]) == native.count for output, digest in results)
            assert results[0][1] == results[1][1]
            checked += 1
    assert checked == 640


@pytest.mark.parametrize("arm,preprocessing", [("bnet_scalar_oracle", "bounded_bnet_parse"),
    ("cadical195_enumeration", "parsimonious_definitional_cnf_and_cadical_defaults")])
def test_control_rows_name_their_actual_preprocessing(tmp_path, arm, preprocessing):
    source = tmp_path / "model.bnet"
    source.write_text("targets,factors\na, a")
    request = {"arm": arm, "path": str(source), "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "query_schedule": [{}], "query_schedule_sha256": hashlib.sha256(canonical_json([{}])).hexdigest(), "queries": 1}
    result = execute_session(request)
    assert result["preprocessing_policy"] == preprocessing
    assert result["query_plan_sha256"] is None
