# CM comprehensive benchmark research package

Prepared 13 September 2026. **80 proposed test families, 42 primary sources, no new benchmark run or cloud launch.**

- [Research report](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/REPORT.md): findings, workload recommendations, fairness protocol, 24–32-variable scaling and amortization.
- [Complete test catalog](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/CATALOG.md): all 80 families with sources, requested outputs and admission conditions.
- [RunPod mega prompt](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/RUNPOD_MEGA_PROMPT.md): bounded local implementation, cloud-approval gate, multi-hour execution, analysis and cleanup.
- [Historical SymPy audit](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/HISTORICAL_AUDIT.md): reaggregated archived observations and why they are not matched-task speedups.
- [Primary-source registry](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/SOURCES.md): publisher, edition/date, URL and use for all consulted sources.

Machine-readable companions are [CATALOG.json](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/CATALOG.json), [SOURCES.json](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/SOURCES.json), [CAMPAIGN_PLAN.json](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/CAMPAIGN_PLAN.json) and [HISTORICAL_AUDIT.json](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/HISTORICAL_AUDIT.json).

The proposed first campaign targets 2,400 base cases, calibrated to a proposed $50 / 16-total-pod-hour cap. Neither spending nor upload is approved. Dataset payloads and revisions are not yet frozen; source admission and adapters are execution work, not a completed result of this package.

To regenerate only this package's derived catalog/source/audit/plan files from the repository root:

```powershell
& .\.venv\Scripts\python.exe -B docs\research\cm-benchmark-research-2026-09-13\build_research_package.py
& .\.venv\Scripts\python.exe -B docs\research\cm-benchmark-research-2026-09-13\verify_package.py
```

These scripts do not run benchmark methods, import project code, access secrets, download datasets or launch cloud resources. Validation checks package consistency and historical arithmetic, not the algorithms' performance or the latest remote contents.
