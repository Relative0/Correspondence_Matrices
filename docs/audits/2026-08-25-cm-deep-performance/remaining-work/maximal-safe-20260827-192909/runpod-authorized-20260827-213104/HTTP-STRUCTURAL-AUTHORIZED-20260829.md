# Authorized Runpod structural validation — 2026-08-29

Brian authorized the exact study in
`RUNPOD-NEXT-STRUCTURAL-VALIDATION-PROPOSAL-20260828.md`:

> I authorize the next structural validation study: k=6,8,12,16 across five
> families, 360 calls/1,560 planned rows, one zero-volume CPU pod, 20 minutes,
> $0.10 phase/$0.20 campaign caps, and no replacement?

The leading statement "I authorize" grants the one attempt; the trailing
question mark does not expand or alter the linked proposal. The linked proposal
controls all details.

Authorized execution is limited to one Secure CPU pod with 2 vCPU and at least
4 GB RAM, the pinned Python image, the same frozen 65-file/13-wheel payload,
12 GB container storage, zero pod volume, no network volume, HTTPS proxy ports
8080/8081, and the focused 70-test gate followed by only the specified
five-family structural study. The controller and independent watchdog each
enforce the 20-minute horizon. There is no automatic or manual replacement
under this authorization.

Budget gates are at most $0.25/hour, $0.10 projected for this phase, and $0.20
projected across the campaign, with at least $0.02 reserved for the two prior
actual HTTP allocations or higher attributable billing if observed.
