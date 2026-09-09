#!/usr/bin/env python3
"""Create deterministic project-owned cover template and asset receipts."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))
from content_paths import control_reference, evidence_dir, select_content_root
from project_config import assets_config, load_project_reference, visual_config  # noqa: E402


FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?", re.S)
TEMPLATE_ID = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")


def _atomic_write(path: Path, text: str) -> None:
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


def _project_file(project_root: Path, reference: str, *, asset_root: str | None = None) -> Path:
    raw = Path(str(reference).strip()).expanduser()
    if not str(reference).strip() or raw.is_absolute() or ".." in raw.parts:
        raise ValueError("资产路径必须是项目内相对路径")
    root = project_root.resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"项目资产不存在或逃逸项目根目录：{reference}")
    if asset_root:
        allowed = (root / asset_root).resolve()
        if not path.is_relative_to(allowed):
            raise ValueError(f"项目资产必须位于 assets.root：{reference}")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_template_reference(
    *,
    project_config: dict[str, Any],
    project_root: Path,
    template_id: str,
    reference_path: str,
    reference_url: str,
    confirmed: bool,
) -> dict[str, str]:
    if not confirmed:
        raise ValueError("封面模板必须先经用户确认")
    if not TEMPLATE_ID.fullmatch(template_id):
        raise ValueError("template_id 格式无效")
    parsed = urllib.parse.urlsplit(reference_url)
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment
    ):
        raise ValueError("reference_url 必须是无凭证、无查询参数的 HTTPS URL")
    root = project_root.resolve()
    asset_root = str(assets_config(project_config)["root"])
    reference = _project_file(root, reference_path, asset_root=asset_root)
    library_ref = str(visual_config(project_config).get("layout_library") or "").strip()
    library = Path(library_ref)
    if not library_ref or library.is_absolute() or ".." in library.parts:
        raise ValueError("visual.layout_library 必须是项目内相对路径")
    library_root = (root / library).resolve()
    if not library_root.is_relative_to(root):
        raise ValueError("visual.layout_library 不能通过符号链接逃逸项目根目录")
    template = (library_root / f"{template_id}.md").resolve()
    if not template.is_relative_to(library_root) or not template.is_file():
        raise ValueError(f"封面模板不存在：{library_ref}/{template_id}.md")
    text = template.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("封面模板缺 YAML frontmatter")
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError("封面模板 frontmatter 顶层必须是对象")
    existing_id = str(metadata.get("id") or "").strip()
    if existing_id and existing_id != template_id:
        raise ValueError("封面模板 frontmatter.id 与文件名不一致")
    digest = _sha256(reference)
    metadata.update({
        "id": template_id,
        "reference_path": reference_path,
        "reference_url": reference_url,
        "reference_sha256": digest,
        "status": "verified",
    })
    body = text[match.end():]
    rendered = "---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + "---\n" + body
    _atomic_write(template, rendered)
    return {"template_id": template_id, "reference_sha256": digest}


def finalize_cover_receipt(
    project_config: dict[str, Any],
    project_root: Path,
    bundle: Path,
) -> dict[str, str]:
    root = project_root.resolve()
    bundle = bundle.resolve()
    if not bundle.is_relative_to(root):
        raise ValueError("内容包必须位于项目根目录内")
    manifest_path = evidence_dir(bundle) / "cover.yaml"
    record_path = bundle / "record.md"
    if not manifest_path.is_file() or not record_path.is_file():
        raise ValueError("内容包缺审计目录中的 cover.yaml 或 record.md")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(manifest, dict):
        raise ValueError("cover.yaml 顶层必须是对象")
    asset_root = str(assets_config(project_config)["root"])
    source = _project_file(root, str(manifest.get("source_path") or ""), asset_root=asset_root)
    final = _project_file(root, str(manifest.get("final_path") or ""), asset_root=asset_root)
    source_sha = _sha256(source)
    final_sha = _sha256(final)
    manifest["source_sha256"] = source_sha
    manifest["final_sha256"] = final_sha
    _atomic_write(
        manifest_path,
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
    )
    record = record_path.read_text(encoding="utf-8")
    marker = f"- source_sha256: {source_sha}\n- final_sha256: {final_sha}"
    if marker not in record:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        suffix = f"\n## Cover Asset Receipt · {timestamp}\n\n{marker}\n"
        with record_path.open("a", encoding="utf-8") as handle:
            handle.write(suffix)
    return {"source_sha256": source_sha, "final_sha256": final_sha}


def _project(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    workspace = Path.cwd().resolve()
    root = select_content_root(workspace, project_file=args.project_file)
    reference = control_reference(workspace, root, args.project_file)
    _, project = load_project_reference(reference, root)
    return root, project


def main() -> int:
    parser = argparse.ArgumentParser(description="Create project-owned cover receipts")
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("register-template")
    template.add_argument("--project-file", required=True)
    template.add_argument("--template-id", required=True)
    template.add_argument("--reference-path", required=True)
    template.add_argument("--reference-url", required=True)
    template.add_argument("--confirmed", action="store_true")
    cover = commands.add_parser("finalize-cover")
    cover.add_argument("--project-file", required=True)
    cover.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    root, project = _project(args)
    if args.command == "register-template":
        result = register_template_reference(
            project_config=project, project_root=root, template_id=args.template_id,
            reference_path=args.reference_path, reference_url=args.reference_url,
            confirmed=args.confirmed,
        )
    else:
        result = finalize_cover_receipt(project, root, args.bundle)
    print(yaml.safe_dump({"status": "saved", **result}, allow_unicode=True).strip())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
