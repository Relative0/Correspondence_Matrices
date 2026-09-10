"""Pinned, read-only evidence adapter for the learning and neural website page.

The adapter deliberately consumes saved artifacts only.  It does not discover
latest runs, execute benchmarks, fit selectors, train models, or write evidence.
Required identities and conservative decision boundaries fail closed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.query_ladder_learning_evidence import build_evidence
from cmbench.recognition import query_ladder_development_experiment as development

PINNED = {
    "c": (
        "docs/recognition/learning_milestone_c_results.json",
        "f9ee8df9dc6e500624cd50f396c4520028409c0394647066633baa1a0f7f44d5",
    ),
    "c2": (
        "docs/recognition/learning_milestone_c2_results.json",
        "54963176656040c44fd539ff0828cb158904f10f1f3e272498570ac0d2113062",
    ),
    "c3": (
        "docs/recognition/learning_milestone_c3_natural_decomposition_results.json",
        "3e66b22cd35d20db280456f77c77ec014cfb3c6ed210a441d8fa2e1daba4871b",
    ),
    "c4": (
        "docs/recognition/learning_milestone_c4_direct_cut_ranking_results.json",
        "1191b4cc7e892df01c775907c910b6c32bbb9effde71f7290095d5a125de3b7b",
    ),
    "c5": (
        "docs/recognition/learning_milestone_c5_variable_conditioned_cut_results.json",
        "5225e424b4ca109b468f7fd9f673c86b83b8d51cf484c543d00a1c306f17047e",
    ),
    "c6": (
        "docs/recognition/learning_milestone_c6_packed_source_anf_results.json",
        "ec398dcb6eddcbc534f0a27c176c8f535fe49441b8ddae2c8a923e59ede3dfa6",
    ),
    "post": (
        "docs/recognition/runs/post-benchmark-neural-eligibility-development-20260903-001/assessment.json",
        "40bd8e37a475090496beaf88d17ce31442e57190060d2b94b46dac650be3e8df",
    ),
    "protocol": (
        "docs/recognition/runs/version-history-learning-development-20260904-004/assessment.json",
        "50d24b481c1e91a94329ae563042624b3e1f2bcf1601134e29a974c8e9d00460",
    ),
    "freeze": (
        "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/FREEZE.json",
        "3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692",
    ),
    "freeze_verification": (
        "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/INDEPENDENT_VERIFICATION.json",
        "a205649db2b9b4e6a74ad74949437dc98ed428a89d4cc9cde5a692ddb9617c7e",
    ),
}

# Explicit publication allowlist.  It intentionally does not discover "latest"
# files, so a new milestone cannot silently inherit the page's audit wording.
MILESTONE_SOURCES = (
    ("AB", "LEARNING_MILESTONES_AB_2026_08_29.md", "learning_milestones_ab_results.json"),
    ("C", "LEARNING_MILESTONE_C_2026_08_29.md", "learning_milestone_c_results.json"),
    ("C2", "LEARNING_MILESTONE_C2_2026_08_29.md", "learning_milestone_c2_results.json"),
    ("C3", "LEARNING_MILESTONE_C3_NATURAL_DECOMPOSITION_2026_08_29.md", "learning_milestone_c3_natural_decomposition_results.json"),
    ("C4", "LEARNING_MILESTONE_C4_DIRECT_CUT_RANKING_2026_08_29.md", "learning_milestone_c4_direct_cut_ranking_results.json"),
    ("C5", "LEARNING_MILESTONE_C5_VARIABLE_CONDITIONED_CUT_2026_08_29.md", "learning_milestone_c5_variable_conditioned_cut_results.json"),
    ("C6", "LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md", "learning_milestone_c6_packed_source_anf_results.json"),
    ("C7 machine attempt", "LEARNING_MILESTONE_C7_SECOND_MACHINE_ATTEMPT_2026_08_30.md", "learning_milestone_c7_second_machine_attempt_results.json"),
    ("C7 source confirmation", "LEARNING_MILESTONE_C7_YOSYS_SOURCE_CONFIRMATION_2026_08_30.md", "learning_milestone_c7_yosys_source_confirmation_results.json"),
    ("C8", "LEARNING_MILESTONE_C8_LINUX_SOURCE_ANF_CONFIRMATION_2026_08_30.md", "learning_milestone_c8_linux_source_anf_results.json"),
    ("C9–C12 consolidated", "LEARNING_MILESTONE_C12_ADAPTIVE_EXACT_DISPATCHER_2026_08_30.md", "learning_milestone_c12_adaptive_dispatcher_results.json"),
    ("C13", "LEARNING_MILESTONE_C13_IN_KERNEL_TAIL_SENTINEL_2026_08_30.md", "learning_milestone_c13_in_kernel_sentinel_results.json"),
    ("C14", "LEARNING_MILESTONE_C14_TASK_GUARD_SHADOW_2026_08_30.md", "learning_milestone_c14_task_guard_results.json"),
    ("C15", "LEARNING_MILESTONE_C15_EXACT_CM_GF2_2026_08_30.md", "learning_milestone_c15_exact_cm_gf2_results.json"),
    ("C16", "LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md", "learning_milestone_c16_exact_screened_gf2_results.json"),
    ("C17", "LEARNING_MILESTONE_C17_GF2_TASK_DISPATCHER_2026_08_31.md", "learning_milestone_c17_gf2_task_dispatcher_results.json"),
    ("C18", "LEARNING_MILESTONE_C18_INDEPENDENT_GF2_TRANSFER_2026_08_31.md", "learning_milestone_c18_independent_gf2_transfer_results.json"),
    ("C19", "LEARNING_MILESTONE_C19_CHEAP_GF2_WORK_POLICY_2026_08_31.md", "learning_milestone_c19_cheap_gf2_work_policy_results.json"),
    ("C20", "LEARNING_MILESTONE_C20_COMPILED_GF2_POLICY_VTR_TAIL_2026_08_31.md", "learning_milestone_c20_compiled_gf2_policy_vtr_tail_results.json"),
    ("C21", "LEARNING_MILESTONE_C21_TASK_MATCHED_GF2_METHOD_TABLE_2026_08_31.md", "learning_milestone_c21_task_matched_gf2_method_table_results.json"),
    ("C22 boundary", "LEARNING_MILESTONE_C24_C22_BOUNDARY_2026_08_31.md", "learning_milestone_c24_c22_boundary_results.json"),
    ("C23", "LEARNING_MILESTONE_C23_FRESH_YOSYS_GF2_TABLE_2026_08_31.md", "learning_milestone_c23_fresh_yosys_gf2_table_results.json"),
    ("C25", "LEARNING_MILESTONE_C25_RESIDENT_C22_SESSION_2026_08_31.md", "learning_milestone_c25_resident_c22_session_results.json"),
    ("C26", "LEARNING_MILESTONE_C26_FUSED_VERIFIED_CONTEXT_2026_08_31.md", "learning_milestone_c26_fused_verified_context_results.json"),
    ("C27", "LEARNING_MILESTONE_C27_SUPPORT_AWARE_FRESH_CONFIRMATION_2026_08_31.md", "learning_milestone_c27_support_aware_fresh_confirmation_results.json"),
    ("C28", "LEARNING_MILESTONE_C28_CROSS_MACHINE_PROFITABILITY_ADJUDICATION_2026_09_01.md", "learning_milestone_c28_cross_machine_profitability_adjudication_results.json"),
    ("C29", "LEARNING_MILESTONE_C29_VARIANCE_LOCALIZATION_2026_09_01.md", "learning_milestone_c29_variance_localization_results.json"),
    ("C30", "LEARNING_MILESTONE_C30_PREPARED_POLICY_CONTEXT_2026_09_01.md", "learning_milestone_c30_prepared_policy_context_results.json"),
    ("C31", "LEARNING_MILESTONE_C31_PROSPECTIVE_SECOND_MACHINE_FREEZE_2026_09_01.md", "learning_milestone_c31_prepared_policy_replication_results.json"),
    ("C32", "LEARNING_MILESTONE_C32_PREPARED_POLICY_SHADOW_BOUNDARY_2026_09_01.md", "learning_milestone_c32_prepared_policy_shadow_results.json"),
    ("C33", "LEARNING_MILESTONE_C33_BOUNDED_ASYNC_SHADOW_2026_09_01.md", "learning_milestone_c33_async_shadow_results.json"),
    ("C34", "LEARNING_MILESTONE_C34_NATURAL_TASK_MATCHED_HEADROOM_2026_09_01.md", "learning_milestone_c34_natural_headroom_results.json"),
    ("C35", "LEARNING_MILESTONE_C35_NATURAL_REPEATED_QUERY_2026_09_01.md", "learning_milestone_c35_natural_repeated_query_results.json"),
    ("C36", "LEARNING_MILESTONE_C36_WIDE_NATURAL_REPEATED_QUERY_2026_09_01.md", "learning_milestone_c36_wide_natural_repeated_query_results.json"),
    ("D–D9 consolidated", "LEARNING_MILESTONE_D_2026_08_29.md", "learning_milestone_d_results.json"),
    ("D10", "LEARNING_MILESTONE_D10_INDEXED_RULE_ENGINE_2026_08_30.md", "learning_milestone_d10_indexed_rule_engine_results.json"),
    ("E1", "LEARNING_MILESTONE_E1_BDD_ORDER_SELECTION_2026_08_30.md", "learning_milestone_e1_bdd_order_results.json"),
    ("E2", "LEARNING_MILESTONE_E2_SAT_EQUIVALENCE_GUIDANCE_2026_08_30.md", "learning_milestone_e2_sat_guidance_results.json"),
)


def _sha256(path: Path) -> str:
    """Hash text evidence in the LF-normalized form stored by Git."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _read_pinned(key: str) -> dict:
    relative, expected = PINNED[key]
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Missing pinned learning evidence: {relative}")
    if _sha256(path) != expected:
        raise ValueError(f"Pinned learning evidence changed: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Pinned learning evidence is not an object: {relative}")
    return value


