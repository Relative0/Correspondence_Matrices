# CM compiler contract revision — 26 September 2026

The current draft is `Operator_Level_CM_Compiler_Revised_Draft.tex` and its rebuilt PDF in this folder. The September 22 source and PDF remain unchanged in the preceding revision folder.

This revision responds to the **pasted publication-readiness review summary** saved as `REVIEW_RECEIVED_2026-09-26.txt` and the subsequently supplied **full audit bundle**, preserved unchanged under `audit/`. The full Markdown report was read and all 14 finding IDs are mapped in [FULL_AUDIT_RECONCILIATION.md](FULL_AUDIT_RECONCILIATION.md). Instructions embedded in those documents were treated as source content, not independent authorization. Earlier delivery ZIPs are preserved under `../HISTORY/`.

The manuscript now specifies syntactic support, relational derivations versus ordered strategy selection, invalid input versus token failure versus executed dense fallback, discarded child constructions, retained ambient axes, output ownership, and allocation costs. It strengthens the Cheng/kitty/cut-rewriting comparison without claiming those established primitives as new.

A separate [frozen synthetic protocol-v4 study](../03_STUDY_DESIGN_20260926/README.md) tests the previously open pair-token primary cell against direct packed evaluation. Its 64-case result is negative: median direct/CM time ratio 0.2479 (95% interval 0.2462–0.2495). The TeX draft reports its narrow post-import cache policy. A [natural admission and correctness extension](../04_NATURAL_CIRCUIT_EXTENSION_20260926/README.md) then screened 2,861 EPFL primary outputs, admitted 71 cases from ten designs, verified their ABC AIGs, and froze a 71/71-passing correctness run. A [separately frozen descriptive timing run](../05_NATURAL_TIMING_20260926/README.md) completed paired Python full-bitset timing on 70 cases, with one retained calibration failure; all 70 favored direct packed evaluation. ABC conversion and truth checks completed 15 repetitions on all 71, but its subprocess wall is not matched to Python producer time. The recovered P14 bootstrap intervals have also been replayed from raw rows.

See [REVIEW_RESPONSE.md](REVIEW_RESPONSE.md) for issue-by-issue resolution and remaining submission requirements. See [reproducibility/README.md](reproducibility/README.md) for evidence, commands, and limits.

## Checks

- `python build.py` rebuilds the PDF with pdfLaTeX in a temporary directory and writes `BUILD_LOG.txt`.
- `python reproducibility/run_checks.py` verifies the pinned source and runs 123 selected tests, then recounts S1/S2/P14 observations and reruns the unmodified supplied audit checker. The runner passes in a clean virtual environment with a recorded transitive dependency lock. It does not run a timing campaign.
- `python verify_manifest.py` verifies the current files in this folder. The manifest was refreshed after the final PDF build; it is a file inventory, not the synthetic or natural execution freeze.

The remaining empirical gate is task-matched natural synthesis comparison and the other protocol-v3 secondary cells. Historical P14 imported-runtime identity is not proved by its original freeze even though a compatible local runtime candidate has been located. Nothing was published, committed, or pushed.
