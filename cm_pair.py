from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cm_token import cm_compose


@dataclass(frozen=True)
class PairNode:
    xl: str  # left operand variable name
    xr: str  # right operand variable name
    tok: int  # 4-bit token encoding the 2x2 operator


def compose_pair(p1: PairNode, p2: PairNode, op: str) -> Optional[PairNode]:
    """If pairs align on operands, compose in O(1) via token LUTs."""
    if p1.xl == p2.xl and p1.xr == p2.xr:
        return PairNode(p1.xl, p1.xr, cm_compose(p1.tok, p2.tok, op))
    return None


__all__ = ["PairNode", "compose_pair"]

