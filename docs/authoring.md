# Authoring agent instructions

Keep one content router, explicit stage contracts, verifiable scripts, and project-independent distribution.

## Placement

Put steps common to a Skill's paths in its entry; conditional rules in a directly linked reference; deterministic work in scripts with meaningful offline verification. Consumer names, persona, business parameters, sample-derived Styles, and delivery records stay in consumer projects. External Skill source and patches stay with their upstream/installation manager.

`dasen-content` is the only automatic content router. Other stages run through it or explicit user requests. A reference-sized capability does not justify a new Skill.

## Entry contract

Frontmatter includes accurate name, discriminating description, MIT license, and `metadata.version` matching registry. Put runtime requirements in compatibility and `metadata.invocation: router-or-explicit` on stages, also stating that condition in their descriptions. Preserve applicable harness metadata instead of assuming one tool's private frontmatter works everywhere.

Lead with the shortest execution path and make inputs, outputs, failures, and completion checkable. Distinguish retrieval from writing and drafts from publication. Link references with the condition for reading them; avoid deep reference chains and duplicate rule owners.

## Implementation boundaries

Use the smallest implementation that meets the current contract. New abstractions, settings, and dependencies need an actual use case and an explanation of what existing code cannot do. Split by responsibility, reason for change, or validation boundary; line counts are review signals, not mandatory fragmentation targets.

A rule must identify its condition, action, and checkable outcome. Explain the permitted route for hard guardrails. Use the current file tree and CLI help as truth; document only high-frequency commands and constraints that inspection cannot reveal. Historical receipts prove their own versions, not present behavior.

## Original and reusable source

Design from this project's content contracts. Studying interfaces/data flow is different from copying implementation; licensed reuse preserves required attribution close to source. A tool name does not transfer ownership. Do not promote one project's preference into a universal default.

Built-in writing/visual Styles are original, general-purpose, reviewed distribution data. Content tasks add or revise private Styles through project interfaces. Body/cover roles remain separate. Per-asset variation belongs in Direction; layouts, reference assets, provider/model, and identity belong to the project or adapter layer. Defaults contain no private names, paths, contacts, credentials, or single-project brand assets.

Maintain English engineering instructions/code and meaningful Chinese linguistic examples. Full traces and repeated snapshots stay in ignored/private storage. Commit only necessary synthetic cases, concise evidence, hashes, and limitations.

## Review

Check discriminating invocation, one router, complete inputs/outputs/state/blockers, correct project-versus-core ownership, optional-integration fallbacks, meaningful positive/refusal/dry-run coverage, and synchronized metadata/dependencies/provenance. New Skills also need an independent trigger, a reason an existing stage cannot own the work, and actual or equivalently strong acceptance evidence.
