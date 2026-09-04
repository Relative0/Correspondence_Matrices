# Correspondence Matrices: research library

Read the material directly on GitHub, or download it to inspect the
interactive explainer, raw measurements, source snapshots and tests locally.
This library integrates the project's August 27–September 3, 2026 follow-up work.
Evidence boundaries and unsuccessful experiments are retained.

Latest exact-execution and comparison decision:
[C38 Linux/GCC replication](CM_C38_LINUX_GCC_NATIVE_REPLICATION_2026_09_03.md), the
[four-lane local functional admission](CM_FOUR_LANE_COMPARISON_HARNESS_FUNCTIONAL_ADMISSION_2026_09_03.md),
and the cross-machine q1/q4/q16/q64 architecture ladder now summarized on the expert
page as a task map.
The [architecture-audit disposition](CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md)
records which H0-H10 recommendations were implemented, rejected, or deferred and why.
C38 confirmed exact native execution and aggregate/multi-root benefit on Linux, but its
0.840x minimum single-root case failed the frozen 0.95x floor, so native remains
guarded/opt-in. The new four-lane harness then matched exact artifacts across complete
relations, repeated restrictions, related roots, and separate smaller-query/persistence
sublanes. The later timing campaigns retained direct BitSet, CSE-flat and natural
smaller-query controls, and the public page preserves both favorable and unfavorable
results rather than promoting a universal CM backend. Training and production
promotion remain disabled; the website changes are published only through the reviewed
branch workflow.

Latest comparative follow-up: [fresh-process structural persistence](FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md).
CM, structural CSE, direct CNF and a portable `dd.autoref` ROBDD control passed
256/256 counterbalanced cells using 512 distinct within-cell supervised build
and reload/query processes, producing 512 exact relation rows. Native CUDD BDD,
CUDD ZDD and d4 d-DNNF persistence remain explicit admission refusals. The
preceding [persistence and trace-provenance work](PERSISTENCE-AND-TRACE-PROGRESS-2026-08-29.md)
records 48 generated task controls and zero observed natural traces.
A bounded public-source search found useful PROFilE endpoint configurations,
but not ordered user-event sessions; its non-commercial datasets are linked,
not redistributed. These are correctness and provenance results, not a
performance, memory, full-model or independent-replication claim.

Earlier rewrite-recognition follow-up: [Milestone D9 frozen calibrated profitability policy](../recognition/NATURAL_PROFITABILITY_POLICY_MILESTONE_D9_2026_08_29.md).
The leakage-controlled policy was exact on 501 measurements from 23 optimized
BLIF cones, but found no profitable rewrite region. It abstained on all 33 sealed
evaluation workloads; unconditional one pass measured 0.429x and the charged
gate measured 0.982x versus no rewrite. This is a retained negative result from
a circuit-disjoint split within EPFL, not independent benchmark-family evidence.

Latest local follow-up: [matched sessions and version-change contracts](SESSION-AND-VERSION-CONTRACT-PROGRESS-2026-08-28.md):
208/208 comparison cells passed, plus a separate 16/16-cell known-change
control, using CM, structural CSE, direct CNF and native CaDiCaL with fresh
and reused representations. The final focused check passed 206 tests.
All seven automatically selected real slices had zero version change; the
separate Soletta control correctly identified two changed assignments.
These are correctness results, not a performance ranking. CUDD/ZDD/d4 remain
unexecuted in this follow-up. See also the preceding
[process/native controls](PROCESS-AND-NATIVE-CONTRACT-PROGRESS-2026-08-28.md)
and [v2 reproducibility work](REPRODUCIBILITY-AND-CONTRACT-PROGRESS-2026-08-28.md).
The downloadable August 28 snapshot remains pinned to its original source
commit and does not contain these later changes. The new results are linked
as Markdown and raw evidence here; the interactive HTML has not been rebuilt
for this continuation.

## Start reading

