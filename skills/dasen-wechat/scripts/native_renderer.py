#!/usr/bin/env python3
"""Render Markdown into WeChat-safe inline HTML using dasen-owned rules."""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

import yaml

try:
    from markdown_it import MarkdownIt
except ImportError as exc:  # pragma: no cover - exercised by setup checks
    raise SystemExit("markdown-it-py is required: python3 -m pip install -r requirements.txt") from exc

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer, get_lexer_by_name
    from pygments.style import Style
    from pygments.token import Comment, Error, Generic, Keyword, Literal, Name, Number, Operator, String
except ImportError as exc:  # pragma: no cover - exercised by setup checks
    raise SystemExit("Pygments is required: python3 -m pip install -r requirements.txt") from exc


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.S)
VOID_TAGS = {"br", "hr", "img"}
ALLOWED_TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "figcaption", "figure", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "img", "li", "ol", "p", "pre", "s", "section", "span", "strong",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
DANGEROUS_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "math", "form", "input", "button"}
ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "ol": {"start"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "section": {"aria-label", "data-dasen-code"},
    "span": {"aria-label"},
}
COMMON_ATTRS = {"style"}
ALLOWED_STYLE_PROPERTIES = {
    "align-items", "background", "background-color", "border", "border-bottom", "border-color",
    "border-left", "border-radius", "border-right", "border-style", "border-top", "border-width", "box-shadow",
    "box-sizing", "color", "display", "flex-direction", "font-family", "font-size", "font-style", "font-weight",
    "height", "justify-content", "letter-spacing", "line-height", "margin", "margin-bottom", "margin-left",
    "margin-right", "margin-top", "max-height", "max-width", "min-height", "min-width", "object-fit", "overflow",
    "overflow-x", "overflow-y", "padding", "padding-bottom", "padding-left", "padding-right", "padding-top",
    "table-layout", "text-align", "text-decoration", "text-indent", "text-transform", "vertical-align", "white-space",
    "width", "word-break", "word-wrap",
}


class DasenLightStyle(Style):
    """Small original palette for readable light code blocks."""

    background_color = "#f7f7f8"
    default_style = ""
    styles = {
        Comment: "italic #7a7f87",
        Error: "border:#c53030",
        Keyword: "bold #7c3aed",
        Operator: "#5b6472",
        Name.Builtin: "#9a6700",
        Name.Class: "bold #2563a6",
        Name.Function: "#2563a6",
        Name.Namespace: "#2563a6",
        Name.Tag: "#b42318",
        Name.Attribute: "#8a5d00",
        Literal: "#267a3e",
        String: "#267a3e",
        Number: "#9a6700",
        Generic.Heading: "bold #2563a6",
        Generic.Subheading: "bold #2563a6",
        Generic.Deleted: "#b42318",
        Generic.Inserted: "#267a3e",
    }


@dataclass(frozen=True)
class Article:
    metadata: dict
    markdown: str


@dataclass(frozen=True)
class Theme:
    theme_id: str
    styles: dict[str, str]
    legacy_aliases: tuple[str, ...]


def load_article_text(text: str) -> Article:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return Article({}, text)
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError("article frontmatter must be a mapping")
    return Article(metadata, text[match.end():])


def load_article(path: Path) -> Article:
    return load_article_text(path.read_text(encoding="utf-8"))


def load_theme(theme_dir: Path, requested: str) -> Theme:
    candidates = sorted(theme_dir.glob("*.yaml"))
    for path in candidates:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        theme_id = str(data.get("id") or "")
        aliases = tuple(str(value) for value in data.get("legacy_aliases") or [])
        if requested not in {theme_id, *aliases}:
            continue
        styles = data.get("styles") or {}
        if not isinstance(styles, dict) or "root" not in styles:
            raise ValueError(f"invalid theme: {path}")
        return Theme(theme_id, {str(k): str(v) for k, v in styles.items()}, aliases)
    available = ", ".join(path.stem for path in candidates)
    raise ValueError(f"unknown theme {requested!r}; available: {available}")


