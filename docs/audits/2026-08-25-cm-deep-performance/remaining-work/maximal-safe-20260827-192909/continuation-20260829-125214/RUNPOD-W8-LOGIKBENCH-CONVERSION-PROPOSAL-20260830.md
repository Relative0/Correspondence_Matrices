# Runpod W8 LogikBench conversion-only scout

Date: 2026-08-30  
Status: executable under Brian's approved comprehensive plan and standing $5 Runpod campaign authorization

## Purpose

Convert a statically admitted, independently sourced LogikBench corpus from RTL to BLIF and return bounded evidence for a later local semantic/admission freeze. This scout does **not** execute CM methods and does **not** produce comparative performance rankings.

## Frozen upload

- Manifest: `RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V2-20260830.json`
- Manifest SHA-256: `5365b4362fc42790bf7107c6b8da29ec61b79faf8d69ac40bcfeb77a87640354`
- Bundle: `RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V2-20260830.zip`
- Bundle SHA-256: `1b3796d6ded0f6d1b0d6266c5e783f1b0687aae9c7ecfdac901ad625c6e6ff95`
- Bundle size: 204,586 bytes
- Exact members: 159 files, 617,274 uncompressed source bytes
- Upstream repository: `https://github.com/zeroasiccorp/logikbench.git`
- Pinned upstream commit: `891ced851ea4c2f9a46f6ab991eeee199e2fd516`
- Static candidates: 70 combinational, non-AI-primary clusters with permissive license evidence
- Private uploaded files: the conversion worker and the two local acquisition/admission JSON records listed by the manifest
- Excluded: credentials, `.env` files, Git metadata, databases, private keys, and unrelated project source

The remote wrapper is transported separately as authenticated controller code. It is pinned by SHA-256 in the authorization and transport-freeze records.

## Remote action

1. Verify the archive, manifest, every member hash, paths, and source identity.
2. Install only Debian's binary `yosys` package with `apt-get`; no source builds and no Python package install.
3. Record Yosys command and Debian package identities.
4. Run five exhaustive known-answer RTL-to-BLIF semantic fixtures.
5. Attempt the 70 frozen candidates in deterministic order with a 20-second per-cluster and 600-second aggregate conversion ceiling.
6. Retain at most 4 MiB per BLIF and 20 MiB of BLIF output in total; retain at most 16 KiB per captured stdout/stderr stream.
7. Re-hash all uploaded files after work and return at most 32 MiB of aggregate evidence through the token-gated result channel.

A controller result is successful only if source identity remains unchanged, all five known-answer fixtures are equivalent, all 70 candidates receive a terminal converted/rejected record, at least 30 convert, evidence checksums match, and no performance claim is made.

## Resource and transport limits

- One Secure Runpod CPU pod selected from the approved `cpu3c`, `cpu3m`, or `cpu5c` set
- Exactly 2 vCPU and at least 4 GiB RAM
- Pinned image: `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`
- 12 GiB container disk
- Zero pod volume and zero network volume
- Only `8080/http` and `8081/http`, protected by a per-run random token
- 256 KiB bounded resumable upload chunks
- 20-minute provider horizon; owned cleanup begins by 18 minutes
- Setup must reach conversion within 390 seconds; the worker's absolute setup deadline is 360 seconds after create
- One create in this controller; no automatic replacement
- Independent local watchdog must be live and acknowledge the exact atomic controller state before create
- Cleanup may target only the pod name/ID bound to this create response; both v1 and v2 inventories must be empty afterward

## Budget and authorization

- Maximum quoted/actual rate: $0.25/hour
- Conservative storage-rate reserve: $0.01/hour despite zero persistent volume
- Phase cap: $0.10
- Campaign cap: $5.00
- Preflight accounts once per locally recorded pod, reserves $0.05 for each created pod lacking an estimate, compares that bound with current observed campaign billing, and adds a $0.25 unattributed/billing-lag reserve
- No create if the conservative prior bound plus a full 20-minute projection reaches either cap, current inventories are nonempty, host AC power is absent, or account/spend-limit checks fail

Brian authorized the comprehensive next-steps plan and up to $5 for needed runs, reruns, and failed runs on 2026-08-30, asking that attempts be reported afterward. This record applies that standing authorization to this bounded W8 conversion scout.

## Interpretation boundary

Conversion success establishes usable, provenance-pinned BLIF inputs. It does not establish CM correctness on those inputs, performance, memory use, or superiority over another method. Those require the later local confirmation freeze and the separately frozen W4 timing/RSS package.