| Reader | What it covers |
| --- | --- |
| [Simple One-Pager](readers/SIMPLE-ONE-PAGER.md) | The idea, suitable problems and important limits, in plain language. |
| [Technical Summary](readers/TECHNICAL-SUMMARY.md) | Representation, output contracts, comparison rules and remaining work. |
| [CM Use Cases](readers/CM-USE-CASES.md) | All eight fields: pain points, proposed CM roles, incumbents, real datasets, synthetic scenarios and success criteria. |
| [Master Explainer](readers/MASTER-EXPLAINER.md) | The full authored knowledge-base content, including corrections and number provenance. |
| [Verified Runpod smoke](readers/RUNPOD-MEMORY-SMOKE.md) | Executed results, memory findings, cleanup and remaining measurement gaps. |
| [Runpod setup and handoff](readers/RUNPOD-SETUP.md) | Working configuration and distinctions between historical workflows; no credentials. |
| [Fresh-process persistence](FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md) | Frozen CM/CSE/direct-CNF/portable-ROBDD build-and-reload evidence, native admission refusals and exact measurement boundaries. |
| [Structural persistence and trace provenance](PERSISTENCE-AND-TRACE-PROGRESS-2026-08-29.md) | Frozen CM/CSE/direct-CNF structural reload evidence, exact claim boundaries and the natural-session admission contract. |
| [D9 frozen profitability policy](../recognition/NATURAL_PROFITABILITY_POLICY_MILESTONE_D9_2026_08_29.md) | Exact calibrated abstention on optimized BLIF plus the retained negative timing result. |

The generated Markdown readers do not require JavaScript. They are reading
editions, not screenshots or pixel-identical copies of the interactive pages.
Use the downloaded HTML for charts, controls and progressive disclosure.

## Download and view the interactive explainer

