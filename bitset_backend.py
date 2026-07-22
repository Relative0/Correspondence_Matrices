from __future__ import annotations

from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

if TYPE_CHECKING:
    from cm_ir import CMNode


@lru_cache(maxsize=256)
def _build_bitset_env_cached(vars_key: Tuple[str, ...]) -> Mapping[str, int]:
    n_vars = len(vars_key)
    n_rows = 1 << n_vars
    env: Dict[str, int] = {}
    if n_vars > 10:
        # The pure-Python block loop below is O(2^n) bigint shifts per variable and
        # becomes a first-touch cliff (~130 ms at n=16, ~1.5 s at n=18). Vectorize:
        # bit k of a variable's mask is that variable's value in assignment row k.
        rows = np.arange(n_rows, dtype=np.uint32)
        for v, name in enumerate(vars_key):
            bits = ((rows >> (n_vars - 1 - v)) & 1).astype(np.uint8)
            packed = np.packbits(bits, bitorder="little")
            env[name] = int.from_bytes(packed.tobytes(), "little")
    else:
        for v, name in enumerate(vars_key):
            block = 1 << (n_vars - 1 - v)
            stride = block << 1
            mask = 0
            one_block = (1 << block) - 1
            for start in range(block, n_rows, stride):
                mask |= one_block << start
            env[name] = mask
    # Freeze to prevent external mutation of cached state.
    return MappingProxyType(env)


def clear_bitset_env_cache() -> None:
    _build_bitset_env_cached.cache_clear()


def bitset_env_cache_stats() -> Dict[str, int]:
    info = _build_bitset_env_cached.cache_info()
    return {"hits": int(info.hits), "misses": int(info.misses), "size": int(info.currsize)}


def build_bitset_env(vars: Sequence[str]) -> Mapping[str, int]:
    """Build var -> truth-column bitmasks using MSB-first assignment ordering.

    Bit k corresponds to assignment row k in all_assignments_tt/eval_expr_tt.
    """
    return _build_bitset_env_cached(tuple(vars))


def eval_expr_bitset(expr: Expr, env: Mapping[str, int]) -> int:
    """Evaluate Expr to a packed truth-table bitset with width 2^n."""
    if not env:
        return 0
    n_vars = len(env)
    n_rows = 1 << n_vars
    full_mask = (1 << n_rows) - 1

    def rec(e: Expr) -> int:
        if isinstance(e, Var):
            return env[f"x{e.i}"]
        if isinstance(e, Not):
            return (~rec(e.a)) & full_mask
        if isinstance(e, And):
            return rec(e.a) & rec(e.b)
        if isinstance(e, Or):
            return rec(e.a) | rec(e.b)
        if isinstance(e, Xor):
            return rec(e.a) ^ rec(e.b)
        if isinstance(e, Imp):
            return ((~rec(e.a)) | rec(e.b)) & full_mask
        if isinstance(e, Eqv):
            return (~(rec(e.a) ^ rec(e.b))) & full_mask
        raise TypeError(e)

    return rec(expr)


def bitset_to_bool_array(bits: int, n_vars: int) -> np.ndarray:
    """Convert packed bitset to uint8 truth vector in TT row order."""
    n_rows = 1 << n_vars
    n_bytes = (n_rows + 7) // 8
    raw = bits.to_bytes(n_bytes, byteorder="little", signed=False)
    unpacked = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little")
    return unpacked[:n_rows]


def bitset_to_bool_hypercube(bits: int, n_vars: int) -> np.ndarray:
    """Convert packed bitset to a boolean hypercube with shape ``(2,) * n_vars``."""
    return bitset_to_bool_array(bits, n_vars).astype(bool, copy=False).reshape((2,) * n_vars)


