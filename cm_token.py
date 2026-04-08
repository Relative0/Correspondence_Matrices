"""
cm_token.py

4-bit token representation for 2x2 correspondence operators and constant-time
composition via tiny lookup tables (pure Python).

Bit layout (MSB→LSB):
  bits = [ (11)<<3 | (12)<<2 | (21)<<1 | (22)<<0 ]

Example: AND = [[1,0],[0,0]] -> 0b1000 = 0x8
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

MASK: int = 0xF

# Operator-name → token constants.
TOK: Dict[str, int] = {
    "AND": 0x8,
    "OR": 0xE,
    "XOR": 0x6,
    "EQV": 0x9,
    "XNOR": 0x9,
    "IFF": 0x9,
    "IMP": 0xB,  # X -> Y (bits 11,12,21,22 = 1,0,1,1)
    "=>": 0xB,
    "<=": 0xD,
    "NAND": 0x7,
    "NOR": 0x1,
    "UP": 0x4,
    "DOWN": 0x2,
    "L": 0xC,
    "R": 0xA,
    "TOP": 0xF,
    "ZERO": 0x0,
}


def cm_not(t: int) -> int:
    return (~int(t)) & MASK


def cm_transpose(t: int) -> int:
    """Swap (12) <-> (21), i.e., bits 2 <-> 1."""
    t = int(t) & MASK
    return (t & 0b1001) | ((t & 0b0010) << 1) | ((t & 0b0100) >> 1)


def cm_rot90(t: int) -> int:
    """Rotate 90° clockwise: (11)->(12)->(22)->(21)->(11)."""
    t = int(t) & MASK
    b11 = (t >> 3) & 1
    b12 = (t >> 2) & 1
    b21 = (t >> 1) & 1
    b22 = t & 1
    # New token = [b21 b11 b22 b12]
    return ((b21 << 3) | (b11 << 2) | (b22 << 1) | b12) & MASK


def cm_rot270(t: int) -> int:
    return cm_rot90(cm_rot90(cm_rot90(t)))


def cm_rot180(t: int) -> int:
    t = int(t) & MASK
    # 180°: [b11 b12 b21 b22] -> [b22 b21 b12 b11]
    return (((t & 0b0001) << 3) | ((t & 0b0010) << 1) | ((t & 0b0100) >> 1) | ((t & 0b1000) >> 3)) & MASK


def make_lut(op: str) -> List[List[int]]:
    """Build a 16x16 composition LUT for op in {AND, OR, XOR, IMP, EQV}.

    Composition is elementwise boolean on the 4 bits.
    """
    lut: List[List[int]] = [[0] * 16 for _ in range(16)]
    for a in range(16):
        for b in range(16):
            r = 0
            for k, s in enumerate((0b1000, 0b0100, 0b0010, 0b0001)):
                A = 1 if (a & s) else 0
                B = 1 if (b & s) else 0
                if op == "AND":
                    v = A & B
                elif op == "OR":
                    v = A | B
                elif op == "XOR":
                    v = A ^ B
                elif op == "IMP":
                    v = (1 - A) | B
                elif op == "EQV":
                    v = 1 - (A ^ B)
                else:
                    raise ValueError(op)
                r |= (v << (3 - k))
            lut[a][b] = r
    return lut


LUT_AND = make_lut("AND")
LUT_OR = make_lut("OR")
LUT_XOR = make_lut("XOR")
LUT_IMP = make_lut("IMP")
LUT_EQV = make_lut("EQV")


@lru_cache(maxsize=None)
def cm_compose(t1: int, t2: int, op: str) -> int:
    """Constant-time composition via table lookup."""
    t1 = int(t1) & MASK
    t2 = int(t2) & MASK
    if op == "AND":
        return LUT_AND[t1][t2]
    if op == "OR":
        return LUT_OR[t1][t2]
    if op == "XOR":
        return LUT_XOR[t1][t2]
    if op == "IMP":
        return LUT_IMP[t1][t2]
    if op == "EQV":
        return LUT_EQV[t1][t2]
    raise ValueError(op)


__all__ = [
    "TOK",
    "MASK",
    "cm_not",
    "cm_transpose",
    "cm_rot90",
    "cm_rot180",
    "cm_rot270",
    "cm_compose",
    "LUT_AND",
    "LUT_OR",
    "LUT_XOR",
    "LUT_IMP",
    "LUT_EQV",
]

