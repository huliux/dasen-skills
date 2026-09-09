#!/usr/bin/env python3
"""Resolve WeChat credentials from project/device locators without central account state."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))

from project_config import load_project_reference  # noqa: E402


DEFAULT_APP_ID_ENV = "WECHAT_APP_ID"
DEFAULT_APP_SECRET_ENV = "WECHAT_APP_SECRET"
DEVICE_KEYCHAIN_SERVICE_ENV = "DASEN_WECHAT_KEYCHAIN_SERVICE"
DEVICE_APP_ID_ACCOUNT_ENV = "DASEN_WECHAT_APP_ID_ACCOUNT"
DEVICE_APP_SECRET_ACCOUNT_ENV = "DASEN_WECHAT_APP_SECRET_ACCOUNT"
ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{1,127}")


@dataclass(frozen=True)
class CredentialLocator:
    app_id_env: str
    app_secret_env: str
    keychain_service: str | None
    app_id_account: str | None
    app_secret_account: str | None


@dataclass(frozen=True)
class CredentialPair:
    app_id: str
    app_secret: str
    source: str


def credential_locator(project: dict[str, Any], platform_id: str = "wechat") -> CredentialLocator:
    channels = project.get("channels") or {}
    channel = channels.get(platform_id) if isinstance(channels, dict) else {}
    channel = channel if isinstance(channel, dict) else {}
    raw = channel.get("credentials") or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"channels.{platform_id}.credentials 必须是对象")
    forbidden = sorted(
        key for key in ("app_id", "app_secret", "password", "secret", "token")
        if raw.get(key) not in (None, "")
    )
    if forbidden:
        raise RuntimeError(
            f"channels.{platform_id}.credentials 只保存定位，不保存凭证值：{forbidden[0]}"
        )

    app_id_env = str(raw.get("app_id_env") or DEFAULT_APP_ID_ENV).strip()
    app_secret_env = str(raw.get("app_secret_env") or DEFAULT_APP_SECRET_ENV).strip()
    if not ENV_NAME.fullmatch(app_id_env) or not ENV_NAME.fullmatch(app_secret_env):
        raise RuntimeError(f"channels.{platform_id}.credentials 的 env 字段必须是环境变量名")

    project_keychain = (
        str(raw.get("keychain_service") or "").strip(),
        str(raw.get("app_id_account") or "").strip(),
        str(raw.get("app_secret_account") or "").strip(),
    )
    if any(project_keychain) and not all(project_keychain):
        raise RuntimeError(
            f"channels.{platform_id}.credentials 的 Keychain 定位必须完整包含 service 和两个 account"
        )
    if all(project_keychain):
        service, app_id_account, app_secret_account = project_keychain
    else:
        device_keychain = (
            os.environ.get(DEVICE_KEYCHAIN_SERVICE_ENV, "").strip(),
            os.environ.get(DEVICE_APP_ID_ACCOUNT_ENV, "").strip(),
            os.environ.get(DEVICE_APP_SECRET_ACCOUNT_ENV, "").strip(),
        )
        if any(device_keychain) and not all(device_keychain):
            raise RuntimeError("设备环境中的 WeChat Keychain 定位必须完整")
        service, app_id_account, app_secret_account = device_keychain

    return CredentialLocator(
        app_id_env=app_id_env,
        app_secret_env=app_secret_env,
        keychain_service=service or None,
        app_id_account=app_id_account or None,
        app_secret_account=app_secret_account or None,
    )


def read_keychain(service: str, account: str) -> str:
    if platform.system() != "Darwin" or not shutil.which("security"):
        return ""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def write_keychain(service: str, account: str, value: str) -> None:
    if platform.system() != "Darwin" or not shutil.which("security"):
        raise RuntimeError("当前设备不支持 macOS Keychain；请使用完整环境变量对")
    result = subprocess.run(
        ["security", "add-generic-password", "-a", account, "-s", service, "-U", "-w", value],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("写入 macOS Keychain 失败")


def delete_keychain(service: str, account: str) -> None:
    if platform.system() != "Darwin" or not shutil.which("security"):
        return
    subprocess.run(
        ["security", "delete-generic-password", "-a", account, "-s", service],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def load_credentials(project: dict[str, Any], platform_id: str = "wechat") -> CredentialPair:
    locator = credential_locator(project, platform_id)
    app_id = os.environ.get(locator.app_id_env, "").strip()
    app_secret = os.environ.get(locator.app_secret_env, "").strip()
    if bool(app_id) != bool(app_secret):
        raise RuntimeError(
            f"{locator.app_id_env} 与 {locator.app_secret_env} 必须提供完整环境变量对"
        )
    if app_id and app_secret:
        return CredentialPair(app_id, app_secret, "environment")

    if locator.keychain_service:
        candidate_id = read_keychain(locator.keychain_service, str(locator.app_id_account))
        candidate_secret = read_keychain(locator.keychain_service, str(locator.app_secret_account))
        if bool(candidate_id) != bool(candidate_secret):
            raise RuntimeError("项目或设备指定的 WeChat Keychain 来源只有半套凭证")
        if candidate_id and candidate_secret:
            return CredentialPair(candidate_id, candidate_secret, "keychain")

    raise RuntimeError(
        "WeChat 凭证未找到；请提供完整环境变量对，或在项目 channel 或设备环境配置完整 Keychain 定位"
    )


def credential_status(project: dict[str, Any], platform_id: str = "wechat") -> dict[str, str | None]:
    try:
        pair = load_credentials(project, platform_id)
    except RuntimeError as exc:
        return {"status": "unavailable", "source": None, "reason": str(exc)}
    return {"status": "ready", "source": pair.source, "reason": None}


def store_pair(
    project: dict[str, Any],
    app_id: str,
    app_secret: str,
    platform_id: str = "wechat",
    *,
    replace: bool = True,
) -> None:
    locator = credential_locator(project, platform_id)
    if not locator.keychain_service:
        raise RuntimeError("写入 Keychain 前，必须在项目 channel 或设备环境配置完整 Keychain 定位")
    if not app_id.strip() or not app_secret.strip():
        raise RuntimeError("AppID/AppSecret 不能为空")
    service = locator.keychain_service
    id_account = str(locator.app_id_account)
    secret_account = str(locator.app_secret_account)
    new_id, new_secret = app_id.strip(), app_secret.strip()
    previous_id = read_keychain(service, id_account)
    previous_secret = read_keychain(service, secret_account)
    if bool(previous_id) != bool(previous_secret):
        raise RuntimeError("目标 Keychain 定位已经存在半套凭证，拒绝覆盖")
    if previous_id and previous_secret:
        if previous_id == new_id and previous_secret == new_secret:
            return
        if not replace:
            raise RuntimeError("目标 Keychain 定位已有不同凭证，拒绝迁移覆盖")
    try:
        write_keychain(service, id_account, new_id)
        write_keychain(service, secret_account, new_secret)
        if read_keychain(service, id_account) != new_id or read_keychain(service, secret_account) != new_secret:
            raise RuntimeError("Keychain 写入后验证失败")
    except Exception:
        if previous_id and previous_secret:
            write_keychain(service, id_account, previous_id)
            write_keychain(service, secret_account, previous_secret)
        else:
            delete_keychain(service, id_account)
            delete_keychain(service, secret_account)
        raise


def migrate_service_prefix(
    project: dict[str, Any],
    legacy_prefix: str,
    platform_id: str = "wechat",
) -> None:
    prefix = str(legacy_prefix).strip()
    if not prefix or any(char in prefix for char in "\r\n\0"):
        raise RuntimeError("旧 Keychain service prefix 无效")
    account = getpass.getuser()
    app_id = read_keychain(f"{prefix}.appid", account)
    app_secret = read_keychain(f"{prefix}.appsecret", account)
    if bool(app_id) != bool(app_secret):
        raise RuntimeError("旧 Keychain service prefix 只有半套凭证，拒绝迁移")
    if not app_id or not app_secret:
        raise RuntimeError("旧 Keychain service prefix 未找到完整凭证")
    store_pair(project, app_id, app_secret, platform_id, replace=False)


def _load_project(reference: str | None) -> dict[str, Any]:
    if not reference:
        return {}
    _, project = load_project_reference(reference, Path.cwd().resolve())
    return project


def _project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-file", help="Current-workspace-relative project.md path")
    parser.add_argument("--platform", default="wechat", help="Channel ID, defaults to wechat")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect, store or migrate WeChat credentials")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Report availability without printing credential values")
    _project_argument(status)
    store = commands.add_parser("store", help="Store a complete pair at a configured Keychain locator")
    _project_argument(store)
    migrate = commands.add_parser("migrate-prefix", help="Migrate one explicitly named legacy service prefix")
    _project_argument(migrate)
    migrate.add_argument("--legacy-prefix", required=True)
    args = parser.parse_args()

    project = _load_project(args.project_file)
    if args.command == "status":
        print(json.dumps(credential_status(project, args.platform), ensure_ascii=False))
        return 0
    if args.command == "migrate-prefix":
        migrate_service_prefix(project, args.legacy_prefix, args.platform)
        print("PASS: WeChat credential pair migrated and verified; no credential value was printed")
        return 0

    locator = credential_locator(project, args.platform)
    app_id = os.environ.get(locator.app_id_env, "").strip()
    app_secret = os.environ.get(locator.app_secret_env, "").strip()
    if bool(app_id) != bool(app_secret):
        raise RuntimeError(
            f"{locator.app_id_env} 与 {locator.app_secret_env} 必须提供完整环境变量对"
        )
    if not app_id:
        app_id = input("WeChat AppID: ").strip()
        app_secret = getpass.getpass("WeChat AppSecret: ").strip()
    store_pair(project, app_id, app_secret, args.platform)
    print("PASS: WeChat credential pair stored and verified; no credential value was printed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