def eval_cm_node_bitset(
    node: "CMNode",
    live_vars: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
) -> int:
    """Evaluate a CM IR node to a packed truth-table bitset over ``live_vars``.

    ``live_vars`` defines the MSB-first assignment order used by the packed result.
    Variables absent from ``live_vars`` must be provided in ``fixed``.
    """
    vars_key = tuple(live_vars)
    env = build_bitset_env(vars_key)
    fixed_map = fixed or {}
    n_rows = 1 << len(vars_key)
    full_mask = (1 << n_rows) - 1
    # Memo keyed by id(node): nodes are kept alive by the DAG for the whole call, and
    # structural hashing of CMNode keys is O(subtree) — id lookup is O(1). Two
    # structurally-equal but distinct node objects only cost a memo miss, never correctness.
    memo: Dict[int, int] = {}

    def rec(cur: "CMNode") -> int:
        cached = memo.get(id(cur))
        if cached is not None:
            return cached

        if cur.kind == "const":
            out = full_mask if int(cur.const_value or 0) else 0
        elif cur.kind == "var":
            if cur.var_name in fixed_map:
                out = full_mask if int(bool(fixed_map[cur.var_name])) else 0
            else:
                try:
                    out = int(env[cur.var_name])
                except KeyError as exc:
                    raise KeyError(f"missing live/fixed value for variable {cur.var_name!r}") from exc
        elif cur.kind == "not":
            out = (~rec(cur.args[0])) & full_mask
        elif cur.op == "AND":
            out = full_mask
            for arg in cur.args:
                out &= rec(arg)
        elif cur.op == "OR":
            out = 0
            for arg in cur.args:
                out |= rec(arg)
        elif cur.op == "XOR":
            out = 0
            for arg in cur.args:
                out ^= rec(arg)
        elif cur.op == "IMP":
            left = rec(cur.args[0])
            right = rec(cur.args[1])
            out = ((~left) | right) & full_mask
        elif cur.op == "EQV":
            left = rec(cur.args[0])
            right = rec(cur.args[1])
            out = (~(left ^ right)) & full_mask
        else:
            raise TypeError(cur)

        memo[id(cur)] = out
        return out

    return rec(node)


# ---------------------------------------------------------------------------
# C1a: flat (linearized) CM-node evaluator — opt-in alternative to the
# recursive kernel above. The interned CMNode DAG is lowered ONCE into a
# linear postorder instruction list (one instruction per unique DAG node, so
# sharing is exploited at compile time and the eval loop needs no memo), and
# per-(vars_key, fixed) variable/constant masks are resolved ONCE into a
# "bound" slot template (legitimate compile-once reuse, same class as the
# build_bitset_env LRU: it stores resolved *input* masks, never outputs).
# Bit-identical to eval_cm_node_bitset by construction and by test sweep.
# ---------------------------------------------------------------------------

_FLAT_OP_NOT = 0
_FLAT_OP_AND = 1
_FLAT_OP_OR = 2
_FLAT_OP_XOR = 3
_FLAT_OP_IMP = 4
_FLAT_OP_EQV = 5

_FLAT_OPCODE = {"AND": _FLAT_OP_AND, "OR": _FLAT_OP_OR, "XOR": _FLAT_OP_XOR,
                "IMP": _FLAT_OP_IMP, "EQV": _FLAT_OP_EQV}

_FLAT_BOUND_CACHE_MAX = 64
# At 2**16 bits, clearing references was neutral for CM and slowed raw-flat on the
# audit workload.  It becomes consistently worthwhile from 2**18-bit outputs.
_FLAT_FREE_MIN_VARS = 18
_FLAT_FREE_MIN_SLOTS = 64


class FlatProgram:
    """Linear postorder program lowered from a CMNode DAG.

    ``loads``: tuple of (slot, kind, payload) with kind in {"var", "const"}.
    ``ops``:   tuple of (slot, opcode, arg_slots) in dependency order.
    ``release_after``: dead input slots to clear after each operation.
    ``bound_cache``: {(vars_key, fixed_items): (slot_template, full_mask)} —
    small FIFO-evicted cache of resolved input masks.
    """

    __slots__ = ("n_slots", "root_slot", "loads", "ops", "release_after", "bound_cache",
                 "word_plan", "word_scratch")

    def __init__(self, n_slots: int, root_slot: int, loads, ops) -> None:
        self.n_slots = n_slots
        self.root_slot = root_slot
        self.loads = loads
        self.ops = ops
        self.release_after = _last_use_releases(n_slots, root_slot, ops)
        self.bound_cache: Dict[tuple, tuple] = {}
        self.word_plan = None
        self.word_scratch: Dict[int, list] = {}


