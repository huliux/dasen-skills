# Installation benchmarks

Reviewed **2026-09-09** to reduce the effort required for a new Dasen user to install the six-Skill core and produce a first local artifact. This is research, not a new
installation contract or a claim of supported harnesses.

## Findings

Adopt a guided, outcome-based installation flow: identify the user's harness and scope, install one complete versioned bundle, prepare its private runtime, verify native discovery,
then offer a separate user-requested first Chinese article with HTML. Keep optional research services and publishing accounts outside that first run.

The upstream projects solve different problems. Gstack automates a substantial runtime setup; Superpowers delegates distribution to native plugin managers; Matt Pocock offers a
managed plugin installation or editable files, followed by per-project configuration. A short installation command alone does not prove that dependencies, activation, updates, or the
first useful task work.

## Sources and evidence limits

Official repositories were read through the GitHub API at these fixed revisions:

| Project | Reviewed revision | Commit date (UTC) |
|---|---|---|
| [Gstack](https://github.com/garrytan/gstack/tree/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16) | `c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16` | 2026-09-09 |
| [Superpowers](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797) | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | 2026-08-12 |
| [Matt Pocock Skills](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015) | `3cca18b368ae95cdbdebbff572ccafa662551015` | 2026-09-04 |

These are source inspections. No upstream installer, Skill, paid model session, account operation, or remote publication was executed. Upstream marketplace availability and timing
below are attributed to their documentation; an installed marketplace version was not independently checked. Windows source and CI inspection do not establish an observed
successful Windows installation.

## Entry points and first use

Commands below describe upstream entry points; they are not Dasen commands or instructions to install those projects as Dasen dependencies.

| Project | First installation action | Scope and payload | First useful action |
|---|---|---|---|
| Gstack | Paste a request containing `git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack`, then run `./setup` inside it | Default documented Claude path is user-level. Setup can detect several installed hosts or accept an explicit `--host`. Runtime assets accompany generated Skill entries. | `/office-hours` with an idea, then selected planning/review/QA commands. |
| Superpowers | Claude: `/plugin install superpowers@claude-plugins-official`. Codex App: Plugins → Superpowers → install. Codex CLI: `/plugins` and search. | Install separately for each harness through its manager. The Codex manifest selects `./skills/`; Pi declares both Skills and an extension. | Start a normal development request; methodology Skills are intended to activate as relevant. OpenCode offers a specific discovery check. |
| Matt Pocock Skills | Claude: `claude plugins install mattpocock-skills`. Other agents/editable route: `npx skills@latest add mattpocock/skills`. | Managed read-only Claude bundle or installer-selected Skills and target agents. The README explicitly says to choose one route to avoid duplicates. | Run `/setup-matt-pocock-skills` once per repository; `/ask-matt` routes users who do not know which workflow to choose. |

Sources: [Gstack quick start and installation](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#quick-start), [Superpowers
installation](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/README.md#installation), [Superpowers Codex
manifest](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.codex-plugin/plugin.json), [Matt installation and
reference](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/README.md#installation-30-second-setup).

## What implementation adds to the README

### Gstack: automate the work, report partial readiness

Gstack's advertised 30-second entry requires Git and Bun; Windows additionally needs Node for its browser runtime. `setup` refuses missing Bun and prints recovery instructions. It
installs package dependencies and builds runtime binaries. It first attempts a frozen lockfile but falls back to an ordinary install. Browser download has a deadline and classified
failures; browser failure can leave other Skills registered and usable. This is substantially more work than copying Markdown. The headline is not a cold-machine timing measurement
from this research. Sources: [requirements](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#install--30-seconds), [Bun
precheck](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L52-L62), [dependency/build
path](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L886-L913), [browser failure
handling](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L3066-L3094).

On Unix it links entries; on Windows without the required link behavior it copies files and explicitly requires setup again after a Git update. Ownership checks and backup paths
protect unrelated or customized entries. These are useful installation properties to borrow. Its Windows workflow also exercises build and binary resolution, but skips Playwright
for that build: that workflow is not evidence of complete browser QA success. Sources: [link/copy and ownership
implementation](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L86-L226), [Windows
reminder](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L403-L405), [Windows
workflow](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/.github/workflows/windows-setup-e2e.yml).

Do not copy its default breadth: automatic multi-host detection, global installation, browser routing overrides, optional system package installation, and team auto-updates add
side effects and maintenance costs beyond Dasen's first article. The user's chosen harness and scope should remain explicit. This is a Dasen recommendation, based on the [setup
dispatch](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/setup#L597-L628) and [documented team
mode](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#step-2-team-mode--auto-update-for-shared-repos-recommended).

### Superpowers: native packaging plus explicit activation adapters

Its core distribution is mostly instructions; root `package.json` declares no runtime dependency list. Harness adapters supply integration. OpenCode's plugin adds the bundled
`skills` directory to live discovery configuration and injects bootstrap context. Pi declares native resources and reinjects its bootstrap after compaction, with fallbacks when
optional subagent/task tools are absent. This reduces manual link management without pretending every harness exposes the same tools. Sources: [package
metadata](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/package.json), [OpenCode
adapter](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/plugins/superpowers.js), [Pi
adapter](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.pi/extensions/superpowers.ts).

Activation is not uniform. Claude's session hook invokes Bash; its Windows wrapper silently succeeds without bootstrap when Bash cannot be found. The Codex manifest explicitly has
an empty `hooks` object. Therefore neither "plugin installed" nor the README's automatic-trigger language proves identical activation on every host. Dasen should report discovery,
execution and first artifact separately, rather than copy silent degradation or universal bootstrap claims. Sources: [hook
registration](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/hooks/hooks.json), [Windows
wrapper](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/hooks/run-hook.cmd), [Codex
manifest](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.codex-plugin/plugin.json).

OpenCode's installation guide is particularly useful: it provides a native discovery check, old-link migration instructions, cache-related update caveats, a version-pinned package
example, and a Windows npm fallback. These are concrete recovery paths, not merely a "try reinstalling" message. Source: [OpenCode installation and
troubleshooting](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/INSTALL.md).

### Matt Pocock: separate installation from project configuration

The setup Skill first explores existing configuration, then requests only unresolved choices. It skips triage labels when triage is absent and defaults ordinary repositories to a
single document context. It updates one existing agent-instruction block without overwriting surrounding user content. It is explicitly a prompt-driven configuration workflow, not
a deterministic runtime installer or dependency doctor. Source: [setup
Skill](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/setup-matt-pocock-skills/SKILL.md).

Its hard/soft dependency distinction is especially relevant: require setup only where missing configuration would make output wrong; otherwise proceed with reduced context. Dasen
should not demand a brand, content series, publishing account, Bitbook, AIHot, or Agent Reach before a standalone sourced article. Source: [setup-dependency
decision](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md).

The native Claude plugin curates explicit Skill paths. Its Codex plugin is deferred because its bucketed source layout cannot express that same curated subset with a single path;
its recorded tests found cached symlinks unsuitable. Dasen already has a six-Skill public tree, so this particular layout blocker is smaller here, but plugin installation still
needs actual package validation. Sources: [plugin manifest](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.claude-plugin/plugin.json),
[distribution decision](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/adr/0002-ship-as-a-claude-code-plugin.md).

## Updates, removal and recovery

| Project | Observed policy or mechanism | Limit relevant to Dasen |
|---|---|---|
| Gstack | Explicit upgrade Skill, opt-in auto-upgrade, hourly team updater, setup refresh, backup/restore branches, dedicated uninstall with `--keep-state`. | Lifecycle is extensive, not one atomic universal rollback. Git and copied installs take different paths. Uninstall leaves instruction-file cleanup to users. Do not import reset or silent-update behavior. |
| Superpowers | Updates/removal belong to the chosen manager. OpenCode documents cache/reinstall issues and pinning a Git tag. | No single universal doctor/uninstaller/rollback procedure was found in the reviewed entry and adapter files. Manager support must be checked per host. |
| Matt Pocock | Managed Claude channel or deliberate `npx skills update` for editable installations. | The ADR records an official-marketplace SHA pin: upstream release and availability to installed users can differ. No project-wide dependency doctor or universal rollback recipe was found in the reviewed entry/setup files. |

Sources: [Gstack upgrade](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/gstack-upgrade/SKILL.md), [team
updater](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/bin/gstack-session-update), [Gstack
uninstall](https://github.com/garrytan/gstack/blob/c8f0c4e368fd59ec316c0eb0d1f4ebfa896c2d16/README.md#uninstall), [Superpowers update
caveats](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/INSTALL.md#updating), [Matt install
modes](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/README.md#installation-30-second-setup), [marketplace pin
evidence](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/adr/0002-ship-as-a-claude-code-plugin.md#update-2026-08-05).

## Dasen distribution implications

The six Skills require sibling relationships and root files such as `requirements.txt`, `LICENSE`, `ORIGIN.md`, and `THIRD_PARTY.md`. The complete-artifact route now checks distribution integrity, declared dependency versions, and deterministic local HTML separately from native host discovery. See [installation checks](../../skills/dasen-content/scripts/install_check.py), [distribution scope](../../packs.yaml), and [measured evidence](../evidence/installation-readiness.md).

The examined Vercel Skills installer copies each selected Skill's subtree into an agent or canonical directory. It does not automatically carry arbitrary parent-root files with
that subtree. Consequently, copying Matt's `npx` entry verbatim would not itself solve Dasen's bundle root, dependency environment, notices or six-Skill closure. Source: [Vercel
installer at `80feb488`](https://github.com/vercel-labs/skills/blob/80feb48868972d518436f26711509bc78595b5cb/src/installer.ts#L337-L361).

That CLI revision is version 1.5.25 and requires Node `>=22.20.0`. It is an optional distribution adapter, not a reason to add mandatory Node setup to Dasen's Python runtime.
Source: [Vercel package metadata](https://github.com/vercel-labs/skills/blob/80feb48868972d518436f26711509bc78595b5cb/package.json).

## Recommended adoption order

1. **One short Chinese quick start.** Let the user select the harness and
   installation scope, with project scope as the default. Provide a copyable
   request for the agent and a manual fallback; show the first useful content
   task before explaining internals.
2. **One complete, versioned runtime bundle.** Preserve the six-Skill dependency
   closure, required root files, and one accountable installation owner. Use
   native plugins where their cache/payload semantics are verified. Gate any
   generic per-Skill installer route on an explicit layout adaptation test.
3. **Deterministic environment preparation beneath the conversation.** Reuse a
   compatible interpreter or prepare an isolated runtime; install the declared
   dependencies through a supported manager. Detect missing runtime, network,
   permissions and name collisions before activation. Keep additional system
   installations and accounts visible and scoped.
4. **A capability-specific doctor and first artifact.** Report distribution
   integrity, interpreter/dependency versions, native discovery and local
   conversion independently. Offer a separate user-requested first article and local HTML from
   supplied material; installation itself uses deterministic fixtures and makes no model calls. Do not require an external service or claim
   publishing readiness from that result.
5. **A reversible lifecycle.** Record installed version, owner, scope and files;
   preview changes, preserve user edits, replace only owned entries, and retain
   the previous working version until checks pass. Uninstall removes installed
   tools, while preserving the user's articles and project configuration unless
   separately requested. Manager-owned installations remain with that manager.

The acceptance target is a measured path from a clean supported environment to a first useful artifact, plus successful repeat install, upgrade, rollback and uninstall. Measure
required human decisions, elapsed time, failure recovery and remaining capabilities. Do not publish a 30-second or all-harness promise before those paths have actually been
exercised.
