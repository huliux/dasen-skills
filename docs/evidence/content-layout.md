# Content layout verification

Scope: spec §14, implemented from base 087ed54. New content defaults and evidence paths are forward-only; no historical package migration. Themes are original data for the native renderer, with design references documented in the theme directory.

## Deterministic and visual evidence

- Full local suite: 300 tests passed. Includes source-workspace isolation, explicit custom roots, legacy uncertain-state preservation, conflicting-state refusal, Wiki origin deduplication, structure-source exclusion, optional Wiki initialization, and three-theme structure/image equivalence.
- Runtime export check and six-Skill/three-pack validation passed; executable examples passed 35/35.
- Same synthetic Markdown rendered with all three themes. Browser observation at 375px per preview confirmed loaded images, heading hierarchy, lists, tables and code blocks. No external renderer was invoked. This is local HTML acceptance, not a WeChat phone or remote draft receipt.
- Initial verification failures were retained privately: localized error-message expectations, a fixture assertion that matched a template comment, and platform-component tests still using the draft stage. Corrections retained render-stage refusal checks and added text-only draft acceptance.

## Model sample

Two fresh offline Codex CLI contexts, model gpt-6-astra, medium effort, 240-second limit per case. Skill/case/rubric snapshots and full traces remain private. User config was ignored; a directory boundary is not complete filesystem isolation.

- Source-workspace initialization: completed in 61.34s. It created content/writing with evidence/, preserved the unrelated software project file and source file, and did not draft or render. Contract PASS; editorial quality NOT_ASSESSED; delivery PARTIAL because the appended preparation record used literal newline escapes. This remains an observed model-output limitation, not a clean success.
- Explicit Wiki query under a read-only consumer schema: completed in 35.06s. Read the index, relevant page and raw origin; returned the small-sample/correlation boundary and left every input unchanged. Contract and delivery PASS; long-form editorial quality NOT_ASSESSED. This does not establish the complete research-to-writing workflow.

No online research, credentials, upload, paid image/voice service or platform write was part of these cases. The small sample does not establish general stability, other-harness acceptance or editorial gains.

## Theme fidelity correction

The owner rejected the first simplified visual designs and supplied MWeb Bear, Lark and Typo styles. That selection supersedes the earlier original-theme statement above. The conversion retains source notices in the theme directory and keeps the native engine.

Baseline aec41ed reproduced two renderer defects: border-collapse/border-spacing were discarded by the CSS allowlist, and block code was forced to 12px. The correction preserves those properties, theme-selected code sizes/palettes, and nested styles. Source container padding, heading metrics and decoration replace the simplified theme values. Documented static substitutions remain; this is not pixel identity across platforms.

- Full suite: 302 tests passed; examples 35/35; six-Skill/three-pack and dependency-export checks passed.
- Browser inspection of the same synthetic article: three 375px previews and full-width pages passed local visual checks. All images decoded; tables computed to border-collapse:collapse; code computed to 14.4px (Bear), 14px (Lark), and 14px (Typo). Bear desktop border-box measured 838.4px with 25.6px/51.2px padding.
- One fresh offline model case, declared 180-second limit, gpt-6-astra/medium: completed in 128.33s. It produced the three requested native HTML files, preserved the source/image and Skill snapshot, and wrote a truthful static-check receipt. Contract and local structural delivery PASS; model-session visual acceptance PARTIAL because its sandbox prevented browser launch. The maintainer browser checks above are separate evidence, not attributed to that model session.
- No platform delivery or phone preview. Private source snapshots, model traces and local Asset Check retain the exact outputs and hashes.
