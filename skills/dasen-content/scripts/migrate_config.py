#!/usr/bin/env python3
"""One-time migration from legacy content/project schemas to schema v3."""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from visual_styles import load_catalog as load_visual_catalog
from visual_styles import BUILTIN_CATALOG as BUILTIN_VISUAL_CATALOG


FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?", re.S)
LEGACY_THEMES = {
    "bitbook-default": "dasen-default",
    "default": "dasen-default",
    "codex-reset-bear-v1": "dasen-default",
    "mweb-bear-default": "dasen-default",
    "mweb-bear-wenyan": "dasen-default",
    "mweb-indigo": "dasen-default",
    "mweb-indigo-wenyan": "dasen-default",
    "codex-reset-bear-v2": "dasen-default",
    "codex-white-collar": "dasen-default",
}
LEGACY_HIGHLIGHTS = {"bitbook-light": "dasen-light", "atom-one-light": "dasen-light"}
LEGACY_VISUAL_PRESETS = {
    "bitbook-editorial": {
        "body": "body-whiteboard-clarity",
        "cover": "cover-clean-editorial",
    }
}


def parse_document(text: str) -> tuple[dict[str, Any], str | None]:
    match = FRONTMATTER.match(text)
    raw = match.group(1) if match else text
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML top level must be a mapping")
    return data, text[match.end():] if match else None


def serialize_document(data: dict[str, Any], body: str | None) -> str:
    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return f"---\n{dumped}---\n{body or ''}" if body is not None else dumped


def _channel_aliases(data: dict[str, Any]) -> None:
    channel = data.get("channel")
    if not isinstance(channel, dict):
        return
    theme = str(channel.get("theme") or "")
    highlight = str(channel.get("highlight") or "")
    if theme in LEGACY_THEMES:
        channel["theme"] = LEGACY_THEMES[theme]
    if highlight in LEGACY_HIGHLIGHTS:
        channel["highlight"] = LEGACY_HIGHLIGHTS[highlight]


def _visual_defaults(visual: dict[str, Any]) -> None:
    legacy_preset = str(visual.pop("preset", "") or "").strip()
    legacy_styles = LEGACY_VISUAL_PRESETS.get(legacy_preset) or {}
    defaults = visual.get("defaults") if isinstance(visual.get("defaults"), dict) else {}
    defaults.setdefault("body_style", legacy_styles.get("body") or "body-clean-editorial")
    defaults.setdefault("cover_style", legacy_styles.get("cover") or "cover-clean-editorial")
    visual["defaults"] = defaults
    visual.setdefault("style_library", None)
    rendering = visual.get("rendering") if isinstance(visual.get("rendering"), dict) else {}
    rendering.setdefault("body", "auto")
    rendering.setdefault("cover", "auto")
    visual["rendering"] = rendering
    legacy_library = visual.pop("template_library", None)
    if not visual.get("layout_library"):
        visual["layout_library"] = legacy_library


def _freeze_builtin_visual(style_id: str, selected_from: str) -> dict[str, Any]:
    catalog = load_visual_catalog(BUILTIN_VISUAL_CATALOG, origin="builtin")
    style = deepcopy(catalog[style_id])
    style["selected_from"] = selected_from
    return style


