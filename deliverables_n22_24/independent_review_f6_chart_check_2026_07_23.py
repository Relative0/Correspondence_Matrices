"""Independent review of F6: recompute every plotted value from source CSVs and
compare against the arrays embedded in both public HTML pages.

V3's chart-trace CSV was generated FROM the source CSVs; this script closes the
loop by checking the HTML side against independently recomputed values.
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent

FAILURES: list[str] = []


def read(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check(label, expected, actual, tol=0.005):
    if expected is None and actual is None:
        return
    if expected is None or actual is None or abs(expected - actual) > tol:
        FAILURES.append(f"{label}: html={actual} recomputed={expected}")


# ---- HTML-embedded arrays (transcribed verbatim from the committed pages) ----
KERNEL = {
    "n": [16, 18, 20, 22, 24],
    "bigint engine": [0.56, 0.85, 0.89, 0.96, 0.87],
    "words engine": [0.90, 0.89, 0.96, 0.94, 1.04],
}
WRAPPER = {
    "n": [16, 18, 20, 22, 24, 26, 28, 30, 32],
    "v": [1.05, 1.27, 1.23, 1.15, 1.05, 0.98, 0.92, 0.89, 0.84],
}
FRONTIER_CORRECTED = {"n": [16, 18, 20, 22, 24, 26], "v": [0.48, 0.53, 0.57, 0.48, 0.40, 0.53]}
FRONTIER_BEYOND = {24: 0.96, 28: 0.97, 32: 0.97}

DASH_N = [12, 14, 16, 18, 20, 22, 24]
DASH_EVAL = {
    "bigint_cm_us": [206.1, 398.5, 1254.6, 4996.6, 22458.4, 142092.2, 891702.4],
    "bigint_raw_us": [231.7, 492.5, 2250.7, 5863.9, 25275.2, 148364.4, 1019870.6],
    "words_cm_us": [445.6, 472.6, 809.6, 1855.8, 6706.8, 27172.1, 141895.1],
    "words_raw_us": [555.8, 587.2, 902.2, 2090.0, 7005.5, 28764.8, 136547.3],
}
DASH_SPEEDUP = {
    "cm_speedup": [0.46, 0.84, 1.55, 2.69, 3.35, 5.23, 6.28],
    "raw_speedup": [0.42, 0.84, 2.49, 2.81, 3.61, 5.16, 7.47],
}
DASH_LIVE = {
    "n": [18, 20, 22, 24],
    "cm_flat_liveness_speedup": [1.11, 1.23, 2.10, 0.99],
    "raw_flat_liveness_speedup": [1.28, 1.09, 1.73, 0.98],
}
DASH_C3 = {
    "n": [16, 18, 20, 22, 24],
    "cm_cached_us": [48.0, 10.4, 12.4, 13.0, 6.5],
    "bitset_old_us": [51.5, 17.6, 20.4, 23.1, 10.3],
    "bitset_new_us": [42.2, 8.5, 9.9, 10.5, 7.7],
}
DASH_FULLVARS = {
    "n": [16, 18, 20, 22, 24, 26],
    "cm_words_us_median": [164.45, 369.17, 1252.44, 6595.09, 32325.20, 184430.00],
    "bitset_words_us_median": [308.55, 722.51, 2281.94, 14662.84, 81394.90, 353951.40],
}
DASH_ENV = {
    "n": [14, 16, 18, 20],
    "old_ms": [13.6, 117.3, 1176, 16269],
    "new_ms": [1.32, 5.78, 35.2, 123],
}


def main():
    f1 = {int(r["n"]): r for r in read("CM_V3AUDIT_F1_words_timing.csv") if r["interpreter"] == "3.13.5"}
    for i, n in enumerate(DASH_N):
        row = f1[n]
        for field, arr in DASH_EVAL.items():
            check(f"dashboard eval {field} n={n}", float(row[field]), arr[i], tol=0.06)
        for field, arr in DASH_SPEEDUP.items():
            check(f"dashboard speedup {field} n={n}", float(row[field]), arr[i], tol=0.006)
    for i, n in enumerate(KERNEL["n"]):
        row = f1[n]
        check(
            f"kernel bigint n={n}",
            round(float(row["bigint_cm_us"]) / float(row["bigint_raw_us"]), 2),
            KERNEL["bigint engine"][i],
        )
        check(
            f"kernel words n={n}",
            round(float(row["words_cm_us"]) / float(row["words_raw_us"]), 2),
            KERNEL["words engine"][i],
        )

    f2 = read("CM_V3AUDIT_F2_threshold_paired_raw.csv")
    for i, n in enumerate(WRAPPER["n"][:5]):
        med = statistics.median(float(r["t16_over_bitset"]) for r in f2 if int(r["n"]) == n)
        check(f"wrapper n={n}", round(med, 2), WRAPPER["v"][i])
    ext = read("CM_FABLE_extended_n32_summary.csv")
    for i, n in enumerate(WRAPPER["n"][5:], start=5):
        rows = [r for r in ext if int(r["n"]) == n and int(r["depth"]) == 4]
        assert len(rows) == 1, (n, len(rows))
        check(f"wrapper ext n={n}", round(float(rows[0]["ratio_median"]), 2), WRAPPER["v"][i])

    corr = {int(r["n"]): r for r in read("CM_V3AUDIT_F5_corrected_all_live_summary.csv")}
    for i, n in enumerate(FRONTIER_CORRECTED["n"]):
        check(
            f"frontier corrected n={n}",
            round(float(corr[n]["cm_over_bitset_median"]), 2),
            FRONTIER_CORRECTED["v"][i],
        )
        check(
            f"dashboard fullvars cm n={n}",
            float(corr[n]["cm_words_us_median"]),
            DASH_FULLVARS["cm_words_us_median"][i],
            tol=0.5,
        )
        check(
            f"dashboard fullvars bs n={n}",
            float(corr[n]["bitset_words_us_median"]),
            DASH_FULLVARS["bitset_words_us_median"][i],
            tol=0.5,
        )

    beyond = read("CM_FABLE_comprehensive_beyondguard.csv")
    for n, v in FRONTIER_BEYOND.items():
        med = statistics.median(float(r["ratio_words"]) for r in beyond if int(r["n"]) == n)
        check(f"frontier beyond n={n}", round(med, 2), v)

    live = {int(r["n"]): r for r in read("CM_flat_liveness_py313_fable_summary.csv")}
    for i, n in enumerate(DASH_LIVE["n"]):
        check(
            f"liveness cm n={n}",
            round(float(live[n]["cm_flat_liveness_speedup"]), 2),
            DASH_LIVE["cm_flat_liveness_speedup"][i],
        )
        check(
            f"liveness raw n={n}",
            round(float(live[n]["raw_flat_liveness_speedup"]), 2),
            DASH_LIVE["raw_flat_liveness_speedup"][i],
        )

    c3 = {int(r["n"]): r for r in read("CM_FABLE_c3_blast_radius_summary.csv")}
    for i, n in enumerate(DASH_C3["n"]):
        for field in ("cm_cached_us", "bitset_old_us", "bitset_new_us"):
            check(f"c3 {field} n={n}", float(c3[n][field]), DASH_C3[field][i], tol=0.06)

    env = {int(r["n"]): r for r in read("CM_env_build_2026-07-21_py313_fable.csv")}
    for i, n in enumerate(DASH_ENV["n"]):
        check(f"env old n={n}", float(env[n]["old_median_s"]) * 1000, DASH_ENV["old_ms"][i], tol=1.0)
        check(f"env new n={n}", float(env[n]["new_median_s"]) * 1000, DASH_ENV["new_ms"][i], tol=0.05)

    if FAILURES:
        print(f"{len(FAILURES)} MISMATCHES:")
        for f in FAILURES:
            print(" ", f)
        sys.exit(1)
    print("All plotted values match their source CSVs (both pages).")


if __name__ == "__main__":
    main()
