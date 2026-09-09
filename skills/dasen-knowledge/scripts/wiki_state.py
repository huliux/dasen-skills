#!/usr/bin/env python3
"""Manage ignored LLM-wiki state without writing beneath wiki/raw."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from wiki_common import (
    atomic_json,
    envelope,
    find_wiki,
    lint_snapshot,
    load_frontmatter,
    page_snapshot,
    sha256,
    snapshot_digest,
    utc_timestamp,
)

STATUS = {"pending", "compiled", "skipped", "obsolete"}
PAGE_DIRS = {"sources", "entities", "topics", "comparisons", "synthesis"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def relkey(wiki: Path, path: Path) -> str:
    return path.relative_to(wiki.parent).as_posix()


def state_path(wiki: Path) -> Path:
    return wiki / ".kb" / "state.json"


def new_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "raw_inputs": {},
        "reflect": {"last_success_at": None, "pages_digest": None, "seen_pages": {}},
        "lint": {
            "last_success_at": None,
            "pages_digest": None,
            "tracked_digest": None,
            "mode": None,
            "errors": None,
            "warnings": None,
        },
    }


def _valid_raw_key(key: str) -> bool:
    if not isinstance(key, str) or "\\" in key:
        return False
    pure = PurePosixPath(key)
    return (
        not pure.is_absolute()
        and ".." not in pure.parts
        and len(pure.parts) >= 3
        and pure.parts[:2] == ("wiki", "raw")
    )


def _valid_page_rel(value: str) -> bool:
    if not isinstance(value, str) or "\\" in value:
        return False
    pure = PurePosixPath(value)
    return (
        not pure.is_absolute()
        and ".." not in pure.parts
        and len(pure.parts) == 3
        and pure.parts[0] == "pages"
        and pure.parts[1] in PAGE_DIRS
        and pure.suffix == ".md"
    )


def _validate_state(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("invalid .kb/state.json schema_version")
    recorded = data.get("raw_inputs")
    if not isinstance(recorded, dict):
        raise ValueError("invalid .kb/state.json raw_inputs")
    for key, item in recorded.items():
        if not _valid_raw_key(key) or not isinstance(item, dict):
            raise ValueError(f"invalid raw state item: {key!r}")
        if not SHA_RE.fullmatch(str(item.get("sha256") or "")):
            raise ValueError(f"invalid raw SHA-256 in state: {key}")
        if item.get("status") not in STATUS:
            raise ValueError(f"invalid raw status in state: {key}")
        if not isinstance(item.get("recorded_at"), str) or not item["recorded_at"]:
            raise ValueError(f"invalid raw timestamp in state: {key}")
        outputs = item.get("outputs")
        if not isinstance(outputs, list) or any(not _valid_page_rel(value) for value in outputs):
            raise ValueError(f"invalid raw outputs in state: {key}")
        if item["status"] == "compiled" and not outputs:
            raise ValueError(f"compiled raw has no outputs in state: {key}")
        if item["status"] in {"skipped", "obsolete"} and not str(item.get("reason") or "").strip():
            raise ValueError(f"{item['status']} raw has no reason in state: {key}")
    reflect = data.get("reflect")
    lint = data.get("lint")
    if not isinstance(reflect, dict) or not isinstance(reflect.get("seen_pages", {}), dict):
        raise ValueError("invalid reflect state")
    for page, digest in reflect.get("seen_pages", {}).items():
        if not _valid_page_rel(page) or not SHA_RE.fullmatch(str(digest or "")):
            raise ValueError(f"invalid reflect page state: {page!r}")
    if not isinstance(lint, dict):
        raise ValueError("invalid lint state")
    for label, value in (
        ("reflect pages_digest", reflect.get("pages_digest")),
        ("lint pages_digest", lint.get("pages_digest")),
        ("lint tracked_digest", lint.get("tracked_digest")),
    ):
        if value is not None and not SHA_RE.fullmatch(str(value)):
            raise ValueError(f"invalid {label}")
    return data


def read_state(wiki: Path) -> dict[str, Any] | None:
    path = state_path(wiki)
    if not path.exists():
        return None
    return _validate_state(json.loads(path.read_text(encoding="utf-8")))


def ensure_state(wiki: Path) -> dict[str, Any]:
    return read_state(wiki) or new_state()


def raw_files(wiki: Path) -> list[Path]:
    root = wiki / "raw"
    if not root.exists():
        return []
    links = sorted(path for path in root.rglob("*") if path.is_symlink())
    if links:
        raise ValueError(f"raw symlink is not allowed: {relkey(wiki, links[0])}")
    return sorted(path for path in root.rglob("*") if path.is_file() and path.name != ".DS_Store")


def canonical_raw(wiki: Path, value: str) -> tuple[str, Path]:
    text = value[5:] if value.startswith("wiki/") else value
    if "\\" in text:
        raise ValueError("raw path must use POSIX separators")
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or len(pure.parts) < 2 or pure.parts[0] != "raw":
        raise ValueError(f"raw path must stay beneath wiki/raw: {value}")
    target = wiki.joinpath(*pure.parts)
    root = (wiki / "raw").resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(root) or target.is_symlink() or not target.is_file():
        raise ValueError(f"raw path is missing, linked, or escapes wiki/raw: {value}")
    return f"wiki/{pure.as_posix()}", target


def canonical_page(wiki: Path, value: str) -> tuple[str, Path]:
    text = value[5:] if value.startswith("wiki/") else value
    if not _valid_page_rel(text):
        raise ValueError(f"output must be pages/<type>/<slug>.md: {value}")
    pure = PurePosixPath(text)
    target = wiki.joinpath(*pure.parts)
    root = (wiki / "pages").resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(root) or target.is_symlink() or not target.is_file():
        raise ValueError(f"output page is missing, linked, or escapes wiki/pages: {value}")
    return pure.as_posix(), target


def direct_raw_keys(page: Path) -> set[str]:
    fm, _, _ = load_frontmatter(page)
    keys = set()
    for source in fm.get("sources") or []:
        if not isinstance(source, str) or not source.startswith("raw/"):
            continue
        raw = source.split("#", 1)[0]
        pure = PurePosixPath(raw)
        if not pure.is_absolute() and ".." not in pure.parts and pure.parts and pure.parts[0] == "raw":
            keys.add(f"wiki/{pure.as_posix()}")
    return keys


def provenance_outputs(wiki: Path) -> dict[str, list[str]]:
    outputs: dict[str, list[str]] = {}
    for page in sorted((wiki / "pages").glob("*/*.md")):
        try:
            keys = direct_raw_keys(page)
        except Exception:
            continue
        for key in keys:
            outputs.setdefault(key, []).append(page.relative_to(wiki).as_posix())
    return outputs


def make_diag(severity: str, code: str, message: str, path: str = "") -> dict:
    return {"severity": severity, "code": code, "path": path, "line": 0, "message": message}


def _compiled_output_diagnostics(wiki: Path, key: str, item: dict[str, Any]) -> list[dict]:
    diagnostics = []
    if item.get("status") != "compiled":
        return diagnostics
    for value in item.get("outputs", []):
        try:
            normalized, page = canonical_page(wiki, value)
        except ValueError as exc:
            diagnostics.append(make_diag("error", "OUTPUT_MISSING", str(exc), value))
            continue
        try:
            provenance = direct_raw_keys(page)
        except Exception as exc:
            diagnostics.append(make_diag("error", "OUTPUT_INVALID", str(exc), normalized))
            continue
        if key not in provenance:
            diagnostics.append(
                make_diag(
                    "error",
                    "OUTPUT_PROVENANCE_MISMATCH",
                    f"compiled output does not directly cite {key}",
                    normalized,
                )
            )
    return diagnostics


def check(wiki: Path) -> dict:
    state = read_state(wiki)
    exists = (wiki / "raw").exists()
    if state is None and not exists:
        return envelope(True, "clone-raw-absent", [make_diag("info", "SKIP_RAW_ABSENT", "raw and state are absent")])
    if state is None:
        return envelope(False, "vault", [make_diag("error", "STATE_MISSING", "raw exists but .kb/state.json is missing")])
    diagnostics = []
    actual = {relkey(wiki, path): path for path in raw_files(wiki)}
    recorded = state["raw_inputs"]
    for key, item in recorded.items():
        path = actual.get(key)
        if path is None:
            diagnostics.append(make_diag("error", "RAW_MISSING", "recorded raw file is missing", key))
        elif sha256(path) != item["sha256"]:
            diagnostics.append(make_diag("error", "RAW_HASH_DRIFT", "recorded raw SHA-256 changed", key))
        diagnostics.extend(_compiled_output_diagnostics(wiki, key, item))
    for key in sorted(set(actual) - set(recorded)):
        diagnostics.append(make_diag("error", "RAW_UNRECORDED", "raw file is not recorded in state", key))
    return envelope(
        not any(item["severity"] == "error" for item in diagnostics),
        "vault",
        diagnostics,
        raw_inputs=len(recorded),
    )


def bootstrap(wiki: Path, import_legacy: bool) -> dict:
    existing = read_state(wiki)
    files = raw_files(wiki)
    if not files and not (wiki / "raw").exists():
        return envelope(
            True,
            "clone-raw-absent",
            [make_diag("info", "SKIP_RAW_ABSENT", "bootstrap made no state because raw is absent")],
            unchanged=True,
        )
    outputs = provenance_outputs(wiki)
    now = utc_timestamp()
    warnings = []
    state = existing or new_state()
    if existing is not None:
        report = check(wiki)
        blockers = [item for item in report["diagnostics"] if item["code"] in {"RAW_MISSING", "RAW_HASH_DRIFT", "OUTPUT_MISSING", "OUTPUT_PROVENANCE_MISMATCH", "OUTPUT_INVALID"}]
        if blockers:
            return envelope(False, "vault", blockers, raw_inputs=len(state["raw_inputs"]))
    added = 0
    for path in files:
        key = relkey(wiki, path)
        if key in state["raw_inputs"]:
            continue
        page_outputs = sorted(set(outputs.get(key, [])))
        status = "compiled" if page_outputs else "pending"
        reason = None
        if import_legacy and not page_outputs and path.suffix.lower() == ".md":
            try:
                fm, _, _ = load_frontmatter(path)
                legacy = fm.get("status")
                if legacy in {"skipped", "obsolete"}:
                    status = legacy
                    reason = "imported legacy status"
                elif legacy == "compiled":
                    warnings.append(make_diag("warning", "LEGACY_COMPILED_UNRESOLVED", "legacy compiled status has no unambiguous output; kept pending", key))
            except Exception:
                warnings.append(make_diag("warning", "LEGACY_METADATA_UNREADABLE", "legacy metadata could not be read; kept pending", key))
        item = {
            "sha256": sha256(path),
            "status": status,
            "recorded_at": now,
            "status_updated_at": now,
            "outputs": page_outputs,
        }
        if reason:
            item["reason"] = reason
        state["raw_inputs"][key] = item
        added += 1
    if added or existing is None:
        atomic_json(state_path(wiki), state)
    return envelope(True, "vault", warnings, raw_inputs=len(state["raw_inputs"]), added=added, unchanged=added == 0, state_file="wiki/.kb/state.json")


def mark(wiki: Path, raw_path: str, status: str, pages: list[str], reason: str | None) -> dict:
    state = read_state(wiki)
    if state is None:
        raise ValueError("state missing; run bootstrap first")
    key, actual = canonical_raw(wiki, raw_path)
    item = state["raw_inputs"].get(key)
    if item is None:
        return envelope(False, "vault", [make_diag("error", "RAW_NOT_SEALED", "path is not recorded; run seal first", key)])
    if sha256(actual) != item["sha256"]:
        return envelope(False, "vault", [make_diag("error", "RAW_HASH_DRIFT", "cannot mark changed raw", key)])
    normalized = []
    for value in pages:
        page_rel, page = canonical_page(wiki, value)
        if key not in direct_raw_keys(page):
            return envelope(
                False,
                "vault",
                [make_diag("error", "OUTPUT_PROVENANCE_MISMATCH", f"output does not directly cite {key}", page_rel)],
            )
        normalized.append(page_rel)
    normalized = sorted(set(normalized))
    if status == "compiled" and not normalized:
        return envelope(False, "vault", [make_diag("error", "OUTPUT_REQUIRED", "compiled requires at least one --page", key)])
    if status in {"skipped", "obsolete"} and not str(reason or "").strip():
        return envelope(False, "vault", [make_diag("error", "REASON_REQUIRED", f"{status} requires --reason", key)])
    item.update(status=status, status_updated_at=utc_timestamp(), outputs=normalized)
    if reason:
        item["reason"] = reason
    else:
        item.pop("reason", None)
    atomic_json(state_path(wiki), state)
    return envelope(True, "vault", [], path=key, status=status, outputs=normalized)


def load_lint_attestation(
    wiki: Path, report_path: Path
) -> tuple[dict[str, Any], dict[str, str], str, str]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    snapshot = page_snapshot(wiki)
    pages_digest = snapshot_digest(snapshot)
    tracked_digest = snapshot_digest(lint_snapshot(wiki))
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("lint report has an invalid schema")
    if report.get("ok") is not True or (report.get("summary") or {}).get("errors") != 0:
        raise ValueError("lint report is not a passing attestation")
    if report.get("pages") != len(snapshot) or report.get("pages_digest") != pages_digest:
        raise ValueError("lint report does not match the current tracked pages")
    if report.get("tracked_digest") != tracked_digest:
        raise ValueError("lint report does not match the current index and pages")
    return report, snapshot, pages_digest, tracked_digest


def record_lint(wiki: Path, report_path: Path) -> dict:
    report, _, pages_digest, tracked_digest = load_lint_attestation(wiki, report_path)
    state = ensure_state(wiki)
    state["lint"] = {
        "last_success_at": utc_timestamp(),
        "pages_digest": pages_digest,
        "tracked_digest": tracked_digest,
        "mode": report.get("mode"),
        "errors": report["summary"]["errors"],
        "warnings": report["summary"]["warnings"],
    }
    atomic_json(state_path(wiki), state)
    return envelope(
        True,
        "vault" if (wiki / "raw").exists() else "tracked-only",
        [],
        pages_digest=pages_digest,
        tracked_digest=tracked_digest,
        state_file="wiki/.kb/state.json",
    )


def unseen(wiki: Path) -> dict:
    state = read_state(wiki)
    current = page_snapshot(wiki)
    seen = ((state or {}).get("reflect") or {}).get("seen_pages") or {}
    changed = sorted(path for path, digest in current.items() if seen.get(path) != digest)
    deleted = sorted(set(seen) - set(current))
    return envelope(True, "vault" if state else "tracked-only", [], changed=changed, deleted=deleted)


def record_reflect(wiki: Path, report_path: Path, pages: list[str]) -> dict:
    _, snapshot, digest, _ = load_lint_attestation(wiki, report_path)
    state = ensure_state(wiki)
    previous = (state.get("reflect") or {}).get("seen_pages") or {}
    changed = sorted(path for path, value in snapshot.items() if previous.get(path) != value)
    declared = []
    for value in pages:
        page_rel, _ = canonical_page(wiki, value)
        declared.append(page_rel)
    if declared and any(path not in changed for path in declared):
        raise ValueError("--page must name a page changed since the previous successful reflect")
    state["reflect"] = {
        "last_success_at": utc_timestamp(),
        "pages_digest": digest,
        "seen_pages": snapshot,
        "changed_pages": sorted(set(declared or changed)),
    }
    atomic_json(state_path(wiki), state)
    return envelope(True, "vault" if (wiki / "raw").exists() else "tracked-only", [], pages_digest=digest, changed=state["reflect"]["changed_pages"], state_file="wiki/.kb/state.json")


def emit(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{'PASS' if report['ok'] else 'FAIL'} [{report['mode']}] errors={report['summary']['errors']} warnings={report['summary']['warnings']}")
        for item in report["diagnostics"]:
            print(f"{item['severity'].upper()} {item['code']} {item.get('path', '')}: {item['message']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str) -> argparse.ArgumentParser:
        item = sub.add_parser(name)
        item.add_argument("--wiki", type=Path)
        item.add_argument("--json", action="store_true")
        return item

    boot = command("bootstrap")
    boot.add_argument("--import-legacy-status", action="store_true")
    seal = command("seal")
    seal.add_argument("--import-legacy-status", action="store_true")
    command("check")
    command("unseen")
    listing = command("list")
    listing.add_argument("--status", choices=sorted(STATUS))
    marking = command("mark")
    marking.add_argument("--path", required=True)
    marking.add_argument("--status", choices=sorted(STATUS - {"pending"}), required=True)
    marking.add_argument("--page", action="append", default=[])
    marking.add_argument("--reason")
    linting = command("record-lint")
    linting.add_argument("--report", type=Path, required=True)
    reflecting = command("record-reflect")
    reflecting.add_argument("--report", type=Path, required=True)
    reflecting.add_argument("--page", action="append", default=[])
    args = parser.parse_args()
    try:
        wiki = find_wiki(args.wiki) if args.wiki else find_wiki()
        if args.command == "check":
            report = check(wiki)
        elif args.command in {"bootstrap", "seal"}:
            report = bootstrap(wiki, args.import_legacy_status)
        elif args.command == "mark":
            report = mark(wiki, args.path, args.status, args.page, args.reason)
        elif args.command == "record-lint":
            report = record_lint(wiki, args.report)
        elif args.command == "record-reflect":
            report = record_reflect(wiki, args.report, args.page)
        elif args.command == "unseen":
            report = unseen(wiki)
        else:
            state = read_state(wiki)
            items = [] if state is None else [
                {"path": key, **value}
                for key, value in sorted(state["raw_inputs"].items())
                if not args.status or value.get("status") == args.status
            ]
            report = envelope(True, "vault" if state else "clone-raw-absent", [], items=items)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        report = envelope(False, "tool-error", [make_diag("error", "TOOL_ERROR", str(exc))])
        emit(report, args.json)
        return 2
    emit(report, args.json)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