def _last_use_releases(n_slots: int, root_slot: int, ops) -> tuple:
    """Return input slots whose final use occurs at each operation.

    Slots are never reused, which keeps lowering simple and makes the old retained-slot
    behavior available for measurement.  Clearing the references is enough to let CPython
    reclaim wide bigint intermediates promptly.
    """
    remaining = [0] * n_slots
    for _slot, _opcode, arg_slots in ops:
        for arg_slot in arg_slots:
            remaining[arg_slot] += 1
    releases = []
    for _slot, _opcode, arg_slots in ops:
        dead = []
        for arg_slot in arg_slots:
            remaining[arg_slot] -= 1
            if remaining[arg_slot] == 0 and arg_slot != root_slot:
                dead.append(arg_slot)
        releases.append(tuple(dead))
    return tuple(releases)


def compile_flat(node: "CMNode") -> FlatProgram:
    """Lower a CMNode DAG to a FlatProgram (iterative postorder, id-memoized)."""
    slot_of: Dict[int, int] = {}
    loads = []
    ops = []
    stack = [(node, False)]
    while stack:
        cur, processed = stack.pop()
        if id(cur) in slot_of:
            continue
        if not processed:
            stack.append((cur, True))
            for arg in cur.args:
                if id(arg) not in slot_of:
                    stack.append((arg, False))
            continue
        slot = len(slot_of)
        slot_of[id(cur)] = slot
        if cur.kind == "const":
            loads.append((slot, "const", int(cur.const_value or 0)))
        elif cur.kind == "var":
            loads.append((slot, "var", cur.var_name))
        elif cur.kind == "not":
            ops.append((slot, _FLAT_OP_NOT, (slot_of[id(cur.args[0])],)))
        else:
            opcode = _FLAT_OPCODE.get(cur.op)
            if opcode is None:
                raise TypeError(cur)
            ops.append((slot, opcode, tuple(slot_of[id(a)] for a in cur.args)))
    return FlatProgram(len(slot_of), slot_of[id(node)], tuple(loads), tuple(ops))


def get_flat_program(node: "CMNode") -> FlatProgram:
    """Return the node's FlatProgram, lowering and caching it on first use.

    Cached on the (frozen) node instance itself via object.__setattr__ — the
    same lifetime-correct pattern CMNode.__hash__ uses for its cached hash.
    """
    prog = node.__dict__.get("_flat_program")
    if prog is None:
        prog = compile_flat(node)
        object.__setattr__(node, "_flat_program", prog)
    return prog


def _bind_flat_program(prog: FlatProgram, vars_key: Tuple[str, ...],
                       fixed_map: Mapping[str, int]) -> tuple:
    key = (vars_key, tuple(sorted(fixed_map.items())))
    bound = prog.bound_cache.get(key)
    if bound is None:
        env = build_bitset_env(vars_key)
        full_mask = (1 << (1 << len(vars_key))) - 1
        template = [0] * prog.n_slots
        for slot, kind, payload in prog.loads:
            if kind == "const":
                template[slot] = full_mask if payload else 0
            elif payload in fixed_map:
                template[slot] = full_mask if int(bool(fixed_map[payload])) else 0
            else:
                try:
                    template[slot] = int(env[payload])
                except KeyError as exc:
                    raise KeyError(
                        f"missing live/fixed value for variable {payload!r}"
                    ) from exc
        if len(prog.bound_cache) >= _FLAT_BOUND_CACHE_MAX:
            prog.bound_cache.pop(next(iter(prog.bound_cache)))
        bound = (template, full_mask)
        prog.bound_cache[key] = bound
    return bound


