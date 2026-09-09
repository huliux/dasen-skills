#!/usr/bin/env python3
"""Build and verify the clean, distributable Skill subset declared in packs.yaml."""

from __future__ import annotations

import argparse
from copy import deepcopy
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from source_snapshot import source_snapshot, write_manifest
from export_runtime import verify as verify_runtime_lock


ROOT = Path(__file__).resolve().parent.parent
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}
GOVERNANCE_FILES = {
    ".git",
    ".agents",
    "AGENTS.md",
    "CHANGELOG.md",
    "SESSION-HANDOFF-2026-09-05.md",
    "docs/history",
    "docs/research",
    "docs/evidence",
}
FORBIDDEN_TEXT = {
    "gzh-image" + ".tos": "project-specific TOS endpoint",
    "cn-" + "beijing": "project-specific TOS region",
    "大森": "private persona",
    "creator-" + "buddy": "private adapter",
}
PERSONAL_PATH = re.compile(
    r"(?<![\w.-])(?:/(?:Users|home)/[^/\s`'\"]+|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s`'\"]+)"
)
EMAIL = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+)@([A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])", re.I)
SENSITIVE_LITERAL = re.compile(
    r"(?im)^\s*[\"']?(endpoint|region|bucket|public_base_url|keychain_service|"
    r"access_key_account|secret_key_account|credential_profile|model)[\"']?\s*[:=]\s*[\"']([^\"']+)[\"']"
)
SENSITIVE_YAML_LITERAL = re.compile(
    r"(?im)^\s*(endpoint|region|bucket|public_base_url|keychain_service|"
    r"access_key_account|secret_key_account|credential_profile|model)\s*:\s*([^\s#][^#\n]*)$"
)
PLACEHOLDER_WORDS = ("example", "sample", "placeholder", "dummy", "test")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return data


def ignored(directory: str, names: list[str]) -> set[str]:
    result = {
        name for name in names
        if name in IGNORED_NAMES or name.endswith((".pyc", ".pyo"))
    }
    if Path(directory).name == "evals" and "runs" in names:
        result.add("runs")
    return result


