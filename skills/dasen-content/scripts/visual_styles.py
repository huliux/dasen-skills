#!/usr/bin/env python3
"""Resolve visual styles and persist confirmed styles to a project-local catalog."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml


STYLE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
TOKEN_REF = re.compile(r"\{([a-z0-9_.-]+)\}")
ROLES = {"body", "cover"}
METHODS = {"html-css", "image-model", "manual"}
SOURCE_KINDS = {"dasen-original", "project-authored", "sample-derived"}
LIST_FIELDS = ("do", "avoid", "omitted", "known_gaps")
ROLE_DEFAULTS = {
    "body": "body-clean-editorial",
    "cover": "cover-clean-editorial",
}
LEGACY_PRESET_STYLES = {
    "bitbook-editorial": {
        "body": "body-whiteboard-clarity",
        "cover": "cover-clean-editorial",
    }
}
ROLE_COMPONENTS = {
    "body": {"canvas", "information-node", "caption"},
    "cover": {"headline-zone", "hero-subject", "atmosphere-layer", "safe-area"},
}
ROLE_CONSTRAINTS = {
    "body": {"mobile_min_text_px", "max_information_units", "evidence_treatment"},
    "cover": {"headline_max_chars", "safe_area_percent", "crop_strategy"},
}
BUILTIN_CATALOG = Path(__file__).resolve().parent.parent / "references/visual-styles.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"视觉风格文件无法解析：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"视觉风格文件顶层必须是对象：{path}")
    return data


def _string_list(value: object, field: str, style_id: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"visual style {style_id}.{field} 必须是字符串数组")
    cleaned = [str(item).strip() for item in value]
    if any(not item for item in cleaned) or (nonempty and not cleaned):
        raise ValueError(f"visual style {style_id}.{field} 不得为空")
    return list(dict.fromkeys(cleaned))


def _token_path_exists(style: dict[str, Any], path: str) -> bool:
    value: object = style
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return not isinstance(value, (dict, list))


def _validate_refs(value: object, style: dict[str, Any], style_id: str) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _validate_refs(child, style, style_id)
    elif isinstance(value, list):
        for child in value:
            _validate_refs(child, style, style_id)
    elif isinstance(value, str):
        for path in TOKEN_REF.findall(value):
            if not _token_path_exists(style, path):
                raise ValueError(f"visual style {style_id} 引用了不存在的 token：{path}")


def _normalize_samples(value: object, style_id: str, role: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"visual style {style_id}.source.samples 必须是数组")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"visual style {style_id}.source.samples 每项必须包含 path/sha256")
        path = str(item.get("path") or "").strip()
        digest = str(item.get("sha256") or "").strip().lower()
        sample_role = str(item.get("role") or "").strip()
        if not path or Path(path).is_absolute() or path.startswith("@") or ".." in Path(path).parts:
            raise ValueError(f"visual style {style_id}.source.samples 只接受项目相对路径")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"visual style {style_id}.source.samples 缺有效 sha256")
        if sample_role != role:
            raise ValueError(f"visual style {style_id}.source.samples.role 必须是 {role}")
        if path not in seen:
            result.append({"path": path, "sha256": digest, "role": sample_role})
            seen.add(path)
    return result


def _normalize_style(style_id: str, raw_style: object, *, origin: str) -> dict[str, Any]:
    if not STYLE_ID.fullmatch(style_id):
        raise ValueError(f"无效 Visual Style ID：{style_id}")
    if not isinstance(raw_style, dict):
        raise ValueError(f"visual style {style_id} 必须是对象")
    role = str(raw_style.get("role") or "").strip()
    label = str(raw_style.get("label") or "").strip()
    summary = str(raw_style.get("summary") or "").strip()
    revision = raw_style.get("revision")
    if role not in ROLES:
        raise ValueError(f"visual style {style_id}.role 必须是 body 或 cover")
    if not label or not summary:
        raise ValueError(f"visual style {style_id} 必须填写 label 和 summary")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError(f"visual style {style_id}.revision 必须是正整数")

    source = raw_style.get("source") or {}
    if not isinstance(source, dict):
        raise ValueError(f"visual style {style_id}.source 必须是对象")
    source_kind = str(source.get("kind") or "").strip()
    if source_kind not in SOURCE_KINDS:
        raise ValueError(f"visual style {style_id}.source.kind 不受支持：{source_kind}")
    samples = _normalize_samples(source.get("samples") or [], style_id, role)
    conflicts = _string_list(source.get("conflicts") or [], "source.conflicts", style_id)
    captured_at = source.get("captured_at")
    if source_kind == "sample-derived":
        if len(samples) < 3:
            raise ValueError(f"sample-derived visual style {style_id} 至少需要 3 条样本回执")
        if not str(captured_at or "").strip():
            raise ValueError(f"sample-derived visual style {style_id} 必须记录 captured_at")

    methods = _string_list(raw_style.get("compatible_methods"), "compatible_methods", style_id, nonempty=True)
    unsupported = sorted(set(methods) - METHODS)
    if unsupported:
        raise ValueError(f"visual style {style_id} 使用未知 render method：{unsupported[0]}")
    tokens = raw_style.get("tokens")
    components = raw_style.get("components")
    constraints = raw_style.get("constraints")
    if not isinstance(tokens, dict) or not tokens:
        raise ValueError(f"visual style {style_id}.tokens 必须是非空对象")
    if not isinstance(components, dict) or not components:
        raise ValueError(f"visual style {style_id}.components 必须是非空对象")
    if not isinstance(constraints, dict):
        raise ValueError(f"visual style {style_id}.constraints 必须是对象")
    missing_components = ROLE_COMPONENTS[role] - set(components)
    missing_constraints = ROLE_CONSTRAINTS[role] - set(constraints)
    if missing_components:
        raise ValueError(f"visual style {style_id} 缺 {role} component：{sorted(missing_components)[0]}")
    if missing_constraints:
        raise ValueError(f"visual style {style_id} 缺 {role} constraint：{sorted(missing_constraints)[0]}")
    for field in ROLE_CONSTRAINTS[role] & {"mobile_min_text_px", "max_information_units", "headline_max_chars", "safe_area_percent"}:
        value = constraints.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"visual style {style_id}.constraints.{field} 必须是正整数")

    normalized: dict[str, Any] = {
        "id": style_id,
        "role": role,
        "label": label,
        "revision": revision,
        "summary": summary,
        "origin": origin,
        "source": {
            "kind": source_kind,
            "samples": samples,
            "conflicts": conflicts,
            "captured_at": str(captured_at) if captured_at is not None else None,
        },
        "compatible_methods": methods,
        "tokens": deepcopy(tokens),
        "components": deepcopy(components),
        "constraints": deepcopy(constraints),
    }
    for field in LIST_FIELDS:
        normalized[field] = _string_list(raw_style.get(field), field, style_id)
    _validate_refs(normalized["components"], normalized, style_id)
    return normalized


def load_catalog(path: Path, *, origin: str) -> dict[str, dict[str, Any]]:
    data = _load_yaml(path)
    if data.get("schema_version") != 1:
        raise ValueError(f"视觉风格库 schema_version 必须为 1：{path}")
    raw_styles = data.get("styles")
    if not isinstance(raw_styles, dict) or not raw_styles:
        raise ValueError(f"视觉风格库 styles 必须是非空对象：{path}")
    return {
        str(style_id): _normalize_style(str(style_id), raw, origin=origin)
        for style_id, raw in raw_styles.items()
    }


def project_style_library(
    config: dict[str, Any], project_root: Path, *, must_exist: bool = True
) -> tuple[Path | None, str | None]:
    visual = config.get("visual") or {}
    if not isinstance(visual, dict):
        raise ValueError("project.visual 必须是对象")
    reference = str(visual.get("style_library") or "").strip()
    if not reference:
        return None, None
    raw = Path(reference).expanduser()
    if reference.startswith("@") or raw.is_absolute() or ".." in raw.parts:
        raise ValueError("visual.style_library 只接受当前工作区内的相对路径")
    root = project_root.resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError("visual.style_library 必须位于项目根目录内")
    if path == BUILTIN_CATALOG.resolve():
        raise ValueError("中央内置视觉风格库属于发行源码；项目只能写入私有库")
    if must_exist and not path.is_file():
        raise ValueError(f"visual.style_library 不存在：{reference}")
    return path, reference


def available_styles(config: dict[str, Any], project_root: Path) -> dict[str, dict[str, Any]]:
    builtin = load_catalog(BUILTIN_CATALOG, origin="builtin")
    path, reference = project_style_library(config, project_root)
    if path is None:
        return builtin
    custom = load_catalog(path, origin=f"project:{reference}")
    root = project_root.resolve()
    for style_id, style in custom.items():
        for sample in style["source"]["samples"]:
            sample_path = (root / sample["path"]).resolve()
            if not sample_path.is_relative_to(root) or not sample_path.is_file():
                raise ValueError(f"项目视觉风格 {style_id} 的样本不存在或越界：{sample['path']}")
            actual = hashlib.sha256(sample_path.read_bytes()).hexdigest()
            if actual != sample["sha256"]:
                raise ValueError(f"项目视觉风格 {style_id} 的样本与 sha256 不一致：{sample['path']}")
    collisions = sorted(set(builtin) & set(custom))
    if collisions:
        raise ValueError(f"项目视觉风格不得覆盖内置 Visual Style ID：{collisions[0]}")
    return {**builtin, **custom}


def resolve_visual_style(
    *, role: str, requested: str | None, project_config: dict[str, Any],
    series_config: dict[str, Any], project_root: Path
) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"未知 visual role：{role}")
    project_visual = project_config.get("visual") or {}
    project_defaults = project_visual.get("defaults") if isinstance(project_visual, dict) else {}
    project_defaults = project_defaults if isinstance(project_defaults, dict) else {}
    legacy_preset = str(project_visual.get("preset") or "").strip() if isinstance(project_visual, dict) else ""
    legacy_style = (LEGACY_PRESET_STYLES.get(legacy_preset) or {}).get(role)
    series_visual = series_config.get("visual") or {}
    series_visual = series_visual if isinstance(series_visual, dict) else {}
    key = f"{role}_style"
    candidates = (
        ("brief", requested),
        ("series", series_visual.get(key)),
        ("project", project_defaults.get(key)),
        ("legacy-preset", legacy_style),
        ("fallback", ROLE_DEFAULTS[role]),
    )
    selected_from, raw_id = next(
        (source, value) for source, value in candidates if str(value or "").strip()
    )
    style_id = str(raw_id).strip()
    catalog = available_styles(project_config, project_root)
    if style_id not in catalog:
        choices = ", ".join(sorted(key for key, value in catalog.items() if value["role"] == role))
        raise ValueError(f"未知 {role} Visual Style ID：{style_id}；可用值：{choices}")
    resolved = deepcopy(catalog[style_id])
    if resolved["role"] != role:
        raise ValueError(f"Visual Style ID {style_id} 的 role 是 {resolved['role']}，不能用于 {role}")
    resolved["selected_from"] = selected_from
    return resolved


def validate_style_snapshot(snapshot: object, *, expected_id: str, expected_role: str) -> None:
    if not isinstance(snapshot, dict):
        raise ValueError(f"brief.visual.{expected_role}.style 必须是对象")
    normalized = _normalize_style(expected_id, snapshot, origin=str(snapshot.get("origin") or ""))
    if str(snapshot.get("id") or "") != expected_id:
        raise ValueError(f"brief.visual.{expected_role}.style.id 与 style_id 不一致")
    if normalized["role"] != expected_role:
        raise ValueError(f"brief.visual.{expected_role}.style.role 必须是 {expected_role}")
    if not normalized["origin"]:
        raise ValueError(f"brief.visual.{expected_role}.style.origin 为空")
    if snapshot.get("selected_from") not in {"brief", "series", "project", "fallback", "legacy-preset"}:
        raise ValueError(f"brief.visual.{expected_role}.style.selected_from 无效")


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
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


def _sample_receipts(samples: object, project_root: Path, role: str) -> list[dict[str, str]]:
    if not isinstance(samples, list):
        raise ValueError("visual style source.samples 必须是数组")
    root = project_root.resolve()
    receipts: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in samples:
        reference = str(item.get("path") if isinstance(item, dict) else item).strip()
        raw = Path(reference).expanduser()
        if not reference or reference.startswith("@") or raw.is_absolute() or ".." in raw.parts:
            raise ValueError("visual style samples 只接受项目内文件的相对路径")
        path = (root / raw).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"visual style sample 不存在或逃逸项目根目录：{reference}")
        if reference not in seen:
            receipts.append({
                "path": reference,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "role": role,
            })
            seen.add(reference)
    return receipts


def save_project_style(
    *, project_config: dict[str, Any], project_root: Path, definition: dict[str, Any],
    confirmed: bool, expected_revision: int | None = None
) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("项目视觉风格必须先获得用户确认")
    style_id = str(definition.get("id") or "").strip()
    if not STYLE_ID.fullmatch(style_id):
        raise ValueError(f"无效 Visual Style ID：{style_id}")
    if style_id in load_catalog(BUILTIN_CATALOG, origin="builtin"):
        raise ValueError(f"项目视觉风格不得使用内置 Visual Style ID：{style_id}")
    source = definition.get("source") or {}
    if not isinstance(source, dict):
        raise ValueError("visual style source 必须是对象")
    source_kind = str(source.get("kind") or "").strip()
    if source_kind not in {"project-authored", "sample-derived"}:
        raise ValueError("项目视觉风格 source.kind 只能是 project-authored 或 sample-derived")
    captured_at = str(source.get("captured_at") or date.today().isoformat()).strip()
    try:
        date.fromisoformat(captured_at)
    except ValueError as exc:
        raise ValueError("项目视觉风格 captured_at 必须是 YYYY-MM-DD") from exc
    role = str(definition.get("role") or "").strip()
    if role not in ROLES:
        raise ValueError("项目视觉风格 role 必须是 body 或 cover")
    receipts = _sample_receipts(source.get("samples") or [], project_root, role)
    if source_kind == "sample-derived" and len(receipts) < 3:
        raise ValueError("sample-derived 项目视觉风格至少需要 3 条样本回执")

    path, reference = project_style_library(project_config, project_root, must_exist=False)
    if path is None or reference is None:
        raise ValueError("项目未配置 visual.style_library，不能持久化私有视觉风格")
    if path.exists():
        data = _load_yaml(path)
        load_catalog(path, origin=f"project:{reference}")
    else:
        data = {"schema_version": 1, "styles": {}}
    if data.get("schema_version") != 1 or not isinstance(data.get("styles"), dict):
        raise ValueError(f"视觉风格库 schema 无效：{path}")

    raw_style = deepcopy(definition)
    raw_style.pop("id", None)
    raw_style.pop("origin", None)
    raw_style.pop("selected_from", None)
    existing = data["styles"].get(style_id)
    if existing is None:
        if expected_revision is not None:
            raise ValueError(f"项目 Visual Style ID 不存在，不能修订：{style_id}")
        revision = 1
    else:
        current = existing.get("revision") if isinstance(existing, dict) else None
        if expected_revision is None:
            raise ValueError(f"项目 Visual Style ID 已存在；修订时必须提供 expected_revision：{style_id}")
        if current != expected_revision:
            raise ValueError(f"项目 Visual Style revision 已变化：期望 {expected_revision}，实际 {current}")
        revision = expected_revision + 1
    raw_style["revision"] = revision
    raw_style["source"] = {
        "kind": source_kind,
        "samples": receipts,
        "conflicts": source.get("conflicts") or [],
        "captured_at": captured_at,
    }
    _normalize_style(style_id, raw_style, origin=f"project:{reference}")
    data["styles"][style_id] = raw_style
    _atomic_write(path, data)
    return load_catalog(path, origin=f"project:{reference}")[style_id]


def _project(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    from project_config import load_project_reference

    root = Path.cwd().resolve()
    if not args.project_file:
        return root, {}
    _, project = load_project_reference(args.project_file, root)
    return root, project


def main() -> int:
    parser = argparse.ArgumentParser(description="List or save project-private visual styles")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--project-file")
    save = commands.add_parser("save")
    save.add_argument("--project-file", required=True)
    save.add_argument("--definition", required=True, help="Project-relative YAML style definition")
    save.add_argument("--expected-revision", type=int)
    save.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()
    root, project = _project(args)
    if args.command == "list":
        styles = available_styles(project, root)
        result = {
            "styles": [
                {"id": item["id"], "role": item["role"], "label": item["label"], "summary": item["summary"]}
                for item in styles.values()
            ]
        }
    else:
        raw = Path(args.definition).expanduser()
        definition_path = (root / raw).resolve()
        if raw.is_absolute() or not definition_path.is_relative_to(root) or not definition_path.is_file():
            raise ValueError("--definition 必须是项目内已存在的相对路径")
        definition = _load_yaml(definition_path)
        saved = save_project_style(
            project_config=project,
            project_root=root,
            definition=definition,
            confirmed=args.confirmed,
            expected_revision=args.expected_revision,
        )
        result = {"status": "saved", "style_id": saved["id"], "revision": saved["revision"]}
    print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False).strip())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
