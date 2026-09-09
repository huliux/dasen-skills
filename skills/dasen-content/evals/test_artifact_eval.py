"""Verify evidence integrity, not model wording or semantic grades."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SPEC = importlib.util.spec_from_file_location("artifact_eval", Path(__file__).with_name("artifact_eval.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    source = tmp_path / "source"
    skill = source / "skills/dasen-content"
    (skill / "evals").mkdir(parents=True)
    (skill / "SKILL.md").write_text("skill snapshot")
    (skill / "evals/private-rubric.txt").write_text("hidden expectation")
    monkeypatch.setattr(runner, "ROOT", source)
    monkeypatch.setattr(runner, "command_output", lambda *args: "test-runtime")
    dest = tmp_path / "run"
    runner.prepare(dest, ["local-article-html"])
    return dest


def test_prepare_hides_rubric_and_preserves_existing_run(prepared):
    workspace = prepared / "local-article-html/workspace"
    assert not list(workspace.rglob("*rubric*"))
    assert not list(workspace.rglob("evals"))
    assert (prepared / "rubric.snapshot.json").is_file()
    before = (prepared / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="destination exists"):
        runner.prepare(prepared, ["local-article-html"])
    assert (prepared / "manifest.json").read_bytes() == before


def test_prepare_rejects_tracked_source_output(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(runner, "ROOT", source)
    target = source / "skills/dasen-content/evals/runs/new-run"
    with pytest.raises(ValueError, match="ignored eval-results"):
        runner.prepare(target, ["local-article-html"])
    assert not target.exists()


def test_collect_reports_unrun_and_source_tampering(prepared):
    runner.collect(prepared)
    result = json.loads((prepared / "collection.json").read_text())["local-article-html"]
    assert result["execution"]["status"] == "not_run"
    assert result["artifacts"] == {}
    assert set(result["assessment"].values()) == {"NOT_ASSESSED"}
    workspace = prepared / "local-article-html/workspace"
    (workspace / "materials/trial.md").write_text("rewritten")
    (workspace / ".agents/skills/dasen-content/SKILL.md").write_text("changed")
    runner.collect(prepared)
    result = json.loads((prepared / "collection.json").read_text())["local-article-html"]
    assert not result["materials_unchanged"]
    assert not result["skills_unchanged"]


def test_successful_process_is_not_a_quality_pass(prepared, monkeypatch):
    def no_artifacts(cmd, **kwargs):
        kwargs["stdout"].write('{"type":"turn.completed","usage":{"output_tokens":3}}\n')
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(runner.subprocess, "run", no_artifacts)
    assert runner.run_case(prepared, "local-article-html", "test-model", "high", 10) == 0
    result = json.loads((prepared / "collection.json").read_text())["local-article-html"]
    assert result["execution"]["status"] == "completed"
    assert result["artifacts"] == {}
    assert result["usage_events"] == [{"output_tokens": 3}]
    assert set(result["assessment"].values()) == {"NOT_ASSESSED"}
    with pytest.raises(ValueError, match="already started"):
        runner.run_case(prepared, "local-article-html", "test-model", "high", 10)


def test_timeout_remains_in_results(prepared, monkeypatch):
    def timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 1)
    monkeypatch.setattr(runner.subprocess, "run", timeout)
    assert runner.run_case(prepared, "local-article-html", "test-model", "high", 1) == 124
    result = json.loads((prepared / "collection.json").read_text())["local-article-html"]
    assert result["execution"]["status"] == "timeout"
    assert set(result["assessment"].values()) == {"NOT_ASSESSED"}
