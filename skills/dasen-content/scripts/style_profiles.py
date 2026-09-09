#!/usr/bin/env python3
"""Resolve writing styles and persist confirmed styles to a project-local catalog."""
from __future__ import annotations

import argparse
import os
import re
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml


STYLE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
STYLE_LIST_FIELDS = ("voice", "rhythm", "structure", "evidence", "avoid")
SOURCE_KINDS = {"dasen-original", "project-authored", "sample-derived"}
BUILTIN_CATALOG = Path(__file__).resolve().parent.parent / "references/writing-styles.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"写作风格库无法解析：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"写作风格库顶层必须是对象：{path}")
    return data


def _clean_string_list(value: object, field: str, style_id: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"style {style_id}.{field} 必须是字符串数组")
    cleaned = [str(item).strip() for item in value]
    if any(not item for item in cleaned):
        raise ValueError(f"style {style_id}.{field} 不得包含空值")
    return list(dict.fromkeys(cleaned))


def load_catalog(path: Path, *, origin: str) -> dict[str, dict[str, Any]]:
    """Validate a catalog and return normalized style records keyed by ID."""
    data = _load_yaml(path)
    if data.get("schema_version") != 1:
        raise ValueError(f"写作风格库 schema_version 必须为 1：{path}")
    raw_styles = data.get("styles")
    if not isinstance(raw_styles, dict) or not raw_styles:
        raise ValueError(f"写作风格库 styles 必须是非空对象：{path}")

    result: dict[str, dict[str, Any]] = {}
    for raw_id, raw_style in raw_styles.items():
        style_id = str(raw_id)
        if not STYLE_ID.fullmatch(style_id):
            raise ValueError(f"无效 Style ID：{style_id}")
        if not isinstance(raw_style, dict):
            raise ValueError(f"style {style_id} 必须是对象")
        label = str(raw_style.get("label") or "").strip()
        summary = str(raw_style.get("summary") or "").strip()
        revision = raw_style.get("revision")
        if not label or not summary:
            raise ValueError(f"style {style_id} 必须填写 label 和 summary")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError(f"style {style_id}.revision 必须是正整数")

        raw_source = raw_style.get("source") or {}
        if not isinstance(raw_source, dict):
            raise ValueError(f"style {style_id}.source 必须是对象")
        kind = str(raw_source.get("kind") or "").strip()
        if kind not in SOURCE_KINDS:
            raise ValueError(f"style {style_id}.source.kind 不受支持：{kind}")
        sample_refs = _clean_string_list(raw_source.get("sample_refs") or [], "source.sample_refs", style_id)
        conflicts = _clean_string_list(raw_source.get("conflicts") or [], "source.conflicts", style_id)
        captured_at = raw_source.get("captured_at")
        if captured_at is not None and not str(captured_at).strip():
            raise ValueError(f"style {style_id}.source.captured_at 不得为空")
        if kind == "sample-derived":
            if len(sample_refs) < 3:
                raise ValueError(f"sample-derived style {style_id} 至少需要 3 条 sample_refs")
            if captured_at is None:
                raise ValueError(f"sample-derived style {style_id} 必须记录 captured_at")

        normalized: dict[str, Any] = {
            "id": style_id,
            "label": label,
            "revision": revision,
            "summary": summary,
            "origin": origin,
            "source": {
                "kind": kind,
                "sample_refs": sample_refs,
                "conflicts": conflicts,
                "captured_at": str(captured_at) if captured_at is not None else None,
            },
        }
        for field in STYLE_LIST_FIELDS:
            normalized[field] = _clean_string_list(raw_style.get(field), field, style_id)
        result[style_id] = normalized
    return result


def project_style_library(
    config: dict[str, Any],
    project_root: Path,
    *,
    must_exist: bool = True,
) -> tuple[Path | None, str | None]:
    """Resolve an optional project-local catalog without allowing path escape."""
    writing = config.get("writing") or {}
    if not isinstance(writing, dict):
        raise ValueError("project.writing 必须是对象")
    reference = str(writing.get("style_library") or "").strip()
    if not reference:
        return None, None
    raw = Path(reference).expanduser()
    if raw.resolve() == BUILTIN_CATALOG.resolve():
        raise ValueError("中央内置风格库属于发行源码；项目风格只能写入项目私有库")
    if reference.startswith("@") or raw.is_absolute():
        raise ValueError("writing.style_library 只接受当前工作区内的相对路径")
    root = project_root.resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError("writing.style_library 必须位于项目根目录内")
    if path == BUILTIN_CATALOG.resolve():
        raise ValueError("中央内置风格库属于发行源码；项目风格只能写入项目私有库")
    if must_exist and not path.is_file():
        raise ValueError(f"writing.style_library 不存在：{reference}")
    return path, reference


