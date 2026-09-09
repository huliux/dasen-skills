#!/usr/bin/env python3
"""Create one dasen content bundle without overwriting existing work."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:  # pragma: no cover - user-facing dependency error
    print("[error] PyYAML 未安装：python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

from project_config import (
    assets_config,
    author_profile,
    brand_config,
    channel_config,
    deep_merge,
    default_project_reference,
    editorial_config,
    load_project_reference,
    visual_config,
)
from style_profiles import resolve_style
from visual_styles import METHODS as VISUAL_METHODS
from visual_styles import resolve_visual_style

ALLOWED = {
    "journey": {"series", "breaking", "material"},
    "length": {"quick", "standard", "deep", "custom"},
    "method": {"original", "pattern-adapt", "revise"},
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create writing/YYYY-MM-DD/<slug>/ content bundle")
    p.add_argument("--id", required=True, help="YYYY-MM-DD-topic-slug")
    p.add_argument("--journey", required=True, choices=sorted(ALLOWED["journey"]))
    p.add_argument("--length", required=True, choices=sorted(ALLOWED["length"]))
    p.add_argument("--method", required=True, choices=sorted(ALLOWED["method"]))
    p.add_argument("--platform", default="generic", help="Opaque target format/platform id")
    p.add_argument("--objective", required=True)
    p.add_argument("--audience", required=True)
    p.add_argument("--deliverable", required=True)
    p.add_argument("--topic-label", help="One primary topic label; required when project.md enables topic_label_required")
    p.add_argument("--project-file", help="project-relative config; auto-detected when omitted")
    p.add_argument("--series")
    p.add_argument("--series-file", help="series.md path; defaults are compiled into brief")
    p.add_argument("--profile", help="Writing Style ID; built-in or project-local")
    p.add_argument("--body-style", help="Body Visual Style ID; built-in or project-local")
    p.add_argument("--cover-style", help="Cover Visual Style ID; built-in or project-local")
    p.add_argument("--visual-selection-mode", choices=("user", "agent", "default"))
    p.add_argument("--visual-selection-reason", help="Required when an autonomous agent selects styles")
    p.add_argument("--body-render-method", choices=("auto", *sorted(VISUAL_METHODS)))
    p.add_argument("--cover-render-method", choices=("auto", *sorted(VISUAL_METHODS)))
    p.add_argument("--cover-reference", help="HTTPS URL or existing project-relative reference image")
    p.add_argument("--image-policy", choices=["local", "stable-cdn", "platform-upload"])
    p.add_argument("--response-stage", choices=["alert", "take", "demo", "deep"])
    p.add_argument("--deadline")
    p.add_argument("--checked-at")
    p.add_argument("--pattern-url")
    p.add_argument("--product-placement", action="store_true")
    p.add_argument("--product-name")
    p.add_argument("--product-alias", action="append", default=[])
    p.add_argument("--product-fact", action="append", default=[], help="Exact verified phrase used by product placement; repeatable")
    p.add_argument("--author-persona", default="", help="Comma list: byline,first-person,contact")
    p.add_argument("--persona-id", help="Project authors.profiles id")
    p.add_argument("--persona-name")
    p.add_argument("--persona-contact", action="append", default=[])
    p.add_argument("--verified-experience", action="append", default=[], help="Verified first-person experience; repeatable")
    p.add_argument("--word-min", type=int)
    p.add_argument("--word-max", type=int)
    p.add_argument("--title-min", type=int)
    p.add_argument("--title-max", type=int)
    p.add_argument("--title-forbid", action="append", default=[])
    p.add_argument("--source-minimum", type=int)
    p.add_argument("--primary-required", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--root", default="writing")
    return p


def parse_id(value: str) -> tuple[str, str]:
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]{1,80})", value)
    if not m:
        raise ValueError("--id 必须是 YYYY-MM-DD-topic-slug，slug 只用小写字母/数字/短横线")
    dt.date.fromisoformat(m.group(1))
    return m.group(1), m.group(2)


def load_md_frontmatter(value: str | None, project_root: Path) -> dict:
    if not value:
        return {}
    raw = Path(value).expanduser()
    if raw.is_absolute():
        raise ValueError(f"控制文档请使用项目相对路径：{value}")
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise ValueError(f"控制文档必须位于项目根目录内：{value}")
    if not path.is_file():
        raise ValueError(f"控制文档不存在：{value}")
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError(f"控制文档缺 YAML frontmatter：{value}")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"控制文档 frontmatter 顶层必须是对象：{value}")
    return data


def freeze_cover_reference(value: str | None, project_root: Path) -> dict | None:
    reference = str(value or "").strip()
    if not reference:
        return None
    parsed = urlsplit(reference)
    if parsed.scheme:
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("--cover-reference URL 必须是无凭证 HTTPS")
        return {"kind": "https", "ref": reference, "sha256": None}
    raw = Path(reference).expanduser()
    root = project_root.resolve()
    path = (root / raw).resolve()
    if raw.is_absolute() or ".." in raw.parts or not path.is_relative_to(root) or not path.is_file():
        raise ValueError("--cover-reference 必须是项目内已存在的相对路径")
    return {
        "kind": "local",
        "ref": reference,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    args = parser().parse_args()
    project_root = Path.cwd().resolve()
    try:
        date_str, slug = parse_id(args.id)
        project_ref = args.project_file or default_project_reference(project_root)
        project_cfg = {}
        if project_ref:
            _, project_cfg = load_project_reference(project_ref, project_root)
        series_cfg = load_md_frontmatter(args.series_file, project_root)
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    series_name = args.series or series_cfg.get("series")
    if args.journey == "series" and not series_name:
        print("[error] series journey 必须提供 --series 或 --series-file", file=sys.stderr)
        return 2
    if args.journey == "series" and (not project_ref or not args.series_file):
        print("[error] series journey 必须绑定 project.md 和 series 控制文档", file=sys.stderr)
        return 2
    if project_cfg and series_cfg and series_cfg.get("project") != project_cfg.get("project"):
        print("[error] series.md 的 project 与 project.md 不一致", file=sys.stderr)
        return 2
    if args.series and series_cfg and args.series != series_cfg.get("series"):
        print("[error] --series 与 series.md 的 series 不一致", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", args.platform):
        print("[error] --platform 必须是小写字母或数字开头的平台 ID", file=sys.stderr)
        return 2
    project_hard_rules = project_cfg.get("hard_rules") or {}
    topic_label = str(args.topic_label or "").strip()
    if project_hard_rules.get("topic_label_required") and not topic_label:
        print("[error] project.md 要求主题标签，必须提供 --topic-label", file=sys.stderr)
        return 2
    if args.journey == "breaking" and not args.checked_at:
        print("[error] breaking journey 必须提供 --checked-at", file=sys.stderr)
        return 2
    if args.method == "pattern-adapt" and not args.pattern_url:
        print("[error] pattern-adapt 必须提供 --pattern-url", file=sys.stderr)
        return 2
    if args.pattern_url and not args.pattern_url.startswith("https://"):
        print("[error] --pattern-url 必须使用 HTTPS", file=sys.stderr)
        return 2
    if (args.word_min is None) != (args.word_max is None):
        print("[error] --word-min/--word-max 必须成对提供", file=sys.stderr)
        return 2
    if args.length == "custom" and (args.word_min is None or args.word_max is None):
        print("[error] custom length 必须提供 --word-min/--word-max", file=sys.stderr)
        return 2
    if args.word_min is not None and args.word_max is not None and args.word_min > args.word_max:
        print("[error] --word-min 不能大于 --word-max", file=sys.stderr)
        return 2
    if (args.title_min is None) != (args.title_max is None):
        print("[error] --title-min/--title-max 必须成对提供", file=sys.stderr)
        return 2
    if args.title_min is not None and args.title_max is not None and args.title_min > args.title_max:
        print("[error] --title-min 不能大于 --title-max", file=sys.stderr)
        return 2
    if args.source_minimum is not None and args.source_minimum < 0:
        print("[error] --source-minimum 不能小于 0", file=sys.stderr)
        return 2

    output_root = Path(args.root).expanduser()
    if output_root.is_absolute():
        print("[error] --root 必须是项目根相对路径", file=sys.stderr)
        return 2
    output_root = (project_root / output_root).resolve()
    if not output_root.is_relative_to(project_root):
        print("[error] --root 必须位于项目根目录内", file=sys.stderr)
        return 2

    skill_dir = Path(__file__).resolve().parent.parent
    templates = skill_dir / "templates"
    bundle = output_root / date_str / slug
    if bundle.exists():
        print(f"[error] 内容包已存在，拒绝覆盖：{bundle}", file=sys.stderr)
        return 3

    selected_channel = channel_config(project_cfg, args.platform)
    editorial = editorial_config(project_cfg, series_cfg)
    try:
        style_profile = resolve_style(
            requested=args.profile,
            project_config=project_cfg,
            series_config=series_cfg,
            project_root=project_root,
            journey=args.journey,
        )
        body_style = resolve_visual_style(
            role="body",
            requested=args.body_style,
            project_config=project_cfg,
            series_config=series_cfg,
            project_root=project_root,
        )
        cover_style = resolve_visual_style(
            role="cover",
            requested=args.cover_style,
            project_config=project_cfg,
            series_config=series_cfg,
            project_root=project_root,
        )
        cover_reference = freeze_cover_reference(args.cover_reference, project_root)
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    profile = style_profile["id"]
    visual_base = visual_config(project_cfg, include_credential_locators=False)
    project_rendering = visual_base.get("rendering") or {}
    series_visual = series_cfg.get("visual") or {}
    series_rendering = series_visual.get("rendering") if isinstance(series_visual, dict) else {}
    series_rendering = series_rendering if isinstance(series_rendering, dict) else {}
    body_render_method = str(
        args.body_render_method or series_rendering.get("body") or project_rendering.get("body") or "auto"
    )
    cover_render_method = str(
        args.cover_render_method or series_rendering.get("cover") or project_rendering.get("cover") or "auto"
    )
    for role, method, selected in (
        ("body", body_render_method, body_style),
        ("cover", cover_render_method, cover_style),
    ):
        if method != "auto" and method not in selected["compatible_methods"]:
            print(
                f"[error] {role} render method {method} 与 Visual Style ID {selected['id']} 不兼容",
                file=sys.stderr,
            )
            return 2
    explicit_visual_style = bool(args.body_style or args.cover_style)
    selection_mode = args.visual_selection_mode or ("user" if explicit_visual_style else "default")
    selection_reason = str(args.visual_selection_reason or "").strip() or None
    if selection_mode == "agent" and not selection_reason:
        print("[error] agent 自主选择视觉风格必须提供 --visual-selection-reason", file=sys.stderr)
        return 2
    if selection_mode == "agent" and not (args.body_style and args.cover_style):
        print("[error] agent 自主选择必须显式提供 --body-style 与 --cover-style", file=sys.stderr)
        return 2
    if selection_mode == "user" and not explicit_visual_style:
        print("[error] user 选择模式必须显式提供 --body-style 或 --cover-style", file=sys.stderr)
        return 2
    if selection_mode == "default" and explicit_visual_style:
        print("[error] default 选择模式不能同时传入 --body-style/--cover-style", file=sys.stderr)
        return 2
    if selection_mode != "agent" and selection_reason:
        print("[error] --visual-selection-reason 只用于 agent 选择模式", file=sys.stderr)
        return 2
    image_policy = (
        args.image_policy
        or selected_channel.get("image_policy")
        or "local"
    )

    brief = yaml.safe_load((templates / "brief-template.yaml").read_text(encoding="utf-8"))
    brief.update({
        "id": args.id,
        "journey": args.journey,
        "length": args.length,
        "method": args.method,
        "configuration": "project" if project_ref else "standalone",
        "platform": args.platform,
        "project": project_cfg.get("project"),
        "project_file": project_ref,
        "workspace_root": os.path.relpath(project_root, bundle),
        "series": series_name,
        "series_file": args.series_file,
        "profile": profile,
        "style_profile": style_profile,
        "image_policy": image_policy,
        "response_stage": args.response_stage or ("alert" if args.journey == "breaking" else None),
        "objective": args.objective,
        "audience": args.audience,
        "deliverable": args.deliverable,
        "topic_label": topic_label or None,
        "deadline": args.deadline,
        "checked_at": args.checked_at,
    })
    brief["brand"] = brand_config(project_cfg)
    brief["assets"] = assets_config(project_cfg)
    brief["visual"] = {
        "selection": {"mode": selection_mode, "reason": selection_reason},
        "body": {
            "style_id": body_style["id"],
            "style": body_style,
            "render_method": body_render_method,
        },
        "cover": {
            "style_id": cover_style["id"],
            "style": cover_style,
            "render_method": cover_render_method,
            "reference": cover_reference,
        },
        "cover_size": visual_base.get("cover_size"),
        "layout_library": visual_base.get("layout_library"),
        "generation": visual_base.get("generation") or {},
    }
    if visual_base.get("compatibility"):
        brief["visual"]["compatibility"] = visual_base["compatibility"]
    if selected_channel:
        brief["channel"] = selected_channel
    source_rules = editorial.get("sources") or {}
    source_policy = deep_merge(source_rules.get("default") or {}, {})
    if args.journey == "breaking":
        source_policy = deep_merge(source_policy, source_rules.get("breaking") or {})
    elif args.length == "deep":
        source_policy = deep_merge(source_policy, source_rules.get("deep") or {})
    brief["source_policy"].update(source_policy)
    if args.source_minimum is not None:
        brief["source_policy"]["minimum"] = args.source_minimum
    if args.primary_required is not None:
        brief["source_policy"]["primary_required"] = args.primary_required
    title_rules = editorial.get("title") or {}
    brief["title_policy"] = deep_merge(
        title_rules.get("default") or {}, title_rules.get(args.platform) or {}
    )
    if args.title_min is not None and args.title_max is not None:
        brief["title_policy"].update({"min": args.title_min, "max": args.title_max})
    if args.title_forbid:
        brief["title_policy"]["forbidden_characters"] = list(dict.fromkeys(args.title_forbid))
    if args.word_min is not None and args.word_max is not None:
        brief["word_count"].update({"min": args.word_min, "max": args.word_max})
    else:
        brief["word_count"].update((editorial.get("word_count") or {}).get(args.length) or {})
    if args.method == "pattern-adapt":
        brief["pattern_reference"]["url"] = args.pattern_url
    if args.product_placement:
        product_name = str(args.product_name or "").strip()
        if not product_name:
            print("[error] 启用产品植入必须显式提供 --product-name", file=sys.stderr)
            return 2
        brief["product_placement"].update({
            "enabled": True,
            "product_name": product_name,
            "aliases": [x.strip() for x in args.product_alias if x.strip()],
            "required_facts": [x.strip() for x in args.product_fact if x.strip()],
        })
    persona_uses = [x.strip() for x in args.author_persona.split(",") if x.strip()]
    if persona_uses:
        allowed_uses = {"byline", "first-person", "contact"}
        invalid = sorted(set(persona_uses) - allowed_uses)
        if invalid:
            print(f"[error] 不支持的 --author-persona 值：{', '.join(invalid)}", file=sys.stderr)
            return 2
        experiences = [x.strip() for x in args.verified_experience if x.strip()]
        if "first-person" in persona_uses and not experiences:
            print("[error] first-person 人设必须提供 --verified-experience", file=sys.stderr)
            return 2
        project_persona = author_profile(project_cfg, args.persona_id)
        persona_name = str(args.persona_name or project_persona.get("name") or "").strip()
        contacts = [x.strip() for x in args.persona_contact if x.strip()] or [
            str(x).strip() for x in project_persona.get("contacts") or [] if str(x).strip()
        ]
        if "byline" in persona_uses and not persona_name:
            print("[error] byline 人设必须配置 --persona-name 或 project authors profile name", file=sys.stderr)
            return 2
        if "contact" in persona_uses and not contacts:
            print("[error] contact 人设必须配置 --persona-contact 或 project authors profile contacts", file=sys.stderr)
            return 2
        brief["author_persona"].update({
            "enabled": True,
            "profile_id": project_persona.get("profile_id"),
            "name": persona_name or None,
            "contacts": contacts,
            "uses": persona_uses,
            "verified_experiences": experiences,
        })

    try:
        bundle.mkdir(parents=True)
        (bundle / "assets").mkdir()
        (bundle / "brief.yaml").write_text(
            yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        sources_text = (templates / "sources-template.md").read_text(encoding="utf-8").replace(
            "YYYY-MM-DD-topic-slug", args.id
        ).replace("YYYY-MM-DDTHH:MM:SS+08:00", now)
        (bundle / "sources.md").write_text(sources_text, encoding="utf-8")

        placement = brief["product_placement"]
        persona = brief["author_persona"]
        record_text = (templates / "record-template.md").read_text(encoding="utf-8")
        replacements = {
            "{{CONTENT_ID}}": args.id,
            "{{NOW}}": now,
            "{{JOURNEY}}": args.journey,
            "{{LENGTH}}": args.length,
            "{{METHOD}}": args.method,
            "{{PROFILE}}": str(profile),
            "{{BODY_STYLE}}": str(body_style["id"]),
            "{{COVER_STYLE}}": str(cover_style["id"]),
            "{{VISUAL_SELECTION}}": selection_mode,
            "{{PRODUCT_PLACEMENT}}": (
                f"开启（{placement.get('mode', 'soft')}，上限 {float(placement.get('max_ratio', 0.05)):.0%}）"
                if placement.get("enabled") else "关闭"
            ),
            "{{AUTHOR_PERSONA}}": (
                "开启（" + ", ".join(persona.get("uses") or []) + "）"
                if persona.get("enabled") else "关闭"
            ),
        }
        for key, value in replacements.items():
            record_text = record_text.replace(key, value)
        (bundle / "record.md").write_text(record_text, encoding="utf-8")

        channel = brief.get("channel") or {}
        article_meta = {
            "title": "",
            "author": channel.get("default_author") or "",
            "digest": "",
            "cover": "",
            "tags": channel.get("required_tags") or [],
        }
        if args.journey == "breaking":
            article_meta["checked_at"] = args.checked_at
        (bundle / "article.md").write_text(
            "---\n" + yaml.safe_dump(article_meta, allow_unicode=True, sort_keys=False)
            + f"---\n\n# {slug}\n\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(bundle, ignore_errors=True)
        raise

    print(yaml.safe_dump({
        "status": "created",
        "bundle": str(bundle),
        "brief": str(bundle / "brief.yaml"),
        "next": "dasen-research",
    }, allow_unicode=True, sort_keys=False).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
