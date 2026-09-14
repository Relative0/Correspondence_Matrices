"""Result admission for future attribution experiments, independent of v1 logs."""
from __future__ import annotations

import math
import re

SCHEMA = "cm-biology-attribution-result/v1"
CATEGORIES = frozenset({"comparator-only", "correctness/control evidence",
    "CM-associated but algorithmically general", "attribution-isolated CM effect",
    "negative/no-go", "unresolved"})
ARMS = {
    "bnet_scalar_oracle": ("raw_bnet", "exhaustive_truth_table", "python"),
    "raw_factorized": ("raw_bnet", "factorized_counts", "python_packed"),
    "prepared_cm_factorized": ("prepared_cm", "factorized_counts", "python_packed"),
    "explicit_packed_cm": ("explicit_cm", "packed_evaluation", "python_packed"),
    "biodivine_aeon": ("bnet_to_bdd", "symbolic_fixed_points", "biodivine_aeon"),
    "cadical195_enumeration": ("definitional_cnf", "sat_enumeration", "cadical195"),
    "cryptominisat": ("definitional_cnf", "sat", "cryptominisat"),
    "d4": ("definitional_cnf", "exact_model_count", "d4"),
    "ganak": ("definitional_cnf", "exact_model_count", "ganak"),
}
STATUSES = frozenset({"ok", "timeout", "unavailable", "unsupported", "parse_error",
    "invalid_witness", "count_mismatch", "resource_limit", "backend_error"})


def mechanism_attribution(arm):
    representation, algorithm, backend = ARMS[arm]
    preprocessing = {
        "bnet_scalar_oracle": "bounded_bnet_parse",
        "raw_factorized": "bnet_parse_and_flat_program_compilation",
        "prepared_cm_factorized": "bnet_parse_cm_ingress_and_flat_program_compilation",
        "explicit_packed_cm": "bnet_parse_cm_ingress_and_packed_materialization",
        "biodivine_aeon": "bnet_parse_infer_valid_graph_and_bdd_construction",
        "cadical195_enumeration": "parsimonious_definitional_cnf_and_cadical_defaults",
        "cryptominisat": "parsimonious_definitional_cnf_and_cryptominisat_defaults",
        "d4": "parsimonious_definitional_cnf_normalization_and_d4_defaults",
        "ganak": "parsimonious_definitional_cnf_normalization_and_ganak_defaults",
    }[arm]
    return {"representation": representation, "algorithm": algorithm, "backend": backend,
            "preprocessing": preprocessing, "category": "correctness/control evidence",
            "isolated_effect": None, "ablation_id": None}


def validate_result(row):
    """Structural admission only; callers must verify referenced evidence bytes.

    This does not prove an effect merely because a row names an ablation.
    """
    if row.get("schema") != SCHEMA or row.get("arm") not in ARMS:
        raise ValueError("unknown future result schema/arm")
    mechanism = row.get("mechanism_attribution")
    required = {"representation", "algorithm", "backend", "preprocessing", "category", "isolated_effect", "ablation_id"}
    if not isinstance(mechanism, dict) or not required <= mechanism.keys():
        raise ValueError("explicit mechanism_attribution required")
    if tuple(mechanism[k] for k in ("representation", "algorithm", "backend")) != ARMS[row["arm"]]:
        raise ValueError("mechanism disagrees with declared arm")
    if mechanism["category"] not in CATEGORIES or not mechanism["preprocessing"]:
        raise ValueError("invalid attribution category/preprocessing")
    isolated = mechanism["category"] == "attribution-isolated CM effect"
    if isolated:
        if row["arm"] not in {"prepared_cm_factorized", "explicit_packed_cm"} or not mechanism["ablation_id"] or not mechanism["isolated_effect"]:
            raise ValueError("isolated CM effect requires CM arm and explicit ablation")
        if not re.fullmatch(r"[0-9a-f]{64}", str(mechanism.get("ablation_evidence_sha256", ""))):
            raise ValueError("isolated effect requires bound ablation evidence")
    elif mechanism["isolated_effect"] is not None:
        raise ValueError("unisolated result must not claim an isolated effect")
    for key in ("input_sha256", "query_schedule_sha256", "source_manifest_sha256"):
        if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", row[key]):
            raise ValueError(f"invalid {key}")
    for key in ("instance_id", "cluster_id", "environment_id", "memory_scope"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(f"missing {key}")
    if row.get("partition") not in {"train", "development", "held_out", "diagnostic"}:
        raise ValueError("invalid partition")
    if row.get("perturbation_semantics") not in {"clamp", "condition"}:
        raise ValueError("explicit perturbation semantics required")
    if type(row.get("repetition")) is not int or row["repetition"] < 0:
        raise ValueError("invalid repeated measurement id")
    if type(row.get("queries")) is not int or row["queries"] not in {1, 8, 64}:
        raise ValueError("invalid session size")
    status = row.get("status")
    if status not in STATUSES:
        raise ValueError("unknown failure classification")
    times = row.get("timing_seconds", {})
    keys = ("cold_construction", "preparation", "warm_queries", "total_session")
    if set(times) != set(keys) or any(type(times[k]) not in (float, int) or not math.isfinite(times[k]) or times[k] < 0 for k in keys):
        raise ValueError("complete finite nonnegative timing breakdown required")
    if times["total_session"] + 1e-9 < sum(times[k] for k in keys[:-1]):
        raise ValueError("total session excludes measured phases")
    if type(row.get("peak_memory_bytes")) is not int or row["peak_memory_bytes"] < 0:
        raise ValueError("peak memory and scope required")
    if status == "ok":
        outputs = row.get("outputs")
        if not isinstance(outputs, list) or len(outputs) != row["queries"]:
            raise ValueError("one exact output per query required")
        for output in outputs:
            count = output.get("count")
            sat = output.get("satisfiable")
            if type(sat) is not bool:
                raise ValueError("explicit SAT decision required")
            if row["arm"] != "cryptominisat":
                if not isinstance(count, str) or not re.fullmatch(r"0|[1-9][0-9]*", count) or sat != (int(count) > 0):
                    raise ValueError("exact decimal count and SAT decision disagree")
            elif count is not None:
                raise ValueError("SAT-only arm cannot claim a count")
            if sat and (not isinstance(output.get("witness"), dict) or output.get("witness_validated") is not True):
                raise ValueError("satisfiable output requires original-model witness validation")
            if sat and not output.get("witness_backend"):
                raise ValueError("witness provenance required, including companion SAT controls")
            if not sat and output.get("witness") is not None:
                raise ValueError("UNSAT output has a witness")
    elif not row.get("failure_reason") or row.get("outputs") is not None:
        raise ValueError("failure requires reason and null outputs (never zero count)")
    return row
