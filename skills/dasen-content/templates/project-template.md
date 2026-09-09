---
schema_version: 3
project: example-project
brand:
  name: null
  aliases: []
channels: {}
authors:
  default: null
  profiles: {}
writing:
  style_library: null
defaults:
  profile: practical
  language: zh-CN
editorial:
  word_count:
    quick: {min: 1, max: 1000}
    standard: {min: 1000, max: 2500}
    deep: {min: 3000, max: 5000}
  title:
    default: {min: 1, max: 100, forbidden_characters: []}
  sources:
    default: {minimum: 2, primary_required: false}
    breaking: {minimum: 1, primary_required: true}
    deep: {minimum: 5, primary_required: false}
assets:
  root: assets
  remote:
    provider: none
    endpoint: null
    region: null
    bucket: null
    public_base_url: null
    access_key_env: null
    secret_key_env: null
    keychain_service: null
    access_key_account: null
    secret_key_account: null
visual:
  style_library: null
  defaults:
    body_style: body-clean-editorial
    cover_style: cover-clean-editorial
  rendering:
    body: auto
    cover: auto
  cover_size: null
  layout_library: null
  generation:
    required: false
    provider: none
    model: null
    endpoint: null
    api_key_env: null
    credential_profile: null
    options: {}
hard_rules:
  product_placement_opt_in: true
  author_persona_opt_in: true
  publish_requires_human: true
---

# Project

## 使命与读者

项目为什么存在、服务谁、读者完成什么任务。

## 内容承诺

稳定兑现的价值，不写单篇结构和临时语气。

## 可选配置

需要长期复用时再增加 `brand`、`authors.profiles`、`writing.style_library`、`visual.style_library`、`channels.<platform>`、视觉 Adapter 或远程存储；单篇生产不依赖这些配置。

## 事实、安全与平台边界

项目不可被单篇 brief 覆盖的规则。

## 产品与作者身份

- 产品植入默认关闭；仅单篇 brief 显式开启并填写产品名与事实锚点。
- 作者人设、第一人称和联系方式默认关闭；仅使用项目配置和已验证经历。

## 活跃系列

| series | phase | 核心假设 | 路径 |
|---|---|---|---|
