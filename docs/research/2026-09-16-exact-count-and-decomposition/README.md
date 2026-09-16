# September 16 research publication

This publication was prepared in an isolated worktree from the reviewed local
integration at `7ffb184e`. The original dirty checkout was not modified. The
user authorized committing recent findings and Python files and updating the
Correspondence Matrices website; no dd upstream issue, pull request, or release
was requested or created.

## Included evidence and source

- The exact-integer dd/CUDD research prototype, cross-backend tests, resident-root
  benchmark, and differential allocation-cleanup results.
- C39 phase timing, C40 development-blind confirmation, and C41 ablation sources
  and aggregate results. Original results.json bytes were checked against each
  local RESULTS_MANIFEST.json before extracting these aggregates. Each aggregate
  retains its original result hash, freeze hash, environment, and source path.
- The already reviewed cut-fusion experiment, including its STOP result.
- Individual source downloads and a deterministic ZIP containing repository
  overlay files, not a standalone dependency distribution.

C40/C41 corpus redistribution is unresolved. Corpus vectors, frozen corpus
files, third-party source trees, native binaries, and local build environments
are excluded. Historical study Markdown retains references to local evidence
that is not part of this publication. The C41 source-closure test uses synthetic
temporary inputs so a clean public checkout can test validation without those
corpus files. No external-tool performance superiority is claimed.

## Verification before commit

- Focused research and website tests: **85 passed, 36 subtests passed**.
- Prototype evidence: **57 prototype tests and 23 dd regression tests passed**;
  allocation-failure injection was not performed.
- The 40,000-call Valgrind differential check passed; interpreter-baseline lost
  bytes remain and are explicitly disclosed.
- Website release verifier: 9 pages, 18 current panels, 1,467 records and 23
  shared figure definitions verified for publication.
- JavaScript syntax check and Git whitespace check passed.
- Browser inspection confirmed the findings table and download navigation;
  no page warning/error console entries were observed.
- HTTP verification checked all 42 publication files against their SHA-256
  checksums and lengths, including the source ZIP.

The publication manifest SHA-256 is
`73d1decbcdf6e1964f75019ddf9092d4456c7632c259eb3444b83acbfb9da24c`.
Regenerate the package with `scripts/cm_september16_research_export.py`, then
rebuild the website with its existing `cm_master_build_2026_08_03.py` generator.
