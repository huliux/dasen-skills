---
name: dasen-wechat
description: Render a sourced content package into safe WeChat HTML or deliver it to the draft box with a real receipt. Run only when routed by dasen-content or explicitly requested. Own formatting, image handling, preflight, and draft delivery; do not change arguments, generate images, or mass-publish.
license: MIT
metadata:
  version: 6.0.0
  invocation: router-or-explicit
  compatibility: Requires Python 3.10+, PyYAML, markdown-it-py and Pygments. Draft delivery additionally needs network access plus a complete credential pair in named environment variables or a project/device-configured Keychain locator.
---

# Dasen WeChat

Deterministic scripts own Markdown-to-inline-HTML conversion, image handling, WeChat API calls, and delivery receipts.

## Inputs and runtime

Read the platform/identity contracts in `../dasen-content/references/contracts.md` and [platform rules](references/platform.md). For a bound project, read `channels.wechat`, `assets.root`, fixed layout, and publication requirements; do not invent configuration for standalone. Prefer a package directory; single-file Markdown is legacy compatibility. Read [delivery/recovery](references/workflow.md) for account actions and [implementation research](references/implementation-research.md) only when maintaining code.

Use Python 3.10+ with PyYAML, markdown-it-py, and Pygments. The Python commands below work without a shell wrapper. On macOS/POSIX, `setup.sh` checks PATH then existing pyenv interpreters; `DASEN_PYTHON` explicitly selects one. It does not install packages or change global Python.

## Local export and authorized drafts

```bash
python <skills-dir>/dasen-wechat/scripts/native_publish.py --dry-run \
  --output exports/article-wechat.html writing/YYYY-MM-DD/<slug>/
```

Without `--output`, dry-run checks preflight and rendering in memory and writes no file. Existing output is refused; use `--force` only for an explicitly requested replacement. To save an authorized remote draft, omit `--dry-run`:

```bash
python <skills-dir>/dasen-wechat/scripts/native_publish.py writing/YYYY-MM-DD/<slug>/
```

`publish.sh` remains a POSIX convenience wrapper for the same interface. Credential values stay on the device. Project settings contain environment-variable names or Keychain locators only. Without project configuration, a complete `WECHAT_APP_ID`/`WECHAT_APP_SECRET` pair or complete device Keychain locator may be used. Never combine partial sources or invent a default account/service. See platform rules for credential commands.

Theme/highlight precedence is CLI → brief channel → project channel → built-in default. Current IDs are `dasen-default` and `dasen-light`. Use `migrate_config.py` for old schema conversion and `migrate_namespace.py` for persisted branded values; neither silently changes delivered history.

For renderer-only inspection:

```bash
python <skills-dir>/dasen-wechat/scripts/native_renderer.py \
  --file writing/YYYY-MM-DD/<slug>/article.md --output exports/article-wechat.html \
  --theme dasen-default --highlight dasen-light
```

The delivery script:

1. Runs render preflight for dry-run or publish preflight for remote drafts; nonzero stops the action.
2. Applies optional project heading components in memory without changing `article.md`.
3. Parses frontmatter/Markdown, filters dangerous HTML, and inlines theme/highlight styles.
4. In dry-run, verifies fixed components, headings, and renderer markers; optionally writes the requested HTML, without reading credentials, uploading images, or changing brief/record.
5. For remote delivery, loads one complete authorized credential source and rechecks rendered images. Uploads local body assets from `assets.root` to WeChat, plus permanent cover media when configured.
6. Persists delivery state before calling the draft API. Only a real Media ID and successful local persistence permit PASS and `delivered`. Formal publication remains a human action.

## Legacy files and uncertain delivery

A single Markdown path invokes explicitly labeled compatibility mode without the full brief/sources/record gates. It does not load project asset roots; local images must be beneath the article directory. New work uses packages.

If a request might have reached WeChat without a reliable receipt, subsequent delivery fails closed. Inspect the real draft box, then use `native_publish.py` with one of:

- `--resolve-media-id <MEDIA_ID> <bundle>` to finish local receipts for an existing draft. If only local persistence failed, pass the same ID saved in delivery state; no platform request is resent.
- `--abandon-pending <bundle>` after confirming no draft exists, to close the old operation before a separate rerun.
- `--retry-confirmed <bundle>` only after a human confirms the old request created no draft.
- `--new-draft <bundle>` to explicitly create another draft after successful delivery.

## Completion

Local export requires an actual HTML file and passing applicable checks. Missing account, credentials, cover, generation, or CDN does not block local output. An in-memory dry-run is validation only, not file delivery.

Remote delivery requires compliant body images, permanent cover upload when present, a real Media ID, and record entries for `dasen native-v1`, canonical theme, and no formal publication. A missing dedicated cover does not block upstream work; if the actual account/API rejects it, report the blocker at that boundary. A human checks title, summary, author, cover, mobile layout, images/GIFs, and end links in WeChat.

Credential failure, invalid images, unknown themes, unsafe HTML, platform errors, or a missing Media ID blocks success receipts.
