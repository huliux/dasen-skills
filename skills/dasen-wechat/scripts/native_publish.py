#!/usr/bin/env python3
"""Preflight, render and save a dasen article to the WeChat draft box."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))

from content_paths import evidence_dir
from project_config import assets_config  # noqa: E402

from native_renderer import load_article_text, load_theme, render_markdown
from prepare_article import channel_options, load_bundle_config, replace_headings
from wechat_api import WechatApiError, WechatClient
from wechat_credentials import load_credentials  # noqa: E402


DEFAULT_THEME = "dasen-default"
DEFAULT_HIGHLIGHT = "dasen-light"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PREFLIGHT = SKILL_DIR.parent / "dasen-content" / "scripts" / "preflight.py"


def run_preflight(bundle: Path, *, dry_run: bool) -> None:
    stage = "render" if dry_run else "publish"
    command = [sys.executable, str(PREFLIGHT), "--bundle", str(bundle), "--stage", stage]
    if not dry_run:
        command.extend(["--append-record", "--update-status"])
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise RuntimeError("Publish preflight did not pass; no render or delivery was performed")


def count_markdown_headings(source: str, level: int) -> int:
    heading = re.compile(rf"^ {{0,3}}{'#' * level}(?!#)\s+")
    fence = re.compile(r"^\s*(`{3,}|~{3,})")
    in_fence = False
    fence_char = ""
    count = 0
    for line in source.splitlines():
        match = fence.match(line)
        if match:
            char = match.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = char
            elif char == fence_char:
                in_fence = False
                fence_char = ""
        elif not in_fence and heading.match(line):
            count += 1
    return count


def prepare_source(article_path: Path, root: Path, project: dict[str, Any]) -> tuple[str, int]:
    source = article_path.read_text(encoding="utf-8")
    rule = ((project.get("hard_rules") or {}).get("section_heading") or {})
    if not rule.get("required"):
        return source, 0
    level = int(rule.get("level") or 2)
    if level < 2 or level > 6:
        raise RuntimeError("section_heading.level must be between 2 and 6")
    template_path = (root / str(rule.get("template") or "")).resolve()
    if not template_path.is_relative_to(root) or not template_path.is_file():
        raise RuntimeError(f"section heading template not found under project root: {template_path}")
    image_url = str(rule.get("image_url") or "")
    marker = str(rule.get("marker") or "").strip()
    if not image_url.startswith("https://") or not marker:
        raise RuntimeError("section heading requires an HTTPS image_url and non-empty marker")
    template = template_path.read_text(encoding="utf-8")
    required = ("{{title}}", "{{marker}}", "{{image_url}}", "{{image_alt}}")
    missing = [token for token in required if token not in template]
    if missing:
        raise RuntimeError("section heading template missing placeholders: " + ", ".join(missing))
    transformed, count = replace_headings(
        source,
        level=level,
        template=template,
        values={
            "marker": marker,
            "image_url": image_url,
            "image_alt": str(rule.get("image_alt") or ""),
        },
    )
    return transformed, count


def verify_rendered(
    rendered: str,
    original_source: str,
    project: dict[str, Any],
    transformed_heading_count: int,
) -> None:
    errors: list[str] = []
    rules = project.get("hard_rules") or {}
    if 'data-dasen-renderer="native-v1"' not in rendered:
        errors.append("native renderer marker is missing")
    if re.search(r"<(?:script|style|iframe|object|embed|form)\b", rendered, re.I):
        errors.append("unsafe HTML survived sanitization")
    if rules.get("body_h1_forbidden") and re.search(r"<h1\b", rendered, re.I):
        errors.append("rendered body contains h1")

    guide = rules.get("follow_guide") or {}
    section_heading = rules.get("section_heading") or {}
    if guide.get("required"):
        marker = str(guide.get("marker") or "")
        url = str(guide.get("url") or "")
        expected_text = re.sub(r"\s+", "", str(guide.get("text") or ""))
        heading_url_uses = transformed_heading_count if section_heading.get("image_url") == url else 0
        if rendered.count(f'aria-label="{html.escape(marker, quote=True)}"') != 1:
            errors.append("rendered follow guide count is not 1")
        if rendered.count(html.escape(url, quote=True)) != 1 + heading_url_uses:
            errors.append("rendered follow guide image reference count is incorrect")
        visible = re.sub(r"<[^>]+>", " ", html.unescape(rendered))
        if expected_text and expected_text not in re.sub(r"\s+", "", visible):
            errors.append("rendered follow guide text is missing")

    if section_heading.get("required"):
        marker = str(section_heading.get("marker") or "")
        image_url = str(section_heading.get("image_url") or "")
        level = int(section_heading.get("level") or 2)
        expected = count_markdown_headings(original_source, level)
        guide_url_use = 1 if guide.get("url") == image_url else 0
        if transformed_heading_count != expected:
            errors.append(f"transformed heading count {transformed_heading_count} != {expected}")
        if rendered.count(f'aria-label="{html.escape(marker, quote=True)}"') != expected:
            errors.append("rendered section heading marker count is incorrect")
        if rendered.count(html.escape(image_url, quote=True)) != expected + guide_url_use:
            errors.append("rendered section heading image count is incorrect")
    if errors:
        raise RuntimeError("; ".join(errors))


def sanitize_delivery_detail(detail: str, limit: int = 400) -> str:
    """Make external failures safe for a tracked Markdown receipt."""
    value = re.sub(r"[\r\n\t]+", " ", str(detail or ""))

    def strip_query(match: re.Match[str]) -> str:
        parsed = urllib.parse.urlsplit(match.group(0))
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

    value = re.sub(r"https?://[^\s<>()]+", strip_query, value)
    home = str(Path.home())
    if home:
        value = value.replace(home, "[local-home]")
    value = re.sub(r"(?<![:/\w])/(?:[^\s/]+/)+[^\s]*", "[local-path]", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit] + ("…" if len(value) > limit else "")


def append_delivery(record: Path, result: str, article: Path, theme: str, media_id: str = "", detail: str = "") -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "",
        f"## Draft Delivery · {now}",
        "",
        f"- 结果：{result}",
        "- 平台：wechat draft box",
        f"- 文章：`{article.name}`",
        "- 渲染器：dasen native-v1",
        f"- 主题：{theme}",
    ]
    if media_id:
        lines.append(f"- Media ID：`{media_id}`")
    if detail:
        lines.append(f"- 说明：{sanitize_delivery_detail(detail)}")
    lines.append("- 正式发布：未执行，等待人工后台核对")
    with record.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def update_status_delivered(brief_path: Path) -> None:
    data = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
    data["status"] = "delivered"
    data["blocker"] = None
    data["resume_from"] = None
    brief_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _read_delivery_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_delivery_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _content_digest(article_path: Path, rendered: str) -> str:
    digest = hashlib.sha256()
    digest.update(article_path.read_bytes())
    digest.update(b"\0rendered\0")
    digest.update(rendered.encode("utf-8"))
    return digest.hexdigest()


def begin_delivery(
    path: Path,
    article_sha256: str,
    *,
    retry_confirmed: bool,
    new_draft: bool,
) -> str:
    previous = _read_delivery_state(path)
    status = str(previous.get("status") or "")
    if status in {"submitting", "uncertain"} and not retry_confirmed:
        raise RuntimeError(
            "a previous draft request may have reached WeChat; confirm the draft box, then use "
            "--resolve-media-id, --abandon-pending, or --retry-confirmed"
        )
    if (
        status == "succeeded"
        and previous.get("article_sha256") == article_sha256
        and not new_draft
    ):
        raise RuntimeError("this exact article already has a successful draft receipt; use --new-draft explicitly")
    history = previous.get("history") if isinstance(previous.get("history"), list) else []
    if previous:
        history = [*history, {key: previous.get(key) for key in (
            "operation_id", "article_sha256", "status", "media_id", "updated_at"
        )}][-20:]
    operation_id = uuid.uuid4().hex
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    _write_delivery_state(path, {
        "operation_id": operation_id,
        "article_sha256": article_sha256,
        "status": "preparing",
        "media_id": None,
        "created_at": now,
        "updated_at": now,
        "history": history,
    })
    return operation_id


def transition_delivery(path: Path, operation_id: str, status: str, media_id: str | None = None) -> None:
    state = _read_delivery_state(path)
    if state.get("operation_id") != operation_id:
        raise RuntimeError("delivery state changed during the operation; refusing to overwrite it")
    state["status"] = status
    state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    if media_id:
        state["media_id"] = media_id
    _write_delivery_state(path, state)


def resolve_pending_delivery(path: Path, *, media_id: str | None, abandon: bool) -> str:
    state = _read_delivery_state(path)
    status = str(state.get("status") or "")
    if status == "succeeded":
        existing = str(state.get("media_id") or "")
        if abandon:
            raise RuntimeError("a successful delivery cannot be abandoned")
        if not media_id or media_id != existing:
            raise RuntimeError("--resolve-media-id must match the successful delivery state")
        return "succeeded"
    if status not in {"submitting", "uncertain"}:
        raise RuntimeError("there is no pending/uncertain draft delivery to resolve")
    operation_id = str(state.get("operation_id") or "")
    if abandon:
        transition_delivery(path, operation_id, "abandoned")
        return "abandoned"
    if not media_id or not re.fullmatch(r"[A-Za-z0-9_-]{8,256}", media_id):
        raise RuntimeError("--resolve-media-id must be a plausible WeChat Media ID")
    transition_delivery(path, operation_id, "succeeded", media_id)
    return "succeeded"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render and save a content bundle to the WeChat draft box")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", "-o", type=Path, help="With --dry-run, save rendered HTML locally")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing local HTML output")
    parser.add_argument("--retry-confirmed", action="store_true", help="Start a new request after manually confirming no prior draft exists")
    parser.add_argument("--new-draft", action="store_true", help="Create another draft for content already delivered successfully")
    resolution = parser.add_mutually_exclusive_group()
    resolution.add_argument("--resolve-media-id", help="Reconcile a pending request or finalize a successful state with its Media ID")
    resolution.add_argument("--abandon-pending", action="store_true", help="Mark a manually checked pending request as absent/abandoned")
    parser.add_argument("input", type=Path)
    parser.add_argument("theme", nargs="?")
    parser.add_argument("highlight", nargs="?")
    args = parser.parse_args(argv)
    if args.dry_run and any((args.retry_confirmed, args.new_draft, args.resolve_media_id, args.abandon_pending)):
        raise RuntimeError("delivery recovery options cannot be combined with --dry-run")
    if (args.output or args.force) and not args.dry_run:
        raise RuntimeError("--output/--force are local-export options and require --dry-run")

    input_path = args.input.resolve()
    bundle: Path | None = None
    project: dict[str, Any] = {}
    brief: dict[str, Any] = {}
    root = input_path.parent
    if input_path.is_dir():
        bundle = input_path
        article_path = bundle / "article.md"
        record = bundle / "record.md"
        brief_path = bundle / "brief.yaml"
        if not article_path.is_file():
            raise RuntimeError(f"content bundle is missing article.md: {bundle}")
        run_preflight(bundle, dry_run=args.dry_run)
        root, brief, project = load_bundle_config(bundle)
        project_theme, project_highlight = channel_options(brief, project)
    elif input_path.is_file():
        article_path = input_path
        record = Path()
        brief_path = Path()
        project_theme = ""
        project_highlight = ""
        print("WARNING: legacy single-file mode does not have the complete content-bundle gates", file=sys.stderr)
    else:
        raise RuntimeError(f"input does not exist: {input_path}")

    requested_theme = args.theme or project_theme or DEFAULT_THEME
    requested_highlight = args.highlight or project_highlight or DEFAULT_HIGHLIGHT
    theme = load_theme(SKILL_DIR / "themes", requested_theme)
    original_source = article_path.read_text(encoding="utf-8")
    prepared_source, transformed = prepare_source(article_path, root, project)
    article = load_article_text(prepared_source)
    rendered = render_markdown(article.markdown, theme, requested_highlight)
    verify_rendered(rendered, original_source, project, transformed)

    if args.dry_run:
        if args.output:
            output = args.output.resolve()
            if output == article_path:
                raise RuntimeError("local HTML output must differ from article.md")
            if output.exists() and not args.force:
                raise RuntimeError(f"local HTML output exists; pass --force to replace it: {output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered + "\n", encoding="utf-8")
            print(f"- local HTML: {output}")
        print("PASS: content bundle, render preflight and native WeChat render; no credentials or platform writes used")
        print(f"- theme: {theme.theme_id}")
        print(f"- highlight: {DEFAULT_HIGHLIGHT}")
        return 0

    delivery_state = evidence_dir(bundle, brief) / "delivery.json" if bundle is not None else None
    if args.resolve_media_id or args.abandon_pending:
        if bundle is None or delivery_state is None:
            raise RuntimeError("delivery recovery requires content-bundle mode")
        outcome = resolve_pending_delivery(
            delivery_state, media_id=args.resolve_media_id, abandon=args.abandon_pending
        )
        if outcome == "succeeded":
            append_delivery(
                record,
                "PASS",
                article_path,
                theme.theme_id,
                args.resolve_media_id,
                "reconciled from a user-confirmed draft Media ID",
            )
            update_status_delivered(brief_path)
        else:
            append_delivery(record, "ABANDONED", article_path, theme.theme_id, detail="pending request manually checked and abandoned")
        print(f"PASS: pending delivery {outcome}; no platform request was made")
        return 0

    operation_id = ""
    try:
        credentials = load_credentials(project, str(brief.get("platform") or "wechat"))
        client = WechatClient(credentials.app_id, credentials.app_secret)
        asset_root = article_path.parent
        if bundle is not None:
            root_value = Path(str(assets_config(brief)["root"]))
            if root_value.is_absolute():
                raise RuntimeError("assets.root must be project-relative")
            asset_root = (root / root_value).resolve()
            if not asset_root.is_relative_to(root):
                raise RuntimeError("assets.root must stay under the project root")
        if delivery_state is not None:
            operation_id = begin_delivery(
                delivery_state,
                _content_digest(article_path, rendered),
                retry_confirmed=args.retry_confirmed,
                new_draft=args.new_draft,
            )

        def before_draft() -> None:
            if delivery_state is not None:
                transition_delivery(delivery_state, operation_id, "submitting")

        media_id = client.publish_article(
            article.metadata,
            rendered,
            article_path.parent,
            asset_root,
            before_draft,
        )
    except Exception as exc:
        if delivery_state is not None and operation_id:
            current = _read_delivery_state(delivery_state)
            failure_status = "uncertain" if current.get("status") == "submitting" else "failed"
            transition_delivery(delivery_state, operation_id, failure_status)
        if bundle is not None:
            append_delivery(record, "FAIL", article_path, theme.theme_id, detail=str(exc))
        raise
    if not media_id:
        if bundle is not None:
            append_delivery(record, "UNVERIFIED", article_path, theme.theme_id, detail="draft API returned no Media ID")
        raise RuntimeError("draft API returned no Media ID; status was not marked delivered")
    if bundle is not None:
        try:
            transition_delivery(delivery_state, operation_id, "succeeded", media_id)
        except Exception:
            print(
                f"UNVERIFIED: WeChat returned Media ID {media_id}, but the local delivery receipt could not be finalized",
                file=sys.stderr,
            )
            raise
        append_delivery(record, "PASS", article_path, theme.theme_id, media_id, "saved to draft box")
        update_status_delivered(brief_path)
    print(f"PASS: saved to WeChat draft box; Media ID: {media_id}; formal publication was not performed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, WechatApiError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(3)
