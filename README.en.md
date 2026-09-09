# dasen-skills · Content creation by dasen

[简体中文](README.md)

Turn material and ideas into sourced Chinese articles, visuals, and WeChat HTML. Start with `dasen-content` in your AI Agent.

## Install

**First community test release: [v0.1.0-alpha.1](https://github.com/huliux/dasen-skills/releases/tag/v0.1.0-alpha.1).** The macOS installation flow is implemented. See [compatibility](docs/en/compatibility.md) for Windows and other hosts.

### Ask your Agent to install

Open your content project in Codex or Claude Code and paste this unchanged. No path editing or manual download is needed:

```text
Install dasen-skills for the current project and current Agent.
Read the official instructions at https://raw.githubusercontent.com/huliux/dasen-skills/v0.1.0-alpha.1/INSTALL.md and follow them to download, verify, and install the complete v0.1.0-alpha.1 artifact.
Prepare the required environment, preserve existing installations and edits, then verify the version actually loaded and tell me whether it is ready to use.
```

First preparation needs internet access. Python, Node.js, and Git need not be preinstalled on macOS.

### Install manually

Prefer the terminal? Follow the [manual steps](docs/en/installation.md#manual-installation-macos) to prepare the environment, select your host, connect the project, and verify the result. Both routes use the same installer.

## Start creating

After installation and host refresh, supply material and ask:

> Use dasen-content to write a Chinese article from my supplied material, state sources and uncertainties, and export local WeChat HTML. No images or uploads yet.

You can also ask:

- “Plan a series around this topic and start the first article.”
- “Continue with the next article in this series.”
- “Revise this draft for a clearer conclusion and stronger evidence.”
- “Show me this project's content progress.”

Research, writing, knowledge, visuals, and WeChat export are five cooperating stages. Normally, use only `dasen-content`. Ordinary writing and local export need no WeChat account, brand setup, or image-generation service.

## Help and contributions

[Installation guide](docs/en/installation.md) · [Compatibility](docs/en/compatibility.md) · [Updates and removal](docs/en/updating.md)

Chinese or English Issues and PRs are welcome in the project repository. Contributors can start with `CONTRIBUTING.md` in the source checkout.

Licensed under [MIT](LICENSE). See [origin](ORIGIN.md) and [external components](THIRD_PARTY.md).
