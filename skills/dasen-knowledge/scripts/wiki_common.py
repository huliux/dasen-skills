#!/usr/bin/env python3
"""Shared deterministic helpers for dasen wiki tools."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required") from exc


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader: yaml.Loader, node: yaml.Node, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise yaml.constructor.ConstructorError("mapping", node.start_mark, f"duplicate key: {key}", key_node.start_mark)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_frontmatter(path: Path) -> tuple[dict[str, Any], str, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start on line 1")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("frontmatter has no closing delimiter") from exc
    data = yaml.load("\n".join(lines[1:end]), Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, "\n".join(lines[end + 1 :]), end + 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def page_snapshot(wiki: Path) -> dict[str, str]:
    """Return stable hashes for canonical two-level wiki pages."""
    return {
        path.relative_to(wiki).as_posix(): sha256(path)
        for path in sorted((wiki / "pages").glob("*/*.md"))
        if path.is_file() and not path.is_symlink()
    }


def snapshot_digest(snapshot: dict[str, str]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def lint_snapshot(wiki: Path) -> dict[str, str]:
    """Hash every tracked input whose content affects structural lint."""
    snapshot = page_snapshot(wiki)
    index = wiki / "index.md"
    if index.is_file():
        snapshot["index.md"] = sha256(index)
    return snapshot


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def find_wiki(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.name == "wiki" and (current / "schema.md").is_file():
        return current
    for candidate in (current, *current.parents):
        wiki = candidate / "wiki"
        if (wiki / "schema.md").is_file():
            return wiki
    raise FileNotFoundError("could not find wiki/schema.md")


def envelope(ok: bool, mode: str, diagnostics: list[dict], **extra: Any) -> dict:
    order = {"error": 0, "warning": 1, "info": 2}
    diagnostics.sort(key=lambda d: (order.get(d["severity"], 9), d["code"], d.get("path", "").casefold(), d.get("line", 0), d["message"]))
    summary = {
        "errors": sum(d["severity"] == "error" for d in diagnostics),
        "warnings": sum(d["severity"] == "warning" for d in diagnostics),
        "skipped": sum(d["severity"] == "info" and d["code"].startswith("SKIP") for d in diagnostics),
    }
    return {"schema_version": 1, "ok": ok, "mode": mode, "summary": summary, "diagnostics": diagnostics, **extra}
