# WeChat cover

Load for a requested article cover. Topic-label fields/checks apply only when topic_label exists or project/brief requires one. This does not change body-image acquisition.

## Configuration and fallback

```yaml
assets:
  root: assets
  remote:
    provider: none
visual:
  style_library: null
  defaults:
    body_style: body-clean-editorial
    cover_style: cover-clean-editorial
  rendering:
    body: auto
    cover: auto
  cover_size: null
  layout_library: null
  generation:
    required: false
    provider: none
    model: null
    endpoint: null
    api_key_env: null
    credential_profile: null
    options: {}
```

Assets root is workspace-relative; binaries go under its date/slug directory, while package assets contains audit text. Private visual Style IDs cannot overwrite built-ins. A project layout library records provenance, permitted use, and reference hashes. Provider/model are opaque capabilities, never a universal account/plan prerequisite.

Without a template/provider/authorization, deliver cover purpose, known aspect ratio, required title and optional topic label, composition/text hierarchy/exclusions, and a transferable prompt without calling services. Use cover_size or a real platform adapter for dimensions; leave unknown dimensions unresolved rather than guessing. Cover Style supplies safe areas. Missing capability blocks only generation.required; absence of a dedicated cover does not block writing/local layout. The real delivery adapter reports an actual platform cover requirement.

## Authorized generation

1. Read article meaning/title, optional topic_label, visual settings, and asset root.
2. Read the frozen cover Style. Resolve a selected layout and verify local/HTTPS reference assets and hashes; do not mix unknown-provenance assets.
3. Fill all variables and record Style ID/revision, layout, Adapter, reference, positive/negative prompts in package assets/cover-prompt.md.
4. Use the available authorized provider/model. Save versioned source pixels under assets.root/date/slug, with actual receipt, native dimensions, and hash.
5. Check Chinese/English spelling, title promise, identity permission, fake data, and real-screenshot claims; repair errors.
6. Produce cover.png using configured cover_size or actual adapter dimensions. Show the local final image before upload when human confirmation is required.
7. Only configured, authorized remote storage receives uploads; verify downloaded bytes/hash before updating article. Use cover_receipts.py finalize-cover from actual local files for cover.yaml and record evidence; local-only delivery still needs its applicable local receipt.

For a new project layout, confirm extracted mechanisms/reference assets first. register-template --confirmed updates an existing recipe in the declared project layout library with reference_path, reference_url, reference_sha256, and status. The compatibility command name does not turn it into Style or central source. Extract abstract layout/color/hierarchy from references, not original text, account identity, characters, mascots, or pixels. Prompt wording follows the task.

## Cover receipt

Prompt path is package-relative; source/final paths are workspace-relative.

```yaml
provider: ""
model: ""
style_id: cover-clean-editorial
style_revision: 1
adapter: html-css
layout: ad-hoc
topic_label: ""
title: ""
source_path: assets/YYYY-MM-DD/<slug>/cover-source-v1.png
source_width: 0
source_height: 0
source_sha256: ""
prompt_path: assets/cover-prompt.md
final_path: assets/YYYY-MM-DD/<slug>/cover.png
final_sha256: ""
width: 0
height: 0
cdn_url: null
generated_at: ""
```

Image binaries may stay out of Git; prompt/manifest/record must remain auditable. With a remote URL, publish preflight checks URL safety and actual byte hash. --skip-remote-check is explicitly offline inspection only.

## Legacy layout

Old visual.preset: bitbook-editorial maps to body-whiteboard-clarity plus cover-clean-editorial. The purple renderer remains an explicitly selected layout, not a Visual Style:

```bash
python3 scripts/render_topic_cover.py \
  --preset dasen-editorial \
  --input <source.png> \
  --output <cover.png> \
  --topic-label <label> \
  --title <title> \
  --title-lines '<line1>|<line2>' \
  --accent-line <text> \
  --summary <text> \
  --feature <label::proof> \
  --feature <label::proof> \
  --feature <label::proof>
```

Purple colors, font coordinates, topic capsule, and cards belong to this layout alone, not general WeChat/cover-clean-editorial requirements.

Required unavailable generation blocks cover-generator-unavailable. Required references without locator/hash block generation. Unfilled variables, wrong text/dimensions, or unmet authorization fail Asset Check. Required remote storage configuration/hash failure blocks remote upload only; retain local assets.
