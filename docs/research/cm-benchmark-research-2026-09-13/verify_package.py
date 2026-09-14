"""Read-only validation of this research package; no benchmark or network calls."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import median


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read_json(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    catalog = read_json("CATALOG.json")
    sources = read_json("SOURCES.json")
    plan = read_json("CAMPAIGN_PLAN.json")
    audit = read_json("HISTORICAL_AUDIT.json")
    validation = read_json("VALIDATION.json")
    tests = catalog["tests"]
    ids = [test["id"] for test in tests]
    source_ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids)) == 80
    assert len(source_ids) == len(set(source_ids)) == 42
    assert len({source["url"] for source in sources}) == 42
    assert all(source["url"].startswith("https://") for source in sources)
    assert all(not source["dataset_downloaded_by_this_package"] for source in sources)
    assert all(source["frozen_revision"] is None for source in sources)
    for test in tests:
        assert set(test["sources"]) <= set(source_ids)
        assert set(test["tasks"]) <= catalog["tasks"].keys()
        assert test["scale_profile"] in catalog["scale_profiles"]
        assert test["status"] == "recommended_not_executed"
        assert test["performance_claim"] is None and test["frozen_input_count"] == 0
    assert set(plan["first_pool_ids"]) <= set(ids)
    assert len(plan["first_pool_ids"]) == len(set(plan["first_pool_ids"]))
    assert sum(plan["allocations"].values()) == plan["core_case_count_target"] == 2400
    assert sum(plan["phased_pod_hours"].values()) == plan["proposed_pod_hour_cap"] == 16
    assert plan["approved_budget_usd"] is None
    assert not plan["approved_pod_ids"] and not plan["cloud_execution_started"]
    assert plan["status"] == "research_proposal_not_launch_authorization"
    assert plan["default_limits"]["frontier_output_bytes"] == (1 << 32) // 8
    assert validation["test_families"] == len(tests)
    assert validation["groups"] == dict(Counter(test["group"] for test in tests))

    raw = ROOT / audit["raw_file"]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == audit["raw_sha256"]
    with raw.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 20
    for group in audit["groups"]:
        paired = [row for row in rows if int(row["n_vars"]) == group["n_vars"]]
        ratios = [float(row["sympy_time_s"]) / float(row["cm_time_s"]) for row in paired]
        assert group["pairs"] == len(paired) == 5
        assert math.isclose(median(ratios), group["median_of_paired_recorded_sympy_over_cm"], rel_tol=1e-14)
        assert min(ratios) == group["minimum"] and max(ratios) == group["maximum"]
        assert all(row["cm_ok"] == row["sympy_ok"] == "True" for row in paired)
    assert validation["historical_pairs"] == sum(group["pairs"] for group in audit["groups"])

    # Paths in the evidence snapshot may change later as other tasks edit the repository.
    # Surface that explicitly instead of silently regenerating the historical evidence.
    changed_evidence = []
    for item in audit["inspected_files"]:
        path = ROOT / item["path"]
        assert path.is_file(), path
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            changed_evidence.append(item["path"])

    required = ["README.md", "REPORT.md", "CATALOG.md", "SOURCES.md", "HISTORICAL_AUDIT.md", "RUNPOD_MEGA_PROMPT.md"]
    local_links = 0
    headings = 0
    for name in required:
        path = HERE / name
        body = path.read_text(encoding="utf-8")
        assert body.strip(), path
        assert "\uFFFD" not in body, path
        assert "\u2295" not in body and "\\oplus" not in body, path
        assert body.count("```") % 2 == 0, path
        headings += sum(line.startswith("#") for line in body.splitlines())
        for link in re.findall(r"\]\(([^)]+)\)", body):
            if link.startswith("https://"):
                continue
            target = link.strip("<>")
            target = re.sub(r":\d+$", "", target)
            assert re.match(r"^[A-Za-z]:/", target), (name, link)
            assert Path(target).is_file(), (name, link)
            local_links += 1
    report = (HERE / "REPORT.md").read_text(encoding="utf-8")
    prompt = (HERE / "RUNPOD_MEGA_PROMPT.md").read_text(encoding="utf-8")
    assert "43,200" in report and "720" in report
    assert 2400 * 6 * 3 == 43200 and 43200 * 60 / 3600 == 720
    assert "512 MiB" in report and "128 GiB" in report
    assert (1 << 32) * 32 == 128 * (1 << 30)
    assert "Current approved budget" in prompt and "**none**" in prompt

    print(json.dumps({
        "status": "pass",
        "families": len(tests),
        "primary_sources": len(sources),
        "validated_local_links": local_links,
        "markdown_documents": len(required),
        "headings": headings,
        "historical_pairs_recomputed": len(rows),
        "evidence_files_changed_since_snapshot": changed_evidence,
        "report_words": len(report.split()),
        "execution_prompt_words": len(prompt.split()),
        "new_performance_measurements": 0,
        "cloud_operations": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
