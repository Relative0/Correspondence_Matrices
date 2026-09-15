"""Read-only synthesis of frozen diagnostic results; refuses output overwrite."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE/name).read_text(encoding="utf-8"))


def cause_for(arm, treatment=""):
    if arm.startswith("public"):
        return ["wrapper/lifecycle cost", "CM representation cost", "output conversion/delivery cost", "unresolved"]
    if "cache" in arm or arm == "cm_family":
        return ["CM-family reuse-management cost", "CM representation cost", "unresolved"]
    if arm == "dense_cm":
        return ["inherent explicit-relation/output cost", "output conversion/delivery cost", "task/algorithm mismatch"]
    if arm.startswith("sympy"):
        return ["comparator-specific preparation", "task/algorithm mismatch", "unresolved"]
    if "words" in arm:
        return ["current implementation/runtime cost", "output conversion/delivery cost", "CM representation cost" if arm.startswith("cm") else "comparator-specific preparation", "unresolved"]
    if arm.startswith("cm") or arm == "bare_cm_flat":
        return ["CM representation cost" if treatment != "resident_q64" else "current implementation/runtime cost", "current implementation/runtime cost", "unresolved"]
    return ["current implementation/runtime cost", "comparator-specific preparation", "unresolved"]


def build():
    ladder, tasks, rawtasks, frozen = (read(n) for n in
        ("ladder_summary.json", "TASK_SUMMARY.json", "task-run-001/TASK_RESULTS.json", "frozen_evidence.json"))
    result = {
        "schema": "cm-time-attribution-deep-dive/v1",
        "base_commit": "e334de594262059cc18cf37eaab56b0f79e94843",
        "scientific_disposition_changed": False,
        "classification": "diagnostic only; measured/code-supported inference/hypothesis/unknown kept distinct",
        "measurement_cells": {"ladder": 137, "task_family": 70, "all_exact": True},
        "units": {"ladder": "seconds and bytes", "tasks": "nanoseconds and bytes", "frozen": "original explicit field units"},
        "phase_share_rule": "exclusive own-pass sums; no profiled span divided by an uninstrumented total; inclusive annotations are not summands",
        "bounds_and_exclusions": "PLAN.md; METHOD_LIMITS.md; TASK_METHODS.md",
        "sources": [{"path": name, "sha256": hashlib.sha256((HERE/name).read_bytes()).hexdigest()}
                    for name in ("PLAN.md", "ladder-run-002.json", "ladder_summary.json", "TASK_SUMMARY.json",
                                 "task-run-001/TASK_RESULTS.json", "frozen_evidence.json")],
        "superseded_preserved": ["ladder-smoke-001.json", "ladder-run-001.json"],
        "ladder": ladder,
        "tasks": tasks,
        "frozen_evidence": frozen,
        "unknown_measurements": {
            "exact_arithmetic_versus_allocation_time": None,
            "separate_cache_lookup_versus_validation_time_where_grouped": None,
            "unbiased_tiny_helper_cpu_percentages": None,
            "cumulative_allocated_bytes": None,
            "full_native_peak_rss": None,
            "library_session_final_teardown_time": None,
            "historical_startup_versus_import_versus_transport_split": None,
        },
    }
    for summary, raw in zip(result["tasks"]["cells"], rawtasks["cells"]):
        assert summary["cell"]["id"] == raw["cell"]["id"]
        summary["cprofile_separate_pass"] = raw["profile"]
        summary["memory_separate_pass"] = raw["memory_pass"]
        summary["unresolved_subphases"] = raw["inseparable"]
    observations = []
    indexed = {(r["case"], r["arm"]): r for r in ladder["cells"]}
    for row in ladder["cells"]:
        arm, case = row["arm"], row["case"]
        if arm == "dense_cm":
            observations.append({"suite": "ladder", "case": case, "arm": arm, "status": "different output contract",
                                 "classes": cause_for(arm), "measured_slowdown_ratio": None})
            continue
        refarm = "cse_words" if arm == "cm_words" else "cse_flat"
        if refarm == arm: continue
        control = indexed[(case, refarm)]
        for treatment in ("cold_q1", "resident_q64"):
            wall = row["timing"][treatment]["per_operation"]["wall_s"]["median"]
            ref = control["timing"][treatment]["per_operation"]["wall_s"]["median"]
            if wall <= ref: continue
            phases = row["phase"][treatment]["exclusive_phases"]
            top = sorted(phases, key=lambda n: -phases[n]["wall_s"])[:4]
            observations.append({"suite": "ladder", "case": case, "arm": arm, "control": refarm,
                                 "treatment": treatment, "measured_slowdown_ratio": wall/ref,
                                 "measured_median_increment_s": wall-ref,
                                 "classes": list(dict.fromkeys(cause_for(arm, treatment))),
                                 "largest_measured_joint_phases": top,
                                 "status": "measured difference; cause categories code-supported; exact fraction of difference unresolved"})
    ti = {(r["cell"]["case"],r["cell"]["task"],r["cell"]["q"],r["cell"]["arm"]):r for r in tasks["cells"]}
    for row in tasks["cells"]:
        cell = row["cell"]
        key = (cell["case"],cell["task"],cell["q"])
        choices = ["cse_batch"] if cell["task"] == "assignment_batch" else (["cse_family"] if cell["task"] == "family" else ["cse_packed", "cse"])
        # Source arm labels are taken from the records, never invented.
        candidates = [r for k,r in ti.items() if k[:3]==key and k[3].startswith("cse")]
        if not candidates: continue
        refrow = candidates[0]
        if row is refrow: continue
        ratio = row["wall_median_ns"]/refrow["wall_median_ns"]
        contract = "different family delivery contract" if cell["arm"].startswith("public") else ("algorithm/comparator comparison" if cell["arm"].startswith("sympy") else "same eligible evaluator/contract diagnostic")
        if ratio <= 1 and not cell["arm"].startswith("public"): continue
        observations.append({"suite":"task_family", **cell, "control":refrow["cell"]["arm"],
                             "comparison_class":contract, "measured_slowdown_ratio":ratio if not cell["arm"].startswith("public") else None,
                             "measured_median_increment_s":(row["wall_median_ns"]-refrow["wall_median_ns"])/1e9 if not cell["arm"].startswith("public") else None,
                             "classes":list(dict.fromkeys(cause_for(cell["arm"]))),
                             "largest_measured_joint_phases":sorted(row["phases"],key=lambda n:-row["phases"][n]["mean_wall_ns"])[:4],
                             "status":"measured difference or explicit contract difference; no exact additive causal allocation"})
    result["slowdown_inventory"] = observations
    return result


def matrix(result):
    text = """# Root-cause matrix

