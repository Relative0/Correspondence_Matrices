"""Generate four immutable remote programs for bounded W3 development partitions."""

from __future__ import annotations

from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "runpod_p7_w3_shard_remote_v2_relation_development.py"
PARTITIONS = {
    "ir-development-a": ("p7-ir", 0, 17),
    "ir-development-b": ("p7-ir", 17, 17),
    "relation-development-a": ("p7-relation", 0, 17),
    "relation-development-b": ("p7-relation", 17, 17),
}


DERIVE_FUNCTION = r'''
def derive_freeze_partition(original_path):
    """Create a source-equivalent functional subset and record its parent mapping."""
    import copy
    from cmbench.comparative.contracts import canonical_bytes
    from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze

    original = json.loads(original_path.read_text(encoding="utf-8"))
    policies = {row["policy_id"]: row for row in original["schedule_policies"]}
    policy = policies[SHARD["policy"]]
    cases = {row["case_id"]: row for row in original["cases"]}
    ordered = []
    for row in policy["order_ledger"]:
        case = cases[row["case_id"]]
        if case["role"] == "development" and row["case_id"] not in ordered:
            ordered.append(row["case_id"])
    selected = ordered[CASE_OFFSET:CASE_OFFSET + CASE_LIMIT]
    if len(ordered) != 34 or len(selected) != CASE_LIMIT:
        raise RuntimeError("development partition cardinality changed")

    derived = copy.deepcopy(original)
    selected_set = set(selected)
    derived["cases"] = [row for row in original["cases"] if row["case_id"] in selected_set]
    normalized = {key: value for key, value in policy.items() if key != "order_ledger"}
    normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
    derived["schedule_policies"] = [normalized]
    provenance = dict(derived["provenance"])
    provenance["functional_partition"] = {
        "schema": "cm-comparative-p7-functional-partition/v1",
        "parent_freeze_sha256": original["freeze_sha256"],
        "partition_id": SHARD_ID,
        "policy_id": SHARD["policy"],
        "role": "development",
        "case_offset": CASE_OFFSET,
        "case_limit": CASE_LIMIT,
        "selected_case_ids_in_parent_order": selected,
        "performance_measurement": False,
    }
    derived["provenance"] = provenance
    core = {key: value for key, value in derived.items() if key != "freeze_sha256"}
    derived["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
    validate_freeze(derived)

    path = OUT / "DERIVED-FREEZE.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(derived, stream, indent=2, sort_keys=True)
        stream.write("\n")
    metadata = {
        "schema": "cm-comparative-p7-functional-partition/v1",
        "partition_id": SHARD_ID,
        "policy_id": SHARD["policy"],
        "role": "development",
        "parent_freeze_sha256": original["freeze_sha256"],
        "derived_freeze_sha256": derived["freeze_sha256"],
        "case_offset": CASE_OFFSET,
        "case_limit": CASE_LIMIT,
        "parent_development_cases": len(ordered),
        "selected_case_ids_in_parent_order": selected,
        "selected_case_ids_sha256": hashlib.sha256(canonical_bytes(selected)).hexdigest(),
        "performance_measurement": False,
    }
    with (OUT / "DERIVED-FREEZE-METADATA.json").open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


'''


def build(partition_id: str, policy: str, offset: int, limit: int) -> str:
    text = SOURCE.read_text(encoding="utf-8")
    replacement = f'''SHARDS = {{
    "{partition_id}": {{"policy": "{policy}", "role": "development"}},
}}
SHARD_ID = "{partition_id}"
CASE_OFFSET = {offset}
CASE_LIMIT = {limit}
'''
    text, count = re.subn(
        r"SHARDS = \{.*?\n\}\nSHARD_ID = \"relation-development\"\n",
        replacement,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("remote shard header changed")
    marker = "def _validation_error(errors, section, exc):\n"
    if marker not in text:
        raise RuntimeError("remote validation marker changed")
    text = text.replace(marker, DERIVE_FUNCTION + marker, 1)
    old = (
        '    freeze_path = str(ROOT / "docs/research/verification/'
        'comparative-p6-candidate-v4-2026-08-30/freeze.json")\n'
    )
    new = (
        '    parent_freeze_path = ROOT / "docs/research/verification/'
        'comparative-p6-candidate-v4-2026-08-30/freeze.json"\n'
        '    freeze_path = str(derive_freeze_partition(parent_freeze_path))\n'
    )
    if old not in text:
        raise RuntimeError("remote freeze command changed")
    return text.replace(old, new, 1)


def main() -> int:
    for partition_id, (policy, offset, limit) in PARTITIONS.items():
        target = HERE / ("runpod_p7_w3_split_remote_v4_" + partition_id.replace("-", "_") + ".py")
        if target.exists():
            raise FileExistsError(target)
        target.write_text(build(partition_id, policy, offset, limit), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
