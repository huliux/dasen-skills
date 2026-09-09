#!/usr/bin/env python3
"""Deterministic review hints for dasen Chinese non-fiction drafts."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PLACEHOLDERS = (
    re.compile(r"(?:TODO|TBD|FIXME)", re.I),
    re.compile(r"\[(?:待补|待确认|补充来源|插图)[^\]]*\]"),
    re.compile(r"(?:这里|此处)(?:补|插入)(?:图|数据|案例|来源)"),
)
UNSUPPORTED_CERTAINTY = ("毫无疑问", "显然", "必然会", "彻底解决", "完全取代", "100%")
REPORT_JARGON = ("赋能", "抓手", "组合拳", "降本增效", "价值闭环", "认知跃迁")
TEMPLATE_TURNS = (
    re.compile(r"不是[^。！？\n]{1,80}而是"),
    re.compile(r"并非[^。！？\n]{1,80}而是"),
    re.compile(r"看似[^。！？\n]{1,80}(?:实则|其实)"),
)


def mask_non_prose(text: str) -> str:
    """Preserve offsets while hiding frontmatter, code, links and HTML tags."""
    patterns = (
        re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.S),
        re.compile(r"```.*?```", re.S),
        re.compile(r"`[^`\n]*`"),
        re.compile(r"https?://[^\s)>]+"),
        re.compile(r"<[^>\n]+>"),
    )

    def blank(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group())

    for pattern in patterns:
        text = pattern.sub(blank, text)
    return text


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def paragraphs(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    cursor = 0
    for block in re.split(r"\n\s*\n", text):
        start = text.find(block, cursor)
        cursor = max(cursor, start + len(block))
        clean = re.sub(r"^[#>*+\-\d.、\s]+", "", block).strip()
        if len(re.findall(r"[\u4e00-\u9fff]", clean)) >= 8:
            found.append((start, clean))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 dasen 中文非虚构成稿")
    parser.add_argument("path", help="Markdown/text path, or - for stdin")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR read: {exc}", file=sys.stderr)
        return 2

    prose = mask_non_prose(raw)
    if not re.search(r"[\u4e00-\u9fff]", prose):
        print("ERROR no Chinese prose found")
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    for pattern in PLACEHOLDERS:
        for match in pattern.finditer(prose):
            errors.append(f"line {line_at(raw, match.start())}: unresolved placeholder {match.group()!r}")
    for term in UNSUPPORTED_CERTAINTY:
        for match in re.finditer(re.escape(term), prose):
            warnings.append(f"line {line_at(raw, match.start())}: verify certainty {term!r}")
    for term in REPORT_JARGON:
        for match in re.finditer(re.escape(term), prose):
            warnings.append(f"line {line_at(raw, match.start())}: replace report jargon {term!r} with a concrete action/result")
    for pattern in TEMPLATE_TURNS:
        for match in pattern.finditer(prose):
            warnings.append(f"line {line_at(raw, match.start())}: review template-like turn {match.group()[:48]!r}")

    blocks = paragraphs(prose)
    for (left_line, left), (right_line, right) in zip(blocks, blocks[1:]):
        left_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", left))
        right_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", right))
        if left_terms and right_terms and left_terms == right_terms:
            warnings.append(f"line {line_at(raw, right_line)}: adjacent paragraph may repeat the same wording")
    for start, block in blocks:
        han = len(re.findall(r"[\u4e00-\u9fff]", block))
        if han > 220 and len(re.findall(r"[。！？!?]", block)) < 3:
            warnings.append(f"line {line_at(raw, start)}: dense paragraph ({han} Chinese characters)")

    for item in errors:
        print(f"ERROR {item}")
    for item in warnings:
        print(f"WARN {item}")
    print(f"SUMMARY errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