def _href(relative: str) -> str:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Missing learning evidence link: {relative}")
    return "../../" + relative


def build_learning_neural_evidence(site: Path) -> tuple[dict, dict]:
    if site.resolve() != (ROOT / "deliverables_n22_24/master_explainer_2026_08_03").resolve():
        raise ValueError("Unexpected website root")

    post = _read_pinned("post")
    protocol = _read_pinned("protocol")
    freeze = _read_pinned("freeze")
    freeze_verification = _read_pinned("freeze_verification")
    c = _read_pinned("c")
    c2 = _read_pinned("c2")
    c3 = _read_pinned("c3")
    c4 = _read_pinned("c4")
    c5 = _read_pinned("c5")
    c6 = _read_pinned("c6")
    ladder = build_evidence()

    if post.get("status") != "complete_no_training" or post.get("decision", {}).get("selector_fitted"):
        raise ValueError("Post-benchmark neural boundary changed")
    if protocol.get("status") != "complete_no_training" or protocol.get("decision", {}).get("training_allowed"):
        raise ValueError("Learning protocol boundary changed")
    if freeze.get("status") != "frozen_not_authorized_no_labels" or any(
        freeze.get(field) for field in ("models_trained", "labels_produced", "timing_rows_produced")
    ):
        raise ValueError("Source-blind freeze has consumed prohibited evidence")
    if freeze_verification.get("status") != "verified_source_blind_freeze_no_labels":
        raise ValueError("Source-blind freeze is not independently verified")
    if ladder.get("status") != "verified_gross_only_training_abstained":
        raise ValueError("Query-ladder evidence is not verified and abstained")
    if ladder["decision"] != {
        "development_training_eligible": False,
        "training_performed": False,
        "prospective_data_consumed": False,
        "advice_enabled": False,
        "complete_abstention": True,
        "exact_fallback": "unchanged exact path",
        "production_routing_permitted": False,
    }:
        raise ValueError("Query-ladder fail-closed decision changed")
    if (
        c6.get("status") != "complete"
        or c6.get("semantic_mismatches") != 0
        or c6.get("verification", {}).get("status") != "pass"
        or c6.get("verification", {}).get("semantic_mismatches") != 0
        or c6.get("criteria", {}).get("production_promotion") is not False
    ):
        raise ValueError("C6 exact-core evidence or promotion boundary changed")

    numbers: dict[str, dict] = {}

    def number(name: str, value, fmt: str, relative: str, field: str, note: str = ""):
        numbers[f"ln.{name}"] = {
            "value": value,
            "fmt": fmt,
            "prov": f"{relative} :: {field}",
            "note": note or "Saved development evidence; not a production-routing claim.",
        }

    post_path = PINNED["post"][0]
    protocol_path = PINNED["protocol"][0]
    freeze_path = PINNED["freeze"][0]

    number("version_cases", post["strongest_surface"]["complete_cases"], "int", post_path, "strongest_surface.complete_cases")
    number("version_gross", post["strongest_surface"]["gross_headroom_speedup"], "x9", post_path, "strongest_surface.gross_headroom_speedup")
    number("version_budget", post["strongest_surface"]["maximum_overhead_ns_per_case_preserving_1_10x"], "num1", post_path, "strongest_surface.maximum_overhead_ns_per_case_preserving_1_10x")
    number("protocol_feature_cost", protocol["economics"]["fully_charged_costs_ns_per_case"]["feature_extraction_and_control"], "num1", protocol_path, "economics.fully_charged_costs_ns_per_case.feature_extraction_and_control")
    number("protocol_optimistic", protocol["economics"]["optimistic_p95_speedup_if_retrospective_control_is_oracle"], "x3", protocol_path, "economics.optimistic_p95_speedup_if_retrospective_control_is_oracle")
    number("freeze_cases", freeze["cohort"]["case_count"], "int", freeze_path, "cohort.case_count")
    for split, value in freeze["cohort"]["source_group_counts_by_split"].items():
        number(f"split_{split}", value, "int", freeze_path, f"cohort.source_group_counts_by_split.{split}")
    number("features", freeze["model_input_contract"]["bounded_inference_shape"]["features"], "int", freeze_path, "model_input_contract.bounded_inference_shape.features")
    number("prior_overlap", freeze["cohort"]["prior_alpha_structural_overlap_count"], "int", freeze_path, "cohort.prior_alpha_structural_overlap_count")
    number("seed_min", development.MIN_NEURAL_TRAINING_SEEDS, "int", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_NEURAL_TRAINING_SEEDS")
    number("gate_ba", 100 * development.MIN_BALANCED_ACCURACY, "pct0", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_BALANCED_ACCURACY")
    number("gate_chance", 100 * development.MIN_BALANCED_ACCURACY_ABOVE_CHANCE, "pct0", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_BALANCED_ACCURACY_ABOVE_CHANCE")
    number("gate_accuracy", 100 * development.MIN_ACCURACY_ABOVE_MAJORITY, "pct0", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_ACCURACY_ABOVE_MAJORITY")
    number("gate_control", 100 * development.MIN_BALANCED_ACCURACY_ABOVE_ANALYTICAL_CONTROL, "pct0", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_BALANCED_ACCURACY_ABOVE_ANALYTICAL_CONTROL")
    number("gate_coverage", 100 * development.MIN_NON_ABSTAIN_COVERAGE, "pct0", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_NON_ABSTAIN_COVERAGE")
    number("economic_gate", development.MIN_FULLY_CHARGED_SPEEDUP, "x2", "cmbench/recognition/query_ladder_development_experiment.py", "MIN_FULLY_CHARGED_SPEEDUP", "Minimum fully charged development speedup; gross oracle headroom alone does not pass this gate.")
    number("certificate_work", 100 * protocol["c5_certificate_investigation"]["evaluation"]["minimum_global_work_avoided_fraction"], "pct0", protocol_path, "c5_certificate_investigation.evaluation.minimum_global_work_avoided_fraction")
    c5_slowdowns = [row["safe_learned_over_exact_anf"] for row in c5["cost_ratios"].values()]
    number("c5_slow_min", min(c5_slowdowns), "x1", PINNED["c5"][0], "min(cost_ratios.*.safe_learned_over_exact_anf)")
    number("c5_slow_max", max(c5_slowdowns), "x1", PINNED["c5"][0], "max(cost_ratios.*.safe_learned_over_exact_anf)")
    number("c5_exact_reference", 1.0, "x1", PINNED["c5"][0], "definition of safe_learned_over_exact_anf ratio", "Exact ANF is the denominator and therefore the 1.0x reference.")

    c6_methods = c6["method_summary"]
    for split in ("test", "confirmatory"):
        baseline = c6_methods[f"truth_vector_anf/{split}"]
        packed = c6_methods[f"cached_packed_source_anf/{split}"]
        for field in ("accuracy", "canonical_partition_accuracy", "semantic_mismatches"):
            if packed[field] != (0 if field == "semantic_mismatches" else 1.0):
                raise ValueError(f"C6 cached packed {split} exactness changed: {field}")
        number(
            f"c6.{split}.median_speedup",
            baseline["median_total_ns"] / packed["median_total_ns"],
            "x6", PINNED["c6"][0],
            f"method_summary.truth_vector_anf/{split}.median_total_ns / method_summary.cached_packed_source_anf/{split}.median_total_ns",
            "Exact truth-vector ANF time divided by exact cached packed source-ANF time; above 1 favors the packed core.",
        )
        number(
            f"c6.{split}.p95_speedup",
            baseline["p95_total_ns"] / packed["p95_total_ns"],
            "x6", PINNED["c6"][0],
            f"method_summary.truth_vector_anf/{split}.p95_total_ns / method_summary.cached_packed_source_anf/{split}.p95_total_ns",
            "Exact truth-vector ANF p95 divided by exact cached packed source-ANF p95; above 1 favors the packed core.",
        )
    number("c6.dataset_rows", c6["dataset_rows"], "int", PINNED["c6"][0], "dataset_rows")
    number("c6.test_cases", c6_methods["cached_packed_source_anf/test"]["cases"], "int", PINNED["c6"][0], "method_summary.cached_packed_source_anf/test.cases")
    number("c6.confirmatory_cases", c6_methods["cached_packed_source_anf/confirmatory"]["cases"], "int", PINNED["c6"][0], "method_summary.cached_packed_source_anf/confirmatory.cases")
    number("c6.semantic_mismatches", c6["semantic_mismatches"], "int", PINNED["c6"][0], "semantic_mismatches")
    for key, value, source, field in (
        ("params_matrix_mlp", c["models"]["matrix_mlp_parameters"], PINNED["c"][0], "models.matrix_mlp_parameters"),
        ("params_matrix_cnn", c["models"]["matrix_cnn_parameters"], PINNED["c"][0], "models.matrix_cnn_parameters"),
        ("params_graph_gnn", 80001, PINNED["c3"][0], "natural GNN run model metadata"),
        ("params_natural_multitask", 82926, PINNED["c3"][0], "natural multitask GNN run model metadata"),
        ("params_fusion", c["models"]["fused_parameters"], PINNED["c"][0], "models.fused_parameters"),
        ("params_retrieval", c["models"]["graph_retrieval_parameters"], PINNED["c"][0], "models.graph_retrieval_parameters"),
        ("params_variable_mlp", c2["models"][0]["parameters"], PINNED["c2"][0], "models[variable_matrix_mlp].parameters"),
        ("params_multiscale", c2["models"][2]["parameters"], PINNED["c2"][0], "models[multiscale_cm].parameters"),
        ("params_variable_fused", c2["models"][6]["parameters"], PINNED["c2"][0], "models[variable_fused].parameters"),
        ("params_structural", c4["models"][0]["parameters"], PINNED["c4"][0], "models[structural_pair_ranker].parameters"),
        ("params_direct_cut", c4["models"][2]["parameters"], PINNED["c4"][0], "models[direct_cut_gnn].parameters"),
        ("params_cut", c5["models"][0]["parameters"], PINNED["c5"][0], "models[variable_cut_gnn].parameters"),
    ):
        number(key, value, "int", source, field)

    host_rows = []
    for host_id, host in ladder["hosts"].items():
        prefix = "gcc" if host_id.startswith("gcc") else "clang"
        number(f"{prefix}_fixed_ns", host["best_fixed_sum_ns"], "int", host["raw_path"], "sum(q64 per-case medians for best fixed arm)")
        number(f"{prefix}_oracle_ns", host["oracle_sum_ns"], "num1", host["raw_path"], "sum(q64 per-case per-arm oracle medians)")
        number(f"{prefix}_gross", host["gross_speedup"], "x9", host["raw_path"], "best_fixed_sum_ns / oracle_sum_ns")
        number(f"{prefix}_rows", host["q64_rows"], "int", host["raw_path"], "q64_rows")
        host_rows.append({"id": host_id, "label": "GCC / EPYC 9655" if prefix == "gcc" else "Clang / EPYC 9575F", "prefix": prefix, "best_fixed": host["best_fixed_method"]})
    number("ladder_cases", ladder["cross_host"]["complete_cases"], "int", ladder["input_bindings"]["cross_analysis_path"], "cross_host.complete_cases")
    number("label_agree", ladder["cross_host"]["label_agreement_cases"], "int", ladder["input_bindings"]["cross_analysis_path"], "cross_host.label_agreement_cases")
    number("label_disagree", ladder["cross_host"]["label_disagreement_cases"], "int", ladder["input_bindings"]["cross_analysis_path"], "cross_host.label_disagreement_cases")

    quality_rows = []

    def add_quality(model, split, metric, values, source, field):
        row = {"model": model, "split": split, "metric": metric}
        index = len(quality_rows)
        for name, value in values.items():
            if value is not None:
                key = f"quality_{index}_{name}"
                number(key, 100 * value, "pct1", source, f"{field}.{name}", "Historical held-out or inspected-confirmation metric; small cohorts and seed variance apply.")
                row[name] = f"ln.{key}"
        quality_rows.append(row)

    for model in ("matrix_mlp", "graph_gnn", "fused"):
        for split in ("test", "confirmatory"):
            for seed_index, value in enumerate(c["classification_balanced_accuracy"][model][split], start=1):
                add_quality(f"C {model} · seed {seed_index}", split, "balanced accuracy", {"value": value}, PINNED["c"][0], f"classification_balanced_accuracy.{model}.{split}[{seed_index - 1}]")
    for seed, values in c["retrieval_top1_exact"].items():
        add_quality(f"C retrieval · {seed.replace('_', ' ')}", "confirmatory", "top-1 exact retrieval", {"value": values["confirmatory"]}, PINNED["c"][0], f"retrieval_top1_exact.{seed}.confirmatory")
    for key, metric in c3["matched_classification"].items():
        if key.startswith("natural_graph_gnn/"):
            add_quality("C3 matched natural GNN · " + key.split("/")[1], key.split("/")[2], "balanced accuracy", {"value": metric["balanced_accuracy"], "sensitivity": metric["sensitivity"], "specificity": metric["specificity"]}, PINNED["c3"][0], f"matched_classification.{key}")
    for key, metric in c4["classification"].items():
        if key.startswith("direct_cut_gnn/"):
            add_quality("C4 direct-cut GNN · " + key.split("/")[1], key.split("/")[2], "balanced accuracy", {"value": metric["balanced_accuracy"], "sensitivity": metric["sensitivity"], "specificity": metric["specificity"], "accepted": metric["accepted_positive_recall"]}, PINNED["c4"][0], f"classification.{key}")
    for key, metric in c5["classification"].items():
        if key.startswith("variable_cut_gnn/"):
            add_quality("C5 variable-cut GNN · " + key.split("/")[1], key.split("/")[2], "balanced accuracy", {"value": metric["balanced_accuracy"], "sensitivity": metric["sensitivity"], "specificity": metric["specificity"], "accepted": metric["accepted_positive_recall"]}, PINNED["c5"][0], f"classification.{key}")
    add_quality("C2 always-abstain control", "EPFL (no positive labels)", "ordinary accuracy", {"value": c2["controls"]["epfl"]["always_abstain_accuracy"]}, PINNED["c2"][0], "controls.epfl.always_abstain_accuracy")
    for seed_index, value in enumerate(c["classification_balanced_accuracy"]["graph_gnn"]["epfl_specificity_only"], start=1):
        add_quality(f"C graph GNN · seed {seed_index}", "EPFL (no positive labels)", "specificity only", {"value": value}, PINNED["c"][0], f"classification_balanced_accuracy.graph_gnn.epfl_specificity_only[{seed_index - 1}]")

    reports = [
        ("AB", "A,F", "exact relation learning", "Synthetic exhaustive relations", "NumPy MLP and exact validator", "Plain controls", "Exact on the narrow generated task; did not establish a useful deployed decision surface.", "superseded", "docs/recognition/LEARNING_MILESTONES_AB_2026_08_29.md"),
        ("C", "A,F", "architecture transfer", "Synthetic train/test plus EPFL confirmation", "matrix MLP/CNN, graph GNN, fused and retrieval", "majority and structural controls", "Some test splits were perfect; transfer and seed behavior were inconsistent.", "negative", "docs/recognition/LEARNING_MILESTONE_C_2026_08_29.md"),
        ("C2", "A,F", "variable-size transfer", "Variable-size synthetic plus EPFL", "multiscale CNN, GNN and fusion", "exact detector", "EPFL was all-negative; specificity only, so no balanced deployment claim.", "negative", "docs/recognition/LEARNING_MILESTONE_C2_2026_08_29.md"),
        ("C3", "B,F", "natural decomposition", "Natural decompositions with held-out confirmation", "natural GNN and decoder", "structural linear", "Balanced accuracy was modest and accepted-positive recall was low.", "negative", "docs/recognition/LEARNING_MILESTONE_C3_NATURAL_DECOMPOSITION_2026_08_29.md"),
        ("C4", "B,C", "direct cut ranking", "Natural cut candidates", "cut-ranking GNN", "exact ranking/control", "Confirmation ranking improved, but test transfer and accepted coverage did not hold.", "negative", "docs/recognition/LEARNING_MILESTONE_C4_DIRECT_CUT_RANKING_2026_08_29.md"),
        ("C5", "B,C", "variable conditioned cuts", "Variable-width natural cuts", "conditioned GNN", "exact ANF control", "Equivariance stayed exact; learned safe path was slower and recall remained low.", "retained", "docs/recognition/LEARNING_MILESTONE_C5_VARIABLE_CONDITIONED_CUT_2026_08_29.md"),
        ("C6", "B,C", "packed exact source-ANF core", "Held-out test and confirmatory natural-source cohorts", "cached packed exact OR-convolution", "truth-vector exact ANF", "The exact packed core improved median and p95 timing with perfect exact/canonical accuracy; the learned hybrid and production route did not advance.", "retained", "docs/recognition/LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md"),
        ("C7–C12", "B,C", "screening, bounds and completion", "Successive natural candidate cohorts", "exact structural screens plus learned ranking probes", "analytical and exact controls", "Later work shifted to whether global-best completion could be avoided; it could not.", "superseded", "docs/recognition/LEARNING_MILESTONE_C12_ADAPTIVE_EXACT_DISPATCHER_2026_08_30.md"),
        ("C13–C15", "C,D", "backend/candidate decision surfaces", "Held-out candidate cohorts", "small policies and structural features", "fixed exact backends", "Signals appeared on restricted surfaces but did not survive stronger exact baselines or charged economics.", "negative", "docs/recognition/LEARNING_MILESTONE_C15_EXACT_CM_GF2_2026_08_30.md"),
        ("C16", "C,D", "exact-screened GF(2) tail", "Frozen natural-source and dense-control cases", "exact structural screen plus exhaustive exact fallback", "exhaustive explicit-CM GF(2) search", "The task-equivalent screened whole path preserved the exact best artifact and improved aggregate timing on Windows and Linux; a slower individual case keeps production promotion disabled.", "retained", "docs/recognition/LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md"),
        ("C17–C18", "C,D", "GF(2) routing and transfer", "Independent exact GF(2) cohorts", "task dispatch and structural features", "fixed exact backends", "The C16 exact-screening screen remained useful, but learned routing and broad transfer did not earn promotion.", "negative", "docs/recognition/LEARNING_MILESTONE_C18_INDEPENDENT_GF2_TRANSFER_2026_08_31.md"),
        ("C19–C22", "B,C", "global-best certificates", "Natural candidate universes", "ranking and completion policies", "global completion search", "C21 exposed the completion barrier; C22 retained the certificate boundary.", "blocked", "docs/recognition/LEARNING_MILESTONE_C21_TASK_MATCHED_GF2_METHOD_TABLE_2026_08_31.md"),
        ("C23–C29", "D,E", "prepared/runtime policies", "Prepared exact evaluation surfaces", "rules, predictors and shadow policies", "fixed and oracle exact arms", "Headroom narrowed as task contracts and baselines became more exact.", "negative", "docs/recognition/LEARNING_MILESTONE_C29_VARIANCE_LOCALIZATION_2026_09_01.md"),
        ("C30–C36", "D,E", "context and repeated-query routing", "Natural repeated-query cohorts", "prepared policies and shadow evaluation", "current bigint/native exact portfolio", "The final exposed portfolio selected one fixed exact method, leaving no decision to learn.", "retained", "docs/recognition/LEARNING_MILESTONE_C36_WIDE_NATURAL_REPEATED_QUERY_2026_09_01.md"),
        ("D–D4", "D,E", "exact backend and cost prediction", "Exact backend cohorts", "trees/rules and cost models", "stronger exact portfolio", "Early heterogeneity did not become an admissible, fully charged routing policy.", "superseded", "docs/recognition/LEARNING_MILESTONE_D_2026_08_29.md"),
        ("D5–D10", "D,E", "gated selectors and shadow evaluation", "Held-out/shadow exact surfaces", "abstaining policies", "fixed/oracle exact arms", "D9 abstained on every case; gate and unconditional economics were unfavorable.", "negative", "docs/recognition/LEARNING_MILESTONE_D10_INDEXED_RULE_ENGINE_2026_08_30.md"),
        ("E1–E2", "E", "analytical recognition/cost", "Exact cost surfaces", "first-occurrence control and learned cost tree", "analytical controls", "The analytical control was strongest; the learned cost tree was slower.", "retained", "docs/recognition/LEARNING_MILESTONE_E2_SAT_EQUIVALENCE_GUIDANCE_2026_08_30.md"),
        ("Reassessment", "A–F", "neural eligibility", "All exposed development evidence", "evidence synthesis; no fitting", "current exact portfolios", "No training: advice off, complete abstention, exact fallback unchanged.", "retained", "docs/research/CM_NEURAL_ARCHITECTURE_REASSESSMENT_2026_09_02.md"),
        ("Post-benchmark", "B–E", "new decision surfaces", "Verified architecture comparison", "gross/charged economics audit", "task-identical fixed and oracle arms", "A small version-history gross signal remained development-only and cost-incomplete.", "retained", "docs/research/CM_POST_BENCHMARK_NEURAL_ELIGIBILITY_2026_09_03.md"),
        ("Current protocol", "D,E", "source-blind future gate", "Frozen source-group cohort", "label-free features; fit not authorized", "majority and analytical controls", "Freeze verified with no timings, labels, models, prospective data or cloud work.", "development-only", "docs/research/CM_VERSION_HISTORY_LEARNING_PROTOCOL_2026_09_04.md"),
    ]
    artifacts = {
        "AB": "docs/recognition/learning_milestones_ab_results.json",
        "C": PINNED["c"][0], "C2": PINNED["c2"][0], "C3": PINNED["c3"][0],
        "C4": PINNED["c4"][0], "C5": PINNED["c5"][0],
        "C6": PINNED["c6"][0],
        "C7–C12": "docs/recognition/learning_milestone_c12_adaptive_dispatcher_results.json",
        "C13–C15": "docs/recognition/learning_milestone_c15_exact_cm_gf2_results.json",
        "C16": "docs/recognition/learning_milestone_c16_exact_screened_gf2_results.json",
        "C17–C18": "docs/recognition/learning_milestone_c18_independent_gf2_transfer_results.json",
        "C19–C22": "docs/recognition/learning_milestone_c21_task_matched_gf2_method_table_results.json",
        "C23–C29": "docs/recognition/learning_milestone_c29_variance_localization_results.json",
        "C30–C36": "docs/recognition/learning_milestone_c36_wide_natural_repeated_query_results.json",
        "D–D4": "docs/recognition/learning_milestone_d_results.json",
        "D5–D10": "docs/recognition/learning_milestone_d10_indexed_rule_engine_results.json",
        "E1–E2": "docs/recognition/learning_milestone_e2_sat_guidance_results.json",
        "Reassessment": "docs/research/CM_NEURAL_ARCHITECTURE_REASSESSMENT_2026_09_02.md", "Post-benchmark": PINNED["post"][0],
        "Current protocol": PINNED["freeze"][0],
    }
    timeline = []
    for milestone, task, question, cohort, method, baselines, result, status, report in reports:
        timeline.append({"milestone": milestone, "task": task, "question": question, "cohort": cohort, "method": method, "baselines": baselines, "result": result, "exactness": "Exact outputs/checks retained; learned advice never replaces exact verification.", "status": status, "continuation": "Continue only if the next frozen gate closes the stated evidence and economics gap.", "report": _href(report), "artifact": _href(artifacts[milestone])})

    links = [
        ("Deep technical dossier", "docs/research/CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md"),
        ("Learning roadmap", "docs/recognition/LEARNING_ROADMAP.md"),
        ("Neural benchmark assessment", "docs/recognition/CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md"),
        ("Neural architecture reassessment", "docs/research/CM_NEURAL_ARCHITECTURE_REASSESSMENT_2026_09_02.md"),
        ("Post-benchmark eligibility", "docs/research/CM_POST_BENCHMARK_NEURAL_ELIGIBILITY_2026_09_03.md"),
        ("Version-history learning protocol", "docs/research/CM_VERSION_HISTORY_LEARNING_PROTOCOL_2026_09_04.md"),
        ("Learning benchmark handoff contract", "docs/research/CM_LEARNING_BENCHMARK_HANDOFF_CONTRACT_2026_09_04.md"),
        ("Query-ladder learning evaluation", "docs/research/CM_QUERY_LADDER_DEVELOPMENT_LEARNING_EVALUATION_2026_09_04.md"),
        ("Decision-surface and memory-evaluation boundary", "docs/research/CM_LEARNING_DECISION_SURFACE_AND_MEMORY_EVALUATION_2026_09_09.md"),
        ("Source-blind freeze manifest", "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/MANIFEST.json"),
        ("Source-blind independent verification", "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/INDEPENDENT_VERIFICATION.json"),
    ]

    milestone_sources = []
    for milestone, report_name, artifact_name in MILESTONE_SOURCES:
        artifact_relative = f"docs/recognition/{artifact_name}"
        milestone_sources.append({
            "milestone": milestone,
            "report": _href(f"docs/recognition/{report_name}"),
            "artifact": _href(artifact_relative),
            "artifact_sha256": _sha256(ROOT / artifact_relative),
        })
    number(
        "milestone_source_pairs", len(milestone_sources), "int",
        "deliverables_n22_24/master_explainer_2026_08_03/cm_learning_neural_evidence.py",
        "len(MILESTONE_SOURCES)",
        "Explicit publication allowlist; consolidated stages are labeled as such.",
    )

    evidence = {
        "schema": "cm-learning-neural-website-evidence/v1",
        "status": "verified_read_only_no_training",
        "updated": "2026-09-10",
        "decision": "No selector or neural route is promoted. Advice remains off; every case abstains to the unchanged exact fallback.",
        "excluded_missing_artifacts": [
            {
                "path": "docs/recognition/runs/neural-architecture-reassessment-development-20260902-001/assessment.json",
                "reason": "Not present in integrated Git history; numeric claims that depended on it are intentionally not rendered.",
            },
            {
                "path": "docs/recognition/runs/neural-native-portfolio-reassessment-development-20260903-001/assessment.json",
                "reason": "Not present in integrated Git history; numeric claims that depended on it are intentionally not rendered.",
            },
        ],
        "tasks": [
            {"id": "A", "name": "Exact answers / relations", "role": "Predict a complete exact Boolean object", "verdict": "Do not replace the exact output and checker."},
            {"id": "B", "name": "Decomposition / cuts", "role": "Propose useful exact decompositions", "verdict": "Current learned proposals do not avoid certified global work."},
            {"id": "C", "name": "Partition ranking", "role": "Order exact candidate search", "verdict": "Blocked on a sound early-termination certificate."},
            {"id": "D", "name": "Exact backend selection", "role": "Choose among task-identical exact arms", "verdict": "Current exposed portfolios are fixed-winner or evidence-incomplete."},
            {"id": "E", "name": "Runtime / cost prediction", "role": "Predict exact execution cost", "verdict": "Analytical controls remain stronger; all routing costs must be charged."},
            {"id": "F", "name": "CM representation learning", "role": "Learn embeddings over CM structure", "verdict": "Research-only until a downstream task, ablation and economic gate exist."},
        ],
        "timeline": timeline,
        "c6": {
            "report": _href("docs/recognition/LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md"),
            "artifact": _href(PINNED["c6"][0]),
            "verification": _href(c6["verification"]["path"]),
            "decision": "Packed exact core advanced; learned hybrid unpromoted; production routing unchanged.",
        },
        "milestone_sources": milestone_sources,
        "quality": quality_rows,
        "models": [
            {"family": "Matrix MLP", "parameters": "ln.params_matrix_mlp", "input": "dense fixed CM tensor → binary label", "exactness": "prediction only; exact checker retained", "lesson": "Strong narrow splits did not establish stable transfer."},
            {"family": "Matrix CNN", "parameters": "ln.params_matrix_cnn", "input": "CM image-like tensor", "exactness": "prediction only", "lesson": "No durable advantage over simpler controls."},
            {"family": "Graph GNN", "parameters": "ln.params_graph_gnn", "input": "canonical source-DAG graph → label/proposal", "exactness": "equivariant proposal; exact output checked", "lesson": "Some perfect split scores coexisted with weak confirmation and low accepted recall."},
            {"family": "Fusion", "parameters": "ln.params_fusion", "input": "combined structural views", "exactness": "advisory only", "lesson": "Added representation capacity did not close deployment gates."},
            {"family": "Graph retrieval", "parameters": "ln.params_retrieval", "input": "source-DAG embedding → top-1 exact artifact", "exactness": "retrieval accepted only after exact check", "lesson": "Confirmation varied across seeds."},
            {"family": "Variable matrix MLP", "parameters": "ln.params_variable_mlp", "input": "padded variable-size CM tensor → label", "exactness": "prediction only", "lesson": "Size transfer did not survive natural evaluation."},
            {"family": "Multiscale CM", "parameters": "ln.params_multiscale", "input": "multi-resolution CM tensors → label", "exactness": "prediction only", "lesson": "Natural EPFL had no positive labels; only specificity was identifiable."},
            {"family": "Variable fusion", "parameters": "ln.params_variable_fused", "input": "variable matrix plus source graph → label", "exactness": "prediction only", "lesson": "Fusion did not close the natural transfer gate."},
            {"family": "Natural multitask GNN", "parameters": "ln.params_natural_multitask", "input": "canonical source DAG → label plus interaction edges", "exactness": "decoded proposal checked exactly", "lesson": "Auxiliary edge fit did not yield accepted exact partitions."},
            {"family": "Structural linear", "parameters": "ln.params_structural", "input": "hand-defined source features → label/rank", "exactness": "analytical comparison control", "lesson": "Simple controls were often competitive and cheaper."},
            {"family": "Direct-cut / rank GNN", "parameters": "ln.params_direct_cut", "input": "source DAG and candidate cut → label/rank", "exactness": "proposal plus exact ANF/fallback", "lesson": "Ranking gains were split- and seed-sensitive."},
            {"family": "Variable cut model", "parameters": "ln.params_cut", "input": "conditioned cut candidates", "exactness": "zero equivariance error retained", "lesson": "Safe learned path remained slower than exact ANF."},
            {"family": "CM IR / packed ANF", "parameters": None, "input": "compiler IR or source polynomial → exact output", "exactness": "exact CM-family execution/teacher, not an embedding", "lesson": "These are foundational exact controls, not learned models."},
            {"family": "Non-CM exact controls", "parameters": None, "input": "CSE-flat, direct BitSet, R2/native slots, ROBDD/CUDD, SAT/CNF", "exactness": "task-identical exact output required", "lesson": "Control identity and requested artifact must remain explicit."},
            {"family": "Trees and rules", "parameters": None, "input": "structural/cost features → abstain or exact arm", "exactness": "abstaining advice plus exact fallback", "lesson": "Analytical recognition generally dominated fitted cost policies."},
        ],
        "hosts": host_rows,
        "ladder_blockers": ladder["blockers"],
        "charged_costs": [
            {
                "key": key,
                "label": key.replace("_", " "),
                "status": "missing" if value is None else "measured",
            }
            for key, value in ladder["cost_accounting"]["required_costs_ns_per_case"].items()
        ],
        "source_blind": {
            "features": freeze["model_input_contract"]["feature_names"],
            "forbidden": freeze["model_input_contract"]["forbidden_fields"],
            "split_assignment": "SHA-256 salted source-group assignment; source group is visible only to the split auditor.",
            "freeze_sha256": PINNED["freeze"][1],
        },
        "certificate": protocol["c5_certificate_investigation"]["evaluation"]["required_properties"],
        "next_actions": {
            "now": [
                "Replay pinned verifiers and website evidence tests.",
                "Validate any future q64 package from all raw 16-block timings; reconstruct labels, economics and the v2 handoff rather than trusting aggregates.",
                "Use the split-isolated memory evaluator and its precommitted three-seed neural wrapper for synthetic guardrail testing while keeping exposed H6 cases out of training.",
                "Audit the historical H6 freeze for byte-exact or LF/CRLF-equivalent bindings without altering its strict validator.",
                "Keep candidate code disabled until a freeze-bound handoff is eligible.",
            ],
            "benchmark": [
                "Run the frozen exact cohort on two distinct physical machines.",
                "Retain every case, arm and all 16 paired q64 blocks, including ties, refusals and unfavorable rows.",
                "Generate joint cross-host labels under the precommitted materiality and abstention policy.",
                "Measure every charged p95 component on each decision-bearing host.",
                "Return a source-closed, independently verified handoff with all refusals retained.",
            ],
            "prohibited": [
                "Do not train or fit on the already inspected historical cohort.",
                "Do not read validation, audit or prospective labels before their gate permits it.",
                "Do not combine absolute timings across hosts or runs.",
                "Do not enable advice, production routing or a learned exactness bypass.",
            ],
        },
        "links": [{"label": label, "href": _href(path)} for label, path in links],
        "identities": [{"role": key, "path": relative, "sha256": digest} for key, (relative, digest) in PINNED.items()],
    }
    return evidence, numbers
