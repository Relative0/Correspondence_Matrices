"""Reproduce the biology audit from the retained, hash-bound local input freeze.

Run with the project Python from repository root:
python docs/audits/2026-09-14-cm-benchmark-attribution/corpus_audit.py --evidence-root PATH
No network, extraction, solver invocation, or changes to source evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cmbench.biology_bnet import parse_bnet, undeclared_bnet_regulators

FREEZE = "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-009"
ARCHIVE_SHA = "76f9eb1bcf4f758d06968647ade2232fccec02f92f80bf2b003043b57e97e04a"
SEED = "cm-biology-prospective-family-split-v1-20260914"

# Conservative leakage blocks inferred from archive model names, not verified
# publication genealogy. Multiple blocks may overlap; take their transitive union.
NAME_BLOCKS = {
    "mammalian-cell-cycle": [3, 23],
    "budding-yeast-cell-cycle": [24, 26, 146, 147, 159],
    "t-lgl-survival": [14, 25, 74],
    "breast-cell-line-time-variants": list(range(33, 39)),
    "cardiac-development": [10, 53],
    "bordetella-trichostrongylus": [43, 44, 46],
    "glucose-repression": [48, 173],
    "tumour-invasion-migration": [65, 86],
    "mapk-reductions": [70, 89, 90, 91],
    "tcr-tlr5-2018": [80, 81, 82],
    "macrophage-polarization": [94, 98],
    "pancreatic-microenvironment": [102, 103],
    "asymmetric-cell-division": [109, 110],
    "apoptosis-updated": [111, 138],
    "ags-fate-decision": [148, 149],
    "tcr-redox": [151, 152],
    "th-differentiation-control": [154, 155, 156, 157],
    "eggshell-patterning": [164, 165],
    "drosophila-gap": [169, 170, 171, 172],
    "hepatocellular-carcinoma": [92, 174, 199],
    "lymphoid-myeloid-specification": [73, 177],
    "multilevel-boolean-cell-cycle": [181, 182],
    "chicken-sex-determination": [185, 186],
    "mammal-sex-determination": [187, 188],
    "segment-polarity": [191, 192],
    "epithelial-mesenchymal-transition": [205, 206],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(expression):
    # Avoid Python recursion limits for the deeply nested original exports.
    completed = {}
    pending = [(expression, None)]
    while pending:
        node, children = pending.pop()
        kind = node[0]
        if kind in {"var", "const"}:
            completed[id(node)] = node
        elif children is None:
            children = []
            gather = list(node[1:])
            while gather:
                child = gather.pop()
                if kind in {"and", "or"} and child[0] == kind:
                    gather.extend(child[1:])
                else:
                    children.append(child)
            pending.append((node, children))
            pending.extend((child, None) for child in children)
        else:
            children = [completed[id(child)] for child in children]
            if kind in {"and", "or"}:
                # Associativity/commutativity only, not general equivalence.
                children = sorted(children, key=repr)
            completed[id(node)] = (kind, *children)
    return completed[id(expression)]


def size_bin(n):
    return "n01-10" if n <= 10 else "n11-20" if n <= 20 else "n21-50" if n <= 50 else "n51-plus"


def width_bin(n):
    return "w00-03" if n <= 3 else "w04-08" if n <= 8 else "w09-plus"


def local_truth_table(function):
    """Exact vectorized table, LSB row is all-zero in sorted regulator order."""
    n = len(function.regulators)
    if n > 12:
        return None
    rows = 1 << n
    mask = (1 << rows) - 1
    values = {name: sum(1 << row for row in range(rows) if (row >> i) & 1)
              for i, name in enumerate(function.regulators)}
    completed = {}
    pending = [(function.expression, False)]
    while pending:
        node, visited = pending.pop()
        kind = node[0]
        if kind == "const":
            completed[id(node)] = mask if node[1] else 0
        elif kind == "var":
            completed[id(node)] = values[node[1]]
        elif not visited:
            pending.append((node, True))
            pending.extend((child, False) for child in node[1:])
        elif kind == "not":
            completed[id(node)] = completed[id(node[1])] ^ mask
        else:
            value = mask if kind == "and" else 0
            for child in node[1:]:
                if kind == "and":
                    value &= completed[id(child)]
                else:
                    value |= completed[id(child)]
            completed[id(node)] = value
    return [function.target, function.regulators, hex(completed[id(function.expression)])]


def audit(evidence_root):
    freeze_path = evidence_root / FREEZE / "INPUT_FREEZE.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    archive_path = evidence_root / FREEZE / "raw/edition-2022-bnet.zip"
    archive_bytes = archive_path.read_bytes()
    assert sha(archive_bytes) == ARCHIVE_SHA == freeze["biology"]["archive"]["sha256"]
    models, equations, targets_by_id = [], {}, {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        metadata_bytes = archive.read("edition-2022-bnet/metadata.json")
        summary_bytes = archive.read("edition-2022-bnet/summary.csv")
        metadata = json.loads(metadata_bytes)
        assert metadata["input_representation"] == "free"
        raw_rows = list(csv.reader(io.StringIO(summary_bytes.decode()), skipinitialspace=True))
        assert raw_rows[0] == ["ID", "name", "variables", "regulations"]
        assert all(len(row) == 5 for row in raw_rows[1:])
        summary = {row[0]: row for row in raw_rows[1:]}
        for item in freeze["biology"]["rows"]:
            raw = (evidence_root / item["path"]).read_bytes()
            assert sha(raw) == item["sha256"]
            assert raw == archive.read(item["case_source"])
            functions = parse_bnet(raw.decode())
            model_id = Path(item["case_source"]).stem
            entry = summary[model_id]
            targets = {function.target for function in functions}
            external = list(undeclared_bnet_regulators(functions))
            supports = [len(function.regulators) for function in functions]
            equation_set = {(f.target, repr(canonical(f.expression))) for f in functions}
            equations[model_id] = equation_set
            targets_by_id[model_id] = targets
            normalized = json.dumps(sorted(equation_set), separators=(",", ":")).encode()
            local_tables = [local_truth_table(function) for function in functions]
            semantic_sha = None if any(table is None for table in local_tables) else sha(json.dumps(sorted(local_tables), separators=(",", ":")).encode())
            collisions = [{"external": name, "declared": other}
                          for name in external for other in sorted(targets)
                          if name != other and name.casefold() == other.casefold()]
            models.append({
                "model_id": model_id, "name": entry[1], "input_sha256": sha(raw),
                "bytes": len(raw), "path": item["path"], "archive_member": item["case_source"],
                "source_url": freeze["biology"]["record"]["files"][0]["content_url"] + "#" + item["case_source"],
                "source_revision": "zenodo:8020309", "summary_line": int(model_id) + 1,
                "parsed_functions": len(functions), "all_variables": len(targets | set(external)),
                "regulation_occurrences_by_distinct_target_regulator": sum(supports),
                "maximum_support_width": max(supports),
                "support_width_histogram": dict(sorted(Counter(supports).items())),
                "size_stratum": size_bin(len(functions)), "support_stratum": width_bin(max(supports)),
                "classification": "open" if external else "closed", "parse_status": "valid",
                "external_regulators": external,
                "external_semantics": "archive_declares_free_input_export" if external else "closed_under_declared_targets",
                "biological_role_validation": "unresolved_per_regulator_source_annotations_absent" if external else "not_applicable",
                "translation_integrity": "byte_identical_to_archive_and_syntax_valid; original_translation_not_independently_validated",
                "casefold_collision_flags": collisions,
                "constant_targets": {f.target: f.expression[1] for f in functions if f.expression[0] == "const"},
                "identity_targets": sorted(f.target for f in functions if f.expression == ("var", f.target)),
                "canonical_equation_sha256": sha(normalized),
                "local_truth_table_equation_sha256": semantic_sha,
                "summary_numeric_fields": [int(v) for v in entry[2:]],
                "summary_matches_parsed_functions_external_regulations":
                    [int(v) for v in entry[2:]] == [len(functions), len(external), sum(supports)],
                "summary_count_discrepancy_flags": {
                    "functions": int(entry[2]) != len(functions),
                    "external_regulators": int(entry[3]) != len(external),
                    "regulations": int(entry[4]) != sum(supports),
                },
            })
    models.sort(key=lambda row: row["model_id"])
    assert len(models) == 212
    parent = {row["model_id"]: row["model_id"] for row in models}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def merge(left, right):
        a, b = sorted([find(left), find(right)])
        parent[b] = a

    relations = []
    for label, ids in NAME_BLOCKS.items():
        ids = [f"{value:03d}" for value in ids]
        relations.append({"kind": "named_family_or_variant_candidate", "label": label,
                          "models": ids, "confidence": "conservative_leakage_block_not_verified_genealogy"})
        for model_id in ids[1:]:
            merge(ids[0], model_id)
    exact_groups = defaultdict(list)
    normalized_groups = defaultdict(list)
    semantic_groups = defaultdict(list)
    for row in models:
        exact_groups[row["input_sha256"]].append(row["model_id"])
        normalized_groups[row["canonical_equation_sha256"]].append(row["model_id"])
        if row["local_truth_table_equation_sha256"] is not None:
            semantic_groups[row["local_truth_table_equation_sha256"]].append(row["model_id"])
    for kind, groups in [("byte_identical", exact_groups), ("canonical_equations_identical", normalized_groups), ("local_truth_table_equations_identical", semantic_groups)]:
        for digest, ids in sorted(groups.items()):
            if len(ids) > 1:
                relations.append({"kind": kind, "models": ids, "sha256": digest, "confidence": "demonstrated"})
                for model_id in ids[1:]:
                    merge(ids[0], model_id)
    for i, left in enumerate(models):
        a = left["model_id"]
        for right in models[i + 1:]:
            b = right["model_id"]
            shared = len(equations[a] & equations[b])
            smaller = min(len(equations[a]), len(equations[b]))
            if shared >= 5 and shared / smaller >= .8 and equations[a] != equations[b]:
                relations.append({"kind": "shared_equation_ancestry_candidate", "models": [a, b],
                                  "shared_equations": shared, "smaller_equation_fraction": shared / smaller,
                                  "confidence": "syntax_overlap_evidence_not_verified_genealogy"})
                merge(a, b)
    groups = defaultdict(list)
    for row in models:
        groups[find(row["model_id"])].append(row)
    # Previously screened models cannot become pristine heldout simply by hashing.
    results = json.loads((ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/successor-results-analysis-001/RESULTS.json").read_text())
    exposed_prefixes = {row["case_id"].removeprefix("biology-closed-") for row in results["case_results"] if row["lane"] == "biology_fixed_points"}
    clusters = []
    by_stratum = defaultdict(list)
    for root, members in sorted(groups.items()):
        cluster_id = "biology-family-" + root
        exposure = any(row["input_sha256"].startswith(tuple(exposed_prefixes)) for row in members)
        closed = [row for row in members if row["classification"] == "closed"]
        stratum = (size_bin(max(row["parsed_functions"] for row in members)),
                   width_bin(max(row["maximum_support_width"] for row in members)))
        cluster = {"cluster_id": cluster_id, "models": [row["model_id"] for row in members],
                   "closed_models": [row["model_id"] for row in closed], "stratum": list(stratum),
                   "successor_timing_exposed": exposure,
                   "split_hash": sha((SEED + "\0" + cluster_id).encode()),
                   "partition": "development" if exposure else "pending",
                   "heldout_status": "not_pristine_all_corpus_available_and_previous_screen_selection_known"}
        clusters.append(cluster)
        if not exposure:
            by_stratum[stratum].append(cluster)
    # Hamilton allocation to 60/20/20 within each stratum, deterministic hash order.
    for candidates in by_stratum.values():
        candidates.sort(key=lambda row: row["split_hash"])
        n = len(candidates)
        quotas = [n * .6, n * .2, n * .2]
        counts = [int(q) for q in quotas]
        for index in sorted(range(3), key=lambda i: (-(quotas[i] - counts[i]), i))[:n - sum(counts)]:
            counts[index] += 1
        assignments = [part for part, count in zip(["train", "development", "heldout_candidate"], counts) for _ in range(count)]
        for cluster, partition in zip(candidates, assignments):
            cluster["partition"] = partition
    for cluster in clusters:
        for model_id in cluster["models"]:
            row = next(row for row in models if row["model_id"] == model_id)
            row["independence_cluster"] = cluster["cluster_id"]
            row["recommended_partition"] = cluster["partition"]
            row["successor_case_id"] = next(("biology-closed-" + prefix for prefix in exposed_prefixes if row["input_sha256"].startswith(prefix)), None)
    summary = {
        "models": len(models), "classification": dict(Counter(row["classification"] for row in models)),
        "parse_failures": 0, "archive_byte_mismatches": 0,
        "summary_numeric_match_models": sum(row["summary_matches_parsed_functions_external_regulations"] for row in models),
        "summary_count_discrepancy_models": {key: [row["model_id"] for row in models if row["summary_count_discrepancy_flags"][key]] for key in ["functions", "external_regulators", "regulations"]},
        "external_regulator_occurrences": sum(len(row["external_regulators"]) for row in models),
        "open_models_with_casefold_collision_flags": sum(bool(row["casefold_collision_flags"]) for row in models),
        "exact_duplicate_groups": sum(len(ids) > 1 for ids in exact_groups.values()),
        "canonical_equation_duplicate_groups": sum(len(ids) > 1 for ids in normalized_groups.values()),
        "local_truth_table_equation_duplicate_groups": sum(len(ids) > 1 for ids in semantic_groups.values()),
        "models_with_all_supports_at_most_12_and_semantic_fingerprint": sum(row["local_truth_table_equation_sha256"] is not None for row in models),
        "ancestry_relation_kinds": dict(Counter(row["kind"] for row in relations)),
        "conservative_independence_clusters": len(clusters),
        "clusters_containing_closed_models": sum(bool(row["closed_models"]) for row in clusters),
        "partition_models": dict(Counter(row["recommended_partition"] for row in models)),
        "partition_closed_models": dict(Counter(row["recommended_partition"] for row in models if row["classification"] == "closed")),
    }
    assert summary["classification"] == {"open": 190, "closed": 22}
    return {"schema_version": 1, "audit_date": "2026-09-14", "summary": summary,
            "evidence_root": str(evidence_root),
            "evidence": {"freeze_path": FREEZE + "/INPUT_FREEZE.json", "freeze_sha256": sha(freeze_path.read_bytes()),
                         "archive_path": FREEZE + "/raw/edition-2022-bnet.zip", "archive_sha256": ARCHIVE_SHA,
                         "metadata_member_sha256": sha(metadata_bytes), "summary_member_sha256": sha(summary_bytes),
                         "archive_metadata": metadata, "license": freeze["biology"]["license"],
                         "parser_sha256": sha((ROOT / "cmbench/biology_bnet.py").read_bytes()),
                         "generator_sha256": sha(Path(__file__).read_bytes())},
            "interpretation": {
                "open": "All 190 parse and are byte-identical to the free-input archive export. Omitted update functions are consistent with declared free-input export; absence alone is not broken translation evidence.",
                "summary_header": "Four header fields label five data fields. All values are retained. Empirically compare fields 3/4/5 to parsed function count/external regulator count/regulation count; do not assume absent header semantics.",
                "biological_input_vs_error": "Export intent is established; biological input/perturbation roles and original translation fidelity remain unresolved per regulator because this archive has no original model annotations or bibliography. Casefold collisions flag manual review, not correction.",
                "summary_discrepancies": "Models 039 and 094 have fewer syntactically referenced external regulators than the summary's fourth field (12 vs 14; 7 vs 8). Eighteen models have fewer syntactic edges. Unused original inputs, removed graph edges, export simplification, or translation loss cannot be distinguished here. Do not infer counts over the original model's full input space from exported BNet alone.",
                "open_contract": "Require a named external-input assignment for each query or explicitly count (internal state,input) pairs / project onto internal states. These are different tasks. Do not silently add identity equations or pin inputs.",
                "duplicate_limits": "Byte equality, associative/commutative AST equality, and exact local truth-table equality (all functions support <=12) are checked. Table fingerprints preserve syntactic regulator sets and may miss equivalence with redundant regulators. No complete arbitrary variable-renaming/isomorphism search; candidate ancestry is not proof of shared publication.",
                "independence": "Use conservative family connected components for partitions, resampling, and aggregate claims. Queries, perturbations, repeated runs, and model variants remain nested measurements; singleton clusters do not prove independence.",
                "split": "Seeded SHA256 ordering and 60/20/20 Hamilton allocation within size/support strata; successor-timing-exposed clusters forced to development. All partitions are recommendations; candidate heldout is not pristine given prior corpus access and screening. Freeze algorithm and query generator before any new measurements; use independently sourced families for a confirmatory gate.",
                "seed": SEED,
            }, "relations": relations, "clusters": clusters, "models": models}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("BIOLOGY_CORPUS_AUDIT.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    result = audit(args.evidence_root.resolve())
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


def self_test():
    from cmbench.biology_bnet import evaluate_bnet
    rng = random.Random(20260914)

    def expression(depth):
        if not depth or rng.random() < .3:
            return rng.choice(["a", "b", "c", "0", "1"])
        if rng.random() < .25:
            return "!(" + expression(depth - 1) + ")"
        return "(" + expression(depth - 1) + rng.choice(["&", "|"]) + expression(depth - 1) + ")"

    assignments = 0
    for _ in range(200):
        function = parse_bnet("targets,factors\nz, " + expression(5))[0]
        table = int(local_truth_table(function)[2], 16)
        for row in range(1 << len(function.regulators)):
            values = {name: (row >> i) & 1 for i, name in enumerate(function.regulators)}
            assert (table >> row) & 1 == evaluate_bnet(function.expression, values)
            assignments += 1
    a = parse_bnet("targets,factors\nz, (a & (b & c))")[0]
    b = parse_bnet("targets,factors\nz, ((c & a) & b)")[0]
    c = parse_bnet("targets,factors\nz, ((c & a) | b)")[0]
    assert canonical(a.expression) == canonical(b.expression)
    assert canonical(a.expression) != canonical(c.expression)
    deep = parse_bnet("targets,factors\nz, " + "(a & " * 4000 + "b" + ")" * 4000)[0]
    assert local_truth_table(deep)[2] == "0x8"
    assert canonical(deep.expression)[0] == "and"
    print(f"PASS: 200 seeded expressions, {assignments} scalar/table comparisons, canonical positive/negative controls, depth-4000 input.")


if __name__ == "__main__":
    main()
