# Mechanisms and bounded opportunity decisions

The approved queue is closed for this execution. No policy, IR redesign, new
dependency installation or scientific promotion is included.

| Area | Evidence and recurring cost | Invariant/control | Decision |
|---|---|---|---|
| Duplicate sharing preparation | **Measured:** root-only miss prepasses fall from two to one; normal and persistent canonical keys/program shapes agree. Final resident miss time falls 9–11%. | Exact root/options, scoped plan, subclass/reentry/failure restoration; persistent-off control stays near parity. | **Keep** per-call plan reuse. Do not extend lifetime across calls. |
| Duplicate wrapper admission | **Measured:** fallback uses one budget decision; final resident fallback saves 8–14 us. | Same full/reduced basis, bytes/temp/variable refusal and diagnostic semantics. Generic treatment supplies the incremental control. | **Keep** shared planning. Packed fast calls cost about 1–2 us more; accept the small explicit maintenance tradeoff. |
| Disabled trace dispatch | **Measured:** candidate 2 crosses the tiny identical-family review margin in independent workers. | Same evaluator/oracle plus newly required provenance. Trace off/on is a separate instrumentation treatment. | **Keep** per-family binding of observers so off calls execute helpers directly. Final reporting still costs time; no family-wide speed claim. |
| Repeated structural digest on warm calls | **Measured:** `_persistent_digest` remains in separate hot-helper profiles and traced spans. **Code-supported inference:** it recurs before hits because source/options establish identity. | A persistent plan would need immutable-root lifetime, full option keys and memory bounds; separately allocated equal roots must remain sound. | **Defer** persistent digest/source caching. Existing per-call digest memo already avoids repeated full walks within a call. |
| Foreign adoption and interning | **Measured:** shared family still has 52 subtree hits, no root hits, and adoption/intern helper calls. Retained cache reaches 61 unique CM nodes. | Builder-local UID consistency, canonical rewrites, strong foreign pinning and GC/id-pressure tests. | **Defer** bypassing adoption. A map hit does not mean its parent graph is free to build. |
| Node-count caching | **Code-supported inference:** `_cm_node_count` already caches on the root; separate trace observes the warm read. | Refusal must still precede allocation and execution. | **Reject** another node-count cache: it would duplicate existing state without a demonstrated saving. |
| Budget-plan caching | **Measured:** budget helpers recur; **hypothesis:** repeated identical calls could reuse a plan. | Every output basis, fixed map, representation and limit affects correctness; stale plans could admit an invalid output. | **Defer**. No measured advantage justifies adding a second lifetime/key system in this repair. |
| Variable masks and program binding | **Measured/code-supported:** warm calls retain lowering/bound programs; `_bind_flat_program` still encodes fixed values then looks up a context key. Existing environment and per-program caches already amortize mask construction. | Same positional order, fixed values, output width and cache extent. | **Defer** more caching. The measured kernels are small, and q1/q64 semantics remain covered. |
| CM key/support/node metadata | **Measured:** retained entries, reachable graph counts and support sizes remain material on misses; native/RSS retention is unknown. | Preserve canonical identity and public CM information. | **Defer** compact-IR redesign; this is a separate representation question. |
| Oracle conversion/reference sharing | **Measured:** explicit separate family phases; correctly classified as harness work. | Complete exact checking of every available result; sampled/skipped counts remain explicit. | **Keep** attribution and reduced-output oracle repair; do not remove checks or present cheaper oracle work as CM speed. |
| Words allocation/liveness/conversion | **Measured:** combined words span retained; bare bigint controls are a different engine. | Same widths, allocation and integer-delivery contract. | **Defer** further kernel work; no isolated material defect established here. |
| Cache entry/byte capacity | **Measured:** five-root composition cache is stable across 64 resident rounds; bytes are Python-traced, not native RSS. | Existing eviction and capacity policy, bounded-eviction tests. | **Defer** capacity policy. The small bounded session is not a production memory forecast. |
| SAT/count/equivalence/assignment representation | **Code-supported inference from frozen study:** these contracts may not require an explicit full relation. | Task-matched result/validation/delivery; do not compare a status bit with full-relation output as the same workload. | **Defer** separate research; mathematical expressiveness does not make full-relation execution appropriate. |

Three implementation candidates were examined, preserving all their records.
Subsequent changes corrected two diagnostic defects: root position was initially
confused with root-only policy, and core compilation initially imported a new
tracing module missing from a standalone dependency manifest. The final code
distinguishes both hit axes and receives an optional caller observer instead.
The original `MECHANISMS.json`/v2 and package-closure failure remain superseded
evidence; use `MECHANISMS-final-v3.json`, `PROFILE_RESULTS-v2.json` and final test logs.
Final review additionally fixed hit-origin attribution after an initial key is
evicted and reinserted during the same call. A bounded-eviction regression test
passes; no cache policy changed. Earlier result versions remain preserved.
