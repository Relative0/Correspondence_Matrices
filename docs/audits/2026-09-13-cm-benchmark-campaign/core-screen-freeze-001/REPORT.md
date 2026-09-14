# Bounded core results screen

Status: locally ready; exact fourth-Pod approval pending.

The frozen screen has 36 pre-outcome-selected cases and 192 fresh-process cells: 48 exact-count cells (Ganak and d4), 24 unpaired projected-count cells (Ganak only), 72 biology fixed-point cells (CM scalar and Biodivine AEON), and 48 affine solution-count cells (CM packed elimination and an independent sparse-set elimination). Each case/arm has three repetitions where paired. The projected lane is explicitly excluded from CM speedup claims.

Every selected input is present in the existing 11-shard upload set and matches its frozen SHA-256. Each cell has a 60-second limit; new work stops after 3,600 seconds; unstarted cells are recorded `not_run`. The Pod/controller adds no benchmark corpus beyond the 11 shards. It transmits only the separately hash-bound runner and plan.

Local validation passed 19 focused tests, including direct execution of the biology scalar path and both affine arms, plus compilation and payload-injection checks. The native Linux image smoke already completed successfully on `runpod-primary-003`; the subsequent failure was the now-deselected Git-only source-identity test. A local Docker replay was unavailable because no Docker daemon was running.

The read-only 2026-09-14 live quote is Secure `cpu3g`, 16 vCPU, 64 GB RAM, HIGH availability, $0.64/hour. A two-hour Pod plus prorated 30 GB container disk is estimated at $1.288333; the requested phase cap is $1.35. Both RunPod inventories were empty.

Frozen identities:

- Upload manifest: `f12864a3d072062526ea298aaa1c14ec8a6cb972314de7e9762bf21ba1277e72`
- Plan file: `a3d57313e255ddd5ab2455c0067a094b0921b57fce200f7aac5227033e760abc`
- Core-screen runner: `92637f101559c5a05b7399d74d4a1550520b643f1b0cd6ba59744b5d67ed52de`
- Remote worker: `6c8b6b5d474990aa0d5fdcbf9d5c76ac946fadad76256ebf2991ff78f40d7e94`
- Results controller: `9a9c4e6dd928258be8b7d95895c21a10a4450e86c6fa6f557bf8a6eaeda4ac30`
- Exact approval request: `b0c60bfe6b293d36bb21b7019ea8c5187cc5d90359506210b4b04da2a939c95a`
