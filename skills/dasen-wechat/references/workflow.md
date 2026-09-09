# WeChat delivery and recovery

Package article/brief/sources/record → render preflight → native rendering → local HTML for human use. Only an explicitly requested remote draft proceeds through publish preflight, body-image/permanent-cover upload, draft API, real receipt, and human review/publication.

| Failure | Action |
|---|---|
| Missing package inputs | Block and return to content |
| Text/title/placement/identity failure | Return to writing |
| Missing/escaping/invalid image | Return to visual |
| Unknown theme/palette | Resolve canonical dasen-default/dasen-light; migrate old settings explicitly |
| Missing runtime dependency | Use the declared dependencies and rerun readiness checks |
| Credentials/upload fail before draft call | Block remote only; keep local HTML, sanitized error, and complete project/device locator; retry after repair |
| Uncertain draft request | No automatic retry; inspect real drafts, then resolve/abandon/explicitly retry |
| Real Media ID but local persistence failed | Reconcile locally with the same ID without another platform call |
| HTML passed but remote images/GIF missing | Inspect upload receipts; an authorized repaired delivery creates a new draft |
| Draft exists but layout is wrong | Append Platform Compatibility, repair and redeliver within authorization; mark old draft unusable |

For fixed project components, inspect project/source/assets hashes/old receipts to distinguish current rules from experiments. Change only authorized configuration/articles; changed project defaults do not rewrite historical articles. Keep asset URLs, file hashes, and HTML hashes aligned rather than inferring version from filename. Record asset availability, native render, full preflight, and phone review separately.

Section-heading templates must stay inside the project, use HTTPS images, and include {{title}}, {{marker}}, {{image_url}}, and {{image_alt}}. The publisher transforms selected heading levels in memory through the same renderer. Legacy single-file mode does not apply project transforms.

Human draft review checks title/summary/author/cover, actual theme against configuration, phone paragraphs/code/tables/long links/images, fixed component GIF/static image/dimensions/spacing/text, ending links without generated endnotes, and brief identity/placement. Append Human Review or Platform Compatibility. HTML, draft display, and publication are distinct states.
