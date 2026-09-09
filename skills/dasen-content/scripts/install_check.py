#!/usr/bin/env python3
"""Check a complete artifact and convert a bundled sample without model or network calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

from install_dependencies import inspect_dependencies
from install_integrity import inspect_distribution


def local_conversion(root: Path, output: Path) -> dict:
    source = root / "skills/dasen-content/references/install-sample.md"
    renderer = root / "skills/dasen-wechat/scripts/native_renderer.py"
    target = output / "sample-wechat.html"
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(renderer), "--file", str(source), "--output", str(target)],
            cwd=output, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                             "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
        )
        if result.returncode or not target.is_file():
            return {"status": "blocked", "error": "local renderer failed",
                    "detail": (result.stdout + result.stderr)[-2000:]}
        html = target.read_text(encoding="utf-8")
        if ('data-dasen-renderer="native-v1"' not in html
                or "安装检查示例" not in html or "<table" not in html
                or 'data-dasen-code="true"' not in html or "<script" in html):
            return {"status": "blocked", "error": "renderer output did not preserve the sample contract"}
        return {"status": "ready", "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "bytes": target.stat().st_size}
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        return {"status": "blocked", "error": str(exc)}


def report(root: Path, output: Path) -> dict:
    distribution = inspect_distribution(root)
    dependencies = inspect_dependencies(root / "requirements.txt")
    conversion = {"status": "not-run", "reason": "distribution and dependencies must pass first"}
    if distribution["status"] == dependencies["status"] == "ready":
        conversion = local_conversion(root, output)
    local_ready = all(item["status"] == "ready" for item in (distribution, dependencies, conversion))
    return {
        "schema_version": 1, "artifact_root": str(root),
        "local_readiness": "ready" if local_ready else "blocked",
        "distribution": distribution, "dependencies": dependencies, "local_html": conversion,
        "native_discovery": {"status": "unverified",
                             "reason": "must be observed in the selected host; files are not discovery evidence"},
        "first_creation": {"status": "not-run", "reason": "user-initiated; sample conversion is not authorship"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--local-only", action="store_true",
                        help="Exit 0 for local readiness only; never proves native host discovery")
    parser.add_argument("--output", type=Path,
                        help="Retain sample HTML in a new directory outside the artifact (default: temporary)")
    args = parser.parse_args(argv)
    root = args.artifact_root.resolve()
    try:
        if args.output:
            output = args.output.resolve()
            if output == root or root in output.parents:
                parser.error("--output must be outside the artifact")
            output.mkdir(parents=True, exist_ok=False)
            checks = report(root, output)
            if checks["local_html"]["status"] == "ready":
                checks["local_html"]["output"] = str(output / "sample-wechat.html")
        else:
            with tempfile.TemporaryDirectory(prefix="dasen-install-check-") as temporary:
                checks = report(root, Path(temporary))
    except (OSError, ValueError) as exc:
        checks = {"local_readiness": "blocked", "error": str(exc)}
    ready = checks["local_readiness"] == "ready"
    code = (0 if args.local_only else 2) if ready else 1
    checks["overall"] = ("local-ready" if args.local_only else "discovery-unverified") if ready else "blocked"
    checks["exit_code"] = code
    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        print(f"dasen installation check: {checks['overall']}")
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
