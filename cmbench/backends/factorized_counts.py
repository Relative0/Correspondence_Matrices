"""Exact scalar counting over disjoint supports, with guarded packed leaves.

This is a conservative arithmetic plan, not a general knowledge compiler.
Partial assignments shrink packed leaves but do not repartition the plan.
"""
from __future__ import annotations

from math import prod

from bitset_backend import (
    FlatProgram, compile_expr_cse, compile_flat, _FLAT_OP_NOT as NOT,
    _FLAT_OP_AND as AND, _FLAT_OP_OR as OR, _FLAT_OP_XOR as XOR,
    _FLAT_OP_IMP as IMP, _FLAT_OP_EQV as EQV,
)
from cmbench.backends.packed_mask_cache import ordered_basis
from cmbench.backends.packed_queries import _execute, _fixed, _slice, _validate_program


class FactorizedCountPlan:
    """Count using exact integer arithmetic where child supports are disjoint.

    Overlapping arguments of associative operators form packed components.
    Every component width is checked before touching the supplied mask cache.
    Repeated XOR arguments retain their multiplicity. Counts include unused axes.
    """

    def __init__(self, program, names, *, cache):
        self.basis = ordered_basis(names)
        _validate_program(program, self.basis)
        self.cache = cache
        operations = {s: (op, args) for s, op, args in program.ops}
        loads = {s: (kind, value) for s, kind, value in program.loads}
        supports = {s: frozenset([value]) if kind == 'var' else frozenset()
                    for s, (kind, value) in loads.items()}
        for s, op, args in program.ops:
            if op not in (NOT, AND, OR, XOR, IMP, EQV):
                raise ValueError('unsupported opcode')
            supports[s] = frozenset().union(*(supports[a] for a in args))
        self._unused = frozenset(self.basis) - supports[program.root_slot]
        self._nodes, self._order = {}, []
        pending = [(program.root_slot, False)]
        while pending:
            key, finish = pending.pop()
            if finish:
                self._order.append(key)
                continue
            if key in self._nodes:
                continue
            if isinstance(key, tuple):
                op, roots = key
                leaf = _slice(program, roots)
                if len(roots) > 1:
                    leaf = FlatProgram(leaf.n_slots, leaf.root_slot, leaf.loads,
                                       leaf.ops[:-1] + ((leaf.root_slot, op, leaf.ops[-1][2]),))
                self._nodes[key] = ('packed', leaf, frozenset(leaf.load_vars))
                self._order.append(key)
                continue
            if key in loads:
                kind, value = loads[key]
                self._nodes[key] = (kind, value, supports[key])
                self._order.append(key)
                continue
            op, args = operations[key]
            children = args
            if op in (AND, OR, XOR):
                parents = list(range(len(args)))
                def find(i):
                    while parents[i] != i:
                        parents[i] = parents[parents[i]]
                        i = parents[i]
                    return i
                owner = {}
                for i, a in enumerate(args):
                    for name in supports[a]:
                        if name in owner:
                            parents[find(i)] = find(owner[name])
                        else:
                            owner[name] = i
                groups = {}
                for i, a in enumerate(args):
                    groups.setdefault(find(i), []).append(a)
                if len(groups) == 1 and len(args) > 1:
                    children = None
                else:
                    children = tuple(g[0] if len(g) == 1 else (op, tuple(g))
                                     for g in groups.values())
            elif op in (IMP, EQV) and supports[args[0]] & supports[args[1]]:
                children = None
            if children is None:
                leaf = _slice(program, [key])
                self._nodes[key] = ('packed', leaf, supports[key])
                self._order.append(key)
            else:
                self._nodes[key] = (op, children, supports[key])
                pending.append((key, True))
                pending.extend((a, False) for a in reversed(children))
        self._root = program.root_slot
        self.component_supports = tuple(s for kind, _, s in self._nodes.values() if kind == 'packed')

    @classmethod
    def from_expr(cls, expr, names, *, cache):
        return cls(compile_expr_cse(expr, flatten=True), names, cache=cache)

    @classmethod
    def from_cm_node(cls, node, names, *, cache):
        return cls(compile_flat(node), names, cache=cache)

    def count(self, fixed=None):
        context = _fixed(self.basis, fixed)
        live = {key: tuple(n for n in self.basis if n in support and n not in context)
                for key, (kind, _, support) in self._nodes.items() if kind == 'packed'}
        if any(len(names) > self.cache.max_width for names in live.values()):
            raise ValueError('component live width exceeds the configured build limit')
        values = {}
        for key in self._order:
            kind, payload, _ = self._nodes[key]
            if kind == 'var':
                pair = (1-context[payload], context[payload]) if payload in context else (1, 1)
            elif kind == 'const':
                pair = (1-int(bool(payload)), int(bool(payload)))
            elif kind == 'packed':
                ones = _execute(payload, live[key], context, self.cache).bit_count()
                pair = ((1 << len(live[key])) - ones, ones)
            else:
                children = [values[a] for a in payload]
                total = prod(z+o for z, o in children)
                if kind == NOT:
                    pair = children[0][::-1]
                elif kind == AND:
                    ones = prod(o for _, o in children)
                    pair = (total-ones, ones)
                elif kind == OR:
                    zeros = prod(z for z, _ in children)
                    pair = (zeros, total-zeros)
                elif kind == XOR:
                    balance = prod(z-o for z, o in children)
                    pair = ((total+balance)//2, (total-balance)//2)
                elif kind == IMP:
                    zeros = children[0][1] * children[1][0]
                    pair = (zeros, total-zeros)
                else:
                    ones = children[0][0]*children[1][0] + children[0][1]*children[1][1]
                    pair = (total-ones, ones)
            values[key] = pair
        return values[self._root][1] << len(self._unused - context.keys())

    def exists(self, fixed=None):
        return bool(self.count(fixed))
