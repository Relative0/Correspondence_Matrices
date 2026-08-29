"""LLM provider boundary tested with inert fixtures; no live provider or network."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .contracts import Proposal, Task
from .motif_data import decode_bounded_dag


@dataclass
class FakeOfflineProvider:
    outputs: tuple[str, ...]
    calls: int = 0

    def propose(self, prompt: str) -> str:
        if (type(prompt) is not str or len(prompt.encode("utf-8")) > 4096
                or type(self.outputs) is not tuple or not 1 <= len(self.outputs) <= 3
                or self.calls >= len(self.outputs)):
            raise ValueError("offline provider call/input budget exceeded")
        response = self.outputs[self.calls]
        self.calls += 1
        return response


def parse_offline_proposal(response: str, source_digest: str, task: Task) -> Proposal:
    if type(response) is not str or len(response.encode("utf-8")) > 4096:
        raise ValueError("DSL response exceeds bound")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate DSL field")
            result[key] = value
        return result
    try:
        data = json.loads(response, object_pairs_hook=pairs)
    except (ValueError, RecursionError) as exc:
        raise ValueError("malformed declarative DSL") from exc
    if type(data) is not dict or set(data) != {"schema", "expression"} or data["schema"] != "crse-bool-dsl/v1":
        raise ValueError("unsupported DSL; executable code is never accepted")
    candidate = decode_bounded_dag(data["expression"], task.n_vars, max_nodes=64)
    return Proposal(source_digest, candidate, "learned", "fake-offline-provider-test/v1", None)
