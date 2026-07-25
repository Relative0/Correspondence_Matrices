from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


def _parse_sizes(raw: str | tuple[int, ...] | list[int]) -> tuple[int, ...]:
    if isinstance(raw, str):
        return tuple(int(part) for part in raw.split(",") if part)
    return tuple(int(part) for part in raw)


@dataclass(frozen=True)
class BenchmarkConfig:
    sizes: tuple[int, ...]
    trials: int
    seed: int
    max_depth: int
    full_tt_max_n: int = 16

    out_prefix: str = "bench_random_ops"
    depth_sweep: str = ""
    html: str = ""
    print_summary: bool = False
    bench_equivalence: bool = False
    bench_expression_family: bool = False
    bench_partial_contexts: bool = False
    bench_operator_difference: bool = False
    bench_cm_transformations: bool = False

    expr_style: str = "ordinary"
    require_nontrivial_expr: bool = False
    max_expr_regeneration_attempts: int = 100
    min_used_var_fraction: float = 0.75
    min_tt_density: float = 0.05
    max_tt_density: float = 0.95

    cm_layout: str = "balanced"
    cm_hybrid_threshold: int = 16
    cm_compare_hybrid: bool = False
    cm_compare_no_reinflate: bool = False
    cm_use_persistent_cache: bool = False
    cm_reuse_compiled_ir: bool = False
    cm_compile_once_per_expression: bool = False
    cm_eval_repeat: int = 1
    cm_max_full_output_vars: int = 16
    cm_max_output_bytes: int | None = 1 << 16
    cm_max_temporary_bytes: int | None = None
    cm_flat_eval: bool = False
    cm_words_eval: bool = False
    cm_exec_target: Literal["local", "runpod"] = "local"
    cm_runpod_local_mock: bool = False
    cm_runpod_smoke_test: bool = False
    cm_runpod_start: bool = False
    cm_runpod_stop: bool = False
    cm_runpod_stop_after_run: bool = False
    cm_runpod_fallback_local: bool = False

    cm_lazy: bool = False
    cm_pair: bool = False
    cm_parallel: bool = False
    cm_parallel_workers: int = 0
    cm_parallel_min_n: int = 8
    cm_parallel_min_nodes: int = 40
    cm_parallel_chunk_rows: int = 1024
    cm_parallel_chunk_elems: int = 1 << 17
    cm_parallel_min_work_elems: int = 1 << 18
    cm_parallel_no_reuse_pool: bool = False
    cm_parallel_no_shared_memory: bool = False
    cm_parallel_shared_min_cells: int = 1 << 20
    cm_debug_stats: bool = False
    cm_report_ir_breakdown: bool = False
    cm_profile_cached_exec: bool = False

    no_bitset: bool = False
    no_numba: bool = False
    no_sympy: bool = False
    no_espresso: bool = False
    no_bdd_sop: bool = False
    no_dd: bool = False
    no_robdd: bool = False
    no_robdd_dd: bool = False

    robdd_dd_backend: Literal["auto", "cudd", "autoref"] = "auto"
    robdd_order_policy: Literal["fixed", "expr", "random", "best-of-k"] = "fixed"
    robdd_order_seed: int | None = None
    robdd_order_sweeps: int = 1
    robdd_dynamic_reordering: bool = False
    robdd_reorder_method: str = "sift"
    robdd_measure_tt_extract: bool = False
    robdd_tt_extract_method: str = "all-assignments"
    robdd_tt_extract_max_n: int = 16

    sampled_correctness: int = 0

    equiv_pair_style: str = "rewritten_equiv"
    equiv_backends: str = "all"
    equiv_compare_repeat: int = 1000

    operator_diff_mode: str = "all"
    operator_pair_style: str = "related_variant"
    cm_transform_kind: str = "all"
    operator_quotient_report_matrix: bool = False
    operator_quotient_max_dense_n: int = 16

    partial_contexts: int = 100
    partial_fixed_var_count: int | None = None
    partial_fixed_var_fraction: float = 0.5
    partial_context_style: str = "random_fixed"
    partial_output_mode: str = "remaining-vars"
    partial_reuse_compiled_ir: bool = True
    partial_robdd_measure_extract: bool = False

    family_size: int = 50
    family_seed: int | None = None
    family_variant_style: str = "composition_mix"
    family_shared_blocks: int = 4
    family_mutation_rate: float = 0.15
    family_force_shared_substructure: bool = False
    family_no_robdd: bool = False
    family_robdd_shared_manager: bool = False

    large_n_safe: bool = False
    verbose: bool = False

    def validate(self) -> None:
        if self.trials < 1:
            raise ValueError("trials must be >= 1")
        if self.max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if self.full_tt_max_n < 0:
            raise ValueError("full_tt_max_n must be >= 0")
        if self.cm_eval_repeat < 1:
            raise ValueError("cm_eval_repeat must be >= 1")
        if self.cm_max_full_output_vars < 0:
            raise ValueError("cm_max_full_output_vars must be >= 0")
        if self.cm_max_output_bytes is not None and self.cm_max_output_bytes < 0:
            raise ValueError("cm_max_output_bytes must be >= 0")
        if self.cm_max_temporary_bytes is not None and self.cm_max_temporary_bytes < 0:
            raise ValueError("cm_max_temporary_bytes must be >= 0")
        if any(size < 0 for size in self.sizes):
            raise ValueError("sizes must be >= 0")
        if self.robdd_order_sweeps < 1:
            raise ValueError("robdd_order_sweeps must be >= 1")
        if self.robdd_order_policy not in {"fixed", "expr", "random", "best-of-k"}:
            raise ValueError("invalid robdd_order_policy")
        if self.cm_exec_target not in {"local", "runpod"}:
            raise ValueError("invalid cm_exec_target")
        if self.partial_output_mode not in {"remaining-vars", "full-vars"}:
            raise ValueError("invalid partial_output_mode")
        if self.partial_context_style not in {"random_fixed", "block_fixed", "sliding_window", "manufacturing_modes"}:
            raise ValueError("invalid partial_context_style")
        if self.family_size < 1:
            raise ValueError("family_size must be >= 1")
        if self.family_mutation_rate < 0:
            raise ValueError("family_mutation_rate must be >= 0")
        if not 0.0 <= self.min_tt_density <= 1.0:
            raise ValueError("min_tt_density must be in [0, 1]")
        if not 0.0 <= self.max_tt_density <= 1.0:
            raise ValueError("max_tt_density must be in [0, 1]")
        if self.min_tt_density > self.max_tt_density:
            raise ValueError("min_tt_density cannot exceed max_tt_density")


