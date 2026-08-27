"""Generate deterministic, self-checking CM use-case demonstration suites.

The output is deliberately domain-shaped synthetic data, not field evidence.
Every case contains a base Boolean DAG, an equivalent structural rewrite, a
localized behavioral edit, partial contexts, and packed reference truth bits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


GENERATOR_VERSION = "1.0"
DEFAULT_SEED = 20260827
SCENARIOS = {
    "hardware": {"variables": 10, "roots": 3, "workflow": "related output cones and localized netlist revisions"},
    "ai": {"variables": 9, "roots": 1, "workflow": "agent authorization under repeated action contexts and policy versions"},
    "biology": {"variables": 11, "roots": 3, "workflow": "update rules under intervention contexts and model revisions"},
    "quantum": {"variables": 10, "roots": 2, "workflow": "classical reversible or control predicates across circuit variants"},
    "compiler": {"variables": 10, "roots": 1, "workflow": "pure-Boolean guards under known facts and adjacent transformations"},
    "security": {"variables": 9, "roots": 1, "workflow": "authorization replay, audit, and policy-version change impact"},
    "configuration": {"variables": 11, "roots": 1, "workflow": "partial configurations across related feature-model releases"},
    "regulated": {"variables": 9, "roots": 1, "workflow": "Boolean decision-table conformance and local rule revisions"},
}


def dump_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def make_base(rng: random.Random, variables: list[str], root_count: int) -> tuple[list[dict], list[str]]:
    nodes: list[dict] = []
    refs = list(variables)
    for index in range(2 * len(variables) + root_count):
        op = rng.choice(("and", "or", "xor"))
        left, right = rng.sample(refs, 2)
        node_id = f"n{index}"
        nodes.append({"id": node_id, "op": op, "args": [left, right]})
        refs.append(node_id)
    roots = [node["id"] for node in nodes[-root_count:]]
    return nodes, roots


def equivalent_rewrite(nodes: list[dict], roots: list[str]) -> tuple[list[dict], list[str]]:
    rewritten = [dict(node, args=list(node["args"])) for node in nodes]
    new_roots = []
    for index, root in enumerate(roots):
        inner = f"eq_not_{index}_a"
        outer = f"eq_not_{index}_b"
        rewritten.extend((
            {"id": inner, "op": "not", "args": [root]},
            {"id": outer, "op": "not", "args": [inner]},
        ))
        new_roots.append(outer)
    return rewritten, new_roots


def localized_change(nodes: list[dict], roots: list[str], variables: list[str], case_index: int) -> tuple[list[dict], list[str]]:
    changed = [dict(node, args=list(node["args"])) for node in nodes]
    new_roots = []
    for index, root in enumerate(roots):
        node_id = f"changed_root_{index}"
        toggle = variables[(case_index + 2 * index) % len(variables)]
        changed.append({"id": node_id, "op": "xor", "args": [root, toggle]})
        new_roots.append(node_id)
    return changed, new_roots


def contexts(rng: random.Random, variables: list[str]) -> list[dict]:
    order = list(variables)
    rng.shuffle(order)
    result = [{"id": "all_free", "assign": {}}]
    for label, fraction in (("quarter_fixed", 0.25), ("half_fixed", 0.50), ("three_quarters_fixed", 0.75)):
        count = max(1, round(len(variables) * fraction))
        chosen = sorted(order[:count])
        result.append({"id": label, "assign": {name: bool(rng.getrandbits(1)) for name in chosen}})
    return result


def evaluate_dag(nodes: list[dict], root: str, assignment: dict[str, bool]) -> bool:
    values = dict(assignment)
    for node in nodes:
        args = [values[arg] for arg in node["args"]]
        if node["op"] == "not":
            value = not args[0]
        elif node["op"] == "and":
            value = args[0] and args[1]
        elif node["op"] == "or":
            value = args[0] or args[1]
        elif node["op"] == "xor":
            value = args[0] != args[1]
        else:
            raise ValueError(f"unsupported op: {node['op']}")
        values[node["id"]] = value
    return values[root]


def expected_bits(nodes: list[dict], root: str, variables: list[str], fixed: dict[str, bool]) -> dict:
    free = [name for name in variables if name not in fixed]
    bit_count = 1 << len(free)
    packed_value = 0
    for assignment_index in range(bit_count):
        assignment = dict(fixed)
        for bit_index, name in enumerate(free):
            assignment[name] = bool((assignment_index >> bit_index) & 1)
        if evaluate_dag(nodes, root, assignment):
            packed_value |= 1 << assignment_index
    packed = packed_value.to_bytes((bit_count + 7) // 8, byteorder="little")
    return {
        "bit_count": bit_count,
        "free_variables_lsb_first": free,
        "packed_bits_little_endian_hex": packed.hex(),
        "packed_bits_sha256": hashlib.sha256(packed).hexdigest(),
        "true_count": packed_value.bit_count(),
    }


def make_version(version_id: str, relation: str, nodes: list[dict], roots: list[str], variables: list[str], case_contexts: list[dict]) -> dict:
    evaluations = []
    for context in case_contexts:
        evaluations.append({
            "context_id": context["id"],
            "roots": [expected_bits(nodes, root, variables, context["assign"]) for root in roots],
        })
    return {"id": version_id, "relation_to_base": relation, "nodes": nodes, "roots": roots, "evaluations": evaluations}


def make_case(domain: str, spec: dict, seed: int, case_index: int) -> dict:
    rng = random.Random(seed)
    variables = [f"x{i}" for i in range(spec["variables"])]
    base_nodes, base_roots = make_base(rng, variables, spec["roots"])
    eq_nodes, eq_roots = equivalent_rewrite(base_nodes, base_roots)
    changed_nodes, changed_roots = localized_change(base_nodes, base_roots, variables, case_index)
    case_contexts = contexts(rng, variables)
    versions = [
        make_version("base", "identity", base_nodes, base_roots, variables, case_contexts),
        make_version("equivalent_rewrite", "equivalent; two added NOT nodes per root", eq_nodes, eq_roots, variables, case_contexts),
        make_version("localized_change", "behavior-changing XOR at each root", changed_nodes, changed_roots, variables, case_contexts),
    ]
    for context_index in range(len(case_contexts)):
        base_expected = versions[0]["evaluations"][context_index]["roots"]
        eq_expected = versions[1]["evaluations"][context_index]["roots"]
        if [item["packed_bits_sha256"] for item in base_expected] != [item["packed_bits_sha256"] for item in eq_expected]:
            raise AssertionError("equivalent rewrite changed behavior")
    base_all_free = versions[0]["evaluations"][0]["roots"]
    changed_all_free = versions[2]["evaluations"][0]["roots"]
    if any(a["packed_bits_sha256"] == b["packed_bits_sha256"] for a, b in zip(base_all_free, changed_all_free)):
        raise AssertionError("localized change failed to change an all-free root")
    return {
        "schema_version": "1.0",
        "case_id": f"{domain}-{case_index:03d}",
        "domain": domain,
        "synthetic_only": True,
        "workflow_hypothesis": spec["workflow"],
        "seed": seed,
        "variables": variables,
        "contexts": case_contexts,
        "versions": versions,
    }


def generate(output_dir: Path, seed: int, cases_per_domain: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for domain_index, (domain, spec) in enumerate(SCENARIOS.items()):
        records = [
            make_case(domain, spec, seed + domain_index * 100_000 + case_index, case_index)
            for case_index in range(cases_per_domain)
        ]
        path = output_dir / f"{domain}.jsonl"
        payload = b"".join(dump_bytes(record) for record in records)
        path.write_bytes(payload)
        files.append({
            "path": path.name,
            "domain": domain,
            "cases": len(records),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    manifest = {
        "schema_version": "1.0",
        "generator_version": GENERATOR_VERSION,
        "generated_for": "2026-08-27 use-case benchmark design",
        "seed": seed,
        "cases_per_domain": cases_per_domain,
        "domain_count": len(SCENARIOS),
        "case_count": cases_per_domain * len(SCENARIOS),
        "purpose_boundary": "Synthetic mechanism demonstration only; not evidence of domain dominance.",
        "truth_convention": "Free variables are enumerated LSB-first in listed order; packed output bit i is assignment i; bytes are little-endian.",
        "files": files,
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_bytes(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    checksum_lines = [f"{item['sha256']}  {item['path']}" for item in files]
    checksum_lines.append(f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  {manifest_path.name}")
    (output_dir / "CHECKSUMS.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "synthetic")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cases-per-domain", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.cases_per_domain <= 100:
        parser.error("--cases-per-domain must be from 1 through 100")
    manifest = generate(args.output.resolve(), args.seed, args.cases_per_domain)
    print(json.dumps({"output": str(args.output.resolve()), "case_count": manifest["case_count"], "files": len(manifest["files"])}, indent=2))


if __name__ == "__main__":
    main()
