#!/usr/bin/env python3
"""Read-only capability report for the dasen content pipeline. Never prints secrets."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

STAGES = [
    "dasen-content", "dasen-research", "dasen-writing", "dasen-knowledge",
    "dasen-visual", "dasen-wechat", "dasen-video",
]
COMMANDS = ["agent-reach", "aihot", "ffmpeg", "node", "npm", "bitbook"]


def find_repo() -> Path:
    """Locate the caller's workspace without traversing installation ancestors."""
    start = Path.cwd().resolve()
    home = Path.home().resolve()
    for parent in (start, *start.parents):
        if parent == home or parent == parent.parent:
            break
        if (parent / ".git").exists() or (parent / "project.md").is_file():
            return parent
        if any((parent / entry / "dasen-content/SKILL.md").is_file()
               for entry in (".agents/skills", ".claude/skills", ".pi/skills")):
            return parent
    return start


def command_version(name: str) -> tuple[str, str | None]:
    path = shutil.which(name)
    if not path:
        return "unavailable", None
    probes = [[name, "--version"], [name, "version"]]
    for cmd in probes:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if p.returncode == 0:
                line = (p.stdout or p.stderr).splitlines()[0][:160]
                return "ready", line
        except Exception:
            pass
    return "ready", path


def remotion_versions(repo: Path, skills_root: Path) -> dict:
    result: dict[str, object] = {"status": "unavailable", "engine": None, "optional_skill": None}
    package = repo / "remotion/package.json"
    skill = skills_root / "remotion-best-practices/SKILL.md"
    if package.is_file():
        data = json.loads(package.read_text(encoding="utf-8"))
        deps = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
        result["engine"] = deps.get("remotion") or deps.get("@remotion/cli")
    if skill.is_file():
        m = re.search(r"^version:\s*([^\n]+)", skill.read_text(encoding="utf-8"), re.M)
        result["optional_skill"] = m.group(1).strip() if m else None
    if result["engine"]:
        result["status"] = "ready"
    return result


def find_skills_root(repo: Path) -> Path:
    # Consumer projections may point to different canonical repositories. Resolving
    # __file__ alone loses vendor siblings (e.g. Remotion) after single-source migration.
    for relative in (".agents/skills", ".claude/skills", ".pi/skills", "skills"):
        candidate = repo / relative
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect dasen content pipeline capabilities")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--content-root", help="Workspace-relative content directory")
    ap.add_argument("--project-file", help="Current-workspace-relative project.md used for project-scoped capabilities")
    args = ap.parse_args()
    repo = find_repo()
    skill_root = find_skills_root(repo)
    source_root = Path(__file__).resolve().parents[3]

    checks: dict[str, object] = {
        "repo": str(repo),
        "python": {"status": "ready" if sys.version_info >= (3, 10) else "blocked", "version": sys.version.split()[0]},
        "python_packages": {},
        "stages": {},
        "commands": {},
        "packs": {},
        "projects": {},
        "wechat_credentials": {"status": "unavailable", "source": None},
        "remotion": remotion_versions(repo, skill_root),
        "distribution": {
            "root_license": "ready" if any((source_root / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")) else "missing",
        },
        "known_risks": [],
    }
    for module, label in (("yaml", "PyYAML"), ("markdown_it", "markdown-it-py"), ("pygments", "Pygments")):
        try:
            imported = __import__(module)
            checks["python_packages"][label] = {
                "status": "ready",
                "version": getattr(imported, "__version__", None),
            }
        except ImportError:
            checks["python_packages"][label] = {"status": "blocked", "version": None}

    for name in STAGES:
        checks["stages"][name] = "ready" if (skill_root / name / "SKILL.md").is_file() else "blocked"
    for name in COMMANDS:
        status, version = command_version(name)
        checks["commands"][name] = {"status": status, "version": version}
    discovered = sorted({
        *([repo / "project.md"] if (repo / "project.md").is_file() else []),
        *repo.glob("**/series.md"),
    })
    if discovered:
        for path in discovered:
            label = str(path.relative_to(repo))
            checks["projects"][label] = "ready"
    else:
        checks["projects"]["standalone"] = "ready"

    project: dict = {}
    from content_paths import control_reference, select_content_root
    from project_config import default_project_reference
    content_root = select_content_root(repo, args.content_root, args.project_file)
    checks["content_root"] = str(content_root)
    project_reference = control_reference(repo, content_root, args.project_file) or default_project_reference(content_root)
    if project_reference:
        try:
            from project_config import load_project_reference

            _, project = load_project_reference(project_reference, content_root)
        except ValueError as exc:
            ap.error(str(exc))
    credential_script = skill_root / "dasen-wechat" / "scripts" / "wechat_credentials.py"
    if credential_script.is_file():
        sys.path.insert(0, str(credential_script.parent))
        from wechat_credentials import credential_status

        checks["wechat_credentials"] = credential_status(project)

    core_blocked = (
        checks["python"]["status"] == "blocked"
        or checks["python_packages"]["PyYAML"]["status"] == "blocked"
        or any(checks["stages"][name] == "blocked" for name in ("dasen-content", "dasen-research", "dasen-writing"))
    )
    wechat_blocked = core_blocked or any(
        checks["python_packages"][name]["status"] == "blocked" for name in ("markdown-it-py", "Pygments")
    ) or any(checks["stages"][name] == "blocked" for name in ("dasen-knowledge", "dasen-visual", "dasen-wechat"))
    video_blocked = (
        core_blocked
        or checks["stages"]["dasen-video"] == "blocked"
        or checks["commands"]["node"]["status"] == "unavailable"
        or checks["commands"]["ffmpeg"]["status"] == "unavailable"
        or checks["remotion"]["status"] != "ready"
    )
    checks["packs"] = {
        "content-core": "blocked" if core_blocked else "ready",
        "content-wechat": "blocked" if wechat_blocked else "ready",
        "content-video": ("not-installed" if checks["stages"]["dasen-video"] == "blocked"
                          else "blocked" if video_blocked else "ready"),
    }
    has_warnings = (
        checks["distribution"]["root_license"] != "ready"
        or wechat_blocked
        or (video_blocked and checks["stages"]["dasen-video"] == "ready")
    )
    checks["overall"] = "blocked" if core_blocked else "ready-with-warnings" if has_warnings else "ready"

    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        print(f"dasen doctor · {checks['overall']}\nrepo: {repo}")
        print("\nStages")
        for k, v in checks["stages"].items():
            print(f"  {v:9} {k}")
        print("\nCommands")
        for k, v in checks["commands"].items():
            print(f"  {v['status']:11} {k} {v['version'] or ''}")
        print("\nPacks")
        for k, v in checks["packs"].items():
            print(f"  {v:9} {k}")
        print(f"\nWeChat credentials: {checks['wechat_credentials']['status']} ({checks['wechat_credentials']['source'] or 'none'})")
        print(f"Remotion: {checks['remotion']}")
        print(f"Distribution: {checks['distribution']}")
        for risk in checks["known_risks"]:
            print(f"WARN: {risk}")
    return 1 if core_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
