---
status: accepted
---

# Project selection with shared runtime storage

Keep project enablement and version choices separate from user-owned physical storage; matching installations may reuse a verified runtime while different versions coexist. This reduces repeat downloads and setup without forcing every content project to carry a private tool environment, at the cost of explicit runtime ownership and reference-aware recovery. Native managers keep their own payloads; the accepted identity, immutability and channel requirements are defined once in [spec](../spec.md#shared-runtime-and-channel-acceptance-confirmed-2026-09-09).
