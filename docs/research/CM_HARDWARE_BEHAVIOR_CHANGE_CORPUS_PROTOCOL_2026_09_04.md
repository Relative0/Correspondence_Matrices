# CM hardware behavior-change corpus protocol

Date frozen: 2026-09-04

Scope: exact, non-neural source/activation feasibility only

Status: candidate set, production-path rules, selection screen, split, scan bound, and
stop criteria frozen before inspecting any confirmation-repository revision diff or
historical blob

## Question and prior evidence

Can a deterministic sample whose unit of selection is a stable, normalized production-
RTL driver change provide enough real changed and reusable source regions to justify a
separate elaborated-Yosys correctness experiment?

Two prior stop decisions are binding. The natural feature-model trace inadequately
activated after normalization and its incremental prototype lost to the current
persistent CM cache and CSE-flat. The first hardware-history audit independently
replayed 48 transitions, but its held-out histories changed only 7/670 comparable
stable source drivers (1.04%) and overall parser coverage was 63.61%. Neither corpus may
be timed again or used for a performance claim.

This phase measures no CM, CSE, raw-flat, query, timing, memory, neural, or routing
outcome. Its source regions are **pre-synthesis driver regions**, not elaborated nets or
synthesized cones. It may only admit or refuse a later Yosys correctness gate.

## Candidate histories and frozen split

The two development histories are the previously exposed development projects. Their
prior evidence was used to calibrate this source screen. The confirmation projects were
selected from project identity, active public maintenance, different upstream
organizations, synthesizable HDL availability, and primary repository license/default-
branch metadata. Before this freeze, only confirmation repository metadata and the
current path layout were inspected; no confirmation commit list, revision diff,
historical source blob, or activation result was opened.

| Role | Repository | Branch | Production HDL path rule | Expected license |
| --- | --- | --- | --- | --- |
| development | `alexforencich/verilog-axi` | `master` | path starts `rtl/` | MIT |
| development | `lowRISC/ibex` | `master` | path starts `rtl/` | Apache-2.0 |
| confirmation | `black-parrot/black-parrot` | `master` | first component is `bp_be`, `bp_common`, `bp_fe`, `bp_me`, or `bp_top`, followed by `src/` | BSD-3-Clause |
| confirmation | `ultraembedded/riscv` | `master` | path starts `core/riscv/` | BSD-3-Clause |

All paths must also end in `.v`, `.sv`, `.vh`, or `.svh`, compared case-insensitively.
Test, trace/simulation, formal, examples, vendored/external, wrappers, and system-level
integration paths outside the table are excluded by construction. Subjects, authors,
issue labels, PR labels, stars, and timing are never selection predicates.

A repository that fails is retained as a refusal and is not replaced. A confirmation
project or transition from the prior hardware audit cannot be substituted after the
new confirmation data are observed.

## Development-only calibration record

The rule below was prototyped only on the two exposed development histories with the
same cutoff. Targeting 16 qualifying transitions, `verilog-axi` found 16 after 77
screened commits: 1,324/4,032 comparable drivers changed (32.84%) and selected-path
parse coverage was 93.05%. Ibex found 16 after 53 screened commits: 664/3,973 changed
(16.71%) and parse coverage was 65.88%.

These values justify a maximum scan of 160, a 12-transition target, the 60% per-
confirmation parse floor, and the 1% lower change-fraction floor. They are calibration,
not confirmation evidence. The exploratory script under ignored project `tmp` is not a
decision program and will not be included in the evidence artifact.

## Immutable history and scan rule

- Cutoff: `2026-09-04T00:00:00Z`.
- Resolve the last default-branch first-parent commit at or before the cutoff and record
  its full SHA.
- Walk first-parent history newest to oldest and exclude merge commits.
- Screen at most the first 160 non-merge commits that have a parent. Stop earlier only
  after selecting 12 qualifying transitions.
- For every scanned commit, retain its SHA, parent, author/commit timestamps, subject,
  complete changed-path count, eligible production-HDL changes, and a deterministic
  selection or refusal reason.
- Never skip a qualifying transition, reach past the scan bound/cutoff, hand-pick a
  path or commit, follow a non-first parent, replace a repository, or use commit-message
  language as a filter.

