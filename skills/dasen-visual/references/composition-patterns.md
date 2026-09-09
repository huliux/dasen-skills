# Composition patterns

Choose a structure for the content relationship, not variety for its own sake. First assign job: evidence|explanation and acquisition.mode: official|web|capture|user|create. Existing pixels retain original copies/source/treatment/review; only create continues into Style, Direction, composition, and Adapter.

## Style and composition

The catalog lives in dasen-content/references/visual-styles.yaml. Style defines visual language; composition arranges information. Neither is named for a provider/model.

| Signal | Body recommendation | Cover recommendation |
|---|---|---|
| General knowledge, lists, comparison | body-clean-editorial | cover-clean-editorial |
| Systems, code, call paths, risk | body-technical-dark | cover-cinematic-system |
| Abstract mechanisms, teaching, feedback | body-whiteboard-clarity | cover-knowledge-glow |
| Real experience, interviews, human action | body-clean-editorial | cover-human-editorial |

Ordinary conversation recommends the first suitable option plus same-role alternatives; skip uses the general fallback. Autonomous selection records its article-specific rationale, not merely aesthetic preference. Body and cover may come from different rows; this table is not a paired binding.

## Per-asset Direction

Keep Style stable and express this asset's variation in the plan. Chinese labels below are example image content.

```yaml
job: explanation
acquisition: {mode: create}
render_target: {width_px: 750, height_px: 1250, display_width_px: 375}
content_slots:
  input: ["材料", "问题"]
  steps: ["研究", "写作", "验证"]
  output: "可核验结论"
direction:
  focus: steps             # Must name an existing content slot
  density: balanced       # sparse | balanced | dense
  include: [feedback-loop]
  omit: [mascot]
```

Existing images use acquisition receipts rather than rendering controls:

```yaml
job: evidence
acquisition:
  mode: web
  locator: https://example.invalid/image.png
  acquired_at: 2026-09-09T12:00:00+08:00
  local_path: assets/2026-09-09/topic/body-01-source.png
  sha256: <64 lowercase hex>
  width_px: 1600
  height_px: 900
treatment: {mode: preserve, note: ""}
review: pending
```

Content slots contain semantic headings/nodes/evidence labels; lowercase slug keys and single-line strings/lists, without render controls. Focus names exactly one existing slot rather than free-form instructions. Density cannot exceed the Style's display-font/information-unit limits. Include/omit controls safe optional modules, cannot overlap, and cannot remove required canvas/safe areas.

Allowed include modules: feedback-loop, status-key, comparison-baseline, evidence-caption, output-panel, metric-strip, signal-path, human-context. Omit additionally supports mascot, decorative-background, secondary-copy. They are optional composition vocabulary, not mandatory templates; identity/required Style components are outside their control.

Direction and content-slot keys cannot override palette/font/brand/size/provider/model/safety. Render Target separately holds positive width/height/display-width with display_width_px <= width_px. The adapter converts scale to source-font/safe-inset requirements. Schema v3 explicitly requires slots, Direction, and Render Target; v1/v2 may be read compatibly but missing targets cannot prove phone typography/crop checks. Keep one-off variation in the article; extraction follows the shared visual contract.

| Relationship | Composition |
|---|---|
| Input/process/output | One left-to-right path, 3–5 nodes |
| Before/after | Shared-scale side-by-side comparison |
| Choice/routing | One entry, 2–4 branches, applicability at exits |
| Feedback | 3–5 node loop, main feedback arrows only |
| Hierarchy/scope | Nested layers or stacked boxes with containment |
| Time | One-way timeline with consequential changes |
| Risk/limits | Style risk-color interruption beside the main process |
| Data | Common-scale bars/dots with source caption |

State what the image explains in one sentence. Choose relations before decoration; remove elements that do not change understanding; reuse article terminology; repeated images of a topic need a different information task, not just another color.
