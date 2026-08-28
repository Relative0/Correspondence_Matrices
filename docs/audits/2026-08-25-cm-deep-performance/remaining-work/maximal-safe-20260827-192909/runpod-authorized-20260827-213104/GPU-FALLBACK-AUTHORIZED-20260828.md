# GPU fallback authorization received

Brian's latest reply, “Yes, you can, please do”, explicitly approves the immediately preceding GPU fallback question and `GPU-FALLBACK-AUTHORIZATION-PROPOSAL.md`.

Approved effect: at most one Secure NVIDIA RTX PRO 4000 Blackwell pod for the unchanged smoke; compute at most $0.58/hour, total campaign at most $0.20 including storage and earlier observed smoke charges, lifetime at most 20 minutes. The exact 65-file manifest, 13-wheel lock, pinned image, workload commands, deadlines, evidence cap, and teardown safeguards remain unchanged. No alternate GPU, automatic replacement, larger calibration, or additional upload is authorized.

The earlier proposal's “awaiting approval” text is historical. This record supersedes that status, not its technical limits. The new controller is `runpod_gpu_smoke_controller.py`; earlier executed controllers and evidence remain unchanged. Temporary host idle-sleep guards require AC power; the laptop must stay open, awake, and online.
