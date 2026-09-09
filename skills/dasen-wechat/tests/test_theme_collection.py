from html.parser import HTMLParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_renderer import load_theme, render_markdown, image_sources

THEMES = Path(__file__).resolve().parents[1] / 'themes'
SAMPLE = '''## A long explanatory heading

A paragraph with **a supported conclusion**, a [source](https://example.com) and `inline_code`.

> A quotation with a stated boundary.

1. First step
2. Second step

| Item | Result |
| --- | --- |
| Example | Verified |

```python
print("hello")
```

![Evidence](../../../assets/sample.png)

<script>alert(1)</script>
'''

class Structure(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


def test_three_themes_preserve_content_structure_and_image_references():
    results = []
    for name in ('dasen-default', 'dasen-reading', 'dasen-document'):
        rendered = render_markdown(SAMPLE, load_theme(THEMES, name))
        parser = Structure(); parser.feed(rendered)
        assert parser.tags.count('h2') == 1
        assert parser.tags.count('table') == 1
        assert parser.tags.count('pre') == 1
        assert 'script' not in parser.tags
        assert image_sources(rendered) == ['../../../assets/sample.png']
        assert 'background-color:#ffffff' in rendered
        assert 'background-image' not in rendered and 'box-shadow' not in rendered.replace('box-shadow:none;', '')
        results.append(rendered)
    assert len(set(results)) == 3


def test_theme_conversion_preserves_selected_metrics_and_safe_css():
    from native_renderer import parse_style
    assert parse_style('border-collapse:collapse;border-spacing:0;list-style-type:disc;background:url(evil)') == {
        'border-collapse': 'collapse', 'border-spacing': '0', 'list-style-type': 'disc'}
    for alias, canonical, size, keyword in (
        ('mweb-bear', 'dasen-default', '14.4px', '#2478C5'),
        ('mweb-lark', 'dasen-document', '14px', '#07A'),
        ('mweb-typo', 'dasen-reading', '14px', '#277FBE'),
    ):
        theme = load_theme(THEMES, alias)
        assert theme.theme_id == canonical
        output = render_markdown('## Heading\n\n<mark>Marked</mark>\n\n```python\nfor value in range(2):\n    print(value)\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |', theme)
        assert f'font-size:{size}' in output
        assert 'font-size:12px' not in output
        assert 'border-collapse:collapse' in output
        assert '代码块工具栏' not in output
        assert '<mark style=' in output
        assert keyword.lower() in output.lower()
        assert 'padding' in parse_style(theme.styles['root'])


def test_context_styles_reset_nested_blocks_without_flattening_structure():
    output = render_markdown('> A quote\n\n- Parent\n  - Child', load_theme(THEMES, 'mweb-bear'))
    assert 'margin:0;' in output
    assert 'list-style-type:circle' in output
    assert output.count('<ul ') == 2
