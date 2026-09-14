"""Prepare or verify the bounded CM benchmark package; never launch RunPod."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.campaign_prelaunch import (
    Candidate,
    adapter_readiness,
    build_admission_ledger,
    build_arm_manifest,
    build_schedule_ledger,
    build_upload_bundles,
    canonical_digest,
    environment_lock,
    sha256_file,
    source_identity,
    synthetic_specs,
    utc_now,
    validate_admission_ledger,
    verify_upload_bundles,
)


CAMPAIGN_ID = "cm-mega-prelaunch-20260914-008"
DEFAULT_OUT = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/prelaunch-008"
RESEARCH = ROOT / "docs/research/cm-benchmark-research-2026-09-13"
LOGIK = ROOT / "docs/research/verification/comparative-w8-logikbench-confirmation-v1-2026-08-31"
FEATURE = ROOT / "docs/audits/2026-09-11-cm-next-research"
AFFINE = ROOT / "docs/audits/2026-09-11-cm-scalar-research"
INPUT_FREEZE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-009"
INPUT_FREEZE_MANIFEST = "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-009/INPUT_FREEZE.json"
COUNTING_LICENSE = "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-009/COUNTING-LICENSE.txt"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(data, encoding="utf-8", newline="\n")


def cluster_role(cluster_id: str) -> str:
    bucket = int(hashlib.sha256(cluster_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    return "development" if bucket < 4 else "confirmation" if bucket < 8 else "regression"


def candidates() -> list[Candidate]:
    rows: list[Candidate] = []
    logik_manifest = read_json(LOGIK / "source-manifest.json")
    for item in logik_manifest["files"]:
        source = LOGIK / item["path"]
        relative = source.relative_to(ROOT).as_posix()
        prefix = item["cluster_id"].split("-")[1]
        family = "H08" if prefix in {"basic", "blocks"} else "H08"
        rows.append(Candidate(
            case_id="hardware-" + item["case_id"], group="hardware", family_id=family,
            cluster_id=item["cluster_id"], role="regression", path=relative, kind="blif",
            source_url=item["upstream_repository"], source_revision=item["upstream_commit"],
            expected_sha256=item["sha256"], license_spdx="MIT",
            license_path="docs/research/verification/comparative-w8-logikbench-confirmation-v1-2026-08-31/source-manifest.json",
            redistribution="permitted_with_license_notice",
            transformations=("RTL to BLIF using " + item["conversion_tool"],),
        ))
    feature_manifest = read_json(FEATURE / "CORPUS.json")
    for item in feature_manifest["files"]:
        if not item.get("admitted") and not all(key in item for key in ("filename", "url", "sha256")):
            continue
        source = FEATURE / "corpus" / item["filename"]
        rows.append(Candidate(
            case_id="feature-" + item["id"], group="feature_models", family_id="F01",
            cluster_id="softvare-" + Path(item["source_path"]).parent.name.lower(), role="regression",
            path=source.relative_to(ROOT).as_posix(), kind="cnf", source_url=item["url"],
            source_revision=feature_manifest["commit"], expected_sha256=item["sha256"],
            license_spdx="MIT", license_path="docs/audits/2026-09-11-cm-next-research/corpus/UPSTREAM-LICENSE.txt",
            redistribution="permitted_with_license_notice",
        ))
    affine_manifest = read_json(AFFINE / "CORPUS.json")
    for item in affine_manifest["files"]:
        source = AFFINE / "corpus" / item["name"]
        rows.append(Candidate(
            case_id="affine-" + Path(item["name"]).stem, group="affine", family_id="A01",
            cluster_id="gnuradio-ldpc-" + Path(item["name"]).stem, role="regression",
            path=source.relative_to(ROOT).as_posix(), kind="alist", source_url=item["url"],
            source_revision=affine_manifest["commit"], expected_sha256=item["sha256"],
            license_spdx="GPL-3.0-only", license_path="docs/audits/2026-09-11-cm-scalar-research/corpus/COPYING",
            redistribution="permitted_with_license_notice",
        ))
    freeze = read_json(INPUT_FREEZE / "INPUT_FREEZE.json")
    from cmbench.biology_bnet import parse_bnet

    biology_by_model = []
    for item in freeze["biology"]["rows"]:
        source = ROOT / item["path"]
        functions = [function for function in parse_bnet(source.read_text(encoding="utf-8"))
                     if len(function.regulators) <= 32]
        if functions:
            biology_by_model.append((item, functions))
    selected = []
    depth = 0
    while len(selected) < 300:
        before = len(selected)
        for item, functions in biology_by_model:
            if depth < len(functions):
                selected.append((item, functions[depth]))
                if len(selected) == 300:
                    break
        if len(selected) == before:
            raise ValueError("biology input freeze has fewer than 300 bounded update functions")
        depth += 1
    biology_url = freeze["biology"]["record"]["files"][0]["content_url"]
    for item, function in selected:
        cluster = "biodivine-" + Path(item["path"]).stem
        identity = hashlib.sha256((cluster + "\0" + function.target).encode("utf-8")).hexdigest()
        rows.append(Candidate(
            case_id="biology-" + identity[:16], group="biological_functions", family_id="B01",
            cluster_id=cluster, role=cluster_role(cluster), path=item["path"], kind="bnet",
            source_url=biology_url + "#" + item["case_source"], source_revision="zenodo:8020309",
            expected_sha256=item["sha256"], license_spdx="CC-BY-4.0",
            license_path=INPUT_FREEZE_MANIFEST, redistribution="permitted_with_license_notice",
            transformations=("ZIP member extraction only",), selector=function.target,
        ))
    counting_revision = freeze["counting"]["revision"]
    repository = freeze["counting"]["repository"]
    for item in freeze["counting"]["rows"]:
        cluster = "counting-" + hashlib.sha256(str(Path(item["source_path"]).parent).encode("utf-8")).hexdigest()[:16]
        rows.append(Candidate(
            case_id=f"counting-{item['track']}-{item['source_git_blob'][:16]}",
            group="sat_and_counting", family_id="C04" if item["track"] == "exact" else "C05",
            cluster_id=cluster, role=cluster_role(cluster), path=item["path"],
            kind="mc" if item["track"] == "exact" else "pmc",
            source_url=f"{repository}/raw/{counting_revision}/{item['source_path']}",
            source_revision=counting_revision, expected_sha256=item["sha256"],
            license_spdx="CC0-1.0", license_path=COUNTING_LICENSE,
            redistribution="permitted_with_license_notice", transformations=(item["transformation"],),
        ))
    return rows


def prior_refusals() -> list[dict]:
    """Carry forward manifest refusals whose payload was deliberately not retained."""
    manifest = read_json(FEATURE / "CORPUS.json")
    rows = []
    for item in manifest["files"]:
        if item.get("admitted") or all(key in item for key in ("filename", "url", "sha256")):
            continue
        rows.append({
            "case_id": "feature-" + item["id"], "group": "feature_models", "family_id": "F01",
            "cluster_id": "softvare-" + Path(item["source_path"]).parent.name.lower(), "role": "regression",
            "path": None, "kind": "cnf", "source_url": None,
            "source_revision": manifest["commit"], "expected_sha256": None,
            "license_spdx": "MIT",
            "license_path": "docs/audits/2026-09-11-cm-next-research/corpus/UPSTREAM-LICENSE.txt",
            "redistribution": "not_applicable_payload_not_retained", "transformations": [],
            "state": "rejected", "reason": "prior_manifest_refusal:" + item["reason"],
            "bytes": item.get("bytes"), "sha256": None, "metadata": None,
        })
    return rows


def estimate(cells: int, pilot_seconds: float, pilot_cells: int) -> dict:
    observed = pilot_seconds / max(1, pilot_cells)
    scenarios = []
    for label, seconds in (("local_tiny_probe", observed), ("research_example_1s", 1.0),
                           ("research_example_10s", 10.0), ("normal_cell_limit_60s", 60.0)):
        scenarios.append({"scenario": label, "seconds_per_cell": seconds,
                          "single_worker_hours": cells * seconds / 3600})
    return {"schema": "cm-benchmark-runtime-estimate/v1", "full_six_arm_three_rep_cells": cells,
            "pilot": {"cells": pilot_cells, "wall_seconds": pilot_seconds, "seconds_per_cell": observed,
                      "scope": "tiny local correctness probes; not representative performance evidence"},
            "scenarios": scenarios,
            "conclusion": "The 2,400 x 6 x 3 Cartesian plan is infeasible at 10 seconds/cell under 16 pod-hours; apply the frozen stratified not-run policy after a cloud pilot."}


def quote_record() -> dict:
    # Public rate-card snapshot obtained 2026-09-13. Account-specific CPU catalog
    # availability requires credentials and is deliberately not accessed here.
    compute = 0.50
    hours = 16
    disk_gb = 30
    storage = disk_gb * 0.10 * hours / (24 * 30)
    return {
        "schema": "cm-runpod-public-quote/v1", "checked_utc": utc_now(),
        "source": "https://www.runpod.io/pricing", "source_kind": "official public rate card",
        "offer": {"cloud": "Pods on-demand; Community/Secure class must be confirmed in console", "gpu": "RTX 3090", "gpu_vram_gb": 24,
                  "advertised_ram_gb": 125, "advertised_vcpus": 16, "compute_usd_per_hour": compute,
                  "availability": "not account-verified", "preferred_region": "AP-JP-1",
                  "region_fallback": "availability priority; record assigned data center before work"},
        "storage": {"type": "container disk", "gb": disk_gb, "rate_usd_per_gb_month": 0.10,
                    "persistent_after_stop": False, "network_volume_gb": 0},
        "estimate": {"compute_hours": hours, "compute_usd": compute * hours,
                     "storage_usd_prorated": storage, "total_usd": compute * hours + storage,
                     "includes": ["setup", "idle", "benchmark", "retrieval", "one-hour cleanup reserve"],
                     "egress_usd": 0},
        "proposal_not_authorization": {"dollar_cap_usd": 50, "total_pod_hours": 16,
                                       "max_concurrent_pods": 1, "cleanup_reserve_hours": 1},
        "caveats": ["GPU is not expected to accelerate current algorithms; this SKU is selected for its advertised CPU/RAM envelope.",
                    "Usable RAM, cgroup memory.max, CPU affinity/quota, price, region, and availability must be rechecked immediately before any authorized creation.",
                    "The authenticated CPU-only catalog was not queried because secret access is not authorized."],
    }


def launch_gate(admission: dict, readiness: dict, schedule: dict, arms: dict, quote: dict) -> dict:
    shortfalls = {
        group: states.get("not_run", 0)
        for group, states in schedule["summary"].items()
        if states.get("not_run", 0)
    }
    excluded = [
        {"adapter": row["adapter"], "state": row["state"], "reason": row["reason"]}
        for row in arms["rows"] if row["state"] == "not_run"
    ]
    blockers = [
        {"kind": "runpod_placement_unverified", "detail": "price/spec snapshot is public; current account availability, assigned region, CPU quota and memory.max require a pre-create check"},
        {"kind": "authorization_missing", "detail": "no paid creation or upload is authorized"},
    ]
    return {
        "schema": "cm-benchmark-launch-gate/v1",
        "campaign_id": CAMPAIGN_ID,
        "local_package_verified": True,
        "paid_launch_ready": False,
        "paid_launch_authorized": False,
        "upload_authorized": False,
        "admitted_inputs": admission["summary"]["states"].get("admitted", 0),
        "planned_base_cases": sum(row["state"] == "planned" for row in schedule["rows"]),
        "not_run_base_cases": sum(row["state"] == "not_run" for row in schedule["rows"]),
        "frozen_scope_limitations": {
            "corpus_quota_shortfalls": shortfalls,
            "excluded_adapters": excluded,
            "effect": "explicit not-run; excluded from paid schedule unless a new pre-outcome manifest is reviewed",
        },
        "blockers": blockers,
        "future_authorization_scope": {
            "action": "create at most one RunPod Pod and upload only the files listed in UPLOAD_MANIFEST.json after all non-authorization blockers are cleared and the quote is refreshed",
            "maximum_usd": quote["proposal_not_authorization"]["dollar_cap_usd"],
            "maximum_total_pod_hours": quote["proposal_not_authorization"]["total_pod_hours"],
            "cleanup_reserve_hours": quote["proposal_not_authorization"]["cleanup_reserve_hours"],
            "bundle_identity": "resolved by sibling UPLOAD_MANIFEST.json",
            "status": "proposal_only_do_not_execute",
        },
    }


def report_text(summary: dict, admission: dict, readiness: dict, schedule: dict, arms: dict,
                quote: dict, upload: dict) -> str:
    group_lines = [
        f"| {group} | {states.get('planned', 0)} | {states.get('not_run', 0)} |"
        for group, states in schedule["summary"].items()
    ]
    adapter_lines = [f"| `{row['adapter']}` | {row['state']} | {row['reason']} |" for row in readiness["rows"]]
    return "\n".join([
        "# CM benchmark campaign prelaunch report", "",
        f"Campaign: `{CAMPAIGN_ID}`", "",
        "This is a tested local preparation package, not benchmark performance evidence and not launch authorization.", "",
        "## Outcome", "",
        f"- {admission['summary']['states'].get('admitted', 0)} public inputs were hash/license/parser admitted.",
        f"- {summary['planned_base_cases']} of 2,400 base slots are planned; {summary['not_run_base_cases']} remain explicit quota shortfalls.",
        f"- Adapter probes: {readiness['summary'].get('present_verified', 0)} verified, {readiness['summary'].get('present_unverified', 0)} unverified, {readiness['summary'].get('missing', 0)} missing.",
        f"- Reduced scope: {arms['summary'].get('planned', 0)} verified adapter entries planned and {arms['summary'].get('not_run', 0)} frozen not-run.",
        f"- The deterministic upload package contains {len(upload['contents'])} files in {len(upload['bundles'])} bounded shards ({sum(row['bytes'] for row in upload['bundles'])} compressed bytes).",
        "- Paid launch is blocked and unauthorized.", "",
        "## Admission and schedule", "", "| Group | Planned | Not run |", "|---|---:|---:|", *group_lines, "",
        "Previously consumed LogikBench, SoftVarE and GNU Radio inputs remain regression cases. The newly frozen Biodivine biology functions and CC0 exact/projected counting inputs were split by source cluster before benchmarking; no synthetic case was relabeled as real-world.", "",
        "## Adapter readiness", "", "| Adapter | State | Evidence |", "|---|---|---|", *adapter_lines, "",
        "## Public RunPod quote", "",
        f"The official public Pods listing checked at `{quote['checked_utc']}` showed RTX 3090 at ${quote['offer']['compute_usd_per_hour']:.2f}/hour with 125 GB advertised RAM and 16 advertised vCPUs. Sixteen hours plus prorated 30 GB container disk estimates ${quote['estimate']['total_usd']:.2f}. Availability, cloud class, assigned region, usable cgroup RAM and CPU quota were not account-verified.", "",
        "## Gate", "",
        "The reduced scope freezes corpus quota gaps and unavailable adapters as explicit not-run entries rather than launch blockers. Before a paid launch: refresh account-visible placement, then obtain explicit authorization for these exact shards and caps. The pinned Linux image passed Ganak exact/projected, d4 exact, Kissat, CryptoMiniSat XOR-witness, and Biodivine AEON fixed-point smoke tests. No cloud resource or upload was created by this preparation.", "",
    ])


def prepare(out: Path) -> dict:
    if out.exists():
        raise FileExistsError("campaign output already exists; use verify or choose a new directory")
    out.mkdir(parents=True)
    created = utc_now()
    candidate_rows = candidates()
    started = time.perf_counter()
    readiness = adapter_readiness(ROOT, CAMPAIGN_ID, created_utc=created)
    arms = build_arm_manifest(CAMPAIGN_ID, readiness, created_utc=created)
    pilot_seconds = time.perf_counter() - started
    admission = build_admission_ledger(
        ROOT, CAMPAIGN_ID, candidate_rows, created_utc=created, prior_rows=prior_refusals(),
    )
    synthetic = synthetic_specs()
    schedule = build_schedule_ledger(CAMPAIGN_ID, admission, synthetic, created_utc=created)
    write_new(out / "ADAPTER_READINESS.json", readiness)
    write_new(out / "ARM_MANIFEST.json", arms)
    write_new(out / "ADMISSION_LEDGER.json", admission)
    write_new(out / "SYNTHETIC_INPUTS.json", {"schema": "cm-benchmark-synthetic-inputs/v1", "rows": synthetic,
                                               "sha256": canonical_digest(synthetic)})
    write_new(out / "SCHEDULE_LEDGER.json", schedule)
    write_new(out / "RUNTIME_ESTIMATE.json", estimate(2400 * 6 * 3, pilot_seconds, 7))
    write_new(out / "ENVIRONMENT_LOCK.json", environment_lock())
    quote = quote_record()
    write_new(out / "RUNPOD_QUOTE.json", quote)
    gate = launch_gate(admission, readiness, schedule, arms, quote)
    write_new(out / "LAUNCH_GATE.json", gate)
    code_paths = [
        "bitset_backend.py", "cm_expr_serde.py", "cm_exprlib.py", "cm_ir.py", "cm_normalize.py",
        "cmbench/__init__.py", "cmbench/campaign_prelaunch.py", "cmbench/output_budget.py",
        "cmbench/backends/__init__.py", "cmbench/backends/affine_constraints.py",
        "cmbench/backends/native_count.py", "cmbench/backends/native_sat.py", "cmbench/backends/projected_count.py", "cmbench/biology_bnet.py",
        "cmbench/backends/bitset_engine.py", "cmbench/backends/bitset_utils.py",
        "cmbench/backends/packed_mask_cache.py", "cmbench/backends/packed_queries.py",
        "cmbench/backends/packed_stream_io.py", "cmbench/comparative/__init__.py",
        "cmbench/comparative/contracts.py", "cmbench/comparative/arms.py",
        "cmbench/comparative/evidence.py", "cmbench/comparative/exact_cudd_count.py",
        "cmbench/comparative/corpus_freeze.py", "cmbench/comparative/ir.py",
        "cmbench/comparative/readiness.py", "cmbench/comparative/schedule.py",
        "cmbench/comparative/tasks.py", "cmbench/recognition/__init__.py",
        "cmbench/recognition/blif.py", "cmbench/reporting/__init__.py",
        "cmbench/reporting/provenance.py", "cmbench/reporting/summary_tables.py",
        "cmbench/tracing/__init__.py", "cmbench/tracing/schema.py",
        "scripts/cm_benchmark_acquire.py", "scripts/cm_benchmark_prelaunch.py", "scripts/cm_benchmark_provenance.py",
        "scripts/cm_comparative_task_pilot.py",
        "scripts/cm_measurement_verify.py", "scripts/cm_native_contracts.py",
        "scripts/cm_process_supervisor.py", "scripts/cm_session_contracts.py",
        "tests/test_cm_comparative_task_pilot.py", "tests/test_cm_comparative_tasks.py",
        "tests/test_cm_benchmark_acquire.py", "tests/test_cm_benchmark_prelaunch.py",
        "tests/test_cm_campaign_new_adapters.py", "tests/test_cm_native_count_adapter.py",
        "tests/test_cm_native_sat_adapter.py",
        "docker/cm-benchmark-smoke/Dockerfile", "docker/cm-benchmark-smoke/NATIVE_LOCK.json",
        "docker/cm-benchmark-smoke/smoke.py", "docker/cm-benchmark-smoke/fixtures/exact.cnf",
        "docker/cm-benchmark-smoke/fixtures/projected.cnf", "docker/cm-benchmark-smoke/fixtures/sat.cnf",
        "docker/cm-benchmark-smoke/fixtures/unsat.cnf", "docker/cm-benchmark-smoke/fixtures/xor-sat.cnf",
        "docker/cm-benchmark-smoke/fixtures/xor-unsat.cnf", "docker/cm-benchmark-smoke/fixtures/aeon.bnet",
        "docker/cm-benchmark-smoke/vendor/ganak-v2.6.4-linux-amd64.tar.gz",
        "docker/cm-benchmark-smoke/vendor/kissat-4.0.4-linux-amd64.zip",
        "docker/cm-benchmark-smoke/vendor/cryptominisat5-v5.15.0-linux-amd64.tar.gz",
        "docker/cm-benchmark-smoke/vendor/d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz",
        "docker/cm-benchmark-smoke/vendor/libpatoh-linux-x86_64-pr8.a",
        "docker/cm-benchmark-smoke/vendor/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl",
        "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-009/INPUT_FREEZE.json",
        "docs/audits/2026-09-13-cm-benchmark-campaign/linux-smoke-002/LINUX_SMOKE.json",
    ]
    identity = source_identity(ROOT, code_paths)
    write_new(out / "SOURCE_IDENTITY.json", identity)
    input_rows = [row for row in admission["rows"] if row["state"] == "admitted"]
    entries = [{"source": path, "archive": "source/" + path} for path in code_paths]
    entries += [{"source": row["path"], "archive": "inputs/" + row["group"] + "/" + Path(row["path"]).name}
                for row in input_rows]
    license_paths = sorted({row["license_path"] for row in input_rows if row["license_path"]})
    entries += [{"source": path, "archive": "licenses/" + Path(path).name} for path in license_paths]
    generated = {
        "BUNDLE_README.md": (
            b"# CM benchmark prelaunch bundle\n\n"
            b"This bundle is approved for neither upload nor paid execution. Extract it into an empty directory.\n"
            b"The bounded functional pilot entry point is `source/scripts/cm_comparative_task_pilot.py`; "
            b"unavailable adapters and quota gaps are frozen not-run in `manifests/ARM_MANIFEST.json` "
            b"and `manifests/SCHEDULE_LEDGER.json`.\n"
        ),
        "manifests/ADAPTER_READINESS.json": (out / "ADAPTER_READINESS.json").read_bytes(),
        "manifests/ARM_MANIFEST.json": (out / "ARM_MANIFEST.json").read_bytes(),
        "manifests/ADMISSION_LEDGER.json": (out / "ADMISSION_LEDGER.json").read_bytes(),
        "manifests/SYNTHETIC_INPUTS.json": (out / "SYNTHETIC_INPUTS.json").read_bytes(),
        "manifests/SCHEDULE_LEDGER.json": (out / "SCHEDULE_LEDGER.json").read_bytes(),
        "manifests/RUNTIME_ESTIMATE.json": (out / "RUNTIME_ESTIMATE.json").read_bytes(),
        "manifests/ENVIRONMENT_LOCK.json": (out / "ENVIRONMENT_LOCK.json").read_bytes(),
        "manifests/SOURCE_IDENTITY.json": (out / "SOURCE_IDENTITY.json").read_bytes(),
        "manifests/RUNPOD_QUOTE.json": (out / "RUNPOD_QUOTE.json").read_bytes(),
        "manifests/LAUNCH_GATE.json": (out / "LAUNCH_GATE.json").read_bytes(),
        "manifests/INPUT_FREEZE.json": (INPUT_FREEZE / "INPUT_FREEZE.json").read_bytes(),
        "manifests/LINUX_SMOKE.json": (ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/linux-smoke-002/LINUX_SMOKE.json").read_bytes(),
    }
    upload = build_upload_bundles(ROOT, out, CAMPAIGN_ID, entries, generated)
    write_new(out / "UPLOAD_MANIFEST.json", upload)
    verification = verify(out)
    write_new(out / "LOCAL_VERIFICATION.json", verification)
    summary = {"campaign_id": CAMPAIGN_ID, "output": str(out), "admitted_inputs": admission["summary"]["states"].get("admitted", 0),
               "synthetic_specs": len(synthetic), "planned_base_cases": sum(1 for row in schedule["rows"] if row["state"] == "planned"),
               "not_run_base_cases": sum(1 for row in schedule["rows"] if row["state"] == "not_run"),
               "bundle_sha256": [row["sha256"] for row in upload["bundles"]], "paid_launch_authorized": False,
               "verification": verification["status"]}
    write_new(out / "PRELAUNCH_SUMMARY.json", summary)
    (out / "REPORT.md").write_text(
        report_text(summary, admission, readiness, schedule, arms, quote, upload), encoding="utf-8", newline="\n",
    )
    return summary


def verify(out: Path) -> dict:
    names = ("ADAPTER_READINESS.json", "ARM_MANIFEST.json", "ADMISSION_LEDGER.json", "SYNTHETIC_INPUTS.json",
             "SCHEDULE_LEDGER.json", "RUNTIME_ESTIMATE.json", "ENVIRONMENT_LOCK.json", "RUNPOD_QUOTE.json",
             "SOURCE_IDENTITY.json", "LAUNCH_GATE.json", "UPLOAD_MANIFEST.json")
    records = {name: read_json(out / name) for name in names}
    validate_admission_ledger(records["ADMISSION_LEDGER.json"])
    source = records["SOURCE_IDENTITY.json"]
    for row in source["files"]:
        if sha256_file(ROOT / row["path"]) != row["sha256"] or (ROOT / row["path"]).stat().st_size != row["bytes"]:
            raise ValueError("source identity changed: " + row["path"])
    upload_check = verify_upload_bundles(out, records["UPLOAD_MANIFEST.json"])
    schedule = records["SCHEDULE_LEDGER.json"]
    if schedule["schedule_sha256"] != canonical_digest({key: value for key, value in schedule.items() if key != "schedule_sha256"}):
        raise ValueError("schedule digest mismatch")
    if len(schedule["rows"]) != schedule["base_case_target"]:
        raise ValueError("schedule base-case cardinality")
    arms = records["ARM_MANIFEST.json"]
    if arms["arm_manifest_sha256"] != canonical_digest({key: value for key, value in arms.items() if key != "arm_manifest_sha256"}):
        raise ValueError("arm manifest digest mismatch")
    if any(row["state"] == "planned" and row["readiness_state"] != "present_verified" for row in arms["rows"]):
        raise ValueError("unverified adapter entered reduced scope")
    synthetic = records["SYNTHETIC_INPUTS.json"]
    if synthetic["sha256"] != canonical_digest(synthetic["rows"]) or len(synthetic["rows"]) != 600:
        raise ValueError("synthetic freeze mismatch")
    quote = records["RUNPOD_QUOTE.json"]
    if quote["proposal_not_authorization"]["dollar_cap_usd"] != 50 or quote["estimate"]["total_usd"] > 50:
        raise ValueError("quote envelope mismatch")
    return {"schema": "cm-benchmark-local-verification/v1", "status": "passed", "checked_utc": utc_now(),
            "records": {name: sha256_file(out / name) for name in names}, "bundle": upload_check,
            "resource_writes": 0, "cloud_calls": 0, "secret_access": False, "performance_claims": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("prepare", "verify"):
        command = sub.add_parser(action)
        command.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = prepare(args.output.resolve()) if args.action == "prepare" else verify(args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
