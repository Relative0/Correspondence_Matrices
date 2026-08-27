# CM website results audit and evidence update

Date: 2026-08-27  
Evidence revision: `4dbfffc1db749e85401d533c5a07cb529a41eb37`  
Pages: `index.html`, `layperson.html`, `investor.html`, `expert.html`, `usecases.html`

## Outcome

The website was reconciled against the newest accepted local
artifacts at the pinned evidence revision and rebuilt from authored sources.
The central historical conclusions remain intact, but stale claims that cache
reuse was unstudied, context reuse was unprofiled, and output behaviour above
the live-support guard was wholly unknown have been replaced by the narrower
results now supported by the 2026-08-26/27 evidence.

The update adds a dated, audience-filtered evidence section to the four
evidence and audience pages. A same-day refinement adds a prominent route
chooser and a dedicated field-oriented use-case guide. It
keeps synthetic cache/family/context diagnostics separate from real-workload
economics; trace reliability separate from performance; dependency resolution
separate from native-algorithm testing; proposed memory policy separate from
current product policy; and engineering identity separate from global semantic
canonicality.

## Claim inventory

- `CLAIM-LEDGER.csv`: 1,459 machine-readable evidence claims and result leaves,
  each with source/field, date, evidence role, audience, status, and action.
- `AUTHORED-LITERAL-AUDIT.csv`: 1,495 numeric or Boolean literals found in the
  authored content, templates, JavaScript, and builder and classified for
  review.
- `STALE-SUPERSEDED-WITHDRAWN.json`: seven earlier published claims retained
  only as struck-through, explicitly labelled history in the corrections
  ledger.
- The generated bundle defines 188 result tokens; 169 are referenced in prose.
  The 19 unreferenced tokens remain in the evidence bundle for existing charts,
  diagnostics, or provenance and are reported by the builder.

## Accepted late evidence incorporated

| Area | Current supported statement | Boundary retained |
|---|---|---|
| Process-local cache | Synthetic all-hit cached whole-call CM remained 3.13–12.84× BitSet; 50-evaluation execution-only ratios were 2.80× at k=16, 3.87× at k=12, 8.91× at k=8, and 11.18× at k=4. | Synthetic process-local reuse, not production economics or cross-process persistence. |
| Related families and contexts | High-reuse family cells were 5.25–26.45× slower than BitSet. Cached CM was 4.85–7.37× faster than uncached CM on the partial-context grid; three n=16/500-context cells were near parity at 1.108, 0.952, and 0.997. | Three-trial hypothesis-generating diagnostics; no CUDD comparison and no real workload. |
| Metrics tracing | Full-rate V1/V2 were rejected at 1.3037 and 1.1173 median whole-call ratios. Deterministic one-in-16 V3 was retained opt-in at 1.0052, with zero exact mismatches, drops, and I/O errors. | Bounded diagnostic mechanism, not business-workload evidence. |
| Workload intake | The strict manifest template validates structurally but is not ready and records 13 blockers. | Template only; no workload was captured or uploaded. |
| Native dependency feasibility | Three disposable CPU attempts cost $0.001948 cumulatively and ended with zero pods; the final attempt built `astutils` before refusing the unauthorized source-only PLY 3.10 build required by `dd` 0.6.0. | Dependency-resolution refusal only; Numba, `dd.cudd`, native restriction, and native performance remain untested. |
| Temporary memory | Four bounded dense cases showed median tracemalloc peak 3.51–38.73× above the estimator; typed refusal occurred pre-materialisation in 4/4 cases. | No current default temporary limit. The 16/64 MiB profiles remain proposed and approval-deferred. |
| DP-R3 and validation | Three duplicate exact-file SHA-256 helpers became one streaming helper. Exactness passed, while the tiny smoke ratio 1.0402 failed both timing gates. | Maintainability/provenance improvement, not a performance result. |

The established B1/E3 and EPFL CM/CSE-flat parity results, V3 workload-specific
bare-program advantage, public-wrapper disadvantage, complete-output guard,
artifact boundaries, and corpus boundaries were not replaced by these later
diagnostics.

## Stale and superseded treatment

The seven superseded claims remain visible only in the corrections ledger with
strikethrough, replacement text, and provenance. Outside that ledger, the
generated pages no longer assert that the persistent cache has never been
studied, that family/context reuse is currently unprofiled, that a whole-call
CM/BitSet crossover has been established, or that all behaviour above the
public live-support guard is uncharacterised. The exact inventory and action
for every historical row is in `STALE-SUPERSEDED-WITHDRAWN.json`.

## Validation

