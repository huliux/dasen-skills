#!/usr/bin/env python3
"""Prepare isolated production cases and run one fresh Codex CLI per case.

Only collection is automated; semantic quality needs an independent reviewer.
No network/platform validation or model calls happen during prepare/collect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IGNORED = {"evals", "__pycache__", ".pytest_cache", ".DS_Store"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): digest(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and not (set(p.relative_to(root).parts) & IGNORED)
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def command_output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def prepare(destination: Path, case_ids: list[str], suite_path: Path | None = None, rubric_path: Path | None = None) -> None:
    repo_root = ROOT.resolve()
    local_results = (repo_root / "eval-results").resolve()
    if destination.is_relative_to(repo_root) and not destination.is_relative_to(local_results):
        raise ValueError("in-repo output must be under ignored eval-results/")
    suite_path = suite_path or HERE / "artifact-cases.json"
    rubric_path = rubric_path or HERE / "artifact-rubric.json"
    suite = read_json(suite_path)
    rubric = read_json(rubric_path)
    if suite.get("suite_id") != rubric.get("suite_id"):
        raise ValueError("case suite and rubric IDs differ")
    ids = [case["id"] for case in suite["cases"]]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) for name in ids):
        raise ValueError("case IDs must be unique safe path components")
    chosen = [c for c in suite["cases"] if not case_ids or c["id"] in case_ids]
    unknown = set(case_ids) - {c["id"] for c in chosen}
    if unknown:
        raise ValueError(f"unknown case IDs: {sorted(unknown)}")
    if destination.exists():
        raise ValueError("destination exists; use a new directory to preserve the old run")
    destination.mkdir(parents=True)
    manifest = {
        "suite_id": suite["suite_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commit": command_output("git", "rev-parse", "HEAD"),
        "dirty_status": command_output("git", "status", "--short"),
        "cases_sha256": digest(suite_path),
        "rubric_sha256": digest(rubric_path),
        "runner_sha256": digest(Path(__file__)),
        "isolation": "fresh CLI context and workspace; user config ignored; global discovery/read access may remain; audit trace",
        "cases": {},
    }
    # The assessment files stay outside every producer workspace.
    shutil.copy2(suite_path, destination / "cases.snapshot.json")
    shutil.copy2(rubric_path, destination / "rubric.snapshot.json")
    for case in chosen:
        base = destination / case["id"]
        workspace = base / "workspace"
        skills = workspace / ".agents/skills"
        skills.mkdir(parents=True)
        for source in sorted((ROOT / "skills").glob("dasen-*")):
            if (source / "SKILL.md").is_file():
                shutil.copytree(source, skills / source.name, ignore=shutil.ignore_patterns(*IGNORED))
        for name, content in case["files"].items():
            target = workspace / name
            if not target.resolve().is_relative_to(workspace.resolve()):
                raise ValueError(f"input path escapes workspace: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        (workspace / "AGENTS.md").write_text(
            "# 离线内容工作区\n\n"
            "原始材料位于 materials/，保持原文件不变；产出写入当前工作区。\n"
            "本次仅使用当前工作区 .agents/skills/ 中的 Skill 快照及已安装运行库。\n"
            "Skill 快照只读，按需读取对应 SKILL.md；不读取其他项目、全局 Skill 或上级评估文件。\n"
            "本次离线执行，不联网、不读取凭证、不调用付费服务、不上传或写入平台。\n"
            "不安装依赖。安全默认足够时直接执行；无法完成的部分如实说明。\n"
        )
        (base / "prompt.txt").write_text(case["prompt"] + "\n")
        for turn, prompt in enumerate(case.get("followups", []), 2):
            (base / f"prompt-{turn}.txt").write_text(prompt + "\n")
        manifest["cases"][case["id"]] = {
            "inputs": inventory(workspace / "materials"),
            "skills": inventory(skills),
            "instructions_sha256": digest(workspace / "AGENTS.md"),
            "prompt_sha256": digest(base / "prompt.txt"),
            "followups": {p.name: digest(p) for p in sorted(base.glob("prompt-*.txt"))},
        }
    write_json(destination / "manifest.json", manifest)
    print(f"prepared {len(chosen)} cases: {destination}")


def run_case(run: Path, case_id: str, model: str, effort: str, timeout: int) -> int:
    manifest = read_json(run / "manifest.json")
    if case_id not in manifest["cases"]:
        raise ValueError("case not prepared")
    base = run / case_id
    if (base / "execution.json").exists() or (base / "trace.jsonl").exists():
        raise ValueError("case already started; prepare a new run for retries")
    cmd = [
        "codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--model", model,
        "-c", f'model_reasoning_effort="{effort}"',
        "--cd", str(base / "workspace"), "--json",
        "--output-last-message", str(base / "final.md"), "-",
    ]
    execution = {
        "command": cmd, "harness": command_output("codex", "--version"),
        "model_requested": model, "reasoning_effort": effort,
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "running",
    }
    write_json(base / "execution.json", execution)
    start = time.monotonic()
    code = 1
    try:
        with (base / "trace.jsonl").open("w") as trace, (base / "stderr.txt").open("w") as errors:
            result = subprocess.run(
                cmd, input=(base / "prompt.txt").read_text(), text=True,
                stdout=trace, stderr=errors, timeout=timeout, check=False,
            )
        code = result.returncode
        execution.update(status="completed" if code == 0 else "failed", exit_code=code)
    except subprocess.TimeoutExpired:
        execution.update(status="timeout", exit_code=None)
        code = 124
    except OSError as exc:
        execution.update(status="failed", exit_code=None, error=str(exc))
    finally:
        execution["elapsed_seconds"] = round(time.monotonic() - start, 2)
        write_json(base / "execution.json", execution)
        collect(run)
    return code


def collect(run: Path) -> None:
    manifest = read_json(run / "manifest.json")
    results = {}
    for case_id, before in manifest["cases"].items():
        base = run / case_id
        workspace = base / "workspace"
        execution = read_json(base / "execution.json") if (base / "execution.json").exists() else {"status": "not_run"}
        artifacts = {
            name: sha for name, sha in inventory(workspace).items()
            if not name.startswith((".agents/", "materials/")) and name != "AGENTS.md"
        }
        usage = []
        if (base / "trace.jsonl").exists():
            for line in (base / "trace.jsonl").read_text().splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("usage"):
                    usage.append(event["usage"])
        results[case_id] = {
            "execution": execution,
            "materials_unchanged": inventory(workspace / "materials") == before["inputs"],
            "skills_unchanged": inventory(workspace / ".agents/skills") == before["skills"],
            "instructions_unchanged": digest(workspace / "AGENTS.md") == before["instructions_sha256"],
            "artifacts": artifacts, "usage_events": usage,
            "assessment": {"contract": "NOT_ASSESSED", "article": "NOT_ASSESSED", "delivery": "NOT_ASSESSED"},
        }
    write_json(run / "collection.json", results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    p = subs.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--id", action="append", default=[])
    p.add_argument("--suite", type=Path)
    p.add_argument("--rubric", type=Path)
    p = subs.add_parser("run")
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--model", required=True, help="Use the model authorized for this evaluation")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"], default="high")
    p.add_argument("--timeout", type=int, default=900)
    p = subs.add_parser("collect")
    p.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            prepare(args.output.expanduser().resolve(), args.id, args.suite, args.rubric)
        elif args.action == "collect":
            collect(args.run.expanduser().resolve())
        else:
            return run_case(args.run.expanduser().resolve(), args.id, args.model, args.effort, args.timeout)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
