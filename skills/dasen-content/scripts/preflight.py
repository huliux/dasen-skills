#!/usr/bin/env python3
"""Deterministic preflight for a dasen content bundle.

Exit 0 only when every required check for the selected stage passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("[error] PyYAML 未安装：python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

from content_paths import bundle_root, evidence_dir
from source_policy import factual_origins
from project_config import (
    assets_config,
    brand_config,
    channel_config,
    deep_merge,
    editorial_config,
    load_project_reference,
    visual_config,
)
from network_safety import resolve_public_addresses
from style_profiles import STYLE_ID, validate_style_snapshot
from visual_styles import METHODS as VISUAL_METHODS
from visual_styles import validate_style_snapshot as validate_visual_style_snapshot

ALLOWED = {
    "journey": {"series", "breaking", "material"},
    "length": {"quick", "standard", "deep", "custom"},
    "method": {"original", "pattern-adapt", "revise"},
}
SOURCE_TYPES = {"primary", "official", "first-party", "independent", "secondary", "data"}
CONFIDENCE = {"high", "medium", "low"}
UNRESOLVED = re.compile(r"TODO|TBD|FIXME|\{\{[^}]+\}\}|\[待补[^]]*\]|<待补[^>]*>", re.I)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_WORD = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?")
IMAGE = re.compile(r"!\[[^]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
MAX_REMOTE_ASSET_BYTES = 20 * 1024 * 1024


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"YAML 无法解析：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML 顶层必须是对象：{path}")
    return data


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception as exc:
        raise ValueError(f"文章 frontmatter 无法解析：{exc}") from exc
    return meta, text[m.end():]


def visible_text(body: str) -> str:
    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    body = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"https?://\S+", " ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"^\s{0,3}#{1,6}\s*", "", body, flags=re.M)
    body = re.sub(r"[*_~`>|]", "", body)
    return body


def text_units(body: str) -> int:
    text = visible_text(body)
    return len(CJK.findall(text)) + len(LATIN_WORD.findall(text))


def title_from(meta: dict, body: str) -> str:
    if str(meta.get("title") or "").strip():
        return str(meta["title"]).strip()
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return m.group(1).strip() if m else ""


def normalized_label(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def source_entries(path: Path) -> tuple[dict, list[dict]]:
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    raw = meta.get("sources") or []
    return meta, [x for x in raw if isinstance(x, dict)]


def source_minimum(brief: dict, editorial: dict) -> int:
    configured = (brief.get("source_policy") or {}).get("minimum")
    if isinstance(configured, int) and not isinstance(configured, bool) and configured >= 0:
        return configured
    rules = editorial.get("sources") or {}
    selected = deep_merge(rules.get("default") or {}, {})
    if brief.get("journey") == "breaking":
        selected = deep_merge(selected, rules.get("breaking") or {})
    elif brief.get("length") == "deep":
        selected = deep_merge(selected, rules.get("deep") or {})
    minimum = selected.get("minimum", 0)
    return minimum if isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= 0 else 0


def prose_checker() -> Path | None:
    skills_root = Path(__file__).resolve().parents[2]
    candidate = skills_root / "dasen-writing/scripts/check_prose.py"
    return candidate if candidate.exists() else None


def public_url_error(url: str) -> str | None:
    """Reject credentials, unusual ports and every non-public DNS result."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return "只允许 HTTPS"
        if parsed.username or parsed.password:
            return "URL 不得包含凭证"
        if not parsed.hostname:
            return "URL 缺 hostname"
        if parsed.port not in {None, 443}:
            return "只允许 HTTPS 默认端口 443"
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return "禁止本机/内部域名"
        try:
            literal_host = ipaddress.ip_address(host)
        except ValueError:
            literal_host = None
        if literal_host is not None and not literal_host.is_global:
            return f"禁止非公网地址 {literal_host}"
        public, reason = resolve_public_addresses(host, 443)
        if not public:
            return reason
    except (ValueError, OSError) as exc:
        return f"URL/DNS 无法验证：{exc}"
    return None


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        error = public_url_error(newurl)
        if error:
            raise urllib.error.URLError(f"重定向目标不安全：{error}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_remote(url: str, timeout: int = 8) -> str | None:
    error = public_url_error(url)
    if error:
        return error
    opener = urllib.request.build_opener(PublicRedirectHandler())
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            if 200 <= resp.status < 400:
                return None
            return f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 405}:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-0"})
            try:
                with opener.open(req, timeout=timeout) as resp:
                    return None if 200 <= resp.status < 400 else f"HTTP {resp.status}"
            except Exception as retry_exc:  # noqa: BLE001
                return str(retry_exc)
        return f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def remote_sha256_error(url: str, expected: str, timeout: int = 30) -> str | None:
    error = public_url_error(url)
    if error:
        return error
    opener = urllib.request.build_opener(PublicRedirectHandler())
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"}
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            content = response.read(MAX_REMOTE_ASSET_BYTES + 1)
            if len(content) > MAX_REMOTE_ASSET_BYTES:
                return "远程资产超过 20 MiB 校验上限"
            actual = hashlib.sha256(content).hexdigest()
    except Exception as exc:  # noqa: BLE001
        return str(exc)
    return None if actual == expected else f"SHA-256 不一致：期望 {expected}，实际 {actual}"


def local_asset_error(bundle: Path, target: str) -> str | None:
    raw = Path(target)
    if raw.is_absolute():
        return "不得使用本机绝对路径"
    assets_root = evidence_dir(bundle)
    resolved = (bundle / raw).resolve()
    try:
        resolved.relative_to(assets_root)
    except ValueError:
        return "本地文本资产必须位于内容包审计目录，禁止 ../ 或符号链接逃逸"
    if not resolved.is_file():
        return "文件不存在"
    return None


