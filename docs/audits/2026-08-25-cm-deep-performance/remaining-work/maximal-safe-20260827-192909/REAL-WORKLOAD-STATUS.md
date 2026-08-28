# Real-workload status

No metrics-ready owner declaration was found in the scoped repository scan. Only the retained cm-real-workload/v1 template and its validation artifact matched the intake schema. New files under the website use-case benchmark area were checked only for that schema, not for their benchmark findings. No application caller boundary was supplied.

The active library consumers remain benchmark/audit scripts and the remote benchmark worker. A real circuit or feature-model revision in a benchmark does not establish an owner-approved application capture boundary.

WORKLOAD-TEMPLATE-VALIDATION.json preserves the strict validator result and input SHA-256:
f7b07a04b6ffc2181806bd41b31f5bda36dd66720ffaa9b2576e3d302f1bd1dd.
It reports pass, template status, metrics-ready=false, replay-ready=false, external-upload=false, and 13 blockers.

## One intake block for Brian

Copy the existing WORKLOAD-MANIFEST-TEMPLATE.json from the prior three-lane campaign to a new file and supply:

~~~text
Workload label and owner role:
Application/repository or system:
Exact caller function/API boundary:
Requested artifact and variable/bit ordering:
Expected calls per expression:
Process lifecycle and whether cold starts/phase changes matter:
Maximum output bytes / estimated temporary bytes / cache bytes / latency:
Capture duration or total natural calls:
Metrics capture approved: yes/no
Replayable expressions approved: yes/no
Replayable contexts approved: yes/no
External upload approved: yes/no; exact destination and content if yes
Initial sampling: 1 in 16; maximum 1 MiB per file; explicit file-count limit
~~~

Do not replace unknown facts with generated traffic. Capture remains off. A valid declaration must pass scripts/cm_validate_workload_manifest.py and report ready_for_metrics_capture=true before integration at the named caller.

Cache requires 10,000 prepares (or a complete smaller workload), two lifetimes and a phase change. Family requires 200 transitions/20 families (or complete smaller population). Context requires 500 natural transitions/five streams. Selector/native requires 50 formulas/500 k=13..16 calls; selector opportunity at k=13..15 must be at least 3%. No lane cleared these gates here.
