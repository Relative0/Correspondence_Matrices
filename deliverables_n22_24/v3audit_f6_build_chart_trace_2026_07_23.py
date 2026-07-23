"""Build the Audit V3 CSV provenance map for both public HTML pages."""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "deliverables_n22_24"
OUT = DATA / "CM_V3AUDIT_F6_chart_trace.csv"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    rows: list[dict[str, object]] = []

    def add(chart, series, n, value, unit, source, field, derivation="direct"):
        rows.append(
            {
                "chart": chart,
                "series": series,
                "n": n,
                "display_value": value,
                "unit": unit,
                "source_csv": source,
                "source_field": field,
                "derivation": derivation,
            }
        )

    f1_name = "CM_V3AUDIT_F1_words_timing.csv"
    f1 = [row for row in read(f1_name) if row["interpreter"] == "3.13.5"]
    for row in f1:
        n = int(row["n"])
        for series, field in (
            ("CM bigint", "bigint_cm_us"),
            ("Bitset bigint", "bigint_raw_us"),
            ("CM words", "words_cm_us"),
            ("Bitset words", "words_raw_us"),
        ):
            add("dashboard_eval", series, n, float(row[field]), "us", f1_name, field)
        for series, field in (("CM", "cm_speedup"), ("Bitset", "raw_speedup")):
            add("dashboard_words_speedup", series, n, float(row[field]), "x", f1_name, field)
        if n >= 16:
            add(
                "kernel_ratio",
                "bigint engine",
                n,
                round(float(row["bigint_cm_us"]) / float(row["bigint_raw_us"]), 2),
                "CM/Bitset",
                f1_name,
                "bigint_cm_us/bigint_raw_us",
                "ratio, rounded 2dp",
            )
            add(
                "kernel_ratio",
                "words engine",
                n,
                round(float(row["words_cm_us"]) / float(row["words_raw_us"]), 2),
                "CM/Bitset",
                f1_name,
                "words_cm_us/words_raw_us",
                "ratio, rounded 2dp",
            )

    live_name = "CM_flat_liveness_py313_fable_summary.csv"
    for row in read(live_name):
        n = int(row["n"])
        add("dashboard_liveness", "CM", n, round(float(row["cm_flat_liveness_speedup"]), 2),
            "x", live_name, "cm_flat_liveness_speedup")
        add("dashboard_liveness", "Bitset", n, round(float(row["raw_flat_liveness_speedup"]), 2),
            "x", live_name, "raw_flat_liveness_speedup")

    c3_name = "CM_FABLE_c3_blast_radius_summary.csv"
    for row in read(c3_name):
        n = int(row["n"])
        for series, field in (
            ("CM wrapper", "cm_cached_us"),
            ("old comparator", "bitset_old_us"),
            ("corrected Bitset", "bitset_new_us"),
        ):
            add("dashboard_c3", series, n, float(row[field]), "us", c3_name, field)

    env_name = "CM_env_build_2026-07-21_py313_fable.csv"
    for row in read(env_name):
        n = int(row["n"])
        if n <= 20:
            add("dashboard_env", "old builder", n, float(row["old_median_s"]) * 1000,
                "ms", env_name, "old_median_s", "seconds to milliseconds")
            add("dashboard_env", "vectorized", n, float(row["new_median_s"]) * 1000,
                "ms", env_name, "new_median_s", "seconds to milliseconds")

    f2_name = "CM_V3AUDIT_F2_threshold_paired_raw.csv"
    f2 = read(f2_name)
    for n in (16, 18, 20, 22, 24):
        values = [float(row["t16_over_bitset"]) for row in f2 if int(row["n"]) == n]
        add("wrapper_ratio", "wrapper", n, round(statistics.median(values), 2), "CM/Bitset",
            f2_name, "t16_over_bitset", "median over 300, rounded 2dp")
    ext_name = "CM_FABLE_extended_n32_summary.csv"
    for row in read(ext_name):
        n = int(row["n"])
        if int(row["depth"]) == 4 and n > 24:
            add("wrapper_ratio", "wrapper", n, round(float(row["ratio_median"]), 2),
                "CM/Bitset", ext_name, "ratio_median", "depth-4 cell, rounded 2dp")

    corrected_name = "CM_V3AUDIT_F5_corrected_all_live_summary.csv"
    for row in read(corrected_name):
        n = int(row["n"])
        add("corrected_all_live_time", "CM words", n, round(float(row["cm_words_us_median"]), 2),
            "us", corrected_name, "cm_words_us_median")
        add("corrected_all_live_time", "Bitset words", n,
            round(float(row["bitset_words_us_median"]), 2), "us", corrected_name,
            "bitset_words_us_median")
        add("frontier_ratio", "corrected all-live", n,
            round(float(row["cm_over_bitset_median"]), 2), "CM/Bitset", corrected_name,
            "cm_over_bitset_median")

    beyond_name = "CM_FABLE_comprehensive_beyondguard.csv"
    beyond = read(beyond_name)
    for n in (24, 28, 32):
        values = [float(row["ratio_words"]) for row in beyond if int(row["n"]) == n]
        add("frontier_ratio", "beyond guard", n, round(statistics.median(values), 2),
            "CM/Bitset", beyond_name, "ratio_words", "median across depths, rounded 2dp")

    # Key narrative corrections shown next to the charts.
    add("narrative", "F4 raw delta", "32-24", 1.8256669864, "us",
        "CM_V3AUDIT_F4_binding_profile_summary.csv", "full_raw_us_median", "same-formula delta")
    add("narrative", "F4 bind delta", "32-24", 1.49549994, "us",
        "CM_V3AUDIT_F4_binding_profile_summary.csv", "bind_hit_us_median", "same-formula delta")
    add("narrative", "Fable all-live rows actually all-live", "all", 4, "of 29",
        "CM_V3AUDIT_F5_family_structure_summary.csv", "actually_all_live_count")
    add("narrative", "Fable n32 semantic support", 32, 16, "variables",
        "CM_V3AUDIT_F5_family_structure_raw.csv", "semantic_live_k")

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} chart/narrative provenance rows -> {OUT.name}")


if __name__ == "__main__":
    main()
