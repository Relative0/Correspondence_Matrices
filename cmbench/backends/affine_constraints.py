"""Exact affine constraint counts over GF(2), without truth-table expansion."""
from __future__ import annotations

from bitset_backend import (
    compile_expr_cse, compile_flat, _FLAT_OP_AND as AND, _FLAT_OP_NOT as NOT,
    _FLAT_OP_XOR as XOR, _FLAT_OP_EQV as EQV,
)
from cmbench.backends.packed_mask_cache import ordered_basis
from cmbench.backends.packed_queries import _validate_program


class AffineConstraintPlan:
    """Rows encode Hx=b, with bit i corresponding to names[i].

    The explicit row and basis limits guard admission. This recognizes affine
    conjuncts only; nonlinear formulas are refused, never approximated.
    Each query eliminates its residual system independently with Python integers.
    """

    def __init__(self, rows, rhs, names, *, max_width=8192, max_rows=16384):
        if type(max_width) is not int or max_width < 0 or type(max_rows) is not int or max_rows < 0:
            raise ValueError('limits must be nonnegative integers')
        self.basis = ordered_basis(names)
        if len(self.basis) > max_width:
            raise ValueError('basis width exceeds limit')
        # Bounded consumption also handles generators safely.
        def bounded(items):
            result = []
            for item in items:
                if len(result) >= max_rows:
                    raise ValueError('constraint count exceeds limit')
                result.append(item)
            return tuple(result)
        self.rows, self.rhs = bounded(rows), bounded(rhs)
        if len(self.rows) != len(self.rhs):
            raise ValueError('row and RHS counts differ')
        if any(type(r) is not int or r < 0 or r.bit_length() > len(self.basis) for r in self.rows):
            raise ValueError('row lies outside basis')
        if any(type(b) not in (int, bool) or b not in (0, 1) for b in self.rhs):
            raise ValueError('RHS must be Boolean')
        self._positions = {name: i for i, name in enumerate(self.basis)}

    @classmethod
    def from_program(cls, program, names, **limits):
        basis = ordered_basis(names)
        # Validate limits before constructing support integers.
        cls((), (), basis, **limits)
        _validate_program(program, basis)
        positions = {n: i for i, n in enumerate(basis)}
        values = {s: (1 << positions[v], 0) if k == 'var' else (0, int(bool(v)))
                  for s, k, v in program.loads}
        operations = {s: (op, args) for s, op, args in program.ops}
        roots, pending, seen = [], [program.root_slot], set()
        while pending:
            s = pending.pop()
            if s in seen:
                continue
            seen.add(s)
            if s in operations and operations[s][0] == AND:
                pending.extend(operations[s][1])
            else:
                roots.append(s)
        needed, pending = set(), list(roots)
        while pending:
            s = pending.pop()
            if s in needed:
                continue
            needed.add(s)
            if s in operations:
                op, args = operations[s]
                if op not in (NOT, XOR, EQV):
                    raise ValueError('non-affine constraint')
                pending.extend(args)
        for s, op, args in program.ops:
            if s not in needed:
                continue
            mask, constant = 0, int(op in (NOT, EQV))
            for a in args:
                mask ^= values[a][0]
                constant ^= values[a][1]
            values[s] = (mask, constant)
        return cls((values[s][0] for s in roots), (1 ^ values[s][1] for s in roots), basis, **limits)

    @classmethod
    def from_expr(cls, expr, names, **limits):
        return cls.from_program(compile_expr_cse(expr, flatten=True), names, **limits)

    @classmethod
    def from_cm_node(cls, node, names, **limits):
        return cls.from_program(compile_flat(node), names, **limits)

    def _context(self, fixed):
        context = dict(fixed or {})
        if any(name not in self._positions for name in context):
            raise ValueError('fixed variable is outside the declared basis')
        if any(type(value) not in (int, bool) or value not in (0, 1) for value in context.values()):
            raise ValueError('fixed values must be Boolean 0 or 1')
        return context

    def count(self, fixed=None):
        context = self._context(fixed)
        fixed_mask = sum(1 << self._positions[n] for n in context)
        ones = sum(1 << self._positions[n] for n, v in context.items() if v)
        pivots = {}
        for row, rhs in zip(self.rows, self.rhs):
            # Coefficients sit above the RHS bit so elimination cannot pivot on b.
            residual = ((row & ~fixed_mask) << 1) | (rhs ^ ((row & ones).bit_count() & 1))
            while residual > 1:
                pivot = residual.bit_length()
                if pivot not in pivots:
                    pivots[pivot] = residual
                    break
                residual ^= pivots[pivot]
            if residual == 1:
                return 0
        return 1 << (len(self.basis) - len(context) - len(pivots))

    def exists(self, fixed=None):
        return bool(self.count(fixed))


def parse_alist(text, *, max_width=8192, max_rows=16384):
    """Read an alist matrix, checking both redundant adjacency directions.

    Whitespace and optional zero padding are accepted. Duplicate edges, invalid
    degrees, inconsistent adjacency and trailing records are rejected.
    """
    lines = [list(map(int, line.split())) for line in text.splitlines() if line.strip()]
    if len(lines) < 4 or len(lines[0]) != 2 or len(lines[1]) != 2:
        raise ValueError('invalid alist header')
    n, m = lines[0]
    if not 0 < n <= max_width or not 0 < m <= max_rows or len(lines) != 4+n+m:
        raise ValueError('alist dimensions or record count invalid')
    dc, dr = lines[2:4]
    if len(dc) != n or len(dr) != m or lines[1] != [max(dc), max(dr)]:
        raise ValueError('invalid alist degrees')
    def edges(record, degree, bound):
        result = [v for v in record if v]
        if len(result) != degree or len(set(result)) != degree or any(not 1 <= v <= bound for v in result):
            raise ValueError('invalid alist adjacency')
        return result
    rows = [0] * m
    for i in range(n):
        for j in edges(lines[4+i], dc[i], m):
            rows[j-1] |= 1 << i
    for j in range(m):
        expected = sum(1 << (i-1) for i in edges(lines[4+n+j], dr[j], n))
        if rows[j] != expected:
            raise ValueError('alist adjacency directions disagree')
    return n, tuple(rows)
