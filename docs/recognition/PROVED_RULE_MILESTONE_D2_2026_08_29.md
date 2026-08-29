# CRSE Milestone D2: proved metavariable rule reuse

Date: 2026-08-29

Retained run: `docs/recognition/runs/rule-20260829-002`

Independent verification: `docs/recognition/verification/rule-20260829-002.json` (`pass`)

## Result

Milestone D2 proves one Boolean motif once, loads the proof as bounded inert
JSON, selects a fixed compiled structural matcher, and reuses that proof across
repeated applications. The rule is:

```text
NOT(NOT(A AND NOT B) AND NOT(NOT A AND B)) -> A XOR B
```

The exhaustive proof covers all four values of the two Boolean metavariables.
This is universal for pure total Boolean subexpressions because every occurrence
of `A` or `B` evaluates to one of those two values for any enclosing assignment.
The matcher separately enforces that each repeated metavariable occurrence is
structurally identical. Commutative `AND` arrangements are accepted; near
matches with a changed repeated binding are rejected.

The proof artifact cannot supply code, class names, paths, or expressions to
execute. Strict schema, rule ID, truth rows, and hashes select one built-in
matcher. Rewriting walks the admitted identity DAG bottom-up and preserves
sharing.

## Comparative computation

Each timed arm starts from the expression, optionally rewrites it, then builds
and executes the CSE backend for a complete eight-variable output. The
`instance_cm_proof` arm uses the same structural detector but constructs and
compares the source and candidate dense exact correspondence matrices at every
proposed site. An independent scalar enumerator audits every result outside the
timer.

| Batch | Applications | Warm compiled total | Per-instance CM total | Compiled speedup vs CM | Compiled speed vs no rewrite |
| --- | ---: | ---: | ---: | ---: | ---: |
| Generated, q=1 | 1 | 0.377 ms | 1.099 ms | 2.914x | 0.430x |
| Generated, q=8 | 8 | 2.972 ms | 6.788 ms | 2.284x | 0.422x |
| Generated, q=32 | 32 | 11.762 ms | 28.456 ms | 2.419x | 0.411x |
| Generated, q=128 | 128 | 44.971 ms | 94.042 ms | 2.091x | 0.415x |
| EPFL D, 12 cones | 5 | 15.241 ms | 17.838 ms | 1.170x | 0.364x |

The one-time proof plus compile cost was 0.469 ms on this machine. Median saved
rewrite time was 0.483 ms per generated application, giving an observed
one-application break-even against repeating the explicit CM proof. A cold
proof-artifact load was effectively even at q=1 (1.018x) and clearly ahead at
q=8 and above (1.648–2.282x).

This answers the narrow reuse question: a proof over metavariables can replace
per-instance dense-CM proof cheaply and exactly. It does **not** yet make the
rewrite profitable versus doing nothing. The no-rewrite CSE arm was 2.33–2.43x
faster on generated batches and 2.75x faster on the EPFL batch.
The current CSE path already handles these small structures efficiently, so the
matcher cost exceeds the downstream saving. No production rewrite is promoted.

## Natural hardware evaluation

EPFL stands for **École polytechnique fédérale de Lausanne**, described in
English as the Swiss Federal Institute of Technology in Lausanne. The retained
EPFL data are provenance-reviewed eight-variable cones derived from its public
logic-synthesis benchmark collection; they are evaluation-only and never enter
training, fitting, or rule construction.

The matcher found five internal sites in two of 12 cones:

- `epfl-arithmetic-hyp-internal212060-c28ab69616`: 3 applications
- `epfl-arithmetic-multiplier-internal72-32d8a19161`: 2 applications

This is a real-source structural and end-to-end computation check, not a claim
about whole-circuit throughput. The earlier Milestone D task benchmark is also
real comparative computation: it measures construction and execution of
direct, CSE, CM-IR, and explicit dense-CM paths. The bounded cones simultaneously
validate the learning/reuse infrastructure before broader, independently
replicated comparisons.

## Safety and verification

- 60 timed cells completed; all outputs matched the independent scalar audit.
- 16 generated near-match controls produced zero false matches.
- 128 repeated generated applications and five EPFL applications were exact.
- The verifier reproduced the four proof rows, reloaded every expression,
  recomputed matcher decisions, checked all retained hashes, and audited all 60
  measurement rows.
- The retained run is single-machine, three-round bounded evidence. It does not
  establish cross-machine timing, a general rule language, learned rule
  discovery, or production profitability.

## Next experiment

Use the proved-rule boundary in a finite version/reuse workload where the same
motif appears across related DAG revisions. Compile a small fixed rule pack,
cache matches by structural identity, invalidate only changed cones, and compare
against fresh full-DAG matching, no rewrite, and per-instance CM proof. Keep the
exact output audit and charge cache identity/invalidation inside each arm.
