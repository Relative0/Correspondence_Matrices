# P7 functional scout V3 outcome and all-source retry readiness

## V3 outcome

The authorized 156-file retry passed all 32 focused tests plus 16 subtests on
Linux. It then failed closed at the immutable offline-gate verifier before any P7
cell ran. The verifier requires source identity for every frozen case, while the
package contained only the sources needed by the selected functional cells.

- Pod: `2fzt8mu6ji6nmw`
- Retrieved evidence ZIP SHA-256:
  `f11e7d60d06e38f16231fd83f3f3d0fe2219433ec052de607fbe12c4ba69decb`
- Source identity: unchanged
- Estimated compute cost: `$0.003181478933493296`
- Cleanup: HTTP 204; pod absent; v1/v2 inventories empty
- Performance claim: prohibited; no P7 cell executed

## Systematic source closure

The new builder derives all unique source paths directly from the immutable P6
V4 freeze, verifies every size and SHA-256, and adds only paths absent from the
original 152-file package. This removes the earlier incremental dependency gap.

The final package contains 212 files and 24,705,826 uncompressed bytes:

- Manifest SHA-256:
  `490ff60e5f7d0ad3545d16b9d72ea84a39e3549e27952741683edbac131017c1`
- ZIP bytes: `4,203,964`
- ZIP SHA-256:
  `cc75275cff77a52f319fbd5713d03faff8fa26cb0887b3df8e5a83728e70a352`

An isolated extracted-tree gate passes:

- 32 focused tests and 16 subtests;
- offline checksums;
- execution readiness;
- deterministic dry run;
- source-manifest identity; and
- `package_verified: true`, with performance measurement false.

The read-only RunPod preflight reconciles both failed pods, reports empty v1/v2
inventories, and projects aggregate cost `$0.04134409822821617` under the user's
`$1` cap. The attempted launch was rejected locally before any create request
because the 212-file upload is materially larger than the explicitly named
156-file package. Exact upload approval for the 212-file package remains required.