def repo_asset_error(project_root: Path, asset_root: str, target: str) -> str | None:
    root_path = Path(asset_root)
    raw = Path(target)
    if root_path.is_absolute() or raw.is_absolute():
        return "asset_root 与图片路径必须是仓库根相对路径"
    allowed_root = (project_root / root_path).resolve()
    resolved = (project_root / raw).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        return "图片必须位于 brief assets.root，禁止路径逃逸"
    if not resolved.is_file():
        return "文件不存在"
    return None


def article_asset_error(
    project_root: Path, article_path: Path, asset_root: str, target: str
) -> str | None:
    root_path = Path(asset_root)
    raw = Path(target)
    if root_path.is_absolute() or raw.is_absolute():
        return "asset_root 与正文图片路径必须是相对路径"
    allowed_root = (project_root / root_path).resolve()
    resolved = (article_path.parent / raw).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        return "正文图片解析后必须位于 brief assets.root，禁止路径逃逸"
    if not resolved.is_file():
        return "文件不存在"
    return None


def append_record(path: Path, stage: str, passed: bool, facts: list[str], errors: list[str], warnings: list[str]) -> None:
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "",
        f"## { {'draft': 'Writing', 'render': 'Render', 'publish': 'Platform'}[stage] } Preflight · {now}",
        "",
        f"- 结果：{'PASS' if passed else 'FAIL'}",
    ]
    lines += [f"- {x}" for x in facts]
    if warnings:
        lines += ["", "### Warnings", ""] + [f"- {x}" for x in warnings]
    if errors:
        lines += ["", "### Blockers", ""] + [f"- {x}" for x in errors]
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate one dasen content bundle")
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--stage", choices=["draft", "render", "publish"], default="draft")
    ap.add_argument("--append-record", action="store_true")
    ap.add_argument("--update-status", action="store_true", help="PASS 时写 drafted/ready；delivered 不回退")
    ap.add_argument("--skip-prose", action="store_true")
    ap.add_argument("--skip-remote-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    bundle = Path(args.bundle).expanduser().resolve()
    project_root = next((p for p in [bundle, *bundle.parents] if (p / ".git").exists()), bundle)
    required = {name: bundle / name for name in ("brief.yaml", "sources.md", "article.md", "record.md")}
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        result = {"passed": False, "stage": args.stage, "errors": [f"缺文件：{x}" for x in missing]}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else "\n".join(result["errors"]))
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    try:
        brief = load_yaml(required["brief.yaml"])
        article_text = required["article.md"].read_text(encoding="utf-8")
        article_meta, article_body = split_frontmatter(article_text)
        sources_meta, sources = source_entries(required["sources.md"])
        record_text = required["record.md"].read_text(encoding="utf-8")
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    try:
        brief_schema = int(brief.get("schema_version") or 0)
    except (TypeError, ValueError):
        brief_schema = 0
    if brief_schema != 3:
        errors.append("brief schema 不兼容；旧版请先运行 migrate_config.py")

    if "project_root" in brief:
        errors.append("brief.project_root 已改名为 workspace_root；请先运行 migrate_config.py")
    try:
        project_root = bundle_root(bundle, brief)
        evidence = evidence_dir(bundle, brief)
    except ValueError as exc:
        print(json.dumps({"passed": False, "stage": args.stage, "errors": [str(exc)]}))
        return 2

    for field, values in ALLOWED.items():
        value = brief.get(field)
        if value not in values:
            errors.append(f"brief.{field}={value!r}，允许值：{', '.join(sorted(values))}")
    configuration = str(brief.get("configuration") or "").strip()
    if configuration not in {"standalone", "project"}:
        errors.append("brief.configuration 必须是 standalone 或 project")
    project_reference = str(brief.get("project_file") or "").strip()
    if configuration == "standalone" and (project_reference or brief.get("project")):
        errors.append("standalone brief 不得绑定 project/project_file")
    if configuration == "project" and not project_reference:
        errors.append("project brief 必须绑定 project_file")
    for field in ("id", "platform", "objective", "audience", "deliverable"):
        if not str(brief.get(field) or "").strip():
            errors.append(f"brief.{field} 为空")
    platform_id = str(brief.get("platform") or "")
    if platform_id and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", platform_id):
        errors.append("brief.platform 必须是小写字母或数字开头的平台 ID")
    profile_id = str(brief.get("profile") or "").strip()
    if not STYLE_ID.fullmatch(profile_id):
        errors.append("brief.profile 必须是有效 Style ID")
    style_snapshot = brief.get("style_profile")
    if style_snapshot:
        try:
            validate_style_snapshot(style_snapshot, profile_id)
        except ValueError as exc:
            errors.append(str(exc))
    else:
        warnings.append("历史 brief 未固化 style_profile；继续写作前应解析当前 Style ID")
    brief_visual = brief.get("visual") or {}
    if not isinstance(brief_visual, dict):
        errors.append("brief.visual 必须是对象")
        brief_visual = {}
    visual_roles_present = [role for role in ("body", "cover") if role in brief_visual]
    if not visual_roles_present:
        warnings.append("历史 brief 未固化正文与封面 Visual Style 快照；视觉阶段前应迁移或补齐")
    elif len(visual_roles_present) != 2:
        errors.append("brief.visual 必须同时固化 body 与 cover 两个 Style 快照")
    else:
        selection = brief_visual.get("selection") or {}
        selection_mode = selection.get("mode") if isinstance(selection, dict) else None
        if selection_mode not in {"user", "agent", "default"}:
            errors.append("brief.visual.selection.mode 必须是 user、agent 或 default")
        elif selection_mode == "agent" and not str(selection.get("reason") or "").strip():
            errors.append("agent 自主选择视觉风格必须记录 selection.reason")
        elif selection_mode != "agent" and selection.get("reason") is not None:
            errors.append("brief.visual.selection.reason 只用于 agent 模式")
        selected_from_by_role: dict[str, str] = {}
        for role in ("body", "cover"):
            role_config = brief_visual.get(role) or {}
            if not isinstance(role_config, dict):
                errors.append(f"brief.visual.{role} 必须是对象")
                continue
            style_id = str(role_config.get("style_id") or "").strip()
            try:
                validate_visual_style_snapshot(
                    role_config.get("style"), expected_id=style_id, expected_role=role
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            selected_from_by_role[role] = str((role_config.get("style") or {}).get("selected_from") or "")
            method = str(role_config.get("render_method") or "auto").strip()
            compatible = (role_config.get("style") or {}).get("compatible_methods") or []
            if method != "auto" and method not in VISUAL_METHODS:
                errors.append(f"brief.visual.{role}.render_method 无效：{method}")
            elif method != "auto" and method not in compatible:
                errors.append(f"brief.visual.{role}.render_method 与 Style 不兼容：{method}")
        if selection_mode == "agent" and any(
            selected_from_by_role.get(role) != "brief" for role in ("body", "cover")
        ):
            errors.append("agent 模式必须显式选择 body 与 cover 两个 Visual Style")
        if selection_mode == "user" and not any(
            selected_from_by_role.get(role) == "brief" for role in ("body", "cover")
        ):
            errors.append("user 模式至少需要一个显式 Visual Style")
        cover_reference = ((brief_visual.get("cover") or {}).get("reference"))
        if cover_reference is not None:
            if not isinstance(cover_reference, dict):
                errors.append("brief.visual.cover.reference 必须是来源回执对象")
            else:
                reference_kind = cover_reference.get("kind")
                reference_value = str(cover_reference.get("ref") or "").strip()
                reference_hash = str(cover_reference.get("sha256") or "").strip().lower()
                if reference_kind == "https":
                    parsed = urlparse(reference_value)
                    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                        errors.append("brief.visual.cover.reference HTTPS 来源无效")
                elif reference_kind == "local":
                    raw_reference = Path(reference_value)
                    reference_path = (project_root / raw_reference).resolve()
                    if (
                        raw_reference.is_absolute() or ".." in raw_reference.parts
                        or not reference_path.is_relative_to(project_root) or not reference_path.is_file()
                    ):
                        errors.append("brief.visual.cover.reference 本地来源不存在或越界")
                    elif not re.fullmatch(r"[0-9a-f]{64}", reference_hash):
                        errors.append("brief.visual.cover.reference 缺有效 sha256")
                    elif hashlib.sha256(reference_path.read_bytes()).hexdigest() != reference_hash:
                        errors.append("brief.visual.cover.reference 与 sha256 不一致")
                else:
                    errors.append("brief.visual.cover.reference.kind 必须是 local 或 https")
    control_docs: dict[str, dict] = {}
    for field in ("project_file", "series_file"):
        value = str(brief.get(field) or "").strip()
        if not value:
            continue
        if field == "project_file":
            try:
                _, meta = load_project_reference(value, project_root)
            except ValueError as exc:
                errors.append(f"brief.project_file 无效：{exc}")
                continue
            control_docs[field] = meta
        else:
            path = Path(value)
            if path.is_absolute() or value.startswith("@"):
                errors.append(f"brief.{field} 必须是项目内相对路径")
                continue
            full = (project_root / path).resolve()
            if not full.is_relative_to(project_root) or not full.is_file():
                errors.append(f"brief.{field} 不存在或越界：{value}")
                continue
            meta, _ = split_frontmatter(full.read_text(encoding="utf-8"))
            control_docs[field] = meta
    project_cfg = control_docs.get("project_file") or {}
    project_hard_rules = project_cfg.get("hard_rules") or {}
    resolved_brand = brand_config(project_cfg)
    brief_brand = brand_config(brief)
    if configuration == "standalone" and brief_brand != {"name": None, "aliases": []}:
        errors.append("standalone brief 的内容品牌必须保持未设置")
    if project_cfg and brief_brand != resolved_brand:
        errors.append("brief.brand 与项目配置不一致；品牌不能由单篇覆盖")
    if project_cfg and brief.get("project") != project_cfg.get("project"):
        errors.append("brief.project 与 project.md 不一致")
    if brief.get("journey") == "series":
        if not brief.get("series"):
            errors.append("series journey 缺 brief.series")
        if not brief.get("series_file"):
            errors.append("series journey 缺 brief.series_file")
        if not brief.get("project_file"):
            errors.append("series journey 缺 brief.project_file")
        series_cfg = control_docs.get("series_file") or {}
        if series_cfg and brief.get("series") != series_cfg.get("series"):
            errors.append("brief.series 与 series.md 不一致")
        if series_cfg and brief.get("project") != series_cfg.get("project"):
            errors.append("brief.project 与 series.md 不一致")
    if brief.get("journey") == "breaking" and not brief.get("checked_at"):
        errors.append("breaking journey 缺 brief.checked_at")
    pattern_ref = ""
    if brief.get("method") == "pattern-adapt":
        pattern_ref = ((brief.get("pattern_reference") or {}).get("url") or "").strip()
        if not pattern_ref.startswith(("http://", "https://")):
            errors.append("pattern-adapt 缺有效 pattern_reference.url")

    series_cfg = control_docs.get("series_file") or {}
    editorial = editorial_config(project_cfg, series_cfg)
    configured_min = (brief.get("source_policy") or {}).get("minimum")
    if configured_min is not None and (
        not isinstance(configured_min, int) or isinstance(configured_min, bool) or configured_min < 0
    ):
        errors.append("source_policy.minimum 必须是非负整数")
    minimum = source_minimum(brief, editorial)
    source_urls = {str(src.get("url") or "").strip() for src in sources}
    if pattern_ref and pattern_ref not in source_urls:
        errors.append("pattern_reference.url 未登记到 sources frontmatter")
    try:
        fact_sources = factual_origins(sources, pattern_ref)
    except ValueError as exc:
        errors.append(str(exc))
        fact_sources = []
    if len(fact_sources) < minimum:
        errors.append(f"事实来源 {len(fact_sources)} 条，低于门槛 {minimum} 条（结构参考不计）")
    primary_required = bool((brief.get("source_policy") or {}).get("primary_required"))
    if primary_required and not any(
        str(x.get("type") or "").lower() in {"primary", "official", "first-party"}
        for x in fact_sources
    ):
        errors.append("来源策略要求第一来源，但事实来源中没有 primary/official/first-party")

    source_ids: list[str] = []
    for i, src in enumerate(sources, 1):
        source_id = str(src.get("id") or "").strip()
        if not source_id:
            errors.append(f"来源 #{i} 缺 id")
        else:
            source_ids.append(source_id)
        source_type = str(src.get("type") or "").lower()
        if source_type not in SOURCE_TYPES:
            errors.append(f"来源 {source_id or '#'+str(i)} type 无效")
        if not str(src.get("title") or "").strip():
            errors.append(f"来源 {source_id or '#'+str(i)} 缺 title")
        if str(src.get("confidence") or "").lower() not in CONFIDENCE:
            errors.append(f"来源 {source_id or '#'+str(i)} 缺有效 confidence")
        supports = src.get("supports") or []
        if not isinstance(supports, list) or not any(str(x).strip() for x in supports):
            errors.append(f"来源 {source_id or '#'+str(i)} 缺 supports")
        if not src.get("checked_at"):
            errors.append(f"来源 {source_id or '#'+str(i)} 缺 checked_at")
        locator = str(src.get("url") or src.get("path") or "").strip()
        if not locator:
            errors.append(f"来源 {source_id or '#'+str(i)} 缺 url/path")
        elif src.get("url") and urlparse(locator).scheme not in {"http", "https"}:
            errors.append(f"来源 {source_id} URL scheme 非 http(s)")
        elif src.get("path"):
            local = Path(locator)
            if local.is_absolute():
                errors.append(f"来源 {source_id} 使用本机绝对路径")
            elif not (project_root / local).exists():
                errors.append(f"来源 {source_id} 本地路径不存在：{locator}")
    if len(source_ids) != len(set(source_ids)):
        errors.append("sources 存在重复 id")

    declared_single = bool(sources_meta.get("single_source"))
    actual_single = len(fact_sources) == 1
    if actual_single and not declared_single:
        errors.append("事实仅有一个来源，但 sources.single_source 未设 true")
    if declared_single and not actual_single:
        errors.append("sources.single_source=true 与事实来源数量不一致")
    if declared_single:
        if not re.search(r"单一.{0,6}来源|仅.{0,8}来源|只有一[份个条]来源", visible_text(article_body)):
            errors.append("单一来源状态未在正文显式披露")
        warnings.append("当前为单一来源信息；record 必须保留警告")

    if brief.get("journey") == "breaking":
        body_visible = visible_text(article_body)
        if not re.search(r"确认|官方|实测", body_visible):
            errors.append("breaking 正文缺已确认事实表述")
        if not re.search(r"未知|还不知道|尚未确认|未确认|未公布|没有公布|待确认", body_visible):
            errors.append("breaking 正文缺未知/未确认项")
        checked = str(brief.get("checked_at") or "")
        checked_date = checked[:10]
        if article_meta.get("checked_at") != brief.get("checked_at") and checked_date not in body_visible:
            errors.append("breaking 的 checked_at 未写入 article frontmatter 或正文")

    units = text_units(article_body)
    length = brief.get("length")
    wc = brief.get("word_count") or {}
    low, high = wc.get("min"), wc.get("max")
    if not isinstance(low, int) or isinstance(low, bool) or not isinstance(high, int) or isinstance(high, bool):
        defaults = (editorial.get("word_count") or {}).get(length) or {}
        low, high = defaults.get("min"), defaults.get("max")
    if length == "custom" and (not isinstance(low, int) or not isinstance(high, int)):
        errors.append("custom length 缺 word_count.min/max")
        low, high = None, None
    if isinstance(low, int) and isinstance(high, int) and (low < 0 or high < low):
        errors.append("word_count 必须满足 0 <= min <= max")
        low, high = None, None
    if isinstance(low, int) and units < low:
        errors.append(f"可见文本 {units} 单位，低于 {length} 下限 {low}")
    if isinstance(high, int) and units > high:
        errors.append(f"可见文本 {units} 单位，超过 {length} 上限 {high}")
    facts.append(f"可见文本：{units} 单位（汉字 + 英文单词）")

    title = title_from(article_meta, article_body)
    title_len = text_units(title)
    title_policy = deep_merge(
        deep_merge(
            (editorial.get("title") or {}).get("default") or {},
            (editorial.get("title") or {}).get(str(brief.get("platform") or "")) or {},
        ),
        brief.get("title_policy") or {},
    )
    title_min, title_max = title_policy.get("min"), title_policy.get("max")
    if not title:
        errors.append("文章缺标题")
    elif isinstance(title_min, int) and isinstance(title_max, int) and not title_min <= title_len <= title_max:
        errors.append(f"标题 {title_len} 单位，不在配置范围 {title_min}–{title_max}")
    forbidden_title = [str(value) for value in title_policy.get("forbidden_characters") or [] if str(value)]
    matched_title = [value for value in forbidden_title if value in title]
    if matched_title:
        errors.append("标题含配置禁用字符：" + " ".join(matched_title))
    if project_hard_rules.get("body_h1_forbidden") and re.search(r"^\s*#\s+", article_body, re.M):
        errors.append("project 禁止正文重复 H1；标题只放 frontmatter")

    follow_guide = project_hard_rules.get("follow_guide") or {}
    follow_components: list[str] = []
    if follow_guide.get("required") and args.stage in {"render", "publish"}:
        guide_url = str(follow_guide.get("url") or "").strip()
        guide_hash = str(follow_guide.get("sha256") or "").strip().lower()
        guide_html_hash = str(follow_guide.get("html_sha256") or "").strip().lower()
        guide_marker = str(follow_guide.get("marker") or "").strip()
        guide_text = str(follow_guide.get("text") or "").strip()
        if not guide_url.startswith("https://"):
            errors.append("project follow_guide.url 必须是 HTTPS")
        if not re.fullmatch(r"[0-9a-f]{64}", guide_hash):
            errors.append("project follow_guide.sha256 无效")
        if not re.fullmatch(r"[0-9a-f]{64}", guide_html_hash):
            errors.append("project follow_guide.html_sha256 无效")
        pattern = re.compile(
            r'<section\b[^>]*aria-label=["\']' + re.escape(guide_marker) +
            r'["\'][^>]*>.*?</section>\s*<section\b[^>]*>.*?</section>',
            re.I | re.S,
        ) if guide_marker else None
        matches = list(pattern.finditer(article_body)) if pattern else []
        follow_components = [match.group(0) for match in matches]
        if len(matches) != 1:
            errors.append(f"正文关注指引必须恰好出现 1 次，实际 {len(matches)} 次")
        else:
            component = matches[0].group(0).strip()
            leading = len(article_body) - len(article_body.lstrip())
            if matches[0].start() != leading:
                errors.append("project 固定关注指引必须位于正文最前方")
            actual_html_hash = hashlib.sha256(component.encode("utf-8")).hexdigest()
            if re.fullmatch(r"[0-9a-f]{64}", guide_html_hash) and actual_html_hash != guide_html_hash:
                errors.append("正文关注指引 HTML 与 project follow_guide.html_sha256 不一致")
            normalized_component = re.sub(r"\s+", "", visible_text(component))
            normalized_guide = re.sub(r"\s+", "", guide_text)
            if normalized_guide and normalized_guide not in normalized_component:
                errors.append("正文关注指引缺 project 固定文案")
        if guide_url and article_body.count(guide_url) != 1:
            errors.append("正文关注指引 URL 必须恰好出现 1 次")
        if (
            args.stage == "publish"
            and not args.skip_remote_check
            and guide_url.startswith("https://")
            and re.fullmatch(r"[0-9a-f]{64}", guide_hash)
        ):
            failure = remote_sha256_error(guide_url, guide_hash)
            if failure:
                errors.append(f"关注指引 CDN 完整性失败：{failure}")

    topic_label = str(brief.get("topic_label") or "").strip()
    if project_hard_rules.get("topic_label_required"):
        if not topic_label:
            errors.append("project 要求主题标签，但 brief.topic_label 为空")
        else:
            label_units = text_units(topic_label)
            if not 1 <= label_units <= 12:
                errors.append(f"brief.topic_label {label_units} 单位，不在 1–12")
            if project_hard_rules.get("topic_label_in_title") and normalized_label(topic_label) not in normalized_label(title):
                errors.append(f"文章标题未逐字包含主题标签：{topic_label}")
            facts.append(f"主题标签：{topic_label}")

    unresolved = sorted(set(UNRESOLVED.findall(article_body)))
    if unresolved:
        errors.append(f"正文仍有待补标记：{', '.join(unresolved[:5])}")
    requirements = brief.get("requirements") or {}
    body_lower = visible_text(article_body).lower()
    for phrase in requirements.get("required_phrases") or []:
        phrase = str(phrase).strip()
        if phrase and phrase.lower() not in body_lower:
            errors.append(f"缺 brief.required_phrase：{phrase}")
    for phrase in requirements.get("forbidden_phrases") or []:
        phrase = str(phrase).strip()
        if phrase and phrase.lower() in body_lower:
            errors.append(f"命中 brief.forbidden_phrase：{phrase}")

    placement = brief.get("product_placement") or {}
    if "bitbook" in placement and "enabled" not in placement:
        errors.append("product_placement 使用旧 schema；请先运行迁移器")
        placement = {}
    product_name = str(placement.get("product_name") or "").strip()
    product_names = list(dict.fromkeys(
        [product_name, *[str(value).strip() for value in placement.get("aliases") or []]]
    ))
    product_names = [value for value in product_names if value]
    body_visible = visible_text(article_body)
    has_product = any(value.casefold() in body_visible.casefold() for value in product_names)
    if has_product and not placement.get("enabled"):
        errors.append(f"正文出现产品名 {product_name or product_names[0]}，但 brief 未显式开启产品植入")
    if placement.get("enabled") and not product_name:
        errors.append("product_placement 已开启但 product_name 为空")
    if placement.get("enabled") and units:
        paragraphs = [
            paragraph for paragraph in re.split(r"\n\s*\n", article_body)
            if any(name.casefold() in visible_text(paragraph).casefold() for name in product_names)
        ]
        placement_units = sum(text_units(p) for p in paragraphs)
        ratio = placement_units / units
        try:
            max_ratio = float(placement.get("max_ratio", 0.05))
        except (TypeError, ValueError):
            max_ratio = 0.05
            errors.append("product_placement.max_ratio 无效")
        if not 0 < max_ratio <= 1:
            errors.append("product_placement.max_ratio 必须在 0–100% 之间")
        facts.append(f"{product_name or '产品'} 植入占比：{ratio:.1%}")
        if ratio > max_ratio:
            errors.append(f"产品植入占比 {ratio:.1%}，超过 {max_ratio:.1%}")
        required_facts = [str(x).strip() for x in placement.get("required_facts") or [] if str(x).strip()]
        if has_product and not required_facts:
            errors.append("产品植入缺 required_facts 事实锚点")
        for fact in required_facts:
            if fact.lower() not in article_body.lower():
                errors.append(f"product required_fact 未在正文出现：{fact}")
        nonempty_paragraphs = [p for p in re.split(r"\n\s*\n", article_body) if visible_text(p).strip()]
        if has_product and nonempty_paragraphs and any(
            name.casefold() in visible_text(nonempty_paragraphs[-1]).casefold() for name in product_names
        ):
            errors.append("产品植入不得作为文章最后一段")

    persona = brief.get("author_persona") or {}
    persona_enabled = bool(persona.get("enabled"))
    uses = set(persona.get("uses") or [])
    allowed_uses = {"byline", "first-person", "contact"}
    invalid_uses = sorted(uses - allowed_uses)
    if invalid_uses:
        errors.append(f"author_persona uses 无效：{', '.join(invalid_uses)}")
    brief_channel = brief.get("channel")
    if brief_channel is not None and not isinstance(brief_channel, dict):
        errors.append("brief.channel 必须是对象")
        brief_channel = {}
    selected_channel = brief_channel or channel_config(project_cfg, str(brief.get("platform") or ""))
    default_author = str((selected_channel.get("default_author") if isinstance(selected_channel, dict) else "") or "").strip()
    if default_author and str(article_meta.get("author") or "").strip() != default_author:
        errors.append(f"article.author 必须逐字等于 channel.default_author：{default_author}")
    persona_body = article_body
    for component in follow_components:
        persona_body = persona_body.replace(component, " ")
    persona_visible = visible_text(persona_body)
    persona_name = str(persona.get("name") or "").strip()
    persona_contacts = [str(value).strip() for value in persona.get("contacts") or [] if str(value).strip()]
    has_persona_name = bool(persona_name and persona_name.casefold() in persona_visible.casefold())
    has_contact = any(value.casefold() in persona_visible.casefold() for value in persona_contacts)
    body_byline = bool(persona_name and re.search(
        r"(?:作者|署名|文)\s*[：:]?\s*" + re.escape(persona_name), persona_visible, re.I
    ))
    first_person_pattern = re.compile(
        r"(?:^|[，。！？；：\s])(?:我(?:们|的|在|曾|做|用|认为|发现|测试|会|想|把|给|看|写|说|建议|整理|跑|拿|买|是|有|要|也|就|自己|亲自)|对我来说|在我看来|据我|由我|让我|向我|给我)|\b(?:I|we|my|our)\b",
        re.I,
    )
    has_first_person = bool(first_person_pattern.search(persona_visible))
    if (has_persona_name or has_contact or has_first_person) and not persona_enabled:
        errors.append("正文出现作者身份、联系信息或第一人称，但 brief 未显式开启 author_persona")
    if persona_enabled and not uses:
        errors.append("author_persona 已开启但 uses 为空")
    if body_byline and "byline" not in uses:
        errors.append("正文出现作者署名，但 uses 未开启 byline")
    if has_contact and "contact" not in uses:
        errors.append("正文出现作者联系方式，但 uses 未开启 contact")
    if has_first_person and "first-person" not in uses:
        errors.append("正文使用第一人称，但 author_persona uses 未开启 first-person")
    verified_experiences = [
        str(item).strip() for item in persona.get("verified_experiences") or [] if str(item).strip()
    ]
    if persona_enabled and "first-person" in uses and not verified_experiences:
        errors.append("启用第一人称但 verified_experiences 为空")
    experience_pattern = re.compile(
        r"(?:我|我们)(?:曾|在.{0,20}(?:工作|使用|测试|参与|负责|做过)|用过|测试过|做过|参与过|负责过)|我的经历",
        re.I,
    )
    claims = [
        sentence.strip()
        for sentence in re.split(r"[。！？\n]+", persona_visible)
        if experience_pattern.search(sentence)
    ]
    for claim in claims:
        normalized_claim = normalized_label(claim)
        if not any(
            normalized_label(experience) in normalized_claim
            or normalized_claim in normalized_label(experience)
            for experience in verified_experiences
        ):
            errors.append(f"第一人称经历未在 verified_experiences 留痕：{claim[:40]}")

    image_policy = str(
        brief.get("image_policy")
        or (selected_channel.get("image_policy") if isinstance(selected_channel, dict) else None)
        or "local"
    ).strip()
    if image_policy not in {"local", "stable-cdn", "platform-upload"}:
        errors.append(f"brief.image_policy={image_policy!r}，允许值：local, stable-cdn, platform-upload")
        image_policy = "local"
    asset_root = str(assets_config(brief).get("root") or "").strip()
    for raw in IMAGE.findall(article_body):
        target = raw.strip("<>")
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https"}:
            if image_policy == "platform-upload":
                errors.append(f"platform-upload 策略不允许远程 Markdown 图片：{target}")
            elif parsed.scheme != "https":
                errors.append(f"正文图片必须使用 HTTPS：{target}")
            elif args.stage == "publish" and not args.skip_remote_check:
                failure = check_remote(target)
                if failure:
                    errors.append(f"远程图片不可访问：{target} ({failure})")
        elif parsed.scheme:
            errors.append(f"图片 URL scheme 不安全：{target}")
        else:
            if image_policy == "stable-cdn":
                errors.append(f"stable-cdn 策略不允许本地正文图片：{target}")
            elif not asset_root:
                errors.append("brief assets.root 为空")
            else:
                failure = article_asset_error(project_root, required["article.md"], asset_root, target)
                if failure:
                    errors.append(f"本地正文图片不安全：{target}（{failure}）")

    if not args.skip_prose:
        checker = prose_checker()
        if checker:
            proc = subprocess.run([sys.executable, str(checker), str(required["article.md"])], capture_output=True, text=True)
            if proc.returncode:
                errors.append("check_prose 未通过：" + " | ".join(proc.stdout.splitlines()[-5:]))
            else:
                facts.append("check_prose：PASS")
        else:
            errors.append("找不到 dasen-writing/check_prose.py")

    if args.stage == "publish":
        for field in ("title",):
            if not str(article_meta.get(field) or "").strip():
                errors.append(f"publish 缺 article frontmatter.{field}")
        cover = str(article_meta.get("cover") or "").strip()
        if cover:
            parsed_cover = urlparse(cover)
            if parsed_cover.scheme in {"http", "https"}:
                if image_policy == "platform-upload":
                    errors.append("platform-upload 策略要求 cover 使用 assets.root 内本地图片")
                elif parsed_cover.scheme != "https":
                    errors.append("cover 必须使用 HTTPS")
                elif not args.skip_remote_check:
                    failure = check_remote(cover)
                    if failure:
                        errors.append(f"cover 不可访问：{cover} ({failure})")
            elif parsed_cover.scheme:
                errors.append("cover 使用非 HTTPS scheme")
            elif image_policy == "stable-cdn":
                errors.append("stable-cdn 策略要求 cover 使用 HTTPS URL")
            elif not asset_root:
                errors.append("brief assets.root 为空")
            else:
                failure = article_asset_error(project_root, required["article.md"], asset_root, cover)
                if failure:
                    errors.append(f"本地 cover 不安全：{cover}（{failure}）")
        project_visual = visual_config(brief)
        generation = project_visual.get("generation") or {}
        required_cover_model = str(generation.get("model") or "").strip()
        generation_required = bool(generation.get("required"))
        manifest_path = evidence / "cover.yaml"
        if generation_required or manifest_path.is_file():
            if not manifest_path.is_file():
                errors.append(f"brief 要求生成封面，但缺 {evidence.name}/cover.yaml")
            else:
                try:
                    cover_manifest = load_yaml(manifest_path)
                except ValueError as exc:
                    errors.append(str(exc))
                    cover_manifest = {}
                if required_cover_model and str(cover_manifest.get("model") or "").strip() != required_cover_model:
                    errors.append(f"cover.yaml model 必须是 {required_cover_model}")

                frozen_cover = brief_visual.get("cover") if isinstance(brief_visual, dict) else {}
                frozen_cover = frozen_cover if isinstance(frozen_cover, dict) else {}
                if frozen_cover:
                    expected_style_id = str(frozen_cover.get("style_id") or "").strip()
                    expected_revision = (frozen_cover.get("style") or {}).get("revision")
                    if str(cover_manifest.get("style_id") or "").strip() != expected_style_id:
                        errors.append(f"cover.yaml style_id 必须是 {expected_style_id}")
                    if cover_manifest.get("style_revision") != expected_revision:
                        errors.append(f"cover.yaml style_revision 必须是 {expected_revision}")
                    adapter = str(cover_manifest.get("adapter") or "").strip()
                    if adapter not in VISUAL_METHODS:
                        errors.append("cover.yaml adapter 必须是有效 render method")

                layout_id = str(cover_manifest.get("layout") or cover_manifest.get("template") or "").strip()
                if cover_manifest.get("layout") and cover_manifest.get("template") and cover_manifest.get("layout") != cover_manifest.get("template"):
                    errors.append("cover.yaml layout 与兼容字段 template 不一致")
                template_library = str(project_visual.get("layout_library") or "").strip()
                if not layout_id:
                    errors.append("cover.yaml 缺 layout（构图 ID，手写提示词填 ad-hoc）")
                elif layout_id == "ad-hoc":
                    if not str(cover_manifest.get("layout_reason") or cover_manifest.get("template_reason") or "").strip():
                        errors.append("cover.yaml layout=ad-hoc 时必须填写 layout_reason")
                elif not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", layout_id):
                    errors.append("cover.yaml layout ID 格式无效")
                elif not template_library:
                    errors.append("brief visual 缺 layout_library")
                else:
                    library = Path(template_library)
                    if library.is_absolute():
                        errors.append("visual.layout_library 必须是项目根相对路径")
                    else:
                        library_root = (project_root / library).resolve()
                        template_path = (library_root / f"{layout_id}.md").resolve()
                        try:
                            template_path.relative_to(library_root)
                        except ValueError:
                            errors.append("cover.yaml template 路径逃逸")
                        else:
                            if not template_path.is_file():
                                errors.append(f"cover.yaml layout 不存在：{template_library}/{layout_id}.md")
                            else:
                                try:
                                    template_meta, _ = split_frontmatter(template_path.read_text(encoding="utf-8"))
                                except ValueError as exc:
                                    errors.append(f"封面模板 frontmatter 无效：{exc}")
                                    template_meta = {}
                                if str(template_meta.get("id") or "").strip() != layout_id:
                                    errors.append("封面 layout frontmatter.id 与 cover.yaml layout 不一致")
                                if str(template_meta.get("status") or "").strip() != "verified":
                                    errors.append("封面模板 status 必须是 verified")
                                reference_path = str(template_meta.get("reference_path") or "").strip()
                                reference_url = str(template_meta.get("reference_url") or "").strip()
                                reference_hash = str(template_meta.get("reference_sha256") or "").strip().lower()
                                reference_hash_valid = bool(re.fullmatch(r"[0-9a-f]{64}", reference_hash))
                                if not reference_path:
                                    errors.append("封面模板缺 reference_path")
                                if not reference_url.startswith("https://"):
                                    errors.append("封面模板 reference_url 必须是 HTTPS")
                                if not reference_hash_valid:
                                    errors.append("封面模板 reference_sha256 无效")
                                if reference_path and asset_root and reference_hash_valid:
                                    failure = repo_asset_error(project_root, asset_root, reference_path)
                                    if failure == "文件不存在":
                                        warnings.append("封面模板本地 style reference 缺失；使用 CDN 恢复地址")
                                    elif failure:
                                        errors.append(f"封面模板 reference_path 无效：{failure}")
                                    else:
                                        actual = hashlib.sha256((project_root / reference_path).resolve().read_bytes()).hexdigest()
                                        if actual != reference_hash:
                                            errors.append("封面模板本地 style reference 与 reference_sha256 不一致")
                                if (
                                    reference_url.startswith("https://")
                                    and reference_hash_valid
                                    and not args.skip_remote_check
                                ):
                                    failure = remote_sha256_error(reference_url, reference_hash)
                                    if failure:
                                        errors.append(f"封面模板 CDN 完整性失败：{failure}")

                if normalized_label(cover_manifest.get("topic_label")) != normalized_label(topic_label):
                    errors.append("cover.yaml topic_label 与 brief.topic_label 不一致")
                if str(cover_manifest.get("title") or "").strip() != title:
                    errors.append("cover.yaml title 与文章标题不一致")
                expected_size = project_visual.get("cover_size") or []
                if isinstance(expected_size, list) and len(expected_size) == 2:
                    if [cover_manifest.get("width"), cover_manifest.get("height")] != expected_size:
                        errors.append(f"cover.yaml 尺寸必须是 {expected_size[0]}×{expected_size[1]}")
                for dimension in ("source_width", "source_height"):
                    value = cover_manifest.get(dimension)
                    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                        errors.append(f"cover.yaml 缺有效 {dimension}")

                prompt_path = str(cover_manifest.get("prompt_path") or "").strip()
                if not prompt_path:
                    errors.append("cover.yaml 缺 prompt_path")
                else:
                    failure = local_asset_error(bundle, prompt_path)
                    if failure:
                        errors.append(f"cover.yaml prompt_path 无效：{failure}")

                if not asset_root:
                    errors.append("brief assets.root 为空")
                final_digest = ""
                for path_field, hash_field in (
                    ("source_path", "source_sha256"),
                    ("final_path", "final_sha256"),
                ):
                    target = str(cover_manifest.get(path_field) or "").strip()
                    digest = str(cover_manifest.get(hash_field) or "").strip().lower()
                    digest_valid = bool(re.fullmatch(r"[0-9a-f]{64}", digest))
                    if hash_field == "final_sha256" and digest_valid:
                        final_digest = digest
                    if not target:
                        errors.append(f"cover.yaml 缺 {path_field}")
                    if not digest_valid:
                        errors.append(f"cover.yaml 缺有效 {hash_field}")
                    elif digest not in record_text.lower():
                        errors.append(f"record 缺 {hash_field} 回执")
                    if target and asset_root:
                        failure = repo_asset_error(project_root, asset_root, target)
                        if failure == "文件不存在" and image_policy == "stable-cdn" and digest_valid:
                            warnings.append(f"cover.yaml {path_field} 本地生产图片缺失；使用 manifest/record 哈希留痕")
                        elif failure:
                            errors.append(f"cover.yaml {path_field} 无效：{failure}")
                        elif digest_valid:
                            actual = hashlib.sha256((project_root / target).resolve().read_bytes()).hexdigest()
                            if actual != digest:
                                errors.append(f"cover.yaml {path_field} 与 {hash_field} 不一致")
                if not str(cover_manifest.get("generated_at") or "").strip():
                    errors.append("cover.yaml 缺 generated_at")
                manifest_cdn = str(cover_manifest.get("cdn_url") or "").strip()
                if image_policy == "stable-cdn" and manifest_cdn != cover:
                    errors.append("cover.yaml cdn_url 与 article frontmatter.cover 不一致")
                if (
                    image_policy == "stable-cdn"
                    and manifest_cdn
                    and final_digest
                    and not args.skip_remote_check
                ):
                    failure = remote_sha256_error(manifest_cdn, final_digest)
                    if failure:
                        errors.append(f"cover CDN 完整性失败：{failure}")
                if project_hard_rules.get("topic_label_in_cover") and not topic_label:
                    errors.append("封面要求主题标签，但 brief.topic_label 为空")
                if required_cover_model:
                    facts.append(f"封面模型：{required_cover_model}")

        tags = article_meta.get("tags") or []
        required_tags = (selected_channel.get("required_tags") if isinstance(selected_channel, dict) else []) or []
        if required_tags and not isinstance(tags, list):
            errors.append("article frontmatter.tags 必须是列表")
            tags = []
        for tag in required_tags:
            if tag not in tags:
                errors.append(f"缺频道必带标签：{tag}")

    passed = not errors
    facts += [f"事实来源：{len(fact_sources)} 个原始来源（登记 {len(sources)} 条；门槛 {minimum}）", f"标题：{title_len} 单位"]
    result = {
        "passed": passed,
        "stage": args.stage,
        "bundle": str(bundle),
        "facts": facts,
        "warnings": warnings,
        "errors": errors,
    }
    if args.append_record:
        append_record(required["record.md"], args.stage, passed, facts, errors, warnings)
    if passed and args.update_status and brief.get("status") != "delivered":
        brief["status"] = "drafted" if args.stage == "draft" else "ready"
        brief["blocker"] = None
        brief["resume_from"] = None
        required["brief.yaml"].write_text(
            yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{'PASS' if passed else 'FAIL'} · {args.stage} · {bundle}")
        for x in facts:
            print(f"[ok] {x}")
        for x in warnings:
            print(f"[warn] {x}")
        for x in errors:
            print(f"[error] {x}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
