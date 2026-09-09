# dasen-content 模型 Eval

通用盲测、评分、脱敏与证据要求遵循仓库 `docs/maintenance.md > 模型 Eval 证据`；本目录只保留 dasen-content 的用例、可见上下文和评分口径。`evals.json` 当前覆盖三类发行门禁：

- `should-trigger`：内容生产请求必须先进入唯一 router；
- `should-not-trigger`：纯资讯、纯采集、用户点名 stage、无关任务不得误触发；
- `output-contract`：即使正确触发，也不得越过 persona、事实、三轴或正式发布边界。

2026-09-05 历史 run 包含 12 项 2.0.3 用例。2.0.4 时另加系列状态投影用例；该 case 已于 2026-09-07 在三个逐 case 隔离的 Codex CLI 上下文中跨模型运行，结果为触发 3/3、完整契约 1/3、2 项 PARTIAL、0 项 FAIL。它不改写历史 30/36 结果，也不代表完整 13 case 已完成跨模型或原生 harness 评估；详见 `runs/2026-09-07-series-status-projection-eval.md`。路由集合声明的版本读取 `evals.json`，实际被测版本读取各 run；二者均不能代替当前 Skill 的版本与覆盖证明。

## 1. 确定性基线

从仓库根运行并把完整命令、版本、Git commit 与脏状态写入 run 记录：

```bash
python3 --version
python3 -m pytest --version
git rev-parse HEAD
git status --short
python3 scripts/validate.py
python3 skills/dasen-content/examples/verify_examples.py
python3 -m pytest \
  skills/dasen-content/tests \
  skills/dasen-knowledge/tests \
  skills/dasen-video/tests -q
python3 -m json.tool skills/dasen-content/evals/evals.json >/dev/null
python3 skills/dasen-content/evals/export_prompts.py >/tmp/dasen-content-prompts.jsonl
```

`export_prompts.py` 只导出 `id` 和 `prompt`，不会泄漏 expected output 或 assertions。可用 `--id <case-id>` 只导出一个 case。

## 2. 盲测输入与环境

每个 case 最好使用新的模型上下文。评估器只可见：

- `AGENTS.md`；
- `skills/dasen-content/SKILL.md`；
- `skills/dasen-content/references/contracts.md`；
- `skills/dasen-content/references/workflow.md`；
- 六个 dasen stage `SKILL.md` 的 frontmatter；
- `export_prompts.py` 输出的当前 case。

评估器不得读取 `evals.json`、`runs/` 或评分结果。工具限制为只读文件访问；不允许写文件、联网、平台动作或读取消费项目私人内容。若 harness 不能强制这些限制，run 记录必须明确说明。

固定 evaluator 指令：

```text
把自己当作刚收到该用户请求的 coding assistant。依据可见 Skill 契约决定是否调用 dasen-content。只返回一个 JSON 对象，字段固定为 id、invoke_content（布尔）、direct_route（字符串）、first_actions（最多3项字符串）、guardrails（最多3项字符串）。不得修改文件或执行内容生产。
```

记录模型完整标识、agent/profile、thinking/temperature（可得时）、harness 版本、是否逐 case 隔离、可见文件和工具清单。批量共享上下文的结果不得表述为逐 case 隔离。

## 3. 独立评分

评估回答落盘后，grader 才能读取 `evals.json`。逐项保存原始回答和 assertion 判定证据：

- `should-trigger` 与 `output-contract` 的 `invoke_content` 期望为 `true`；
- `should-not-trigger` 的期望为 `false`；
- `PASS`：触发判断正确且全部 assertions 有回答证据；
- `PARTIAL`：触发判断正确，但缺失护栏、状态核验，或提前推进用户未请求的 stage；
- `FAIL`：触发判断错误，或违反 persona、事实、平台发布等硬边界。

run 记录必须包含原始回答文件、逐 case/逐 evaluator 评分、grader 身份或模型、评分理由、基线命令结果和失败样例；只有汇总数字不能作为发行证据。

## 4. 数据与副作用边界

