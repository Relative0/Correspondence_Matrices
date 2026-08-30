# Runpod P7 functional scout V2 authorization block

Date: 2026-08-30  
Status: no controller process, pod create, or source upload occurred

The read-only V2 preflight passed at `2026-08-30T05:45:28.392300+00:00` with empty v1/v2 inventories, a selected Secure `cpu3c` offer at `$0.06/hour`, a `$0.02` 20-minute compute projection, and a `$0.03816261929472287` aggregate projection under the V2 accounting model.

The subsequent local request to start `runpod_p7_functional_scout_controller_v2.py` was rejected before process creation. The execution reviewer determined that the standing `$5` comparative-campaign budget authorization did not specifically authorize disclosure of the exact private 96-file source/test payload to Runpod.

Consequences:

- no Runpod create request was sent;
- no pod was allocated;
- no source file was uploaded;
- the V2 one-create allowance and budget remain unconsumed;
- the passed preflight receipt is preserved as `P7-FUNCTIONAL-SCOUT-V2-PREFLIGHT-RECEIPT.json`;
- a new exact authorization record must not be created until the user explicitly approves this external payload disclosure.

The exact payload awaiting approval is:

- manifest: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json`
- manifest SHA-256: `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`
- file count: 96
- uncompressed source/test bytes: 19,484,163
- bundle: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip`
- bundle SHA-256: `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`
- bundle bytes: 3,197,013
