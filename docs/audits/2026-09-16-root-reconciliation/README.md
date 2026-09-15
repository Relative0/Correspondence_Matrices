# Root reconciliation — 2026-09-16

## Purpose and scope

This record reconciles the protected dirty checkout at
`C:\Users\brian\Documents\CM_Computation` without altering it.  The checkout
was on `codex/cm-dirty-preservation-20260914` at
`72041c23ceebc257afc977c9e744b762bccaf21c`.  Its coarse `git status` reported
314 entries; with untracked directories expanded, that is 31,933 individual
files.

The reconciliation branch is `codex/cm-root-reconciliation-20260916`, based
on the reviewed snapshot `015f5cbb70b112795c08b61c27924c1ee752b9e9`.  Its
source-preservation commits are:

- `0fa87428` — CM research and benchmark pipeline.
- `31aea727` — CM paper workbench source.
- `efb08fb8` — CM video authoring source.

The protected checkout remains intact.  No reset, clean, switch, delete, or
in-place edit was performed there.

## Functional disposition

| Cohort | Files | Disposition |
| --- | ---: | --- |
| Benchmark campaign evidence | 3,475 | Archived exactly. |
| Other research/audit evidence | 24,044 | Archived exactly. |
| Build/replay output | 1,402 | Archived exactly. |
| Work/run output | 1,380 | Archived exactly. |
| Deep-series video production media | 1,164 | Archived exactly; authoring source is also committed. |
| Paper temporary render/output | 55 | Archived exactly; paper source is committed. |
| Docker vendor packages | 6 | Archived exactly; smoke source/fixtures are in the snapshot. |
| One-off output | 1 | Archived exactly. |
| Prior consolidation recovery package | 51 | Re-archived as an independent verified package. |
| Source, tests, docs, site, and metadata | 355 | Archived exactly; 319 match the snapshot byte-for-byte and 36 have snapshot-canonical replacements. |

The 36 non-identical source paths include the already-reviewed compiler and
pytest-profile changes, current site output, and stale root configuration/site
copies.  The reconciliation snapshot retains the newer compiler/site direction;
the root versions remain recoverable in `source-and-metadata-root-dirty.zip`.
In particular, the older website cohort was not allowed to revert roughly
31,463 lines of current snapshot content.

## Local archive payloads

The ZIP payloads are intentionally outside Git, beside this worktree at
`.recovery\root-reconciliation-20260916`.  Every ZIP was CRC-tested with the
ZIP reader before hashing.  Paths inside each ZIP are repository-relative.

| Archive | Members | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `audit-benchmark-campaign-root-dirty.zip` | 3,475 | 946,774,624 | `8CB1FD72652981F5AD24B591B3D788E262A1DAA5792DDD9969EBACA92A8CEBBE` |
| `audit-research-root-dirty.zip` | 24,044 | 228,250,244 | `5865F8C13885AE95D8FD08C43BE164F6B21C287573B3023DC3FCD8D1B3652582` |
| `build-root-dirty.zip` | 1,402 | 57,915,847 | `78A4CBBC4C48CAA6561D760394323311BBFDB669234E8F78F0CCEEE98E22297C` |
| `docker-vendor-root-dirty.zip` | 6 | 47,743,754 | `B049433EB26A0D5421B911B89E9FA70B138F7B29AE1F84974555EBF3D1554B3F` |
| `output-root-dirty.zip` | 1 | 878,534 | `157581C8C8C88EEC2DB8C0F0A5FFFB40FAD3D82087F54BF5665AB0F0603EFFAF` |
| `paper-program-tmp-root-dirty.zip` | 55 | 13,088,313 | `018D642E6DBB122F9AF6AAE7D52FF2F7486CBF754EEF2217B807BB2AA580AE6C` |
| `prior-consolidation-recovery-root-dirty.zip` | 51 | 327,143,368 | `781794163633D33979EB086DE83F053B76C81958B344D1453A06A8797A6074F4` |
| `source-and-metadata-root-dirty.zip` | 355 | 5,624,314 | `6B48F20FE70927E7F8F12F4B8FFE3847F6AB37D7EF1811FBAF046583AC45048A` |
| `video-deep-series-root-dirty.zip` | 1,164 | 616,810,593 | `B7AD836D77F5D45F553845AC2DCAD9CDD6FF2C095CAE29D37BB9FC40F3C537B8` |
| `work-root-dirty.zip` | 1,380 | 220,463,307 | `ED0231A5D6510F22D4011BBCCB539C3811D6E7A43548AE6D90D96F6133307C91` |

The archive union has 31,933 members, exactly matching the expanded root dirty
file list: zero missing paths, zero extra paths, and zero overlaps.  The ZIP
payload total is 2,464,692,898 bytes.

For recovery, first extract a needed ZIP into a new scratch directory and
verify its SHA-256 against this table.  Do not extract directly over the
protected root checkout.

## Verification notes

- `python -B -m compileall -q cmbench scripts tests native` passed for the
  research-pipeline commit.
- The selected paper audit and manuscript checks passed, including the
  exhaustive CM identity checks.
- Video source compiled.  Its source-specific tests that need archived media,
  review JSON, or local DejaVu fonts remain environment/resource-dependent;
  they were not treated as source regressions.
- The isolated target does not contain every frozen audit dataset, so
  data-coupled test failures there were recorded rather than papered over.
