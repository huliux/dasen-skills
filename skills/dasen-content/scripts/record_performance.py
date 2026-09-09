#!/usr/bin/env python3
"""Append one comparable, sourced performance snapshot to record.md."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


METRIC_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
PLATFORM_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
NUMBER = re.compile(r"(?:0|[1-9]\d*)(?:\.\d+)?")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Append a sourced platform performance snapshot")
    command.add_argument("--record", required=True, help="Workspace-relative record.md path")
    command.add_argument("--platform", required=True)
    command.add_argument("--captured-at", required=True, help="ISO-8601 timestamp with timezone")
    command.add_argument("--timezone", required=True, help="Platform reporting timezone, e.g. Asia/Shanghai")
    command.add_argument(
        "--source-type", required=True,
        choices=["platform-dashboard", "platform-api", "export", "manual-entry"],
    )
    command.add_argument("--source-ref", required=True, help="Dashboard/export/screenshot locator; never a credential")
    command.add_argument("--window-start", help="Optional ISO-8601 measurement-window start")
    command.add_argument("--window-end", help="Optional ISO-8601 measurement-window end")
    command.add_argument("--metric", action="append", default=[], help="NAME=NON_NEGATIVE_NUMBER")
    command.add_argument("--unit", action="append", default=[], help="NAME=UNIT; required for every metric")
    command.add_argument(
        "--definition", action="append", default=[],
        help="NAME=PLATFORM_DEFINITION; required for every metric",
    )
    command.add_argument("--note", action="append", default=[])
    return command


def parse_timestamp(value: str, field: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} 必须是 ISO-8601 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} 必须包含时区")
    return parsed.isoformat(timespec="seconds")


def parse_pairs(values: list[str], field: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        name, separator, value = item.partition("=")
        name, value = name.strip(), value.strip()
        if not separator or not METRIC_ID.fullmatch(name) or not value:
            raise ValueError(f"{field} 必须使用 NAME=VALUE，NAME 为稳定小写 ID")
        if name in result:
            raise ValueError(f"{field} 重复：{name}")
        result[name] = value
    return result


def metric_value(value: str) -> int | float:
    if not NUMBER.fullmatch(value):
        raise ValueError(f"metric value 必须是非负数字：{value}")
    return float(value) if "." in value else int(value)


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    args = parser().parse_args()
    workspace = Path.cwd().resolve()
    raw_record = Path(args.record).expanduser()
    if raw_record.is_absolute():
        raise SystemExit("[error] --record 必须是当前工作区内相对路径")
    record = (workspace / raw_record).resolve()
    if not record.is_relative_to(workspace) or record.name != "record.md":
        raise SystemExit("[error] --record 必须指向当前工作区内的 record.md")
    if not record.is_file():
        raise SystemExit(f"[error] record 不存在：{args.record}")
    if not PLATFORM_ID.fullmatch(args.platform):
        raise SystemExit("[error] --platform 必须是稳定的小写平台 ID")

    try:
        captured_at = parse_timestamp(args.captured_at, "captured_at")
        if bool(args.window_start) != bool(args.window_end):
            raise ValueError("--window-start/--window-end 必须成对提供")
        window = None
        if args.window_start and args.window_end:
            start = parse_timestamp(args.window_start, "window_start")
            end = parse_timestamp(args.window_end, "window_end")
            if dt.datetime.fromisoformat(start) > dt.datetime.fromisoformat(end):
                raise ValueError("window_start 不能晚于 window_end")
            window = {"start": start, "end": end}
        raw_metrics = parse_pairs(args.metric, "--metric")
        units = parse_pairs(args.unit, "--unit")
        definitions = parse_pairs(args.definition, "--definition")
        if not raw_metrics:
            raise ValueError("至少提供一个 --metric")
        if set(raw_metrics) != set(units) or set(raw_metrics) != set(definitions):
            raise ValueError("每个 metric 必须有同名 --unit 和 --definition")
        metrics = {
            name: {
                "value": metric_value(value),
                "unit": units[name],
                "definition": definitions[name],
            }
            for name, value in raw_metrics.items()
        }
    except ValueError as exc:
        raise SystemExit(f"[error] {exc}") from exc

    source_ref = args.source_ref.strip()
    if not source_ref or any(char in source_ref for char in ("\n", "\r", "\x00")):
        raise SystemExit("[error] --source-ref 不能为空或包含控制字符")
    parsed_ref = urlparse(source_ref)
    if parsed_ref.scheme and parsed_ref.scheme not in {"https"}:
        raise SystemExit("[error] source URL 只接受 HTTPS")
    if parsed_ref.username or parsed_ref.password:
        raise SystemExit("[error] source URL 不得包含凭证")
    source_sha256 = None
    if not parsed_ref.scheme:
        raw_source = Path(source_ref).expanduser()
        if raw_source.is_absolute():
            raise SystemExit("[error] 本地 source-ref 必须是工作区相对路径")
        source_path = (workspace / raw_source).resolve()
        if not source_path.is_relative_to(workspace) or not source_path.is_file():
            raise SystemExit("[error] 本地 source-ref 必须指向工作区内存在的证据文件")
        source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    timezone = args.timezone.strip()
    if not timezone or any(char in timezone for char in ("\n", "\r", "\x00")):
        raise SystemExit("[error] --timezone 无效")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise SystemExit("[error] --timezone 必须是有效 IANA 时区") from exc

    snapshot = {
        "schema_version": 1,
        "platform": args.platform,
        "captured_at": captured_at,
        "timezone": timezone,
        "measurement_window": window,
        "source": {"type": args.source_type, "ref": source_ref, "sha256": source_sha256},
        "metrics": metrics,
        "notes": [note.strip() for note in args.note if note.strip()],
    }
    canonical = yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=True)
    snapshot_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    snapshot["snapshot_id"] = snapshot_id

    original = record.read_text(encoding="utf-8")
    if f"snapshot_id: {snapshot_id}" in original:
        raise SystemExit(f"[error] 相同表现快照已存在：{snapshot_id}")
    block = (
        f"\n## Performance Snapshot · {captured_at}\n\n"
        "```yaml\n"
        + yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False)
        + "```\n"
    )
    atomic_write(record, original.rstrip() + "\n" + block)
    print(yaml.safe_dump({"status": "appended", "record": str(record), "snapshot_id": snapshot_id}, sort_keys=False).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
