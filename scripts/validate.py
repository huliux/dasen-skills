#!/usr/bin/env python3
"""Cheap deterministic validation for the canonical dasen skill repository."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
ABSOLUTE = re.compile(r"/(?:Users)/[^\s`'\"]+|~/(?:\.claude|\.codex|\.pi|\.agents)/")
SECRET = re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        raise ValueError("missing YAML frontmatter")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data


def main() -> int:
    errors: list[str] = []
    registry = yaml.safe_load((ROOT / "registry.yaml").read_text(encoding="utf-8"))
    packs = yaml.safe_load((ROOT / "packs.yaml").read_text(encoding="utf-8"))
    registered = registry.get("skills", {})

    actual = {p.name for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    if actual != set(registered):
        errors.append(f"registry mismatch: actual={sorted(actual)} registered={sorted(registered)}")

    for name in sorted(actual):
        skill = SKILLS / name
        entry = skill / "SKILL.md"
        text = entry.read_text(encoding="utf-8")
        try:
            meta = frontmatter(entry)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue
        if meta.get("name") != name:
            errors.append(f"{name}: frontmatter name={meta.get('name')!r}")
        if meta.get("license") != "MIT":
            errors.append(f"{name}: frontmatter license must be MIT")
        desc = str(meta.get("description") or "")
        if not desc or len(desc) > 1024:
            errors.append(f"{name}: description length {len(desc)}")
        if len(text.splitlines()) > 500:
            errors.append(f"{name}: SKILL.md >500 lines")
        version = str((meta.get("metadata") or {}).get("version") or "")
        if version != str(registered[name].get("version")):
            errors.append(f"{name}: metadata.version {version!r} != registry {registered[name].get('version')!r}")
        if registered[name].get("ownership") != "owned":
            errors.append(f"{name}: central Skill ownership must be owned")
        if registered[name].get("license") != "MIT":
            errors.append(f"{name}: central Skill license must be MIT")
        if "upstream" in registered[name]:
            errors.append(f"{name}: external Skill provenance belongs in ../skill-vendors")
        missing_dependencies = set(registered[name].get("depends_on") or []) - actual
        if missing_dependencies:
            errors.append(f"{name}: external names in depends_on {sorted(missing_dependencies)}")
        missing_routes = set(registered[name].get("routes_to") or []) - actual
        if missing_routes:
            errors.append(f"{name}: unknown routes_to targets {sorted(missing_routes)}")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in link or link.startswith("#"):
                continue
            if not (skill / link).resolve().exists():
                errors.append(f"{name}: missing reference {link}")
        for path in skill.rglob("*"):
            if (
                not path.is_file()
                or "__pycache__" in path.parts
                or path.stat().st_size > 1_000_000
                or path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".mp3", ".wav", ".mp4"}
            ):
                continue
            content = path.read_text(errors="ignore")
            if ABSOLUTE.search(content):
                errors.append(f"{name}: personal/harness absolute path in {path.relative_to(skill)}")
            if SECRET.search(content) and "your_" not in content.lower() and "dummy" not in content.lower():
                errors.append(f"{name}: possible literal secret in {path.relative_to(skill)}")

    for pack, cfg in (packs.get("packs") or {}).items():
        missing = set(cfg.get("skills") or []) - actual
        if missing:
            errors.append(f"pack {pack}: missing {sorted(missing)}")
        misplaced = set(cfg.get("optional_skills") or []) & actual
        if misplaced:
            errors.append(f"pack {pack}: owned Skills cannot be optional external Skills {sorted(misplaced)}")
        legacy_keys = {"external", "optional_external"} & set(cfg)
        if legacy_keys:
            errors.append(f"pack {pack}: use external_tools/optional_skills, not {sorted(legacy_keys)}")

    public = packs.get("public_subset") or {}
    public_skills = set(public.get("skills") or [])
    unknown_public = public_skills - actual
    if unknown_public:
        errors.append(f"public subset: missing {sorted(unknown_public)}")
    for name in public_skills:
        missing_public_dependencies = set(registered[name].get("depends_on") or []) - public_skills
        if missing_public_dependencies:
            errors.append(f"public subset: {name} misses dependencies {sorted(missing_public_dependencies)}")
        if registered[name].get("visibility") != "public-candidate":
            errors.append(f"public subset: {name} is not public-candidate")
    if public.get("license") != "MIT":
        errors.append("public subset must use root MIT license")
    for relative in public.get("distribution_files") or []:
        if not (ROOT / str(relative)).is_file():
            errors.append(f"public subset: missing distribution file {relative}")

    if not (ROOT / "LICENSE").is_file():
        errors.append("root MIT license missing")
    if not (ROOT / "scripts/build_public.py").is_file():
        errors.append("public subset build script missing")

    scripts = [p for p in [*SKILLS.rglob("*.py"), *ROOT.glob("scripts/*.py")] if "__pycache__" not in p.parts]
    for script in scripts:
        proc = subprocess.run([sys.executable, "-m", "py_compile", str(script)], capture_output=True, text=True)
        if proc.returncode:
            errors.append(f"python syntax: {script.relative_to(ROOT)}: {proc.stderr.strip()}")
    shell_scripts = list(SKILLS.rglob("*.sh"))
    if shell_scripts and not shutil.which("bash"):
        print("NOTE: bash syntax checks unavailable; Python entry points remain usable")
    for script in shell_scripts if shutil.which("bash") else []:
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        if proc.returncode:
            errors.append(f"bash syntax: {script.relative_to(ROOT)}: {proc.stderr.strip()}")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {len(actual)} skills, {len(packs.get('packs') or {})} packs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
