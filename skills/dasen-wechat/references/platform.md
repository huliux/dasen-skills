# WeChat platform contract

## Article frontmatter

```yaml
title: "Required; local gate allows at most 32 characters"
author: "Optional; must match a configured channel.default_author"
digest: "Optional; at most 120 characters"
cover: "Optional; HTTPS URL or local path bounded by assets.root"
tags: []
```

Project channels.wechat may provide display name, default author, and required tags, compiled into brief.channel; otherwise they remain optional. A byline does not authorize first person/contact details. Formatting does not rewrite author or inject identity/promotion.

A dedicated cover is not required upstream. Never invent thumb_media_id or silently select the first body image. If the actual account/API requires permanent cover media, block at remote delivery.

## Image policies

**local (default):** local HTML may retain workspace image references for human inspection/handling, without CDN/storage/credentials. Authorized remote drafts still revalidate and upload local images to WeChat.

**platform-upload (explicit):** article/cover paths resolve relative to article.md and must remain beneath frozen assets.root; package evidence contains text only. Preflight and publisher reject absolute paths and lexical/symlink escape. The publisher rechecks every raw-HTML img src, preventing Markdown bypass. Body JPG/PNG uses the inline image endpoint when eligible; GIF/oversized images use permanent image material. An existing cover uploads permanently and contributes its returned media_id.

**stable-cdn (explicit):** originals remain under assets.root while prose uses verified stable HTTPS URLs. The publisher downloads validated URLs and uploads through WeChat; CDN is optional. Downloads reject credential-bearing URLs, non-HTTPS, unusual ports, redirects, nonpublic DNS results, and oversized responses. When a proxy returns only fake IPs, require explicitly configured DASEN_DOH_RESOLVER_URL: an HTTPS JSON DNS API accepting name/type and returning Answer. A binary RFC8484 endpoint does not fit. Missing configuration or unconfirmed public addresses fails closed; there is no built-in public resolver. Preflight and upload share this check and report protocol failures.

Runtime accepts only local/platform-upload/stable-cdn; wenyan-upload is migration input. Choose one policy per article. Fixed project UI assets may be independently verified HTTPS resources.

## Theme, HTML, code, and links

Use the three [MWeb theme adaptations](../themes/README.md), including their selection names, compatible IDs, metrics and conversion boundaries. Theme data maps safe tags/context to inline styles; no external renderer or CSS execution is introduced. Explicit project component dimensions can override defaults. The safe tag stack prevents stray closing tags escaping the root; event handlers, scripts, forms, iframes, CSS URLs and dangerous protocols remain filtered.

Pygments tokenizes fenced code using the selected theme's palette and block-code metrics; unknown languages become plain text. Markdown links remain ordinary anchors, without automatic endnotes. Facts remain in sources/record.

### Body-image captions

When formatting supplied body images with explanatory captions, group each image and its actual caption in a figure, placing figcaption directly below the image:

```html
<figure>
<img src="../../../assets/YYYY-MM-DD/slug/result.png" alt="结果截图" />
<figcaption>配图说明：本次结果仅代表所列测试条件。</figcaption>
</figure>
```

Use the existing explanation verbatim. Convert a clearly identified image explanation into this markup in the formatting copy; retain source Markdown and image URLs. Alt text remains accessibility text, not an automatic visible caption. A following ordinary paragraph is not a caption unless its role is explicit. Do not invent explanations for images without supplied captions. Fixed project UI icons and cover media are outside body-figure formatting.

The three themes apply the shared [caption styles](../themes/README.md#body-image-captions). Check the rendered image and caption share the horizontal center, the caption is below the image, and its computed font size is 2px below the body with #999999 text. Preserve caption text and local/CDN image references in the Asset Check.

## API and credentials

Authorized remote delivery uses token GET /cgi-bin/token, body-image POST /cgi-bin/media/uploadimg, permanent-image POST /cgi-bin/material/add_material?type=image, and draft POST /cgi-bin/draft/add. Recheck official API documentation when changing implementation.

Tokens/image receipts use permission-restricted user cache, never source/package/log. Load AppID/AppSecret from one complete source; partial pairs cannot be combined. Central source stores no default Keychain service/account/old prefix.

```yaml
channels:
  wechat:
    credentials:
      app_id_env: WECHAT_APP_ID
      app_secret_env: WECHAT_APP_SECRET
      keychain_service: null
      app_id_account: null
      app_secret_account: null
```

Environment fields are variable names, defaulting to the neutral names above. Keychain locators are all three fields or none. Device fallback uses DASEN_WECHAT_KEYCHAIN_SERVICE, DASEN_WECHAT_APP_ID_ACCOUNT, and DASEN_WECHAT_APP_SECRET_ACCOUNT. wechat_credentials.py status reports availability/source only. Its store command (or POSIX store_credentials.sh wrapper) stores an environment-provided complete pair or hidden interactive input at the declared locator. Explicit migrate-prefix requires --legacy-prefix, verifies new entries, prints no values, and retains old entries. Inspect --help for exact arguments.

Recognize already uploaded images by parsed exact hostname, not string prefix. Sanitize external errors before recording: remove query strings, hide absolute paths, flatten, truncate. Current local field gates are title 32, author 16, digest 120, visible body below 20000 characters, and HTML below 1 MiB. Platform errcode or missing media_id fails closed.

## Fixed project layout and recovery

Optional hard_rules.follow_guide appears once before the first paragraph with a real img. body_h1_forbidden excludes body H1. section_heading transforms only an in-memory copy using a project-contained template with required placeholders; Markdown stays clean. Dry-run asserts marker/shared-image-URL/visible-text counts. New themes/components still need human phone review for images/GIFs, spacing, long titles, and tables.

Authorized automation stops at drafts; success does not prove preview/publication. Persist evidence/delivery.json before the draft call. Submitting/uncertain state prevents automatic retry until a human inspects the draft box and resolves the real ID, abandons, or explicitly retries. Append a new receipt for each authorized new delivery without overwriting history.
