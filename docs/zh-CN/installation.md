# 安装 dasen-skills

[English](../en/installation.md) · [返回首页](../../README.md)

选择一种方式即可：**不想操作终端，选提示词安装；想自己控制每一步，选手动安装。** 两种方式使用相同的程序，完成后得到相同的项目安装。

## 安装前准备

- 一台 Mac，已能正常使用 Codex 或 Claude Code；其他环境见[兼容性](compatibility.md)。
- 一个准备存放文章的创作文件夹。
- 提示词安装会自动下载安装包；手动安装按下面第 1 步下载。
- 可联网下载依赖。无需预装 Python、Node.js 或 Git，也无需配置公众号或 API Key。

完整安装包见 [v0.1.0-alpha.1 发行页](https://github.com/huliux/dasen-skills/releases/tag/v0.1.0-alpha.1)。若只有 Git 源码，见文末的开发者构建方法；GitHub 的“Source code”压缩包不能直接当作安装包运行。

## 提示词安装（推荐）

在 AI 工具中打开创作文件夹，直接复制下面整段，无需填写路径或提前下载：

```text
帮我安装 dasen-skills，供当前项目和当前 Agent 使用。
请读取官方安装说明 https://raw.githubusercontent.com/huliux/dasen-skills/v0.1.0-alpha.1/INSTALL.md ，按说明自行下载并校验 v0.1.0-alpha.1 完整安装包，然后完成安装。
自动准备所需环境，保留已有安装和修改，最后检查实际加载的版本并告诉我是否可以开始使用。
```

Agent 会依次检查系统与目标、准备依赖、连接项目并验证结果。目标不明确或已有安装冲突时，它会说明问题；正常步骤直接继续。引导过程使用当前 AI 工具的正常额度。

完成后跳到[确认安装与首次使用](#确认安装与首次使用)。

## 手动安装（macOS）

以下命令在 Mac 的“终端”中执行。**保持在同一个终端窗口，按顺序操作；任何一步报错都先停止处理。** 全程不需要 `sudo`。

### 1. 下载并校验安装包

直接复制整段；显示压缩包校验 `OK` 后再继续。

```sh
dasen_download="$(mktemp -d "${TMPDIR:-/tmp}/dasen-download.XXXXXX")" &&
curl -fL --retry 3 "https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/dasen-skills-0.1.0-alpha.1-install.zip" -o "$dasen_download/dasen-skills-0.1.0-alpha.1-install.zip" &&
curl -fL --retry 3 "https://github.com/huliux/dasen-skills/releases/download/v0.1.0-alpha.1/SHA256SUMS" -o "$dasen_download/SHA256SUMS" &&
(cd "$dasen_download" && shasum -a 256 -c SHA256SUMS) &&
ditto -x -k "$dasen_download/dasen-skills-0.1.0-alpha.1-install.zip" "$dasen_download" &&
dasen_artifact="$dasen_download/dasen-skills-0.1.0-alpha.1"
```

### 2. 选择项目和工具

第一行填创作文件夹；使用 Claude Code 时，将第二行的 `codex` 改成 `claude-code`。路径保留双引号。第三行使用默认存储位置即可。

```sh
dasen_project="$HOME/Documents/my-writing"
dasen_host="codex"
dasen_data="$HOME/Library/Application Support/dasen-skills"

test -f "$dasen_artifact/artifact-manifest.json" && mkdir -p "$dasen_project"
```

最后一行检查包内清单，并在需要时创建创作文件夹；不会覆盖已有文章。找不到清单时，先核对解压位置和包的类型。

### 3. 准备环境

复制整段执行。脚本安装所需的 Python 和锁定依赖；后面几行自动读取结果，供下一步使用，无需手动复制回执字段。

```sh
dasen_result="$(DASEN_DATA_ROOT="$dasen_data" /bin/sh "$dasen_artifact/prepare-macos.sh")" &&
dasen_python="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract python raw -o - -)" &&
dasen_release="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract artifact_root raw -o - -)" &&
dasen_ready="$(printf '%s' "$dasen_result" | /usr/bin/plutil -extract receipt raw -o - -)" &&
printf '%s\n' 'Environment ready. Continue to step 4.'
```

出现 `Environment ready. Continue to step 4.` 后继续。首次下载可能需要几分钟。这一步只准备环境，还没有接入 AI 工具。

### 4. 连接项目

先查看将创建的入口和已有安装：

```sh
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" plan \
  --project "$dasen_project" --data-root "$dasen_data" --ready "$dasen_ready" --host "$dasen_host"
```

确认输出中的项目与工具正确、没有阻止安装的冲突后，执行：

```sh
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" apply \
  --project "$dasen_project" --data-root "$dasen_data" --ready "$dasen_ready" --host "$dasen_host" &&
"$dasen_python" -B "$dasen_release/skills/dasen-content/scripts/project_install.py" status \
  --project "$dasen_project" --data-root "$dasen_data"
```

最后的 `status` 应显示 `bound-locally`：项目文件已连接。若列出同名全局入口，还需在下一步确认实际加载路径。

## 确认安装与首次使用

1. 在工具中重新打开创作项目或刷新 Skill 列表。
2. 确认能发现 `dasen-content`、`dasen-research`、`dasen-writing`、`dasen-knowledge`、`dasen-visual` 和 `dasen-wechat`，并核对来源是本次选择的版本。
3. 提供一份材料，发送下面的请求：

> 使用 dasen-content，根据这份材料写一篇中文文章，明确来源和未知项，导出本地微信 HTML。暂不配图，不上传。

能看到名称并不保证加载了正确版本：Claude Code 可能优先加载同名个人入口。如果无法核对，保留“工具发现未验证”的状态。安装检查使用内置示例；文章事实和实际交付还需复核。

## 文件在哪里

文章留在创作项目中；`dasen-skills.lock.json` 记录所选版本，隐藏目录保存入口和本机绑定。安装包与运行环境共享保存在 `~/Library/Application Support/dasen-skills/`；Python 本体和下载缓存由 uv 管理。系统 Python、PATH 和 shell 配置不变。

## 常见问题

| 情况 | 下一步 |
|---|---|
| 下载失败 | 检查 GitHub 下载源和 PyPI 的连通性，恢复后重试第 1 或 3 步；原有环境保留。 |
| 已有安装或本地修改冲突 | 保留文件，让 Agent 按 `INSTALL.md` 判断归属和处理方式。 |
| 安装完成但工具看不到 | 重新打开正确项目，检查实际加载路径和同名全局入口。 |
| 换了终端窗口 | 重新执行第 1 至 3 步恢复变量；健康环境会复用。 |
| 升级、回滚或卸载 | 见[升级与卸载](updating.md)。 |
| Windows | 自动环境准备和项目绑定尚未实现；已有 Python 的开发者可按 [Windows 本地检查](../../INSTALL.md#windows-developer-testing-only)测试，不代表完整安装成功。 |

<details>
<summary>从 Git 源码构建安装包（开发者）</summary>

需要 Git 和 uv。在来源已确认、工作区干净的 Git checkout 根目录执行；输出目录必须尚不存在：

```sh
uv sync --locked
uv run --locked python scripts/build_public.py --kind install --output ../dasen-skills-install
```

构建通过后，将上面的 `dasen_artifact` 指向生成的目录，再继续安装。本方法用于开发与测试；普通用户直接使用完整发行安装包。

</details>
