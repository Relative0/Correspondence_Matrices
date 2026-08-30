"""Bounded W8 semantic/root/oracle scout for frozen converted LogikBench BLIFs."""

from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


MIN_SUPPORT = 4
MAX_SUPPORT = 16
MAX_SOURCE_NODES = 4096
PER_CASE_SECONDS = 45
TOTAL_SECONDS = 720
PRIMARY_CASES = 30
CHILD_OUTPUT_CAP = 64 << 10


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def support_bin(value: int) -> str:
    return "k04-07" if value <= 7 else "k08-11" if value <= 11 else "k12-16"


def node_bin(value: int) -> str:
    return "nodes0001-0064" if value <= 64 else "nodes0065-0512" if value <= 512 else "nodes0513-4096"


def one_case(payload_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    cluster_id = payload["cluster_id"]
    path = Path(payload["path"])
    expected_sha256 = payload["blif_sha256"]
    result = {
        "schema": "cm-comparative-w8-semantic-case/v1",
        "cluster_id": cluster_id,
        "blif_sha256": expected_sha256,
        "status": "rejected",
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }
    try:
        if not path.is_file() or path.is_symlink() or sha256(path) != expected_sha256:
            raise RuntimeError("converted BLIF identity mismatch")
        from bitset_backend import build_bitset_env, eval_expr_bitset
        from cmbench.recognition.blif import parse_blif

        netlist = parse_blif(path)
        ordered_outputs = sorted(
            netlist.outputs,
            key=lambda root: (sha256_bytes(("cm-w8-root-v1\0" + cluster_id + "\0" + root).encode()), root),
        )
        selected = None
        eligible_output_count = 0
        for root in ordered_outputs:
            metadata = netlist.bounded_metadata(
                root,
                min_support=MIN_SUPPORT,
                max_support=MAX_SUPPORT,
                max_source_nodes=MAX_SOURCE_NODES,
            )
            if metadata is None:
                continue
            eligible_output_count += 1
            if selected is None:
                selected = metadata
        if selected is None:
            result.update(error="no_bounded_primary_output", outputs=len(netlist.outputs))
        else:
            expression, expression_support = netlist.build_expr(
                selected.node, max_identity_nodes=MAX_SOURCE_NODES
            )
            packed, packed_support = netlist.packed_value(selected.node)
            if expression_support != selected.support or packed_support != selected.support:
                raise RuntimeError("translation/oracle support disagreement")
            k = len(selected.support)
            translated = eval_expr_bitset(
                expression, build_bitset_env(tuple(f"x{index}" for index in range(k)))
            )
            if translated != packed:
                raise RuntimeError("CM expression translation disagrees with BLIF oracle")
            truth_bytes = packed.to_bytes(((1 << k) + 7) // 8, "little")
            truth_sha256 = sha256_bytes(truth_bytes)
            oracle_core = {
                "schema": "cm-comparative-w8-blif-oracle/v1",
                "cluster_id": cluster_id,
                "blif_sha256": expected_sha256,
                "root": selected.node,
                "support": list(selected.support),
                "k": k,
                "encoding": "packed truth bits; assignment index; little-endian bytes; frozen sorted support order",
                "truth_sha256": truth_sha256,
            }
            result.update({
                "status": "eligible",
                "model": netlist.model,
                "inputs": len(netlist.inputs),
                "outputs": len(netlist.outputs),
                "eligible_output_count": eligible_output_count,
                "root": selected.node,
                "root_selection_key": sha256_bytes(
                    ("cm-w8-root-v1\0" + cluster_id + "\0" + selected.node).encode()
                ),
                "support": list(selected.support),
                "k": k,
                "source_nodes": selected.source_nodes,
                "source_edges": selected.source_edges,
                "depth": selected.depth,
                "local_fanin": selected.local_fanin,
                "local_cubes": selected.local_cubes,
                "local_literals": selected.local_literals,
                "truth_sha256": truth_sha256,
                "truth_ones": packed.bit_count(),
                "truth_density_ppm": round(packed.bit_count() * 1_000_000 / (1 << k)),
                "oracle_sha256": sha256_bytes(canonical_bytes(oracle_core)),
                "translation_compatible": True,
                "translation_truth_sha256": truth_sha256,
            })
    except Exception as exc:
        result.update(error="case_exception", error_type=type(exc).__name__, error_detail=str(exc)[:500])
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def select_primary(unique_rows: list[dict]) -> list[dict]:
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in unique_rows:
        row["primary_selection_key"] = sha256_bytes(
            ("cm-w8-primary-v1\0" + row["cluster_id"] + "\0" + row["root"] + "\0" + row["blif_sha256"]).encode()
        )
        buckets[(row["group"], support_bin(row["k"]), node_bin(row["source_nodes"]))].append(row)
    for values in buckets.values():
        values.sort(key=lambda row: (row["primary_selection_key"], row["cluster_id"]))
    result = []
    depth = 0
    while len(result) < PRIMARY_CASES:
        added = False
        for key in sorted(buckets):
            values = buckets[key]
            if depth < len(values):
                result.append(values[depth])
                added = True
                if len(result) == PRIMARY_CASES:
                    break
        if not added:
            break
        depth += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversion-root", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--one-case", type=Path)
    args = parser.parse_args()
    if args.one_case is not None:
        return one_case(args.one_case)
    if args.output.exists():
        raise RuntimeError("semantic output already exists")
    args.output.mkdir(parents=True)
    case_inputs = args.output / "case-inputs"
    case_inputs.mkdir()
    conversions = json.loads((args.conversion_root / "conversions.json").read_text(encoding="utf-8"))
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    acquisition = json.loads(args.acquisition.read_text(encoding="utf-8"))
    if conversions.get("converted") != 64 or conversions.get("attempted") != 70:
        raise RuntimeError("conversion outcome identity changed")
    admitted = {row["cluster_id"]: row for row in admission["clusters"]}
    acquired = {row["cluster_id"]: row for row in acquisition["clusters"]}
    rows = []
    deadline = time.monotonic() + TOTAL_SECONDS
    converted_rows = [row for row in conversions["rows"] if row.get("status") == "converted"]
    for index, conversion in enumerate(converted_rows):
        cluster_id = conversion["cluster_id"]
        path = args.conversion_root / "converted" / (cluster_id + ".blif")
        case_input = case_inputs / f"{index:03d}.json"
        write(case_input, {
            "cluster_id": cluster_id,
            "path": str(path),
            "blif_sha256": conversion["sha256"],
        })
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            child = {"cluster_id": cluster_id, "blif_sha256": conversion["sha256"],
                     "status": "rejected", "error": "total_semantic_deadline",
                     "performance_measurement": False, "performance_claim_permitted": False}
        else:
            try:
                process = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()),
                     "--conversion-root", str(args.conversion_root),
                     "--admission", str(args.admission),
                     "--acquisition", str(args.acquisition),
                     "--output", str(args.output),
                     "--one-case", str(case_input)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=min(PER_CASE_SECONDS, max(1, remaining)),
                    check=False,
                    env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                         "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"},
                )
                if len(process.stdout) > CHILD_OUTPUT_CAP or len(process.stderr) > CHILD_OUTPUT_CAP:
                    raise RuntimeError("child output cap exceeded")
                if process.returncode:
                    child = {"cluster_id": cluster_id, "blif_sha256": conversion["sha256"],
                             "status": "rejected", "error": "child_exit",
                             "returncode": process.returncode,
                             "stderr": process.stderr.decode(errors="replace")[-1000:],
                             "performance_measurement": False, "performance_claim_permitted": False}
                else:
                    child = json.loads(process.stdout)
            except subprocess.TimeoutExpired:
                child = {"cluster_id": cluster_id, "blif_sha256": conversion["sha256"],
                         "status": "rejected", "error": "case_timeout",
                         "performance_measurement": False, "performance_claim_permitted": False}
        if child.get("cluster_id") != cluster_id or child.get("blif_sha256") != conversion["sha256"]:
            raise RuntimeError("semantic child identity mismatch")
        static = admitted[cluster_id]
        source = acquired[cluster_id]
        child.update({
            "group": static["group"],
            "name": static["name"],
            "source_set_sha256": static["source_set_sha256"],
            "tree_sha256": static["tree_sha256"],
            "rtl_paths": static["rtl_paths"],
            "rtl_sha256": static["rtl_sha256"],
            "license_ids": static["license_ids"],
            "license_paths": static["license_paths"],
            "ai_provenance_present": source["ai_provenance_present"],
        })
        rows.append(child)

    eligible = [row for row in rows if row.get("status") == "eligible"]
    semantic_seen = {}
    unique = []
    duplicates = []
    for row in eligible:
        semantic_key = f"{row['k']}:{row['truth_sha256']}"
        row["semantic_key"] = semantic_key
        if semantic_key in semantic_seen:
            row["semantic_duplicate_of"] = semantic_seen[semantic_key]
            duplicates.append(row)
        else:
            semantic_seen[semantic_key] = row["cluster_id"]
            row["semantic_duplicate_of"] = None
            unique.append(row)
    primary = select_primary(unique)
    if len(primary) != PRIMARY_CASES:
        raise RuntimeError(f"only {len(primary)} unique eligible clusters; W8 requires 30")
    primary_ids = {row["cluster_id"] for row in primary}
    for row in rows:
        row["primary_selected"] = row.get("cluster_id") in primary_ids

    oracle_rows = []
    cases = []
    for row in primary:
        root_digest = sha256_bytes(row["root"].encode())[:12]
        case_id = f"confirmation-logikbench-{row['name']}-{root_digest}"
        oracle = {
            "case_id": case_id,
            "cluster_id": row["cluster_id"],
            "input_sha256": row["blif_sha256"],
            "root": row["root"],
            "support": row["support"],
            "k": row["k"],
            "encoding": "packed truth bits; assignment index; little-endian bytes; frozen sorted support order",
            "truth_sha256": row["truth_sha256"],
            "oracle_sha256": row["oracle_sha256"],
        }
        oracle_rows.append(oracle)
        cases.append({
            "case_id": case_id,
            "cluster_id": row["cluster_id"],
            "role": "confirmation",
            "origin": "natural",
            "family": row["group"],
            "kind": "blif",
            "tasks": ["ir_preparation", "complete_relation"],
            "source": {
                "path": "sources/" + row["cluster_id"] + ".blif",
                "sha256": row["blif_sha256"],
                "upstream_repository": acquisition["repository"],
                "upstream_commit": acquisition["commit"],
                "upstream_rtl_paths": row["rtl_paths"],
                "upstream_rtl_sha256": row["rtl_sha256"],
                "license_ids": row["license_ids"],
                "license_paths": row["license_paths"],
                "conversion_tool": "Yosys 0.23 Debian package 0.23-6",
            },
            "strata": {
                "root": row["root"],
                "support": row["support"],
                "live_k": row["k"],
                "syntactic_support": row["k"],
                "semantic_support": None,
                "dag_nodes": row["source_nodes"],
                "source_edges": row["source_edges"],
                "depth": row["depth"],
                "shape": "circuit-output-cone",
                "truth_density_ppm": row["truth_density_ppm"],
                "selection_max_support": MAX_SUPPORT,
                "selection_max_source_nodes": MAX_SOURCE_NODES,
                "root_selection_key": row["root_selection_key"],
                "primary_selection_key": row["primary_selection_key"],
            },
            "oracle": oracle,
        })
    schedule = {
        "schema": "cm-comparative-w8-confirmation-schedule-contract/v1",
        "locality": "round_robin",
        "seed": 0,
        "ir": {"blocks": 8, "arms": ["cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat"]},
        "relation": {"blocks": 10, "arms": ["cm-dense", "cm-packed-bigint", "cm-packed-words", "cm-no-reinflate", "cm-cse-flat"]},
        "counterbalance": "balanced_orders: every arm in every position twice, one forward and one reverse cycle",
        "execution_stage": "P9/W10 only after development analysis is frozen",
    }
    metrics = {
        "schema": "cm-comparative-w8-primary-metrics/v1",
        "correctness": "exact oracle digest equality; any mismatch invalidates affected confirmation claim",
        "timing": "paired per-case task_total_wall_ns; median and MAD; complete counterbalance cycles only",
        "memory": "sampled owned-process-group peak RSS, reported separately from cgroup limits",
        "refusals": "all typed refusals retained; no confirmation case may be dropped after execution begins",
        "performance_measurement_in_this_scout": False,
    }
    write(args.output / "semantic-scout.json", {
        "schema": "cm-comparative-w8-semantic-scout/v1",
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "converted_inputs": len(converted_rows),
        "terminal_rows": len(rows),
        "eligible": len(eligible),
        "unique_eligible": len(unique),
        "semantic_duplicates": len(duplicates),
        "primary_selected": len(primary),
        "rows": rows,
    })
    write(args.output / "oracle-package.json", {
        "schema": "cm-comparative-w8-oracle-package/v1",
        "generator": "cmbench.recognition.blif.BlifNetlist.packed_value",
        "performance_measurement": False,
        "rows": oracle_rows,
    })
    write(args.output / "confirmation-draft.json", {
        "schema": "cm-comparative-w8-logikbench-confirmation-draft/v1",
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "selection_rule": "one hash-ordered bounded primary output per cluster; semantic first occurrence; round-robin static group/support/node strata",
        "case_count": len(cases),
        "cases": cases,
        "schedule_contract": schedule,
        "primary_metrics": metrics,
    })
    print(json.dumps({
        "converted_inputs": len(converted_rows),
        "terminal_rows": len(rows),
        "eligible": len(eligible),
        "unique_eligible": len(unique),
        "semantic_duplicates": len(duplicates),
        "primary_selected": len(primary),
        "performance_measurement": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