Renames, additions, and deletions are recorded but cannot establish stable reuse.
Line-count and blob/hash records are retained for every eligible path. Non-production
and non-HDL files are counted but their content is not read by the audit.

## Conservative stable driver screen

Module identity is repository + stable relative path + declared module name. Driver
identity appends one simple driven identifier. Parse only:

- a complete continuous `assign` statement whose left side is one named signal,
  optionally with one packed or unpacked index; or
- assignments to one named signal inside a complete `always`, `always_comb`,
  `always_ff`, or `always_latch` statement/block.

Strip comments while preserving quoted strings and newlines, then remove insignificant
whitespace before hashing the complete driver statement/block. Literals, identifiers,
operators, sensitivity lists, and control structure remain significant. A driver is
refused on invalid UTF-8, missing/unterminated module or block, macros crossing its
region, generate scope, complex/concatenated left side, unstable path/module identity,
or more than one candidate region for the same identity. Sequential and combinational
regions use the same identity rules; the audit does not infer clock semantics.

For a stable identity present on both sides, unequal normalized hashes are a changed
driver and equal hashes are reusable. Additions/removals remain separate. A transition
qualifies if all are true:

1. at least one stable comparable driver changed;
2. at least one stable comparable driver remained unchanged; and
3. no more than 90% of its comparable stable drivers changed.

The third condition excludes near-total source rebuilds from an incremental-reuse
corpus. It is not a CM-favorability test. Every nonqualifying scanned commit and exact
reason remains in the evidence.

## Provenance and deterministic evidence

Bind exact public origin URL, branch, sampled head, cutoff, license identity/file/hash,
Git version, clone command, audit and verifier hashes, interpreter/platform, production-
path rule, and every source blob Git OID/SHA-256. Accepted license text must be verified
from the sampled head. Evidence contains hashes and metrics, not upstream source text,
credentials, token-bearing URLs, Git config, or local user paths.

Emit deterministic JSON for all repositories, all scanned commits through the stopping
point, every selection/refusal, every eligible path and source-side parse count, selected
transition driver identities/counts, per-history summaries, manifest, inventory, and
checksums. A separate verifier must disable lazy fetch and recompute the entire audit
from cached Git objects without trusting the saved summary.

## Frozen admission decision

The corpus is admissible for a separate Yosys correctness protocol only if every
condition is true:

1. all four repositories pass exact origin, branch/head, readable-object, and sampled-
   head license checks;
2. each confirmation repository supplies at least 8 mechanically selected transitions
   within the 160-commit scan bound;
3. every selected confirmation transition has both changed and unchanged stable drivers
   (an invariant of the frozen selector);
4. each confirmation repository has at least 8 changed and at least 8 unchanged stable
   driver identities in aggregate;
5. each confirmation repository spans at least 4 distinct stable production source
   paths and at least 4 distinct declared module identities among its selected changes;
6. across confirmation repositories, changed/comparable stable drivers are at least 1%
   and at most 80%;
7. admitted/discovered driver-region parse coverage is at least 60% separately in each
   confirmation repository and at least 65% across all four histories; and
8. offline replay has zero selection, source-hash, license, count, identity, and summary
   mismatches.

Any failed condition stops the phase as `insufficient_behavior_change_or_provenance`.
There is no timing fallback, threshold revision, repository replacement, or favorable-
development substitution after confirmation is opened.

## Next gate if admitted

Admission permits only a new, committed Yosys correctness protocol. Before any
elaboration, that protocol must pin a local executable or immutable container digest,
front-end flags, include/define/file-list handling, top/module admission, ambiguity and
failure behavior, stable cross-version cell/net/cone identity, earlier/later/XOR
artifacts, independent direct checks, source/tool manifests, resource ceilings, and a
separate go/no-go rule. It must preserve every selected and refused corpus case.

The Yosys phase must not time CM algorithms. Only a passed Yosys correctness gate may
justify freezing a later local timing protocol. RunPod, GitHub Actions compute, paid
services, production changes, website claims, publishing, and pushing remain
unauthorized.
