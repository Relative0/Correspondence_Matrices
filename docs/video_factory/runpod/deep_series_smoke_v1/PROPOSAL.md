# CM deep-series first-five RunPod smoke proposal v1

Status: **exact authorization requested; no remote or paid work performed**

This proposal renders two silent 1080p chapters—about 75 seconds each—to exercise all five visual primitives before the first five narrated videos are produced.

- Proposal: `cm-video-deep-series-first5-smoke-remote-v1`
- Bible: `6a02c82190f3d0771d830ac50052505b6c9407c607e9657d079ee0c4c8cd0f7e`
- Review manifest: `071d6aeecf378c8957f0beb114e561c6242942bd87406a5d7980ce7b2d9ae2fe`
- Bundle: `cd148f790d1bfc6945830172ff9c01fea1a916332e44bb104db37e7f8d3a6686`
- Batch: `50674a3b753074cc41070089af1813799af8376bd11a57ffe2ad84b78834be82`
- Work: 2 ordered jobs, 4,492 frames, 1920×1080 at 30 fps, silent
- Resource: one-at-a-time Secure RTX A5000 Pod; current exact quote $0.27/hour, LOW availability
- Ceiling: at most 2 sequential creates, never more than 1 live pod, at most 3 hours per pod, and at most $2 total RunPod spend
- Cleanup: delete on every terminal path and reconcile that no owned pod remains

All six CPU flavors reported zero availability at quote time, so this proposal uses the cheapest currently available Secure GPU Pod as a CPU rendering host. The GPU is not required by the renderer. No persistent volume, publication, commit, push, narration, complete-video render, or remaining-series job is included.
