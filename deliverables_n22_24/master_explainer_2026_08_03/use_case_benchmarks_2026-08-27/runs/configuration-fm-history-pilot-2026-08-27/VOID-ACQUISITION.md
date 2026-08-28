# Void full-cohort acquisition attempt

**Date:** 2026-08-27  
**Status:** void before source provenance, DIMACS parsing, correctness evaluation, or timing.

The preregistered full 40-endpoint run stopped while acquiring the second payload from the pinned official Feature-Model Benchmark commit. GitHub accepted the filtered repository clone but rejected the attempted direct fetch of blob `1e26c0f68add6ff8f04960f67d3710f5e0aced7f`:

```text
fatal: bad revision '1e26c0f68add6ff8f04960f67d3710f5e0aced7f'
error: https://github.com/SoftVarE-Group/feature-model-benchmark.git did not send all necessary objects
```

Unfiltered shallow-clone and browser-archive fallbacks also stalled before receiving payload bytes. No model was parsed and no performance result was produced in this directory. The runner and V2 protocol remain valid for a future retry from the same exact source commit.
