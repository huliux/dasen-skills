# Agent installation procedure

Read this when asked to install, update, diagnose, or remove a complete Dasen artifact. The user-facing entry is README.md; the [manual guide](docs/en/installation.md#manual-installation-macos) contains the complete terminal sequence. This procedure is distributed with both source and installation artifacts; an unbuilt source checkout has no artifact manifest and cannot use the preparation route.

## Official Alpha download

For v0.1.0-alpha.1, download these two files into a fresh temporary directory:

- [Complete installation ZIP](https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/dasen-skills-0.1.0-alpha.1-install.zip)
- [SHA256SUMS](https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/SHA256SUMS)

Verify the ZIP against SHA256SUMS before extracting or executing it. Stop on a failed download or mismatch; do not fall back to an unverified source. Extract the ZIP and use its `dasen-skills-0.1.0-alpha.1` directory as the complete artifact. The [manual guide](docs/en/installation.md#manual-installation-macos) provides macOS commands. GitHub's generated source archives are for development, not installation.

## 1. Resolve the target

Resolve the source before preparing anything. Use artifact locations, attachments, and official release links already supplied in the conversation or project. Inspect only those locations and the current project's relevant files; do not guess a publisher/repository from the project name or scan the whole machine. For an explicit official release link, download the complete fixed-version artifact and verify its release checksum before execution. A bare project name is insufficient to authenticate a download.

If several supplied artifacts conflict, clarify the desired version. If no usable source is available, report that the official release link or complete artifact is missing and request that material through the host's supported attachment/link mechanism. Do not ask the user to edit placeholders in the installation prompt, invent a download URL, or report installation complete.

Identify the complete artifact path, operating system, intended content project, current Agent, and any existing installation owner. Reuse known context; ask only for ambiguous targets. The implemented automatic route is **macOS with Codex or Claude Code project entries**. This is a test route, not a claim of complete host or content-quality acceptance. Other environments require a separately verified adapter; the developer-only Windows procedure below verifies local execution only.

Use a fixed artifact from a verified maintainer/release channel and check its published checksum when available. Keep the complete payload, including `artifact-manifest.json`, six sibling Skills, root dependency files, and notices. A self-contained manifest checks consistency, not publisher identity. Do not substitute GitHub's source archive or copy six Skill folders alone.

Completion: one unambiguous project and host, a complete trusted artifact, and a compatible route. Preserve another manager's installation; use that manager or resolve the conflict before replacement. Installation authorization covers the requested route, not extra hosts, content creation, or account writes.

## 2. Prepare the runtime on macOS

Run with the actual artifact path, quoted for the shell:

```sh
/bin/sh "<artifact>/prepare-macos.sh"
```

The script downloads pinned, checksum-verified uv and managed Python, stores the artifact, installs hash-locked dependencies, and tests bundled local HTML conversion. It needs internet access but not Python, Node.js, or Git on PATH. It does not change system Python, PATH, or shell profiles. Agent guidance itself uses the host's normal model allowance; deterministic installation checks make no model calls.

Default Dasen storage is `~/Library/Application Support/dasen-skills/`: `tools/` holds uv, `releases/` complete artifacts, `runtimes/` versioned venvs and receipts, and `projects/` machine binding records. uv owns its managed Python and download cache; report the actual returned locations. Managed Python is an active dependency, not disposable cache. `DASEN_DATA_ROOT` can explicitly select separate absolute storage.

Read the JSON result. Require `status: local-ready` and record `artifact_root`, `python`, `receipt`, `source_revision`, and `release_id`. Use this **returned interpreter and stored artifact** for subsequent commands. `<data>` below is the chosen storage root; `<ready>` is the returned receipt. Exit 0 here proves only local readiness; no host is enabled yet.

On download failure, explain the failing phase and allow retry. Repeating preparation rechecks and reuses healthy state. Preserve changed artifacts; a failed runtime recheck can be repaired with explicit `--repair`, which creates a new generation and retains the old one. A missing prerequisite or failed check is not successful installation.

## 3. Connect the project

Replace placeholders with the resolved paths. `<host>` is `codex` or `claude-code`; repeat `--host` only if the user explicitly requested both.

```sh
"<python>" -B "<artifact>/skills/dasen-content/scripts/project_install.py" plan --project "<project>" --data-root "<data>" --ready "<ready>" --host <host>
"<python>" -B "<artifact>/skills/dasen-content/scripts/project_install.py" apply --project "<project>" --data-root "<data>" --ready "<ready>" --host <host>
"<python>" -B "<artifact>/skills/dasen-content/scripts/project_install.py" status --project "<project>" --data-root "<data>"
```

Inspect the plan before applying. When it matches the authorized target and reports no blocking conflict, continue without another confirmation. Preserve unowned entries and local edits. Global/ancestor same-name entries require native conflict inspection; do not delete them or edit unrelated host settings to force discovery.

The project receives `dasen-skills.lock.json`, `.dasen-skills/` bindings and runner, six relative discovery links per selected host, and a managed `.gitignore` block. Codex uses `.agents/skills`; Claude Code uses `.claude/skills`. Other compatible tools may read these directories; only the selected entry sets are created.

Completion: `status` reports `bound-locally` with the intended source revision and host set. `recovery-required` must be resolved before normal use. File bindings alone do not establish native discovery.

## 4. Verify native discovery and hand off

Refresh/reopen the host using its supported mechanism and inspect which six Skills and paths it actually loads. Claude Code may select a same-name personal Skill over a project Skill; Codex can list multiple scopes. Verify the selected source, not just the name. If the host cannot be inspected, report **local checks passed; native discovery unverified**, with the required user action. Do not claim a desktop result from CLI evidence.

Report the version, project, selected host, installation owner, payload/runtime locations, local check result, native discovery result, and next step. Offer this first-task prompt without executing it during installation:

> Use dasen-content to write a Chinese article from my supplied material, state sources and uncertainties, and export local WeChat HTML. No images or uploads yet.

Subsequent project scripts use the captured runtime boundary:

```sh
/bin/sh "<project>/.dasen-skills/run" <dasen-skill>/scripts/<script>.py [arguments]
```

For example, local export of an already prepared content package uses:

```sh
/bin/sh "<project>/.dasen-skills/run" dasen-wechat/scripts/native_publish.py --dry-run --output "exports/article-wechat.html" "<content-package>"
```

Keep content outside the artifact. Incomplete sources, editorial errors, or missing delivery records remain content failures even when local scripts pass.

## Updates, removal, and diagnostics

For an authorized update, pause content execution, record the current selection and preserve user data, prepare the new complete artifact, then plan/apply/status with its returned interpreter and receipt. All registered hosts in that project switch together; other projects stay pinned. Rollback selects a retained previous ready receipt through the same process. A source rollback does not restore migrated project data. Existing source managers retain their own lifecycle.

Use the same interpreter/script prefix from step 3 for these actions:

- `uninstall --project "<project>" --data-root "<data>"`: removes only owned project entries; retains articles and shared resources.
- `recover --project "<project>" --data-root "<data>"`: rolls back an interrupted switch; `--finish` explicitly completes it instead. Preserve later user edits when recovery refuses.
- `cleanup --data-root "<data>"`: inventory only; deletes nothing.
- Fresh clones: obtain the exact locked release, prepare it, and plan/apply with `--rebind`. Existing bindings after a folder move need explicit reconciliation; see the [project installation contract](skills/dasen-content/references/project-installation.md).

To inspect artifact integrity, dependencies, and bundled HTML independently:

```sh
"<python>" -B "<artifact>/skills/dasen-content/scripts/install_check.py" --json
```

Exit 1 is local failure; exit 2 is local success with native discovery unverified. Explicit `--local-only` returns 0 for local success alone. Optional `--output "<new-directory-outside-artifact>"` preserves sample HTML and refuses an existing directory. `doctor.py` inventories capabilities; it is not complete installation acceptance. Publish only redacted diagnostics.

## Windows: developer testing only

Automatic preparation and project binding are not implemented on Windows. For an explicitly requested local test, use an existing Python 3.10+ to create a separate venv outside the artifact, then run in PowerShell:

```powershell
python -m venv "<new-venv>"
& "<new-venv>/Scripts/python.exe" -m pip install --require-hashes -r "<artifact>/requirements.txt"
& "<new-venv>/Scripts/python.exe" -B "<artifact>/skills/dasen-content/scripts/install_check.py" --json
```

Use the validated interpreter without relying on activation. Report local readiness separately from the unimplemented binding route. Do not run the macOS shell bootstrap or project installer on Windows, or claim that these checks activate a host.
