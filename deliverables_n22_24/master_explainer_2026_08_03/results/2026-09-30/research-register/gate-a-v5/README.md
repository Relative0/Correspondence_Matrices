# Protocol v5 candidate — Gate A NO-GO

Start with REVIEW_REPORT_V5.md and PROTOCOL_V5.md. This is prospective design and untimed validation, not a stability pass or an authorized confirmatory freeze.

The 187-file source closure is unmodified. The primary corpus bytes are unchanged. New measurement code lives at package root; legacy/ is immutable provenance. All result templates remain empty. No natural population is included. Generated secondary schedule expansions are data, not executable authorization.

Read-only integrity check (from the extracted candidate directory): `python -B verify_candidate.py`.
Untimed/synthetic design checks: `python -B -m pytest tests/test_v5.py -q -p no:cacheprovider --basetemp <new external temporary directory>`.
Do not run copied legacy pilot/runner scripts. No Frozen Execution Prompt is supplied. No future pilot binding is included. A future binding must be separately authorized and prepared on the selected controlled host; see Protocol section 8 and the review report.

The checksum-identified ZIP and manifest define the immutable candidate. Unzip into a new directory for review; never append to its result templates or promote this candidate manifest to GO. Future results belong under one new pilot-v5-* identity outside the candidate.
