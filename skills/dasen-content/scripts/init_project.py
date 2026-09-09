#!/usr/bin/env python3
"""Create one optional project content configuration without storing secrets."""
from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yaml

from project_config import default_channel_config, default_project_config

def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Create a dasen content configuration")
    command.add_argument("--output", help="Override destination; project default is project.md")
    command.add_argument("--project", required=True, help="Stable lowercase project id")
    command.add_argument("--platform", action="append", default=[], help="Configured channel id; repeatable")
    command.add_argument("--brand-name")
    command.add_argument("--brand-alias", action="append", default=[])
    command.add_argument("--language", default="zh-CN")
    command.add_argument("--default-author", default="")
    command.add_argument("--persona-id")
    command.add_argument("--persona-name", default="")
    command.add_argument("--persona-contact", action="append", default=[])
    command.add_argument("--default-profile", default="practical", help="Default writing Style ID")
    command.add_argument("--style-library", help="Optional project-relative writing style catalog")
    command.add_argument("--asset-root", default="assets")
    command.add_argument("--remote-provider", default="none", help="Opaque storage provider id, for example tos or oss")
    command.add_argument("--remote-endpoint")
    command.add_argument("--remote-region")
    command.add_argument("--remote-bucket")
    command.add_argument("--remote-public-base-url")
    command.add_argument("--remote-access-key-env")
    command.add_argument("--remote-secret-key-env")
    command.add_argument("--remote-keychain-service")
    command.add_argument("--remote-access-key-account")
    command.add_argument("--remote-secret-key-account")
    command.add_argument("--visual-provider", default="none")
    command.add_argument("--visual-model")
    command.add_argument("--visual-endpoint")
    command.add_argument("--visual-api-key-env")
    command.add_argument("--visual-credential-profile")
    command.add_argument("--visual-style-library", help="Optional project-relative visual style catalog")
    command.add_argument("--default-body-style", default="body-clean-editorial")
    command.add_argument("--default-cover-style", default="cover-clean-editorial")
    command.add_argument("--body-render-method", choices=("auto", "html-css", "image-model", "manual"), default="auto")
    command.add_argument("--cover-render-method", choices=("auto", "html-css", "image-model", "manual"), default="auto")
    command.add_argument("--layout-library", help="Optional project-relative visual layout catalog")
    command.add_argument("--visual-preset", help=argparse.SUPPRESS)
    command.add_argument("--cover-size", help="WIDTHxHEIGHT")
    command.add_argument("--template-library", help=argparse.SUPPRESS)
    command.add_argument("--visual-required", action="store_true")
    return command


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    args = parser().parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", args.project):
        raise SystemExit("[error] --project 只用小写字母、数字和短横线，长度 2–81")
    brand_name = str(args.brand_name or "").strip() or None
    platforms = list(dict.fromkeys(value.strip() for value in args.platform if value.strip()))
    asset_root = args.asset_root.strip()
    invalid_platforms = [value for value in platforms if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value)]
    if invalid_platforms:
        raise SystemExit("[error] --platform 必须是小写字母或数字开头的平台 ID")
    if args.default_author.strip() and len(platforms) != 1:
        raise SystemExit("[error] --default-author 需要且只允许一个 --platform")
    if args.brand_alias and not brand_name:
        raise SystemExit("[error] --brand-alias 需要 --brand-name")
    if Path(asset_root).is_absolute() or ".." in Path(asset_root).parts:
        raise SystemExit("[error] --asset-root 必须是项目内相对路径")
    remote_values = {
        "endpoint": str(args.remote_endpoint or "").strip() or None,
        "region": str(args.remote_region or "").strip() or None,
        "bucket": str(args.remote_bucket or "").strip() or None,
        "public_base_url": str(args.remote_public_base_url or "").strip() or None,
        "access_key_env": str(args.remote_access_key_env or "").strip() or None,
        "secret_key_env": str(args.remote_secret_key_env or "").strip() or None,
        "keychain_service": str(args.remote_keychain_service or "").strip() or None,
        "access_key_account": str(args.remote_access_key_account or "").strip() or None,
        "secret_key_account": str(args.remote_secret_key_account or "").strip() or None,
    }
    remote_provider = str(args.remote_provider or "none").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", remote_provider):
        raise SystemExit("[error] --remote-provider 必须是小写字母或数字开头的 provider ID")
    if remote_provider != "none":
        common = ("endpoint", "region", "bucket", "public_base_url")
        env_pair = remote_values["access_key_env"] and remote_values["secret_key_env"]
        keychain_triple = (
            remote_values["keychain_service"]
            and remote_values["access_key_account"]
            and remote_values["secret_key_account"]
        )
        if any(not remote_values[field] for field in common) or not (env_pair or keychain_triple):
            raise SystemExit(
                "[error] 远程存储需 endpoint/region/bucket/public-base-url，且需完整 env 变量名对或 Keychain service/account 组"
            )
        for field in ("endpoint", "public_base_url"):
            parsed = urlparse(str(remote_values[field]))
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise SystemExit(f"[error] --remote-{field.replace('_', '-')} 必须是无凭证 HTTPS URL")
        for field in ("access_key_env", "secret_key_env"):
            value = remote_values[field]
            if value and not re.fullmatch(r"[A-Z][A-Z0-9_]{1,127}", str(value)):
                raise SystemExit(f"[error] --remote-{field.replace('_', '-')} 必须是环境变量名，不是密钥值")
    elif any(value for value in remote_values.values()):
        raise SystemExit("[error] 远程存储参数需要非 none 的 --remote-provider")
    cover_size: list[int] | None = None
    if args.cover_size:
        match = re.fullmatch(r"(\d+)x(\d+)", args.cover_size.strip())
        if not match or min(int(match.group(1)), int(match.group(2))) <= 0:
            raise SystemExit("[error] --cover-size 必须是正整数 WIDTHxHEIGHT")
        cover_size = [int(match.group(1)), int(match.group(2))]
    visual_style_library = str(args.visual_style_library or "").strip() or None
    layout_library = str(args.layout_library or args.template_library or "").strip() or None
    if args.layout_library and args.template_library and args.layout_library != args.template_library:
        raise SystemExit("[error] --layout-library 与兼容参数 --template-library 不能指向不同路径")
    for name, reference in (
        ("--visual-style-library", visual_style_library),
        ("--layout-library", layout_library),
    ):
        if reference and (
            reference.startswith("@") or Path(reference).is_absolute() or ".." in Path(reference).parts
        ):
            raise SystemExit(f"[error] {name} 必须是项目内相对路径")
    if args.visual_endpoint and not re.match(r"^https://[^\s]+$", args.visual_endpoint):
        raise SystemExit("[error] --visual-endpoint 必须是 HTTPS URL")
    if args.visual_api_key_env and not re.fullmatch(r"[A-Z][A-Z0-9_]{1,127}", args.visual_api_key_env):
        raise SystemExit("[error] --visual-api-key-env 必须是环境变量名，不是密钥值")
    visual_provider = str(args.visual_provider or "none").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", visual_provider):
        raise SystemExit("[error] --visual-provider 必须是小写字母或数字开头的 provider ID")
    if visual_provider == "none" and any((
        args.visual_model,
        args.visual_endpoint,
        args.visual_api_key_env,
        args.visual_credential_profile,
        args.visual_required,
    )):
        raise SystemExit("[error] 配置生图参数时必须设置非 none 的 --visual-provider")
    body_style = str(args.default_body_style or "body-clean-editorial").strip()
    cover_style = str(args.default_cover_style or "cover-clean-editorial").strip()
    if args.visual_preset:
        if args.visual_preset != "bitbook-editorial":
            raise SystemExit("[error] 兼容参数 --visual-preset 只接受 bitbook-editorial")
        if body_style == "body-clean-editorial":
            body_style = "body-whiteboard-clarity"
    for name, style_id in (("--default-body-style", body_style), ("--default-cover-style", cover_style)):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", style_id):
            raise SystemExit(f"[error] {name} 必须是有效 Visual Style ID")

    raw_destination = Path(args.output).expanduser() if args.output else Path("project.md")
    project_root = Path.cwd().resolve()
    if raw_destination.is_absolute():
        raise SystemExit("[error] --output 必须是当前工作区内相对路径")
    destination = (project_root / raw_destination).resolve()
    if not destination.is_relative_to(project_root):
        raise SystemExit("[error] --output 必须位于当前工作区内")
    if destination.exists():
        raise SystemExit(f"[error] 配置已存在，拒绝覆盖：{destination}")

    persona_name = args.persona_name.strip() or None
    persona_contacts = list(dict.fromkeys(value.strip() for value in args.persona_contact if value.strip()))
    persona_id = str(args.persona_id or ("default" if persona_name or persona_contacts else "")).strip() or None
    if persona_id and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", persona_id):
        raise SystemExit("[error] --persona-id 必须是小写字母或数字开头的稳定 ID")
    default_profile = str(args.default_profile or "practical").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", default_profile):
        raise SystemExit("[error] --default-profile 必须是有效 Style ID")
    style_library = str(args.style_library or "").strip() or None
    if style_library and (
        style_library.startswith("@")
        or Path(style_library).is_absolute()
        or ".." in Path(style_library).parts
    ):
        raise SystemExit("[error] --style-library 必须是项目内相对路径")
    channels = {
        platform: default_channel_config(args.default_author.strip())
        for platform in platforms
    }
    profiles = ({persona_id: {"name": persona_name, "contacts": persona_contacts}} if persona_id else {})

    config = default_project_config(args.project)
    config["brand"] = {
        "name": brand_name,
        "aliases": list(dict.fromkeys(value.strip() for value in args.brand_alias if value.strip())),
    }
    config["channels"] = channels
    config["authors"] = {"default": persona_id, "profiles": profiles}
    config["writing"] = {"style_library": style_library}
    config["defaults"]["profile"] = default_profile
    config["defaults"]["language"] = args.language.strip() or "zh-CN"
    config["assets"] = {"root": asset_root, "remote": {"provider": remote_provider, **remote_values}}
    config["visual"] = {
        "style_library": visual_style_library,
        "defaults": {"body_style": body_style, "cover_style": cover_style},
        "rendering": {"body": args.body_render_method, "cover": args.cover_render_method},
        "cover_size": cover_size,
        "layout_library": layout_library,
        "generation": {
            "required": args.visual_required,
            "provider": visual_provider,
            "model": args.visual_model,
            "endpoint": args.visual_endpoint,
            "api_key_env": args.visual_api_key_env,
            "credential_profile": args.visual_credential_profile,
            "options": {},
        },
    }
    body = (
        "# Project\n\n"
        "## 使命与读者\n\n项目为什么存在、服务谁、读者完成什么任务。\n\n"
        "## 内容承诺\n\n稳定兑现的价值；系列和单篇约束分别写入 series/brief。\n"
    )
    text = "---\n" + yaml.safe_dump(config, allow_unicode=True, sort_keys=False) + "---\n\n" + body
    atomic_write(destination, text)
    print(yaml.safe_dump({"status": "created", "configuration": "project", "path": str(destination)}, allow_unicode=True).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
