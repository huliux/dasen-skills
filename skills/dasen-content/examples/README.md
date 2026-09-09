# Brief examples

- `series-deep-brief.yaml`：长期系列 + deep + original；产品植入和作者身份关闭。
- `breaking-quick-pattern-brief.yaml`：突发事件 + quick + pattern-adapt；要求第一来源、checked_at、单源声明与参考结构登记。

示例只展示控制字段，不是可发布内容。复制后必须替换日期、目标、来源和渠道配置；`example.com` 只作占位，不得进入正式 sources/article。

## 可复现验收（2026-09-04）

```bash
python3 <skills-dir>/dasen-content/examples/verify_examples.py
```

脚本使用临时目录、无网络、无正式发布副作用；当前结果 `34/34 passed`。

| 路径/门禁 | 预期 |
|---|---|
| 零配置创建 standalone，内容品牌未设置 | PASS |
| standalone 无微信凭证导出本地 HTML，brief/record 不变 | PASS |
| series + deep + original + 5 条完整来源 | PASS |
| breaking + quick + pattern-adapt + 1 个事实第一来源 + 1 个结构参考 | PASS |
| 配置的产品未授权出现 | FAIL |
| 已授权产品仍放文章末段 | FAIL |
| 配置的作者联系信息未授权出现 | FAIL |
| 作者只开 byline 却加入 contact | FAIL |
| source minimum 降到模式底线以下 | FAIL |
| required phrase 缺失 | FAIL |
| 单一事实来源却声明 false | FAIL |
| 来源缺 title/supports/confidence/checked_at 等证据字段 | FAIL |
| 本地图片用 `../` 逃出 assets | FAIL |
| assets 内符号链接指向包外文件 | FAIL |
| HTTPS URL 指向 loopback/private 地址 | FAIL |
| init 开启植入/persona 后 record 仍写关闭 | FAIL（当前已正确写开启） |
| WeChat dry-run 修改 brief/record | FAIL（当前无状态副作用） |
| WeChat 本地导出要求账号、封面、生图或 CDN | FAIL（这些只影响可选增强或远程投递） |
| 微信草稿 API 没有返回 Media ID | FAIL，不标 delivered |
| 有 Media ID 的草稿回执 | PASS，record 保留 ID 并标 delivered |

真实项目验收只记入对应项目的 `record.md`，不把项目名称、正文或业务阈值复制进可分发示例。
