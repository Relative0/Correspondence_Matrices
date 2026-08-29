# Structural persistence and trace-provenance progress

CM, structural common-subexpression elimination (CSE) and the direct-CNF
control passed the expanded frozen structural serialize/reload pilot on eight
cached real feature-model slices. The run produced 144/144 successful cells
and 288 independently checked relation rows. This establishes bounded
functional persistence for these three representations. It is not a speed,
memory, file-size or deployment advantage.

The same work closes a provenance ambiguity: generated task sequences,
reconstructed sequences and genuinely observed user sessions now have distinct
contracts. The saved pilot contains 48 generated controls and zero natural
traces. Its natural-trace claim is therefore explicitly false.

## Executed evidence

| Item | Result | Evidence |
| --- | --- | --- |
| Expanded frozen pilot | 144/144 cells passed: 48 each for CM, CSE and direct CNF | [summary](verification/comparative-persistence-pilot-v2-2026-08-29/summary.json) |
| Semantic checking | 288 exact relation rows agreed with the scalar CNF oracle and independent flat-program/clause replay | [cell ledger](verification/comparative-persistence-pilot-v2-2026-08-29/ledger.jsonl) and [oracles](verification/comparative-persistence-pilot-v2-2026-08-29/oracles.json) |
| Determinism | Serialized bytes were identical across six balanced blocks for each backend/case/version identity | [plan](verification/comparative-persistence-pilot-v2-2026-08-29/plan.json) |
| Trace provenance | 48 generated controls, six task classes, zero natural sessions | [trace record](verification/comparative-persistence-pilot-v2-2026-08-29/trace-provenance.json) |
| Frozen reproduction | 36-file checksum set, unchanged source snapshot and successful non-mutating verifier | [checksums](verification/comparative-persistence-pilot-v2-2026-08-29/checksums.json) and [frozen sources](verification/comparative-persistence-pilot-v2-2026-08-29/source_snapshot) |

The three new suites plus the master-site suite passed 25/25 tests. The broader
comparative discovery passed 82/82 tests. `pip check` reported no broken
installed requirements, and the frozen pilot verifier again reported 36 files,
144 cells and `mutated: false`.

The wider [research check receipt](verification/research-check-persistence-trace-2026-08-29.json)
is deliberately retained as failed: 208 of its 209 current tests and all 121
frozen-snapshot tests passed, while the concurrently added
`test_cm_runpod_corpus_offline` module could not import because `pytest` is not
installed in the project virtual environment. No test failure occurred after
that import boundary, no harness file changed during the check, and no package
was silently installed. This tooling gap must be resolved before calling the
whole research check green.

The local master page passed its HTML/parser and exact-content tests, including
the report link and saved-summary values. Programmatic in-app visual inspection
was unavailable because the browser control policy refuses local `file://`
page access; no alternate browser or policy workaround was attempted.

The earlier 64-cell CM/CSE-only v1 receipt is retained beside v2 rather than
rewritten. The eight inputs are conditioned `k=8` slices from the existing cached-real
bridge, not full feature models or a new upstream acquisition. Each of the two
versions was reconstructed and executed after reload in every cell. Six
balanced blocks detect order-dependent nondeterminism but are repetitions of
the same eight cases, not independent datasets.

The serialized bundle is inert canonical JSON containing backend identity,
scenario/version/order identity and either flat structural instructions or the
direct-CNF clauses. It refuses unknown fields, noncanonical JSON, identity
mismatches, unsupported backends, oversized inputs, malformed instructions and
out-of-range literals. It does not contain a truth vector, cached query answer
or serialized executable object. CM/CSE reload builds a fresh program through
the scalar flat-program importer; direct CNF reconstructs an immutable clause
structure before a separate clause replay.

The implementation is in
[`cmbench/comparative/persistence.py`](../../cmbench/comparative/persistence.py),
with the provenance contract in
[`cmbench/comparative/traces.py`](../../cmbench/comparative/traces.py).
The frozen runner and verifier are
[`scripts/cm_comparative_persistence_pilot.py`](../../scripts/cm_comparative_persistence_pilot.py).

## Claim boundary

This pilot supports only the following statement:

> On eight previously cached conditioned feature-model slices, the tested CM,
> structural CSE and direct-CNF implementations serialized their structures,
> reconstructed fresh structures, and reproduced both versions' exact bounded
> relations in all 144 scheduled cells.

It does not establish:

- a persistence advantage over BDD, ZDD, d-DNNF, SAT or direct CNF;
- cold-start, reload-time, peak-RSS, resident-memory or artifact-size rankings;
- portability across language/runtime versions or untrusted deployment hosts;
- whole-model behavior, production compatibility or a stable public format;
- a natural-session workload or real-user interaction distribution; or
- independent reproduction by another person or organization.