def config_from_args(args: Any) -> BenchmarkConfig:
    config = BenchmarkConfig(
        sizes=_parse_sizes(getattr(args, "sizes", ())),
        trials=int(getattr(args, "trials", 1)),
        seed=int(getattr(args, "seed", 0)),
        max_depth=int(getattr(args, "max_depth", 3)),
        full_tt_max_n=int(getattr(args, "full_tt_max_n", 16)),
        out_prefix=str(getattr(args, "out_prefix", "bench_random_ops")),
        depth_sweep=str(getattr(args, "depth_sweep", "")),
        html=str(getattr(args, "html", "")),
        print_summary=bool(getattr(args, "print_summary", False)),
        bench_equivalence=bool(getattr(args, "bench_equivalence", False)),
        bench_expression_family=bool(getattr(args, "bench_expression_family", False)),
        bench_partial_contexts=bool(getattr(args, "bench_partial_contexts", False)),
        bench_operator_difference=bool(getattr(args, "bench_operator_difference", False)),
        bench_cm_transformations=bool(getattr(args, "bench_cm_transformations", False)),
        expr_style=str(getattr(args, "expr_style", "ordinary")),
        require_nontrivial_expr=bool(getattr(args, "require_nontrivial_expr", False)),
        max_expr_regeneration_attempts=int(getattr(args, "max_expr_regeneration_attempts", 100)),
        min_used_var_fraction=float(getattr(args, "min_used_var_fraction", 0.75)),
        min_tt_density=float(getattr(args, "min_tt_density", 0.05)),
        max_tt_density=float(getattr(args, "max_tt_density", 0.95)),
        cm_layout=str(getattr(args, "cm_layout", "balanced")),
        cm_hybrid_threshold=int(getattr(args, "cm_hybrid_threshold", 16)),
        cm_compare_hybrid=bool(getattr(args, "cm_compare_hybrid", False)),
        cm_compare_no_reinflate=bool(getattr(args, "cm_compare_no_reinflate", False)),
        cm_use_persistent_cache=bool(getattr(args, "cm_use_persistent_cache", False)),
        cm_reuse_compiled_ir=bool(getattr(args, "cm_reuse_compiled_ir", False)),
        cm_compile_once_per_expression=bool(getattr(args, "cm_compile_once_per_expression", False)),
        cm_eval_repeat=int(getattr(args, "cm_eval_repeat", 1)),
        cm_max_full_output_vars=int(getattr(args, "cm_max_full_output_vars", 16)),
        cm_max_output_bytes=(
            None
            if getattr(args, "cm_max_output_bytes", 1 << 16) is None
            else int(getattr(args, "cm_max_output_bytes", 1 << 16))
        ),
        cm_max_temporary_bytes=(
            None
            if getattr(args, "cm_max_temporary_bytes", None) is None
            else int(getattr(args, "cm_max_temporary_bytes", 0))
        ),
        cm_flat_eval=bool(getattr(args, "cm_flat_eval", False)),
        cm_words_eval=bool(getattr(args, "cm_words_eval", False)),
        cm_exec_target=getattr(args, "cm_exec_target", "local"),
        cm_runpod_local_mock=bool(getattr(args, "cm_runpod_local_mock", False)),
        cm_runpod_smoke_test=bool(getattr(args, "cm_runpod_smoke_test", False)),
        cm_runpod_start=bool(getattr(args, "cm_runpod_start", False)),
        cm_runpod_stop=bool(getattr(args, "cm_runpod_stop", False)),
        cm_runpod_stop_after_run=bool(getattr(args, "cm_runpod_stop_after_run", False)),
        cm_runpod_fallback_local=bool(getattr(args, "cm_runpod_fallback_local", False)),
        cm_lazy=bool(getattr(args, "cm_lazy", False)),
        cm_pair=bool(getattr(args, "cm_pair", False)),
        cm_parallel=bool(getattr(args, "cm_parallel", False)),
        cm_parallel_workers=int(getattr(args, "cm_parallel_workers", 0)),
        cm_parallel_min_n=int(getattr(args, "cm_parallel_min_n", 8)),
        cm_parallel_min_nodes=int(getattr(args, "cm_parallel_min_nodes", 40)),
        cm_parallel_chunk_rows=int(getattr(args, "cm_parallel_chunk_rows", 1024)),
        cm_parallel_chunk_elems=int(getattr(args, "cm_parallel_chunk_elems", 1 << 17)),
        cm_parallel_min_work_elems=int(getattr(args, "cm_parallel_min_work_elems", 1 << 18)),
        cm_parallel_no_reuse_pool=bool(getattr(args, "cm_parallel_no_reuse_pool", False)),
        cm_parallel_no_shared_memory=bool(getattr(args, "cm_parallel_no_shared_memory", False)),
        cm_parallel_shared_min_cells=int(getattr(args, "cm_parallel_shared_min_cells", 1 << 20)),
        cm_debug_stats=bool(getattr(args, "cm_debug_stats", False)),
        cm_report_ir_breakdown=bool(getattr(args, "cm_report_ir_breakdown", False)),
        cm_profile_cached_exec=bool(getattr(args, "cm_profile_cached_exec", False)),
        no_bitset=bool(getattr(args, "no_bitset", False)),
        no_numba=bool(getattr(args, "no_numba", False)),
        no_sympy=bool(getattr(args, "no_sympy", False)),
        no_espresso=bool(getattr(args, "no_espresso", False)),
        no_bdd_sop=bool(getattr(args, "no_bdd_sop", False)),
        no_dd=bool(getattr(args, "no_dd", False)),
        no_robdd=bool(getattr(args, "no_robdd", False)),
        no_robdd_dd=bool(getattr(args, "no_robdd_dd", False)),
        robdd_dd_backend=getattr(args, "robdd_dd_backend", "auto"),
        robdd_order_policy=getattr(args, "robdd_order_policy", "fixed"),
        robdd_order_seed=getattr(args, "robdd_order_seed", None),
        robdd_order_sweeps=int(getattr(args, "robdd_order_sweeps", 1)),
        robdd_dynamic_reordering=bool(getattr(args, "robdd_dynamic_reordering", False)),
        robdd_reorder_method=str(getattr(args, "robdd_reorder_method", "sift")),
        robdd_measure_tt_extract=bool(getattr(args, "robdd_measure_tt_extract", False)),
        robdd_tt_extract_method=str(getattr(args, "robdd_tt_extract_method", "all-assignments")),
        robdd_tt_extract_max_n=int(getattr(args, "robdd_tt_extract_max_n", 16)),
        sampled_correctness=int(getattr(args, "sampled_correctness", 0)),
        equiv_pair_style=str(getattr(args, "equiv_pair_style", "rewritten_equiv")),
        equiv_backends=str(getattr(args, "equiv_backends", "all")),
        equiv_compare_repeat=int(getattr(args, "equiv_compare_repeat", 1000)),
        operator_diff_mode=str(getattr(args, "operator_diff_mode", "all")),
        operator_pair_style=str(getattr(args, "operator_pair_style", "related_variant")),
        cm_transform_kind=str(getattr(args, "cm_transform_kind", "all")),
        operator_quotient_report_matrix=bool(getattr(args, "operator_quotient_report_matrix", False)),
        operator_quotient_max_dense_n=int(getattr(args, "operator_quotient_max_dense_n", 16)),
        partial_contexts=int(getattr(args, "partial_contexts", 100)),
        partial_fixed_var_count=getattr(args, "partial_fixed_var_count", None),
        partial_fixed_var_fraction=float(getattr(args, "partial_fixed_var_fraction", 0.5)),
        partial_context_style=str(getattr(args, "partial_context_style", "random_fixed")),
        partial_output_mode=str(getattr(args, "partial_output_mode", "remaining-vars")),
        partial_reuse_compiled_ir=bool(getattr(args, "partial_reuse_compiled_ir", True)),
        partial_robdd_measure_extract=bool(getattr(args, "partial_robdd_measure_extract", False)),
        family_size=int(getattr(args, "family_size", 50)),
        family_seed=getattr(args, "family_seed", None),
        family_variant_style=str(getattr(args, "family_variant_style", "composition_mix")),
        family_shared_blocks=int(getattr(args, "family_shared_blocks", 4)),
        family_mutation_rate=float(getattr(args, "family_mutation_rate", 0.15)),
        family_force_shared_substructure=bool(getattr(args, "family_force_shared_substructure", False)),
        family_no_robdd=bool(getattr(args, "family_no_robdd", False)),
        family_robdd_shared_manager=bool(getattr(args, "family_robdd_shared_manager", False)),
        large_n_safe=bool(getattr(args, "large_n_safe", False)),
        verbose=bool(getattr(args, "verbose", False)),
    )
    config.validate()
    return config
