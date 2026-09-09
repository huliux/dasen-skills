# Install dasen-skills

[简体中文](../zh-CN/installation.md) · [Home](../../README.en.md)

Choose one route: **use the Agent prompt to avoid terminal work, or follow the manual steps to control each action.** Both routes use the same installer and produce the same project installation.

## Before you start

- A Mac with a working Codex or Claude Code installation; see [compatibility](compatibility.md) for other environments.
- A folder for your content project.
- The Agent downloads the artifact automatically; manual users download it in step 1 below.
- Internet access for dependencies. Python, Node.js, Git, a WeChat account, and API keys are not prerequisites.

Get the complete artifact from [v0.1.0-alpha.1](https://github.com/huliux/dasen-skills/releases/tag/v0.1.0-alpha.1). If you only have a Git checkout, see the developer build instructions below. GitHub's “Source code” archive is not a ready installation artifact.

## Install with an Agent (recommended)

Open your content folder in the AI tool and paste the entire prompt unchanged. No path editing or advance download is needed:

```text
Install dasen-skills for the current project and current Agent.
Read the official instructions at https://raw.githubusercontent.com/huliux/dasen-skills/v0.1.0-alpha.1/INSTALL.md and follow them to download, verify, and install the complete v0.1.0-alpha.1 artifact.
Prepare the required environment, preserve existing installations and edits, then verify the version actually loaded and tell me whether it is ready to use.
```

The Agent checks the system and targets, prepares dependencies, connects the project, and verifies results. It explains ambiguous targets or installation conflicts and continues through ordinary steps. Guidance uses your current AI tool's normal allowance.

Then go to [verification and first use](#verification-and-first-use).

## Manual installation (macOS)

Run these commands in the Mac Terminal. **Use the same terminal window throughout, in order; stop and resolve any error before continuing.** No `sudo` is needed.

### 1. Download and verify the artifact

Paste the whole block. Continue only after the archive checksum reports `OK`.

```sh
dasen_download="$(mktemp -d "${TMPDIR:-/tmp}/dasen-download.XXXXXX")" &&
curl -fL --retry 3 "https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/dasen-skills-0.1.0-alpha.1-install.zip" -o "$dasen_download/dasen-skills-0.1.0-alpha.1-install.zip" &&
curl -fL --retry 3 "https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/SHA256SUMS" -o "$dasen_download/SHA256SUMS" &&
(cd "$dasen_download" && shasum -a 256 -c SHA256SUMS) &&
ditto -x -k "$dasen_download/dasen-skills-0.1.0-alpha.1-install.zip" "$dasen_download" &&
dasen_artifact="$dasen_download/dasen-skills-0.1.0-alpha.1"
```

### 2. Select the project and host

Set your content folder on the first line. For Claude Code, replace `codex` with `claude-code` on the second line. Keep the double quotes. The third line uses the default storage location.

```sh
dasen_project="$HOME/Documents/my-writing"
dasen_host="codex"
dasen_data="$HOME/Library/Application Support/dasen-skills"

test -f "$dasen_artifact/artifact-manifest.json" && mkdir -p "$dasen_project"
```

The final line checks the manifest and creates the content folder if needed, preserving existing articles. If the manifest is missing, check the extracted location and artifact type first.

### 3. Prepare the environment

Paste the whole block. The script installs Python and locked dependencies; the remaining lines read the results automatically for the next step, without manual receipt copying.

```sh
dasen_result="$(DASEN_DATA_ROOT="$dasen_data" /bin/sh "$dasen_artifact/prepare-macos.sh")" &&
dasen_python="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract python raw -o - -)" &&
dasen_release="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract artifact_root raw -o - -)" &&
dasen_ready="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract receipt raw -o - -)" &&
printf '%s\n' 'Environment ready. Continue to step 4.'
```

Continue only after `Environment ready. Continue to step 4.` appears. First downloads may take several minutes. This step prepares the environment; it does not connect a host yet.

### 4. Connect the project

First inspect the planned entries and any existing installations:

```sh
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" plan \
  --project "$dasen_project" --data-root "$dasen_data" --ready "$dasen_ready" --host "$dasen_host"
```

When the project and host are correct and no blocking conflict is reported, run:

```sh
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" apply \
  --project "$dasen_project" --data-root "$dasen_data" --ready "$dasen_ready" --host "$dasen_host" &&
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" status \
  --project "$dasen_project" --data-root "$dasen_data"
```

The final `status` should show `bound-locally`: the project files are connected. If same-name global entries are listed, verify the actual loaded path in the next step.

## Verification and first use

1. Reopen the content project in your host or refresh its Skill list.
2. Confirm discovery of `dasen-content`, `dasen-research`, `dasen-writing`, `dasen-knowledge`, `dasen-visual`, and `dasen-wechat`, and inspect that their source is the selected version.
3. Supply material and ask:

> Use dasen-content to write a Chinese article from this material, state sources and uncertainties, and export local WeChat HTML. No images or uploads yet.

Names alone do not establish the loaded version: Claude Code may prefer a same-name personal entry. If the source cannot be checked, report native discovery as unverified. Installation checks use a bundled sample; article accuracy and complete delivery still need review.

## File locations

Articles stay in the content project. `dasen-skills.lock.json` records the selected version; hidden directories hold discovery entries and machine bindings. Artifacts and runtimes share `~/Library/Application Support/dasen-skills/`; uv owns managed Python and download caches. System Python, PATH, and shell configuration remain unchanged.

## Troubleshooting

| Situation | Next step |
|---|---|
| Download failure | Check GitHub download and PyPI connectivity, then retry step 1 or 3. Existing environments are preserved. |
| Existing installation or local edit conflict | Preserve the files and ask the Agent to resolve ownership under `INSTALL.md`. |
| Host cannot see the installed Skills | Reopen the correct project and inspect actual paths and same-name global entries. |
| New terminal window | Repeat steps 1 through 3 to restore variables; healthy environments are reused. |
| Update, rollback, or removal | See [updates and removal](updating.md). |
| Windows | Automated preparation and project binding are not implemented. Developers with Python can run [Windows local checks](../../INSTALL.md#windows-developer-testing-only); these do not constitute complete installation. |

<details>
<summary>Build an artifact from a Git checkout (developers)</summary>

Git and uv are required. From a trusted, clean Git checkout, run the following. The output directory must not already exist:

```sh
uv sync --locked
uv run --locked python scripts/build_public.py --kind install --output ../dasen-skills-install
```

After the build passes, point `dasen_artifact` to the output and continue installation. This route is for development and testing; ordinary users use the complete release artifact.

</details>
