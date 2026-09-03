"""ctypes adapter for the development-only fused native slot executor."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
import ctypes
import hashlib
from pathlib import Path
from typing import Any

import numpy as np


_OPCODES = {
    "var": 0,
    "not": 1,
    "and": 2,
    "or": 3,
    "xor": 4,
    "imp": 5,
    "eqv": 6,
}


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class NativeSlotLibrary:
    path: Path
    sha256: str
    abi_version: int
    supports_multi_root: bool
    handle: Any = field(repr=False, compare=False)


@dataclass
class NativeSlotArena:
    library: NativeSlotLibrary
    opcodes: np.ndarray
    child_a: np.ndarray
    child_b: np.ndarray
    variable_indices: np.ndarray
    variable_count: int
    root: int
    _workspaces: dict[int, tuple[np.ndarray, np.ndarray]] = field(
        default_factory=dict, init=False, repr=False)

    @property
    def node_count(self) -> int:
        return int(self.opcodes.size)

    @property
    def arena_bytes(self) -> int:
        return int(
            self.opcodes.nbytes + self.child_a.nbytes + self.child_b.nbytes
            + self.variable_indices.nbytes)

    def workspace_bytes(self, live_count: int) -> int:
        words = max(1, ((1 << live_count) + 63) // 64)
        return int((self.node_count * words + words) * np.dtype(np.uint64).itemsize)

    def prepare_bindings(
        self,
        fixed: Mapping[str, int],
        remaining: Sequence[str],
    ) -> np.ndarray:
        remaining_tuple = tuple(remaining)
        fixed_map = dict(fixed)
        _require(
            remaining_tuple
            and set(remaining_tuple).isdisjoint(fixed_map)
            and set(remaining_tuple) | set(fixed_map)
            == {f"x{index}" for index in range(self.variable_count)}
            and all(type(value) is int and value in (0, 1)
                    for value in fixed_map.values()),
            "invalid native slot restriction",
        )
        bindings = np.empty(self.variable_count, dtype=np.int16)
        for index in range(self.variable_count):
            name = f"x{index}"
            if name in fixed_map:
                bindings[index] = -2 if fixed_map[name] else -1
            else:
                bindings[index] = remaining_tuple.index(name)
        bindings.flags.writeable = False
        return bindings

    def evaluate(self, bindings: np.ndarray, live_count: int) -> int:
        _require(
            isinstance(bindings, np.ndarray)
            and bindings.dtype == np.int16
            and bindings.ndim == 1
            and bindings.size == self.variable_count
            and type(live_count) is int
            and 1 <= live_count < 31,
            "invalid native slot evaluation",
        )
        word_count = max(1, ((1 << live_count) + 63) // 64)
        buffers = self._workspaces.get(word_count)
        if buffers is None:
            buffers = (
                np.empty(self.node_count * word_count, dtype=np.uint64),
                np.empty(word_count, dtype=np.uint64),
            )
            self._workspaces[word_count] = buffers
        workspace, output = buffers
        pointer = ctypes.POINTER
        status = self.library.handle.cm_fused_slots_eval(
            self.opcodes.ctypes.data_as(pointer(ctypes.c_uint8)),
            self.child_a.ctypes.data_as(pointer(ctypes.c_int32)),
            self.child_b.ctypes.data_as(pointer(ctypes.c_int32)),
            self.variable_indices.ctypes.data_as(pointer(ctypes.c_int16)),
            ctypes.c_size_t(self.node_count),
            ctypes.c_size_t(self.root),
            bindings.ctypes.data_as(pointer(ctypes.c_int16)),
            ctypes.c_size_t(self.variable_count),
            ctypes.c_size_t(live_count),
            ctypes.c_size_t(word_count),
            workspace.ctypes.data_as(pointer(ctypes.c_uint64)),
            output.ctypes.data_as(pointer(ctypes.c_uint64)),
        )
        if status != 0:
            raise RuntimeError(f"native fused slot evaluator failed with status {status}")
        return int.from_bytes(output.tobytes(), "little")


@dataclass
class NativeMultiRootArena:
    library: NativeSlotLibrary
    opcodes: np.ndarray
    child_a: np.ndarray
    child_b: np.ndarray
    variable_indices: np.ndarray
    roots: np.ndarray
    variable_count: int
    _workspaces: dict[int, tuple[np.ndarray, np.ndarray]] = field(
        default_factory=dict, init=False, repr=False)

    @property
    def node_count(self) -> int:
        return int(self.opcodes.size)

    @property
    def root_count(self) -> int:
        return int(self.roots.size)

    @property
    def arena_bytes(self) -> int:
        return int(
            self.opcodes.nbytes + self.child_a.nbytes + self.child_b.nbytes
            + self.variable_indices.nbytes + self.roots.nbytes)

    def workspace_bytes(self, live_count: int) -> int:
        words = max(1, ((1 << live_count) + 63) // 64)
        return int((self.node_count * words + self.root_count * words)
                   * np.dtype(np.uint64).itemsize)

    def prepare_bindings(
        self,
        fixed: Mapping[str, int],
        remaining: Sequence[str],
    ) -> np.ndarray:
        # Binding semantics are identical to the single-root arena.
        proxy = NativeSlotArena(
            library=self.library,
            opcodes=self.opcodes,
            child_a=self.child_a,
            child_b=self.child_b,
            variable_indices=self.variable_indices,
            variable_count=self.variable_count,
            root=int(self.roots[0]),
        )
        return proxy.prepare_bindings(fixed, remaining)

    def evaluate(self, bindings: np.ndarray, live_count: int) -> tuple[int, ...]:
        _require(
            isinstance(bindings, np.ndarray)
            and bindings.dtype == np.int16
            and bindings.ndim == 1
            and bindings.size == self.variable_count
            and type(live_count) is int
            and 1 <= live_count < 31,
            "invalid native multi-root evaluation",
        )
        word_count = max(1, ((1 << live_count) + 63) // 64)
        buffers = self._workspaces.get(word_count)
        if buffers is None:
            buffers = (
                np.empty(self.node_count * word_count, dtype=np.uint64),
                np.empty(self.root_count * word_count, dtype=np.uint64),
            )
            self._workspaces[word_count] = buffers
        workspace, outputs = buffers
        pointer = ctypes.POINTER
        status = self.library.handle.cm_fused_slots_eval_multi(
            self.opcodes.ctypes.data_as(pointer(ctypes.c_uint8)),
            self.child_a.ctypes.data_as(pointer(ctypes.c_int32)),
            self.child_b.ctypes.data_as(pointer(ctypes.c_int32)),
            self.variable_indices.ctypes.data_as(pointer(ctypes.c_int16)),
            ctypes.c_size_t(self.node_count),
            self.roots.ctypes.data_as(pointer(ctypes.c_int32)),
            ctypes.c_size_t(self.root_count),
            bindings.ctypes.data_as(pointer(ctypes.c_int16)),
            ctypes.c_size_t(self.variable_count),
            ctypes.c_size_t(live_count),
            ctypes.c_size_t(word_count),
            workspace.ctypes.data_as(pointer(ctypes.c_uint64)),
            outputs.ctypes.data_as(pointer(ctypes.c_uint64)),
        )
        if status != 0:
            raise RuntimeError(f"native multi-root evaluator failed with status {status}")
        raw = outputs.tobytes()
        byte_count = word_count * 8
        return tuple(
            int.from_bytes(raw[index * byte_count:(index + 1) * byte_count], "little")
            for index in range(self.root_count)
        )


def load_native_slot_library(path: Path) -> NativeSlotLibrary:
    resolved = path.resolve()
    _require(resolved.is_file(), "native fused slot library is missing")
    handle = ctypes.CDLL(str(resolved))
    handle.cm_fused_slots_abi_version.argtypes = []
    handle.cm_fused_slots_abi_version.restype = ctypes.c_uint32
    abi = int(handle.cm_fused_slots_abi_version())
    _require(abi == 1, "unsupported native fused slot ABI")
    handle.cm_fused_slots_eval.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
    ]
    handle.cm_fused_slots_eval.restype = ctypes.c_int
    supports_multi_root = hasattr(handle, "cm_fused_slots_eval_multi")
    if supports_multi_root:
        handle.cm_fused_slots_eval_multi.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int32),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64),
        ]
        handle.cm_fused_slots_eval_multi.restype = ctypes.c_int
    return NativeSlotLibrary(
        path=resolved,
        sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
        abi_version=abi,
        supports_multi_root=supports_multi_root,
        handle=handle,
    )


def compile_native_slot_arena(
    document: Mapping[str, Any],
    library: NativeSlotLibrary,
    *,
    variable_count: int | None = None,
) -> NativeSlotArena:
    _require(isinstance(document, Mapping) and document.get("version") == 2,
             "native slots require expression DAG v2")
    nodes = document.get("nodes")
    root = document.get("root")
    _require(isinstance(nodes, list) and nodes, "native slot nodes")
    _require(type(root) is int and root == len(nodes) - 1,
             "native slots require a topological reachable root")
    opcodes = np.empty(len(nodes), dtype=np.uint8)
    child_a = np.full(len(nodes), -1, dtype=np.int32)
    child_b = np.full(len(nodes), -1, dtype=np.int32)
    variable_indices = np.full(len(nodes), -1, dtype=np.int16)
    max_variable = -1
    for slot, node in enumerate(nodes):
        _require(isinstance(node, Mapping), "invalid native slot node")
        opcode = str(node.get("op", "")).lower()
        _require(opcode in _OPCODES, "invalid native slot opcode")
        opcodes[slot] = _OPCODES[opcode]
        if opcode == "var":
            variable = node.get("i")
            _require(type(variable) is int and 0 <= variable <= np.iinfo(np.int16).max,
                     "invalid native slot variable")
            variable_indices[slot] = variable
            max_variable = max(max_variable, variable)
        else:
            a = node.get("a")
            _require(type(a) is int and 0 <= a < slot,
                     "invalid native slot child a")
            child_a[slot] = a
            if opcode != "not":
                b = node.get("b")
                _require(type(b) is int and 0 <= b < slot,
                         "invalid native slot child b")
                child_b[slot] = b
    for array in (opcodes, child_a, child_b, variable_indices):
        array.flags.writeable = False
    inferred_variables = max_variable + 1
    declared_variables = inferred_variables if variable_count is None else variable_count
    _require(type(declared_variables) is int and declared_variables >= inferred_variables,
             "native slot variable count is too small")
    return NativeSlotArena(
        library=library,
        opcodes=opcodes,
        child_a=child_a,
        child_b=child_b,
        variable_indices=variable_indices,
        variable_count=declared_variables,
        root=root,
    )


def compile_native_multi_root_arena(
    document: Mapping[str, Any],
    library: NativeSlotLibrary,
    *,
    variable_count: int,
) -> NativeMultiRootArena:
    _require(library.supports_multi_root,
             "native fused slot library lacks multi-root support")
    _require(isinstance(document, Mapping) and document.get("version") == 2,
             "native multi-root slots require DAG v2")
    nodes = document.get("nodes")
    roots_value = document.get("roots")
    _require(isinstance(nodes, list) and nodes, "native multi-root nodes")
    _require(
        isinstance(roots_value, list)
        and len(roots_value) >= 2
        and all(type(root) is int and 0 <= root < len(nodes) for root in roots_value),
        "native multi-root roots",
    )
    opcodes = np.empty(len(nodes), dtype=np.uint8)
    child_a = np.full(len(nodes), -1, dtype=np.int32)
    child_b = np.full(len(nodes), -1, dtype=np.int32)
    variable_indices = np.full(len(nodes), -1, dtype=np.int16)
    max_variable = -1
    for slot, node in enumerate(nodes):
        _require(isinstance(node, Mapping), "invalid native multi-root node")
        opcode = str(node.get("op", "")).lower()
        _require(opcode in _OPCODES, "invalid native multi-root opcode")
        opcodes[slot] = _OPCODES[opcode]
        if opcode == "var":
            variable = node.get("i")
            _require(type(variable) is int and 0 <= variable <= np.iinfo(np.int16).max,
                     "invalid native multi-root variable")
            variable_indices[slot] = variable
            max_variable = max(max_variable, variable)
        else:
            a = node.get("a")
            _require(type(a) is int and 0 <= a < slot,
                     "invalid native multi-root child a")
            child_a[slot] = a
            if opcode != "not":
                b = node.get("b")
                _require(type(b) is int and 0 <= b < slot,
                         "invalid native multi-root child b")
                child_b[slot] = b
    _require(type(variable_count) is int and variable_count >= max_variable + 1,
             "native multi-root variable count is too small")
    roots = np.asarray(roots_value, dtype=np.int32)
    for array in (opcodes, child_a, child_b, variable_indices, roots):
        array.flags.writeable = False
    return NativeMultiRootArena(
        library=library,
        opcodes=opcodes,
        child_a=child_a,
        child_b=child_b,
        variable_indices=variable_indices,
        roots=roots,
        variable_count=variable_count,
    )
