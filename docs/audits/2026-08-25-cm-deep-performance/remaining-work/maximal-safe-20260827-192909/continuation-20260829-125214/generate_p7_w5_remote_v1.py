"""Generate four immutable W5 remote programs from the verified W4 transport."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "runpod_p7_w4_timing_remote_v1.py"
CAMPAIGN_PATH = (
    HERE.parents[5]
    / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01/campaign.json"
)
OUTPUT_MANIFEST = HERE / "P7-W5-REMOTE-PROGRAMS-V1.json"
PARENT_SHA256 = "54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd"


DERIVE_FUNCTION = r'''def derive_w5_freeze(parent_path, case_ids, expected_sha256, partition_id):
    import copy
    from cmbench.comparative.contracts import canonical_bytes
    from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze

    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    validate_freeze(parent)
    if parent.get("freeze_sha256") != PARENT_FREEZE_SHA256:
        raise RuntimeError("P6 parent freeze identity changed")
    selected = set(case_ids)
    if len(selected) != len(case_ids):
        raise RuntimeError("duplicate W5 selected case")
    derived = copy.deepcopy(parent)
    derived["cases"] = [case for case in parent["cases"] if case["case_id"] in selected]
    if len(derived["cases"]) != len(selected):
        raise RuntimeError("W5 selected case unavailable")
    policy = next(row for row in parent["schedule_policies"] if row["policy_id"] == POLICY_ID)
    normalized = {field: value for field, value in policy.items() if field != "order_ledger"}
    normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
    derived["schedule_policies"] = [normalized]
    provenance = dict(derived["provenance"])
    provenance["w5_development_partition"] = {
        "schema": "cm-comparative-p7-w5-development-partition/v1",
        "parent_freeze_sha256": PARENT_FREEZE_SHA256,
        "partition_id": partition_id,
        "policy_id": POLICY_ID,
        "case_count": len(case_ids),
        "selected_case_ids_in_parent_order": case_ids,
        "selected_case_ids_sha256": hashlib.sha256(canonical_bytes(case_ids)).hexdigest(),
        "typed_feasibility_exclusion": "development-epfl-sqrt-31cdaf5d0213",
        "case_selection_uses_comparative_timing": False,
        "shard_size_uses_w4_resource_timing": True,
    }
    derived["provenance"] = provenance
    core = {field: value for field, value in derived.items() if field != "freeze_sha256"}
    derived["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
    if derived["freeze_sha256"] != expected_sha256:
        raise RuntimeError("W5 derived freeze identity mismatch")
    validate_freeze(derived)
    path = OUT / (partition_id + "-FREEZE.json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(derived, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


'''


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(primary: dict, anchor: dict) -> str:
    shard_id = primary["partition_id"]
    text = SOURCE.read_text(encoding="utf-8")
    text = text.replace(
        '"""Run the frozen 12-case P7 W4 timing/RSS scout on one Linux allocation."""',
        f'"""Run the frozen {shard_id} P7 W5 development shard on one Linux allocation."""',
        1,
    )
    header = f'''SHARD_ID = {json.dumps(shard_id)}
POLICY_ID = {json.dumps(primary["policy_id"])}
PRIMARY_CASE_IDS = {json.dumps(primary["case_ids"], indent=4)}
PRIMARY_BLOCKS = {primary["blocks"]}
PRIMARY_CELLS = {primary["planned_cells"]}
PRIMARY_FREEZE_SHA256 = {json.dumps(primary["freeze_sha256"])}
ANCHOR_ID = {json.dumps(anchor["partition_id"])}
ANCHOR_CASE_IDS = {json.dumps(anchor["case_ids"], indent=4)}
ANCHOR_BLOCKS = {anchor["blocks"]}
ANCHOR_CELLS = {anchor["planned_cells"]}
ANCHOR_FREEZE_SHA256 = {json.dumps(anchor["freeze_sha256"])}
PARENT_FREEZE_SHA256 = {json.dumps(PARENT_SHA256)}
ROOT = Path({json.dumps("/workspace/cm-p7-w5-" + shard_id)})
'''
    text, count = re.subn(
        r"SCOUT_CASE_IDS = \[.*?\nROOT = Path\(\"/workspace/cm-p7-w4-timing\"\)\n",
        header,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("W4 remote header changed")
    start = text.index("def derive_w4_freeze(")
    end = text.index("def _validation_error", start)
    text = text[:start] + DERIVE_FUNCTION + text[end:]
    text = text.replace('for name in ("p7-ir", "p7-relation"):', 'for name in ("primary", "diagnostic-anchor"):', 1)
    text = text.replace('"principal_p7_result": False', '"principal_p7_result": True')
    text = text.replace('"w4_freeze_sha256": DERIVED_FREEZE_SHA256', '"w5_primary_freeze_sha256": PRIMARY_FREEZE_SHA256')
    start = text.index("    parent_freeze = ROOT /", text.index('emit("stage", name="offline-gate")'))
    end_marker = '    status = "complete"\n'
    end = text.index(end_marker, start) + len(end_marker)
    execution = '''    parent_freeze = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
    primary_freeze = str(derive_w5_freeze(
        parent_freeze, PRIMARY_CASE_IDS, PRIMARY_FREEZE_SHA256, SHARD_ID
    ))
    anchor_freeze = str(derive_w5_freeze(
        parent_freeze, ANCHOR_CASE_IDS, ANCHOR_FREEZE_SHA256, ANCHOR_ID
    ))
    execution_deadline = float(os.environ.pop("CM_EXECUTION_DEADLINE"))
    runs = (
        ("primary", primary_freeze, PRIMARY_CASE_IDS, PRIMARY_BLOCKS, ("regression", "development")),
        ("diagnostic-anchor", anchor_freeze, ANCHOR_CASE_IDS, ANCHOR_BLOCKS, ("development",)),
    )
    for name, freeze_path, case_ids, blocks, roles in runs:
        emit("stage", name=name)
        remaining = execution_deadline - time.time()
        if remaining <= 60:
            raise RuntimeError("insufficient W5 execution horizon")
        run_command(
            name,
            [
                sys.executable, "scripts/cm_comparative_p7_runner.py", "run",
                "--project-root", str(ROOT), "--freeze", freeze_path,
                "--output", str(OUT / name), "--policy", POLICY_ID,
                "--roles", *roles, "--blocks", str(blocks),
                "--profile", "performance",
                "--timeout-seconds", "30", "--rss-stop-bytes", str(1 << 30),
            ],
            min(840, remaining),
        )
        summary = json.loads((OUT / name / "summary.json").read_text(encoding="utf-8"))
        expected_cells = PRIMARY_CELLS if name == "primary" else ANCHOR_CELLS
        if (
            summary.get("status") != "passed"
            or summary.get("reconciliation", {}).get("planned_cells") != expected_cells
            or summary.get("reconciliation", {}).get("observed_cells") != expected_cells
            or summary.get("reconciliation", {}).get("statuses") != {"ok": expected_cells}
        ):
            raise RuntimeError(name + " summary did not reconcile")
        remaining = execution_deadline - time.time()
        if remaining <= 20:
            raise RuntimeError("insufficient W5 verification horizon")
        run_command(
            name + "-verify",
            [
                sys.executable, "scripts/cm_comparative_p7_runner.py", "verify",
                "--project-root", str(ROOT), "--freeze", freeze_path,
                "--output", str(OUT / name),
            ],
            min(120, remaining),
        )
    status = "complete"
'''
    text = text[:start] + execution + text[end:]
    if "derive_w4_freeze" in text or "SCOUT_CASE_IDS" in text or "DERIVED_FREEZE_SHA256" in text:
        raise RuntimeError("stale W4 remote symbol remains")
    compile(text, shard_id + ".py", "exec")
    return text


def main() -> int:
    if OUTPUT_MANIFEST.exists():
        raise FileExistsError(OUTPUT_MANIFEST)
    campaign = load(CAMPAIGN_PATH)
    definitions = {row["partition_id"]: row for row in campaign["definitions"]}
    rows = []
    for shard_id in ("p7-ir-a", "p7-ir-b", "p7-relation-a", "p7-relation-b"):
        primary = definitions[shard_id]
        anchor = definitions[primary["policy_id"] + "-anchor"]
        target = HERE / ("runpod_p7_w5_remote_v1_" + shard_id.replace("-", "_") + ".py")
        if target.exists():
            raise FileExistsError(target)
        target.write_text(build(primary, anchor), encoding="utf-8", newline="\n")
        rows.append(
            {
                "shard_id": shard_id,
                "path": target.name,
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
                "policy_id": primary["policy_id"],
                "primary_cells": primary["planned_cells"],
                "diagnostic_cells": anchor["planned_cells"],
                "primary_freeze_sha256": primary["freeze_sha256"],
                "anchor_freeze_sha256": anchor["freeze_sha256"],
            }
        )
    value = {
        "schema": "cm-runpod-p7-w5-remote-programs/v1",
        "source_template": SOURCE.name,
        "source_template_sha256": sha256(SOURCE),
        "campaign_sha256": sha256(CAMPAIGN_PATH),
        "programs": rows,
    }
    OUTPUT_MANIFEST.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
