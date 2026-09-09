# Installation environments and on-disk layouts

Research date: 2026-09-09. This report describes upstream source behavior, not an executed installation. Project installation scope, payload location, runtime dependencies, and mutable state are separate concerns. Default paths can change through host settings or environment variables.

## Superpowers and Matt Pocock: manager-owned files or editable Skills

Inspected Superpowers at `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` and Matt Pocock Skills at `3cca18b368ae95cdbdebbff572ccafa662551015`. Their installation routes do not provision a Python environment per consuming project. Superpowers declares no root npm dependency list; Matt's root dependencies are development-only release tooling. Selected workflows can still need the user's project tools, shell, or issue-tracker access. Instruction-oriented distribution does not establish that every workflow has no prerequisites. [Superpowers package](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/package.json), [Matt package](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/package.json).

### Claude plugin route

Both projects document a Claude plugin entry. Claude's official reference places copied marketplace plugins in `~/.claude/plugins/cache`, grouped by marketplace, plugin and installed version. Enabling a plugin at project scope writes project settings; it does not imply that the plugin payload is physically copied into that project. [Superpowers installation](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/README.md#installation), [Matt installation](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/README.md#installation-30-second-setup), [Claude scopes and caching](https://code.claude.com/docs/en/plugins-reference).

```text
~/.claude/plugins/cache/<marketplace>/
├── superpowers/<version>/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   └── hooks/
└── mattpocock-skills/<version>/
    ├── .claude-plugin/plugin.json
    └── skills/

<project>/.claude/settings.json   # Project enablement, when selected
```

This is a schematic of documented defaults, not an observed marketplace installation. The manager owns update/removal and actual cache naming. Its plugin cache contains active executable/instruction files; it is not merely a disposable download cache.

### Superpowers on OpenCode

The current route adds a Git-backed package to the global or project `opencode.json` plugin array. OpenCode owns its package installation. Its official documentation places npm plugin packages and dependencies in `~/.cache/opencode/node_modules/`; the precise Git-backed cache layout can vary with the host/Bun version. Superpowers' Windows fallback explicitly installs to `~/.config/opencode/node_modules/superpowers` and configures that path. Its former `~/.config/opencode/superpowers` clone-and-symlink recipe is a migration source, not the current default. [Superpowers guide](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/INSTALL.md), [OpenCode package installation](https://opencode.ai/docs/plugins/#how-plugins-are-installed).

### Matt through Vercel Skills

