# Runpod W8 LogikBench semantic/root/oracle scout proposal

Date: 2026-08-30  
Status: prepared; exact external-upload approval required before launch

## Purpose

Use the 64 conversion outputs from the audited W8 Yosys scout to determine whether at least 30 independent natural circuit clusters have a bounded primary-output cone usable by CM. This scout freezes roots, ordered supports, exact truth-oracle hashes, provenance, strata, and later timing schedules. It performs no comparative timing and permits no performance claim.

For every eligible cone, the scout independently compares:

1. the BLIF netlist's packed truth evaluation; and
2. the truth evaluation of the expression translated into the CM expression language.

Any disagreement rejects that case. Semantic duplicates are removed before the deterministic 30-case primary selection.

## Exact upload

- Manifest: `RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json`
- Manifest SHA-256: `42411d3b0e22b048f143cdece99848b104d2cc9278ab7cbef050c1db9ecba5d1`
- Manifest bytes: 39,363
- Bundle: `RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-BUNDLE-V1-20260830.zip`
- Bundle SHA-256: `142f6d5e6ad4fe68ef3f64e6a74a0236fa786ae9e990c27ea1ed8c533faa24aa`
- Bundle bytes: 1,540,008
- Files: 82
- Uncompressed source bytes: 15,054,954
- Converted BLIFs: 64
- Credentials, environment files, Git metadata, private keys, databases: none

The manifest identifies every uploaded file by target, byte count, SHA-256, and provenance. The private portion consists of the bounded parser/evaluator source and test, the scout worker, locked dependency records, and local audit records. The converted BLIFs derive from the pinned public LogikBench commit `891ced851ea4c2f9a46f6ab991eeee199e2fd516`.

## Exact remote program

- Remote wrapper: `runpod_w8_logikbench_semantic_remote_v1.py`
- Wrapper SHA-256: `13e70cfa43d962eaaeac5a1975f5c0a66a59b0aee4b7254ea47ccb8e204686e6`
- Worker: `runpod_w8_logikbench_semantic_worker_v1.py`
- Worker SHA-256: `67277dc93fa350f6b11b9ff6d7b42ef15ace84897d61cac1e67f9aa1f0308157`
- Bootstrap SHA-256: `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9`

The wrapper installs the existing 13 hash-locked binary Python packages, runs six focused BLIF parser/oracle tests, and runs the bounded semantic scout. It does not install Yosys or any source-built package.

## Frozen semantic contract

- Inputs: all 64 audited converted BLIFs.
- Root order: SHA-256 of `cm-w8-root-v1`, cluster ID, and primary-output name.
- Support: 4 through 16 variables inclusive.
- Cone bound: at most 4,096 source nodes.
- Per-case deadline: 45 seconds in a fresh child process.
- Aggregate semantic deadline: 720 seconds.
- Required output: exactly 30 unique primary confirmation cases.
- Static selection: deterministic round-robin across source group, support stratum, and cone-size stratum.
- Frozen output: source/provenance hashes, selected root, sorted support order, structural strata, truth SHA-256, oracle SHA-256, case IDs, later arm schedules, and primary metrics.
- Timing: none in this scout.

If fewer than 30 unique eligible cases survive, the run fails and no smaller confirmation set is silently accepted.

## Resource and safety envelope

- One Runpod Secure CPU pod.
- Exactly 2 vCPU and at least 4 GB RAM.
- Pinned Python 3.13.15 image already used by the audited campaign.
- 12 GB container storage.
- Zero pod volume and zero network volume.
- 20-minute absolute lifetime; controller cleanup begins at 18 minutes.
- Phase cap: $0.10.
- Attributable campaign cap: $5.00, including conservative lagging-billing and missing-cost reserves.
- One create, owned-name/ID cleanup, no replacement within this controller.
- Existing unrelated pods cause a local refusal; the controller never deletes them.
- Uploads and result retrieval use bounded resumable chunks and token-gated routes.

## Success gate

Success requires all of the following:

- six focused tests pass;
- all 82 uploaded files remain byte-identical;
- all 64 converted inputs produce terminal typed outcomes;
- at least 30 semantically unique eligible clusters remain;
- exactly 30 deterministic primary cases are frozen;
- every primary case has exact BLIF-oracle/CM-expression truth agreement;
- the retrieved evidence archive and its internal hashes verify;
- the created pod is deleted by owned identity and both Runpod inventories are empty.

The next comparative timing/RSS package remains blocked until this evidence is audited and the 30-case confirmation corpus is frozen locally.
