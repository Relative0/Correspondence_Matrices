"""Matched BNet/CM ingress and bounded repeated-perturbation session worker.

Matched CM ingress deliberately bypasses CMIRBuilder's algebraic rewrites using
its interning primitive. Canonical CM ingress is a separately named ablation.
Neither raw compilation nor common normalization constructs a CM node.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from bitset_backend import (FlatProgram, compile_flat, _FLAT_OP_AND as AND,
                           _FLAT_OP_OR as OR, _FLAT_OP_NOT as NOT, _FLAT_OP_EQV as EQV)
from cmbench.biology_bnet import parse_bnet, require_closed_bnet
from cmbench.biology_controls import is_fixed_point, bnet_scalar_oracle, native_fixed_points
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import _slice, _execute, _fixed


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def program_hash(program):
    return hashlib.sha256(canonical_json([program.n_slots, program.root_slot, program.loads, program.ops])).hexdigest()


def raw_equation(function):
    """Direct raw BNet AST to FlatProgram, without CM/Expr conversion."""
    slots, loads, ops = {}, [], []
    pending = [(function.expression, False)]
    while pending:
        node, finish = pending.pop()
        if id(node) in slots:
            continue
        kind = node[0]
        if kind not in {"var", "const"} and not finish:
            pending.append((node, True))
            pending.extend((child, False) for child in reversed(node[1:]))
            continue
        slot = len(slots)
        slots[id(node)] = slot
        if kind in {"var", "const"}:
            loads.append((slot, kind, node[1]))
        else:
            opcode = {"not": NOT, "and": AND, "or": OR}[kind]
            ops.append((slot, opcode, tuple(slots[id(child)] for child in node[1:])))
    target = len(slots)
    loads.append((target, "var", function.target))
    ops.append((target + 1, EQV, (target, slots[id(function.expression)])))
    return FlatProgram(target + 2, target + 1, loads, ops)


def cm_equation(function, builder, *, canonical=False):
    def operation(op, children):
        if canonical:
            if op == "NOT": return builder.negate(children[0])
            if op == "AND": return builder.make_and(children)
            if op == "OR": return builder.make_or(children)
            return builder.make_eqv(*children)
        # Non-rewriting CM ingress: preserve input order/multiplicity. The
        # builder interns these CMNodes; subsequent compile_flat is unchanged.
        return builder._intern(kind="not" if op == "NOT" else "op",
            key=(op, *(child.key for child in children)),
            vars=tuple(sorted(set().union(*(set(child.vars) for child in children)))),
            const_value=None, op=op, args=tuple(children))
    nodes = {}
    pending = [(function.expression, False)]
    while pending:
        node, finish = pending.pop()
        if id(node) in nodes:
            continue
        kind = node[0]
        if kind == "var":
            nodes[id(node)] = builder.var(node[1])
        elif kind == "const":
            nodes[id(node)] = builder.const(node[1])
        elif not finish:
            pending.append((node, True))
            pending.extend((child, False) for child in reversed(node[1:]))
        else:
            nodes[id(node)] = operation({"not": "NOT", "and": "AND", "or": "OR"}[kind],
                                       tuple(nodes[id(child)] for child in node[1:]))
    return operation("EQV", (builder.var(function.target), nodes[id(function.expression)]))


def normalize_forest(programs):
    """Shared general postorder/CSE normalization; preserves operator structure.

    No algebraic, commutative, associative or idempotence rewrite is performed.
    Both ingress paths pay this identical pass. Its output retains each equation.
    """
    intern, loads, ops, roots = {}, [], [], []
    for program in programs:
        old_loads = {s: (kind, value) for s, kind, value in program.loads}
        old_ops = {s: (op, args) for s, op, args in program.ops}
        remap = {}
        pending = [(program.root_slot, False)]
        while pending:
            old, finish = pending.pop()
            if old in remap:
                continue
            if old in old_loads:
                key = ("load", *old_loads[old])
            elif not finish:
                pending.append((old, True))
                pending.extend((child, False) for child in reversed(old_ops[old][1]))
                continue
            else:
                op, args = old_ops[old]
                key = ("op", op, tuple(remap[a] for a in args))
            if key not in intern:
                slot = len(intern)
                intern[key] = slot
                if key[0] == "load": loads.append((slot, key[1], key[2]))
                else: ops.append((slot, key[1], key[2]))
            remap[old] = intern[key]
        roots.append(remap[program.root_slot])
    root = len(intern)
    if roots:
        ops.append((root, AND, tuple(roots)))
    else:
        loads.append((root, "const", 1))
    return FlatProgram(root + 1, root, loads, ops), tuple(roots)


class PreparedBNet:
    def __init__(self, functions, *, arm="raw_factorized", representation_mode="matched",
                 max_width=20, cache_bytes=64 << 20):
        require_closed_bnet(functions)
        if arm not in {"raw_factorized", "prepared_cm_factorized", "explicit_packed_cm"}:
            raise ValueError("unknown prepared arm")
        if representation_mode not in {"matched", "cm_canonical"} or (arm == "raw_factorized" and representation_mode != "matched"):
            raise ValueError("invalid ingress/representation mode")
        self.functions = functions
        self.names = tuple(f.target for f in functions)
        self.arm = arm
        self.cache = PackedMaskCache(max_bytes=cache_bytes, max_width=max_width)
        self.builder = None
        if arm == "raw_factorized":
            programs = [raw_equation(f) for f in functions]
        else:
            from cm_ir import CMIRBuilder
            self.builder = CMIRBuilder()
            self.cm_roots = tuple(cm_equation(f, self.builder, canonical=representation_mode == "cm_canonical") for f in functions)
            programs = [compile_flat(node) for node in self.cm_roots]
        self.program, self.roots = normalize_forest(programs)
        self.plans = {}

    def _plan(self, fixed=None, *, semantics="clamp"):
        fixed = _fixed(self.names, fixed)
        if semantics not in {"clamp", "condition"}:
            raise ValueError("unknown perturbation semantics")
        excluded = frozenset(fixed) if semantics == "clamp" else frozenset()
        if excluded not in self.plans:
            roots = [r for f, r in zip(self.functions, self.roots) if f.target not in excluded]
            program = _slice(self.program, roots) if roots else FlatProgram(1, 0, ((0, "const", 1),), ())
            plan = None if self.arm == "explicit_packed_cm" else FactorizedCountPlan(program, self.names, cache=self.cache)
            self.plans[excluded] = program, plan, program_hash(program)
        return fixed, self.plans[excluded]

    def prepare_queries(self, queries, *, semantics="clamp"):
        for query in queries:
            fixed, (_, plan, _) = self._plan(query, semantics=semantics)
            widths = ([len(self.names) - len(fixed)] if plan is None else
                      [len(s - fixed.keys()) for s in plan.component_supports])
            if any(width > self.cache.max_width for width in widths):
                raise ValueError("component live width exceeds configured limit")

    def query(self, fixed=None, *, semantics="clamp"):
        planning_started = time.perf_counter()
        fixed, cached = self._plan(fixed, semantics=semantics)
        lazy_planning_seconds = time.perf_counter() - planning_started
        program, plan, digest = cached
        if self.arm == "explicit_packed_cm":
            def count(context):
                live = tuple(n for n in self.names if n not in context)
                return _execute(program, live, context, self.cache).bit_count()
        else:
            count = plan.count
        count_started = time.perf_counter()
        total = count(fixed)
        count_seconds = time.perf_counter() - count_started
        witness_started = time.perf_counter()
        witness = None
        if total:
            witness = dict(fixed)
            for name in self.names:
                if name not in witness:
                    witness[name] = 0
                    if count(witness) == 0:
                        witness[name] = 1
            if not is_fixed_point(self.functions, witness, fixed=fixed, semantics=semantics):
                raise ValueError("invalid_witness: prepared plan fails original BNet")
        self.last_query_metrics = {"plan_lookup_or_lazy_preparation": lazy_planning_seconds,
                                   "count": count_seconds, "witness_and_validation": time.perf_counter() - witness_started}
        return {"count": str(total), "satisfiable": bool(total), "witness": witness,
                "witness_validated": bool(total), "witness_backend": self.arm + "_self_reduction" if total else None}, digest


def execute_session(request):
    """Worker payload only; supervisor adds process-tree resources/admission."""
    arm = request["arm"]
    reuse = request.get("reuse_mode", "retained")
    if reuse not in {"retained", "rebuild"}:
        raise ValueError("unknown reuse mode")
    source = Path(request["path"])
    started = time.perf_counter()
    phase = started
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != request["input_sha256"]:
        raise ValueError("input hash mismatch")
    functions = parse_bnet(data.decode("utf-8"))
    require_closed_bnet(functions)
    construction = time.perf_counter() - phase
    queries = request["query_schedule"]
    if hashlib.sha256(canonical_json(queries)).hexdigest() != request["query_schedule_sha256"]:
        raise ValueError("query schedule hash mismatch")
    q = request["queries"]
    if type(q) is not int or q not in {1, 8, 64} or len(queries) < q:
        raise ValueError("invalid query schedule length")
    prepared_arms = {"raw_factorized", "prepared_cm_factorized", "explicit_packed_cm"}
    if arm not in prepared_arms | {"bnet_scalar_oracle", "cadical195_enumeration"}:
        raise ValueError("unsupported worker arm")
    def prepare():
        return PreparedBNet(functions, arm=arm, representation_mode=request.get("representation_mode", "matched"),
                            max_width=request.get("max_width", 20), cache_bytes=request.get("cache_bytes", 64 << 20))
    phase = time.perf_counter()
    prepared = prepare() if arm in prepared_arms and reuse == "retained" else None
    if prepared is not None:
        prepared.prepare_queries(queries[:q], semantics=request.get("perturbation_semantics", "clamp"))
    preparation = time.perf_counter() - phase
    outputs, hashes, timings = [], [], []
    for fixed in queries[:q]:
        query_started = time.perf_counter()
        rebuild_seconds = 0.
        if arm in prepared_arms:
            if reuse == "rebuild":
                prepared = None  # release previous state before allocating its replacement
                prepared = prepare()
                prepared.prepare_queries([fixed], semantics=request.get("perturbation_semantics", "clamp"))
                rebuild_seconds = time.perf_counter() - query_started
            output, digest = prepared.query(fixed, semantics=request.get("perturbation_semantics", "clamp"))
            hashes.append(digest)
        else:
            function = bnet_scalar_oracle if arm == "bnet_scalar_oracle" else native_fixed_points
            kwargs = {"max_variables": 16} if arm == "bnet_scalar_oracle" else {"max_targets": 16}
            result = function(functions, fixed=fixed, semantics=request.get("perturbation_semantics", "clamp"), **kwargs)
            output = {"count": str(result.count), "satisfiable": bool(result.count), "witness": result.witness,
                      "witness_validated": bool(result.count), "witness_backend": result.backend if result.count else None}
        outputs.append(output)
        timings.append({"total": time.perf_counter() - query_started, "rebuild_preparation": rebuild_seconds,
                        **(prepared.last_query_metrics if prepared is not None else {})})
    return {"status": "ok", "outputs": outputs, "query_plan_sha256": hashes if arm in prepared_arms else None,
            "query_timings_seconds": timings, "timing_seconds": {"cold_construction": construction,
            "preparation": preparation, "warm_queries": sum(t["total"] for t in timings),
            "total_session": time.perf_counter() - started},
            "targets": len(functions), "function_support_width": max(len(f.regulators) for f in functions),
            "preprocessing_policy": ("bounded_bnet_parse" if arm == "bnet_scalar_oracle" else
                                     "parsimonious_definitional_cnf_and_cadical_defaults" if arm == "cadical195_enumeration" else
                                     "CM_algebraic_rewrites" if request.get("representation_mode") == "cm_canonical" else
                                     "same_general_postorder_CSE_no_algebraic_rewrites")}


def worker_main(path):
    request = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        result = execute_session(request)
    except (ValueError, MemoryError, ImportError) as exc:
        reason = str(exc)
        status = ("resource_limit" if isinstance(exc, MemoryError) else "unavailable" if isinstance(exc, ImportError)
                  else "unsupported" if "width" in reason or "bounds exceeded" in reason else
                  "invalid_witness" if "invalid_witness" in reason else "parse_error")
        result = {"status": status, "outputs": None, "failure_reason": reason}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True)
    worker_main(parser.parse_args().worker)
