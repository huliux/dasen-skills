#!/usr/bin/env python3
"""Create an optional compatible wiki without replacing existing files."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))
from content_paths import contained, select_content_root


def initialize(root: Path) -> Path:
    wiki = contained(root.resolve(), "wiki", "wiki")
    wiki.mkdir()  # Refuse even an existing empty directory.
    try:
        template = Path(__file__).resolve().parents[1] / "templates/schema.md"
        (wiki / "schema.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        (wiki / "index.md").write_text("# Wiki Index\n\n" + "\n\n".join("## " + name for name in ("Entities", "Topics", "Sources", "Comparisons", "Synthesis")) + "\n", encoding="utf-8")
        (wiki / "log.md").write_text("# Wiki Log\n", encoding="utf-8")
        (wiki / ".gitignore").write_text("/raw/\n/.kb/\n", encoding="utf-8")
        for name in ("sources", "entities", "topics", "comparisons", "synthesis"):
            (wiki / "pages" / name).mkdir(parents=True)
    except Exception:
        shutil.rmtree(wiki)
        raise
    return wiki


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-root", help="Workspace-relative content directory")
    args = parser.parse_args()
    root = select_content_root(Path.cwd(), args.content_root)
    root.mkdir(parents=True, exist_ok=True)
    print(initialize(root))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
