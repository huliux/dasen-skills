# Usage and dependency selection

Read the consumer's business constraints and the complete selected `SKILL.md`; follow its conditional references. Start with the user's intended outcome, not configuration. Use registry/packs for actual stage/dependency membership. Installation guidance is [paired](en/installation.md); existing source managers remain optional.

`dasen-content` handles series startup/continuation, standalone writing/revision, status inspection, and delivery routing. The detailed behavior belongs to [workflow](../skills/dasen-content/references/workflow.md). It reuses available answers and asks only for material decisions; status inspection stays read-only.

Resolve the [content root and layout](../skills/dasen-content/references/content-paths.md), then explicit workspace-relative project file → content-root project.md → standalone. No global project configuration is read. A series requires its project/series; ordinary writing and local rendering do not. Brand defaults to unset. Dasen is the distribution identity; Bitbook is a separate optional product/context integration.

One writing stage applies the frozen Style. Projects can own multiple private Styles, series choose an ID, and an article may override it. Body and cover use separate Visual Styles. Keep Style, layout, asset role, render method, provider/model, and channel formatting independent. Catalogs are read-only in content tasks.

Optional Agent Reach, AIHot, or Bitbook context does not replace authorization or evidence gates. Fall back to suitable native retrieval or supplied material when integrations are absent. Runtime tools and external Skills are separate dependency classes. Local WeChat formatting needs no account; real draft delivery is separately authorized. A dry-run, test asset, draft receipt, and public publication are different outcomes.

Content artifacts stay in the consumer workspace; Skill implementation changes return to its source. Retain project-specific examples and receipts, and reference maintained generic instructions rather than copying their tutorials.

Research reuses relevant Wiki evidence before filling source gaps; new ingestion needs a confirmed batch. Plain writing has no render/Asset Check requirement. The three white native HTML themes live in [themes](../skills/dasen-wechat/themes/README.md).
