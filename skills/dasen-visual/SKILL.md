---
name: dasen-visual
description: Find, capture, reuse, or create traceable visuals for a content package. Run only when routed by dasen-content or explicitly requested. Match assets to brief/article/sources using official or web images, task screenshots, user assets, or explanatory graphics. Do not default to image generation or inject products/author identity.
license: MIT
metadata:
  version: 5.0.0
  invocation: router-or-explicit
  compatibility: Shot lists work in any text runtime. Project receipt helpers require Python 3.10+ and PyYAML. Image generation requires an available image-generation tool; screenshot and asset checks require local file access.
---

# Dasen Visual

Visuals support evidence and understanding. Select the asset that best serves the article before choosing existing pixels, capture, or creation. Official origin, self-creation, and Style compliance are not universal priorities independent of the task.

## Preparation

1. Read identity, external-content, and asset contracts in `../dasen-content/references/contracts.md`, then brief/article/sources.
2. Use the frozen `brief.visual.body.style` for body assets and `.cover.style` for covers. Do not re-resolve snapshots after catalog changes.
3. In ordinary conversation, with no specified Style or cover reference and before package creation, use `visual_styles.py list` to offer one recommendation per role, alternatives, and skip; wait for the choice. Explicit skip/no-interruption uses defaults. In goal/autonomous mode as defined by contracts, select based on the brief without asking and record `visual.selection.mode: agent` with a specific reason.
4. Read `references/composition-patterns.md` for composition and per-asset Direction. Keep Style, Direction, layout, body/cover role, render method, and provider/model separate. For requested avatar/character/brand exploration, also read `references/identity-exploration.md`.
5. For a WeChat cover, read `references/wechat-topic-cover.md`. Topic-label rules apply only when a label exists or the project requires one. A reference image informs article-local layout or a confirmed private Style. Without a generation request, deliver a visual plan only.
6. Use `scripts/render_adapters.py` to resolve `html-css`, `image-model`, or `manual`. Once the plan is final, compile each created asset using `--visual-plan` and body `--asset-id`, producing ordered prompts, exclusions, Render Target conversion, text policy, postprocessing, QA, and `compilation_fingerprint`. Resolution/compilation does not call models. Probe/call providers only for authorized generation. Missing capability blocks only when `visual.generation.required: true`.

If requested generation is unavailable, report that capability and offer configured tools or manual handoff. Check current official provider instructions before account/plan recommendations; do not promise access based on a subscription name. Provider/model identifiers remain opaque project values and API keys stay outside Skills.

## Asset selection

Mark each article anchor `job: evidence` for a real interface/result/data/mechanism or `job: explanation` for explaining relationships, processes, or comparisons. Select `acquisition.mode`:

- `official` / `web`: existing public images, using suitable installed search or native retrieval.
- `capture`: a public page, current task page, or authorized real result.
- `user`: preserve the user's specified image as the default first choice; disclose factual conflicts rather than silently replacing it.
- `create`: HTML/CSS, plotting, image generation, or manual design when existing assets cannot accurately do the job.

Except for user-specified assets, compare article relevance → information accuracy → clarity/resolution → source authority → visual consistency. English labels, different colors, and pending mobile review do not automatically disqualify candidates. Missing license metadata does not prevent discovery/draft consideration; final use requires review before publication. Abstract backgrounds are not real-result evidence. Do not add images merely to meet a count.

Immediately save an untouched project copy of each non-created candidate. Record a credential-free original URL or project-relative source, timezone-aware acquisition time, project-relative path, SHA-256, dimensions, treatment, and `review: pending`. Pending assets may enter drafts; only the user's choice changes them to accepted/rejected. Treatments are preserve/crop/annotate/translate, default preserve. Derived assets receive separate paths/hashes. Acquisition is independent of local/platform-upload/stable-cdn delivery.

## Workflow

Project identity exploration follows its reference and project asset records, not article gates. Before prose stabilizes, provisional planning may remain in conversation. Write final `evidence/visual-plan.yaml` and run Asset Check only after reading stable prose.

1. Identify useful results, steps, comparisons, data, and limits. Give each anchor a job and one-sentence purpose; understanding determines the count.
2. Select relevant existing/user/captured assets first; create only when necessary for the task. Style governs created pixels and surrounding captions/layout, not existing image pixels.
3. If a cover is required, produce its Style-bound brief; generate only with an available authorized provider. A generated cover is not factual evidence.
4. Use the schema-v3 plan in composition patterns. Every new/revised shot has job/acquisition. Existing images have source/treatment/review receipts; created ones have Style, semantic content, Direction, layout, Render Target, and Adapter. Do not invent separate shot-list, cover-brief, and adapter-plan filenames.
5. Compile only created assets. HTML/CSS implements tokens, geometry, and text exactly; image models receive Style/composition guidance, with critical text laid out afterward by default; manual yields a handoff package. Generate per authorized asset, one structure per image.
6. Read `references/qa-checklist.md` for correspondence, provenance, and redaction. Review created body assets at `display_width_px`; record existing assets' actual dimensions and let the user judge them in the draft, without a mandatory mobile-preview discovery gate.
7. Check capture scope. Public/current-task pages may be captured; private authenticated pages, communications, and unrelated windows need explicit authorization. Remove secrets, contact details, chats, and customer data before incorporation; record cropping/redaction.
8. Preserve user assets, checking original SHA-256 and dimensions. Derive only when requested or required for platform acceptance, retaining the original.
9. If this request requires human cover confirmation, show the final local image before remote storage upload or draft overwrite.
10. Save image binaries beneath frozen `<assets.root>/YYYY-MM-DD/<slug>/` (standalone defaults to content-root `assets/`). Package `evidence/` contains textual plans/prompts/manifests. Record paths, sources, treatments, and review state in `record.md > Asset Check`.

## Private Styles and identity

Built-in Style IDs are read-only during content work. On explicit extraction/addition, configure `visual.style_library`, write a project-relative definition, obtain confirmation, and use:

```bash
python <skills-dir>/dasen-content/scripts/visual_styles.py save \
  --project-file project.md --definition <project-relative-style.yaml> --confirmed
```

`sample-derived` requires at least three same-role samples. The script records hashes/revision and refuses built-in ID overwrites. Extract stable color roles, hierarchy, geometry, composition tendencies, and exclusions. Third-party brand names, logos, proprietary fonts, source wording, and pixel templates do not enter built-ins. A one-off reference or Direction does not become a persistent Style automatically; later extraction still needs confirmation.

Disabled `product_placement` forbids the configured product/logo/promotion. Disabled `author_persona` forbids the configured author's name/avatar/contact details. The dasen namespace does not authorize watermarks or branding in user content. Do not reuse another creator's characters, mascots, visual IP, or distinctive composition.

## Handoff

Report actual created/saved counts, article positions/purposes, files/sources, required/optional assets, and missing real screenshots. Include job/acquisition/treatment/review for each asset; created ones also need Direction, Render Target, Adapter, fingerprint, compiled text, and postprocessing boundaries. State explicitly when only planning is complete.

For a required generated cover, include actual Style ID/revision, Adapter, provider/model, layout, `cover-prompt.md`, source/final image paths, `cover.yaml` with SHA-256, and applicable storage receipts. Missing required evidence blocks the stage. Use `cover_receipts.py register-template` / `finalize-cover` for project layout references and final receipts; inspect `--help` rather than copying hashes manually.
