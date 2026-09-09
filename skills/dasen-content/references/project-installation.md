# Project artifact bindings (macOS)

Use this route for a reviewed complete artifact after `prepare-macos.sh` reports local readiness. Native plugin-owned installations keep their original manager. The caller identifies the consumer project and requested tools; a maintenance checkout or result directory is not automatically the consumer. No public download channel or native desktop acceptance is implied.

## Bind or update

Use the bootstrap result's `python`, `receipt` (the generation's `ready.json`) and data root. Run `project_install.py` from the reviewed artifact with that interpreter:

```sh
<python> -B <artifact>/skills/dasen-content/scripts/project_install.py plan --project <project> --data-root <data> --ready <ready.json> --host codex
<python> -B <artifact>/skills/dasen-content/scripts/project_install.py apply --project <project> --data-root <data> --ready <ready.json> --host codex
```

Use `--host claude-code` for Claude Code, or repeat `--host` when both were requested. The plan is read-only. Review exact paths, inherited entries and shared scope; application creates only requested entry sets. Both directories may be read by other compatible tools. Existing project installations or modified owned files block replacement. Inherited user/ancestor entries are reported and preserved; native settings, permissions and plugin conflicts still require host inspection. Resolve ambiguous same-name/native-manager discovery through its owner before claiming the selected version is usable.

For an update, prepare the new complete release first and supply its ready receipt. Omitting `--host` keeps all registered hosts. Adding another explicit host never removes existing ones. The single project pointer selects both release and interpreter; no other project's pointer changes. Repetition validates existing state and reuses it. Downgrading through the same command with an older verified receipt that supports project bindings is source-version rollback; content is untouched. `status` reports prior receipt choices. A broken or edited artifact is not silently repaired or replaced.

## Files and execution

- `dasen-skills.lock.json`: portable release identity, source revision, host selections and shared-scope choice. It contains no machine paths.
- `.dasen-skills/`: ignored local binding and `run` entry. Host Skill links go through this binding into the complete user-owned artifact.
- Selected `.agents/skills/dasen-*` and/or `.claude/skills/dasen-*`: six relative links per requested host. They are ignored because machine bindings must be rebuilt on another machine.
- `.gitignore`: one owned block; other text is preserved. User edits to that block require reconciliation.
- `<data>/projects/<project-path-hash>/`: private machine state, immutable binding generations, current pointer and any interrupted-switch journal. Runtime and release storage remain shared.

For script execution, use the project entry with a release-relative script name:

```sh
/bin/sh <project>/.dasen-skills/run dasen-content/scripts/doctor.py
/bin/sh <project>/.dasen-skills/run dasen-wechat/scripts/native_publish.py --dry-run --output exports/article-wechat.html <bundle>
```

The entry captures a single binding, uses its Python and Skill script, and runs from the project root. It removes inherited `PYTHON*` overrides for the command tree and disables bytecode writes and user-site imports in nested Python calls, so local rendering leaves the complete artifact unchanged. It blocks incomplete switches, divergent portable selections and paths outside the selected release. A call already executing can finish with its captured version; refresh the host before new content work after a version change. No background host refresh or automatic article creation occurs.

## Inspect, recover, move and uninstall

`status --project <project> --data-root <data>` checks owned files, the version pointer and runtime, reports inherited entries and refresh requirements, and retains `native_discovery: unverified`. A successful command or link resolution is not native discovery evidence. Verify the exact selected release in the chosen host and then perform a separately requested first article.

Normal switch errors attempt rollback. A killed process leaves `pending.json`; `recover --project <project> --data-root <data>` rolls it back, while `recover --finish ...` validates the target and finishes it. Recovery accepts only recorded before/after file states. Later user edits block automatic recovery and remain preserved; inspect the journal and differences before resolving them. An unfinished transaction blocks content execution.

On a fresh clone containing the portable lock and ignore rules, prepare that exact release and use `plan/apply --rebind ...`. A different release is refused. Copied virtual environments, old absolute bindings, and moved-but-still-bound folders are not fresh clones: preserve and reconcile their old machine bindings before rebinding; the installer does not guess ownership from their names.

`uninstall --project <project> --data-root <data>` removes the owned project entries, portable selection and ignore block while preserving articles, business settings, unrelated ignore rules, shared releases and runtimes. Changed owned files block deletion. Machine records remain as inactive recovery/ownership evidence. Empty host container directories may remain.

`cleanup --data-root <data>` currently inventories known project references, uncertainty and runtime sizes; it deletes nothing. Missing projects, pending transactions, and direct/unregistered runtime use cannot be proven safe from receipts alone. Automatic deletion and active-use leases remain a separate acceptance item; never reinterpret “not currently registered” as “safe to delete”.

## Sources and limits

[Codex local discovery](https://learn.chatgpt.com/docs/build-skills) documents `.agents/skills` and symlink support. [Claude Code skills](https://code.claude.com/docs/en/skills) documents `.claude/skills`, symlink support and name precedence. These sources establish route candidates, not acceptance of this installation. This implementation targets macOS filesystem bindings; native Windows, native desktop discovery, plugin lifecycle and formal support remain separately verified.