本 Skill 默认只使用仓库中的合成 prompt。若经授权加入真实失败样例，除共享维护规则外，还必须删除或替换：用户正文、私人 URL、账号/Media ID、凭证、设备路径及其它身份信息。无法可靠脱敏的样例只保留抽象复现描述，不进入 Git。

上述路由 Eval 只做无副作用决策，不执行内容生产。真实产物使用下面的独立协议；真实平台验证另走消费项目 preflight/dry-run，并按其授权单独记录。

## 5. 真实产物案例

`artifact-cases.json` 保存原创合成请求与原始材料，`artifact-rubric.json` 保存生产者不可见的判定依据。与路由问答分开版本化，实际执行写作、改稿和本地排版。执行与评审责任遵循仓库维护指南的“真实产物评估”。

```bash
# output 必须不存在；eval-results 已由仓库忽略
python3 skills/dasen-content/evals/artifact_eval.py prepare --output eval-results/<run-id>
# 每个 ID 单独启动新 Codex；model 使用本次批准的现有模型
python3 skills/dasen-content/evals/artifact_eval.py run \
  --run eval-results/<run-id> --id local-article-html --model <authorized-model>
python3 skills/dasen-content/evals/artifact_eval.py collect --run eval-results/<run-id>
```

`prepare --id` 可选单例；其余 ID 读取案例文件。快照排除整个 evals 目录，评分材料留在生产者工作区外。`run` 使用 `--ignore-user-config`、`--ephemeral`、`workspace-write` 与独立 `.agents/skills` 快照；它仍复用既有账号认证，不能据此宣称全局 Skill 元数据、系统读取权限或完整机器环境已隔离。检查 trace 是否真的使用本次快照、是否发生越界；不能用提示词约束冒充强制隔离。

每次重跑创建新目录，不覆盖先前结果。`collection.json` 保存实际产物 hash、材料/Skill 完整性、运行状态与可得 token；缺省语义评分始终为 `NOT_ASSESSED`。它不依据退出码自动评文章，也不替代独立评审。评审另存原始逐项证据；缺必需媒体时同时记录正确的阻塞行为和未完整交付。完整 run 不进入 Git，结论压缩到 `docs/history/` 的单份回执。

离线验证执行器可运行 `python3 -m pytest skills/dasen-content/evals/test_artifact_eval.py -q`；这些测试不调用模型，不能充当行为基线。

首轮实际运行与逐版本覆盖见 [2026-09-08 评估与校准回执](../../../docs/history/2026-09-08/editorial-calibration.md)。不可将历史或局部复验数字改称当前全部门禁通过。

## Guided conversations and integrated editorial comparison

`guidance-cases.json` contains synthetic requests, initial project artifacts, and frozen follow-up answers. `guidance-rubric.json` remains outside producer workspaces. Prepare it with `artifact_eval.py prepare --suite <case-file> --rubric <rubric-file> --output <new-run>`. Follow-up prompts are not copied into the producer workspace.

Run each turn through `conversation_eval.py --run <run> --id <case-id> --turn <n> --model <authorized-model>`. The first turn starts a fresh persisted CLI session; later turns resume its exact session ID. Inspect the previous answer before supplying a follow-up: if it no longer represents a coherent user response, retain the failed path and prepare a revised case rather than silently editing a frozen prompt. The runner records before/after hashes of all workspace files, including caches, plus per-turn traces, settings, usage, and process status. It refuses an existing turn, altered prompt, failed predecessor, or changed model settings. This proves observed filesystem changes, not system-level read isolation or semantic success.

`editorial-cases.json` supplies two raw material pools without preselected topics or titles. Use `artifact_eval.py` with `editorial-rubric.json` and separate baseline/candidate source snapshots. Record the observed baseline issue and expected method effect before candidate generation. Hide version labels in the owner's comparison; retain the mapping privately with run evidence. The adoption decision and workload are owned by `docs/spec.md`, not an automatic score in either runner.

The conversation tests do not count against the four-article editorial pilot. Neither suite establishes platform performance, cross-harness support, or stable editorial improvement by itself. Run `python3 -m pytest skills/dasen-content/evals -q` to check runner evidence integrity without model calls.
