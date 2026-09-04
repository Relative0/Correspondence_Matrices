# CM hardware-revision feasibility protocol

Date frozen: 2026-09-04

Scope: exact, non-neural source/activation feasibility only

Status: candidate set, transition rule, split, and stop criteria frozen before inspecting
candidate commit diffs or running any CM timing

## Question

Can a deterministic sample of natural adjacent hardware revisions provide enough real,
stable changed regions to justify a later exact changed-cone CM experiment?

This phase does not benchmark CM, train a selector, alter production routing, update a
public speed claim, or authorize cloud execution. It may only admit or refuse a future
source-closed experiment.

## Candidate histories

The following repositories were selected from project identity, continuing public
maintenance, and repository-declared permissive license metadata before inspecting
their revision diffs:

| Role | Repository | Default branch | Declared license |
| --- | --- | --- | --- |
| development | `alexforencich/verilog-axi` | `master` | MIT |
| development | `lowRISC/ibex` | `master` | Apache-2.0 |
| confirmation | `olofk/serv` | `main` | ISC |
| confirmation | `YosysHQ/picorv32` | `main` | ISC |

The role split is the lexicographic first half versus second half of the frozen
repository slugs. A refused repository is retained as a refusal; it is not replaced
after activation is observed.

## Immutable history rule

- Cutoff: `2026-09-04T00:00:00Z`.
- Resolve the last default-branch commit at or before the cutoff and record its full SHA.
- Walk first-parent history from that commit.
- Exclude merge commits.
- Select the first 12 commits, newest first, whose parent-to-commit diff touches at least
  one `*.v`, `*.sv`, `*.vh`, or `*.svh` path.
- Each selected commit and its first parent form one transition. Do not hand-pick paths,
  commits, projects, or change sizes.
- Record fewer than 12 if the available first-parent history is exhausted. Never reach
  past the cutoff or substitute a different branch.

For every transition retain the commit/parent SHAs, author and commit timestamps,
subject, changed HDL paths, change status, byte hashes at both sides where present,
and added/deleted line counts. Non-HDL files are not inputs but their presence in the
commit is counted.

## Provenance and redistribution gate

Record the repository URL, default branch, immutable sampled-head SHA, license SPDX
identity, license-file path and SHA-256, clone command, Git version, and audit-program
SHA-256. The audit may cache Git objects under ignored project `tmp`; decision evidence
must contain no credentials, token-bearing URLs, Git config, or user-identifying paths.

A repository is refused if its declared license cannot be verified at the sampled head,
the selected branch/head cannot be resolved, required objects cannot be read, or its
license does not permit redistribution of the exact source excerpts needed by a later
experiment. Feasibility evidence records hashes and metrics only; source redistribution
is a separate later decision.

## Stable source-region identity

This phase deliberately does not call source text a synthesized cone. It computes
pre-synthesis *cone seeds* conservatively:

- module identity: repository + relative path + declared module name;
- driven-region identity: module identity + normalized driven identifier;
- eligible driver: a complete continuous `assign` statement whose left side resolves
  to one named signal, or a complete procedural assignment to one named signal inside
  an `always_comb`, `always @*`, or `always @(*)` block;
- normalized content: comments and insignificant whitespace removed, literals and
  operators retained, identifiers case-sensitive;
- ambiguity, macros crossing the region, generated names, multiple drivers, parse
  incompleteness, or an unstable/renamed path cause that region to be refused.

For a stable identity present on both sides, a changed normalized driver is an activated
seed; identical content is reusable; additions and removals are recorded separately and
are not mislabeled as stable reuse. A later timing protocol must replace this source
screen with elaborated Yosys cell/net cones and an independently checked cross-version
matching contract.

## Feasibility outputs

The audit must emit deterministic JSON containing:

- every candidate and refusal;
- every mechanically selected transition, including zero-change/refused transitions;
- file, module, and stable driven-region counts;
- unchanged, changed, added, removed, ambiguous, and refused seed counts;
- change fractions without timing or method results;
- development and confirmation summaries aggregated within repository first;
- tool identities, source hashes, inventory, and checksums.

A second verifier must recompute selection and all metrics from the cached Git objects
without trusting the summary.

## Frozen admission decision

The source trace is admissible for a later synthesis/correctness gate only if all are
true:

1. at least three of four repositories are provenance-admitted;
2. both confirmation repositories are provenance-admitted;
3. each confirmation repository supplies at least six mechanically selected transitions;
4. each confirmation repository has at least four transitions with one or more changed
   stable cone seeds;
5. each confirmation repository has at least 16 changed stable cone seeds in aggregate;
6. across confirmation repositories, at least 20% and at most 90% of comparable stable
   seeds change (a workload of almost all rebuilds is not an incremental trace);
7. at least 70% of all discovered driver regions are parsed to admitted stable identities;
8. the independent replay has zero selection, hash, and metric mismatches.

Any failed prerequisite stops the phase as `insufficient_activation_or_provenance`.
There is no timing fallback and no replacement repository.

## Next gate if admitted

Freeze a new protocol before synthesis or timing. It must bind a reproducible Yosys
version/container, elaboration scripts, stable cell/net/cone identity, exact earlier/
later/XOR artifacts, direct oracle, cold CM, current persistent CM, research incremental
CM, CSE-flat and raw-flat arms, complete cost accounting, memory ceilings, history-
clustered inference, and local promotion criteria. RunPod remains unauthorized unless
that later local gate passes every frozen criterion and an exact paid-run request is
separately approved.
