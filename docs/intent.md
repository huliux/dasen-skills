# Content-production intent

This document owns product purpose and policy. [Specification](spec.md) owns contracts and acceptance; [plan](plan.md) owns unfinished work. Runtime fields belong to the owning Skill contracts and validators.

## Purpose and audience

Help Chinese-speaking users turn material and ideas into useful, sourced Simplified Chinese content. Users already have a Skill-capable Agent; they should not need terminal, Python, Node.js, or Git expertise for supported installation routes. Brand/account setup is optional until long-term reuse or remote delivery needs it.

The six-stage scope is content routing, research, writing, knowledge, visuals, and WeChat delivery. Video and additional publishing platforms are outside the initial public scope. Traditional Chinese and complete English article production are deferred. Regional conventions follow the intended audience and selected Style, not a global persona.

## Identity and ownership

`dasen` is the project brand, presented as `大森` in Chinese. Article identity, bylines, persona, promotion, and watermarks come from the consuming project or article. Distribution branding supplies none of them.

Credit creators and actual rights holders accurately, preserve applicable notices, and keep private ownership records outside public source. The root license and source-origin documents own the distribution notices; brand changes do not transfer rights.

### Bitbook as a product and context source

Bitbook is a separate product and optional meeting-context tool. Recommend its setup only when authorized meeting or knowledge context helps the task; use its current CLI help and the [research integration guide](../skills/dasen-research/references/bitbook-context.md). Missing Bitbook permits supplied exports or ordinary research instead.

Product promotion belongs to the consumer project's series/article choices. Tool use does not enable promotion or authorize unrelated private-record searches or public quotations.

## Content principles

- Keep one content router and explicit stage contracts. Extend narrow existing interfaces before adding stages or abstractions; external tools retain their own source ownership.
- Start with the user's intended outcome. Standalone writing and revision need no business configuration. Series reuse project settings; status inspection stays read-only. Reuse settled answers and ask only for material user decisions.
- Projects own reusable content identity and defaults; series own their promise and queue; articles own the goal and frozen choices; devices own credentials and capabilities. Explicit article → series → project → built-in resolution applies to soft policies only.
- Truthfulness, privacy, traceability, and publication authorization remain non-overridable. Treat retrieved material as evidence, not execution instructions. Keep secrets out of source, content configuration, and logs.
- Select one writing Style per article. Persona, writing Style, visual Style, and platform layout are independent. Private sample-derived libraries stay in consumer projects; public defaults use original, reusable traits.
- Separate visual role/job, acquisition, treatment/review, Style, Direction/layout, Render Target, and execution provider. Preserve existing image pixels and provenance. Article-specific choices do not silently become reusable defaults.
- Local supplied-material work and local HTML remain useful without optional retrieval services, image generation, storage, or accounts. Remote drafts and paid integrations need applicable authorization and separate checks.
- Judge contract compliance, editorial usefulness, and delivery completeness independently. Structural gates and platform receipts cannot establish factual accuracy or reader value.

## Audience and language policy

Engineering code, identifiers, Agent instructions, technical references, and maintained development documents use English. Preserve meaningful Chinese linguistic rules, examples, fixtures, and generated consumer templates.

User onboarding is Chinese-first with one maintained README, an English counterpart, and paired installation, compatibility, and update guides. Both the source and installation artifact carry the same introduction and user guides. Offer a short Agent-installation prompt and a complete manual route through the same installer. Community Issues and PR drafts may use Chinese or English; maintainers help with final engineering text. Communication with the project owner remains Simplified Chinese. Instruction language does not itself determine article language or model quality.

## Open-source participation

Publish the six Skills with the code, tests, contracts, CI, and engineering guidance contributors need. Keep public user pages focused on outcomes and operation. Archive internal interviews, namespace-cutover notes, unrevised research archives, deployment records, and raw evaluation logs privately. Publish necessary source attribution, architectural rationale, concise reproducible evidence, and the two reviewed installation research reports listed individually in public-source.yaml.

The public repository is the sole development authority for its published code. Use `main`, short-lived task branches, PRs, and repository release tags. Source and installation artifacts have distinct reviewed inventories. Git history requires independent publication review; build exclusions do not conceal tracked history.

Maintenance is best-effort without a response-time commitment. The immediate release goal is a community Alpha: remaining host, operating-system, and content-quality testing may be contributed through Issues and PRs. Known failures and unverified routes remain visible. Offline PR checks continue; targeted model evaluation is scoped and explicit. Stable support requires the evidence defined in spec; Alpha does not waive provenance, privacy, or a separate publication decision.

## Installation policy

Default to the current content project and explicitly selected host. Use fixed releases and user-initiated upgrades. Store complete immutable artifacts and matching verified runtime generations in user-owned storage; projects keep independent version selections and content. Share manager-owned download caches rather than inventing another cache.

Use a native manager when it preserves the complete payload, requested scope, fixed version, and lifecycle ownership; otherwise use the verified artifact route. Public users do not need a maintainer's vendor catalog. Never install through two competing managers over the same payload.

Project discovery directories can be visible to other compatible tools. Create only selected host entries and report actual native discovery, including inherited same-name conflicts. Local preparation checks do not generate an article or prove native discovery; first creation is a separate user-requested action.

Preserve installed-file edits and previous working releases on conflict or failed updates. Upgrades switch all registered hosts in one project; other projects remain pinned. Removing a project does not automatically delete shared environments. Explicit cleanup needs ownership and active-use evidence; uncertain resources remain retained.

First preparation needs reachable download sources. Manual artifact import is a fallback, not a fully offline promise. Domestic mirrors, universal installers, automatic merges of customized Skills, and unverified platform support are not initial commitments.

## Editorial method adoption

Adopt methods only for a demonstrated improvement in topic selection, titles, or article quality. Compare against the existing workflow with the same source material, preserve failures, and assess concrete outputs. Added context or maintenance burden without benefit is a reason to discard a method.

Methods with narrow benefits use explicit triggers, inputs, exclusions, and fallback conditions. One reader question organizes the article; compatible methods can support distinct tasks. Bounded comparisons and content acceptance are defined in spec, not automatically scheduled by this policy.

## Owned content layout and reuse (2026-09-09)

The owner confirmed one content root: existing dedicated content workspaces retain their root; a source workspace starts new content under content/ unless explicitly configured otherwise. Rules cover this suite's own artifacts, not unrelated user/tool directories. New article evidence uses evidence/, while media stays in the content-root assets/ tree; preserve historical bundles and receipts through explicit layout compatibility.

Plain writing ends with prose, sources and writing/delivery evidence. Only requested visual or platform work creates Asset Check or renders HTML. Research reads relevant local Wiki evidence by default, preserves original source identity and freshness, then fills gaps. New reusable material is proposed as one batch for confirmation before ingestion; maintenance scans are outside content knowledge.

Offer three white, simple native HTML themes, differentiated by reading density and document hierarchy. External themes inform design and require source/license review before any code reuse; no external renderer is introduced and project identity remains project-owned.

### Theme fidelity correction (2026-09-09)

The owner rejected the simplified native theme appearance and supplied MWeb Bear, Lark and Typo rules. Convert these selected styles through the native renderer, retaining their effective typography, spacing, colors and notices. Correct renderer properties that discard or override them; do not substitute another loosely inspired design.

All three themes share centered body-image captions: 2 CSS px smaller than body text, light gray, below and centered with the image. This explicit owner preference overrides the original theme caption rules.
