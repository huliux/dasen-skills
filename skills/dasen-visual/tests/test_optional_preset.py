from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "render_topic_cover.py"


def test_topic_cover_renderer_requires_explicit_optional_preset() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", "missing.png"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--preset" in result.stderr
