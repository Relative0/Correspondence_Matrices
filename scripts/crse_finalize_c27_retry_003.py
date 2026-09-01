"""Record the independently verified C27 retry-003 result without changing its policy."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RESULTS = DOCS / "learning_milestone_c27_support_aware_fresh_confirmation_results.json"
REGISTER = DOCS / "experiment_register.json"
FINAL = DOCS / "c27_linux_confirmation/RUNPOD_C27_RETRY_003_FINAL_VERIFICATION_20260901.json"
PROXY_RECONCILIATION = (
    DOCS / "c27_linux_confirmation/RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")


SCOPE = (
    "C27 froze an n<=4 truth-screened / n>=5 packed-screened rule before a new "
    "48-case unused-generator corpus. Retry-003 ran the unchanged 63-file package on "
    "a Secure cpu5c RunPod backed by an AMD EPYC 4564P. Its independent verifier and "
    "a byte-identical post-retrieval replay checked 720 batches, 7,560 timed queries, "
    "24 memory batches, and 2,520 semantic contexts with zero mismatches. The "
    "second-machine gate passed first at 8 queries (1.035x aggregate, 0.961x minimum "
    "width). The pod was deleted after 79.86 seconds at an estimated $0.001553. "
    "Production remains disabled because timing margins are narrow and machine-specific."
)

NEXT = (
    "Use the frozen Windows, three same-host Docker, and verified RunPod C27 timing "
    "surfaces to build a no-refit cross-machine profitability adjudicator with paired "
    "uncertainty bounds. Retain exact fallback and require a conservative q>=8 lower "
    "bound before any shadow-only promotion."
)


def main() -> None:
    final = load(FINAL)
    if (
        final.get("status") != "pass"
        or final.get("scientific_confirmation_complete") is not True
        or final.get("support_aware_confirmation_gate") is not True
        or final.get("support_aware_break_even_query_count") != 8
        or final.get("semantic_or_artifact_mismatches") != 0
        or final.get("cpu_flavor") != "cpu5c"
    ):
        raise RuntimeError("C27 retry-003 final verification is not admissible")

    results = load(RESULTS)
    prior_cost = load(PROXY_RECONCILIATION)["estimated_compute_cost_usd"]
    results.update({
        "status": "fresh_local_and_second_machine_linux_confirmation_complete",
        "interpretation": (
            "The transparent support rule remained exact on the fresh C27 corpus and "
            "now has an unchanged physical second-machine Linux confirmation. The "
            "RunPod gate passed first at eight queries with 1.035x aggregate and 0.961x "
            "minimum-width speedup over direct screened execution; q16 and q32 also "
            "passed. An on-pod independent verifier and byte-identical post-retrieval "
            "replay found zero mismatches across all 7,560 timed queries. Together with "
            "three same-host Docker passes, this supports a portable q>=8 shadow rule, "
            "but the small timing margins remain machine-specific and production "
            "promotion stays false."
        ),
    })
    results["retry_003"] = {
        "status": "verified_second_machine_scientific_confirmation_complete",
        "authorization_granted": True,
        "authorization": (
            "docs/recognition/c27_linux_confirmation/"
            "RUNPOD_C27_RETRY_003_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json"
        ),
        "authorization_request": (
            "docs/recognition/c27_linux_confirmation/"
            "RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json"
        ),
        "readiness": (
            "docs/recognition/c27_linux_confirmation/"
            "RUNPOD_C27_RETRY_003_READINESS_20260901.json"
        ),
        "final_verification": (
            "docs/recognition/c27_linux_confirmation/"
            "RUNPOD_C27_RETRY_003_FINAL_VERIFICATION_20260901.json"
        ),
        "create_requests": 1,
        "pod_created": True,
        "pod_id": final["pod_id"],
        "required_cpu_flavor": "cpu5c",
        "cpu_model": final["cpu_model"],
        "quoted_rate_usd_per_hour": 0.07,
        "source_files_uploaded": 63,
        "owned_pod_absent_verified": True,
        "estimated_compute_cost_usd": final["estimated_compute_cost_usd"],
        "elapsed_since_create_s": final["elapsed_since_create_s"],
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
        "support_aware_confirmation_gate": True,
        "break_even_query_count": 8,
        "production_promotion": False,
    }
    results["second_machine_linux"] = {
        "status": "verified",
        "physical_second_machine": True,
        "runtime": {
            "system": "Linux",
            "machine": "x86_64",
            "python": "3.13.15",
            "numpy": "2.3.2",
            "dd": "0.6.0-vendored",
            "cpu_flavor": final["cpu_flavor"],
            "cpu_model": final["cpu_model"],
        },
        "verification": results["retry_003"]["final_verification"],
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
        "support_aware_confirmation_gate": True,
        "break_even_query_count": 8,
        "q8_aggregate_speedup_over_direct_screened": final["summary"]["by_query_count"]["8"][
            "methods"]["support_aware_c27_advice_on"]["aggregate_speedup_over_direct_screened"],
        "q8_minimum_width_speedup_over_direct_screened": final["summary"]["by_query_count"]["8"][
            "methods"]["support_aware_c27_advice_on"]["minimum_width_speedup_over_direct_screened"],
        "production_promotion": False,
    }
    linux = results["linux_replication"]
    linux.update({
        "status": "retry_003_verified_second_machine_scientific_result",
        "scientific_replication_complete": True,
        "second_machine_replication": True,
        "create_requests_total": 3,
        "pods_created_total": 2,
        "source_files_uploaded_total": 63,
        "cost_usd": prior_cost + final["estimated_compute_cost_usd"],
        "retry_003_create_requests": 1,
        "retry_003_pod_created": True,
        "retry_003_cpu_flavor": "cpu5c",
        "retry_003_final_verification": results["retry_003"]["final_verification"],
        "retry_003_support_aware_confirmation_gate": True,
        "retry_003_break_even_query_count": 8,
        "unrelated_pod_modified": False,
    })
    write(RESULTS, results)

    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("research track/application inventory changed before C27 finalization")
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            c27_results = [item for item in row.get("results", [])
                           if item.get("machine_summary") == RESULTS.name]
            for item in c27_results:
                item["scope"] = SCOPE
            if c27_results and "status_reason" in row:
                row["status_reason"] = SCOPE
            if c27_results and "next_experiment" in row:
                row["next_experiment"] = NEXT
    register["milestones"]["F"] = (
        "C27 independently verifies a frozen support-aware exact GF(2) rule on a fresh "
        "corpus and on a physical second Linux machine; the unchanged cpu5c run passes "
        "the timing gate at q8, q16, and q32 with zero mismatches, while narrow "
        "machine-specific margins keep production disabled"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C27 finalization changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "updated",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c27_result_references": sum(
            item.get("machine_summary") == RESULTS.name
            for row in (*register["tracks"], *register["applications"])
            for item in row.get("results", [])
        ),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
