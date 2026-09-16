# C41 task-aligned external-producer search

Status: scoped negative result, searched 2026-09-16.

## Required contract

A task-aligned producer must independently emit a complete
`crse-exact-cm-gf2-artifact/v1` document for the supplied truth vector. The
document must include one of the four accepted payload families, all variable
and partition identities, factor-size fields, the source hash, and the canonical
payload hash. Acceptance is only through
`adapt_external_candidate`; the adapter performs strict document admission and
complete truth reconstruction. C16 may supply an expected document for identity
comparison, but it may not create or repair the external payload.

## Primary-source and implementation checks

- The exact schema string was searched verbatim on the public web and produced
  no matching producer. This is a scoped search result, not proof that no private
  or unindexed implementation exists.
- Berkeley ABC's official repository describes ABC as a logic-synthesis and
  formal-verification system and exposes embedding through its static-library
  API: <https://github.com/berkeley-abc/abc>. The pinned ACD implementation used
  in C40 is under
  <https://github.com/berkeley-abc/abc/tree/baf4ddb16acb94fbfe75ac0fe6a99330ba1e315a/src/map/if/acd>.
  The retained C40 runner calls `ac_decomposition_impl.run`, `get_profile`, and
  the LUT-count statistic; its output is feasibility, return value, delay
  profile, LUT cost, and time. It has no complete C16-family factor document.
  All 20 calls were therefore correctly contract-incompatible.
- ABC also has a DSD formula representation. Its official I/O implementation
  documents syntax for AND, XOR, inversion, and hexadecimal truth-table nodes:
  <https://github.com/berkeley-abc/abc/blob/master/src/base/io/io.c>. That is a
  different decomposition language and does not emit the required four-family
  artifact document, canonical objective fields, or project hash identities.
- M4RI's official implementation provides dense GF(2) arithmetic and PLE/Gaussian
  elimination: <https://github.com/malb/m4ri>. Its matrix API is primary
  implementation evidence for a possible rank-factor building block, but it is
  not a Boolean-function portfolio producer and does not emit the required
  artifact schema, cofactor/Kronecker/XOR alternatives, or canonical selection.

## Result and frozen comparison boundary

No genuinely task-aligned external producer was identified in this scoped
search, so C41 makes no external speed or quality claim and runs no external
timing lane. A wrapper that obtains only feasibility, cost, a mapped network, a
DSD formula, or a matrix factor remains contract-incompatible; translating it
with C16 logic would no longer be an external producer result.

If future work adopts a shared objective instead of the exact artifact contract,
it must freeze before measurement: accepted decomposition class; factor/circuit
size objective and tie-breaking; input and variable order; partition and search
bounds; producer versions and build flags; lifecycle and timeout; independent
reconstruction/equivalence validation; corpus; schedule; exclusions; and the
aggregate statistic. No such shared-objective performance measurement is part
of C41.
