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
