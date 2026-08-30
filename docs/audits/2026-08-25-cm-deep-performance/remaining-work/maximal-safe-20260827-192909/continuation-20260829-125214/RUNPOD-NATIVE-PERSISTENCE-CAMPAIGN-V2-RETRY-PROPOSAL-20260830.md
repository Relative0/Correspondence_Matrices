# RunPod native persistence campaign V2 retry proposal

This retry preserves the complete V1 workload, 136-file upload manifest, dependency identities, resource limits, cost limits, exactness gates, and cleanup controls from the V1 proposal.

V1 pod `jof02fgwixhwj8` failed before native dependency installation because the temporary remote program location was first on `sys.path`, so the uploaded project-root `scripts` namespace was not importable. V1 retained partial evidence, reported unchanged source identity, deleted the pod with HTTP 204, and reconciled both inventories as empty. Its estimated compute cost was $0.0007711103161176046.

The only workload-code correction is to insert the exact uploaded project root `/workspace/cm-native-persistence-scout` at the front of `sys.path` before importing the hash-bound dependency installer. No project source/data file or upload-manifest identity changes. This separately frozen controller may create exactly one replacement under the user's explicit external-upload approval, automatic-retry instruction, and aggregate $10 cap. All V1 acceptance and mandatory-cleanup requirements remain in force.

