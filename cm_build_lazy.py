"""
cm_build_lazy.py
Lazy CM wrapper backed by the shared symbolic CM IR.
"""
from typing import Dict, List, Optional

import numpy as np

from cm_ir import (
    clear_cm_ir_alignment_cache,
    cm_ir_alignment_cache_stats,
    compile_expr_to_cm_ir,
    materialize_cm,
)


def lazy_align_cache_stats() -> Dict[str, int]:
    return cm_ir_alignment_cache_stats()


def clear_lazy_align_cache() -> None:
    clear_cm_ir_alignment_cache()


def compile_expr_to_cm_lazy(
    e,
    R: List[str],
    C: List[str],
    fixed: Dict[str, int],
    *,
    diagnostics: Optional[Dict[str, int]] = None,
    materialize_mode: str = "partial_hybrid",
    hybrid_threshold: int = 7,
    reuse_compiled_ir: bool = False,
    use_persistent_cache: bool = False,
) -> np.ndarray:
    node = compile_expr_to_cm_ir(
        e,
        diagnostics=diagnostics,
        reuse_cache=reuse_compiled_ir,
        persistent_cache=use_persistent_cache,
    )
    return materialize_cm(
        node,
        R,
        C,
        fixed,
        diagnostics=diagnostics,
        materialize_mode=materialize_mode,
        hybrid_threshold=hybrid_threshold,
    )
