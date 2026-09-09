"""Validate a complete release artifact without importing its runtime packages."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

PUBLIC_SKILLS = (
    "dasen-content", "dasen-research", "dasen-writing",
    "dasen-knowledge", "dasen-visual", "dasen-wechat",
)
ROOT_FILES = ("LICENSE", "ORIGIN.md", "THIRD_PARTY.md", "requirements.txt",
              "registry.yaml", "packs.yaml", "README.md", "prepare-macos.sh")


def regular_file(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if (not relative or path.is_absolute() or ".." in path.parts
            or "\\" in relative or ":" in relative or path.as_posix() != relative):
        raise ValueError(f"unsafe artifact path: {relative!r}")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"artifact link is not supported: {relative}")
    if not target.is_file():
        raise ValueError(f"missing artifact file: {relative}")
    return target


def inspect_distribution(root: Path) -> dict:
    errors = []
    required = [*ROOT_FILES, *(f"skills/{name}/SKILL.md" for name in PUBLIC_SKILLS)]
    for relative in required:
        try:
            regular_file(root, relative)
        except ValueError as exc:
            errors.append(str(exc))
    manifest_path = root / "artifact-manifest.json"
    if not manifest_path.exists():
        return {"status": "blocked", "errors": [*errors, "missing artifact-manifest.json"],
                "source_revision": None}
    try:
        regular_file(root, "artifact-manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("artifact manifest must be an object")
        if manifest.get("schema_version") != 1 or manifest.get("kind") not in {"source", "install"}:
            raise ValueError("unsupported artifact manifest schema or kind")
        revision = manifest.get("source_revision")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            raise ValueError("manifest has no full source revision")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("manifest files must be a nonempty object")
        for relative in required:
            if relative not in files:
                errors.append(f"required file absent from manifest: {relative}")
        for relative, digest in files.items():
            if relative == "artifact-manifest.json":
                raise ValueError("manifest cannot include itself")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"invalid SHA-256 for {relative}")
            path = regular_file(root, relative)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append(f"hash mismatch: {relative}")
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                errors.append(f"unexpected artifact link: {relative}")
            elif path.is_file() and relative != "artifact-manifest.json" and relative not in files:
                errors.append(f"unlisted artifact file: {relative}")
        actual = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
        if actual != set(PUBLIC_SKILLS):
            errors.append("artifact must contain exactly the six public Skills")
        return {"status": "blocked" if errors else "ready", "errors": list(dict.fromkeys(errors)),
                "kind": manifest["kind"], "source_revision": revision,
                "file_count": len(files),
                "assurance": "file consistency only; release origin must be verified separately"}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {"status": "blocked", "errors": list(dict.fromkeys([*errors, str(exc)])),
                "source_revision": None}
