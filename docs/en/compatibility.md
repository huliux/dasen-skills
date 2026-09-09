# Compatibility

[简体中文](../zh-CN/compatibility.md)

Currently preparing an Alpha for community testing; complete production support is not yet claimed.

| Environment | Current status |
|---|---|
| macOS + Codex CLI | Project discovery, local scripts, and HTML export observed; complete creation needs testing |
| macOS + Claude Code | Project binding and local execution observed; complete creation timed out and needs testing |
| macOS + Codex desktop | Installation bindings implemented; in-app use unverified |
| Windows | No automated preparation or project binding route; manual route for developer testing |
| Other Agents | Awaiting community verification |

When a same-name global Skill exists, check the actual loaded path; Claude Code may prefer the personal entry. Factual accuracy and delivery completeness still need human review.

Ordinary writing and local HTML need no additional account. Online retrieval, image generation, cloud storage, and remote WeChat drafts are configured and tested separately.

Report issues or contribute a PR in the project repository, including your system, host version, reproduction steps, and redacted results. Contributors can find detailed observations in the source checkout's `docs/evidence/`.