def eval_cm_node_flat(
    node: "CMNode",
    live_vars: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
    free_dead_slots: bool = True,
) -> int:
    """Flat-program equivalent of eval_cm_node_bitset (bit-identical output).

    ``free_dead_slots=False`` retains the original C1a behavior for controlled
    before/after measurements.  When enabled, freeing is selected only for wide programs
    (at least 18 variables and 64 slots), where reduced peak liveness repays its loop cost.
    The default is safe because the whole flat evaluator is already opt-in at the public
    CM wrapper.
    """
    prog = get_flat_program(node)
    template, full_mask = _bind_flat_program(prog, tuple(live_vars), fixed or {})
    values = template.copy()
    release_dead = bool(
        free_dead_slots
        and len(live_vars) >= _FLAT_FREE_MIN_VARS
        and prog.n_slots >= _FLAT_FREE_MIN_SLOTS
    )
    for op_index, (slot, opcode, arg_slots) in enumerate(prog.ops):
        if opcode == _FLAT_OP_AND:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc &= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_OR:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc |= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_XOR:
            acc = values[arg_slots[0]]
            for i in arg_slots[1:]:
                acc ^= values[i]
            values[slot] = acc
        elif opcode == _FLAT_OP_NOT:
            values[slot] = (~values[arg_slots[0]]) & full_mask
        elif opcode == _FLAT_OP_IMP:
            values[slot] = ((~values[arg_slots[0]]) | values[arg_slots[1]]) & full_mask
        else:  # _FLAT_OP_EQV
            values[slot] = (~(values[arg_slots[0]] ^ values[arg_slots[1]])) & full_mask
        if release_dead:
            for dead_slot in prog.release_after[op_index]:
                values[dead_slot] = None
    return values[prog.root_slot]


def compile_expr_flat(expr: Expr) -> FlatProgram:
    """Lower a raw Expr tree to a flat program without CM canonicalization/sharing."""
    loads = []
    ops = []

    def rec(cur: Expr) -> int:
        if isinstance(cur, Var):
            slot = len(loads) + len(ops)
            loads.append((slot, "var", f"x{cur.i}"))
            return slot
        if isinstance(cur, Not):
            arg_slots = (rec(cur.a),)
            opcode = _FLAT_OP_NOT
        elif isinstance(cur, (And, Or, Xor, Imp, Eqv)):
            arg_slots = (rec(cur.a), rec(cur.b))
            opcode = {
                And: _FLAT_OP_AND,
                Or: _FLAT_OP_OR,
                Xor: _FLAT_OP_XOR,
                Imp: _FLAT_OP_IMP,
                Eqv: _FLAT_OP_EQV,
            }[type(cur)]
        else:
            raise TypeError(cur)
        slot = len(loads) + len(ops)
        ops.append((slot, opcode, arg_slots))
        return slot

    root_slot = rec(expr)
    return FlatProgram(len(loads) + len(ops), root_slot, tuple(loads), tuple(ops))


def get_expr_flat_program(expr: Expr) -> FlatProgram:
    """Return a raw-AST flat program cached on the root expression object."""
    prog = expr.__dict__.get("_bitset_flat_program")
    if prog is None:
        prog = compile_expr_flat(expr)
        object.__setattr__(expr, "_bitset_flat_program", prog)
    return prog


