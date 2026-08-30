# P7 functional scout V1 outcome and V2 retry readiness

## V1 outcome

The authorized 152-file scout failed closed during focused-test collection.
`cmbench/recognition/blif.py` imported `cmbench/recognition/features.py`, which was
not in the manifest-bound upload. No P7 cell ran and no performance conclusion is
permitted.

- Pod: `1xh6csc4oxy067`
- Focused-test result: three collection errors; zero executed tests
- Source identity: unchanged
- Retrieved partial-evidence ZIP SHA-256:
  `0cd9a0462b719d6c860ca291dc76ab3e9441040453bc967890ce9f6688e4f62b`
- Estimated compute cost: `$0.002207883052031199`
- Cleanup: pod absent and both v1/v2 inventories empty

The authoritative saved result is `p7-functional-scout-v1-001/RUN.json`.

## Dependency-closure audit

An extracted-tree gate was added so tests cannot silently import omitted files
from the live checkout. It found three dependency classes missing from V1:

1. `cmbench/recognition/features.py`, imported by the BLIF parser.
2. `deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl`, referenced
   by both selected frozen development cases.
3. `cmbench/backends/__init__.py` and `cmbench/backends/bitset_engine.py`, imported
   during complete-relation materialization.

The V2 and V3 intermediate candidates are deliberately retained with their
failing local-gate evidence. The final V4 upload candidate contains 156 files and
11,591,021 uncompressed bytes. From a fresh extracted temporary tree it passes
all 32 focused tests plus 16 subtests.

## Frozen retry candidate

- Manifest:
  `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V4-20260830.json`
  - SHA-256: `8bdcd14cdbb6116519a0ab2198c9b90acc2dcf5d8ed8830a536090e33c8ead6a`
- ZIP: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V4-20260830.zip`
  - Bytes: `1,731,976`
  - SHA-256: `3f4ae4ad709b029ebedf6b8cab8d4f359f40bf741ae9e3280f4d97a7a0660b17`
- Isolated local gate:
  `P7-FUNCTIONAL-SCOUT-UPLOAD-V4-LOCAL-GATE-20260830.json`
- Retry controller:
  `runpod_p7_functional_scout_controller_v2.py`
  - SHA-256: `87660264b02dca20f254664a277524a78c69b286fd622b58ae233254aee74b16`

The read-only retry preflight passes, both inventories are empty, and the
conservative prior-cost bound is `$0.01`. The controller remains unable to create
a pod because the exact V2 authorization record is absent.
