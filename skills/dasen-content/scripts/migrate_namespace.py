#!/usr/bin/env python3
"""Preview or migrate known configuration values from the Bitbook namespace."""
from __future__ import annotations

import argparse
from copy import deepcopy
import difflib
import os
from pathlib import Path
import sys

import yaml

from migrate_config import atomic_write, is_published_history, parse_document, serialize_document


def migrate_namespace(data: dict) -> dict:
    """Change technical values only; retain product facts and content identity."""
    result = deepcopy(data)
    channels = [result.get("channel")]
    if isinstance(result.get("channels"), dict):
        channels.extend(result["channels"].values())
    for channel in channels:
        if isinstance(channel, dict):
            for field, old, new in (("theme", "bitbook-default", "dasen-default"),
                                    ("highlight", "bitbook-light", "dasen-light")):
                if channel.get(field) == old:
                    channel[field] = new

    styles = [result.get("style_profile")]
    if isinstance(result.get("styles"), dict):
        styles.extend(result["styles"].values())
    visual = result.get("visual")
    if isinstance(visual, dict):
        for role in ("body", "cover"):
            selection = visual.get(role)
            if isinstance(selection, dict):
                styles.append(selection.get("style"))
    for style in styles:
        if isinstance(style, dict) and isinstance(style.get("source"), dict):
            if style["source"].get("kind") == "bitbook-original":
                style["source"]["kind"] = "dasen-original"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Document path relative to the workspace")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true", help="Back up and replace the document")
    args = parser.parse_args()
    try:
        workspace = args.workspace.resolve(strict=True)
        if args.path.is_absolute() or ".." in args.path.parts:
            raise ValueError("input must be a workspace-relative path without '..'")
        candidate = workspace / args.path
        path = candidate.resolve(strict=True)
        if candidate.is_symlink() or not path.is_relative_to(workspace):
            raise ValueError("input must stay inside the workspace and cannot be a symlink")
        original_bytes = path.read_bytes()
        before = original_bytes.decode("utf-8").replace("\r\n", "\n")
        data, body = parse_document(before)
        migrated = migrate_namespace(data)
        if migrated == data:
            print("PASS: no namespace changes needed")
            return 0
        if is_published_history(path, data):
            raise ValueError("delivered/published history is immutable; create a new working copy")
        after = serialize_document(migrated, body)
        if not args.write:
            print("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                  fromfile=str(args.path), tofile=f"{args.path} (dasen namespace)")), end="")
            print("PREVIEW: no files changed")
            return 0
        backup = path.with_name(path.name + ".pre-dasen.bak")
        if path.read_bytes() != original_bytes:
            raise ValueError("input changed during migration; retry after reviewing it")
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(original_bytes)
        atomic_write(path, after)
        print(f"PASS: migrated {args.path}; backup={backup.name}")
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
