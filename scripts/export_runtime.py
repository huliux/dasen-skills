"""Export runtime-only hashed requirements from the canonical uv lock."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

HEADER = "# Generated from uv.lock by scripts/export_runtime.py; do not edit.\n"


def exported(root: Path) -> str:
    result = subprocess.run(
        ["uv", "export", "--locked", "--offline", "--no-dev", "--no-emit-project",
         "--no-header", "--no-annotate"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise ValueError("cannot export locked runtime requirements: " + result.stderr.strip()[-2000:])
    return HEADER + result.stdout


def verify(root: Path) -> None:
    if (root / "requirements.txt").read_text(encoding="utf-8") != exported(root):
        raise ValueError("requirements.txt is stale; run python scripts/export_runtime.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.check:
        verify(root)
    else:
        (root / "requirements.txt").write_text(exported(root), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
