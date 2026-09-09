#!/usr/bin/env python3
"""Deterministic structural lint for the dasen wiki (no network, no writes)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path, PurePosixPath
import re
import sys
import unicodedata
from urllib.parse import parse_qsl, urlsplit

from wiki_common import envelope, find_wiki, lint_snapshot, load_frontmatter, page_snapshot, snapshot_digest
from wiki_state import check as state_check

TYPE_DIR = {"sources": "source-summary", "entities": "entity", "topics": "topic", "comparisons": "comparison", "synthesis": "synthesis"}
INDEX_HEADINGS = {"Entities": "entities", "Topics": "topics", "Sources": "sources", "Comparisons": "comparisons", "Synthesis": "synthesis"}
REQUIRED = {"title", "type", "tags", "sources", "related", "confidence", "created", "updated"}
LINK_RE = re.compile(r"!?\[\[([^\[\]\n]+)\]\]")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOKEN_KEYS = re.compile(r"(?:token|key|secret|signature|credential|password|auth)", re.I)


def diag(out: list[dict], severity: str, code: str, path: Path | str, message: str, line: int = 0) -> None:
    out.append({"severity": severity, "code": code, "path": str(path).replace("\\", "/"), "line": line, "message": message})


def clean_markdown(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def link_target(value: str) -> str:
    target = value.split("|", 1)[0].split("#", 1)[0].strip()
    if target.endswith(".md"):
        target = target[:-3]
    return target


def date_value(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime): return value.date()
    if isinstance(value, dt.date): return value
    if isinstance(value, str) and DATE_RE.fullmatch(value):
        try: return dt.date.fromisoformat(value)
        except ValueError: return None
    return None


def valid_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        username, password = parsed.username, parsed.password
    except ValueError:
        return "URL is malformed"
    if parsed.scheme not in {"http", "https"} or not hostname:
        return "URL must use http(s) and include a hostname"
    if username or password:
        return "URL userinfo/credentials are forbidden"
    if any(TOKEN_KEYS.search(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
        return "URL contains a token-like query parameter"
    return None


def raw_locator(value: str) -> tuple[str, tuple[int, int] | None] | None:
    raw, _, fragment = value.partition("#")
    pure = PurePosixPath(raw)
    if not raw.startswith("raw/") or "\\" in raw or pure.is_absolute() or ".." in pure.parts:
        return None
    if not fragment:
        return raw, None
    match = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", fragment)
    if not match:
        return None
    start = int(match.group(1)); end = int(match.group(2) or start)
    if start < 1 or end < start: return None
    return raw, (start, end)


def resolve(target: str, slugs: dict[str, list[Path]], wiki: Path) -> list[Path]:
    known = {path.resolve() for paths in slugs.values() for path in paths}
    if target.startswith("pages/"):
        text = target if target.endswith(".md") else target + ".md"
        if "\\" in text:
            return []
        pure = PurePosixPath(text)
        if pure.is_absolute() or ".." in pure.parts or len(pure.parts) != 3:
            return []
        if pure.parts[0] != "pages" or pure.parts[1] not in TYPE_DIR:
            return []
        path = wiki.joinpath(*pure.parts)
        return [path] if path.resolve() in known and path.is_file() and not path.is_symlink() else []
    if "/" in target or "\\" in target or target in {".", ".."}:
        return []
    key = unicodedata.normalize("NFC", target).casefold()
    return slugs.get(key, [])


def lint(wiki: Path, require_raw: bool = False) -> dict:
    findings: list[dict] = []
    rel = lambda p: p.relative_to(wiki.parent)
    all_page_paths = sorted((wiki / "pages").rglob("*.md"))
    page_paths = []
    for path in all_page_paths:
        parts = path.relative_to(wiki / "pages").parts
        if len(parts) != 2 or parts[0] not in TYPE_DIR:
            diag(findings, "error", "MISPLACED_PAGE", rel(path), "page must be pages/<type>/<slug>.md", 1)
        else:
            page_paths.append(path)
    pages: dict[Path, tuple[dict, str, int]] = {}
    slugs: dict[str, list[Path]] = {}

    for path in page_paths:
        key = unicodedata.normalize("NFC", path.stem).casefold()
        slugs.setdefault(key, []).append(path)
        if not SLUG_RE.fullmatch(path.stem):
            # One historical Chinese source slug is retained until a dedicated content migration.
            diag(findings, "warning", "NON_KEBAB_SLUG", rel(path), "filename is not ASCII kebab-case", 1)
        try:
            pages[path] = load_frontmatter(path)
        except Exception as exc:
            diag(findings, "error", "INVALID_YAML", rel(path), str(exc), 1)

    for key, paths in slugs.items():
        if len(paths) > 1:
            names = ", ".join(str(rel(p)) for p in paths)
            for path in paths:
                diag(findings, "error", "DUPLICATE_SLUG", rel(path), f"slug {path.stem} is also used by: {names}", 1)

    for path, (fm, body, body_line) in pages.items():
        rpath = rel(path)
        missing = sorted(REQUIRED - set(fm))
        for field in missing: diag(findings, "error", "MISSING_FIELD", rpath, f"required field is missing: {field}", 2)
        directory = path.parent.name
        expected = TYPE_DIR.get(directory)
        if fm.get("type") != expected: diag(findings, "error", "TYPE_DIRECTORY_MISMATCH", rpath, f"{directory}/ requires type: {expected}", 3)
        if not isinstance(fm.get("title"), str) or not fm["title"].strip():
            diag(findings, "error", "INVALID_TITLE", rpath, "title must be a nonempty string", 2)
        alias = fm.get("alias")
        if alias is not None and (not isinstance(alias, list) or any(not isinstance(item, str) or not item.strip() for item in alias)):
            diag(findings, "error", "INVALID_ALIAS", rpath, "alias must be a list of nonempty strings", 2)
        for field in ("tags", "sources", "related"):
            value = fm.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                diag(findings, "error", "INVALID_LIST", rpath, f"{field} must be a list of nonempty strings", 2)
            elif not value:
                diag(findings, "error", "EMPTY_LIST", rpath, f"{field} must not be empty", 2)
            elif len(value) != len(set(value)):
                diag(findings, "error", "DUPLICATE_LIST_ITEM", rpath, f"{field} contains duplicate entries", 2)
        if fm.get("confidence") not in {"high", "medium", "low"}:
            diag(findings, "error", "INVALID_CONFIDENCE", rpath, "confidence must be high, medium, or low", 2)
        created, updated = date_value(fm.get("created")), date_value(fm.get("updated"))
        if created is None: diag(findings, "error", "INVALID_DATE", rpath, "created must be YYYY-MM-DD", 2)
        if updated is None: diag(findings, "error", "INVALID_DATE", rpath, "updated must be YYYY-MM-DD", 2)
        if created and updated and created > updated: diag(findings, "error", "DATE_ORDER", rpath, "created must not be after updated", 2)

        sources = fm.get("sources") if isinstance(fm.get("sources"), list) else []
        source_summary_paths: set[Path] = set()
        provenance_identities: set[str] = set()
        page_type = fm.get("type")
        for source in sources:
            if not isinstance(source, str):
                continue
            identity = source
            if source.startswith("[[") and source.endswith("]]" ):
                target = link_target(source[2:-2])
                matches = resolve(target, slugs, wiki)
                if len(matches) != 1:
                    diag(findings, "error", "INVALID_PROVENANCE_LINK", rpath, f"source link is missing or ambiguous: {source}", 2)
                elif pages.get(matches[0], ({}, "", 0))[0].get("type") != "source-summary":
                    diag(findings, "error", "DERIVED_PROVENANCE_LINK", rpath, f"source wikilink must resolve to source-summary: {source}", 2)
                else:
                    source_summary_paths.add(matches[0])
                    identity = f"page:{matches[0].resolve()}"
            elif source.startswith(("http://", "https://")):
                error = valid_url(source)
                if error:
                    diag(findings, "error", "INVALID_SOURCE_URL", rpath, error, 2)
                if date_value(fm.get("checked_at")) is None:
                    diag(findings, "error", "CHECKED_AT_REQUIRED", rpath, "direct URL provenance requires checked_at: YYYY-MM-DD", 2)
                if page_type == "source-summary":
                    diag(findings, "error", "SOURCE_SUMMARY_NOT_MATERIALIZED", rpath, "source-summary must cite immutable raw, not a live URL", 2)
                if page_type == "synthesis":
                    diag(findings, "error", "SYNTHESIS_DIRECT_PROVENANCE", rpath, "synthesis sources must be source-summary wikilinks", 2)
                identity = f"url:{source}"
            else:
                locator = raw_locator(source)
                if locator is None:
                    diag(findings, "error", "INVALID_RAW_LOCATOR", rpath, f"invalid provenance value: {source}", 2)
                else:
                    raw, lines = locator
                    identity = f"raw:{raw}#{lines or ''}"
                    if require_raw:
                        target = wiki / raw
                        if not target.is_file():
                            diag(findings, "error", "RAW_SOURCE_MISSING", rpath, f"raw source does not exist: {raw}", 2)
                        elif lines:
                            count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
                            if lines[1] > count:
                                diag(findings, "error", "RAW_LOCATOR_RANGE", rpath, f"locator exceeds {count} lines: {source}", 2)
                if page_type == "synthesis":
                    diag(findings, "error", "SYNTHESIS_DIRECT_PROVENANCE", rpath, "synthesis sources must be source-summary wikilinks", 2)
            if identity in provenance_identities:
                diag(findings, "error", "DUPLICATE_PROVENANCE", rpath, f"duplicate provenance: {source}", 2)
            provenance_identities.add(identity)
        if page_type == "source-summary" and any(isinstance(item, str) and item.startswith("[[") for item in sources):
            diag(findings, "error", "INDIRECT_SOURCE_SUMMARY", rpath, "source-summary provenance must be raw or URL", 2)
        if page_type == "synthesis":
            mode = fm.get("source_mode")
            count = len(source_summary_paths)
            if mode not in {"single", "multi"}:
                diag(findings, "error", "SOURCE_MODE_REQUIRED", rpath, "synthesis requires source_mode: single|multi", 2)
            if mode == "multi" and count < 2:
                diag(findings, "error", "MULTI_SOURCE_REQUIRED", rpath, "multi synthesis requires at least two distinct source-summary links", 2)
            if mode == "single" and (count != 1 or fm.get("confidence") != "low"):
                diag(findings, "error", "SINGLE_SOURCE_RULE", rpath, "single synthesis requires exactly one source-summary and confidence: low", 2)
            cited_paths = set()
            for match in LINK_RE.finditer(clean_markdown(body)):
                matches = resolve(link_target(match.group(1)), slugs, wiki)
                if len(matches) == 1:
                    cited_paths.add(matches[0])
            for source_path in sorted(source_summary_paths - cited_paths):
                diag(findings, "error", "PROVENANCE_NOT_CITED", rpath, f"synthesis source is not cited in the body: {source_path.stem}", body_line)

        related = fm.get("related") if isinstance(fm.get("related"), list) else []
        nonself = 0
        for value in related:
            if not isinstance(value, str): continue
            match = LINK_RE.fullmatch(value.strip())
            if not match:
                diag(findings, "error", "INVALID_RELATED_LINK", rpath, f"related entry must be one wikilink: {value}", 2); continue
            target = link_target(match.group(1)); matches = resolve(target, slugs, wiki)
            if not matches: diag(findings, "error", "BROKEN_LINK", rpath, f"related target does not exist: {target}", 2)
            elif len(matches) > 1: diag(findings, "error", "AMBIGUOUS_LINK", rpath, f"related target is ambiguous: {target}", 2)
            elif matches[0] != path: nonself += 1
        if related and nonself == 0: diag(findings, "error", "SELF_ONLY_RELATED", rpath, "related must include another page", 2)

        cleaned = clean_markdown(body)
        for line_no, line in enumerate(cleaned.splitlines(), body_line):
            for match in LINK_RE.finditer(line):
                target = link_target(match.group(1)); matches = resolve(target, slugs, wiki)
                if not matches: diag(findings, "error", "BROKEN_LINK", rpath, f"target does not exist: {target}", line_no)
                elif len(matches) > 1: diag(findings, "error", "AMBIGUOUS_LINK", rpath, f"target is ambiguous: {target}", line_no)
            for slug in slugs:
                if f"[{slug}]" in line and f"[[{slug}]]" not in line:
                    diag(findings, "warning", "SINGLE_BRACKET_LINK", rpath, f"possible wikilink uses single brackets: {slug}", line_no)
        prose = re.sub(r"[#>*_`\-\[\]()]", "", cleaned)
        sentences = [s for s in re.split(r"[。！？.!?]\s*", prose) if len(s.strip()) >= 8]
        if len(sentences) < 3: diag(findings, "warning", "THIN_PAGE", rpath, "page has fewer than three substantive sentences")

    # Canonical index bullets under known H2 headings.
    index = wiki / "index.md"; entries: dict[str, list[tuple[str, int]]] = {}
    section = None
    if not index.is_file():
        diag(findings, "error", "INDEX_MISSING", rel(index), "index.md is missing")
    else:
        for line_no, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
            heading = re.fullmatch(r"## ([^#].*)", line)
            if heading: section = INDEX_HEADINGS.get(heading.group(1).split("（", 1)[0].strip()); continue
            match = re.fullmatch(r"- \[\[([^\]|#]+)(?:\|[^\]]+)?\]\]\s+—\s+(.+)", line)
            if match and section:
                target = link_target(match.group(1)); entries.setdefault(target.casefold(), []).append((section, line_no))
                matches = resolve(target, slugs, wiki)
                if not matches: diag(findings, "error", "INDEX_UNKNOWN", rel(index), f"index target does not exist: {target}", line_no)
                elif len(matches) == 1 and matches[0].parent.name != section: diag(findings, "error", "INDEX_WRONG_SECTION", rel(index), f"{target} belongs under {matches[0].parent.name}", line_no)
        for path in page_paths:
            hits = entries.get(path.stem.casefold(), [])
            if not hits: diag(findings, "error", "INDEX_MISSING_PAGE", rel(index), f"page is not indexed: {path.stem}")
            elif len(hits) > 1: diag(findings, "error", "INDEX_DUPLICATE_PAGE", rel(index), f"page is indexed {len(hits)} times: {path.stem}")

    mode = "tracked-only"
    if require_raw:
        report = state_check(wiki); mode = report["mode"]
        findings.extend(report["diagnostics"])
        if report["mode"] == "clone-raw-absent": diag(findings, "error", "RAW_REQUIRED", rel(wiki / "raw"), "strict local lint requires raw and sidecar state")
    elif not (wiki / "raw").exists():
        diag(findings, "info", "SKIP_RAW_ABSENT", rel(wiki / "raw"), "raw existence and locator bounds were skipped")
    ok = not any(d["severity"] == "error" for d in findings)
    snapshot = page_snapshot(wiki)
    return envelope(
        ok,
        mode,
        findings,
        pages=len(page_paths),
        pages_digest=snapshot_digest(snapshot),
        tracked_digest=snapshot_digest(lint_snapshot(wiki)),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-raw", action="store_true")
    parser.add_argument("--strict-warnings", action="store_true")
    args = parser.parse_args()
    try:
        wiki = find_wiki(args.wiki) if args.wiki else find_wiki()
        report = lint(wiki, args.require_raw)
    except Exception as exc:
        report = envelope(False, "tool-error", [{"severity": "error", "code": "TOOL_ERROR", "path": "", "line": 0, "message": str(exc)}])
        code = 2
    else:
        if args.strict_warnings and report["summary"]["warnings"]:
            report["ok"] = False
            report["strict_warnings"] = True
        code = 1 if not report["ok"] else 0
    if args.json: print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{'PASS' if code == 0 else 'FAIL'} [{report['mode']}] errors={report['summary']['errors']} warnings={report['summary']['warnings']} pages={report.get('pages', 0)}")
        for d in report["diagnostics"]: print(f"{d['severity'].upper()} {d['code']} {d.get('path','')}:{d.get('line',0)} {d['message']}")
    return code


if __name__ == "__main__": raise SystemExit(main())
