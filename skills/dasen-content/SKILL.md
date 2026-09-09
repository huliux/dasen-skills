---
name: dasen-content
description: The single dasen content entry for planning or continuing a series, writing or revising an article, inspecting progress, and preparing visuals or platform deliverables. Use for “策划系列”, “继续这个系列”, “写一篇”, “改这篇稿”, “看看内容进展”, or “排版发布”. Resolve intent before creating a brief; status inspection is read-only. Pure news or information lookup belongs to research tools.
license: MIT
metadata:
  version: 5.0.0
  compatibility: Requires Python 3.10+ and PyYAML. Agent Reach and AIHot are optional preferred research integrations. Platform delivery may additionally require the dasen-wechat Python packages, FFmpeg, Remotion, or image generation tools.
---

# Dasen Content

Turn the user's content request into an explicit brief and coordinate stages through files. `dasen-*` identifies the distribution, never the user's content brand. Content identity comes only from optional project configuration and defaults to unset.

## Environment

If `dasen-skills.lock.json` exists in the consumer project, read the artifact-bound execution section of [shared contracts](references/contracts.md) before any script call, including checks. Installation recovery is separate from content work.

Check capabilities only when production needs them. Status inspection follows `references/workflow.md` without initializing or repairing files.

```bash
python <skills-dir>/dasen-content/scripts/doctor.py
```

Add `--project-file <workspace-relative-path>` for project capabilities. A missing core stage fails; optional capabilities are reported separately, without credential values. If dependencies are missing, inspect available interpreters and use an existing suitable one. Record the actual interpreter. If none works, retain usable prose and report incomplete packaging/gates; a prose-check pass is not a package pass. Installation dependencies belong to the distribution's installation guide.

## Resolve the request

1. Read `references/contracts.md` for file, state, identity, precedence, and safety contracts.
2. Read `references/workflow.md` to distinguish inspection, planning/startup, continuation, and production. Finish inspection or planning-only on that branch. Resume an existing package before initializing another.
3. Resolve the content root and owned paths using [content paths](references/content-paths.md). Resolve configuration: explicit workspace-relative `--project-file`, then content-root `project.md`, then `standalone`. Read `series.md` only for a bound series. Never read global project settings. Missing brand, account, visuals, or storage does not block an article or local rendering.
4. Resolve the three brief axes together: `journey: series|breaking|material`, `length: quick|standard|deep|custom`, and `method: original|pattern-adapt|revise`.
5. If the project requires a topic label, resolve exactly one `topic_label` in this round and preserve it verbatim in title and cover for every journey/method.
6. Select one writing Style: explicit article choice → series → project → built-in fallback. Freeze its complete rules in the brief.
7. Resolve body and cover Visual Styles separately. In ordinary conversation, on first entering actual visual production, with no specified Style or cover reference and before creating a package, read the catalog and present one recommendation per role, alternatives of that role, and “skip”; wait for the choice. An explicit skip or no-interruption instruction uses the fallback. Writing, revision, or imageless local rendering retains the initializer's `visual.selection`; complete with Writing/Delivery receipts (or Platform Preflight for requested HTML), keeping `selection.reason: null` in default/user mode. For goal/autonomous mode, apply the explicit conditions in contracts: select without asking and record a brief-specific reason. A generic instruction to use safe defaults does not itself waive the ordinary visual choice.
8. Create a package when the user has supplied enough information. Pause only for the high-risk/high-ambiguity cases in workflow. Keep Style, composition, purpose, render method, and provider/model separate.
9. Advance by state. Each stage reads its own inputs; record blockers instead of inventing missing outputs.

For a series or ongoing operation, suggest a project when needed:

```bash
python <skills-dir>/dasen-content/scripts/init_project.py --project example-project
```

Load brand, channels, persona, writing/visual Style libraries, editorial thresholds, layout, adapters, provider/model, assets, and storage only when the task uses them. Private Styles are data in `writing.style_library` or `visual.style_library`, not new Skills. Built-in catalogs are read-only during content work; additions use project write interfaces. Store environment variable names or credential locators, never secrets. Only the series journey requires both project and series bindings.

