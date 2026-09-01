# W8 LogikBench untouched confirmation freeze v1

This directory freezes 30 independent LogikBench circuit/output cones selected
without comparative timing. The Linux semantic scout found 36 eligible unique
clusters among 64 converted inputs; the static predeclared selection chose 30.
Every selected translated CM expression exactly matched the independent packed
BLIF truth oracle.

The sources, roots, support order, oracle digests, selection/exclusion ledger,
schedule, and primary metrics are immutable under logical freeze
`427522568449d4d385ce642769b87b0703216535edb131653a0a75b2a8e39dcc`.

This cohort is reserved for untouched P9/W10 confirmation. It must not be used
to tune W4/W5 development arms, thresholds, schedules, exclusions, or analysis.
The semantic scout measured no performance. Any later typed refusal remains in
the denominator, and no case may be dropped after confirmation execution starts.

Files:

- `freeze.json`: authoritative cases, schedule, metrics, provenance, and use boundary.
- `sources/`: the 30 exact converted BLIF inputs.
- `oracle-package.json`: independent source-bound truth digests.
- `confirmation-selection.json`: the original Runpod-produced selection draft.
- `semantic-scout.json`: all 64 terminal semantic rows.
- `selection-exclusions.json`: 28 rejected and 6 eligible-unselected rows.
- `source-manifest.json`: source bytes, hashes, upstream paths, licenses, and conversion identity.
- `freeze-verification.json` and `checksums.json`: publication verification evidence.