The examined installer at `80feb48868972d518436f26711509bc78595b5cb` defaults to project scope and symlink mode. It copies selected Skill subtrees to `.agents/skills/<name>` and links appropriate host discovery entries to them; copy mode writes directly to host directories, and failed links can fall back to copies. User-wide canonical files instead live under `~/.agents/skills`. [Directory and copy implementation](https://github.com/vercel-labs/skills/blob/80feb48868972d518436f26711509bc78595b5cb/src/installer.ts), [directory constants](https://github.com/vercel-labs/skills/blob/80feb48868972d518436f26711509bc78595b5cb/src/constants.ts).

```text
<project>/
├── .agents/skills/<selected-skill>/
│   ├── SKILL.md
│   └── <references, metadata, or scripts shipped with that Skill>
├── .claude/skills/<selected-skill> -> ../../.agents/skills/<selected-skill>
└── skills-lock.json
```

The tree illustrates a Claude project target in symlink mode; another host or copy mode has a different discovery layout. The local lock records sources and content hashes. It does not create a Python or Node runtime for each selected Skill. [Local lock](https://github.com/vercel-labs/skills/blob/80feb48868972d518436f26711509bc78595b5cb/src/local-lock.ts).

`npx` runs the installer using Node/npm. When the requested package is absent locally, npm places it in its own execution cache rather than adding a runtime dependency to every consumer project. Default npm cache roots are `~/.npm` on POSIX and `%LOCALAPPDATA%\\npm-cache` on Windows. Installing editable Markdown therefore does not itself require a new project `node_modules`. Matt's setup Skill configures project conventions; it is not a Python dependency installer. [npm execution](https://docs.npmjs.com/cli/v11/commands/npm-exec/), [npm cache](https://docs.npmjs.com/cli/v11/commands/npm-cache/), [Matt setup](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/setup-matt-pocock-skills/SKILL.md).

## Adoption in Dasen

This comparison informed the [storage decision](../adr/0001-project-selection-with-shared-runtime.md). Dasen stores complete immutable artifacts and verified runtime generations in user-owned data storage. Projects select versions independently and contain discovery entries rather than private copies of Python. uv manages Python installations and download caches. Only explicitly selected hosts receive entries.

The current contract and implementation are authoritative; the upstream layouts above are revision-specific source observations, not acceptance evidence for Dasen or permission to run an upstream installer. See [installation evidence](../evidence/installation-readiness.md) for measured limits.

## gstack

Inspected revision: `c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16`. Retrieval used read-only GitHub API requests; no setup script or gstack Skill was executed.

### Default Claude installation

The README clones one complete checkout into `~/.claude/skills/gstack` and runs its setup. This is a user-level tool installation shared by projects, not a Python-style virtual environment inside every consuming project. Git and Bun are prerequisites; setup checks for Bun on `PATH` and exits with installation instructions when absent. It does not install a dedicated Bun runtime for each project. Bun's actual executable/cache locations belong to its existing installation method and were not verified here. [README, lines 45–58](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#L45-L58), [setup, lines 52–66](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L52-L66).

```text
~/.claude/skills/
├── gstack/                      # Complete source checkout
│   ├── package.json
│   ├── bun.lock
│   ├── node_modules/            # Dependencies installed in this checkout
│   ├── browse/dist/browse       # Compiled browser CLI
│   ├── design/dist/design
│   └── make-pdf/dist/pdf
└── <skill-name>/                # Host discovery entries
    ├── SKILL.md                 # Linked source/render; Windows gets copies
    └── <runtime assets>         # Links/copies of each Skill's assets

~/.gstack/                       # User-level configuration and state
├── config.yaml
├── projects/
├── render/claude/               # Generated variants, when used
└── backups/skills/              # Backups created when applicable

<consumer-project>/.gstack/      # Per-project browser state and logs
├── browse.json
├── browse-console.log
├── browse-network.log
└── browse-audit.jsonl
```

`setup` changes into the source checkout before `bun install` and `bun run build`; binaries are built below that same source root. Discovery entries link/copy each Skill's instruction file and runtime assets. Generated user variants can live in `~/.gstack/render/claude`. [Build implementation, lines 886–916](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L886-L916), [discovery entries, lines 1362–1402](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L1362-L1402).

User-level state defaults to `~/.gstack`, with `GSTACK_HOME` supported by the runtime resolver; some setup steps explicitly use `$HOME/.gstack`. Browser state defaults to the detected Git root's `.gstack/`, falling back to the current directory, and can be overridden with `BROWSE_STATE_FILE`. This isolates browser state by project while the default installation's code and dependencies remain shared. [Browser state, lines 59–84](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/browse/src/config.ts#L59-L84), [user state, lines 196–218](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/browse/src/config.ts#L196-L218), [setup state directory, lines 1225–1226](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L1225-L1226), [backup location, lines 123–127](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L123-L127).

### Browser payload and Windows

Setup runs `bunx playwright install chromium`; it does not force browsers into the gstack checkout. Playwright 1.62.1's source defines these default browser payload locations:

| System | Default browser payload location |
| --- | --- |
| macOS | `~/Library/Caches/ms-playwright/` |
| Windows | `%LOCALAPPDATA%\ms-playwright\` (fallback: `~/AppData/Local/ms-playwright/`) |
| Linux / WSL | `${XDG_CACHE_HOME:-~/.cache}/ms-playwright/` |

These are executable browser installations under a cache directory, not merely disposable download archives. `PLAYWRIGHT_BROWSERS_PATH` overrides the location; value `0` uses the package-local `.local-browsers` directory. The defaults were verified against Playwright source, not against a live installation. [gstack installation call, lines 1148–1156](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L1148-L1156), [Playwright revision `26a9e47`, lines 498–529](https://github.com/microsoft/playwright/blob/26a9e470a7b3c7822084b09fb7f13902c5f37b51/packages/playwright-core/src/server/registry/index.ts#L498-L529).

On native Windows, gstack adds a Node.js prerequisite for the browser server, compiles `.exe` binaries, and builds `browse/dist/server-node.mjs`. That server keeps runtime dependencies such as Playwright external and resolves them from the installation's `node_modules`; setup verifies Node can load them and can attempt local `npm install --no-save` repairs. Native Windows registration uses explicit copies; rerunning setup refreshes them. WSL follows Unix behavior and paths. These branches are source evidence, not a native Windows acceptance test. [Windows setup and copies, lines 76–110](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L76-L110), [Node dependency verification, lines 1178–1201](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L1178-L1201), [Node bundle, lines 16–35](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/browse/scripts/build-node-server.sh#L16-L35), [README Windows guidance, lines 552–554](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#L552-L554).

### Project and alternate-host variants

The deprecated `--local` route sets the Claude discovery directory to the current directory's `.claude/skills`, but this alone does not relocate the source checkout or create a private runtime. The current `gstack-team-init` explicitly uses the global installation, removes a detected old vendored project copy, and adds team instructions/hooks. Its behavior should take precedence over the setup help's older “per-repo gstack” wording when describing current isolation. [Deprecated local mode, lines 575–587](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L575-L587), [team migration and instructions, lines 42–79](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/bin/gstack-team-init#L42-L79).

Alternate hosts have their own discovery locations. A directly cloned Codex installation at `~/.codex/skills/gstack` is migrated by setup to `~/.gstack/repos/gstack` to prevent duplicate discovery; generated Skills and runtime references are then registered for the host. This is another example of discovery location differing from payload ownership. [Host paths, lines 63–74](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L63-L74), [Codex migration, lines 637–668](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L637-L668).
