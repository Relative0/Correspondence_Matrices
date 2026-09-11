# CM local implementation continuation — September 11, 2026

Three optional facilities are implemented and verified: a bounded positional
mask cache, exact independent-component counts/existence, and bounded ordered
packed streaming. The existing native batch successor also completed its full
prospective local campaign. It is exact but **failed the frozen performance
gate**, so it is not advanced or promoted. Existing production dispatch remains
unchanged.

The [execution plan](../../research/CM_LOCAL_IMPLEMENTATION_PLAN_2026_09_11.md)
provides standing authorization for routine local work and records the remaining
prerequisites. The [API guide](../../research/CM_PACKED_QUERY_APIS_2026_09_11.md)
contains executable usage patterns, limits and ownership contracts. The
[research disposition ledger](../../research/CM_CONTINUATION_RESEARCH_DISPOSITIONS_2026_09_11.md)
carries the wider algorithm and hardware opportunities forward without reopening
failed gates or substituting synthetic data for real application traces.

**Implemented behavior.** `PackedMaskCache` shares immutable integer columns by
width across renamed bases. It has an explicit admitted-column byte budget,
maximum build width, LRU eviction, oversized-entry bypass, serialized builds and
clear, and observable lifecycle counters. Its accounting covers width keys,
column tuples and column integers; LRU bookkeeping, builds in flight and
caller-retained references are separate. It is not a total-process RSS ceiling.

`IndependentCountPlan` peels a root conjunction and merges operands with
overlapping support. Counts multiply only across disjoint components, with
unused live axes contributing their exact multiplicity. It supports fixed
assignments, constants, arbitrary declared ordering and existence queries. An
inseparable expression follows the exact single-component path or refuses a
live width above the caller's build limit. Restriction does not trigger another
decomposition pass. Both raw expressions and existing CM nodes are accepted.

`PackedStreamPlan` fixes high assignment axes and evaluates low axes in bounded
chunks using the existing flat evaluator. Output offsets, valid bit counts,
little-endian bytes and remaining-variable order are explicit. Invalid contexts,
chunk limits and total-output budgets are refused before iteration starts.
Separate iterators have separate bindings; early closure releases the generator
frame. A caller who retains every chunk intentionally retains the full output.

These facilities use neither the global named-mask LRU nor its per-program bound
context cache. They retain compiled structure within an explicit session and
share a caller-owned positional cache. This makes cache lifetime and the output
contract visible to the caller; it does not establish a universal backend policy.

**Frozen local panels.** Development used count widths 12/16, streaming widths
16/18 and width-16 cache traces. Confirmation used distinct count widths 18/20,
streaming widths 17/20 and width-18 cache traces. Count inputs included both
disjoint conjunctions and inseparable OR combinations. q1 is unrestricted;
q16 uses rotating three-variable restrictions. Cache traces include repeated
names, renamed bases, width phases and pressure, with 32 requests each.

Nine paired rounds reverse arm order. Cold costs include serialized ingress
decode, preparation, binding, evaluation, required scalar JSON or incremental
ordered-vector SHA-256 delivery, and explicit plan/cache release. A repeated
prepared query pass is measured separately. The direct contextual interpreter
is identity-memoized and explicitly breaks its recursion-cell reference to
release temporary masks promptly. CSE-flat uses the current sharing-aware
compiler; `dd.autoref` is an explicitly portable symbolic control with fixed
ordering. No native CUDD result is implied.

Allocation tracing is separate from timing. Fourteen source files, exact
fixtures and the full schedule were frozen before measurement. All 612
development and 612 confirmation timing rows were exact; 136 separate memory
rows also checked their outputs. Replay verifies **15,480 cold outputs**, source
identity, schedules, cache bounds and summaries. Another 15,480 warm outputs
were asserted exact during execution but are not independently stored. The
verifier shares the NumPy oracle and bootstrap implementation with the harness;
the scalar unit tests are the independent semantic implementation check.

