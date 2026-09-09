"""Version selection and project bindings; filesystem readiness is not native discovery."""
from __future__ import annotations

import json
from pathlib import Path
import platform
import subprocess
import uuid

from install_integrity import PUBLIC_SKILLS
from install_state import (HOST_ROOTS, LOCAL, SELECTION, atomic_json, file_value, ignore_block, ignored_value,
                           load_state, project_path, read_json, record_dir, snapshot,
                           transact, validate_files)
from prepare_runtime import digest, verify_artifact

RUNNER = '''#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd -P)
binding=$(CDPATH= cd -- "$root/binding" && pwd -P)
exec "$binding/runtime/bin/python" -E -s -B "$binding/release/skills/dasen-content/scripts/project_run.py" "$binding" "$@"
'''


def checked_runtime(data: Path, ready: Path) -> dict:
    if ready.is_symlink() or not ready.is_file():
        raise ValueError('Use an existing regular ready.json from managed runtime preparation')
    relative = ready.relative_to(data)
    if len(relative.parts) != 4 or relative.parts[0] != 'runtimes' or relative.name != 'ready.json':
        raise ValueError('Runtime receipt must belong to this data store')
    for parent in ready.parents:
        if parent == data:
            break
        if parent.is_symlink():
            raise ValueError('Runtime receipt parents must not be links')
    record = read_json(ready)
    identity = record.get('identity', {})
    if record.get('owner') != 'dasen-artifact' or record.get('generation') != str(ready.parent):
        raise ValueError('Runtime ownership mismatch')
    release_id = identity.get('release', '')
    if not isinstance(release_id, str) or len(release_id) != 64 or any(c not in '0123456789abcdef' for c in release_id):
        raise ValueError('Invalid runtime release identity')
    release = data / 'releases' / release_id
    if release.is_symlink() or (data / 'releases').is_symlink():
        raise ValueError('Release storage is not owned by this route')
    metadata = verify_artifact(release)
    for script in ('project_run.py', 'install_state.py'):
        if not (release / 'skills/dasen-content/scripts' / script).is_file():
            raise ValueError('Release predates project binding support; use its original installation route')
    if digest(release / 'artifact-manifest.json') != release_id or digest(release / 'requirements.txt') != identity.get('lock'):
        raise ValueError('Release/lock identity changed')
    python = ready.parent / 'venv/bin/python'
    query = 'import sys,platform,json; print(json.dumps([sys.version,sys._base_executable,sys.platform,platform.machine()]))'
    result = subprocess.run([str(python), '-I', '-B', '-c', query], capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode:
        raise ValueError('Runtime interpreter failed; prepare an explicit repair')
    version, executable, system, architecture = json.loads(result.stdout)
    if (version != identity.get('python') or str(Path(executable).resolve()) != identity.get('interpreter')
            or digest(Path(executable).resolve()) != identity.get('interpreter_sha256')
            or system != identity.get('os') or architecture != identity.get('architecture')
            or system != 'darwin' or architecture != platform.machine()):
        raise ValueError('Runtime Python/platform identity changed')
    check = subprocess.run([str(python), '-E', '-s', '-B', str(release / 'skills/dasen-content/scripts/install_check.py'),
                            '--local-only', '--json'], capture_output=True, text=True, timeout=60, check=False)
    if check.returncode:
        raise ValueError('Runtime local check failed; run install_check.py with this interpreter for details')
    if json.loads(check.stdout).get('local_readiness') != 'ready':
        raise ValueError('Runtime is not locally ready')
    return {'release_id': release_id, 'source_revision': metadata['source_revision'],
            'release': str(release), 'python': str(python), 'runtime': str(python.parent.parent), 'ready': str(ready)}


def inherited_entries(project: Path, hosts: list[str]) -> list[str]:
    roots = {parent / root for parent in project.parents for root in HOST_ROOTS.values()}
    roots.update(Path.home() / root for root in ('.agents/skills', '.claude/skills', '.codex/skills'))
    found = []
    for root in sorted(roots):
        for name in PUBLIC_SKILLS:
            for candidate in (name, name.replace('dasen-', 'bitbook-', 1)):
                path = root / candidate
                if path.exists() or path.is_symlink():
                    found.append(str(path))
    return found


def binding_metadata(record: Path, state: dict) -> dict:
    binding = state.get('binding')
    if not isinstance(binding, str) or not binding.startswith('bindings/') or len(Path(binding).parts) != 2:
        raise ValueError('Invalid project binding identity')
    directory = record / binding
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError('Binding metadata must be an owned directory')
    metadata = read_json(directory / 'binding.json')
    for name in ('release', 'runtime'):
        if snapshot(directory / name) != {'kind': 'link', 'target': metadata[name]}:
            raise ValueError(f'Binding {name} changed; preserve and inspect it')
    return metadata


def inspect(data: Path, project: Path, *, check_runtime: bool = True) -> dict:
    record = record_dir(data, project)
    if (record / 'pending.json').exists():
        return {'status': 'recovery-required', 'project': str(project), 'journal': str(record / 'pending.json')}
    state = load_state(record, project)
    if not state['hosts']:
        return {'status': 'not-bound', 'project': str(project), 'shared_storage_retained': True}
    validate_files(project, state)
    if snapshot(record / 'current') != {'kind': 'link', 'target': state['binding']}:
        raise ValueError('Project version pointer changed; preserve and inspect it')
    metadata = binding_metadata(record, state)
    if check_runtime:
        checked_runtime(data, Path(metadata['ready']))
    history = []
    for item in sorted((record / 'bindings').glob('*/binding.json')):
        value = read_json(item)
        history.append({'release_id': value['release_id'], 'ready': value['ready']})
    return {'status': 'bound-locally', 'project': str(project), 'owner': 'dasen-artifact',
            'hosts': state['hosts'], 'shared_discovery': True, **metadata,
            'native_discovery': 'unverified', 'refresh_required': state['hosts'],
            'inherited_entries': inherited_entries(project, state['hosts']),
            'discovery_limit': 'Inherited skills, host settings and plugins require native inspection; no exclusive host visibility is claimed.',
            'first_creation': 'not-run', 'rollback_choices': history}


def selection(runtime: dict, hosts: list[str]) -> dict:
    return {'schema_version': 1, 'release_id': runtime['release_id'],
            'source_revision': runtime['source_revision'], 'hosts': hosts, 'shared_discovery': True}


def plan(data: Path, project: Path, ready: Path | None, hosts: list[str], *, uninstall: bool = False, rebind: bool = False) -> dict:
    if not project.is_dir() or project == data or project in data.parents or data in project.parents:
        raise ValueError('Use an existing project separate from data storage')
    record = record_dir(data, project)
    if (record / 'pending.json').exists():
        raise ValueError('Interrupted switch: run recover before another change')
    old = load_state(record, project)
    if rebind:
        if old['hosts']:
            raise ValueError('Project already has a local owner; use its normal update path')
        portable = read_json(project_path(project, SELECTION))
        portable_hosts = portable.get('hosts', [])
        if not portable_hosts or set(portable_hosts) - HOST_ROOTS.keys():
            raise ValueError('Invalid portable host selection')
        runtime = checked_runtime(data, ready)
        if portable != selection(runtime, sorted(portable_hosts)):
            raise ValueError('Prepare the exact portable release before rebind; do not silently upgrade it')
        hosts = sorted(set(hosts) | set(portable_hosts))
        old['files'][SELECTION] = snapshot(project / SELECTION)
        existing_ignore = (project / '.gitignore').read_text() if (project / '.gitignore').is_file() else ''
        block = ignore_block(sorted(portable_hosts))
        if block in existing_ignore:
            old['ignore_block'] = block
    validate_files(project, old)
    if old['hosts']:
        inspect(data, project, check_runtime=False)
        if not uninstall:
            verify_artifact(Path(binding_metadata(record, old)['release']))
    chosen = [] if uninstall else sorted(set(old['hosts']) | set(hosts))
    if set(chosen) - HOST_ROOTS.keys() or (not uninstall and not chosen):
        raise ValueError('Choose codex and/or claude-code explicitly for the first binding')
    runtime = checked_runtime(data, ready) if not uninstall else None
    desired = {}
    if chosen:
        desired[SELECTION] = file_value(json.dumps(selection(runtime, chosen), indent=2) + '\n', 0o644)
        desired[f'{LOCAL}/run'] = file_value(RUNNER, 0o700)
        desired[f'{LOCAL}/binding'] = {'kind': 'link', 'target': str(record / 'current')}
        for host in chosen:
            for name in PUBLIC_SKILLS:
                desired[f'{HOST_ROOTS[host]}/{name}'] = {
                    'kind': 'link', 'target': f'../../{LOCAL}/binding/release/skills/{name}'}
    for name in desired:
        if name not in old['files'] and (project_path(project, name).exists() or project_path(project, name).is_symlink()):
            raise ValueError(f'Unowned project entry already exists: {name}; preserve it and use its owner to migrate')
    for name in old['files'].keys() - desired.keys():
        desired[name] = {'kind': 'absent'}
    ignore_before = snapshot(project_path(project, '.gitignore'))
    ignore, block = ignored_value(project, old, chosen)
    if snapshot(project_path(project, '.gitignore')) != ignore_before:
        raise ValueError('.gitignore changed during planning; retry')
    desired['.gitignore'] = ignore
    new = {**old, 'hosts': chosen, 'files': {k: v for k, v in desired.items()
                                          if k != '.gitignore' and v['kind'] != 'absent'},
           'ignore_block': block, 'binding': None,
           'ignore_was_absent': old.get('ignore_was_absent', snapshot(project / '.gitignore')['kind'] == 'absent')}
    baseline = {name: old['files'].get(name, {'kind': 'absent'}) for name in desired}
    baseline['.gitignore'] = ignore_before
    return {'old': old, 'new': new, 'desired': desired, 'baseline': baseline, 'runtime': runtime,
            'record': str(record), 'project': str(project), 'shared_discovery': True,
            'inherited_entries': inherited_entries(project, chosen)}


def apply(data: Path, project: Path, ready: Path | None, hosts: list[str], *, uninstall: bool = False, rebind: bool = False) -> dict:
    proposal = plan(data, project, ready, hosts, uninstall=uninstall, rebind=rebind)
    old, new = proposal['old'], proposal['new']
    if uninstall and not old['hosts']:
        return {'status': 'not-bound', 'changed': False, 'shared_storage_retained': True}
    record = Path(proposal['record'])
    runtime = proposal['runtime']
    if old['hosts'] and runtime and binding_metadata(record, old) == runtime:
        new['binding'] = old['binding']
    if not (record / 'state.json').exists():
        record.mkdir(parents=True, exist_ok=True)
        atomic_json(record / 'state.json', old)
    if new['hosts'] and not new['binding']:
        new['binding'] = f'bindings/{uuid.uuid4().hex}'
        directory = record / new['binding']
        directory.mkdir(parents=True)
        for name in ('release', 'runtime'):
            (directory / name).symlink_to(runtime[name])
        atomic_json(directory / 'binding.json', runtime)
    if old == new and all(snapshot(project_path(project, k)) == v for k, v in proposal['desired'].items()):
        return {**inspect(data, project, check_runtime=False), 'changed': False}
    transact(record, project, old, new, proposal['desired'], proposal['baseline'])
    if uninstall:
        directory = project / LOCAL
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    return {**inspect(data, project, check_runtime=False), 'changed': True}
