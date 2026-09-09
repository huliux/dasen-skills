from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_prose.py"


def run(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    article = tmp_path / "article.md"
    article.write_text(body, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(article)], capture_output=True, text=True)


def test_clean_article_passes(tmp_path: Path) -> None:
    result = run(tmp_path, "## 结果\n\n团队在两周内完成测试，记录了输入、步骤和失败条件。\n")
    assert result.returncode == 0
    assert "errors=0" in result.stdout


def test_placeholder_blocks_delivery(tmp_path: Path) -> None:
    result = run(tmp_path, "## 结果\n\n这里补数据，然后再完成这一段。\n")
    assert result.returncode == 1
    assert "unresolved placeholder" in result.stdout


def test_code_and_frontmatter_are_not_linted_as_prose(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        "---\ntitle: TODO\n---\n\n正文说明了已经核验的实际结果。\n\n```text\nTODO\n```\n",
    )
    assert result.returncode == 0