def migrate(data: dict[str, Any], *, project_document: bool) -> dict[str, Any]:
    migrated = deepcopy(data)
    legacy_brand = str(migrated.pop("system_brand", "") or "").strip()
    brand = migrated.get("brand") if isinstance(migrated.get("brand"), dict) else {}
    brand["name"] = str(brand.get("name") or legacy_brand or "").strip() or None
    brand.setdefault("aliases", [])
    migrated["brand"] = brand
    _channel_aliases(migrated)

    hard_rules = migrated.get("hard_rules") if isinstance(migrated.get("hard_rules"), dict) else {}
    assets = migrated.get("assets") if isinstance(migrated.get("assets"), dict) else {}
    if not assets.get("root"):
        assets["root"] = hard_rules.pop("asset_root", None) or "assets"
    assets.setdefault("remote", {"provider": "none"})
    migrated["assets"] = assets

    visual = migrated.get("visual") if isinstance(migrated.get("visual"), dict) else {}
    generation = visual.get("generation") if isinstance(visual.get("generation"), dict) else {}
    legacy_model = hard_rules.pop("cover_generation_model", None)
    if legacy_model and not generation.get("model"):
        generation["model"] = legacy_model
        generation.setdefault("provider", "unspecified")
    generation.setdefault("required", bool(legacy_model))
    generation.setdefault("provider", "none")
    generation.setdefault("model", None)
    generation.setdefault("endpoint", None)
    generation.setdefault("api_key_env", None)
    generation.setdefault("credential_profile", None)
    generation.setdefault("options", {})
    visual.setdefault("cover_size", hard_rules.pop("cover_size", None))
    legacy_hard_library = hard_rules.pop("cover_template_library", None)
    if not visual.get("layout_library"):
        visual["layout_library"] = legacy_hard_library
    _visual_defaults(visual)
    visual["generation"] = generation
    migrated["visual"] = visual
    migrated["hard_rules"] = hard_rules

    if project_document:
        scope = str(migrated.pop("scope", "project") or "project").strip()
        if scope == "global":
            raise ValueError("全局配置不再受支持；请先把所需值显式复制到目标项目，再迁移该项目文件")

        legacy_platform = migrated.pop("platform", None)
        if isinstance(legacy_platform, str):
            platform_ids = [legacy_platform] if legacy_platform.strip() else []
        elif isinstance(legacy_platform, list):
            platform_ids = [str(value).strip() for value in legacy_platform if str(value).strip()]
        else:
            platform_ids = []
        legacy_channel = migrated.pop("channel", {})
        legacy_channel = legacy_channel if isinstance(legacy_channel, dict) else {}
        if legacy_channel and not platform_ids:
            platform_ids = ["wechat"]
        channels = migrated.get("channels") if isinstance(migrated.get("channels"), dict) else {}
        legacy_image_policy = None
        defaults = migrated.get("defaults") if isinstance(migrated.get("defaults"), dict) else {}
        if "image_policy" in defaults:
            legacy_image_policy = defaults.pop("image_policy")
        for platform_id in dict.fromkeys(platform_ids):
            selected = channels.get(platform_id) if isinstance(channels.get(platform_id), dict) else {}
            selected = {**deepcopy(legacy_channel), **deepcopy(selected)}
            theme = str(selected.get("theme") or "")
            highlight = str(selected.get("highlight") or "")
            if theme in LEGACY_THEMES:
                selected["theme"] = LEGACY_THEMES[theme]
            if highlight in LEGACY_HIGHLIGHTS:
                selected["highlight"] = LEGACY_HIGHLIGHTS[highlight]
            selected.setdefault(
                "image_policy",
                legacy_image_policy or ("platform-upload" if platform_id == "wechat" else "local"),
            )
            channels[platform_id] = selected
        migrated["channels"] = channels
        migrated["defaults"] = defaults

        legacy_persona = migrated.pop("author_persona", {})
        legacy_persona = legacy_persona if isinstance(legacy_persona, dict) else {}
        authors = migrated.get("authors") if isinstance(migrated.get("authors"), dict) else {}
        profiles = authors.get("profiles") if isinstance(authors.get("profiles"), dict) else {}
        if legacy_persona and "default" not in profiles:
            contacts = legacy_persona.get("contacts") if isinstance(legacy_persona.get("contacts"), list) else []
            profiles["default"] = {
                "name": str(legacy_persona.get("name") or "").strip() or None,
                "contacts": [str(value) for value in contacts if str(value).strip()],
            }
            authors.setdefault("default", "default")
        else:
            authors.setdefault("default", None)
        authors["profiles"] = profiles
        migrated["authors"] = authors
        writing = migrated.get("writing") if isinstance(migrated.get("writing"), dict) else {}
        writing.setdefault("style_library", None)
        migrated["writing"] = writing
        migrated["schema_version"] = 3
        return migrated

    project_file = str(migrated.get("project_file") or "").strip()
    if project_file.startswith("@"):
        raise ValueError("@global brief 不再受支持；请先把配置显式放入目标项目并改写 project_file")
    migrated["configuration"] = "project" if project_file else "standalone"
    if "project_root" in migrated and "workspace_root" not in migrated:
        migrated["workspace_root"] = migrated.pop("project_root")
    placement = migrated.get("product_placement")
    if isinstance(placement, dict) and "bitbook" in placement and "enabled" not in placement:
        legacy = placement.get("bitbook") if isinstance(placement.get("bitbook"), dict) else {}
        migrated["product_placement"] = {
            "enabled": bool(legacy.get("enabled")),
            "product_name": str(brand.get("name") or "bitbook"),
            "aliases": [],
            "mode": legacy.get("mode") or "soft",
            "max_ratio": legacy.get("max_ratio", 0.05),
            "required_facts": legacy.get("required_facts") or [],
        }
    persona = migrated.get("author_persona")
    if isinstance(persona, dict):
        contacts = persona.get("contacts") if isinstance(persona.get("contacts"), list) else []
        for key in ("contact", "email", "wechat"):
            value = str(persona.pop(key, "") or "").strip()
            if value:
                contacts.append(value)
        persona["contacts"] = list(dict.fromkeys(str(item) for item in contacts if str(item)))
        persona.setdefault("profile_id", None)
    if migrated.get("image_policy") == "wenyan-upload":
        migrated["image_policy"] = "platform-upload"
    visual = migrated.get("visual") if isinstance(migrated.get("visual"), dict) else {}
    _visual_defaults(visual)
    generation = visual.get("generation") if isinstance(visual.get("generation"), dict) else {}
    generation.pop("api_key_env", None)
    generation.pop("credential_profile", None)
    generation.setdefault("required", False)
    generation.setdefault("provider", "none")
    generation.setdefault("model", None)
    generation.setdefault("endpoint", None)
    generation.setdefault("options", {})
    visual["generation"] = generation
    if not isinstance(visual.get("body"), dict) or not isinstance(visual.get("cover"), dict):
        body_id = str((visual.get("defaults") or {}).get("body_style") or "body-clean-editorial")
        cover_id = str((visual.get("defaults") or {}).get("cover_style") or "cover-clean-editorial")
        visual["selection"] = {"mode": "default", "reason": None}
        visual["body"] = {
            "style_id": body_id,
            "style": _freeze_builtin_visual(body_id, "fallback"),
            "render_method": str((visual.get("rendering") or {}).get("body") or "auto"),
        }
        visual["cover"] = {
            "style_id": cover_id,
            "style": _freeze_builtin_visual(cover_id, "fallback"),
            "render_method": str((visual.get("rendering") or {}).get("cover") or "auto"),
            "reference": None,
        }
    for field in ("defaults", "rendering", "style_library"):
        visual.pop(field, None)
    migrated["visual"] = visual
    migrated["schema_version"] = 3
    return migrated


