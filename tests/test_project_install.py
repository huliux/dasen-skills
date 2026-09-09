"""Project version switches preserve other projects, content and user edits."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'skills/dasen-content/scripts'))
import build_public
import install_state as state
import project_bindings as bindings
from project_install import storage_inventory
from prepare_runtime import digest, runtime_identity

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='macOS artifact binding route')


@pytest.fixture
def installation(tmp_path):
    data = tmp_path / 'shared data'
    data.mkdir()
    ready = []
    for revision in ['a', 'b']:
        artifact = tmp_path / revision
        build_public.build_snapshot(ROOT, revision * 40, artifact, run_tests=False, kind='install')
        release = data / 'releases' / digest(artifact / 'artifact-manifest.json')
        release.parent.mkdir(exist_ok=True)
        artifact.rename(release)
        identity = runtime_identity(release)
        generation = data / 'runtimes' / (revision * 64) / 'generation'
        venv = generation / 'venv'
        (venv / 'bin').mkdir(parents=True)
        (venv / 'bin/python').symlink_to(sys.executable)
        shutil.copyfile(Path(sys.prefix) / 'pyvenv.cfg', venv / 'pyvenv.cfg')
        site = Path('lib') / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
        (venv / site).parent.mkdir(parents=True)
        (venv / site).symlink_to(Path(sys.prefix) / site, target_is_directory=True)
        receipt = generation / 'ready.json'
        state.atomic_json(receipt, {'schema_version': 1, 'owner': 'dasen-artifact',
                                    'generation': str(generation), 'identity': identity})
        ready.append(receipt)
    project = tmp_path / '中文 project'
    project.mkdir()
    (project / 'article.md').write_text('preserve user content', encoding='utf-8')
    return data, project, ready


def apply(installation, version=0, hosts=None, **kwargs):
    data, project, ready = installation
    return bindings.apply(data, project, ready[version], hosts or [], **kwargs)


def test_plan_is_read_only_and_initial_apply_selects_only_requested_host(installation):
    data, project, ready = installation
    plan = bindings.plan(data, project, ready[0], ['codex'])
    assert plan['shared_discovery']
    assert not (data / 'projects').exists() and not (project / state.SELECTION).exists()
    result = apply(installation, hosts=['codex'])
    assert result['native_discovery'] == 'unverified' and result['refresh_required'] == ['codex']
    assert len(list((project / '.agents/skills').iterdir())) == 6
    assert not (project / '.claude').exists()
    portable = (project / state.SELECTION).read_text()
    assert str(data) not in portable and str(project) not in portable
    assert json.loads(portable)['release_id'] == result['release_id']


def test_two_projects_share_runtime_and_upgrade_independently(installation):
    data, project, ready = installation
    one = apply(installation, hosts=['codex'])
    other = project.parent / 'other'
    other.mkdir()
    two = bindings.apply(data, other, ready[0], ['claude-code'])
    assert one['python'] == two['python'] and one['release'] == two['release']
    upgraded = apply(installation, 1)
    assert upgraded['release'] != one['release']
    assert bindings.inspect(data, other)['release'] == one['release']
    assert (other / '.claude/skills/dasen-content').resolve() == Path(one['release']) / 'skills/dasen-content'


def test_two_hosts_switch_through_one_pointer_and_rollback(installation):
    data, project, ready = installation
    first = apply(installation, hosts=['codex', 'claude-code'])
    old_links = {str(p): p.readlink() for p in project.glob('.*/*/dasen-*')}
    updated = apply(installation, 1)
    for root in state.HOST_ROOTS.values():
        for name in state.PUBLIC_SKILLS:
            path = project / root / name
            assert path.resolve() == Path(updated['release']) / 'skills' / name
            assert path.readlink() == old_links[str(path)]
    reverted = apply(installation)
    assert reverted['release'] == first['release'] and (project / 'article.md').read_text() == 'preserve user content'
    repeat = apply(installation)
    assert repeat['changed'] is False


def test_user_edits_block_replacement_and_uninstall(installation):
    data, project, ready = installation
    apply(installation, hosts=['codex'])
    runner = project / '.dasen-skills/run'
    runner.write_text('user edit')
    for uninstall in [False, True]:
        with pytest.raises(ValueError, match='Installed file changed'):
            apply(installation, 1, uninstall=uninstall)
        assert runner.read_text() == 'user edit'


def test_unowned_entry_is_never_replaced(installation):
    data, project, ready = installation
    entry = project / '.agents/skills/dasen-content'
    entry.mkdir(parents=True)
    (entry / 'SKILL.md').write_text('another manager')
    with pytest.raises(ValueError, match='Unowned project entry'):
        apply(installation, hosts=['codex'])
    assert (entry / 'SKILL.md').read_text() == 'another manager'
    assert not (data / 'projects').exists()


def test_modified_shared_artifact_blocks_all_updates(installation):
    result = apply(installation, hosts=['codex'])
    skill = Path(result['release']) / 'skills/dasen-content/SKILL.md'
    skill.write_text('user edit')
    with pytest.raises(ValueError, match='hash mismatch'):
        apply(installation, 1)
    assert skill.read_text() == 'user edit'


def test_uninstall_keeps_content_other_ignore_rules_and_shared_storage(installation):
    data, project, ready = installation
    (project / '.gitignore').write_text('user-before\n')
    result = apply(installation, hosts=['codex', 'claude-code'])
    with (project / '.gitignore').open('a') as handle:
        handle.write('user-after\n')
    removed = apply(installation, uninstall=True)
    assert removed['status'] == 'not-bound'
    assert (project / '.gitignore').read_text() == 'user-before\nuser-after\n'
    assert (project / 'article.md').read_text() == 'preserve user content'
    assert not (project / state.SELECTION).exists() and not (project / '.dasen-skills').exists()
    assert Path(result['release']).is_dir() and ready[0].exists()


@pytest.mark.parametrize('forward', [False, True])
def test_interrupted_switch_recovers_without_mixed_hosts(installation, monkeypatch, forward):
    data, project, ready = installation
    first = apply(installation, hosts=['codex', 'claude-code'])
    original = state.write_value
    interrupted = False
    def writing(path, value):
        nonlocal interrupted
        original(path, value)
        if path.name == state.SELECTION and not interrupted:
            interrupted = True
            raise KeyboardInterrupt('simulated process interruption')
    monkeypatch.setattr(state, 'write_value', writing)
    with pytest.raises(KeyboardInterrupt):
        apply(installation, 1)
    assert bindings.inspect(data, project)['status'] == 'recovery-required'
    record = state.record_dir(data, project)
    journal = state.read_json(record / 'pending.json')
    monkeypatch.setattr(state, 'write_value', original)
    state.finish_transaction(record, project, journal, forward=forward)
    result = bindings.inspect(data, project)
    assert (result['release_id'] == first['release_id']) is (not forward)
    for root in state.HOST_ROOTS.values():
        assert (project / root / 'dasen-content').resolve() == Path(result['release']) / 'skills/dasen-content'


def test_recovery_preserves_later_user_edits(installation, monkeypatch):
    data, project, ready = installation
    apply(installation, hosts=['codex'])
    original = state.write_value
    def writing(path, value):
        original(path, value)
        if path.name == state.SELECTION:
            raise KeyboardInterrupt()
    monkeypatch.setattr(state, 'write_value', writing)
    with pytest.raises(KeyboardInterrupt):
        apply(installation, 1)
    record = state.record_dir(data, project)
    selection = project / state.SELECTION
    selection.write_text('later user edit')
    with pytest.raises(ValueError, match='later edit'):
        state.finish_transaction(record, project, state.read_json(record / 'pending.json'), forward=False)
    assert selection.read_text() == 'later user edit'


def test_clone_rebind_uses_portable_selection(installation):
    data, project, ready = installation
    first = apply(installation, hosts=['codex'])
    clone = project.parent / 'clone'
    clone.mkdir()
    for name in [state.SELECTION, '.gitignore']:
        shutil.copyfile(project / name, clone / name)
    with pytest.raises(ValueError, match='exact portable release'):
        bindings.apply(data, clone, ready[1], [], rebind=True)
    result = bindings.apply(data, clone, ready[0], [], rebind=True)
    assert result['release_id'] == first['release_id']
    assert (clone / '.agents/skills/dasen-content').resolve() == Path(first['release']) / 'skills/dasen-content'


def test_runner_uses_selected_release_and_project_cwd(installation):
    data, project, ready = installation
    apply(installation, hosts=['codex'])
    result = subprocess.run(['/bin/sh', str(project / '.dasen-skills/run'),
                             'dasen-content/scripts/init_content.py', '--id', '2026-09-09-runner',
                             '--journey', 'material', '--length', 'quick', '--method', 'original',
                             '--objective', 'test', '--audience', 'reader', '--deliverable', 'article'],
                            cwd=project.parent, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / 'writing/2026-09-09/runner/brief.yaml').exists()
    escaped = subprocess.run(['/bin/sh', str(project / '.dasen-skills/run'), '../outside.py'],
                             capture_output=True, text=True)
    assert escaped.returncode == 1


def test_cleanup_retains_missing_project_and_unproven_resources(installation):
    data, project, ready = installation
    result = apply(installation, hosts=['codex'])
    inventory = storage_inventory(data)
    assert any(r['reference'] == 'registered-current' for r in inventory['runtimes'])
    project.rename(project.parent / 'moved')
    inventory = storage_inventory(data)
    assert inventory['uncertain'] and inventory['deleted'] == []
    assert Path(result['python']).exists()


def test_normal_switch_error_rolls_back_existing_working_state(installation, monkeypatch):
    data, project, ready = installation
    first = apply(installation, hosts=['codex', 'claude-code'])
    original = state.write_value
    failed = False
    def writing(path, value):
        nonlocal failed
        original(path, value)
        if path.name == 'current' and not failed:
            failed = True
            raise OSError('synthetic pointer-write error')
    monkeypatch.setattr(state, 'write_value', writing)
    with pytest.raises(OSError, match='synthetic'):
        apply(installation, 1)
    result = bindings.inspect(data, project)
    assert result['release_id'] == first['release_id']
    assert not (state.record_dir(data, project) / 'pending.json').exists()


def test_failed_runtime_check_makes_no_project_changes(installation):
    data, project, ready = installation
    payload = state.read_json(ready[0])
    payload['identity']['python'] = 'wrong interpreter identity'
    state.atomic_json(ready[0], payload)
    with pytest.raises(ValueError, match='identity changed'):
        apply(installation, hosts=['codex'])
    assert not (project / state.SELECTION).exists() and not (data / 'projects').exists()


def test_shared_discovery_parent_is_not_written_through(installation):
    data, project, ready = installation
    outside = project.parent / 'outside'
    outside.mkdir()
    (project / '.agents').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='parent'):
        apply(installation, hosts=['codex'])
    assert not list(outside.iterdir())


def test_uninstall_on_unbound_project_is_a_no_op(installation):
    data, project, ready = installation
    assert apply(installation, uninstall=True)['changed'] is False
    assert set(p.name for p in project.iterdir()) == {'article.md'}
    assert not (data / 'projects').exists()


def test_runner_blocks_an_interrupted_switch(installation):
    data, project, ready = installation
    apply(installation, hosts=['codex'])
    record = state.record_dir(data, project)
    state.atomic_json(record / 'pending.json', {'test': 'unfinished'})
    result = subprocess.run(['/bin/sh', str(project / '.dasen-skills/run'),
                             'dasen-content/scripts/init_project.py', '--project', 'must-not-exist'],
                            capture_output=True, text=True)
    assert result.returncode == 1 and 'incomplete' in result.stdout
    assert not (project / 'project.md').exists()


def test_runner_preserves_venv_imports_through_binding(installation):
    data, project, ready = installation
    apply(installation, hosts=['codex'])
    result = subprocess.run(['/bin/sh', str(project / '.dasen-skills/run'),
                             'dasen-content/scripts/install_check.py', '--local-only', '--json'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['local_readiness'] == 'ready'


def test_nested_render_refusal_preserves_artifact_and_python_isolation(installation, monkeypatch):
    data, project, ready = installation
    selected = apply(installation, hosts=['codex'])
    bundle = project / 'incomplete-bundle'
    bundle.mkdir()
    (bundle / 'article.md').write_text('Incomplete input must be refused without changing the runtime.')
    injected = project / 'foreign-python'
    injected.mkdir()
    marker = project / 'foreign-python-loaded'
    (injected / 'sitecustomize.py').write_text(
        f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
    monkeypatch.setenv('PYTHONPATH', str(injected))
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '0')
    result = subprocess.run(['/bin/sh', str(project / '.dasen-skills/run'),
                             'dasen-wechat/scripts/native_publish.py', '--dry-run', str(bundle)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'preflight did not pass' in result.stderr
    assert not list(Path(selected['release']).rglob('*.pyc'))
    assert not marker.exists()
    assert bindings.inspect(data, project)['status'] == 'bound-locally'