def eval_expr_flat_bitset(
    expr: Expr,
    vars_all: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
    free_dead_slots: bool = True,
) -> int:
    """Evaluate a compile-once raw Expr flat program over packed bigint columns.

    This is the fair flat-vs-flat bitset control: it uses no CM rewrites or DAG
    canonicalization, while sharing the same cached input-mask builder and last-use policy.
    The bound cache contains inputs only; operation outputs are always recomputed.
    """
    prog = get_expr_flat_program(expr)
    template, full_mask = _bind_flat_program(prog, tuple(vars_all), fixed or {})
    values = template.copy()
    release_dead = bool(
        free_dead_slots
        and len(vars_all) >= _FLAT_FREE_MIN_VARS
        and prog.n_slots >= _FLAT_FREE_MIN_SLOTS
    )
    for op_index, (slot, opcode, arg_slots) in enumerate(prog.ops):
        if opcode == _FLAT_OP_AND:
            values[slot] = values[arg_slots[0]] & values[arg_slots[1]]
        elif opcode == _FLAT_OP_OR:
            values[slot] = values[arg_slots[0]] | values[arg_slots[1]]
        elif opcode == _FLAT_OP_XOR:
            values[slot] = values[arg_slots[0]] ^ values[arg_slots[1]]
        elif opcode == _FLAT_OP_NOT:
            values[slot] = (~values[arg_slots[0]]) & full_mask
        elif opcode == _FLAT_OP_IMP:
            values[slot] = ((~values[arg_slots[0]]) | values[arg_slots[1]]) & full_mask
        else:  # _FLAT_OP_EQV
            values[slot] = (~(values[arg_slots[0]] ^ values[arg_slots[1]])) & full_mask
        if release_dead:
            for dead_slot in prog.release_after[op_index]:
                values[dead_slot] = None
    return values[prog.root_slot]


# ---------------------------------------------------------------------------
# numpy-uint64 word backend (Tier-C C1b-lite)
#
# Executes the same FlatProgram over 64-bit word vectors instead of Python
# bigints.  Op outputs go into a small pool of scratch buffers colored by the
# existing last-use schedule (peak-live buffers, not one per slot), with out=
# so the steady state performs zero allocations.  Word width requires the
# packed width to be a multiple of 64, i.e. at least 6 live variables; below
# that the public entry points fall back to the bigint flat kernel, so the
# words functions are bit-compatible drop-ins at every size.
# ---------------------------------------------------------------------------

_WORDS_MIN_VARS = 6           # 2**6 bits = one uint64 word
_WORDS_ENV_CACHE_MAX = 4      # an n=24 entry holds n arrays of 2 MB each
_WORDS_SCRATCH_WIDTHS_MAX = 2  # widths cached per program (FIFO)


@lru_cache(maxsize=_WORDS_ENV_CACHE_MAX)
def _build_words_env_cached(vars_key: Tuple[str, ...]) -> Mapping[str, np.ndarray]:
    """var -> read-only little-endian uint64 view of its truth-column mask."""
    env = build_bitset_env(vars_key)
    n_words = (1 << len(vars_key)) // 64
    out: Dict[str, np.ndarray] = {}
    for name in vars_key:
        out[name] = np.frombuffer(
            int(env[name]).to_bytes(n_words * 8, "little"), dtype="<u8"
        )
    return MappingProxyType(out)


@lru_cache(maxsize=8)
def _words_const(n_words: int, value: int) -> np.ndarray:
    byte = b"\xff" if value else b"\x00"
    return np.frombuffer(byte * (n_words * 8), dtype="<u8")


def _compute_word_plan(prog: FlatProgram) -> tuple:
    """Color op outputs onto a minimal scratch-buffer pool via release_after.

    Returns (steps, n_buffers, root_loc, load_info) where each step is
    (out_buffer, opcode, arg_locs) and a location is ("l", load_slot) for a
    shared read-only input array or ("s", buffer_index) for scratch.  A dying
    argument's buffer is recycled only after its consuming op completes, so an
    op's output buffer can never alias any of its inputs (required because
    IMP/EQV/n-ary ops execute as multi-step in-place sequences).
    """
    load_info = {slot: (kind, payload) for slot, kind, payload in prog.loads}
    buffer_of: Dict[int, int] = {}
    free: list = []
    n_buffers = 0
    steps = []
    for op_index, (slot, opcode, args) in enumerate(prog.ops):
        arg_locs = tuple(
            ("l", a) if a in load_info else ("s", buffer_of[a]) for a in args
        )
        if free:
            out = free.pop()
        else:
            out = n_buffers
            n_buffers += 1
        buffer_of[slot] = out
        steps.append((out, opcode, arg_locs))
        for dead in prog.release_after[op_index]:
            recycled = buffer_of.pop(dead, None)
            if recycled is not None:
                free.append(recycled)
    if prog.root_slot in load_info:
        root_loc = ("l", prog.root_slot)
    else:
        root_loc = ("s", buffer_of[prog.root_slot])
    return steps, n_buffers, root_loc, load_info


