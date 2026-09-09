from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import native_publish  # noqa: E402
from native_publish import (  # noqa: E402
    DEFAULT_HIGHLIGHT,
    DEFAULT_THEME,
    append_delivery,
    begin_delivery,
    resolve_pending_delivery,
    transition_delivery,
    verify_rendered,
)
from native_renderer import load_theme, render_markdown  # noqa: E402
from prepare_article import channel_options, load_bundle_config  # noqa: E402


def write_bundle(root: Path, *, project_channel: str, brief_channel: str = "") -> Path:
    (root / ".git").mkdir()
    nested_project_channel = "\n".join("  " + line for line in project_channel.splitlines())
    (root / "project.md").write_text(
        f"---\nschema_version: 3\nproject: example\nchannels:\n  wechat:\n{nested_project_channel}\n---\n",
        encoding="utf-8",
    )
    bundle = root / "writing" / "sample"
    bundle.mkdir(parents=True)
    channel = "channel:\n" + brief_channel + "\n" if brief_channel else "channel: {}\n"
    (bundle / "brief.yaml").write_text(
        "schema_version: 3\nconfiguration: project\nplatform: wechat\nproject: example\nproject_file: project.md\n" + channel,
        encoding="utf-8",
    )
    return bundle


def test_owned_defaults_are_canonical() -> None:
    assert DEFAULT_THEME == "dasen-default"
    assert DEFAULT_HIGHLIGHT == "dasen-light"
    assert load_theme(SKILL_DIR / "themes", DEFAULT_THEME).theme_id == DEFAULT_THEME


def test_bundle_options_follow_brief_project_fallback_order(tmp_path: Path) -> None:
    bundle = write_bundle(
        tmp_path,
        project_channel="  theme: project-theme\n  highlight: project-light",
        brief_channel="  theme: article-theme\n  highlight: article-light",
    )
    _, brief, project = load_bundle_config(bundle)
    assert channel_options(brief, project) == ("article-theme", "article-light")


def test_bundle_options_use_project_when_brief_is_unset(tmp_path: Path) -> None:
    bundle = write_bundle(
        tmp_path,
        project_channel="  theme: dasen-default\n  highlight: dasen-light",
    )
    _, brief, project = load_bundle_config(bundle)
    assert channel_options(brief, project) == ("dasen-default", "dasen-light")


def test_bundle_loader_rejects_global_project_reference(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    bundle = tmp_path / "writing" / "sample"
    bundle.mkdir(parents=True)
    (bundle / "brief.yaml").write_text("project_file: '@global'\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="不支持 @global"):
        load_bundle_config(bundle)


def test_native_render_verification_checks_project_invariants() -> None:
    theme = load_theme(SKILL_DIR / "themes", DEFAULT_THEME)
    rendered = render_markdown("## 小节\n\n正文", theme)
    verify_rendered(rendered, "## 小节\n\n正文", {"hard_rules": {"body_h1_forbidden": True}}, 0)


def test_publish_wrapper_has_no_wenyan_runtime_reference() -> None:
    scripts = [SKILL_DIR / "scripts" / "publish.sh", SKILL_DIR / "scripts" / "native_publish.py"]
    assert all("wenyan" not in path.read_text(encoding="utf-8").lower() for path in scripts)


def test_delivery_receipt_does_not_store_absolute_article_path(tmp_path: Path) -> None:
    record = tmp_path / "record.md"
    article = tmp_path / "article.md"
    append_delivery(record, "FAIL", article, DEFAULT_THEME, detail="test failure")
    receipt = record.read_text(encoding="utf-8")
    assert "`article.md`" in receipt
    assert str(tmp_path) not in receipt


def test_delivery_receipt_redacts_queries_paths_and_multiline_detail(tmp_path: Path) -> None:
    record = tmp_path / "record.md"
    article = tmp_path / "article.md"
    detail = f"failed\nURL https://example.com/image.png?token=secret path {tmp_path}/secret.txt"
    append_delivery(record, "FAIL", article, DEFAULT_THEME, detail=detail)
    receipt = record.read_text(encoding="utf-8")
    assert "token=secret" not in receipt
    assert str(tmp_path) not in receipt
    assert "failed URL https://example.com/image.png" in receipt


def test_delivery_state_blocks_ambiguous_retry_until_reconciled(tmp_path: Path) -> None:
    state_path = tmp_path / "assets" / "delivery.json"
    operation = begin_delivery(
        state_path, "a" * 64, retry_confirmed=False, new_draft=False
    )
    transition_delivery(state_path, operation, "submitting")
    with pytest.raises(RuntimeError, match="may have reached WeChat"):
        begin_delivery(state_path, "a" * 64, retry_confirmed=False, new_draft=False)

    assert resolve_pending_delivery(
        state_path, media_id="MEDIA_ID_123456", abandon=False
    ) == "succeeded"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["status"] == "succeeded"
    assert state["media_id"] == "MEDIA_ID_123456"
    with pytest.raises(RuntimeError, match="already has a successful draft"):
        begin_delivery(state_path, "a" * 64, retry_confirmed=False, new_draft=False)


def test_retry_confirmed_starts_a_new_operation_and_keeps_history(tmp_path: Path) -> None:
    state_path = tmp_path / "assets" / "delivery.json"
    first = begin_delivery(state_path, "a" * 64, retry_confirmed=False, new_draft=False)
    transition_delivery(state_path, first, "uncertain")
    second = begin_delivery(state_path, "a" * 64, retry_confirmed=True, new_draft=False)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert second != first
    assert state["status"] == "preparing"
    assert state["history"][-1]["operation_id"] == first


def test_successful_state_can_finalize_a_missing_receipt_without_new_request(tmp_path: Path) -> None:
    state_path = tmp_path / "assets" / "delivery.json"
    operation = begin_delivery(state_path, "a" * 64, retry_confirmed=False, new_draft=False)
    transition_delivery(state_path, operation, "submitting")
    transition_delivery(state_path, operation, "succeeded", "MEDIA_ID_123456")

    assert resolve_pending_delivery(
        state_path, media_id="MEDIA_ID_123456", abandon=False
    ) == "succeeded"
    with pytest.raises(RuntimeError, match="must match"):
        resolve_pending_delivery(state_path, media_id="OTHER_MEDIA_123", abandon=False)
    with pytest.raises(RuntimeError, match="cannot be abandoned"):
        resolve_pending_delivery(state_path, media_id=None, abandon=True)
