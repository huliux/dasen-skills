#!/usr/bin/env python3
"""Shared project configuration resolution for the content Skills."""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EDITORIAL: dict[str, Any] = {
    "word_count": {
        "quick": {"min": 1, "max": 1000},
        "standard": {"min": 1000, "max": 2500},
        "deep": {"min": 3000, "max": 5000},
    },
    "title": {
        "default": {"min": 1, "max": 100, "forbidden_characters": []},
    },
    "sources": {
        "default": {"minimum": 2, "primary_required": False},
        "breaking": {"minimum": 1, "primary_required": True},
        "deep": {"minimum": 5, "primary_required": False},
    },
}


def split_frontmatter(text: str) -> dict[str, Any]:
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError("配置文件缺 YAML frontmatter")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("配置文件 frontmatter 顶层必须是对象")
    return data


def load_project_reference(reference: str, project_root: Path) -> tuple[Path, dict[str, Any]]:
    root = project_root.resolve()
    raw = Path(reference).expanduser()
    if reference.startswith("@") or raw.is_absolute():
        raise ValueError("项目配置只接受当前工作区内的相对路径；不支持 @global 或绝对路径")
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError("项目配置必须位于项目根目录内")
    if not path.is_file():
        raise ValueError(f"项目配置不存在：{reference}")
    config = split_frontmatter(path.read_text(encoding="utf-8"))
    hard_rules = config.get("hard_rules") if isinstance(config.get("hard_rules"), dict) else {}
    legacy = [name for name in (
        "asset_root", "cover_generation_model", "cover_size", "cover_template_library"
    ) if name in hard_rules]
    top_level_legacy = [name for name in ("system_brand", "scope", "channel", "platform") if name in config]
    try:
        schema_version = int(config.get("schema_version") or 0)
    except (TypeError, ValueError):
        schema_version = 0
    if top_level_legacy or legacy or schema_version != 3:
        fields = [*top_level_legacy, *[f"hard_rules.{name}" for name in legacy]]
        raise ValueError(
            "检测到不兼容项目配置（" + ", ".join(fields or ["schema_version"]) + "）；旧版先运行 migrate_config.py"
        )
    for field in (
        "brand", "channels", "authors", "writing", "defaults", "editorial", "assets", "visual", "hard_rules"
    ):
        if field in config and not isinstance(config[field], dict):
            raise ValueError(f"project.{field} 必须是对象")
    project_id = str(config.get("project") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", project_id):
        raise ValueError("project.project 必须是稳定的小写项目 ID")
    for platform_id, channel in (config.get("channels") or {}).items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", str(platform_id)):
            raise ValueError(f"project.channels 包含无效平台 ID：{platform_id}")
        if not isinstance(channel, dict):
            raise ValueError(f"project.channels.{platform_id} 必须是对象")
    authors = config.get("authors") or {}
    profiles = authors.get("profiles") or {}
    if not isinstance(profiles, dict):
        raise ValueError("project.authors.profiles 必须是对象")
    default_author = str(authors.get("default") or "").strip()
    if default_author and default_author not in profiles:
        raise ValueError("project.authors.default 必须指向 authors.profiles 中的 profile")
    invalid_profiles = [
        profile_id for profile_id, profile in profiles.items()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", str(profile_id)) or not isinstance(profile, dict)
    ]
    if invalid_profiles:
        raise ValueError(f"project.authors.profiles 包含无效 profile：{invalid_profiles[0]}")
    return path, config


def default_project_reference(project_root: Path) -> str | None:
    if (project_root / "project.md").is_file():
        return "project.md"
    return None


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def brand_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("brand") or {}
    name = str(raw.get("name") or "").strip() or None
    aliases = [str(value).strip() for value in raw.get("aliases") or [] if str(value).strip()]
    return {"name": name, "aliases": list(dict.fromkeys(aliases))}


def channel_config(config: dict[str, Any], platform: str) -> dict[str, Any]:
    """Return the publishable channel snapshot without credential locators."""
    channels = config.get("channels") or {}
    if not isinstance(channels, dict):
        return {}
    selected = channels.get(platform) or {}
    if not isinstance(selected, dict):
        return {}
    snapshot = deepcopy(selected)
    snapshot.pop("credentials", None)
    return snapshot


def default_channel_config(default_author: str = "") -> dict[str, Any]:
    """Return platform-neutral channel defaults owned by the content contract."""
    return {
        "display_name": "",
        "default_author": default_author,
        "required_tags": [],
        "theme": None,
        "highlight": None,
        "image_policy": "local",
    }


def author_profile(config: dict[str, Any], requested: str | None = None) -> dict[str, Any]:
    """Resolve one reusable author profile; activation still belongs to the brief."""
    authors = config.get("authors") or {}
    if not isinstance(authors, dict):
        return {"profile_id": None, "name": None, "contacts": []}
    profiles = authors.get("profiles") or {}
    if not isinstance(profiles, dict):
        profiles = {}
    profile_id = str(requested or authors.get("default") or "").strip()
    raw = profiles.get(profile_id) if profile_id else {}
    raw = raw if isinstance(raw, dict) else {}
    contacts = [str(value).strip() for value in raw.get("contacts") or [] if str(value).strip()]
    return {
        "profile_id": profile_id or None,
        "name": str(raw.get("name") or "").strip() or None,
        "contacts": list(dict.fromkeys(contacts)),
    }


def assets_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("assets") or {}
    root = str(raw.get("root") or "assets").strip()
    remote = deep_merge(
        {
            "provider": "none",
            "endpoint": None,
            "region": None,
            "bucket": None,
            "public_base_url": None,
            "access_key_env": None,
            "secret_key_env": None,
            "keychain_service": None,
            "access_key_account": None,
            "secret_key_account": None,
        },
        raw.get("remote") or {},
    )
    return {"root": root, "remote": remote}


def writing_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the optional project-local style catalog reference."""
    raw = config.get("writing") or {}
    reference = str(raw.get("style_library") or "").strip() or None
    return {"style_library": reference}


def editorial_config(*configs: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(DEFAULT_EDITORIAL)
    for config in configs:
        result = deep_merge(result, config.get("editorial") or {})
    return result


def visual_config(config: dict[str, Any], *, include_credential_locators: bool = True) -> dict[str, Any]:
    """Normalize the visual project contract and its narrow legacy aliases."""
    raw = config.get("visual") or {}
    legacy_preset = str(raw.get("preset") or "").strip() or None
    legacy_template_library = str(raw.get("template_library") or "").strip() or None
    defaults = deep_merge(
        {
            "body_style": "body-clean-editorial",
            "cover_style": "cover-clean-editorial",
        },
        raw.get("defaults") or {},
    )
    if legacy_preset == "bitbook-editorial" and not raw.get("defaults"):
        defaults.update({
            "body_style": "body-whiteboard-clarity",
            "cover_style": "cover-clean-editorial",
        })
    rendering = deep_merge(
        {"body": "auto", "cover": "auto"},
        raw.get("rendering") or {},
    )
    generation = deep_merge(
        {
            "required": False,
            "provider": "none",
            "model": None,
            "endpoint": None,
            "api_key_env": None,
            "credential_profile": None,
            "options": {},
        },
        raw.get("generation") or {},
    )
    if not include_credential_locators:
        generation.pop("api_key_env", None)
        generation.pop("credential_profile", None)
    result = {
        "style_library": str(raw.get("style_library") or "").strip() or None,
        "defaults": defaults,
        "rendering": rendering,
        "cover_size": raw.get("cover_size"),
        "layout_library": str(raw.get("layout_library") or legacy_template_library or "").strip() or None,
        "generation": generation,
    }
    compatibility: dict[str, Any] = {}
    if legacy_preset:
        compatibility["preset"] = legacy_preset
    if legacy_template_library:
        compatibility["template_library"] = legacy_template_library
    if compatibility:
        result["compatibility"] = compatibility
    return result


def default_project_config(project_id: str) -> dict[str, Any]:
    """Build the one canonical schema-v3 project baseline."""
    return {
        "schema_version": 3,
        "project": project_id,
        "brand": brand_config({}),
        "channels": {},
        "authors": {"default": None, "profiles": {}},
        "writing": writing_config({}),
        "defaults": {"profile": "practical", "language": "zh-CN"},
        "editorial": editorial_config(),
        "assets": assets_config({}),
        "visual": visual_config({}),
        "hard_rules": {
            "product_placement_opt_in": True,
            "author_persona_opt_in": True,
            "publish_requires_human": True,
        },
    }
