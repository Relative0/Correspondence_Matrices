# CM hardware-revision feasibility result

Date: 2026-09-04

Decision: **stop; the frozen natural-history corpus is not admissible for a changed-cone timing experiment**

Scope: exact, non-neural source/activation feasibility only

## Result

The [preregistered protocol](CM_HARDWARE_REVISION_FEASIBILITY_PROTOCOL_2026_09_04.md)
mechanically sampled 12 first-parent, non-merge, HDL-touching transitions from each of
four public hardware repositories. All four repositories passed the frozen origin,
branch, history, and permissive-license checks. The resulting 48-transition audit was
then replayed offline from cached Git objects.

The replay passed: all 48 transitions, source hashes, selections, and metrics matched,
and the summary reproduced exactly. The frozen admission decision nevertheless remains
`insufficient_activation_or_provenance` because the trace failed its activation and
parser-coverage requirements.

| Frozen measure | Observed | Required | Decision |
| --- | ---: | ---: | --- |
| provenance-admitted repositories | 4/4 | at least 3/4 | pass |
| admitted confirmation repositories | 2/2 | 2/2 | pass |
| selected transitions per confirmation repository | 12 each | at least 6 each | pass |
| confirmation transitions with changed stable seeds | SERV 2; PicoRV32 3 | at least 4 each | fail |
| confirmation changed stable seeds | SERV 4; PicoRV32 3 | at least 16 each | fail |
| confirmation changed/comparable stable seeds | 7/670 (1.04%) | 20% to 90% | fail |
| admitted/discovered driver regions | 11,912/18,728 (63.61%) | at least 70% | fail |
| independent replay mismatches | 0 | 0 | pass |

The development histories were more active: `verilog-axi` changed 134 of 1,443
comparable stable seeds across three transitions, and Ibex changed 414 of 3,057 across
eight. Those observations cannot replace the frozen confirmation result, change the
split, or justify selecting favorable transitions after seeing the data.

## Evidence boundary

The measured regions are conservative, pre-synthesis **source cone seeds**, not
elaborated or synthesized netlist cones. This phase did not run Yosys, benchmark CM or
CSE-flat, measure speed or memory, train a selector, modify routing, or use RunPod. It
therefore supports no architecture-speed claim and no website benchmark-number change.

The exact artifacts are in
[`verification/hardware-revision-feasibility-retry-002-2026-09-04`](verification/hardware-revision-feasibility-retry-002-2026-09-04/):

- `MANIFEST.json` binds the audit to source revision `64d8f9f9b4507ee04804b332df7ad48ef87af154`,
  the frozen cutoff, candidate set, tool identities, and program hashes;
- `AUDIT.json` retains all selected transitions, including zero-change cases;
- `SUMMARY.json` records every frozen gate condition;
- `INDEPENDENT_VERIFICATION.json` records the successful 48-transition offline replay;
- `INVENTORY.json` and `CHECKSUMS.sha256` make the evidence set auditable.

## Disposition and next legitimate step

This H9 attempt is closed as negative evidence. Do not progress this corpus to
synthesis, timing, optimization, or remote replication.

A further H9 attempt, if desired, must be a distinct preregistered corpus phase. It may
use non-performance metadata to identify histories whose unit of sampling is an actual
HDL-behavior change (for example path-qualified RTL histories or issue/PR-linked fixes),
but it must freeze that rule, repositories, split, cutoff, and stop criteria before
examining CM performance. It must retain inactive and refused cases and may not
retroactively cherry-pick the active development transitions from this phase. Only a
new source trace that passes activation and provenance should proceed to a separately
frozen Yosys correctness gate.
