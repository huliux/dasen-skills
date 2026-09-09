---
name: dasen-writing
description: Write or revise sourced Chinese non-fiction from brief.yaml and sources.md. Run only when routed by dasen-content or explicitly requested. Follow the frozen writing Style, produce article.md, and run prose checks. Extract a private project Style from authorized samples only on explicit request; do not retrieve sources, create visuals, or publish.
license: MIT
metadata:
  version: 3.0.1
  invocation: router-or-explicit
  compatibility: Requires Python 3.10+. Non-fiction research requires dasen-research or equivalent source files.
---

# Dasen Writing

Project constraints define author/channel, the brief defines this article's goal, and sources bound factual claims. Never inherit a persona from another article.

## Inputs

1. Read `../dasen-content/references/contracts.md` and locate the actual package.
2. Read brief, sources, and any existing article. Read project configuration only when bound by the brief; standalone needs no project. Record a blocker if the source gate is unmet, important evidence is missing, or paths conflict.
3. Use one writing Style: `brief.profile` is its ID and `brief.style_profile` its frozen rules. Follow the snapshot without combining another style Skill. Built-ins are in `../dasen-content/references/writing-styles.yaml`.
4. For `pattern-adapt`, read [structural adaptation](references/pattern-adapt.md). For `revise`, retain verified facts and explicit conclusions from the original.

For an older schema-v3 brief without a Style snapshot, resolve a built-in ID from the catalog or a private ID from its project library. Never infer rules from a name. Writing Style governs voice, rhythm, structure, and evidence presentation; visuals and platform format belong to their stages.

## Draft

- Follow compiled `word_count.min/max`, not another fixed length. Narrow or block when evidence cannot sustain the requested length.
- Map important claims to source IDs before drafting. First-person experience must come from authorized original material in `verified_experiences`; otherwise use neutral narration.
- Preserve required title, author, H1, follow-guide component, topic label, and placement wording from project/brief. Do not persist article-only requirements upstream.
- Each paragraph advances one issue through a new fact, action, number, explanation, boundary, or judgment. Merge synonymous repetition.
- Put evidence near judgments and time/population/measurement definitions near numbers. Mark unknowns explicitly.
- Open with the event or question; end with action, limits, or the next observation rather than repeating the article.
- Use clear Markdown headings, lists, quotes, tables, and code where useful. Other stages handle images and platform layout.

## Optional private Style extraction

Only on explicit request to reuse authorized samples; it is not a standalone prerequisite. Prefer at least three representative samples and record project-relative paths, extraction date, and conflicts in the project library.

Extract stable cross-sample voice, rhythm, structure, and evidence habits; one-off phrasing remains a candidate. Use a unique stable lowercase ID. If needed, choose one project YAML library path and configure `writing.style_library`. Built-in catalogs are read-only during content work. Do not copy sentences, distinctive metaphors, catchphrases, private experiences, or another author's identity; external samples yield neutral general traits.

Present the profile for confirmation, then use `../dasen-content/scripts/style_profiles.py` to save it. `sample-derived` requires at least three `sample_refs` and records conflicts; pass `--confirmed` only after approval. Select the ID for a series/article afterward; do not silently change project defaults or create a new Skill. Revisions require current `expected_revision`; fundamentally different styles need new IDs.

## Verify and hand off

Write `article.md` with required frontmatter. Read [revision checks](references/revision.md) and review facts, structure, language, and delivery. Run:

```bash
python <skills-dir>/dasen-writing/scripts/check_prose.py writing/YYYY-MM-DD/<slug>/article.md
```

Clear every `ERROR`. Review each `WARN` in context and record why it remains or revise it; the checker identifies candidates, not editorial truth. Remove placeholders. On success set `drafted` and append Style ID/revision, word count, source count, checks, and revision rounds to record.

Completion requires traceable key facts, no fabricated experiences/quotes/tests, the promised outcome within the requested length, meaningful paragraph progression, visible limitations, complete publication fields/components, and reviewable checks. Record unresolved risks as blockers. If the user requested only prose, show only the prose rather than internal claim maps or review drafts.

Text-only completion uses article.md, sources.md and the actual Writing Preflight/Delivery receipts. HTML rendering and Asset Check belong only to requested platform/visual work routed by dasen-content.
