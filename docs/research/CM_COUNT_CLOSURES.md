# Projected counts and historical evidence

The September 12 count-closure study continues the application evidence release.
Read `docs/audits/2026-09-12-cm-count-closures/REPORT.md` for measured outcomes,
limits, independently checked counts and the full historical regression result.

`cmbench.comparative.component_counts.count_components` is an opt-in research
counter. It accepts signed one-based CNF literals, zero-based selected indices
and fixed `x0`, `x1`, ... assignments. It splits residual formulas using every
variable, including hidden variables; selected decisions add disjoint counts,
while hidden-only decisions use existential OR. Unconstrained selected axes
contribute their exact power of two. A fresh memo table is created per request.
Explicit node, work, depth, input and cache limits bound the computation. A
refusal never returns a partial count. No production default is changed.

The d4 adapter uses an immutable upstream binary and integer projected counting.
A fresh forced-true selected sentinel makes an empty projection unambiguous for
that binary. Exhaustive controls precede real queries. Deadlines and memory caps
for each attempt are preserved in its protocol; extending them does not establish
a speedup against earlier runs.

For the additional historical public CNF fixtures, run inside the research replay:

```text
python -B scripts/restore_cm_historical_fixtures.py --restore
python -B scripts/restore_cm_application_fixtures.py --restore --download-d4
python -B scripts/restore_cm_closure_fixtures.py --restore --download --output closure-fixtures.json
```

The last command restores 46 CNFs from pinned d4/d4v2 revisions, only when they
match the original P6 freeze. It also recreates the recorded empty directory of a
historical preflight refusal, which Git cannot preserve as an empty directory.
It refuses differing existing files or a nonempty historical output directory.
It neither executes an old cloud controller nor consumes an old authorization.

Three separately restored tracked receipt/data files have their original exact
CRLF bytes protected by path-specific Git attributes. No historical expected hash
is rewritten. The former EPFL origin discrepancy was a comparison error: its
upstream blob itself uses CRLF, and the retained file is already byte-identical.

The actual video-production capture remains documented in
`docs/research/CM_APPLICATION_RESEARCH.md`. Run it only as part of an independently
needed render. Presentation formatter calls are not evidence of backend demand.
