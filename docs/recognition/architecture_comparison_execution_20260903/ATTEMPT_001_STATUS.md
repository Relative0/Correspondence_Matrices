# Architecture comparison RunPod attempt 001

Attempt 001 is closed as incomplete before measurement. The controller created
one validated Secure CPU pod at $0.06/hour, installed the hash-locked runtime,
and then stopped when parent-freeze verification found that the upload manifest
did not contain `cmbench/backends/native_restriction.py`. No timed schedule row,
result envelope, independent verification, selector fit, training, routing
change, website update, or publication was produced.

The controller did not create a replacement. It deleted the owned pod and
verified that both RunPod inventories were empty. The estimated compute charge
was $0.0009372. The exact machine-readable closure and evidence identities are
in `ATTEMPT_001_STATUS.json`; the complete controller/evidence directory is
`runpod-architecture-comparison-execute-001/`.

A retry must use a newly generated manifest containing every path in the
parent freeze's source closure, must exercise parent-freeze verification inside
the isolated package test, and requires a new exact user authorization. The
authorization for attempt 001 cannot be reused.