## Initialize production

Run from the consumer workspace:

```bash
python <skills-dir>/dasen-content/scripts/init_content.py \
  --id YYYY-MM-DD-topic-slug --journey material --length standard --method original \
  --objective "本篇要解决的问题" --audience "目标读者" --deliverable "读完拿到什么"
```

The default platform is `generic`; use `--platform wechat` for WeChat output. Series production also needs `--series-file series.md` and a project. Add the following only for the user's explicit request:

```bash
--product-placement --product-name "Product" --product-fact "已核验的功能短语"
--author-persona byline,first-person --persona-name "Author" --verified-experience "授权的真实经历"
--pattern-url <HTTPS-reference-URL>
--profile tutorial
--body-style body-technical-dark --cover-style cover-cinematic-system
```

Agent visual selection must supply both Style flags and `--visual-selection-mode agent --visual-selection-reason "<brief-specific reason>"`. A confirmed ordinary choice uses `--visual-selection-mode user`. For explicit skip/no-interruption, omit Style flags to freeze the fallback. Discover Styles with `visual_styles.py list`; save an approved project definition with `save --confirmed`.

Project → series → article options compile length, title, and source policy. Article overrides include `--word-min/--word-max`, `--title-min/--title-max`, `--title-forbid`, `--source-minimum`, and `--primary-required/--no-primary-required`. Facts, safety, privacy, and publishing permission are not overridable. Preview old-schema conversion with `migrate_config.py`; for saved namespace values use `migrate_namespace.py`. Write only after reviewing the targeted migration. Neither command upgrades Skill installations. Existing packages are never overwritten. See the two example briefs in `examples/` for combinations.

## Route production

| Need | Stage |
|---|---|
| Status or progress | Read-only workflow branch; stop after the summary |
| Start/continue a series | Resolve series and current article through workflow, then route the actual need |
| Fresh facts, platform evidence, sources | `dasen-research` |
| Writing/revision with sufficient sources | `dasen-writing` |
| Images/screenshots for stable prose | `dasen-visual` |
| Local WeChat format or authorized draft delivery | `dasen-wechat` |
| Video with a separately installed compatible stage | `dasen-video` (private optional extension, absent from public core) |
| Relevant Wiki evidence during research, or explicit knowledge operations | Read relevant Wiki through research; route explicit ingest/query/reflect/lint to `dasen-knowledge` |

Plain writing/revision ends at the requested manuscript with sources and Writing Preflight. Enter visual or native HTML production only when that output is requested; text-only delivery needs no Asset Check or HTML render.

For pure AI news lookup, prefer installed AIHot when suitable; for platform retrieval, prefer installed Agent Reach. Otherwise use available native retrieval. Do not create a package until the user wants content production. Future platforms use their own platform IDs and stages; do not invent a general adapter before a second implementation exists.

## Gates and completion

```bash
python <skills-dir>/dasen-content/scripts/preflight.py \
  --bundle writing/YYYY-MM-DD/<slug> --stage draft --append-record --update-status
```

Use `--stage render` for local platform output without credential reads or network writes, and `--stage publish` before authorized remote draft delivery. Any nonzero exit blocks the next stage.

Record performance only from a real platform dashboard, API, export, or human receipt. `record_performance.py --help` describes evidence reference, capture time/timezone, source type, and per-metric value/unit/platform definition. Snapshots accumulate evidence; they do not automatically change series hypotheses or Styles.

Inspection finishes with an evidence-backed summary and no writes. Planning-only finishes with the requested plan and agreed series artifacts, without starting an article. Production requires:

- Article-only requirements have not leaked into project/series defaults.
- Placement, byline, first person, and contact information obey their separate explicit switches.
- Important facts map to sources and applicable preflight has actually passed.
- Required local files, drafts, or video exist; state changes and remote actions have paths/IDs in record.
- For text-only delivery, writing's `drafted` is a handoff. Verify the writing gate and requested files, append delivery path/time/checks to record, then set `delivered`. Keep blockers for unfinished mandatory deliverables.
- Automation stops at an authorized platform draft. Formal publication requires explicit human confirmation.