def filtered_metadata(
    registry: dict[str, Any], packs: dict[str, Any], public_skills: list[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    public_set = set(public_skills)
    public_packs: dict[str, Any] = {}
    for name, config in (packs.get("packs") or {}).items():
        members = set(config.get("skills") or [])
        if members and members <= public_set:
            public_packs[name] = deepcopy(config)
    public_pack_names = set(public_packs)
    public_entries: dict[str, Any] = {}
    for name in public_skills:
        entry = deepcopy(registry["skills"][name])
        if "routes_to" in entry:
            entry["routes_to"] = [target for target in entry["routes_to"] if target in public_set]
        if "packs" in entry:
            entry["packs"] = [pack for pack in entry["packs"] if pack in public_pack_names]
        public_entries[name] = entry
    public_registry = {
        "schema_version": registry.get("schema_version"),
        "policy": registry.get("policy"),
        "skills": public_entries,
    }
    public_manifest = {
        "schema_version": packs.get("schema_version"),
        "public_subset": packs.get("public_subset"),
        "packs": public_packs,
    }
    return public_registry, public_manifest


def is_placeholder(value: str) -> bool:
    normalized = value.strip().casefold()
    return (
        not normalized
        or normalized in {"none", "null"}
        or any(word in normalized for word in PLACEHOLDER_WORDS)
        or normalized.startswith(("${", "{{", "<"))
    )


def scan_text(relative: Path, text: str) -> list[str]:
    errors: list[str] = []
    for needle, label in FORBIDDEN_TEXT.items():
        public_identity = needle == "大森" and relative.as_posix() in {"README.md", "README.en.md", "docs/intent.md"}
        if needle in text and not public_identity and (needle != "大森" or relative.parts[0] == "skills"):
            errors.append(f"{relative}: {label}")
    if PERSONAL_PATH.search(text):
        errors.append(f"{relative}: personal absolute path")
    for match in EMAIL.finditer(text):
        domain = match.group(2).casefold()
        if domain not in {"example.com", "example.net", "example.org"} and not domain.endswith(".test"):
            errors.append(f"{relative}: non-placeholder email address")
            break
    for field, value in SENSITIVE_LITERAL.findall(text):
        if not is_placeholder(value):
            errors.append(f"{relative}: non-placeholder service setting in {field}")
    if relative.suffix.lower() in {".md", ".yaml", ".yml"}:
        for field, value in SENSITIVE_YAML_LITERAL.findall(text):
            scalar = value.strip().strip("\"'")
            if not is_placeholder(scalar):
                errors.append(f"{relative}: non-placeholder service setting in {field}")
    return errors


def scanner_contract_errors() -> list[str]:
    probes = {
        "personal path": "root: /" + "home/private-user/content",
        "personal email": "author: writer" + "@private.invalid",
        "service bucket": 'bucket: "production-private-bucket"',
        "service domain": 'endpoint: "https://cdn.private.invalid"',
    }
    errors: list[str] = []
    for label, probe in probes.items():
        if not scan_text(Path("<scanner-contract>"), probe):
            errors.append(f"public scanner does not reject {label}")
    return errors


def scan_text_tree(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".mp3", ".mp4"
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        errors.extend(scan_text(path.relative_to(root), text))
    return errors


def validate_tree(root: Path, public_skills: list[str], kind: str = "install") -> list[str]:
    errors: list[str] = scanner_contract_errors()
    expected = set(public_skills)
    actual = {
        path.name for path in (root / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    if actual != expected:
        errors.append(f"public Skill set mismatch: expected={sorted(expected)} actual={sorted(actual)}")
    for name in GOVERNANCE_FILES:
        if kind == "install" and (root / name).exists():
            errors.append(f"governance/private path was copied: {name}")
    registry = load_yaml(root / "registry.yaml")
    manifest = load_yaml(root / "packs.yaml")
    declared_packs = set((manifest.get("packs") or {}).keys())
    for name, config in (registry.get("skills") or {}).items():
        missing = set(config.get("depends_on") or []) - expected
        if missing:
            errors.append(f"{name}: public dependency closure misses {sorted(missing)}")
        unknown_packs = set(config.get("packs") or []) - declared_packs
        if unknown_packs:
            errors.append(f"{name}: references omitted public packs {sorted(unknown_packs)}")
    public = manifest.get("public_subset") or {}
    if kind == "install":
        selected_files = set(public.get("distribution_files") or [])
        for path in (root / "docs").rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if (relative not in selected_files or
                    path.parent.relative_to(root).as_posix() not in {"docs/en", "docs/zh-CN"}):
                errors.append(f"unlisted installation document: {relative}")
    excluded = set(public.get("excludes") or [])
    leaked = excluded & actual
    if leaked:
        errors.append(f"excluded Skills were copied: {sorted(leaked)}")
    errors.extend(scan_text_tree(root))
    errors.extend(validate_document_links(root))
    for path in root.rglob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"python syntax: {path.relative_to(root)}: {exc}")
    return errors


def run_offline_checks(root: Path) -> list[str]:
    errors: list[str] = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "skills",
         *(["tests"] if (root / "tests").is_dir() else [])],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if tests.returncode:
        errors.append("public offline tests failed:\n" + (tests.stdout + tests.stderr)[-5000:])
        return errors

    examples = subprocess.run(
        [sys.executable, "skills/dasen-content/examples/verify_examples.py"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if examples.returncode:
        errors.append("public contract examples failed:\n" + (examples.stdout + examples.stderr)[-5000:])
        return errors

    return run_consumer_smoke(root)


def run_consumer_smoke(root: Path) -> list[str]:
    errors: list[str] = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    with tempfile.TemporaryDirectory(prefix="dasen-public-consumer-") as temporary:
        consumer = Path(temporary)
        init_project = root / "skills/dasen-content/scripts/init_project.py"
        init_content = root / "skills/dasen-content/scripts/init_content.py"
        standalone = subprocess.run(
            [
                sys.executable, str(init_content),
                "--id", "2026-09-07-standalone-smoke", "--journey", "material",
                "--length", "quick", "--method", "original",
                "--objective", "smoke", "--audience", "reader", "--deliverable", "article",
            ],
            cwd=consumer,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if standalone.returncode:
            errors.append("public standalone smoke failed: " + standalone.stderr.strip())
            return errors
        standalone_brief = load_yaml(consumer / "writing/2026-09-07/standalone-smoke/brief.yaml")
        if standalone_brief.get("configuration") != "standalone":
            errors.append("public standalone smoke did not use standalone configuration")
        if (standalone_brief.get("brand") or {}).get("name") is not None:
            errors.append("public standalone smoke injected a content brand")

        created = subprocess.run(
            [
                sys.executable, str(init_project),
                "--project", "public-example", "--platform", "wechat",
                "--brand-name", "Northstar",
            ],
            cwd=consumer,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if created.returncode:
            errors.append("public init_project smoke failed: " + created.stderr.strip())
            return errors
        content = subprocess.run(
            [
                sys.executable, str(init_content),
                "--id", "2026-09-07-public-smoke", "--journey", "material",
                "--length", "quick", "--method", "original", "--platform", "wechat",
                "--objective", "smoke", "--audience", "reader", "--deliverable", "article",
            ],
            cwd=consumer,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if content.returncode:
            errors.append("public init_content smoke failed: " + content.stderr.strip())
        else:
            brief = load_yaml(consumer / "writing/2026-09-07/public-smoke/brief.yaml")
            if (brief.get("brand") or {}).get("name") != "Northstar":
                errors.append("public smoke did not compile the configured custom brand")
    return errors


def validate_document_links(root: Path) -> list[str]:
    errors = []
    for path in root.rglob("*.md"):
        # Synthetic Markdown in test fixtures is not repository navigation.
        if {"tests", "examples", "evals"} & set(path.relative_to(root).parts):
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:") or "<" in target:
                continue
            if not (path.parent / target).resolve().is_file():
                errors.append(f"{path.relative_to(root)}: missing document target {target}")
    return errors


def build(destination: Path, *, run_tests: bool, kind: str = "install") -> None:
    if destination.exists():
        raise RuntimeError("destination already exists; refusing to overwrite it")
    with source_snapshot(ROOT) as (snapshot, revision):
        verify_runtime_lock(snapshot)
        build_snapshot(snapshot, revision, destination, run_tests=run_tests, kind=kind)


def build_snapshot(source_root: Path, revision: str, destination: Path, *, run_tests: bool, kind: str) -> None:
    packs = load_yaml(source_root / "packs.yaml")
    registry = load_yaml(source_root / "registry.yaml")
    public = packs.get("public_subset") or {}
    public_skills = [str(name) for name in public.get("skills") or []]
    if not public_skills or set(public_skills) - set(registry.get("skills") or {}):
        raise ValueError("public subset must identify registered Skills")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".dasen-public-", dir=destination.parent))
    try:
        for name in public_skills:
            shutil.copytree(source_root / "skills" / name, staging / "skills" / name, ignore=ignored)
        if kind == "source":
            selected = load_yaml(source_root / "public-source.yaml")["files"]
            for relative in selected:
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("public source selection must stay within the source")
                target = staging / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_root / path, target)
        else:
            for relative in public.get("distribution_files") or []:
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("installation selection must stay within the source")
                target = staging / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_root / path, target)
        public_registry, public_packs = filtered_metadata(registry, packs, public_skills)
        for name, value in (("registry.yaml", public_registry), ("packs.yaml", public_packs)):
            (staging / name).write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
        errors = validate_tree(staging, public_skills, kind)
        if not errors and run_tests:
            errors.extend(run_offline_checks(staging))
        if errors:
            raise RuntimeError("public build validation failed:\n- " + "\n- ".join(errors))
        if kind == "install":
            for skill in (staging / "skills").iterdir():
                for directory in ("tests", "evals"):
                    shutil.rmtree(skill / directory, ignore_errors=True)
                for example in (skill / "examples").glob("*"):
                    if example.suffix in {".py", ".md"}:
                        example.unlink()
            if run_tests:
                errors.extend(run_consumer_smoke(staging))
                if errors:
                    raise RuntimeError("runtime artifact smoke failed: " + "\n".join(errors))
        write_manifest(staging, revision, kind)
        if run_tests:
            result = subprocess.run(
                [sys.executable, "-B", str(staging / "skills/dasen-content/scripts/install_check.py"),
                 "--local-only", "--json"],
                cwd=staging, capture_output=True, text=True, check=False, timeout=60,
            )
            if result.returncode:
                raise RuntimeError("installation readiness failed:\n" + result.stdout + result.stderr)
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a clean public Skill distribution")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--kind", choices=("source", "install"), default="install")
    parser.add_argument("--skip-tests", action="store_true", help="Skip copied-tree pytest and smoke checks")
    args = parser.parse_args()
    try:
        build(args.output.expanduser().resolve(), run_tests=not args.skip_tests, kind=args.kind)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: public distribution built at {args.output.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
