# Additional isolated construction-memory accounting

Before executing this panel, freeze its cases to exactly the previously frozen cold panel: every selected natural design and the synthetic m=8 cases, all eight methods, k=min(2,n), batch=64. Include unsupported outcomes. Each trial runs in a fresh process from construction through verification, serialization, reload and actual prefix count batches. Absolute peak RSS can therefore be attributed to that process lifecycle without inheriting earlier methods' high-water history.

This panel remedies the interpretation limit of in-process producer RSS; it does not change any storage prediction, method, timing panel or favorable-case rule. Extra query/update counts are reported separately, and instrumentation timings are not pooled into primary comparisons. One process per case/method is used, matching the cold panel rather than selecting observed winners.
