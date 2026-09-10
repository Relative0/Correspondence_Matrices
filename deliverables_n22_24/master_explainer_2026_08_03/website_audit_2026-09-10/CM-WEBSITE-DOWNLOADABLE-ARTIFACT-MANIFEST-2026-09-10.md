# CM website downloadable-artifact manifest — 2026-09-10

## Decision

The live site exposes evidence primarily as GitHub `blob/main` links. The referenced material is therefore viewable, but the download experience is not a frozen evidence release: links can drift with `main`, directories are not single downloads, and the repository has no root project license. Phase 2 should add a reviewed download hub with commit-pinned **view** and **raw download** links, SHA-256, byte size, contract, and the exact tests/verifier for each result.

No artifact was copied, published, committed, pushed, or deployed in this Phase-1 audit.

## Inventory summary

- Referenced or nominated paths: **181**
- Currently referenced by site data/templates: **146**
- Explicitly nominated additions: **34**
- Missing from `HEAD`: **0**
- Deliberately absent and explicitly excluded from numeric rendering: **2**
- Root project license: **not present**. Public GitHub visibility does not itself grant redistribution rights; add/clarify a project license before assembling redistributable bundles.
- Privacy scan: filenames and publication scope were checked. Artifact contents were not searched for secrets; operational manifests and ZIPs remain flagged for manual review.

## Priority download sets for Phase 2

| Set | What to expose | Minimum contents | Disposition |
| --- | --- | --- | --- |
| Website evidence snapshot | Exact site inputs and validation | master data/content, three builders, templates/shared code, five website tests, before-state SHA manifest | publish a small commit-pinned bundle after license review |
| Current flattened-CSE result | B2/B4 V3 0.8906 [0.8741, 0.9073] and wrapper 3.0941 | audited_v3_inference.csv, audited_v3_audit.json, protocol/readme if present | add stable view/raw links; label 1.0038 historical |
| C6 exact packed source-ANF | 1.313× test; 1.637× confirmation; exactness and p95 | report, result JSON, raw run directory or reviewed archive, independent verification, relevant tests | add; currently missing from rendered evidence |
| C16 exact screening | local plus Linux 3.1779× whole-path and 3.1180× p95 | local result, Linux final verification, protocol, dataset/manifest, verifier, tests | add Linux confirmation beside local result |
| Feature-model audit | correctness replay, performance gaps, 0.277 task-specific result | audit report, corpus/raw CSVs, artifact replay, clustered statistics, measurement gaps, regression JUnit/tests | retain links; add frozen raw-download index |
| Current architecture | complete relation, multi-root, small-task controls, q1/q4/q16/q64 ladder | analysis JSONs, source freezes/manifests, independent verification, tests | retain qualifications and pin links |
| Recent q64 adjudication | 0.949341 / 0.977972 fully charged no-go | final report, assessment, verification, checksum manifest; ZIP only after archive/privacy review | hold outside normal public set pending later review |

## Broken/missing references

None among the normalized repository paths collected from the committed data/templates.

The two missing neural reassessment `assessment.json` paths are not broken download links: the site explicitly records that they are absent from integrated Git history and suppresses their dependent numeric claims. They remain `deliberately_excluded_missing_artifact` in the JSON manifest.

## Machine-readable detail

The companion JSON contains each normalized path, `HEAD` status, Git object identity, SHA-256 for files, byte size, reference locations, license/privacy flag, and recommended disposition. It intentionally over-includes supporting evidence so Phase 2 can choose a minimal, reviewable public package without rediscovering provenance.