| Check | Result |
|---|---|
| Deterministic build and synthetic generation | Two consecutive runs produced byte-identical SHA-256 hashes for the data bundle, all five pages, and all ten generated synthetic-suite files. |
| Builder / audit / test byte-compilation | Pass under project Python 3.13.5. |
| Shared JavaScript syntax | `node --check` pass under Node 22.18.0. |
| Current website/use-case unit gate | 9 passed in 0.36 s; this includes catalog completeness and synthetic-suite integrity checks. |
| Expanded focused pytest | 91 passed in 44.71 s. |
| Complete repository pytest | 400 passed plus 4 subtests in 101.81 s. An initial sandboxed run had 25 fixture-setup errors because pytest's default Windows temp root was inaccessible; rerunning with an explicit workspace-local `--basetemp` passed with no failures or errors. |
| Claim audit | 1,459 claim rows, 1,495 literal-review rows, seven historical rows. |
| Whitespace integrity | `git diff --check` pass; only line-ending conversion warnings were emitted. |
| Browser, default viewport | All five pages checked at 1280×720: one h1 each, eight audited use-case cards and eight benchmark controls present, zero unresolved tokens, zero horizontal overflow, all local anchors present. |
| Browser, narrow viewport | All five pages checked at 390×844: priority and use-case grids collapse to one column, navigation remains usable, zero page overflow, zero unresolved tokens. |
| Progressive disclosure and console | Benchmark controls opened at both widths, exposed source links and dominance gates, and produced zero console warnings or errors. |

One transient Windows `OSError: [Errno 22]` occurred while overwriting
`expert.html` during an early combined determinism command. A standalone full
rebuild succeeded immediately; the final determinism proof used two subsequent
complete successful builds. A first run of the new token test also exposed a
test-harness false positive for the documented literal `{{token}}` placeholder;
the test now excludes that documentation example and all final gates pass.

Machine-readable JUnit results and final hashes are stored beside this report.

## Same-day navigation and use-case refinement

The master header now leads immediately to **Simple One-Pager**, **CM Use
Cases**, **Investor Brief**, and **Technical Summary**. The earlier audience
labels remain as filenames for link stability but are no longer presented as
“Layperson one-pager” or “Expert technical summary.”

The new use-case guide covers hardware/EDA, rule-constrained AI,
computational biology, classical Boolean support logic in quantum toolchains,
compilers, security policy, configuration systems, and regulated decision
systems. Each field states the problem, CM-specific fit, information that may
be preserved, incumbent methods, and the evidence that would settle the
hypothesis. Hardware remains measured adjacency rather than a deployed
workflow; all other fields are explicitly labelled hypotheses. The quantum
entry excludes amplitudes, phase, entanglement, and general unitary evolution
from the CM claim.

## Same-day use-case audit and benchmark research

All eight analyses received a second field-specific audit. The revised page
now distinguishes a natural pain point, a bounded CM role, the incumbent
methods, the semantics CM must not flatten, real datasets or executable
fixtures, synthetic demonstration design, artifact-equivalent baselines,
separate benchmark tasks, and a predeclared dominance gate.

The resulting priority is intentionally uneven:

1. configuration/product-family histories, security-policy version audit, and
   hardware design histories are Tier A;
2. pure-Boolean compiler predicates are Tier A/B with explicit refusals for
   integer, memory, undefined-behaviour, and interprocedural semantics;
3. AI-agent authorization, biological update rules, and regulated Boolean
   decision tables are Tier B conditional subsets; and
4. quantum support remains Tier C classical reversible/control logic only.

The source investigation identified primary public candidates including the
EPFL circuit suite, Cedar example and integration fixtures, FeatureIDE/FeatJAR
and torte histories, Alive2/LLVM tests, Biodivine Boolean Models, RevLib/MQT
Bench, the DMN TCK, and OpenFisca packages. No third-party corpus was downloaded
or redistributed. URLs, intended use, baseline choices, and scope rules are
recorded in `use_case_benchmarks_2026-08-27/CM-USE-CASE-BENCHMARK-CATALOG.json`;
the human-readable rationale is in
`CM_USE_CASE_BENCHMARK_RESEARCH_2026-08-27.md`.

The dependency-free generator creates 48 self-checking cases across eight
JSONL suites. Each case contains a base Boolean DAG, an equivalent structural
rewrite, a localized behaviour-changing edit, four partial-context levels,
one or more roots, and exact little-endian packed truth bits. The seed,
convention, file hashes, and synthetic-only boundary are captured in the
generated manifest and checksum file. Synthetic results must always be
reported separately: a stress-suite win demonstrates a mechanism, not domain
dominance.

## Ranked remaining evidence gaps

1. **Real workload reuse and economics (decisive):** obtain an owner-approved,
   scrubbed metrics trace and measure actual reuse counts, context change, cache
   hit rates, and preparation amortisation. The validated template is not a
   captured workload.
2. **Temporary-memory policy (safety):** replace or calibrate the non-conservative
   estimator on representative dense cases before approving a default policy;
   keep the existing typed pre-materialisation refusal.
3. **Native backend feasibility (performance):** obtain explicit approval for
   the pinned dependency build path, then separately test installation,
   correctness, restriction/query/extraction boundaries, and representative
   performance. No native speed conclusion is currently supported.
4. **Representative DP-R3 timing (reliability):** if performance attribution is
   required, run a preregistered representative study; the tiny smoke supports
   exactness and integration only.
5. **Canonicality theorem or collision analysis (semantics):** current keys are
   documented engineering identity. A claim of global semantic canonicality
   still requires a formal statement and proof, or a bounded empirical
   collision study with an explicit scope.

## Preservation and external effects

The pre-existing excluded local paths and artifacts listed in
`PREREGISTRATION.md` were not read, modified, staged, deleted, or attributed to
this audit. No dependency was installed and no third-party corpus was
downloaded. No commit, push, deployment, publication, upload, cloud run,
email, or other external write was performed.
