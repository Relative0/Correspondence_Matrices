# Test commands and outcomes

From `C:\Users\brian\Documents\CM_Computation`, using the project interpreter:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\test_packed_mask_construction.py tests\test_bitset_backend.py tests\test_bitset_cse.py tests\test_prepared_flat_evaluation.py tests\test_bitset_engine_policy.py tests\test_context_caches.py -q -p no:cacheprovider
```

Result: 67 passed in 6.06 s.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\test_build_memo.py tests\test_cm_ir_cost.py tests\test_cm_ir_wide_associative.py tests\test_persistent_path_consistency.py tests\test_cm_persistent_ir_cache.py tests\test_foreign_node_interning.py tests\test_share_aware_flatten.py tests\test_expr_serde_v2.py tests\test_output_budget.py tests\test_partial_full_vars_reference.py tests\test_truth_table_conversion.py tests\test_cm_comparative_restricted_evaluators.py tests\test_native_restriction_backend.py -q -p no:cacheprovider
```

Result: 173 passed, four subtests passed, two setup errors in 8.37 s.
Both errors were `PermissionError` opening pytest's existing default temporary
directory at `C:\Users\brian\AppData\Local\Temp\pytest-of-brian`.
The following retry with approved filesystem access passed both tests in 1.36 s:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\test_cm_comparative_restricted_evaluators.py::test_manifest_source_hash_changes_when_bitset_backend_changes tests\test_native_restriction_backend.py::test_changed_native_binary_is_refused_before_loading -q -p no:cacheprovider
```

Result interpretation: 242 distinct tests passed, plus four subtests. The first
setup errors are retained here; no test was disabled or rewritten to obtain a
pass. The full repository suite was not run because this change touches only
packed environment construction and the related validation surfaces.