def available_styles(config: dict[str, Any], project_root: Path) -> dict[str, dict[str, Any]]:
    catalog = load_catalog(BUILTIN_CATALOG, origin="builtin")
    path, reference = project_style_library(config, project_root)
    if path is None:
        return catalog
    custom = load_catalog(path, origin=f"project:{reference}")
    collisions = sorted(set(catalog) & set(custom))
    if collisions:
        raise ValueError(f"项目风格不得覆盖内置 Style ID：{collisions[0]}")
    return {**catalog, **custom}


def _atomic_write_catalog(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _validated_sample_refs(sample_refs: list[str], project_root: Path) -> list[str]:
    root = project_root.resolve()
    cleaned: list[str] = []
    for value in sample_refs:
        reference = str(value).strip()
        raw = Path(reference).expanduser()
        if not reference or reference.startswith("@") or raw.is_absolute() or ".." in raw.parts:
            raise ValueError("sample_refs 只接受项目内已存在文件的相对路径")
        path = (root / raw).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"sample_ref 不存在或逃逸项目根目录：{reference}")
        cleaned.append(reference)
    return list(dict.fromkeys(cleaned))


def save_project_style(
    *,
    project_config: dict[str, Any],
    project_root: Path,
    style_id: str,
    label: str,
    summary: str,
    source_kind: str,
    sample_refs: list[str],
    conflicts: list[str],
    captured_at: str,
    voice: list[str],
    rhythm: list[str],
    structure: list[str],
    evidence: list[str],
    avoid: list[str],
    confirmed: bool,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Add or explicitly revise one style without exposing a central write path."""
    if not confirmed:
        raise ValueError("项目风格画像必须先获得用户确认")
    if not STYLE_ID.fullmatch(style_id):
        raise ValueError(f"无效 Style ID：{style_id}")
    builtin = load_catalog(BUILTIN_CATALOG, origin="builtin")
    if style_id in builtin:
        raise ValueError(f"项目风格不得使用内置 Style ID：{style_id}")
    if source_kind not in {"project-authored", "sample-derived"}:
        raise ValueError("项目风格 source.kind 只能是 project-authored 或 sample-derived")
    samples = _validated_sample_refs(sample_refs, project_root)
    if source_kind == "sample-derived" and len(samples) < 3:
        raise ValueError("sample-derived 项目风格至少需要 3 条 sample_refs")
    captured = str(captured_at).strip()
    if not captured:
        raise ValueError("项目风格必须记录 captured_at")
    try:
        date.fromisoformat(captured)
    except ValueError as exc:
        raise ValueError("项目风格 captured_at 必须是 YYYY-MM-DD") from exc

    path, reference = project_style_library(project_config, project_root, must_exist=False)
    if path is None or reference is None:
        raise ValueError("项目未配置 writing.style_library，不能持久化私有风格")

    if path.exists():
        data = _load_yaml(path)
        load_catalog(path, origin=f"project:{reference}")
    else:
        data = {"schema_version": 1, "styles": {}}
    if data.get("schema_version") != 1 or not isinstance(data.get("styles"), dict):
        raise ValueError(f"写作风格库 schema 无效：{path}")

    styles = data["styles"]
    existing = styles.get(style_id)
    if existing is None:
        if expected_revision is not None:
            raise ValueError(f"项目 Style ID 不存在，不能修订：{style_id}")
        revision = 1
    else:
        current_revision = existing.get("revision") if isinstance(existing, dict) else None
        if expected_revision is None:
            raise ValueError(f"项目 Style ID 已存在；修订时必须提供 expected_revision：{style_id}")
        if current_revision != expected_revision:
            raise ValueError(
                f"项目 Style revision 已变化：期望 {expected_revision}，实际 {current_revision}"
            )
        revision = expected_revision + 1

    style = {
        "label": str(label).strip(),
        "revision": revision,
        "summary": str(summary).strip(),
        "source": {
            "kind": source_kind,
            "sample_refs": samples,
            "conflicts": _clean_string_list(conflicts, "source.conflicts", style_id),
            "captured_at": captured,
        },
        "voice": _clean_string_list(voice, "voice", style_id),
        "rhythm": _clean_string_list(rhythm, "rhythm", style_id),
        "structure": _clean_string_list(structure, "structure", style_id),
        "evidence": _clean_string_list(evidence, "evidence", style_id),
        "avoid": _clean_string_list(avoid, "avoid", style_id),
    }
    if not style["label"] or not style["summary"]:
        raise ValueError(f"style {style_id} 必须填写 label 和 summary")
    styles[style_id] = style
    _atomic_write_catalog(path, data)
    return load_catalog(path, origin=f"project:{reference}")[style_id]


def validate_style_snapshot(snapshot: object, expected_id: str) -> None:
    """Validate the resolved style embedded in a brief without reopening its catalog."""
    if not isinstance(snapshot, dict):
        raise ValueError("brief.style_profile 必须是对象")
    style_id = str(snapshot.get("id") or "").strip()
    if style_id != expected_id:
        raise ValueError("brief.style_profile.id 必须与 brief.profile 一致")
    if not STYLE_ID.fullmatch(style_id):
        raise ValueError(f"无效 Style ID：{style_id}")
    if not str(snapshot.get("label") or "").strip() or not str(snapshot.get("summary") or "").strip():
        raise ValueError("brief.style_profile 缺 label/summary")
    revision = snapshot.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("brief.style_profile.revision 必须是正整数")
    if not str(snapshot.get("origin") or "").strip():
        raise ValueError("brief.style_profile.origin 为空")
    if snapshot.get("selected_from") not in {"brief", "series", "project", "fallback"}:
        raise ValueError("brief.style_profile.selected_from 无效")
    source = snapshot.get("source") or {}
    if not isinstance(source, dict) or source.get("kind") not in SOURCE_KINDS:
        raise ValueError("brief.style_profile.source 无效")
    sample_refs = _clean_string_list(source.get("sample_refs") or [], "source.sample_refs", style_id)
    _clean_string_list(source.get("conflicts") or [], "source.conflicts", style_id)
    if source.get("kind") == "sample-derived":
        if len(sample_refs) < 3:
            raise ValueError("sample-derived brief.style_profile 至少需要 3 条 sample_refs")
        if not str(source.get("captured_at") or "").strip():
            raise ValueError("sample-derived brief.style_profile 必须记录 captured_at")
    for field in STYLE_LIST_FIELDS:
        _clean_string_list(snapshot.get(field), field, style_id)


def resolve_style(
    *,
    requested: str | None,
    project_config: dict[str, Any],
    series_config: dict[str, Any],
    project_root: Path,
    journey: str,
) -> dict[str, Any]:
    """Resolve brief > series > project > journey-aware fallback to one style."""
    project_defaults = project_config.get("defaults") or {}
    candidates = (
        ("brief", requested),
        ("series", series_config.get("profile")),
        ("project", project_defaults.get("profile") if isinstance(project_defaults, dict) else None),
        ("fallback", "flash" if journey == "breaking" else "practical"),
    )
    selected_from, raw_id = next(
        (source, value) for source, value in candidates if str(value or "").strip()
    )
    style_id = str(raw_id).strip()
    if not STYLE_ID.fullmatch(style_id):
        raise ValueError(f"无效 Style ID：{style_id}")
    catalog = available_styles(project_config, project_root)
    if style_id not in catalog:
        choices = ", ".join(sorted(catalog))
        raise ValueError(f"未知 Style ID：{style_id}；可用值：{choices}")
    resolved = deepcopy(catalog[style_id])
    resolved["selected_from"] = selected_from
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Persist one user-confirmed writing style to the configured project-local catalog"
    )
    parser.add_argument("--project-file", required=True, help="Workspace-relative project.md path")
    parser.add_argument("--id", required=True, dest="style_id")
    parser.add_argument("--label", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source-kind", choices=("project-authored", "sample-derived"), required=True)
    parser.add_argument("--sample-ref", action="append", default=[])
    parser.add_argument("--conflict", action="append", default=[])
    parser.add_argument("--captured-at", default=date.today().isoformat())
    parser.add_argument("--voice", action="append", required=True)
    parser.add_argument("--rhythm", action="append", required=True)
    parser.add_argument("--structure", action="append", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--avoid", action="append", required=True)
    parser.add_argument("--expected-revision", type=int)
    parser.add_argument("--confirmed", action="store_true", help="Assert that the user confirmed this profile")
    args = parser.parse_args()

    from project_config import load_project_reference

    project_root = Path.cwd().resolve()
    _, project = load_project_reference(args.project_file, project_root)
    saved = save_project_style(
        project_config=project,
        project_root=project_root,
        style_id=args.style_id,
        label=args.label,
        summary=args.summary,
        source_kind=args.source_kind,
        sample_refs=args.sample_ref,
        conflicts=args.conflict,
        captured_at=args.captured_at,
        voice=args.voice,
        rhythm=args.rhythm,
        structure=args.structure,
        evidence=args.evidence,
        avoid=args.avoid,
        confirmed=args.confirmed,
        expected_revision=args.expected_revision,
    )
    print(yaml.safe_dump({"status": "saved", "style_id": saved["id"], "revision": saved["revision"]}, allow_unicode=True).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
