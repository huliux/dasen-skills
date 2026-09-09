from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tos_upload import parse_tos_config, read_credentials  # noqa: E402


def project_config() -> dict:
    return {
        "schema_version": 3,
        "project": "example",
        "channels": {},
        "assets": {
            "root": "assets",
            "remote": {
                "provider": "tos",
                "endpoint": "https://example-bucket.tos.example.test",
                "region": "example-region",
                "bucket": "example-bucket",
                "public_base_url": "https://assets.example.test/content",
                "access_key_env": "TEST_TOS_ACCESS",
                "secret_key_env": "TEST_TOS_SECRET",
                "keychain_service": "example-tos",
                "access_key_account": "example-access",
                "secret_key_account": "example-secret",
            },
        }
    }


def write_project(root: Path) -> None:
    text = "---\n" + yaml.safe_dump(project_config(), sort_keys=False) + "---\n"
    (root / "project.md").write_text(text, encoding="utf-8")


def test_tos_dry_run_uses_config_and_has_no_credentials_or_network(tmp_path: Path) -> None:
    write_project(tmp_path)
    source = tmp_path / "assets" / "article"
    source.mkdir(parents=True)
    (source / "image.png").write_bytes(b"not-read-by-dry-run")
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEST_TOS_")}
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "tos_upload.py"),
            "assets/article",
            "2026/article",
            "--project-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "DRY-RUN" in result.stdout
    assert "example-bucket" in result.stdout
    assert "no credentials or network used" in result.stdout


def test_tos_source_directory_cannot_escape_asset_root(tmp_path: Path) -> None:
    write_project(tmp_path)
    (tmp_path / "outside").mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "tos_upload.py"),
            "outside",
            "2026/article",
            "--project-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "inside assets.root" in result.stderr


def test_tos_credentials_never_mix_a_partial_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = parse_tos_config(project_config())
    monkeypatch.setenv("TEST_TOS_ACCESS", "access-only")
    monkeypatch.delenv("TEST_TOS_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="half a credential pair"):
        read_credentials(config)


def test_tos_config_has_no_repository_specific_service_defaults() -> None:
    source = (SCRIPTS / "tos_upload.py").read_text(encoding="utf-8")
    assert "gzh-image" not in source
    assert "cn-" + "beijing" not in source
    assert "bitbook-tos" not in source
    assert "DASEN_TOS_" not in source
