"""Artifact preparation preserves working versions and never claims host enablement."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'skills/dasen-content/scripts'))
import build_public
import prepare_runtime as preparation

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='macOS preparation uses POSIX locking')


@pytest.fixture(scope='module')
def artifact(tmp_path_factory):
    target = tmp_path_factory.mktemp('bootstrap-input') / 'artifact'
    build_public.build_snapshot(ROOT, 'b' * 40, target, run_tests=False, kind='install')
    return target


@pytest.fixture
def manager(monkeypatch):
    calls = []
    original = preparation.command
    def run(arguments, phase, **kwargs):
        calls.append(phase)
        if phase == 'Virtual environment preparation':
            directory = Path(arguments[-1]) / 'bin'
            directory.mkdir(parents=True)
            (directory / 'python').symlink_to(sys.executable)
            return ''
        if phase == 'Cache location':
            return str(kwargs['cwd'] / 'fixture-cache')
        if phase == 'Locked dependency download':
            assert '--require-hashes' in arguments and '--only-binary' in arguments
            assert arguments[arguments.index('--link-mode') + 1] == 'copy'
            return ''
        if phase == 'Local readiness check' and Path(arguments[0]).exists():
            arguments = [sys.executable, *arguments[1:]]
        return original(arguments, phase, **kwargs)
    monkeypatch.setattr(preparation, 'command', run)
    return calls


def run(artifact, data, **kwargs):
    return preparation.prepare(artifact, data, Path('/unused/uv'), **kwargs)


def test_repeat_rechecks_and_reuses_without_enabling_any_host(artifact, tmp_path, manager):
    data = tmp_path / '含 空格 storage'
    first = run(artifact, data)
    second = run(artifact, data)
    assert first['status'] == 'local-ready' and not first['reused']
    assert second['reused'] and second['python'] == first['python']
    assert manager.count('Locked dependency download') == 1
    assert manager.count('Local readiness check') == 2
    assert second['enabled_scope'] == 'none' and second['native_discovery'] == 'unverified'
    assert not list(data.rglob('__pycache__'))
    assert not (data / 'writing').exists()
    assert preparation.verify_artifact(Path(first['artifact_root']))['file_count'] > 70


def test_changed_stored_skill_is_preserved(artifact, tmp_path, manager):
    first = run(artifact, tmp_path / 'data')
    skill = Path(first['artifact_root']) / 'skills/dasen-writing/SKILL.md'
    skill.write_text('user edit', encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        run(artifact, tmp_path / 'data')
    assert skill.read_text() == 'user edit'
    assert Path(first['receipt']).is_file()


def test_interrupted_generation_is_never_reused(artifact, tmp_path, manager, monkeypatch):
    original = preparation.command
    def failing(arguments, phase, **kwargs):
        if phase == 'Locked dependency download':
            raise ValueError('network fixture')
        return original(arguments, phase, **kwargs)
    monkeypatch.setattr(preparation, 'command', failing)
    with pytest.raises(ValueError, match='network fixture'):
        run(artifact, tmp_path / 'data')
    generations = list((tmp_path / 'data/runtimes').glob('*/*'))
    assert len(generations) == 1 and not (generations[0] / 'ready.json').exists()
    monkeypatch.setattr(preparation, 'command', original)
    result = run(artifact, tmp_path / 'data')
    assert not result['reused'] and generations[0].exists()
    assert len(list((tmp_path / 'data/runtimes').glob('*/*'))) == 2


def test_broken_ready_environment_requires_explicit_new_generation(artifact, tmp_path, manager):
    first = run(artifact, tmp_path / 'data')
    Path(first['python']).unlink()
    with pytest.raises(ValueError, match='--repair'):
        run(artifact, tmp_path / 'data')
    repaired = run(artifact, tmp_path / 'data', repair=True)
    assert repaired['python'] != first['python'] and Path(first['receipt']).exists()
    assert run(artifact, tmp_path / 'data')['python'] == repaired['python']


def test_concurrent_prepare_refuses_then_recovers(artifact, tmp_path, manager):
    with preparation.preparation_lock(tmp_path / 'data'):
        with pytest.raises(ValueError, match='Another preparation'):
            run(artifact, tmp_path / 'data')
    assert run(artifact, tmp_path / 'data')['status'] == 'local-ready'


@pytest.mark.parametrize('relative', ['releases', 'runtimes', 'preparation.lock'])
def test_managed_links_are_not_followed(artifact, tmp_path, manager, relative):
    outside = tmp_path / 'outside'
    outside.mkdir()
    data = tmp_path / 'data'
    data.mkdir()
    (data / relative).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='link'):
        run(artifact, data)
    assert not list(outside.iterdir())


def test_nested_storage_refuses_before_writing(artifact, manager):
    with pytest.raises(ValueError, match='separate directory trees'):
        run(artifact, artifact / 'runtime')
    assert not (artifact / 'runtime').exists()


def test_failed_manager_output_does_not_leak_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs:
                        subprocess.CompletedProcess([], 1, '', 'https://user:private@example.test'))
    with pytest.raises(ValueError, match='Locked dependency download') as error:
        preparation.command(['uv'], 'Locked dependency download', environment={}, cwd=tmp_path)
    assert 'private' not in str(error.value)


def test_shell_help_needs_no_development_tools(artifact, tmp_path):
    shell = shutil.which('sh')
    if not shell:
        pytest.skip('POSIX shell unavailable')
    result = subprocess.run([shell, str(artifact / 'prepare-macos.sh'), '--help'],
                            env={'PATH': '', 'HOME': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode == 0 and 'does not enable' in result.stdout
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(sys.platform != 'darwin', reason='native macOS shell entry')
def test_shell_preserves_changed_bootstrap_binary(artifact, tmp_path):
    import platform
    target = 'aarch64' if platform.machine() == 'arm64' else 'x86_64'
    data = tmp_path / 'data'
    executable = data / f'tools/uv-0.12.10-{target}-apple-darwin'
    executable.parent.mkdir(parents=True)
    executable.write_text('user edit', encoding='utf-8')
    result = subprocess.run(['/bin/sh', str(artifact / 'prepare-macos.sh')],
                            env={'PATH': '', 'HOME': str(tmp_path), 'DASEN_DATA_ROOT': str(data)},
                            capture_output=True, text=True)
    assert result.returncode == 1 and 'existing uv executable changed' in result.stderr
    assert executable.read_text() == 'user edit'
    assert not (data / 'releases').exists()


@pytest.mark.skipif(sys.platform != 'darwin', reason='native macOS shell entry')
def test_shell_rejects_nested_storage_before_download(artifact, tmp_path):
    result = subprocess.run(['/bin/sh', str(artifact / 'prepare-macos.sh')],
                            env={'PATH': '', 'HOME': str(tmp_path),
                                 'DASEN_DATA_ROOT': str(artifact / 'data')},
                            capture_output=True, text=True)
    assert result.returncode == 1 and 'outside the artifact' in result.stderr
    assert not (artifact / 'data').exists()
