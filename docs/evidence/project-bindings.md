# Host and runtime evidence

Reviewed 2026-09-09 on macOS 26.6.1. These are bounded observations, not complete support claims. Raw inputs, outputs, timings, and unsuccessful traces are preserved privately.

| Case | Source and environment | Result |
|---|---|---|
| Codex project discovery | `05206cb173de322420f0e9f96bc9424ffd5d9c08`; Codex CLI 0.153.4 | Six enabled project entries found; user entries also visible. Managed Python 3.13.15 passed local checks. |
| Claude default discovery | `cc348d91fd1969ae0afd12c559e287d2c1d7ef99`; Claude Code 2.1.263, DeepSeek v4 Pro | Failed project selection: personal same-name entry loaded. |
| Claude scoped discovery | Same source and host; project/local scope | Six project entries found; read-only inspection passed. |
| Claude production | Same source and host; synthetic meeting material | Partial: Markdown and local HTML produced, but the 360-second run and 240-second continuation timed out before verified delivery. |
| Nested runtime regression | `a9096fa2fa3f11ce0a98e0e9a7746183a83a0e53`; Codex CLI model case | Completed in 73.78 seconds, exported HTML, preserved article bytes, and passed post-render installation status. |

Claude editorial review found an unsupported change from “no purchasing decision” to “no purchasing discussion,” confused observation labels, and manually supplied check times ahead of tool events. Structural gates did not detect these defects. The four Claude runs remain one failed selection, one passing inspection, one partial production, and one timed-out continuation. No complete production pass is inferred; this was not an Anthropic-model test.

Nested Python subprocesses originally created bytecode files inside an immutable artifact. Content 4.3.3 propagates bytecode and user-site isolation across descendants. A failing regression, corrected full-bundle export, and post-render integrity check cover that repair. All Skill payload files at `f9088aba4349a6fca27e299a1272818bfcbc3642` match the corrected model-tested candidate. The repair does not regrade the earlier editorial failures.

Inherited maintainer context limits clean-user inference. Codex desktop and native Windows remain unverified. CLI observations cannot establish desktop acceptance; linked directories alone cannot establish any host's discovery.
