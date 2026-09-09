# Owned content paths

Run initialization from the host workspace (the registered project root when using the installation runner). `--content-root` is workspace-relative. Explicit selection wins; existing content project configuration, bundles or Wiki preserve their root. A source workspace without existing content defaults to `content/`; an empty standalone directory uses `.`. Detection is bounded to known content documents and top-level source markers, not a whole-machine search. Ambiguous targets are user decisions.

CLI `--project-file` and `--series-file` remain workspace-relative. Initialization converts them to content-root-relative references in the brief. A new project's `content_root` records its workspace-relative binding for explicit later selection. Other paths in project/brief data, including Style libraries, media and Wiki, are content-root-relative. A custom root can always be selected explicitly. Source-workspace configuration and unrelated project.md files are not treated as content configuration unless explicitly selected.

New bundles freeze `layout_version: 2`, workspace-ancestor-relative `workspace_root`, and workspace-relative `content_root`. These locate owned data when invoked from another directory. Paths must stay within their selected root after symlink resolution. Use the installed runner from the registered workspace; changing cwd does not override its root.

```text
<content-root>/
  projects/<project>/project.md        # optional reusable settings
  projects/<project>/themes/<series>/series.md
  writing/YYYY-MM-DD/<slug>/
    brief.yaml
    sources.md
    article.md
    record.md
    evidence/                         # plans, prompts, manifests, sanitized receipts
    exports/                          # requested derived HTML, etc.
  assets/YYYY-MM-DD/<slug>/            # this article's media
  assets/<project>/                   # shared project media
  wiki/                               # created only for an explicit knowledge task
```

Only create directories needed by the request. Evidence is auditable text; media resides beneath frozen assets.root. Credential values, raw private API responses and machine traces do not belong in tracked evidence. Preserve nested allowed text receipts in the consumer's Git policy; ignore only positively identified private/runtime/media files within owned paths. Example projects may retain their required self-contained fixtures with explicit provenance; do not relocate their files as article images.

Scope covers this suite's artifacts only. Do not organize or change unrelated user/tool directories. Existing inputs can be read by authorized reference without taking ownership of their containing directory.

## Existing bundles

Absence of layout_version means layout 1: the bundle's assets/ remains its evidence directory and workspace_root retains its existing meaning. New bundles use evidence/. Every producer/consumer resolves this centrally with content_paths.evidence_dir; never select a delivery-state file by directory existence. A state in the alternate location or a state symlink fails closed, including pending/uncertain recovery. Preserve old records and their referenced paths. No implicit migration, copying a second delivery state, or rewriting historical receipts.

Existing project roots and old standalone articles remain in place. New layout defaults apply forward; source upgrades do not migrate content. Any separately requested migration first previews exact paths, preserves originals and media hashes, checks references/conflicts, and maintains one active delivery state. Exported HTML is derived, not the manuscript authority.
