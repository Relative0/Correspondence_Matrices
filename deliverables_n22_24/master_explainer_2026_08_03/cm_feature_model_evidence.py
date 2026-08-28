"""Read the explicitly audited feature-model runs for the static website.

No producer imports, experiment execution, latest-run discovery, or evidence
writes. Changed evidence fails closed rather than silently inheriting an audit.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


BENCHMARK_DIR = "use_case_benchmarks_2026-08-27"
RUNS = {
    "pilot": ("configuration-fm-history-pilot-full40-2026-08-27", "3e4d896f47ceccc976b1119c21d6a6de27e4e49c65469c98e61e1ee90bf44529"),
    "core": ("configuration-fm-history-shootout-cudd-full40-2026-08-27", "b8fcc64188274d522339e429d29fa9214911750e93f4d25fe3b67c2b5ec2b6f0"),
    "supplement": ("configuration-fm-history-shootout-supplement-2026-08-27", "2d920097d6670bfbefc655d78c8acac5a2c3f3465fa00a8655d9537605c91c8e"),
    "delta": ("configuration-fm-version-delta-full21-2026-08-27", "d6c3426ad5ad39632d8fb215486787d60498f0000b7917455a66480d0460fab4"),
    "artifact": ("configuration-fm-deep-artifact-audit-2026-08-27", "2d3c67b6b2de2bbb2a5c4072bf223fe16a2c13fabfa93c9de1bb38b9e3dd5f0f"),
    "source": ("configuration-fm-deep-source-audit-2026-08-27", "0727dec04eecd6669b90830285ab791eadde8340dce676e4626d5dad0ac10928"),
    "measurement": ("configuration-fm-measurement-audit-2026-08-27", "9e5068d0817e43c6ab57e8bec7a233c183bce91195dbbdb692b6c9a2031cffbf"),
    "regression": ("configuration-fm-frozen-audit-regression-2026-08-27", "cf9c94345ff6efda25b6c9c209c3daa721ca7fb31fe04b9bbed6c5bc1045b19e"),
}


def verify_run(run: Path, expected_manifest_sha256: str) -> int:
    """Verify a pinned manifest and every listed file, including path safety."""
    run = run.resolve()
    manifest = (run / "CHECKSUMS.sha256").read_bytes()
    if hashlib.sha256(manifest).hexdigest() != expected_manifest_sha256:
        raise ValueError(f"Audit identity changed: {run.name}")
    seen = set()
    for line in manifest.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError(f"Malformed checksum entry: {run.name}")
        digest, relative = match.groups()
        path = (run / relative).resolve()
        if not path.is_relative_to(run) or path in seen:
            raise ValueError(f"Unsafe or repeated evidence path: {relative}")
        seen.add(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Audit artifact changed or missing: {run.name}/{relative}")
    if not seen:
        raise ValueError(f"Empty checksum manifest: {run.name}")
    return len(seen)


def build_feature_model_evidence(site: Path) -> tuple[dict, dict]:
    base = site / BENCHMARK_DIR
    run_paths = {key: base / "runs" / name for key, (name, _) in RUNS.items()}
    identities = []
    expected_files = {}
    for key, (name, digest) in RUNS.items():
        count = verify_run(run_paths[key], digest)
        manifest = (run_paths[key] / "CHECKSUMS.sha256").read_bytes()
        if hashlib.sha256(manifest).hexdigest() != digest:
            raise ValueError(f"Audit identity changed during loading: {name}")
        expected_files[key] = {relative: sha for sha, relative in (
            line.split("  ", 1) for line in manifest.decode("ascii").splitlines()
        )}
        identities.append({"role": key, "id": name, "checksum_sha256": digest,
                           "files_verified": count,
                           "checksum_href": f"{BENCHMARK_DIR}/runs/{name}/CHECKSUMS.sha256"})

    def read_bytes(key: str, filename: str) -> bytes:
        payload = (run_paths[key] / filename).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_files[key].get(filename):
            raise ValueError(f"Audit artifact changed during loading: {key}/{filename}")
        return payload

    def read(key: str, filename: str):
        return json.loads(read_bytes(key, filename).decode("utf-8"))

    artifact = read("artifact", "summary.json")
    source = read("source", "summary.json")
    measurement = read("measurement", "summary.json")
    regression = read("regression", "summary.json")
    core = read("core", "summary.json")
    delta = read("delta", "summary.json")
    clusters = read("artifact", "clustered-statistics.json")
    sizes = read("measurement", "measurement-summary.json")
    gaps = read("measurement", "measurement-gaps.json")
    if any(item["status"] != "passed" for item in (artifact, source, regression)):
        raise ValueError("A required feature-model correctness audit did not pass")
    if measurement["status"] != "gaps_documented" or any(
        item["performance_claims_certified"] for item in (artifact, source)
    ):
        raise ValueError("The selected audit's performance disposition changed")
    if measurement["gap_count"] != len(gaps) or measurement["high_priority_gaps"] != sum(
        gap["severity"] == "high" for gap in gaps
    ):
        raise ValueError("Gap register and summary disagree")
    for key in ("artifact", "source", "measurement", "regression"):
        change = read(key, "concurrent-change-check.json")
        if change["source_changes"] or not change["saved_runs_unchanged"]:
            raise ValueError(f"Concurrent-change qualification needs review: {key}")

    junit = ET.fromstring(read_bytes("regression", "junit.xml"))
    suites = junit.findall("testsuite") if junit.tag == "testsuites" else [junit]
    if any(int(s.attrib.get(field, 0)) for s in suites for field in ("failures", "errors", "skipped")):
        raise ValueError("Frozen regression has failed, errored or skipped tests")
    test_count = len(junit.findall(".//testcase"))

    numbers = {}

    def number(name: str, value, fmt: str, key: str, filename: str, field: str):
        path = run_paths[key] / filename
        numbers[f"fm.{name}"] = {"value": value, "fmt": fmt,
                               "prov": f"{path.relative_to(site.parent.parent).as_posix()} :: {field}",
                               "note": "Saved feature-model cohort only; performance remains provisional."}

    for name, key, field in (
        ("cases", "artifact", "endpoint_cases"),
        ("assignments", "artifact", "assignments_per_representation"),
        ("models", "source", "official_payloads_rehashed_and_reparsed"),
        ("delta_cases", "source", "delta_case_pairs_reconstructed_from_source"),
        ("admitted", "source", "admitted_transition_witnesses_regenerated_and_saved"),
        ("refused", "source", "refusal_independently_confirmed_by_MiniSat22"),
        ("gaps", "measurement", "gap_count"),
        ("high_gaps", "measurement", "high_priority_gaps"),
        ("partial_rows", "core", "partial_row_count"),
        ("transitions", "delta", "transition_count"),
    ):
        number(name, read(key, "summary.json")[field], "int", key, "summary.json", field)
    number("tests", test_count, "int", "regression", "junit.xml", "count(.//testcase), zero failures/errors/skips")
    number("histories", clusters["16"]["endpoint_cm_over_cnf"]["history_count"], "int",
           "artifact", "clustered-statistics.json", "16.endpoint_cm_over_cnf.history_count")
    number("unchanged", sum(row["identical_relation_cases"] for row in delta["by_k"].values()),
           "int", "delta", "summary.json", "sum(by_k.*.identical_relation_cases)")
    number("valid_points", sizes["16"]["valid_point_queries"], "int", "measurement",
           "measurement-summary.json", "16.valid_point_queries")
    number("points", sizes["16"]["point_queries"], "int", "measurement",
           "measurement-summary.json", "16.point_queries")
    number("valid_pct", 100 * sizes["16"]["valid_point_queries"] / sizes["16"]["point_queries"],
           "pct2", "measurement", "measurement-summary.json", "100 * 16.valid_point_queries / 16.point_queries")

    rows = []
    for k in sorted(map(int, clusters)):
        cluster, size = clusters[str(k)], sizes[str(k)]
        rows.append({"k": k, "cases": size["n"], "statistics": cluster, "measurement": size})
    for label, field in (("cnf", "endpoint_cm_over_cnf"), ("cudd", "endpoint_cm_over_cudd_extraction")):
        stats = clusters["16"][field]
        for suffix, value in (("ratio", stats["equal_history_geomean"]),
                              ("lo", stats["cluster_bootstrap_ci95"][0]),
                              ("hi", stats["cluster_bootstrap_ci95"][1])):
            number(f"{label}.{suffix}", value, "ratio3", "artifact", "clustered-statistics.json", f"16.{field}")

    links = []

    def link(label: str, relative: str, note: str = ""):
        if not (site / relative).is_file():
            raise ValueError(f"Missing website evidence link: {relative}")
        links.append({"label": label, "href": relative, "note": note})

    def run_link(key: str, filename: str, label: str, note: str = ""):
        link(label, f"{BENCHMARK_DIR}/runs/{RUNS[key][0]}/{filename}", note)

    link("Full independence and measurement audit", f"{BENCHMARK_DIR}/CONFIGURATION-FM-INDEPENDENCE-AUDIT-2026-08-27.md")
    link("Audit code and reproduction instructions", f"{BENCHMARK_DIR}/independence_audit_2026_08_27/README.md")
    link("Frozen feature-model comparison protocol", f"{BENCHMARK_DIR}/CONFIGURATION-FM-HISTORY-SHOOTOUT-PROTOCOL.md",
         "Planned protocol; the gap register documents deviations in the actual run.")
    for key, filename, label in (
        ("artifact", "summary.json", "Independent artifact-replay summary"),
        ("artifact", "artifact-replay.csv", "Artifact replay and actual graph counts"),
        ("artifact", "clustered-statistics.json", "Equal-history statistics and sensitivity"),
        ("source", "summary.json", "Independent source-reconstruction summary"),
        ("source", "source-inputs.csv", "Official input identities and hashes"),
        ("source", "refusal-certificate.json", "Linux refusal: two-solver corroboration, not a formal proof"),
        ("source", "retrospective-joint-witnesses.jsonl", "Regenerated joint witnesses"),
        ("measurement", "measurement-gaps.json", "All measurement gaps and source locations"),
        ("measurement", "artifact-contracts.csv", "Per-case serialization accounting"),
        ("regression", "junit.xml", "Frozen scoped regression results"),
        ("core", "corpus.jsonl", "Reusable bounded CNF corpus"),
        ("core", "cases.csv", "Original endpoint raw measurements"),
        ("core", "partial-contexts.csv", "Original partial-context measurements"),
        ("supplement", "supplement.csv", "Original group-sifting and d4 measurements"),
        ("supplement", "native-rss.csv", "Original whole-process sampled RSS"),
        ("delta", "version-delta.csv", "Original bounded version-delta measurements"),
        ("delta", "admissions.csv", "All transition admissions and refusals"),
    ):
        run_link(key, filename, label)
    for gap in gaps:
        gap["source_href"] = (
            f"{BENCHMARK_DIR}/runs/{RUNS['measurement'][0]}/source_snapshot/"
            f"deliverables_n22_24/master_explainer_2026_08_03/{BENCHMARK_DIR}/{gap['observed_source']}"
        )
        if not (site / gap["source_href"]).is_file():
            raise ValueError("Missing observed audit source")

    return ({
        "schema": "cm-feature-model-website-evidence/v1",
        "audit_date": "2026-08-27", "website_update_date": "2026-08-28",
        "correctness_status": "passed_for_saved_bounded_relations",
        "performance_status": "provisional_measurement_gaps_open",
        "independence": "Separate implementations, not external third-party certification",
        "automatic_latest_run_selection": False,
        "histories": sorted(clusters["16"]["endpoint_cm_over_cnf"]["per_history"]),
        "runs": identities, "rows": rows, "gaps": gaps, "links": links,
        "forbidden_rankings": ["cold_d4_over_warm_popcount", "asymmetric_version_delta_warm_kernel", "raw_bytes_as_intrinsic_compactness"],
        "source_qualification": {
            "historical_joint_witnesses_missing": source["historical_joint_witnesses_were_missing"],
            "original_pysat": source["historical_pysat_version"], "audit_pysat": source["pysat_version"],
            "historical_dirty_source_reconstructed": artifact["historical_source_reconstruction_claimed"],
            "formal_unsat_proof": False, "actual_sifted_graphs_independently_replayed": False,
        },
        "primary_sources": measurement["external_primary_sources"],
        "historical_correctness": core["correctness"],
        "provenance": [
            f"{(run_paths[key] / filename).relative_to(site.parent.parent).as_posix()} :: {fields}"
            for key, filename, fields in (
                ("artifact", "summary.json", "replay coverage and independence flags"),
                ("artifact", "clustered-statistics.json", "per-width ratios, intervals, density and delta coverage"),
                ("source", "summary.json", "source reconstruction, refusal and runtime qualifications"),
                ("measurement", "summary.json", "gap counts and ordering qualifications"),
                ("measurement", "measurement-summary.json", "per-width encodings and valid point-query mix"),
                ("measurement", "measurement-gaps.json", "all findings and observed-source identities"),
                ("regression", "junit.xml", "testcase counts and outcomes"),
            )
        ],
    }, numbers)
