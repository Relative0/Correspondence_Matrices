"""D10 bounded proved motif pack with indexed no-op bypass and exact cone cache.

The JSON rule pack is inert evidence.  Executable matching stays in this fixed
module and accepts a pack only after reproducing every exhaustive truth row.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .features import postorder, structural_digest
from .portfolio import admit, reference_bits
from .proved_rules import canonical

SCHEMA = "crse-d10-proved-motif-pack/v1"
PACK_ID = "boolean-source-motifs-d10/v1"
MUX_RULE = "mux-shannon-xor/v1"
COMPARATOR_RULE = "comparator-shared-enable/v1"
CARRY_RULE = "adder-carry-majority/v1"
CANCEL_RULE = "arithmetic-xor-cancel/v1"
RULE_PRIORITY = (CANCEL_RULE, CARRY_RULE, COMPARATOR_RULE, MUX_RULE)
SIDE_CONDITIONS = (
    "repeated metavariables bind to structurally identical pure Boolean expressions",
    "the source expression is admitted by the bounded CRSE Boolean contract",
    "an executable rewrite must strictly decrease identity-DAG operator count",
)


def _rule_exprs(rule_id: str) -> tuple[Expr, Expr, tuple[str, ...]]:
    a, b, c, d, e = (Var(index) for index in range(5))
    if rule_id == MUX_RULE:
        return (Or(And(a, b), And(Not(a), c)),
                Xor(c, And(a, Xor(b, c))), ("S", "T", "F"))
    if rule_id == COMPARATOR_RULE:
        return (Or(And(e, And(a, Not(b))), And(e, And(c, Not(d)))),
                And(e, Or(And(a, Not(b)), And(c, Not(d)))),
                ("A", "B", "C", "D", "E"))
    if rule_id == CARRY_RULE:
        return (Or(Or(And(a, b), And(a, c)), And(b, c)),
                Or(And(a, b), And(c, Or(a, b))), ("A", "B", "C"))
    if rule_id == CANCEL_RULE:
        return Xor(Xor(a, b), Xor(a, c)), Xor(b, c), ("A", "B", "C")
    raise ValueError("unknown D10 motif rule")


def _metadata(rule_id: str) -> dict[str, Any]:
    lhs, rhs, metavariables = _rule_exprs(rule_id)
    descriptors = {
        # Support counts describe the concrete source cone, not the number of
        # metavariables: a metavariable may bind a multi-variable subexpression.
        MUX_RULE: ("or", 2, "or:and,and", 1, 16, "two-level mux tree"),
        COMPARATOR_RULE: ("or", 2, "or:and,and", 1, 16, "enabled comparator slice"),
        CARRY_RULE: ("or", 2, "or:and,or", 1, 16, "three-input carry majority"),
        CANCEL_RULE: ("xor", 2, "xor:xor,xor", 1, 16, "repeated arithmetic XOR cone"),
    }
    root, arity, digest, minimum, maximum, label = descriptors[rule_id]
    return {
        "rule_id": rule_id,
        "label": label,
        "metavariables": list(metavariables),
        "domain": "pure total Boolean values {0,1}",
        "pattern": expr_to_json_dag(lhs),
        "replacement": expr_to_json_dag(rhs),
        "index": {"root_op": root, "arity": arity, "shallow_digest": digest,
                  "support_min": minimum, "support_max": maximum},
        "commutative_operators": ["and", "or", "xor"],
        "side_conditions": list(SIDE_CONDITIONS),
        "termination_measure": "strict_identity_dag_operator_count_decrease",
        "proof_method": "exhaustive truth-vector equality over all metavariables",
    }


def _proof_rows(rule_id: str) -> list[dict[str, Any]]:
    lhs, rhs, metavariables = _rule_exprs(rule_id)
    left, right = reference_bits(lhs, len(metavariables)), reference_bits(rhs, len(metavariables))
    if left != right:
        raise RuntimeError(f"D10 proof failed for {rule_id}")
    rows = []
    for assignment in range(1 << len(metavariables)):
        values = {name: (assignment >> (len(metavariables) - 1 - index)) & 1
                  for index, name in enumerate(metavariables)}
        value = (left >> assignment) & 1
        rows.append({"assignment": values, "lhs": value, "rhs": value})
    return rows


@dataclass(frozen=True)
class D10RulePack:
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return self.document["payload_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.document, allow_nan=False))

    @classmethod
    def from_dict(cls, data: Any) -> "D10RulePack":
        keys = {"schema", "pack_id", "priority", "rules", "payload_sha256"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid D10 rule-pack fields")
        payload = {key: data[key] for key in keys - {"payload_sha256"}}
        if (data["schema"] != SCHEMA or data["pack_id"] != PACK_ID
                or data["priority"] != list(RULE_PRIORITY)
                or hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]
                or type(data["rules"]) is not list or len(data["rules"]) != len(RULE_PRIORITY)):
            raise ValueError("invalid D10 rule-pack identity")
        for rule, rule_id in zip(data["rules"], RULE_PRIORITY):
            metadata, rows = _metadata(rule_id), _proof_rows(rule_id)
            expected_keys = set(metadata) | {"proof_rows", "proof_rows_sha256"}
            if type(rule) is not dict or set(rule) != expected_keys:
                raise ValueError("invalid D10 proved-rule fields")
            if ({key: rule[key] for key in metadata} != metadata
                    or rule["proof_rows"] != rows
                    or rule["proof_rows_sha256"] != hashlib.sha256(canonical(rows)).hexdigest()):
                raise ValueError("D10 proved-rule replay disagreement")
        return cls(json.loads(json.dumps(data, allow_nan=False)))

    def save(self, path: Path) -> None:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(self.document, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    @classmethod
    def load(cls, path: Path) -> "D10RulePack":
        raw = path.read_bytes()
        if len(raw) > 131_072:
            raise ValueError("D10 rule pack exceeds 128 KiB")
        return cls.from_dict(_strict_json(raw))


def prove_d10_rule_pack() -> D10RulePack:
    rules = []
    for rule_id in RULE_PRIORITY:
        rows = _proof_rows(rule_id)
        rules.append({**_metadata(rule_id), "proof_rows": rows,
                      "proof_rows_sha256": hashlib.sha256(canonical(rows)).hexdigest()})
    payload = {"schema": SCHEMA, "pack_id": PACK_ID,
               "priority": list(RULE_PRIORITY), "rules": rules}
    return D10RulePack.from_dict({**payload,
        "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()})


def _strict_json(raw: bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))


def _children(node: Expr) -> tuple[Expr, ...]:
    if isinstance(node, Var):
        return ()
    if isinstance(node, Not):
        return (node.a,)
    if isinstance(node, (And, Or, Xor, Imp, Eqv)):
        return (node.a, node.b)
    raise TypeError(node)


def _with_children(node: Expr, children: tuple[Expr, ...]) -> Expr:
    if isinstance(node, Var):
        return node
    if isinstance(node, Not):
        return node if node.a is children[0] else Not(children[0])
    return node if node.a is children[0] and node.b is children[1] else type(node)(*children)


def _op_name(node: Expr) -> str:
    return type(node).__name__.lower()


def _shallow_key(node: Expr) -> tuple[str, int, str]:
    children = _children(node)
    names = sorted(_op_name(child) for child in children)
    root = _op_name(node)
    return root, len(children), f"{root}:{','.join(names)}"


def _operator_count(expr: Expr) -> int:
    # The v2 serializer maximizes structural sharing.  Counting its canonical
    # definitions keeps the termination measure stable across save/reload even
    # when a source AST used identity sharing less aggressively.
    return sum(node["op"] != "var" for node in expr_to_json_dag(expr)["nodes"])


def _uid(node: Expr, uid_by_id: dict[int, int], intern: dict[tuple[Any, ...], int]) -> int:
    if isinstance(node, Var):
        key: tuple[Any, ...] = ("var", int(node.i))
    elif isinstance(node, Not):
        key = ("not", uid_by_id[id(node.a)])
    else:
        a, b = uid_by_id[id(node.a)], uid_by_id[id(node.b)]
        if isinstance(node, (And, Or, Xor)) and b < a:
            a, b = b, a
        key = (_op_name(node), a, b)
    value = intern.get(key)
    if value is None:
        value = intern[key] = len(intern)
    uid_by_id[id(node)] = value
    return value


def _same(a: Expr, b: Expr, uid_by_id: dict[int, int]) -> bool:
    return uid_by_id[id(a)] == uid_by_id[id(b)]


def _signed_and(node: Expr) -> bool:
    return isinstance(node, And) and (isinstance(node.a, Not) or isinstance(node.b, Not))


@dataclass(frozen=True)
class D10Rewrite:
    result: Expr
    source_sha256: str
    result_sha256: str
    pack_sha256: str
    visited_nodes: int
    proposals: int
    selected_sites: int
    conflicts: int
    applications: int
    rejected: int
    applications_by_rule: dict[str, int]
    match_ns: int
    candidate_ns: int
    bypassed: bool
    screen_ns: int
    screen_candidate_sites: int
    provenance: tuple[dict[str, Any], ...]


class CompiledD10RulePack:
    """Fixed matcher pre-indexed by root, arity, digest, and support bounds."""

    def __init__(self, pack: D10RulePack):
        checked = D10RulePack.from_dict(pack.to_dict())
        self.pack_sha256 = checked.digest
        self.rule_ids = tuple(checked.document["priority"])
        self._index: dict[tuple[str, int, str], tuple[tuple[str, int, int], ...]] = {}
        staging: dict[tuple[str, int, str], list[tuple[str, int, int]]] = {}
        for rule in checked.document["rules"]:
            item = rule["index"]
            key = (item["root_op"], item["arity"], item["shallow_digest"])
            staging.setdefault(key, []).append((rule["rule_id"], item["support_min"], item["support_max"]))
        self._index = {key: tuple(values) for key, values in staging.items()}

    @staticmethod
    def _support_masks(nodes: list[Expr]) -> dict[int, int]:
        masks: dict[int, int] = {}
        for node in nodes:
            if isinstance(node, Var):
                masks[id(node)] = 1 << node.i
            elif isinstance(node, Not):
                masks[id(node)] = masks[id(node.a)]
            else:
                masks[id(node)] = masks[id(node.a)] | masks[id(node.b)]
        return masks

    def _screen(self, nodes: list[Expr]) -> tuple[dict[int, tuple[str, ...]], int]:
        supports = self._support_masks(nodes)
        sites: dict[int, tuple[str, ...]] = {}
        for node in nodes:
            entries = self._index.get(_shallow_key(node), ())
            count = supports[id(node)].bit_count()
            eligible = tuple(rule_id for rule_id, minimum, maximum in entries
                             if minimum <= count <= maximum)
            if eligible:
                sites[id(node)] = eligible
        return sites, len(sites)

    @staticmethod
    def _mux(node: Expr, uids: dict[int, int]) -> tuple[Expr, ...] | None:
        if not isinstance(node, Or) or not isinstance(node.a, And) or not isinstance(node.b, And):
            return None
        for positive, negative in ((node.a, node.b), (node.b, node.a)):
            for s_index, selector in enumerate((positive.a, positive.b)):
                true_value = (positive.a, positive.b)[1 - s_index]
                for n_index, complement in enumerate((negative.a, negative.b)):
                    if isinstance(complement, Not) and _same(selector, complement.a, uids):
                        false_value = (negative.a, negative.b)[1 - n_index]
                        return selector, true_value, false_value
        return None

    @staticmethod
    def _comparator(node: Expr, uids: dict[int, int]) -> tuple[Expr, ...] | None:
        if not isinstance(node, Or) or not isinstance(node.a, And) or not isinstance(node.b, And):
            return None
        left, right = (node.a.a, node.a.b), (node.b.a, node.b.b)
        for li, left_term in enumerate(left):
            for ri, right_term in enumerate(right):
                left_body, right_body = left[1 - li], right[1 - ri]
                if (_same(left_term, right_term, uids)
                        and _signed_and(left_body) and _signed_and(right_body)):
                    return left_term, left_body, right_body
        return None

    @staticmethod
    def _carry(node: Expr, uids: dict[int, int]) -> tuple[Expr, ...] | None:
        if not isinstance(node, Or):
            return None
        stack, terms = [node], []
        while stack:
            current = stack.pop()
            if isinstance(current, Or):
                stack.extend((current.a, current.b))
            else:
                terms.append(current)
        if len(terms) != 3 or any(not isinstance(term, And) for term in terms):
            return None
        by_uid: dict[int, Expr] = {}
        edges = set()
        for term in terms:
            a_uid, b_uid = uids[id(term.a)], uids[id(term.b)]
            if a_uid == b_uid:
                return None
            by_uid.setdefault(a_uid, term.a)
            by_uid.setdefault(b_uid, term.b)
            edges.add(tuple(sorted((a_uid, b_uid))))
        ordered = sorted(by_uid)
        if len(ordered) != 3 or edges != {tuple(sorted(pair)) for pair in itertools.combinations(ordered, 2)}:
            return None
        return tuple(by_uid[value] for value in ordered)

    @staticmethod
    def _cancel(node: Expr, uids: dict[int, int]) -> tuple[Expr, ...] | None:
        if not isinstance(node, Xor) or not isinstance(node.a, Xor) or not isinstance(node.b, Xor):
            return None
        left, right = (node.a.a, node.a.b), (node.b.a, node.b.b)
        for li, left_term in enumerate(left):
            for ri, right_term in enumerate(right):
                if _same(left_term, right_term, uids):
                    return left_term, left[1 - li], right[1 - ri]
        return None

    def _match(self, rule_id: str, node: Expr, uids: dict[int, int]) -> tuple[Expr, ...] | None:
        if rule_id == CANCEL_RULE:
            return self._cancel(node, uids)
        if rule_id == CARRY_RULE:
            return self._carry(node, uids)
        if rule_id == COMPARATOR_RULE:
            return self._comparator(node, uids)
        if rule_id == MUX_RULE:
            return self._mux(node, uids)
        raise ValueError("unsupported D10 rule")

    @staticmethod
    def _candidate(rule_id: str, values: tuple[Expr, ...], uids: dict[int, int],
                   intern: dict[tuple[Any, ...], int]) -> Expr:
        if rule_id == CANCEL_RULE:
            result = Xor(values[1], values[2])
            _uid(result, uids, intern)
            return result
        if rule_id == CARRY_RULE:
            a, b, c = values
            ab, a_or_b = And(a, b), Or(a, b)
            _uid(ab, uids, intern); _uid(a_or_b, uids, intern)
            second = And(c, a_or_b); _uid(second, uids, intern)
            result = Or(ab, second); _uid(result, uids, intern)
            return result
        if rule_id == COMPARATOR_RULE:
            body = Or(values[1], values[2]); _uid(body, uids, intern)
            result = And(values[0], body); _uid(result, uids, intern)
            return result
        if rule_id == MUX_RULE:
            selector, true_value, false_value = values
            delta = Xor(true_value, false_value); _uid(delta, uids, intern)
            selected = And(selector, delta); _uid(selected, uids, intern)
            result = Xor(false_value, selected); _uid(result, uids, intern)
            return result
        raise ValueError("unsupported D10 rule")

    def rewrite(self, expr: Expr, n_vars: int, *, max_nodes: int = 4096,
                max_applications: int = 256, index_mode: str = "indexed",
                verify: Callable[[str, Expr, Expr], bool] | None = None) -> D10Rewrite:
        admit(expr, n_vars, 1)
        nodes = postorder(expr)
        if (len(nodes) > max_nodes or not 1 <= max_applications <= 256
                or index_mode not in {"indexed", "full_scan"}):
            raise ValueError("D10 rewrite bounds exceeded")
        source_sha = structural_digest(expr)
        started = time.perf_counter_ns()
        if index_mode == "indexed":
            sites, screen_sites = self._screen(nodes)
        else:
            sites = {id(node): self.rule_ids for node in nodes if not isinstance(node, Var)}
            screen_sites = len(sites)
        screen_ns = max(1, time.perf_counter_ns() - started)
        zero = {rule_id: 0 for rule_id in self.rule_ids}
        if not sites:
            return D10Rewrite(expr, source_sha, source_sha, self.pack_sha256, len(nodes),
                              0, 0, 0, 0, 0, zero, 0, 0, True, screen_ns, 0, ())
        memo: dict[int, Expr] = {}
        uids: dict[int, int] = {}
        intern: dict[tuple[Any, ...], int] = {}
        proposals = selected = conflicts = applications = rejected = 0
        match_ns = candidate_ns = 0
        counts = dict(zero)
        provenance = []
        for site_index, original in enumerate(nodes):
            children = tuple(memo[id(child)] for child in _children(original))
            rebuilt = _with_children(original, children)
            _uid(rebuilt, uids, intern)
            eligible = sites.get(id(original), ())
            matches = []
            if eligible:
                match_started = time.perf_counter_ns()
                for rule_id in eligible:
                    values = self._match(rule_id, rebuilt, uids)
                    if values is not None:
                        matches.append((rule_id, values))
                match_ns += time.perf_counter_ns() - match_started
            proposals += len(matches)
            if matches:
                selected += 1
                conflicts += int(len(matches) > 1)
                rule_id, values = matches[0]
                candidate_started = time.perf_counter_ns()
                candidate = self._candidate(rule_id, values, uids, intern)
                candidate_ns += time.perf_counter_ns() - candidate_started
                before, after = _operator_count(rebuilt), _operator_count(candidate)
                accepted = after < before and (verify is None or verify(rule_id, rebuilt, candidate))
                if accepted:
                    if applications == max_applications:
                        raise ValueError("D10 application bound exceeded")
                    provenance.append({"site_postorder": site_index, "rule_id": rule_id,
                                       "before_sha256": structural_digest(rebuilt),
                                       "after_sha256": structural_digest(candidate),
                                       "operator_count_before": before,
                                       "operator_count_after": after})
                    rebuilt = candidate
                    applications += 1
                    counts[rule_id] += 1
                else:
                    rejected += 1
            memo[id(original)] = rebuilt
        result = memo[id(expr)]
        return D10Rewrite(result, source_sha, structural_digest(result), self.pack_sha256,
                          len(nodes), proposals, selected, conflicts, applications, rejected,
                          counts, match_ns, candidate_ns, False, screen_ns, screen_sites,
                          tuple(provenance))


def compile_d10_rule_pack(pack: D10RulePack) -> CompiledD10RulePack:
    return CompiledD10RulePack(pack)


@dataclass(frozen=True)
class D10CacheResult:
    cone_id: str
    result: Expr
    cache_hit: bool
    invalidated: bool
    reason: str
    identity_ns: int
    rewrite_ns: int
    rewrite: D10Rewrite


class D10ConeCache:
    """Exact changed-cone cache; serialization records each cone's variable count."""

    def __init__(self, max_entries: int = 256):
        if type(max_entries) is not int or not 1 <= max_entries <= 256:
            raise ValueError("invalid D10 cache bound")
        self.max_entries = max_entries
        self._entries: dict[str, tuple[bytes, str, int, D10Rewrite]] = {}

    @property
    def size(self) -> int:
        return len(self._entries)

    def rewrite(self, cone_id: str, expr: Expr, matcher: CompiledD10RulePack,
                n_vars: int) -> D10CacheResult:
        if type(cone_id) is not str or not cone_id or len(cone_id) > 128:
            raise ValueError("invalid D10 cone identity")
        started = time.perf_counter_ns()
        source = canonical(expr_to_json_dag(expr))
        identity = hashlib.sha256(source).hexdigest()
        identity_ns = max(1, time.perf_counter_ns() - started)
        prior = self._entries.get(cone_id)
        if prior is not None and prior[:3] == (source, matcher.pack_sha256, n_vars):
            return D10CacheResult(cone_id, prior[3].result, True, False,
                                  "unchanged_structural_identity", identity_ns, 0, prior[3])
        if prior is None and len(self._entries) == self.max_entries:
            raise ValueError("D10 cache entry bound exceeded")
        reason = ("cold_miss" if prior is None else "pack_changed" if prior[1] != matcher.pack_sha256
                  else "variable_count_changed" if prior[2] != n_vars else "source_changed")
        started = time.perf_counter_ns()
        rewrite = matcher.rewrite(expr, n_vars)
        rewrite_ns = max(1, time.perf_counter_ns() - started)
        self._entries[cone_id] = (source, matcher.pack_sha256, n_vars, rewrite)
        return D10CacheResult(cone_id, rewrite.result, False, prior is not None, reason,
                              identity_ns, rewrite_ns, rewrite)

    def invalidate_missing(self, active_cone_ids: set[str]) -> int:
        if type(active_cone_ids) is not set or any(type(value) is not str for value in active_cone_ids):
            raise ValueError("invalid D10 active cone set")
        missing = [key for key in self._entries if key not in active_cone_ids]
        for key in missing:
            del self._entries[key]
        return len(missing)

    def to_document(self) -> dict[str, Any]:
        entries = []
        for cone_id in sorted(self._entries):
            source, pack_sha, n_vars, rewrite = self._entries[cone_id]
            entries.append({"cone_id": cone_id, "source": json.loads(source),
                            "source_identity_sha256": hashlib.sha256(source).hexdigest(),
                            "pack_sha256": pack_sha, "n_vars": n_vars,
                            "result": expr_to_json_dag(rewrite.result),
                            "result_sha256": rewrite.result_sha256,
                            "applications_by_rule": rewrite.applications_by_rule})
        payload = {"schema": "crse-d10-cone-cache/v1", "max_entries": self.max_entries,
                   "entries": entries}
        return {**payload, "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()}

    def save(self, path: Path) -> None:
        document = self.to_document()
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    @classmethod
    def load(cls, path: Path, matcher: CompiledD10RulePack,
             *, max_bytes: int = 2_000_000) -> "D10ConeCache":
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise ValueError("D10 cache exceeds size bound")
        document = _strict_json(raw)
        keys = {"schema", "max_entries", "entries", "payload_sha256"}
        if type(document) is not dict or set(document) != keys:
            raise ValueError("invalid D10 cache fields")
        payload = {key: document[key] for key in keys - {"payload_sha256"}}
        if (document["schema"] != "crse-d10-cone-cache/v1"
                or document["payload_sha256"] != hashlib.sha256(canonical(payload)).hexdigest()
                or type(document["entries"]) is not list):
            raise ValueError("invalid D10 cache identity")
        cache = cls(document["max_entries"])
        if len(document["entries"]) > cache.max_entries:
            raise ValueError("D10 cache entry bound exceeded")
        for item in document["entries"]:
            expected_keys = {"cone_id", "source", "source_identity_sha256", "pack_sha256",
                             "n_vars", "result", "result_sha256", "applications_by_rule"}
            if type(item) is not dict or set(item) != expected_keys:
                raise ValueError("invalid D10 cache entry")
            source = canonical(item["source"])
            if (hashlib.sha256(source).hexdigest() != item["source_identity_sha256"]
                    or item["pack_sha256"] != matcher.pack_sha256):
                raise ValueError("D10 serialized source or pack disagreement")
            expression = expr_from_json(item["source"])
            replay = matcher.rewrite(expression, item["n_vars"])
            result = expr_from_json(item["result"])
            if (replay.result_sha256 != item["result_sha256"]
                    or structural_digest(result) != replay.result_sha256
                    or replay.applications_by_rule != item["applications_by_rule"]):
                raise ValueError("D10 serialized rewrite replay disagreement")
            cone_id = item["cone_id"]
            if type(cone_id) is not str or not cone_id or cone_id in cache._entries:
                raise ValueError("invalid or duplicate D10 cone identity")
            cache._entries[cone_id] = (source, matcher.pack_sha256, item["n_vars"], replay)
        return cache
