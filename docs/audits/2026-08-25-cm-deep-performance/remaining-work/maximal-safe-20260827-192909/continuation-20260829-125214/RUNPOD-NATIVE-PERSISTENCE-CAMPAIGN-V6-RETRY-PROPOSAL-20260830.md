# RunPod native persistence campaign V6 retry proposal

This retry preserves the complete V5 remote workload and exact 136-file/5,494,221-byte upload identity. V5 pod `hmqvleqhp5n815` passed resource and dual-port health validation but received a transient HTTP 404 at the resumable upload boundary before any source file was accepted. It was deleted with HTTP 204, both inventories reconciled empty, and estimated compute cost was $0.0004298830946286519.

V6 changes only the local transport controller: an exact `proxy HTTP 404` during a chunk POST is handled like the already-reviewed transient connection/read-timeout cases, followed by bounded status reconciliation. All other runtime errors remain fatal. No remote program, project source, dependency, test selection, resource, cost, acceptance, or cleanup condition changes. This controller may create exactly one replacement under the user's explicit external-upload approval, automatic-retry instruction, and aggregate $10 cap.

