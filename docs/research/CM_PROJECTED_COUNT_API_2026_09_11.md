# Exact projected CNF counts

`ProjectedCNFCountPlan` counts distinct assignments to selected variables after existentially eliminating the others. Multiple auxiliary witnesses contribute once. It accepts the same strict CNF, expression and CM-node ingress as the bounded bucket API, with arbitrary-precision integer answers.

```python
from cmbench.backends.projected_counts import ProjectedCNFCountPlan
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan

# p OR h: three complete models, two distinct assignments to p.
plan = ProjectedCNFCountPlan([(1, 2)], ('p', 'h'), ('p',))
assert plan.count() == 2
assert plan.count({'h': 0}) == 1
assert plan.count({'p': 1}) == 1
assert NumpyBucketCNFCountPlan(plan).count() == 2
```

An empty projection returns zero or one. Unused selected variables multiply the answer; unused existential variables do not. Fixed assignments can mention selected and hidden variables. Fixed selected axes are held constant and are not counted again. Invalid names, non-Boolean contexts, duplicate projection names and unsupported inputs are rejected.

The plan eliminates every hidden variable with Boolean OR before summing over selected variables. Changing that order can overcount. The ordering restriction can increase width dramatically: a shared hidden variable coupled to many selected variables is a deliberate refusal case under the width bound. No fallback, approximation, truth-vector expansion or division of a full model count hides that refusal.

The default limits remain explicit: width 14, at most 2,048 variables, 16,384 clauses, and bounded table, elimination and ordering work. The NumPy adapter keeps object integers and its independent array-cell bound. Bounds constrain planned cells/work, not total process RSS or arbitrary caller retention. Queries allocate private intermediate tables; tested concurrent callers can share a read-only plan. Callers should not mutate plan internals.

The comparative task boundary also accepts explicit `bucket_count`, `array_count`, `factorized_count`, `independent_count` and `affine_count` backends for exact-count, SAT-status, partial-context and version-history outputs. Existing default backend lists and routing remain unchanged. Affine input and scalar-output restrictions remain explicit. The existing task contract is bounded to small scenarios; the integration is a tested repository consumer, not evidence of a deployed production workload.

Validated expression DAG JSON remains the inert persistence format. Reload validates and recompiles; it is not a persisted compiled-plan format. The continuation measures its decoding, disk, preparation and storage costs separately from resident reuse. No new binary persistence format is justified merely by the existence of a serializer.

Evidence and all favorable, unfavorable, refusal and incomplete outcomes are in `docs/audits/2026-09-11-cm-next-research/`. Earlier audit source versions are retained in frozen payloads rather than overwritten when this opt-in implementation changes.