## Interpretation

The table classifies mechanisms, not mathematical impossibility. **Measured**
phase times are observations of their stated pass. A code-supported mechanism
does not turn the entire observed difference into a measured causal share.
The per-cell inventory below includes **every positive median difference**
against the declared CSE reference, even tiny differences; this deliberately
avoids selecting a favorable materiality threshold. Near-equality is not a
statistical finding. Different contracts receive no slowdown ratio.

| Cost / tasks | Classification | Evidence level and attribution | Distinguishing limit |
|---|---|---|---|
| Full packed relation and each delivered cofactor | Inherent explicit-relation/output cost | Measured output bytes; code-supported exponential basis-width requirement; fixed-structure k4–18 isolates output growth from node growth | Does not isolate minimal possible arithmetic or allocator cost per output byte |
| Full enumeration used to answer count/SAT/equivalence | Task/algorithm mismatch | Code-supported extra relation information; new identical-evaluator ingress plus frozen task controls | No universal native-counter/CDCL/BDD ranking from tiny cases |
| Structural UID/fanout prepass, Boolean rewriting, sorted support, public structural keys and CMNode construction | CM representation cost | Measured joint phases and counts; cold common-CM slower in all13 disclosed cases; prepared parity often removes this difference | Key construction/hash/sort/allocator interactions inseparable inside helpers |
| Persistent digest, root-only eligibility, subtree reuse, foreign adoption and retained entries | CM-family reuse-management cost | Measured high/partial/zero-hit treatments; composition5 misses0hits; identical roots7hits | No time saved per hit, no separate lookup/validation/eviction duration; no eviction-pressure study |
| Recursive dispatch, identity memo, occurrence expansion, tuple/list allocation, bigint operations, word scratch and release | Current implementation/runtime cost | Measured helper counts, flat primitive counts, memory and joint execution spans | Arithmetic versus allocation/refcount time unresolved; no claim that language/runtime is a CM axiom |
| Node-count budget guards, mode/basis/engine choice, result wrapping, import/process lifecycle, public family diagnostics | Wrapper/lifecycle cost | Matched public/bare resident increment19.6–30.5µs; code-confirmed public obligations; historical process residual | Incremental fraction is not exclusive wrapper share; startup/import/transport not separately identifiable historically |
| Dense reinflation, array/int/bytes/list conversion, serialization, exact API/harness output checks | Output conversion/delivery cost | Measured same-pass stages; Y05 semantic guard68.9%, minimizer28.4%; family residual contains conversion/check/bookkeeping | Common audit guards differ from required API guards; dense and packed outputs have different contracts |
| SymPy conversion/lambdify/minimizer, SAT encoding, BDD construction/extraction, count-specific preparation | Comparator-specific preparation | New measured SymPy stages and frozen task-specific records; source-supported solver/BDD boundary map | Unmeasured native phases remain unknown, not zero |
| Profiler/harness remainder, grouped cache work, object teardown, native RSS, tiny CPU shares | Unresolved | Explicit measured remainder or null; 2.4–66.1% corrected ladder remainder across individual phase passes | No proportional redistribution, fabricated timers or cross-pass additive shares |

