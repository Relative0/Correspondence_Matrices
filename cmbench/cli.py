from __future__ import annotations

from typing import Any, List, Tuple

from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig, config_from_args
from cmbench.context import BenchmarkRunContext, make_context


def parse_sizes(raw: str | list[int] | tuple[int, ...]) -> List[int]:
    if isinstance(raw, str):
        return [int(part) for part in raw.split(",") if part]
    return [int(part) for part in raw]


def parse_depth_sweep(config: BenchmarkConfig) -> List[int]:
    return [int(d) for d in config.depth_sweep.split(",") if d] if config.depth_sweep else [config.max_depth]


def apply_preset_args(args: Any) -> Any:
    if args.experiment == "cm_vs_bitset":
        args.cm_parallel = True
        args.no_bitset = False
    if bool(getattr(args, "compare_robdd_cm", False)):
        args.no_bitset = False
        args.no_dd = False
        args.no_robdd_dd = False
        args.cm_compare_no_reinflate = True
        args.cm_use_persistent_cache = True
        if args.robdd_order_policy == "fixed":
            args.robdd_order_policy = "best-of-k"
        if int(args.robdd_order_sweeps) < 10 and args.robdd_order_policy == "best-of-k":
            args.robdd_order_sweeps = 10
    if args.cm_compare_hybrid:
        args.no_bitset = False
    if getattr(args, "cm_compare_no_reinflate", False):
        args.no_bitset = False
    if args.cm_exec_target == "runpod":
        args.cm_compare_no_reinflate = True
    return args


def build_config_and_context(args: Any) -> Tuple[BenchmarkConfig, BenchmarkRunContext]:
    config = config_from_args(apply_preset_args(args))
    return config, make_context(config, detect_backends())