Native CUDD BDD/ZDD and d4 persistence remain gated on reviewed native builds,
matched extraction obligations and safe process-level resource measurement.
The separate Runpod native scout is not evidence for this persistence claim.

## Natural-trace investigation

A bounded primary-source search on 2026-08-29 did not find a clearly licensed,
public corpus containing ordered, timestamped feature-configurator decisions.
This is a search result, not proof that no such corpus exists.

The strongest reusable candidate found was the University of Magdeburg
[PROFilE dataset page](https://wwwiti.cs.uni-magdeburg.de/~jualves/PROFilE/).
It publishes four historical configuration collections:

| Dataset | Documented size | Documented records | Trace assessment |
| --- | ---: | --- | --- |
| ERP System | 1,653 features; 171 configurations | `userID`, `featureID` pairs | Final selected-feature sets; no order or timestamps documented |
| E-Agribusiness | 2,008 features; 5,749 configurations | `userID`, `featureID` pairs | Final selected-feature sets; no order or timestamps documented |
| Dell Laptop | 68 features; 42 configurations | Per-customer selected/unselected feature files | Final configurations; no order or timestamps documented |
| Library | 135 features; 74 configurations | Per-customer selected-feature files | Final configurations from an experiment with 37 participants; no event order or timestamps documented |

The authors' README files state that these data are available for
**non-commercial use** and omit names and other personal information. The
project should therefore link to the source rather than redistribute the
archives in the public download unless the intended redistribution has been
separately reviewed or permission is obtained. If the endpoint configurations
are later imported for research, the import must preserve the upstream README,
citation, acquisition time, exact archive hash and non-commercial restriction.

PROFilE is valuable for endpoint-frequency, recommendation and complete
configuration workloads. It is not evidence for the order, dwell time,
backtracking or abandonment patterns of real interactive sessions. Any event
sequence synthesized from its unordered endpoints must be labeled
`reconstructed_public_events` or `generated_control`, never
`observed_natural`.

The [FEACKER project](https://github.com/onekin/FEACKER) and its
[research artifact](https://doi.org/10.5281/zenodo.8187116) were also
considered. They concern feature-usage feedback after derivation, rather than
a documented corpus of configurator select/deselect/undo sessions. They may
support a separate deployed-feature-usage workload, but do not close the
natural configuration-trace gap.

## Admission contract for a natural trace

The new corpus validator permits an `observed_natural` claim only when all of
the following are present and internally consistent:

1. A public HTTPS source requiring no credentials, with an exact content
   SHA-256 and a redistribution/use license.
2. A timezone-bounded capture interval and an explicit privacy classification.
3. Stable source record identifiers for every trace.
4. A predeclared or complete-source selection, rather than selection based on
   CM performance or benchmark outcomes.
5. Actual ordered observed events. Reconstructed or generated events cannot
   be upgraded to natural by changing a label.

For an acquisition we control, the minimum pseudonymized event schema should
record:

- pseudonymous session ID and stable source-record ID;
- feature-model ID, exact version/hash and configurator version;
- UTC timestamp plus monotonic event sequence;
- feature ID and action: select, deselect, undo, clear or version transition;
- whether the action was user-entered or solver-propagated;
- observed response: accepted, conflict, completion count or refusal;
- completion, abandonment and error status; and
- license/consent, privacy treatment and capture-window metadata.

Free text, names, email addresses, account identifiers, IP addresses and raw
credentials are outside this benchmark schema. The event collector should be
reviewed before capture and published only as a privacy-safe, license-compatible
snapshot with a frozen selection ledger.

## Reproduce locally

Use the project virtual environment and a new output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_comparative_persistence_pilot.py run --output tmp/persistence-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_comparative_persistence_pilot.py verify --output tmp/persistence-NEW-ID
.\.venv\Scripts\python.exe -B -m unittest tests.test_cm_comparative_persistence tests.test_cm_comparative_traces tests.test_cm_comparative_persistence_pilot
```

The final saved run used no cloud resources or network access. Its per-call
timings are diagnostics only; the contract explicitly disallows a performance
claim. No native dependency was installed and no production default changed.

## Next useful work

1. Add a license-aware, hash-pinned endpoint importer for PROFilE without
   bundling the upstream archives. Treat generated action order as a separate
   control cohort.
2. Seek or collect an observed, consented and privacy-safe configurator event
   corpus under the admission contract above. Freeze selection before any
   method timings are inspected.
3. Extend structural reload to native BDD/ZDD/d-DNNF only after native build
   identity, extraction costs, resource accounting and cleanup are validated.
4. Run balanced fresh-process construction/reload/query blocks with comparable
   process-tree RSS and artifact byte counts. Keep correctness and performance
   receipts separate.
5. Obtain an external-person reproduction of the frozen pilot before treating
   deterministic local replay as independent evidence.

No dataset archive, cloud workload, external write, commit, push or publication
was performed by this continuation.
