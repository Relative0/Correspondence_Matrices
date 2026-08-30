# Native-gap campaign V12 authority reconciliation

Date: 2026-08-29  
Status: authorized

The V11 controller made no create request because a concurrent task replaced
its authorization file with a refusal based on an older one-attempt/no-
replacement authorization. That conservative record is preserved.

The user's newer instruction explicitly authorizes closing all three remaining
native-representation gaps, continuing the subsequent tests, and automatically
retrying failed tests while aggregate testing cost remains below `$10`. This
newer, broader instruction controls V12. It does not retroactively alter any
older frozen authorization.

V12 carries forward the exact V11 measurement-fence workload: 37 files,
5,507,655 bytes, 65 focused tests, 144 P5 cells, pinned dependencies, bounded
read-only upload-status retry, bounded procfs rereads, one Secure 2-vCPU pod,
12-GB container disk, integer-zero pod volume, no network volume, a 20-minute
lifetime, ownership-only cleanup, `$0.10` phase cap, and `$10` aggregate
campaign ceiling. This controller performs exactly one create request.
