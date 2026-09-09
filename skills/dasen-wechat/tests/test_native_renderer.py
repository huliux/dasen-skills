from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from native_renderer import load_article_text, load_theme, render_markdown  # noqa: E402


def theme():
    return load_theme(SKILL_DIR / "themes", "dasen-default")


def test_native_render_inlines_mobile_styles_and_code() -> None:
    markdown = """普通段落包含 **加粗文本**。

## 二级标题

![示例图片](https://example.com/image.png)

<figure><img src="https://example.com/figure.png" alt="结果图" /><figcaption>结果图说明</figcaption></figure>

---

```python
value = 42
```
"""
    rendered = render_markdown(markdown, theme(), "dasen-light")
    assert 'data-dasen-renderer="native-v1"' in rendered
    assert re.search(r'<p style="[^"]*line-height:1\.6', rendered)
    assert re.search(r'<h2 style="[^"]*font-size:1\.3em', rendered)
    assert re.search(r'<h2 style="[^"]*font-weight:500', rendered)
    h2_style = re.search(r'<h2 style="([^"]*)"', rendered).group(1)
    assert "border" not in h2_style and "background" not in h2_style
    assert re.search(r'<img [^>]*style="[^"]*max-width:100%', rendered)
    assert re.search(r'<img [^>]*style="[^"]*border:0', rendered)
    assert re.search(r'<figcaption style="[^"]*font-size:0.9em', rendered)
    assert re.search(r'<hr style="[^"]*border:1px inset #bfbfbf', rendered)
    assert rendered.count("data-dasen-code") == 1
    assert rendered.count('aria-label="close"') == 0
    assert rendered.count('aria-label="minimize"') == 0
    assert rendered.count('aria-label="expand"') == 0
    assert "value" in rendered and "42" in rendered


def test_raw_project_component_is_sanitized_but_preserved() -> None:
    markdown = """<section aria-label="关注指引" onclick="steal()" style="width:26px!important;background-image:url(https://bad.example/a.png)">
<img src="https://example.com/follow.gif" alt="" style="width:26px!important" onerror="steal()" />
<script>alert(1)</script><span>请关注</span>
</section>
"""
    rendered = render_markdown(markdown, theme())
    assert 'aria-label="关注指引"' in rendered
    assert 'src="https://example.com/follow.gif"' in rendered
    assert "width:26px!important" in rendered
    assert "onclick" not in rendered
    assert "onerror" not in rendered
    assert "background-image" not in rendered
    assert "alert(1)" not in rendered


def test_frontmatter_is_separated_from_body() -> None:
    article = load_article_text("---\ntitle: 原创渲染\nauthor: Example Author\n---\n\n正文")
    assert article.metadata["title"] == "原创渲染"
    assert article.markdown.strip() == "正文"
    assert "title:" not in render_markdown(article.markdown, theme())


@pytest.mark.parametrize("legacy", ["default", "mweb-bear-wenyan", "mweb-indigo", "codex-reset-bear-v2"])
def test_legacy_theme_names_require_explicit_migration(legacy: str) -> None:
    with pytest.raises(ValueError, match="unknown theme"):
        load_theme(SKILL_DIR / "themes", legacy)


def test_unsafe_links_and_unknown_themes_fail_closed() -> None:
    rendered = render_markdown("[bad](javascript:alert(1))", theme())
    assert 'href="javascript:' not in rendered
    with pytest.raises(ValueError, match="unknown theme"):
        load_theme(SKILL_DIR / "themes", "unknown")
    with pytest.raises(ValueError, match="unknown highlight"):
        render_markdown("text", theme(), "unknown")


def test_self_closing_safe_and_dangerous_raw_html_stays_balanced() -> None:
    rendered = render_markdown('<span aria-label="empty"/><script/>正文', theme())
    assert '<span aria-label="empty"' in rendered
    assert "</span>" in rendered
    assert "script" not in rendered
    assert "正文" in rendered


def test_unmatched_raw_end_tag_cannot_close_renderer_root() -> None:
    rendered = render_markdown("正文前</section>正文后", theme())
    assert "正文前" in rendered and "正文后" in rendered
    assert rendered.count("<section") == rendered.count("</section>")
    assert rendered.endswith("</section>")


def test_misnested_allowed_tags_are_closed_in_stack_order() -> None:
    rendered = render_markdown("<section><span>正文</section>", theme())
    assert "<section" in rendered and "<span" in rendered
    assert "正文</span></section>" in rendered


def test_cli_can_save_local_html_without_project_configuration(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    output = tmp_path / "exports" / "wechat.html"
    article.write_text("---\ntitle: 本地排版\n---\n\n## 小节\n\n正文\n", encoding="utf-8")
    command = [
        sys.executable, str(SKILL_DIR / "scripts/native_renderer.py"),
        "--file", str(article), "--output", str(output),
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    assert 'data-dasen-renderer="native-v1"' in output.read_text(encoding="utf-8")
    refused = subprocess.run(command, capture_output=True, text=True, check=False)
    assert refused.returncode != 0 and "--force" in refused.stderr
    forced = subprocess.run([*command, "--force"], capture_output=True, text=True, check=False)
    assert forced.returncode == 0, forced.stderr
