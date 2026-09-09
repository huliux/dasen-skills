from __future__ import annotations

import sys
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import wechat_credentials  # noqa: E402


def project_credentials(**overrides: str | None) -> dict:
    credentials = {
        "app_id_env": "PROJECT_WECHAT_APP_ID",
        "app_secret_env": "PROJECT_WECHAT_APP_SECRET",
        "keychain_service": "example-project.wechat",
        "app_id_account": "app-id",
        "app_secret_account": "app-secret",
    }
    credentials.update(overrides)
    return {"channels": {"wechat": {"credentials": credentials}}}


def clear_device_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "WECHAT_APP_ID",
        "WECHAT_APP_SECRET",
        "PROJECT_WECHAT_APP_ID",
        "PROJECT_WECHAT_APP_SECRET",
        "DASEN_WECHAT_KEYCHAIN_SERVICE",
        "DASEN_WECHAT_APP_ID_ACCOUNT",
        "DASEN_WECHAT_APP_SECRET_ACCOUNT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_complete_project_named_environment_pair_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    monkeypatch.setenv("PROJECT_WECHAT_APP_ID", "env-id")
    monkeypatch.setenv("PROJECT_WECHAT_APP_SECRET", "env-secret")
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: "unused")

    pair = wechat_credentials.load_credentials(project_credentials())

    assert (pair.app_id, pair.app_secret, pair.source) == ("env-id", "env-secret", "environment")


def test_environment_and_keychain_halves_are_never_mixed(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    monkeypatch.setenv("PROJECT_WECHAT_APP_ID", "env-id")
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: "keychain-value")

    with pytest.raises(RuntimeError, match="完整环境变量对"):
        wechat_credentials.load_credentials(project_credentials())


def test_project_keychain_locator_reads_one_complete_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    values = {
        ("example-project.wechat", "app-id"): "stored-id",
        ("example-project.wechat", "app-secret"): "stored-secret",
    }
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: values.get((service, account), ""))

    pair = wechat_credentials.load_credentials(project_credentials())

    assert (pair.app_id, pair.app_secret, pair.source) == ("stored-id", "stored-secret", "keychain")


def test_partial_project_keychain_locator_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    project = project_credentials(app_secret_account=None)

    with pytest.raises(RuntimeError, match="Keychain 定位必须完整"):
        wechat_credentials.load_credentials(project)


def test_no_central_keychain_service_is_used_without_project_or_device_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_device_sources(monkeypatch)
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        wechat_credentials,
        "read_keychain",
        lambda service, account: calls.append((service, account)) or "unexpected",
    )

    with pytest.raises(RuntimeError, match="项目 channel 或设备环境"):
        wechat_credentials.load_credentials({})

    assert calls == []


def test_device_keychain_locator_is_supported_without_project(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    monkeypatch.setenv("DASEN_WECHAT_KEYCHAIN_SERVICE", "device.wechat")
    monkeypatch.setenv("DASEN_WECHAT_APP_ID_ACCOUNT", "device-id")
    monkeypatch.setenv("DASEN_WECHAT_APP_SECRET_ACCOUNT", "device-secret")
    values = {
        ("device.wechat", "device-id"): "stored-id",
        ("device.wechat", "device-secret"): "stored-secret",
    }
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: values.get((service, account), ""))

    pair = wechat_credentials.load_credentials({})

    assert pair.source == "keychain"


def test_project_config_rejects_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    project = project_credentials()
    project["channels"]["wechat"]["credentials"]["app_secret"] = "must-not-live-here"

    with pytest.raises(RuntimeError, match="只保存定位"):
        wechat_credentials.load_credentials(project)


def test_migration_reads_legacy_complete_pair_and_writes_project_locator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_device_sources(monkeypatch)
    values = {
        ("old-prefix.appid", "device-user"): "legacy-id",
        ("old-prefix.appsecret", "device-user"): "legacy-secret",
    }
    writes: list[tuple[str, str, str]] = []
    monkeypatch.setattr(wechat_credentials.getpass, "getuser", lambda: "device-user")
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: values.get((service, account), ""))
    def write(service: str, account: str, value: str) -> None:
        writes.append((service, account, value))
        values[(service, account)] = value

    monkeypatch.setattr(wechat_credentials, "write_keychain", write)

    wechat_credentials.migrate_service_prefix(project_credentials(), "old-prefix")

    assert writes == [
        ("example-project.wechat", "app-id", "legacy-id"),
        ("example-project.wechat", "app-secret", "legacy-secret"),
    ]


def test_migration_never_overwrites_different_target_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_device_sources(monkeypatch)
    values = {
        ("old-prefix.appid", "device-user"): "legacy-id",
        ("old-prefix.appsecret", "device-user"): "legacy-secret",
        ("example-project.wechat", "app-id"): "other-id",
        ("example-project.wechat", "app-secret"): "other-secret",
    }
    writes: list[tuple[str, str, str]] = []
    monkeypatch.setattr(wechat_credentials.getpass, "getuser", lambda: "device-user")
    monkeypatch.setattr(wechat_credentials, "read_keychain", lambda service, account: values.get((service, account), ""))
    monkeypatch.setattr(
        wechat_credentials,
        "write_keychain",
        lambda service, account, value: writes.append((service, account, value)),
    )

    with pytest.raises(RuntimeError, match="拒绝迁移覆盖"):
        wechat_credentials.migrate_service_prefix(project_credentials(), "old-prefix")

    assert writes == []