Selected confirmation results follow. Ratios above one favor the new API.
The ratio of medians and the paired geometric-mean estimate are different
statistics; the interval belongs to the paired geometric mean.

| Task and candidate | Baseline → candidate median | Ratio of medians | Paired geometric mean, 95% bootstrap interval |
| --- | ---: | ---: | ---: |
| n18 renamed cache, 32 requests; positional versus named LRU | 29.607 → 1.548 ms | 19.127x | 20.120x [16.883, 23.462] |
| n18 disjoint count, q1; raw-expression plan versus CSE-flat | 1.463 → 0.471 ms | 3.103x | 2.902x [2.686, 3.158] |
| n20 disjoint count, q1; raw-expression plan versus CSE-flat | 4.778 → 0.504 ms | 9.483x | 9.327x [8.673, 9.839] |
| n20 disjoint count, q16; raw-expression plan versus CSE-flat | 8.268 → 1.176 ms | 7.033x | 7.672x [6.996, 8.891] |
| n20 stream, q1; 16-variable chunks versus complete CSE-flat | 6.901 → 2.833 ms | 2.436x | 2.002x [1.562, 2.447] |
| n20 stream, q1; 12-variable chunks versus complete CSE-flat | 6.901 → 8.075 ms | 0.855x | 0.760x [0.653, 0.862] |

These are selected task-specific results, not an aggregate CM victory. The
complete per-case medians, worst paired ratios, warm timings and intervals are
in `packed-panels/*-SUMMARY.json`; all scheduled outcomes remain in the raw files.

The n18 renamed-cache traced peak fell from 20,295,476 to 736,679 bytes. The
n20 disjoint count peak fell from 4,502,680 bytes for CSE-flat to 49,813 bytes
for the expression plan, or 57,421 bytes including CM construction. The n20
stream peak fell from 5,911,188 to 246,073 bytes with 16-variable chunks, about
24x smaller, and to 56,256 bytes with 12-variable chunks. Time to the first
chunk, including setup, was 0.786 ms and 0.559 ms respectively. These are
Python-traced allocations, with chunks consumed incrementally, not OS RSS.

**Regressions and control strengthening.** At n20 on the inseparable q1 count,
the expression plan's cold ratio was 0.981x and its warm ratio only 0.169x.
The full-width column entry exceeds the chosen 2 MiB cache budget and is rebuilt;
the incumbent retains its bound context. The portable BDD control won that cold
case at 1.147 ms versus 5.330 ms for the expression plan. On small development
count sessions, component construction/rebinding also outweighed saved work.
Including CM construction reduced the decomposable n20 q1 speedup from 9.483x
to 5.582x. There is no claim that CM-specific construction caused the gain.

The width-18 pressure trace had a cold positional-cache ratio of 1.301x but a
warm ratio of 0.030x: bounded admission trades cache hits for retention. Same-name
cache timing was noisy: its ratio of medians was 1.400x, but paired geometric
mean was 0.999x with interval [0.789, 1.238]. It supplies no stable speedup claim.
Eight-variable streaming chunks were consistently expensive; the n20 q16 cold
ratio was 0.071x. The smaller memory footprint does not erase that regression.

After confirmation, a separate **reused-data mechanism diagnostic** compared all
four stream fixtures against a single-chunk positional control with the same
binding, dead-slot release and cache budget. All 216 timing cells / 1,836 cold
outputs verified. At n20 q1, 16-variable chunks retained a 2.353x ratio of medians
and reduced peak allocation from 3,670,608 to 246,073 bytes. At n20 q16, their
ratio was 0.929x; the paired interval [0.879, 1.114] does not establish a win.
Thus much of the repeated-query advantage over the original incumbent comes
from positional reuse and binding behavior. Tiling itself remains useful for
memory and larger one-shot outputs. This diagnostic does not replace the frozen
confirmation, tune a threshold or establish a default chunk width. Its absolute
timings differ from the earlier panel and must not be compared across runs.

