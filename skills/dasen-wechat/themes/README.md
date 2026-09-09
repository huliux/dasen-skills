# Native MWeb theme adaptations

The owner selected these three themes to replace the earlier simplified designs. All use the native renderer and white backgrounds. Source rules and license notices live in [NOTICE.md](NOTICE.md).

| Display name | Preferred selection | Existing ID retained | Key metrics |
|---|---|---|---|
| MWeb Bear | `mweb-bear` | `dasen-default` | 16px / 1.6; 500-weight headings; neutral text; blue links; white bordered code |
| MWeb Lark (blue emphasis) | `mweb-lark` | `dasen-document` | 16px / 1.68; 26/22/20px headings; blue emphasis; 14px light-gray code |
| MWeb Typo | `mweb-typo` | `dasen-reading` | 18.2px / 1.8; 100-weight headings; green links; 14px code |

Existing IDs remain accepted so frozen article selections resolve. They now select the corrected styles; already exported HTML remains unchanged. New selections may use the preferred MWeb names. The public render command still accepts `--highlight dasen-light`; token colors come from the selected theme's native palette.

## Conversion boundary

Resolve SCSS variables through their actual core selectors, rather than copying a palette alone. Inline the resulting typography, spacing, container, quote, table and code rules. Bear/Lark retain 25.6px vertical and 51.2px horizontal padding; their 736px source content limit becomes an 838.4px border-box limit. Typo resolves its 14px root and 1.3rem body to 18.2px, with 14px outer padding.

Safe static equivalents replace dynamic page styling: lists use semantic browser markers instead of pseudo-element counters; Typo uses its mobile quote margin at all widths; Lark's flat gradient divider becomes a solid line. Hover, interactive inputs, external fonts, page resets and script-driven charts are not imported. Fonts use the supplied stacks and available system fallbacks; no font download occurs. This is a documented native/platform conversion, not pixel identity across MWeb, browsers and WeChat.

The renderer preserves border collapse/spacing and list properties, applies nested quote/list rules, and separates block-code styling from inline code. Theme code sizes and token colors are honored; toolbar decoration is opt-in. Keep scripts, unsafe URLs and CSS URL/expression rules filtered.

Acceptance compares the same Markdown at mobile and desktop widths, verifies decoded images and actual table/code/heading styles, and retains a real local Asset Check. HTML validity alone is insufficient visual evidence. Phone rendering and remote draft receipts remain separate.
