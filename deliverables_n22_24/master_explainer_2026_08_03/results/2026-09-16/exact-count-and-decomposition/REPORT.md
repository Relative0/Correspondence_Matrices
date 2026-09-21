# September 16 research and source update

## Exact integer CUDD counting

The dd 0.6.0 prototype calls `Cudd_ApaCountMinterm`, folds binary APA digits into
a Python integer, and frees the returned buffer using `Cudd_FreeApaNumber` in
`finally`. Default support-sized counting is preserved. There were 57 prototype
and 23 relevant dd regression passes. A 40,000-call Valgrind comparison showed
unchanged combined lost bytes against the interpreter baseline, not a globally
leak-free interpreter. Allocation failures were not fault-injected.

Nine rounds of 200 calls per method measured already-resident roots on Linux/WSL.
Construction is excluded. On the three larger synthetic diagrams APA was about
9–10 times faster than the existing Python exact traversal, with about 1.1–3.4
times the latency of the double API. Trivial roots favor Python. The OR count
rounded in the double control; the 1,100-variable padded literal overflowed it.
See `cudd-benchmark.json` for all samples, exactness flags, environment and hashes.

## C39–C41 decomposition studies

C39 measured 3.4615 times C16-over-C15 speed across 19 public cases; C40
measured 3.9526 times across 20 cases on a separately acquired public family.
Both use sums of per-case medians of analysis-only time, not end-to-end time.
Selected artifacts were identical and reconstructed the input truth vectors.
C40's sum of median peak-working-set deltas was 33,587,200 bytes for C15 and
19,165,184 bytes for C16. This is a Windows observation, not a general memory bound.

C41 retained 500 timing rows and zero invalid ablation lanes. Repeating layouts
cost 1.7329 times the reference; eager admission cost 3.5491 times. A linear
minimum used 0.9324 times the reference time. Omitting strict checks is a
diagnostic lane, not a safe production optimization. These effects are not
additive causal shares of the historical C15-to-C16 difference.

The ABC ACD output contract is different: no external speed or quality claim is
supported. The published code exposes that incompatibility explicitly.

## Bounded cut fusion: STOP

The locked F1/F2 q64 whole-session speed was 0.4932
times the CSE control, below the frozen 1.10-times threshold. Execution improved
but recognition/compilation did not repay at measured reuse. All 21,840 timing
rows were exact across arms, but natural-panel timing and the relative-memory
promotion sweep were not run after the stop. No default dispatch change is made.

## Source and reuse

Individual Python files and the APA patch are under `sources/`; the ZIP contains
the same explicit allowlist plus these summaries. The source ZIP is an overlay
for the repository, not a standalone Python installation. Prototype build and
validation instructions are in `sources/prototypes/cudd_apa/README.md`.
The repository includes the reviewed recent compiler/research/Python work; the
SymPy cleanup source is included as well, without assigning it a new benchmark.

Source text is normalized only for line endings before hashing. The manifest
records every published file's bytes and SHA-256. Original C39–C41 result hashes
are retained in the aggregate documents. They are aggregate extracts, not a
redistribution of the original corpus or a complete benchmark replay bundle.
Raw corpus vectors, unresolved-licensing data, executable binaries, local paths,
credentials and cloud-operation receipts are outside this publication allowlist.
The dd-derived patch carries `DD-LICENSE`; publication grants no new license to
the remaining project source. Third-party tools must be obtained separately.
