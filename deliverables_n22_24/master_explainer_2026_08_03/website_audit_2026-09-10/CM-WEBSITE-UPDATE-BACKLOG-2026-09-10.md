# CM website update backlog — 2026-09-10

This is a review backlog, not authorization to edit, publish, commit, push, or deploy.

## P0 — evidence correctness and freshness

1. **Replace the ambiguous current flattened-CSE tile.** Lead with B2/B4 V3 bare CM/CSE-flat **0.8905696773 [0.8740654100, 0.9072717742]**. Preserve `1.0038` in a dated “historical B1/E3 local” row. Preserve wrapper **3.094136** as an unfavorable whole-call result. Add an inline “below 1 favors CM” label.
2. **Add the C16 Linux confirmation.** Show local Windows **3.545324×** separately from verified Linux **3.177887× whole path / 3.117978× p95**; state 40 cases, 360 rows, zero semantic/artifact mismatches, and the unfavorable local minimum **0.892796×**.
3. **Expose C6 instead of burying it in C6–C12.** Add **1.313448× test / 1.637157× confirmation** medians and **2.175615× / 1.835850× p95**, exactness, zero mismatches, and the boundary: packed exact core advanced; learned hybrid and production promotion did not.
4. **Keep feature-model claims provisional.** Retain `0.276951 [0.200748, 0.371722]` only as a bounded warm-output CM/direct-CNF result. Keep `0.624416 [0.215794, 1.535452]` CUDD as inconclusive.
5. **Do not convert the Sep-10 q64 no-go into a positive claim.** Hold it outside the normal public set until separately approved; if later added, show the failed 1.10 materiality gate and fully charged two-host values.

## P0 — downloadable evidence

6. **Create a Data & Downloads index generated from the manifest JSON.** Each claim set should include a commit-pinned GitHub view link, raw-download link, SHA-256, byte size, contract, host/split, evidence role, verifier/test links, and license/privacy status.
7. **Publish only reviewed minimal bundles.** Start with the website snapshot, B2/B4 V3, C6, C16, feature-model audit, and current architecture sets listed in the artifact audit. Do not expose a directory as if it were one downloadable file.
8. **Resolve licensing before bundling.** The repository has no root license. Add an explicit project license or a per-artifact rights statement; preserve the existing third-party fixture license.
9. **Review operational metadata and ZIP contents manually.** Do not publish tokens, credentials, private endpoints, local databases, or unnecessary pod/host identifiers. The Phase-1 manifest intentionally did not inspect secret stores or `.env*` files.

## P1 — graph and provenance quality

10. Add SVG `<title>` and `<desc>` to all 22 chart definitions; retain and regression-test the existing keyboard-focusable marks, ARIA live tooltip, and full table fallback.
11. Put ratio direction and timing boundary directly in every chart title/caption: time ratio versus speedup, kernel versus preparation/wrapper, warm versus cold, and lower- versus higher-is-better.
12. Pin evidence links to the reviewed commit rather than `main`; retain a visible “latest repository” link separately.
13. Add the exact source selector/field and evidence role to downloadable manifests; distinguish raw, summary, confirmatory, independent verification, and superseded evidence.
14. Add generated freshness checks that fail when a displayed source has a later accepted same-contract result or when a chart/table value is not produced from the same data object.
15. Give all `T()`/`TV()` table and chart values the same machine-readable token/provenance hooks as prose `P()` spans; the learning/neural route currently exposes no `span.num[title]` provenance nodes.

## P1 — tests for the update pass

16. Extend website tests to assert the B2/B4 headline and historical `1.0038` label, C16 Linux values/qualifications, C6 values/exactness/no-promotion boundary, and q64 post-cutoff exclusion.
17. Test every manifest path at the pinned commit, raw-download URL formation, SHA-256/size, missing-license warnings, and the absence of secret-like publication paths.
18. Rebuild all seven pages, run the full website test set, compare generated-page hashes, inspect every route at desktop and narrow viewport, and check console errors/broken links before deployment.

## P2 — later review

19. Decide whether the Sep-10 q64 no-go belongs in a public “current limitations/research disposition” section. It does not create a positive-use-case headline.
20. Consider a versioned evidence release archive only after license and privacy review; include the claim ledger and checksum manifest in the release.

## Acceptance gate for Phase 2

- No contract substitution.
- No value without a source selector and evidence role.
- No positive label when the ratio direction is unfavorable or an interval crosses parity.
- No post-cutoff result without explicit approval.
- No download without existence, checksum, license, privacy, and reproduction/test review.
- Live deployment must hash-match the reviewed build.
