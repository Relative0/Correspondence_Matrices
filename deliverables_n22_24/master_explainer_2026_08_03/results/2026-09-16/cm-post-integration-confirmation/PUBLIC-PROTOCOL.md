# Reproduction protocol

## Frozen identity

- Source commit: [`63285d2bd16e16ca48d8a0328b6f6328ea038b35`](https://github.com/Relative0/Correspondence_Matrices/tree/63285d2bd16e16ca48d8a0328b6f6328ea038b35)
- B2 corpus SHA-256: `8a7f4a8646eff72275a32299d0e0a9cfa3b983194ddb7f8299d71c18f2f9138f`
- B4 corpus SHA-256: `91f23c8cb62677c8d8b4526099703c837bf9611d5a2cd7becdd1adbf08b53d19`
- Corrected-E3 corpus SHA-256: `3c91cfbf4583ecbdc6aef422de5dd141d581487a6bd54f06632de38391d2a574`
- B2/B4 runner SHA-256: `154598f3a6a03a6f9a0c6ec536dbe7e9f8b9a0514fe82cb149cb491c41b0ebc0`
- Corrected-E3 runner SHA-256: `c486fc799ba7d9920267488de0259997c885cb3d9044b056ccb43640417a35be`

The source commit contains the [B2/B4 runner](https://github.com/Relative0/Correspondence_Matrices/blob/63285d2bd16e16ca48d8a0328b6f6328ea038b35/scripts/cm_symmetric_wrapper_followup.py),
the [corrected-E3 runner](https://github.com/Relative0/Correspondence_Matrices/blob/63285d2bd16e16ca48d8a0328b6f6328ea038b35/deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py),
and the frozen corpora. Source snapshots are omitted from this website bundle because the immutable commit and
source hashes identify the same bytes without duplicating them.

## B2/B4 schedule

Run `scripts/cm_symmetric_wrapper_followup.py --output-prefix <unique-prefix> --rounds 24` in a clean checkout of
the pinned commit. Keep the runner's original 100-call batches at `k <= 8`, 25-call batches at `k <= 12`, and
5-call batches above `k = 12`. Each accepted run must contain 264 rows from 216 formulas, report zero packed-output
mismatches, match both corpus hashes, and select 208 flat-engine plus 56 word-engine rows. The Windows campaign used
three independently launched workers; Linux used one newly created disposable worker.

## Corrected-E3 schedule

Run `deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py --out-dir <unique-directory> --corpus
deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl --rounds 4 --rr-passes 60 --bootstrap 2000`.
Each accepted run must contain 192 rows, match the corpus hash, and report exact output for every row. Derived
break-even counts use the runner's stored preparation and kernel times; they are machine-specific planning estimates.

## Timing and inference contract

Ratios are numerator time divided by denominator time, so values below 1 favor CM. Report bare kernel, whole-call
wrapper, and CSE-flat absolute times beside their paired ratios. Formula-cluster intervals use a deterministic,
10,000-repetition percentile bootstrap over formula-level mean log ratios. They describe formula variation on one
machine and run, not variation between runs or machines. Do not pool the Windows repetitions into a formula-only
confidence interval.

## Execution controls

Workers used unique output paths and refused overwrite. All accepted workers verified the Python worker identity
before numerical imports. Windows stopped above 1 GiB sampled process-tree working set or 300 seconds. Linux stopped
above 1 GiB sampled descendant RSS or 600 seconds per benchmark, with a 1,200-second combined deadline. Polling can
miss brief peaks and is not an operating-system hard memory limit.

The Linux replication used CPython 3.13.5, NumPy 2.3.2, two vCPUs, no persistent volume, and a disposable RunPod
Secure Cloud CPU pod. The pod was deleted after 146.49 seconds; postflight inventories were empty. Cloud credentials,
pod identifiers, network endpoints, source snapshots, and operational logs are intentionally excluded.

## Artifact guide

- `PUBLIC-SUMMARY.json`: chart and claim source used by the website.
- `PUBLIC-REPORT.md`: result tables, interpretation, limits, and monitor incident.
- `windows-*-raw.csv` / `linux-symmetric-raw.csv`: per-formula measurements.
- `*-inference.csv`: formula-cluster estimates and confidence intervals.
- `*-audit.json`: environment, source hashes, exactness, and inference contract; private paths removed.
- `*-break-even-results.json`: per-formula corrected-E3 evidence; corpus paths normalized to repository-relative paths.
- `*-break-even-summary.csv`: runner-produced corrected-E3 tables.
- `VERIFICATION.json`: publication-level acceptance and source-seal record.
- `PUBLICATION-MANIFEST.json`: byte size, SHA-256, role, scope, and reuse review for every file.
