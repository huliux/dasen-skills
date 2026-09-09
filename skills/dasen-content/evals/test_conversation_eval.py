"""Check resumable execution and evidence integrity without calling a model."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import artifact_eval
import conversation_eval as runner


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    skill = source / 'skills/dasen-content'
    (skill / 'evals').mkdir(parents=True)
    (skill / 'SKILL.md').write_text('snapshot')
    (skill / 'evals/hidden.txt').write_text('hidden')
    suite = tmp_path / 'suite.json'
    suite.write_text(json.dumps({'suite_id': 'test', 'cases': [
        {'id': 'conversation', 'prompt': 'first user request', 'followups': ['second user answer'],
         'files': {'materials/raw.md': 'evidence'}}]}))
    rubric = tmp_path / 'rubric.json'
    rubric.write_text('{"suite_id": "test", "private": "expected output"}')
    monkeypatch.setattr(artifact_eval, 'ROOT', source)
    monkeypatch.setattr(artifact_eval, 'command_output', lambda *args: 'test')
    monkeypatch.setattr(runner, 'command_output', lambda *args: 'test')
    dest = tmp_path / 'run'
    artifact_eval.prepare(dest, [], suite, rubric)
    return dest


def fake_run(cmd, **kwargs):
    kwargs['stdout'].write('{"type":"thread.started","thread_id":"fixed-session"}\n')
    kwargs['stdout'].write('{"type":"turn.completed","usage":{"output_tokens":1}}\n')
    Path(kwargs['cwd'], 'answer.md').write_text(kwargs['input'])
    return subprocess.CompletedProcess(cmd, 0)


def test_followup_is_hidden_and_resume_uses_exact_session(prepared, monkeypatch):
    workspace = prepared / 'conversation/workspace'
    assert not any('second user answer' in p.read_text() for p in workspace.rglob('*') if p.is_file())
    assert not list(workspace.rglob('evals'))
    calls = []
    def execute(cmd, **kwargs):
        calls.append(cmd)
        return fake_run(cmd, **kwargs)
    monkeypatch.setattr(runner.subprocess, 'run', execute)
    assert runner.run_turn(prepared, 'conversation', 1, 'test', 'high', 10) == 0
    assert runner.run_turn(prepared, 'conversation', 2, 'test', 'high', 10) == 0
    assert calls[1][-3:] == ['resume', 'fixed-session', '-']
    assert '--ephemeral' not in calls[0]
    result = json.loads((prepared / 'conversation/turn-2/execution.json').read_text())
    assert result['changed_files'] == ['answer.md']
    assert result['assessment'] == 'NOT_ASSESSED'
    with pytest.raises(ValueError, match='already started'):
        runner.run_turn(prepared, 'conversation', 2, 'test', 'high', 10)


def test_tampered_prompt_cannot_run(prepared, monkeypatch):
    (prepared / 'conversation/prompt.txt').write_text('changed')
    with pytest.raises(ValueError, match='changed frozen prompt'):
        runner.run_turn(prepared, 'conversation', 1, 'test', 'high', 10)
    assert not (prepared / 'conversation/turn-1').exists()


def test_timeout_cannot_be_resumed(prepared, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(runner.subprocess, 'run', timeout)
    assert runner.run_turn(prepared, 'conversation', 1, 'test', 'high', 1) == 124
    with pytest.raises(ValueError, match='previous turn did not complete'):
        runner.run_turn(prepared, 'conversation', 2, 'test', 'high', 1)


def test_status_inventory_includes_cache_writes(prepared, monkeypatch):
    def write_cache(cmd, **kwargs):
        target = Path(kwargs['cwd']) / '__pycache__/created.pyc'
        target.parent.mkdir()
        target.write_bytes(b'cache')
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(runner.subprocess, 'run', write_cache)
    assert runner.run_turn(prepared, 'conversation', 1, 'test', 'high', 10) == 0
    result = json.loads((prepared / 'conversation/turn-1/execution.json').read_text())
    assert result['changed_files'] == ['__pycache__/created.pyc']


@pytest.mark.parametrize('bad_id', ['../escape', '/absolute', 'two/parts'])
def test_prepare_rejects_case_path_escape(tmp_path, monkeypatch, bad_id):
    suite = tmp_path / 'suite.json'
    rubric = tmp_path / 'rubric.json'
    suite.write_text(json.dumps({'suite_id': 'test', 'cases': [{'id': bad_id}]}))
    rubric.write_text('{"suite_id":"test"}')
    with pytest.raises(ValueError, match='safe path components'):
        artifact_eval.prepare(tmp_path / 'run', [], suite, rubric)
    assert not (tmp_path / 'run').exists()


def test_prepare_rejects_unrelated_rubric(tmp_path):
    suite = tmp_path / 'suite.json'
    rubric = tmp_path / 'rubric.json'
    suite.write_text('{"suite_id":"one","cases":[]}')
    rubric.write_text('{"suite_id":"other"}')
    with pytest.raises(ValueError, match='IDs differ'):
        artifact_eval.prepare(tmp_path / 'run', [], suite, rubric)
    assert not (tmp_path / 'run').exists()