def _eval_words(prog: FlatProgram, vars_key: Tuple[str, ...],
                fixed_map: Mapping[str, int]) -> int:
    if prog.word_plan is None:
        prog.word_plan = _compute_word_plan(prog)
    steps, n_buffers, root_loc, load_info = prog.word_plan
    n_words = (1 << len(vars_key)) // 64
    env = _build_words_env_cached(vars_key)
    scratch = prog.word_scratch.get(n_words)
    if scratch is None:
        if len(prog.word_scratch) >= _WORDS_SCRATCH_WIDTHS_MAX:
            prog.word_scratch.pop(next(iter(prog.word_scratch)))
        scratch = [np.empty(n_words, dtype="<u8") for _ in range(n_buffers)]
        prog.word_scratch[n_words] = scratch

    def resolve(loc):
        tag, x = loc
        if tag == "s":
            return scratch[x]
        kind, payload = load_info[x]
        if kind == "const":
            return _words_const(n_words, int(payload))
        if payload in fixed_map:
            return _words_const(n_words, int(bool(fixed_map[payload])))
        try:
            return env[payload]
        except KeyError as exc:
            raise KeyError(f"missing live/fixed value for variable {payload!r}") from exc

    for out, opcode, arg_locs in steps:
        dst = scratch[out]
        a0 = resolve(arg_locs[0])
        if opcode == _FLAT_OP_NOT:
            np.bitwise_not(a0, out=dst)
            continue
        a1 = resolve(arg_locs[1]) if len(arg_locs) > 1 else None
        if opcode == _FLAT_OP_AND:
            if a1 is None:
                np.copyto(dst, a0)
            else:
                np.bitwise_and(a0, a1, out=dst)
                for extra in arg_locs[2:]:
                    np.bitwise_and(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_OR:
            if a1 is None:
                np.copyto(dst, a0)
            else:
                np.bitwise_or(a0, a1, out=dst)
                for extra in arg_locs[2:]:
                    np.bitwise_or(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_XOR:
            if a1 is None:
                np.copyto(dst, a0)
            else:
                np.bitwise_xor(a0, a1, out=dst)
                for extra in arg_locs[2:]:
                    np.bitwise_xor(dst, resolve(extra), out=dst)
        elif opcode == _FLAT_OP_IMP:
            np.bitwise_not(a0, out=dst)
            np.bitwise_or(dst, a1, out=dst)
        else:  # _FLAT_OP_EQV
            np.bitwise_xor(a0, a1, out=dst)
            np.bitwise_not(dst, out=dst)
    return int.from_bytes(resolve(root_loc).tobytes(), "little")


def eval_cm_node_words(
    node: "CMNode",
    live_vars: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
) -> int:
    """numpy-words twin of eval_cm_node_flat (bit-identical output).

    Falls back to the bigint flat kernel below 6 live variables, where the
    packed width is narrower than one 64-bit word.
    """
    vars_key = tuple(live_vars)
    if len(vars_key) < _WORDS_MIN_VARS:
        return eval_cm_node_flat(node, vars_key, fixed=fixed)
    return _eval_words(get_flat_program(node), vars_key, fixed or {})


def eval_expr_words_bitset(
    expr: Expr,
    vars_all: Sequence[str],
    *,
    fixed: Optional[Mapping[str, int]] = None,
) -> int:
    """numpy-words twin of eval_expr_flat_bitset — the fair raw-AST control."""
    vars_key = tuple(vars_all)
    if len(vars_key) < _WORDS_MIN_VARS:
        return eval_expr_flat_bitset(expr, vars_key, fixed=fixed)
    return _eval_words(get_expr_flat_program(expr), vars_key, fixed or {})


def clear_words_env_cache() -> None:
    _build_words_env_cached.cache_clear()
    _words_const.cache_clear()
