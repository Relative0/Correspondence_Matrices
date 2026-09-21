"""Opt-in bounded two-operand Boolean cut fusion research pass.

The pass propagates exact four-bit truth tokens across cuts whose boundary has
at most two structurally identified expressions.  It performs one conservative
bottom-up rewrite batch and lowers the result through existing compilers.  It is
not part of default backend selection.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from functools import lru_cache
from itertools import product
from typing import Any

from bitset_backend import compile_expr_cse, compile_flat, eval_expr_bitset, program_metrics
from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir
from cm_token import cm_compose, cm_not, cm_token_value

from .features import IneligibleExpression, postorder

BIN_TYPES = (And, Or, Xor, Imp, Eqv)
COMMUTATIVE_TYPES = (And, Or, Xor, Eqv)
OP_NAMES = {And: "AND", Or: "OR", Xor: "XOR", Imp: "IMP", Eqv: "EQV"}
PRIMITIVE_BIGINT_COST = {Not: 2, And: 1, Or: 1, Xor: 1, Imp: 3, Eqv: 3}

MAX_NODES = 4096
MAX_DEPTH = 96
MAX_NONTRIVIAL_CUTS = 8
MAX_CUT_PAIRS = 400_000
MAX_SHELL_NODES = 32
MAX_SHELL_VISITS = 1_000_000
MAX_REWRITES = 256


def _children(node: Expr) -> tuple[Expr, ...]:
    if type(node) is Var:
        return ()
    if type(node) is Not:
        return (node.a,)
    if type(node) in BIN_TYPES:
        return node.a, node.b
    raise IneligibleExpression("unsupported expression node")


def _with_children(node: Expr, children: tuple[Expr, ...]) -> Expr:
    if type(node) is Var:
        return node
    if type(node) is Not:
        return node if node.a is children[0] else Not(children[0])
    if type(node) in BIN_TYPES:
        return node if node.a is children[0] and node.b is children[1] else type(node)(*children)
    raise IneligibleExpression("unsupported expression node")


def _operator_count(expr: Expr) -> int:
    return sum(type(node) is not Var for node in postorder(expr))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class Template:
    token: int
    label: str
    expr: Expr
    bigint_ops: int
    operator_nodes: int


def _template_candidates() -> list[tuple[str, Expr]]:
    a, b = Var(0), Var(1)
    candidates: list[tuple[str, Expr]] = [
        ("a", a), ("b", b), ("not_a", Not(a)), ("not_b", Not(b)),
        ("zero_xor_aa", Xor(a, a)), ("one_eqv_aa", Eqv(a, a)),
    ]
    for op_name, ctor in (("and", And), ("or", Or), ("xor", Xor), ("imp", Imp), ("eqv", Eqv)):
        for swapped, negate_a, negate_b in product((False, True), repeat=3):
            left, right = (b, a) if swapped else (a, b)
            left = Not(left) if negate_a else left
            right = Not(right) if negate_b else right
            label = f"{op_name}_s{int(swapped)}_na{int(negate_a)}_nb{int(negate_b)}"
            candidates.append((label, ctor(left, right)))
            if op_name in ("and", "or"):
                candidates.append(("not_" + label, Not(ctor(left, right))))
    return candidates


@lru_cache(maxsize=1)
def template_table() -> tuple[dict[int, Template], str]:
    """Return the frozen declared-pool minimum table and its content digest."""
    best: dict[int, Template] = {}
    # Two variables produce exactly four packed truth bits in the token layout.
    from bitset_backend import build_bitset_env
    env = build_bitset_env(("x0", "x1"))
    for label, expr in _template_candidates():
        token = int(eval_expr_bitset(expr, env))
        metrics = program_metrics(compile_expr_cse(expr, flatten=True))
        item = Template(token, label, expr, metrics["executed_bigint_ops"], _operator_count(expr))
        prior = best.get(token)
        if prior is None or (item.bigint_ops, item.operator_nodes, item.label) < (
                prior.bigint_ops, prior.operator_nodes, prior.label):
            best[token] = item
    if set(best) != set(range(16)):
        raise RuntimeError("declared template pool does not cover all 16 functions")
    for token, item in best.items():
        for a, b in product((0, 1), repeat=2):
            if cm_token_value(token, a, b) != ((eval_expr_bitset(
                    item.expr, {"x0": 12, "x1": 10}) >> (2 * a + b)) & 1):
                raise RuntimeError("template truth proof failed")
    document = [{"token": token, "label": best[token].label,
                 "bigint_ops": best[token].bigint_ops,
                 "operator_nodes": best[token].operator_nodes,
                 "expression_v2": expr_to_json_dag(best[token].expr)} for token in range(16)]
    return best, hashlib.sha256(_canonical_bytes(document)).hexdigest()


def template_document() -> dict[str, Any]:
    table, digest = template_table()
    rows = [{"token": token, "label": table[token].label,
             "bigint_ops": table[token].bigint_ops,
             "operator_nodes": table[token].operator_nodes,
             "expression_v2": expr_to_json_dag(table[token].expr)} for token in range(16)]
    return {"schema": "cm-bounded-cut-template-table/v1", "pool": "declared-v1",
            "rows": rows, "payload_sha256": digest}


def _instantiate(template: Expr, a: Expr, b: Expr) -> Expr:
    memo: dict[int, Expr] = {}
    for node in postorder(template):
        if type(node) is Var:
            memo[id(node)] = a if node.i == 0 else b
        else:
            memo[id(node)] = _with_children(node, tuple(memo[id(child)] for child in _children(node)))
    return memo[id(template)]


def _align_token(token: int, old_frame: tuple[int, ...], frame: tuple[int, ...]) -> int:
    result = 0
    for a, b in product((0, 1), repeat=2):
        values = dict(zip(frame, (a, b)))
        old_a = values[old_frame[0]] if old_frame else 0
        old_b = values[old_frame[1]] if len(old_frame) == 2 else 0
        result |= cm_token_value(token, old_a, old_b) << (2 * a + b)
    return result


@dataclass(frozen=True)
class CutCandidate:
    root_id: int
    root_postorder: int
    frame: tuple[int, ...]
    token: int
    boundary_ids: tuple[int, ...]
    interior_ids: frozenset[int]
    raw_bigint_saving: int
    replacement_bigint_ops: int
    replacement_operator_nodes: int
    template_label: str


@dataclass(frozen=True)
class _CutState:
    token: int
    # Structural UIDs traversed inside this cut.  A cut cannot later be lifted
    # to make one of these UIDs a boundary: doing so would stop only some
    # occurrences and could exploit a dependency such as B=NOT(A).
    interior_uids: frozenset[int]


@dataclass(frozen=True)
class CutFusionResult:
    result: Expr
    proposed_result: Expr
    accepted: bool
    fallback_reason: str
    source_nodes: int
    structural_nodes: int
    token_combinations: int
    shell_visits: int
    candidate_cuts: int
    selected_rewrites: int
    removed_identity_nodes: int
    added_operator_nodes: int
    baseline_cse_metrics: dict[str, int]
    proposed_cse_metrics: dict[str, int]
    baseline_cm_metrics: dict[str, int]
    proposed_cm_metrics: dict[str, int]
    template_sha256: str
    selected: tuple[dict[str, Any], ...]
    baseline_cse_program: Any
    proposed_cse_program: Any
    baseline_cm_program: Any
    proposed_cm_program: Any

    def to_document(self) -> dict[str, Any]:
        # dataclasses.asdict() would recursively copy both Expr dataclass trees
        # before they were removed.  On large shared DAGs that defeats sharing
        # and can exceed the research memory cap merely to emit diagnostics.
        return {field.name: getattr(self, field.name) for field in fields(self)
                if field.name not in ("result", "proposed_result", "baseline_cse_program",
                                      "proposed_cse_program", "baseline_cm_program",
                                      "proposed_cm_program")}


def _validate(expr: Expr, n_vars: int) -> tuple[list[Expr], dict[int, int]]:
    if type(n_vars) is not int or not 1 <= n_vars <= 16:
        raise IneligibleExpression("ambient variable count must be in [1,16]")
    nodes = postorder(expr, max_nodes=MAX_NODES)
    depth: dict[int, int] = {}
    for node in nodes:
        if type(node) is Var:
            if node.i >= n_vars:
                raise IneligibleExpression("variable outside declared ambient basis")
            depth[id(node)] = 1
        else:
            depth[id(node)] = 1 + max(depth[id(child)] for child in _children(node))
            if depth[id(node)] > MAX_DEPTH:
                raise IneligibleExpression("expression depth exceeds 96")
    return nodes, depth


def _compile_metrics(expr: Expr):
    cse_program = compile_expr_cse(expr, flatten=True)
    cm_program = compile_flat(compile_expr_to_cm_ir(
        expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True))
    return cse_program, program_metrics(cse_program), cm_program, program_metrics(cm_program)


def optimize_cut_fusion(expr: Expr, n_vars: int) -> CutFusionResult:
    """Perform the frozen bounded pass and exact whole-program acceptance gate."""
    nodes, _depth = _validate(expr, n_vars)
    table, table_sha = template_table()
    index_by_id = {id(node): index for index, node in enumerate(nodes)}

    uid_by_id: dict[int, int] = {}
    uid_intern: dict[tuple[Any, ...], int] = {}
    uid_representative: dict[int, Expr] = {}
    fanout: dict[int, int] = {}
    for node in nodes:
        children = _children(node)
        for child in children:
            fanout[id(child)] = fanout.get(id(child), 0) + 1
        if type(node) is Var:
            key: tuple[Any, ...] = ("var", node.i)
        elif type(node) is Not:
            key = ("not", uid_by_id[id(node.a)])
        else:
            key = (type(node).__name__.lower(), uid_by_id[id(node.a)], uid_by_id[id(node.b)])
        uid = uid_intern.setdefault(key, len(uid_intern))
        uid_by_id[id(node)] = uid
        uid_representative.setdefault(uid, node)

    cuts_by_id: dict[int, dict[tuple[int, ...], _CutState]] = {}
    candidates_by_root: dict[int, list[CutCandidate]] = {}
    token_combinations = 0
    shell_visits = 0
    resource_reason = ""

    for root_index, node in enumerate(nodes):
        root_id = id(node)
        root_uid = uid_by_id[root_id]
        current: dict[tuple[int, ...], _CutState] = {
            (root_uid,): _CutState(0xC, frozenset())}
        found: dict[tuple[int, ...], _CutState] = {}
        children = _children(node)
        if type(node) is Not:
            for frame, state in cuts_by_id[id(node.a)].items():
                token_combinations += 1
                if token_combinations > MAX_CUT_PAIRS:
                    resource_reason = "token_combination_limit"
                    break
                value = _CutState(cm_not(state.token), state.interior_uids | {root_uid})
                prior = found.setdefault(frame, value)
                if prior.token != value.token:
                    raise RuntimeError("inconsistent unary cut token")
        elif type(node) in BIN_TYPES:
            for (left_frame, left_state), (right_frame, right_state) in product(
                    cuts_by_id[id(node.a)].items(), cuts_by_id[id(node.b)].items()):
                token_combinations += 1
                if token_combinations > MAX_CUT_PAIRS:
                    resource_reason = "token_combination_limit"
                    break
                frame = tuple(sorted(set(left_frame) | set(right_frame)))
                if len(frame) > 2:
                    continue
                if ((set(frame) - set(left_frame)) & left_state.interior_uids
                        or (set(frame) - set(right_frame)) & right_state.interior_uids):
                    continue
                left = _align_token(left_state.token, left_frame, frame)
                right = _align_token(right_state.token, right_frame, frame)
                token = cm_compose(left, right, OP_NAMES[type(node)])
                value = _CutState(token, (left_state.interior_uids | right_state.interior_uids
                                          | {root_uid}) - set(frame))
                prior = found.setdefault(frame, value)
                if prior.token != value.token:
                    raise RuntimeError(
                        f"inconsistent binary cut token at {root_index}: frame={frame}, "
                        f"left={left_frame}:{left_state.token}, right={right_frame}:{right_state.token}, "
                        f"prior={prior.token}, value={value.token}, node={node!r}")
        if resource_reason:
            break

        retained = sorted(found.items(), key=lambda item: (len(item[0]), item[0]))[:MAX_NONTRIVIAL_CUTS]
        current.update(retained)
        cuts_by_id[root_id] = current
        root_candidates: list[CutCandidate] = []
        for frame, state in retained:
            if frame == (root_uid,) or not frame:
                continue
            if not any(type(uid_representative[uid]) is not Var for uid in frame):
                continue
            interior: set[int] = set()
            boundaries: dict[int, list[int]] = {uid: [] for uid in frame}
            pending = [node]
            too_large = False
            while pending:
                current_node = pending.pop()
                shell_visits += 1
                if shell_visits > MAX_SHELL_VISITS:
                    resource_reason = "shell_visit_limit"
                    break
                current_id = id(current_node)
                current_uid = uid_by_id[current_id]
                if current_uid in boundaries and current_id != root_id:
                    boundaries[current_uid].append(current_id)
                    continue
                if current_id in interior:
                    continue
                interior.add(current_id)
                if len(interior) > MAX_SHELL_NODES:
                    too_large = True
                    break
                pending.extend(_children(current_node))
            if resource_reason:
                break
            if too_large or any(not boundaries[uid] for uid in frame):
                continue
            if any(inner != root_id and fanout.get(inner, 0) > 1 for inner in interior):
                continue
            original_cost = sum(PRIMITIVE_BIGINT_COST[type(next_node)]
                                for next_node in nodes if id(next_node) in interior)
            template = table[state.token]
            saving = original_cost - template.bigint_ops
            if saving <= 0:
                continue
            boundary_ids = tuple(min(boundaries[uid], key=lambda item: index_by_id[item]) for uid in frame)
            root_candidates.append(CutCandidate(
                root_id, root_index, frame, state.token, boundary_ids, frozenset(interior), saving,
                template.bigint_ops, template.operator_nodes, template.label))
        if resource_reason:
            break
        if root_candidates:
            candidates_by_root[root_id] = sorted(root_candidates, key=lambda item: (
                -item.raw_bigint_saving, item.replacement_operator_nodes, item.frame,
                item.template_label))

    baseline_cse_program, baseline_cse, baseline_cm_program, baseline_cm = _compile_metrics(expr)
    if resource_reason:
        return CutFusionResult(expr, expr, False, resource_reason, len(nodes), len(uid_intern),
            token_combinations, shell_visits, sum(map(len, candidates_by_root.values())), 0, 0, 0,
            baseline_cse, baseline_cse, baseline_cm, baseline_cm, table_sha, (),
            baseline_cse_program, baseline_cse_program, baseline_cm_program, baseline_cm_program)

    selected_by_root: dict[int, CutCandidate] = {}
    used_interior: set[int] = set()
    for node in nodes:
        if len(selected_by_root) == MAX_REWRITES:
            break
        for candidate in candidates_by_root.get(id(node), ()):
            if candidate.interior_ids.isdisjoint(used_interior):
                selected_by_root[id(node)] = candidate
                used_interior.update(candidate.interior_ids)
                break

    rebuilt: dict[int, Expr] = {}
    selected_rows = []
    for node in nodes:
        candidate = selected_by_root.get(id(node))
        if candidate is None:
            rebuilt[id(node)] = _with_children(node, tuple(rebuilt[id(child)] for child in _children(node)))
            continue
        boundary_exprs = [rebuilt[boundary_id] for boundary_id in candidate.boundary_ids]
        a = boundary_exprs[0]
        b = boundary_exprs[1] if len(boundary_exprs) == 2 else a
        rebuilt[id(node)] = _instantiate(table[candidate.token].expr, a, b)
        selected_rows.append({
            "root_postorder": candidate.root_postorder, "frame_uids": list(candidate.frame),
            "token": candidate.token, "template": candidate.template_label,
            "raw_bigint_saving": candidate.raw_bigint_saving,
            "interior_nodes": len(candidate.interior_ids),
            "replacement_operator_nodes": candidate.replacement_operator_nodes,
        })
    proposed = rebuilt[id(expr)]
    proposed_cse_program, proposed_cse, proposed_cm_program, proposed_cm = _compile_metrics(proposed)
    base_ops = baseline_cse["executed_bigint_ops"]
    new_ops = proposed_cse["executed_bigint_ops"]
    saved = base_ops - new_ops
    accepted = bool(selected_rows and saved >= 2 and saved * 10 >= base_ops
                    and proposed_cse["peak_live_word_buffers"] <= baseline_cse["peak_live_word_buffers"])
    if not selected_rows:
        reason = "no_nonoverlapping_profitable_cut"
    elif saved < 2:
        reason = "whole_program_saving_below_two_ops"
    elif saved * 10 < base_ops:
        reason = "whole_program_saving_below_ten_percent"
    elif proposed_cse["peak_live_word_buffers"] > baseline_cse["peak_live_word_buffers"]:
        reason = "peak_live_buffers_increased"
    else:
        reason = "accepted"
    return CutFusionResult(proposed if accepted else expr, proposed, accepted, reason, len(nodes),
        len(uid_intern), token_combinations, shell_visits, sum(map(len, candidates_by_root.values())),
        len(selected_rows), len(used_interior), sum(row["replacement_operator_nodes"] for row in selected_rows),
        baseline_cse, proposed_cse, baseline_cm, proposed_cm, table_sha, tuple(selected_rows),
        baseline_cse_program, proposed_cse_program, baseline_cm_program, proposed_cm_program)


__all__ = ["CutFusionResult", "optimize_cut_fusion", "template_document", "template_table"]