## Mechanism answers

- Raw CM and family CM share representation work. Family reuse adds eligibility,
  digest/cache management and foreign adoption; reuse can fail with high syntax
  sharing because canonical shape is context dependent.
- CSE retains useful structural sharing without CM support/public-key structure.
  CM rewrites can lower fewer operations. Same primitive executor isolates that
  representation interaction from a different packed algorithm.
- Packed primitives may be competitive while complete callers regress. Cold
  preparation, recurring public guards, conversion and process lifecycles have
  distinct amortization rules.
- Guard/oracle work observed in a benchmark is not automatically necessary CM
  semantics. Historical residuals only prove time outside named stages; source
  confirms which mechanisms are present, not their separate percentages.

## Exhaustive positive-difference and contract inventory

All times below are uninstrumented medians. `cold_q1` and `resident_q64` are
different preparation treatments. Task sessions retain imports; q64 restriction
cycles four contexts. Largest phases come from a separate, perturbed pass and
are leads for attribution, not fractions of the uninstrumented delta. All exact
values and explicit category lists are in `PROFILE_RESULTS.json/slowdown_inventory`.

| Suite / case | Arm / reference | Treatment | Ratio | Increment µs | Responsible categories | Largest measured joint spans |
|---|---|---|---:|---:|---|---|
"""
    for r in result["slowdown_inventory"]:
        ratio=r.get("measured_slowdown_ratio")
        delta=r.get("measured_median_increment_s")
        text += f"| {r['suite']} / {r['case']} | {r['arm']} / {r.get('control','contract')} | {r.get('treatment',r.get('task','contract'))} | {ratio:.3f} | {delta*1e6:.3f} | " if ratio is not None else f"| {r['suite']} / {r['case']} | {r['arm']} / {r.get('control','contract')} | contract difference | — | — | "
        text += "; ".join(r["classes"]) + " | " + "; ".join(r.get("largest_measured_joint_phases",[])) + " |\n"
    return text + "\nNo scientific disposition changed. No routing recommendation is made.\n"


if __name__ == "__main__":
    outputs=[HERE/"PROFILE_RESULTS.json", HERE/"ROOT_CAUSE_MATRIX.md"]
    if any(p.exists() for p in outputs): raise SystemExit("refusing to overwrite synthesis")
    result=build()
    outputs[0].write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    outputs[1].write_text(matrix(result),encoding="utf-8")
    print(json.dumps({"cells":result["measurement_cells"],"inventory_rows":len(result["slowdown_inventory"])}))
