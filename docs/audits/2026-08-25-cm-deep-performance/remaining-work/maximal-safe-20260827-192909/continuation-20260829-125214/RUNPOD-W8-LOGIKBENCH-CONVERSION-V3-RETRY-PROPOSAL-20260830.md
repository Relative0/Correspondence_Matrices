# Runpod W8 LogikBench V3 corrected conversion retry

Date: 2026-08-30  
Status: frozen; requires explicit approval of the new V3 upload and remote-wrapper hashes

## Reconciled prior attempt

The explicitly approved V2 attempt created pod `71gv8a3dttwnma`, validated the requested 2-vCPU/4-GiB Secure CPU allocation, uploaded all 159 files, installed Debian Yosys 0.23, passed all five exhaustive known-answer semantic fixtures, and converted the first real cluster. It then stopped on a Python `UnboundLocalError`: the aggregate retained-byte counter had been initialized inside the fixture helper rather than the main candidate loop.

- No comparative timing or CM method ran.
- Source-before and source-after records are byte-identical for all 159 files.
- The owned pod was deleted with HTTP 204; final v1/v2 inventories were empty.
- Controller-derived cost: $0.0008094880898793538.
- The V1 local AC-power refusal performed no upload and no create.

## Exact correction

V3 makes two bounded corrections:

1. Move `retained_blif_bytes = 0` from the fixture helper into the main conversion loop. No conversion algorithm, candidate, limit, or public corpus file changes.
2. In the separate remote wrapper, report source-after identity independently from conversion-artifact parsing, so a missing conversion summary cannot incorrectly overwrite a successful source-identity comparison.

The corrected worker completes a 70-candidate fake-conversion regression test locally, including aggregate byte accounting and all terminal rows. Seven focused W8 offline tests pass.

## Frozen V3 upload

- Manifest: `RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V3-20260830.json`
- Manifest SHA-256: `f908473b2e4df15ac7ca3b88c82e219c5e33c068022a9074d763604968190d98`
- Bundle: `RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V3-20260830.zip`
- Bundle SHA-256: `be42ee3517167e83168b138e8607eeebf5c6cc66d6660167daa2b38b425277b3`
- Bundle size: 204,587 bytes
- Exact members: 159 files, 617,277 uncompressed bytes
- Corrected worker SHA-256: `7722ed54eea875a11eea046b7cc81c13391d1a0b96d848cef8119b700e2fe13f`
- Remote wrapper SHA-256: `1e82c5d59900d01cef657606a9e6555f262e81371841a71a8257dbfce2b74dc3`
- Pinned upstream LogikBench commit: `891ced851ea4c2f9a46f6ab991eeee199e2fd516`
- 70 unchanged static candidates
- No credentials, `.env` files, Git metadata, databases, private keys, or unrelated source

## Unchanged remote scope and limits

- Conversion only; no CM execution and no performance claim
- Install only Debian's binary `yosys` package; no source builds or Python package install
- Five exhaustive known-answer RTL-to-BLIF semantic fixtures
- Attempt all 70 frozen candidates; at least 30 conversions required for controller success
- 20 seconds per candidate, 600 seconds aggregate conversion
- 4 MiB per BLIF, 20 MiB aggregate BLIF retention, 16 KiB per captured stream, 32 MiB aggregate evidence
- One Secure Runpod CPU pod, exactly 2 vCPU, at least 4 GiB RAM
- Pinned Python 3.13.15 slim-bookworm image digest
- 12 GiB container storage, zero pod volume, zero network volume
- Token-gated `8080/http` and `8081/http`; 256 KiB bounded resumable chunks
- 20-minute horizon, owned cleanup by 18 minutes
- One create and no replacement within the V3 controller
- $0.10 retry-phase cap and $5 attributable-campaign cap
- Conservative cost preflight includes every recorded pod, missing-cost reserves, current billing, and the $0.25 lag/unattributed reserve

## Authorization needed

The prior cost authorization covers the expense, but the V3 archive and remote wrapper have new hashes. External upload should proceed only after Brian explicitly approves these exact V3 hashes and the unchanged Runpod effect above.
