# Clarifications after the frozen v4 run

These notes do not change the frozen plan, code, corpus, raw rows, analysis, or decision rule.

- The protocol's phrase “independently selected for negation” is imprecise. The frozen generator uniformly samples exactly 204 of 410 primitive input positions **without replacement** for each formula. The resulting sign indicators within a formula are dependent. Formula seeds remain the independent workload units.
- Power mode was omitted from the premeasurement environment file. A read after the run found the Windows Balanced scheme; [ENVIRONMENT_POSTRUN.json](ENVIRONMENT_POSTRUN.json) records that observation. It does not prove the power setting was constant during every timed case. The large negative point estimate remains a local measurement under this limitation.
- Process peak working set includes common Python and imported-module memory. It is a declared gate metric, but the measured -1.56% difference should not be interpreted as a useful memory saving for the CM representation.
- The original P14 analyzer's full output was not regenerated within a 600-second local timeout. The separate archived-seed bootstrap replay reproduces all 17 numerical interval sets; this does not resolve the historical imported-runtime identity.
