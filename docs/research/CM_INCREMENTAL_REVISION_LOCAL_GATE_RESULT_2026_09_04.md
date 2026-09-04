# CM incremental-revision local gate result

Date: 2026-09-04

Scope: exact, non-neural compilation across cached natural feature-model transitions

Status: source-closed local gate completed; radix prototype not promoted; no RunPod follow-up

## Decision

Keep the current persistent CM cache and stop the digest-radix incremental prototype.
The prototype reused unchanged regions and was much faster than cold CM compilation,
but it was slower than the existing persistent cache, retained substantially more
Python-owned memory, and did not approach CSE-flat end-to-end. The frozen confirmation
cohort also failed the prerequisite workload-activation gate because only three of 42
cases had any normalized-clause change, all from the Linux history.

This is a negative promotion decision, not evidence that incremental CM compilation
cannot help a better-activated revision workload. No selector, production default,
neural component, website claim, or cloud execution is authorized by this result.

## Source-closed execution

The decision-bearing retry 003 ran from implementation commit
`e64e451fdfb6095509fc7ee4ec68a11406fba6c6` on Windows with Python 3.13.5 / MSVC
runtime identity. It used all 120 frozen cases: 20 admitted adjacent transitions,
three widths (`k=8,12,16`), and two slice rules. Transition labels fixed 78
development cases and 42 `last`-transition confirmation cases before timing.

Five counter-rotated rounds across five arms produced 3,000 rows. Every arm returned
the complete earlier vector, later vector, and XOR vector. The in-run replay and the
separate verifier found zero mismatches. The separate verifier also reconstructed all
120 artifacts directly from the unnormalized stored CNFs and checked three saved
SHA-256 values per case.

Evidence:

- [manifest](verification/incremental-revision-local-gate-retry-003-2026-09-04/MANIFEST.json)
- [summary](verification/incremental-revision-local-gate-retry-003-2026-09-04/SUMMARY.json)
- [independent verification](verification/incremental-revision-local-gate-retry-003-2026-09-04/INDEPENDENT_VERIFICATION.json)
- [raw rows](verification/incremental-revision-local-gate-retry-003-2026-09-04/RAW.jsonl)
- [checksums](verification/incremental-revision-local-gate-retry-003-2026-09-04/CHECKSUMS.sha256)

Earlier executions used the same frozen schedule before the implementation and gate
checks were fully source-closed. They are development-only and are excluded from every
decision and ratio reported here.

## Confirmation result

Ratios below are case medians aggregated first within history and then equally across
seven histories. Intervals are the frozen 4,000-draw history bootstrap. A ratio below
1.0 favors the numerator.

| Comparison | Geometric mean | 95% history interval | Disposition |
| --- | ---: | ---: | --- |
| Incremental update / cold CM update | 0.442x | 0.385x–0.514x | Passed the construction-only threshold |
| Current persistent CM update / cold CM update | 0.400x | 0.352x–0.485x | Existing cache was faster than the prototype |
| Incremental update / current persistent CM update | 1.104x | 0.969x–1.264x | Failed the current-cache gate |
| Incremental retained bytes / current persistent retained bytes | 1.678x | 1.513x–1.865x | Failed: worst case was 3.793x versus the 1.25x ceiling |
| Incremental total / CSE-flat total, q1 | 2.875x | 2.788x–2.979x | Failed task-control gate |
| Incremental total / CSE-flat total, q64 | 1.459x | 1.397x–1.530x | No break-even through q64 |
| Current persistent CM total / CSE-flat total, q1 | 2.547x | 2.413x–2.740x | CSE-flat remained faster |
| Current persistent CM total / CSE-flat total, q64 | 1.338x | 1.277x–1.406x | CSE-flat remained faster |

The q values charge the measured two-version resident construction once and the
measured pair evaluation q times. They do not use an output cache. They are a bounded
amortization diagnostic, not a natural request trace.

## Activation and invalidation

Source-clause occurrences changed in 13 of 42 confirmation cases, but normalization
reduced those edits to a changed canonical clause set in only three cases. All three
were Linux cases; BusyBox, Fiasco, FinancialServices01, automotive2, Soletta, and
uClibc had zero normalized changes in their six confirmation cells each. Across the
development split, only eight of 78 cases changed after normalization.

The distinction matters. These are small conditioned neighborhoods around joint
satisfying products. Large upstream model revisions can disappear after conditioning,
or reduce to clause reordering, repeated units, and duplicate occurrences. The corpus
is real, but this bounded projection is not an adequate general incremental-
compilation workload.

The prototype still recorded reuse in every confirmation history and its source
identity changed exactly when the normalized clause set changed. Those checks show
that the bounded LRU and invalidation contract work. They do not rescue the failed
activation, memory, existing-cache, or CSE-flat gates.

The only changed confirmation history, Linux, had an incremental/current-persistent
update ratio of 0.842x. That is hypothesis-generating evidence for a future workload
with real changed regions; it cannot be promoted from one history after the aggregate
gate failed.

## Architecture disposition

- The prototype remains research-only and is not connected to production entry
  points or routing.
- The current association-preserving persistent CM cache remains the best verified CM
  compilation choice for these cases.
- CSE-flat remains the best tested end-to-end arm for the required two-vector/XOR
  artifact through q64.
- H2 compact-key and H3 dense-layout work remain deferred: this experiment did not
  identify either as the limiting end-to-end cost.
- No RunPod replication is justified for a locally slower, higher-memory prototype on
  a confirmation cohort that failed workload activation.

## Next admissible H9 experiment

A separately frozen
[hardware-revision feasibility audit](CM_HARDWARE_REVISION_FEASIBILITY_RESULT_2026_09_04.md)
tested this direction with 48 natural transitions from four public repositories. It
also stopped: the two held-out histories changed only 7/670 comparable stable source
seeds (1.04%), and overall source-driver parse coverage was 63.61%. These were
pre-synthesis source seeds rather than synthesized cones, so the failed activation gate
does not support proceeding to Yosys or timing on that corpus.

A future experiment must start with another source-closed, preregistered trace whose
confirmation partition contains actual normalized changed regions across several
independent histories. Full rebuild, the current persistent CM cache, structural-CSE,
and the incremental prototype must still return the same declared artifact and charge
parsing, matching, invalidation, compilation, lowering, evaluation, delivery, and
retained state.

Do not select transitions after looking for CM wins. Freeze an activation rule before
timing, retain zero-change/refused cases, and stop locally again unless the new trace
beats the current persistent cache and the task-matched control with acceptable memory.