def is_published_history(path: Path, data: dict[str, Any]) -> bool:
    if path.name != "brief.yaml":
        return False
    if str(data.get("status") or "").lower() in {"delivered", "published"}:
        return True
    record = path.with_name("record.md")
    if not record.is_file():
        return False
    text = record.read_text(encoding="utf-8")
    return bool(re.search(r"Draft Delivery[\s\S]{0,1000}结果：PASS", text))


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or write a one-time schema-v3 migration")
    parser.add_argument("path", type=Path)
    parser.add_argument("--write", action="store_true", help="Create a .v1.bak file and replace the source")
    args = parser.parse_args()
    path = args.path.expanduser().resolve()
    if not path.is_file():
        print("error: input file does not exist", file=sys.stderr)
        return 2
    try:
        before = path.read_text(encoding="utf-8")
        data, body = parse_document(before)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    project_document = path.name.endswith("project.md") or (
        "id" not in data and any(key in data for key in ("defaults", "hard_rules", "scope"))
    )
    try:
        migrated = migrate(data, project_document=project_document)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    after = serialize_document(migrated, body)
    if after == before:
        print("PASS: already schema v3; no changes")
        return 0
    if is_published_history(path, data):
        print("error: published/delivered history is immutable and was not migrated", file=sys.stderr)
        return 3
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=path.name,
        tofile=f"{path.name} (schema v3)",
    ))
    if not args.write:
        print(diff, end="")
        print("PREVIEW: no files changed")
        return 0
    backup = path.with_name(path.name + ".pre-v3.bak")
    if backup.exists():
        print("error: migration backup already exists; refusing to overwrite it", file=sys.stderr)
        return 3
    atomic_write(backup, before)
    atomic_write(path, after)
    print(f"PASS: migrated {path.name}; backup={backup.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