**Fresh-process and application limits.** Sixty paired fresh-child diagnostics
include interpreter imports, request execution, output transmission and process
exit. Startup dominates these small tasks. For example, the n20 decomposable
count medians were 787.177 ms CSE-flat and 733.234 ms for the new plan, despite
resident medians of 5.425 and 0.913 ms within those children. The renamed n18
cache improved resident work from 27.255 to 1.673 ms, while whole-process medians
were 855.856 and 846.557 ms. Some n16 whole-process comparisons regressed. Five
pairs on this uncontrolled desktop are descriptive lifecycle checks, not stable
one-shot speedup claims. The faster 16-variable streaming configuration did not
have a separately frozen fresh-process cell; only the fixed 12-variable control
was selected for that diagnostic before timing.

All eight historical conditioned k8 feature-model slices were replayed across
two versions and nine contexts each: 144 exact scalar-CNF count/existence and
packed-stream checks. Component widths were mostly one, with a maximum of five.
These are consumed, bounded real-source slices; their original contract returned
complete version vectors. They do not prove full-model speed or the prevalence
of a count-only or streaming application consumer.

**Native successor result.** The installed MSVC compiler built the separate
successor DLL. Its original exactness tests checked 1,152 C36 restrictions
against scalar native execution and independent full-truth restriction. A new
preflight discovered a JSON hash bug: integer width-count keys were sorted
numerically before saving and lexicographically after loading. Normalizing those
keys to strings before hashing fixed the round trip. The invalid first freeze
is retained, and a regression test verifies both round-trip acceptance and
tamper rejection. No performance cells ran against the invalid freeze.

The corrected prospective campaign used 36 cases, 12 counterbalanced blocks,
q8/q32/q96, and a fresh process for each of 2,592 cells. It completed in
1,917.23 seconds with zero failures, timeouts or independent verification
mismatches. All 117,504 requested query outputs matched their frozen hashes.

| Queries | Fully charged scalar/batch ratio | Batch case wins | Case-geometric-mean 95% interval |
| --- | ---: | ---: | ---: |
| q8 | 0.9864x | 17/36 | [0.9564, 1.0194] |
| q32 | 1.0154x | 24/36 | [0.9927, 1.0400] |
| q96 | 1.0781x | 32/36 | [1.0585, 1.1004] |

The q96 ratio failed the fixed 1.10x requirement; its case-win, lower-confidence-
bound and q32 gates passed. The disposition is **no-go for this workload**.
Cleanup occupied 51.22% of aggregate scalar q96 accounted time and 55.92% of
batch accounted time. Dropping that cost would change the frozen task and is
not used to rescue the result. Process/library startup was recorded separately
and excluded from the frozen resident-request total. This candidate does not
proceed to a second host or production routing.

**Validation and remaining work.** The targeted regression suite passed **245
tests plus four subtests**; the panel preflight added **four passing tests**.
There were no test failures, skips or missing tools in those runs. The new
semantic tests cover all 256 three-variable Boolean functions under all 27
partial assignments, random shared DAGs and all operators, constants, reordered
and unused axes, budget refusal, immutable reuse, eviction, concurrency and
generator closure. The full repository test suite was not run. See `TESTS.xml`,
`PANEL_PREFLIGHT_TESTS.xml` and [commands](COMMANDS.md).

The earlier audit's 54 artifact hashes still match. Initial source snapshots
preserve unrelated dirty-file bytes, and the final manifest records the owned
source, artifacts and review. No commit, push, publish, deployment, paid resource
or external write was performed.

P0–P7 have reached their feasible local completion boundaries. The three APIs
remain explicit options. Production adoption requires a real workload and its
consumer contract; broader symbolic, GF(2), incremental and hardware experiments
retain the concrete admission prerequisites in the research ledger. Routine
local work within that plan does not require another authorization prompt.
