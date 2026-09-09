#!/usr/bin/env python3
"""Prepare project-controlled inputs for native WeChat delivery."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml


CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))

from project_config import channel_config, load_project_reference  # noqa: E402


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def load_yaml_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    return yaml.safe_load(match.group(1)) or {} if match else {}


def workspace_root_for(bundle: Path) -> Path:
    return next(
        (p for p in [bundle, *bundle.parents] if (p / ".git").exists() or (p / "project.md").is_file()),
        bundle,
    )


def load_bundle_config(bundle: Path) -> tuple[Path, dict, dict]:
    brief = yaml.safe_load((bundle / "brief.yaml").read_text(encoding="utf-8")) or {}
    if "project_root" in brief:
        raise SystemExit("project_root was renamed to workspace_root; run migrate_config.py")
    root_ref = str(brief.get("workspace_root") or "").strip()
    if root_ref:
        raw_root = Path(root_ref)
        root = (bundle / raw_root).resolve() if not raw_root.is_absolute() else raw_root
        if raw_root.is_absolute() or not bundle.is_relative_to(root):
            raise SystemExit("workspace_root must be a workspace-ancestor relative path")
    else:
        root = workspace_root_for(bundle)
    project_ref = str(brief.get("project_file") or "").strip()
    project = {}
    if project_ref:
        try:
            _, project = load_project_reference(project_ref, root)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    return root, brief, project


def channel_options(brief: dict, project: dict) -> tuple[str, str]:
    project_channel = channel_config(project, str(brief.get("platform") or "wechat"))
    brief_channel = brief.get("channel") or {}
    if not isinstance(brief_channel, dict):
        raise SystemExit("brief.channel must be a mapping")
    values = []
    for key in ("theme", "highlight"):
        value = str(brief_channel.get(key) or project_channel.get(key) or "").strip()
        if value and not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise SystemExit(f"channel.{key} contains unsupported characters: {value!r}")
        values.append(value)
    return values[0], values[1]


def replace_headings(source: str, *, level: int, template: str, values: dict[str, str]) -> tuple[str, int]:
    marker = "#" * level
    heading_re = re.compile(rf"^ {{0,3}}{re.escape(marker)}(?!#)\s+(.+?)\s*$")
    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    in_fence = False
    fence_char = ""
    output: list[str] = []
    count = 0

    for line in source.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        fence = fence_re.match(bare)
        if fence:
            char = fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = char
            elif char == fence_char:
                in_fence = False
                fence_char = ""
            output.append(line)
            continue

        match = None if in_fence else heading_re.match(bare)
        if not match:
            output.append(line)
            continue

        title = re.sub(r"\s+#+\s*$", "", match.group(1)).strip()
        if not title:
            raise ValueError(f"empty level-{level} heading")
        rendered = template
        replacements = {**values, "title": html.escape(title, quote=False)}
        for key, value in replacements.items():
            rendered = rendered.replace("{{" + key + "}}", html.escape(value, quote=True) if key != "title" else value)
        if re.search(r"{{[a-z_]+}}", rendered):
            raise ValueError("section heading template contains unresolved placeholders")
        output.append(rendered.rstrip() + "\n")
        count += 1

    return "".join(output), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--article", type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-channel-options", action="store_true")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    root, brief, project = load_bundle_config(bundle)
    if args.print_channel_options:
        print("\n".join(channel_options(brief, project)))
        return 0
    if args.article is None or args.output is None:
        parser.error("--article and --output are required unless --print-channel-options is used")

    article = args.article.resolve()
    output = args.output.resolve()
    source = article.read_text(encoding="utf-8")
    rule = ((project.get("hard_rules") or {}).get("section_heading") or {})

    if not rule.get("required"):
        output.write_text(source, encoding="utf-8")
        print("section-heading: disabled")
        return 0

    level = int(rule.get("level") or 2)
    if level < 2 or level > 6:
        raise SystemExit("section_heading.level must be between 2 and 6")
    template_path = (root / str(rule.get("template") or "")).resolve()
    if not template_path.is_relative_to(root) or not template_path.is_file():
        raise SystemExit(f"section heading template not found under project root: {template_path}")
    image_url = str(rule.get("image_url") or "")
    if not re.match(r"^https://", image_url):
        raise SystemExit("section_heading.image_url must be an HTTPS URL")
    marker = str(rule.get("marker") or "").strip()
    if not marker:
        raise SystemExit("section_heading.marker is required")

    template = template_path.read_text(encoding="utf-8")
    required = ("{{title}}", "{{marker}}", "{{image_url}}", "{{image_alt}}")
    missing = [token for token in required if token not in template]
    if missing:
        raise SystemExit("section heading template missing placeholders: " + ", ".join(missing))

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
    output.write_text(transformed, encoding="utf-8")
    print(f"section-heading: transformed {count} level-{level} heading(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
