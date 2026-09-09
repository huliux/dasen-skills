# dasen-skills · 大森的内容创作 Skills

[English](README.en.md)

把资料和想法变成有来源的中文文章、配图和微信公众号 HTML。在你使用的 AI Agent 中，从 `dasen-content` 开始即可。

## 安装

**首个社区测试版：[v0.1.0-alpha.1](https://github.com/huliux/dasen-skills/releases/tag/v0.1.0-alpha.1)。** macOS 的安装流程已实现；Windows 和其他工具的状态见[兼容性](docs/zh-CN/compatibility.md)。

### 让 Agent 安装

在 Codex 或 Claude Code 中打开创作项目，直接复制以下提示词，无需填写路径或手动下载：

```text
帮我安装 dasen-skills，供当前项目和当前 Agent 使用。
请读取官方安装说明 https://raw.githubusercontent.com/huliux/dasen-skills/v0.1.0-alpha.1/INSTALL.md ，按说明自行下载并校验 v0.1.0-alpha.1 完整安装包，然后完成安装。
自动准备所需环境，保留已有安装和修改，最后检查实际加载的版本并告诉我是否可以开始使用。
```

首次安装需联网，macOS 无需预装 Python、Node.js 或 Git。

### 手动安装

希望自己操作终端？按[手动安装步骤](docs/zh-CN/installation.md#手动安装macos)依次准备环境、选择工具、连接项目并检查结果。它与提示词安装使用同一套安装程序。

## 开始使用

安装并刷新工具后，提供材料，再发送：

> 使用 dasen-content，根据我提供的材料写一篇中文文章，明确来源和未知项，导出本地微信 HTML。暂不配图，不上传。

你也可以直接说：

- “围绕这个主题规划一个系列，并开始第一篇。”
- “继续这个系列的下一篇文章。”
- “修改这篇稿子，让结论更清楚、论据更扎实。”
- “看看这个项目的内容进展。”

研究、写作、知识整理、配图和微信导出由五个协作阶段完成，通常只需使用 `dasen-content`。普通写作和本地导出无需配置公众号、品牌或生图服务。

## 帮助与贡献

[完整安装指南](docs/zh-CN/installation.md) · [兼容性](docs/zh-CN/compatibility.md) · [升级与卸载](docs/zh-CN/updating.md)

欢迎在项目仓库提交中文或英文 Issue 与 PR。贡献者可从源码中的 `CONTRIBUTING.md` 开始。

采用 [MIT 许可证](LICENSE)；来源与外部组件见 [ORIGIN](ORIGIN.md) 和 [THIRD_PARTY](THIRD_PARTY.md)。
