# CM deep-series v2 authoring and preview architecture

Authoritative curriculum data flows from `episode_content_bible.json` into sentence-level narration, captions, claim bindings, storyboard beats, chapter cache contracts, renderer briefs, and local review assets. JSON is authoritative; Markdown, VTT, PNG, and GIF files are review surfaces.

The renderer route reuses the existing versioned POP `cm_science` content pack and the `technical_reference` theme. Its supported scientific primitives are expression/matrix, representation comparison, transformation comparison, boundary pipeline, auditable ratio, and result panels. Preview frames use explicit progress, half-open intervals, and no wall-clock animation.

Each episode and chapter is content-addressed. The production plan disables remote work until both content approval and a separate exact RunPod authorization exist. This authoring pipeline has no RunPod client, upload, resource-creation, publication, paid voice, or generative-media path.