- [Download the research snapshot ZIP](https://github.com/Relative0/Correspondence_Matrices/blob/main/docs/research/downloads/CM-Research-2026-08-28.zip?raw=true).
- [Snapshot identity and checksums](https://github.com/Relative0/Correspondence_Matrices/blob/main/docs/research/downloads/README.md).
- [Download the latest complete repository](https://github.com/Relative0/Correspondence_Matrices/archive/refs/heads/main.zip).

Extract the ZIP fully, then open:

```text
Correspondence-Matrices-research-2026-08-28/deliverables_n22_24/master_explainer_2026_08_03/index.html
```

The same directory contains `layperson.html`, `expert.html`, `usecases.html`
and `feature-model-evidence.html`. Open them in a normal browser after
extraction; GitHub's source-file viewer is not the interactive website.
The site displays saved evidence and does not launch paid tests.

Some frozen source snapshots have long filenames. On Windows, extract to a
short directory with a long-path-capable extractor; Python's built-in
extractor is one option:

```powershell
python -m zipfile -e CM-Research-2026-08-28.zip C:\CM
```

For a Git checkout, use `git -c core.longpaths=true clone` with the repository
URL and a short destination. This flag applies to that command, not a global
Git setting. Scientific source snapshots have deliberately not been renamed.

The snapshot preserves repository-relative paths. Its manifest provides
per-file SHA-256 hashes, while the download page records the archive hash
and exact source commit. The branch ZIP is a moving snapshot; use the
commit-pinned download for a reproducible version.
[GitHub's archive documentation](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives).

## What has actually been measured?

| Evidence | Verified scope | What it does not establish |
| --- | --- | --- |
| [Feature-model evidence and independence audit](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-INDEPENDENCE-AUDIT-2026-08-27.md) | Bounded real-model slices, native CUDD and other representation results, version-delta and artifact audits. | Full-model superiority, independent third-party replication, or repaired cold/warm, memory and serialization comparisons. |
| [Measurement-repair protocol](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-MEASUREMENT-RERUN-PROTOCOL-2026-08-28.md) | A specified protocol and a separate 28-cell local functional pilot. | Execution of the complete repaired benchmark campaign. |
| [Matched session/version correctness](SESSION-AND-VERSION-CONTRACT-PROGRESS-2026-08-28.md) | Fresh/reused CM, CSE, direct CNF and native SAT agree on bounded partial configurations and complete version deltas; 208 main cells and 16 separate positive-control cells passed. | Speed or memory superiority, representative nonzero-change coverage, unknown-version online ingestion, or complete measurement repair. |
| [EPFL context pilot](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/HARDWARE-EPFL-CONTEXT-PILOT-RESULTS.md) | A published hardware-expression adjacency and bounded context tests. | A deployed design workflow or whole-chip scalability. |
| [Runpod memory smoke](readers/RUNPOD-MEMORY-SMOKE.md) | 70 passing focused tests; 312 successful rows, including 72 comparable representation calls; verified pod deletion. | Real-world workload performance, full estimator calibration, or production acceptance. |
| [Structural persistence pilot](PERSISTENCE-AND-TRACE-PROGRESS-2026-08-29.md) | CM/CSE/direct-CNF structures reload to exact bounded relations in 144/144 cells; generated and natural trace provenance are mechanically separated. | Native-backend persistence, timing/RSS/file-size rankings, natural user traces, full models or external replication. |
| [Fresh-process persistence pilot](FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md) | CM/CSE/direct-CNF/portable-ROBDD structures were built and reloaded in different owned processes in 256/256 cells; all 512 relation rows and independent structure replays were exact. | Native CUDD/ZDD/d4 persistence, Linux process-tree RSS, performance or broad size rankings, full models or external replication. |

In the memory smoke, the old estimate was too low in 66/72 comparable
calls. The candidate covered all 72 but sometimes overestimated by about
185×. Those are traced-memory estimates on small synthetic cases—not CM
speedups. The candidate remains diagnostic, not production-approved.

## Datasets, protocols and raw results

- [Eight-field benchmark research](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CM_USE_CASE_BENCHMARK_RESEARCH_2026-08-27.md)
  and [machine-readable dataset catalog](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CM-USE-CASE-BENCHMARK-CATALOG.json).
- [Feature-model representation battery](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-REPRESENTATION-BATTERY-RESULTS.md)
  and [history shootout protocol](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-HISTORY-SHOOTOUT-PROTOCOL.md).
- [Benchmark run directories](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs)
  and [independence-audit artifacts](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27).
- [Successful cloud-smoke raw evidence](../audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/http-ephemeral-execute-001/evidence/run-output)
  and [campaign continuation, including failed attempts](../audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/RUNPOD-CONTINUATION-20260828.md).
- [Fresh-process persistence raw evidence](verification/fresh-process-persistence-v2-2026-08-29),
  including the frozen plan, append-only ledger, 256 downloadable artifacts,
  source snapshot and [attempt receipt](verification/fresh-process-persistence-attempts-2026-08-29.json).
- [Memory estimator model](../audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/MEMORY-ESTIMATOR-MODEL.md),
  [preregistration](../audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/PREREGISTRATION.md)
  and [local verification continuation](../audits/CM-VERIFICATION-CONTINUATION-2026-08-28.md).

Dataset references are leads for reproductions, not claims that every
dataset has been benchmarked. Acquisition, subset selection, semantics,
license and exclusion rules remain part of each protocol. Upstream corpora
and libraries retain their own licenses; this package grants no new rights
to third-party data. External repository clones, credentials and installed
dependencies are not bundled. See [publication notes](PUBLICATION-NOTES.md).

## Reproduce the documentation and checks

From the repository root, with the project's dependencies available:

```powershell
python -B deliverables_n22_24/master_explainer_2026_08_03/cm_master_build_2026_08_03.py
python -B scripts/cm_research_publication.py readers
python -B scripts/cm_research_publication.py readers --check
python -B scripts/cm_comparative_fresh_persistence_pilot.py verify --output docs/research/verification/fresh-process-persistence-v2-2026-08-29
python -B -m unittest discover -s tests -p 'test_cm_research_publication.py'
python -B -m unittest discover -s tests -p '*website.py'
python -B -m unittest discover -s tests -p 'test_cm_runpod_*.py'
```

Reading, rebuilding documentation and running the fake-client tests do not
start cloud resources. Historical cloud controllers are provenance, not
reusable launch commands: their one-shot authorizations are consumed.