def parse_style(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        name = name.strip().lower()
        value = value.strip()
        lowered = value.lower()
        if name not in ALLOWED_STYLE_PROPERTIES or not value:
            continue
        if any(marker in lowered for marker in ("url(", "expression(", "javascript:", "@import", "behavior:")):
            continue
        result[name] = value
    return result


def merge_style(base: str, override: str) -> str:
    values = parse_style(base)
    values.update(parse_style(override))
    return "".join(f"{name}:{value};" for name, value in values.items())


def safe_url(value: str, *, image: bool) -> bool:
    clean = html.unescape(value).strip()
    if not clean or any(ord(char) < 32 for char in clean):
        return False
    if clean.startswith(("https://", "http://")):
        return True
    if not image and clean.startswith("#"):
        return True
    if image and not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", clean) and not clean.startswith("//"):
        return True
    return False


class SafeHtmlInliner(HTMLParser):
    def __init__(self, styles: dict[str, str]):
        super().__init__(convert_charrefs=False)
        self.styles = styles
        self.output: list[str] = []
        self.skip_depth = 0
        self.open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.skip_depth:
            if tag in DANGEROUS_TAGS:
                self.skip_depth += 1
            return
        if tag in DANGEROUS_TAGS:
            self.skip_depth = 1
            return
        if tag not in ALLOWED_TAGS:
            return
        rendered = self._attrs(tag, attrs)
        suffix = " /" if tag in VOID_TAGS else ""
        self.output.append(f"<{tag}{rendered}{suffix}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.skip_depth or tag in DANGEROUS_TAGS or tag not in ALLOWED_TAGS:
            return
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_depth:
            if tag in DANGEROUS_TAGS:
                self.skip_depth -= 1
            return
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS or tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.output.append(f"</{current}>")
            if current == tag:
                break

    def close(self) -> None:
        super().close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.output.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&#{name};")

    def _attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = COMMON_ATTRS | ALLOWED_ATTRS.get(tag, set())
        values: dict[str, str] = {}
        inline_style = ""
        for raw_name, raw_value in attrs:
            name = raw_name.lower()
            value = "" if raw_value is None else raw_value
            if name == "style":
                inline_style = value
                continue
            if name not in allowed or name.startswith("on"):
                continue
            if name == "href" and not safe_url(value, image=False):
                continue
            if name == "src" and not safe_url(value, image=True):
                continue
            if name in {"width", "height", "start", "colspan", "rowspan"} and not re.fullmatch(r"\d{1,4}", value):
                continue
            values[name] = value
        style = merge_style(self.styles.get(tag, ""), inline_style)
        if style:
            values["style"] = style
        return "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in values.items())


def highlight_code(code: str, language: str) -> str:
    aliases = {"shell": "bash", "sh": "bash", "js": "javascript", "ts": "typescript", "yml": "yaml"}
    language = aliases.get(language.lower(), language.lower())
    try:
        lexer = get_lexer_by_name(language) if language else TextLexer()
    except Exception:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=True, noclasses=True, style=DasenLightStyle)
    return highlight(code, lexer, formatter).rstrip("\n")


def code_block_html(code: str, language: str, styles: dict[str, str]) -> str:
    toolbar = styles.get("code_toolbar", "")
    dot = styles.get("code_dot", "")
    container = styles.get("code_container", "")
    pre = merge_style(styles.get("pre", ""), "margin:0;border:0;border-radius:0;")
    code_style = merge_style(
        styles.get("code", ""),
        "display:block;padding:0;background-color:transparent;border-radius:0;font-size:12px;white-space:pre;",
    )
    rendered = highlight_code(code, language)
    dots = "".join(
        f'<span aria-label="{label}" style="{dot}background-color:{color};"></span>'
        for label, color in (("close", "#e66a65"), ("minimize", "#e5b454"), ("expand", "#6bbf6a"))
    )
    return (
        f'<section data-dasen-code="true" style="{container}">'
        f'<section aria-label="代码块工具栏" style="{toolbar}">{dots}</section>'
        f'<pre style="{pre}"><code style="{code_style}">{rendered}</code></pre></section>\n'
    )


def markdown_client(styles: dict[str, str]) -> MarkdownIt:
    client = MarkdownIt("commonmark", {"html": True, "linkify": False, "typographer": False})
    client.enable("table")
    client.enable("strikethrough")

    def fence(renderer, tokens, index, options, env):  # type: ignore[no-untyped-def]
        token = tokens[index]
        language = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ""
        return code_block_html(token.content, language, styles)

    def code_block(renderer, tokens, index, options, env):  # type: ignore[no-untyped-def]
        return code_block_html(tokens[index].content, "", styles)

    client.add_render_rule("fence", fence)
    client.add_render_rule("code_block", code_block)
    return client


def render_markdown(markdown: str, theme: Theme, highlight_theme: str = "dasen-light") -> str:
    if highlight_theme != "dasen-light":
        raise ValueError(f"unknown highlight theme {highlight_theme!r}; available: dasen-light")
    raw = markdown_client(theme.styles).render(markdown)
    inliner = SafeHtmlInliner(theme.styles)
    inliner.feed(raw)
    inliner.close()
    root_style = merge_style(theme.styles["root"], "")
    return (
        f'<section data-dasen-renderer="native-v1" style="{root_style}">'
        + "".join(inliner.output).strip()
        + "</section>"
    )


def image_sources(rendered_html: str) -> list[str]:
    pattern = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.I)
    return list(dict.fromkeys(html.unescape(value) for value in pattern.findall(rendered_html)))


def replace_image_sources(rendered_html: str, replacements: dict[str, str]) -> str:
    pattern = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.I)

    def replace(match: re.Match[str]) -> str:
        original = html.unescape(match.group(2))
        value = replacements.get(original, original)
        return match.group(1) + html.escape(value, quote=True) + match.group(3)

    return pattern.sub(replace, rendered_html)


def render_file(article_path: Path, theme_dir: Path, theme_id: str, highlight_theme: str) -> tuple[Article, Theme, str]:
    article = load_article(article_path)
    theme = load_theme(theme_dir, theme_id)
    return article, theme, render_markdown(article.markdown, theme, highlight_theme)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Markdown with the native dasen WeChat renderer")
    parser.add_argument("--file", "-f", required=True, type=Path)
    parser.add_argument("--theme", "-t", default="dasen-default")
    parser.add_argument("--highlight", "-H", default="dasen-light")
    parser.add_argument("--output", "-o", type=Path, help="Save local HTML instead of printing it")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing output file")
    args = parser.parse_args(argv)
    theme_dir = Path(__file__).resolve().parents[1] / "themes"
    source = args.file.resolve()
    _, _, rendered = render_file(source, theme_dir, args.theme, args.highlight)
    if args.output is None:
        print(rendered)
        return 0
    output = args.output.resolve()
    if output == source:
        raise SystemExit("output must differ from the Markdown input")
    if output.exists() and not args.force:
        raise SystemExit(f"output exists; pass --force to replace it: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"PASS: wrote local WeChat HTML: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
