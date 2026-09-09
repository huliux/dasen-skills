"""Resolve owned content paths without moving existing content or delivery state."""
from __future__ import annotations

from pathlib import Path
import re

import yaml


def contained(root: Path, reference: str, label: str) -> Path:
    raw = Path(reference)
    if not reference or reference.startswith("@") or raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"{label} 必须位于项目根目录内，使用不含 .. 的相对路径")
    path = (root / raw).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{label} escapes its content root")
    return path


def content_project_metadata(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        return {}
    match = re.match(r"^---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
    try:
        data = yaml.safe_load(match.group(1)) if match else {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) and data.get("project") else {}


def select_content_root(workspace: Path, requested: str | None = None, project_file: str | None = None) -> Path:
    """Explicit choice, existing content, then isolated source-workspace default."""
    workspace = workspace.resolve()
    if requested is not None:
        return contained(workspace, requested, "content root")
    if project_file:
        project = contained(workspace, project_file, "project file")
        config = content_project_metadata(project)
        return contained(workspace, str(config.get("content_root") or "."), "project.content_root")
    if content_project_metadata(workspace / "project.md") or any(
        content_project_metadata(path) for path in (workspace / "projects").glob("*/project.md")
    ) or any((workspace / "writing").glob("*/*/brief.yaml")) or any((workspace / "writing").glob("*/*.md")) or (workspace / "wiki/schema.md").is_file():
        return workspace
    nested = workspace / "content"
    if content_project_metadata(nested / "project.md") or any((nested / "writing").glob("*/*/brief.yaml")) or (nested / "wiki/schema.md").is_file():
        return contained(workspace, "content", "content root")
    markers = (".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml", "CMakeLists.txt")
    return contained(workspace, "content" if any((workspace / marker).exists() for marker in markers) else ".", "content root")


def control_reference(workspace: Path, content_root: Path, reference: str | None) -> str | None:
    """CLI control-document references remain relative to the host workspace."""
    if not reference:
        return None
    path = contained(workspace, reference, "control document")
    if not path.is_relative_to(content_root):
        raise ValueError("control document must be inside the selected content root")
    return path.relative_to(content_root).as_posix()


def bundle_root(bundle: Path, brief: dict) -> Path:
    """Read legacy workspace roots and the explicit content root of new bundles."""
    bundle = bundle.resolve()
    reference = brief.get("workspace_root")
    if reference:
        raw = Path(str(reference))
        workspace = (bundle / raw).resolve()
        if raw.is_absolute() or not bundle.is_relative_to(workspace):
            raise ValueError("workspace_root must be a workspace-ancestor relative path")
    else:
        if brief.get("layout_version", 1) != 1:
            raise ValueError("new bundles require workspace_root")
        workspace = next((p for p in (bundle, *bundle.parents) if (p / ".git").exists() or (p / "project.md").is_file()), bundle)
    root = contained(workspace, str(brief.get("content_root") or "."), "brief.content_root")
    if not bundle.is_relative_to(root):
        raise ValueError("bundle must be inside its frozen content root")
    return root


def evidence_dir(bundle: Path, brief: dict | None = None) -> Path:
    """Choose one layout, never guess from which directory happens to exist."""
    bundle = bundle.resolve()
    if brief is None:
        path = bundle / "brief.yaml"
        brief = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if not isinstance(brief, dict):
        raise ValueError("brief must be a mapping")
    version = brief.get("layout_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("unsupported layout_version; expected 1 (assets) or 2 (evidence)")
    name, other = ("assets", "evidence") if version == 1 else ("evidence", "assets")
    directory = contained(bundle, name, "bundle evidence directory")
    # A second state file must never bypass an uncertain or pending draft request.
    alternate = bundle / other / "delivery.json"
    if alternate.exists() or alternate.is_symlink():
        raise ValueError("delivery state conflicts with layout_version; reconcile before delivery")
    state = directory / "delivery.json"
    if state.is_symlink():
        raise ValueError("delivery state must not be a symlink")
    return directory
