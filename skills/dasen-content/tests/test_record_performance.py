from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/record_performance.py"


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd,
        capture_output=True, text=True, check=False,
    )


def common_args() -> list[str]:
    return [
        "--record", "writing/item/record.md",
        "--platform", "wechat",
        "--captured-at", "2026-09-08T10:00:00+08:00",
        "--timezone", "Asia/Shanghai",
        "--source-type", "platform-dashboard",
        "--source-ref", "assets/performance/wechat-day-1.png",
        "--window-start", "2026-09-07T10:00:00+08:00",
        "--window-end", "2026-09-08T10:00:00+08:00",
        "--metric", "views=123",
        "--unit", "views=count",
        "--definition", "views=平台后台所示阅读次数",
    ]


def test_appends_sourced_comparable_snapshot_and_rejects_duplicate(tmp_path: Path) -> None:
    record = tmp_path / "writing/item/record.md"
    record.parent.mkdir(parents=True)
    record.write_text("---\ncontent_id: example\n---\n\n# Record\n", encoding="utf-8")
    evidence = tmp_path / "assets/performance/wechat-day-1.png"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"dashboard screenshot fixture")

    first = run(tmp_path, *common_args())
    assert first.returncode == 0, first.stderr
    text = record.read_text(encoding="utf-8")
    assert "platform: wechat" in text
    assert "captured_at: '2026-09-08T10:00:00+08:00'" in text
    assert "type: platform-dashboard" in text
    assert "sha256:" in text
    assert "definition: 平台后台所示阅读次数" in text

    before = record.read_bytes()
    duplicate = run(tmp_path, *common_args())
    assert duplicate.returncode != 0 and "已存在" in duplicate.stderr
    assert record.read_bytes() == before


def test_requires_platform_definition_and_preserves_record_on_failure(tmp_path: Path) -> None:
    record = tmp_path / "writing/item/record.md"
    record.parent.mkdir(parents=True)
    record.write_text("# Record\n", encoding="utf-8")
    evidence = tmp_path / "assets/performance/wechat-day-1.png"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"dashboard screenshot fixture")
    args = common_args()
    definition_index = args.index("--definition")
    del args[definition_index:definition_index + 2]

    before = record.read_bytes()
    result = run(tmp_path, *args)
    assert result.returncode != 0 and "每个 metric" in result.stderr
    assert record.read_bytes() == before


def test_rejects_record_path_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-record.md"
    outside.write_text("# Record\n", encoding="utf-8")
    args = common_args()
    args[1] = f"../{outside.name}"
    before = outside.read_bytes()
    result = run(tmp_path, *args)
    assert result.returncode != 0 and "工作区" in result.stderr
    assert outside.read_bytes() == before


def test_rejects_unknown_reporting_timezone(tmp_path: Path) -> None:
    record = tmp_path / "writing/item/record.md"
    record.parent.mkdir(parents=True)
    record.write_text("# Record\n", encoding="utf-8")
    evidence = tmp_path / "assets/performance/wechat-day-1.png"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"dashboard screenshot fixture")
    args = common_args()
    args[args.index("--timezone") + 1] = "Unknown/Timezone"
    before = record.read_bytes()
    result = run(tmp_path, *args)
    assert result.returncode != 0 and "IANA" in result.stderr
    assert record.read_bytes() == before
