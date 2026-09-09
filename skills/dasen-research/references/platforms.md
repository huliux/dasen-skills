# Retrieval backends and fallback

Use only a task-suitable backend actually verified in this run. Prefer applicable installed Agent Reach/AIHot; otherwise use native search/browser, official public material, or supplied sources. Record unavailable platforms and never present search snippets as platform metrics.

Inspect installed capabilities before their read-only doctor/help. Do not automatically install tools or access unauthorized login state. Agent Reach active_backend: null means its doctor did not run an authenticated live probe, not necessarily that no backend exists. When the task needs that platform, follow its supported read-only verification and require nonempty content.

Backend preference does not change evidence priority: news aggregators/platform signals discover leads; factual claims return to originals or reproducible trials.

| Purpose | Preferred available capability | Fallback |
|---|---|---|
| Current AI news | AIHot | Agent Reach/native search, then original company material |
| WeChat reach metrics | Installed authorized platform capability | Verify public originals without fabricated readership |
| Bilibili | Agent Reach / bili-cli | Native search or public platform API |
| YouTube | Agent Reach / yt-dlp | Native search or official channel |
| Xiaoyuzhou | Agent Reach | Supplied audio/transcripts |
| X / Reddit / Xiaohongshu | Verified authorized Agent Reach backend | Public native pages as leads, not full interaction data |
| GitHub | gh CLI / API | Repository/release pages |
| Web / RSS | Agent Reach Jina/Reader | Native browser/search, original site, supplied URL |
| Authorized meeting context | Bitbook CLI under bitbook-context.md | Supplied authorized transcripts/notes |

Read supplied URLs/files/material completely before targeted gap-filling. Native retrieval needs no mandatory external Skill. Local evidence can support offline research when timeliness is not required; disclose its scope. If essential online evidence is unavailable, request sources or record research-capability-unavailable rather than inventing retrieval from memory.

Normalize title/content, account_name, original published_at, checked_at, retrievable URL, actual platform metrics (missing stays empty), source_type, and confidence. Preserve platform-specific metric definitions; normalize within a platform before any requested editorial ranking in scoring.md.
