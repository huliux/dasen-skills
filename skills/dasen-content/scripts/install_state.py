"""Owned project files and recoverable transactions for the macOS artifact route."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

from install_integrity import PUBLIC_SKILLS

HOST_ROOTS = {'codex': '.agents/skills', 'claude-code': '.claude/skills'}
SELECTION = 'dasen-skills.lock.json'
LOCAL = '.dasen-skills'
IGNORE_START = '# BEGIN DASEN SKILLS MANAGED\n'
IGNORE_END = '# END DASEN SKILLS MANAGED\n'
ALLOWED = {SELECTION, '.gitignore', f'{LOCAL}/binding', f'{LOCAL}/run',
           *(f'{root}/{name}' for root in HOST_ROOTS.values() for name in PUBLIC_SKILLS)}


def read_json(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError(f'Record is a link; preserve it: {path}')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'Expected an object: {path}')
    return value


def atomic_json(path: Path, value: dict) -> None:
    write_value(path, file_value(json.dumps(value, ensure_ascii=False, indent=2) + '\n'))


def file_value(text: str, mode: int = 0o600) -> dict:
    return {'kind': 'file', 'data': base64.b64encode(text.encode()).decode(), 'mode': mode}


def snapshot(path: Path) -> dict:
    if path.is_symlink():
        return {'kind': 'link', 'target': os.readlink(path)}
    if not path.exists():
        return {'kind': 'absent'}
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f'Conflicting directory or oversized file; preserve it: {path}')
    return {'kind': 'file', 'data': base64.b64encode(path.read_bytes()).decode(),
            'mode': path.stat().st_mode & 0o777}


def write_value(path: Path, value: dict) -> None:
    kind = value['kind']
    if kind == 'absent':
        if path.is_symlink() or path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.dasen-write-', dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        if kind == 'link':
            temporary.unlink()
            temporary.symlink_to(value['target'])
        elif kind == 'file':
            with temporary.open('wb') as handle:
                handle.write(base64.b64decode(value['data'], validate=True))
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(value['mode'])
        else:
            raise ValueError('Unknown file state')
        os.replace(temporary, path)
    finally:
        if temporary.is_symlink() or temporary.exists():
            temporary.unlink()


def project_path(project: Path, relative: str) -> Path:
    if relative not in ALLOWED:
        raise ValueError(f'Unexpected managed project path: {relative}')
    path = project / relative
    for parent in path.parents:
        if parent == project:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f'Project discovery/storage parent is not an owned directory: {parent}')
    return path


def record_dir(data: Path, project: Path) -> Path:
    key = hashlib.sha256(os.fsencode(str(project))).hexdigest()
    records = data / 'projects'
    record = records / key
    if records.is_symlink() or record.is_symlink():
        raise ValueError('Project record storage must not be a link')
    return record


def load_state(record: Path, project: Path) -> dict:
    if not (record / 'state.json').exists():
        if record.exists() and any(record.iterdir()):
            raise ValueError('Unowned or incomplete project record; inspect/recover it first')
        return {'schema_version': 1, 'owner': 'dasen-artifact', 'project': str(project),
                'hosts': [], 'files': {}, 'ignore_block': '', 'binding': None}
    state = read_json(record / 'state.json')
    if (state.get('schema_version') != 1 or state.get('owner') != 'dasen-artifact'
            or state.get('project') != str(project) or not isinstance(state.get('files'), dict)
            or set(state.get('hosts', [])) - HOST_ROOTS.keys()):
        raise ValueError('Project record identity mismatch; preserve and inspect it')
    return state


def ignore_block(hosts: list[str]) -> str:
    if not hosts:
        return ''
    lines = [f'/{LOCAL}/', *(f'/{HOST_ROOTS[host]}/{name}'
                           for host in hosts for name in PUBLIC_SKILLS)]
    return '\n' + IGNORE_START + '\n'.join(lines) + '\n' + IGNORE_END


def ignored_value(project: Path, old: dict, hosts: list[str]) -> tuple[dict, str]:
    path = project_path(project, '.gitignore')
    current = snapshot(path)
    if current['kind'] not in {'absent', 'file'}:
        raise ValueError('Linked .gitignore is not managed by this installer')
    text = base64.b64decode(current.get('data', '')).decode('utf-8')
    block = old.get('ignore_block', '')
    if block:
        if text.count(block) != 1:
            raise ValueError('Managed .gitignore block changed; preserve edits and reconcile it')
        text = text.replace(block, '', 1)
    if IGNORE_START in text or IGNORE_END in text:
        raise ValueError('An unowned Dasen ignore block exists; resolve ownership first')
    new = ignore_block(hosts)
    if not text and not new and old.get('ignore_was_absent'):
        return {'kind': 'absent'}, new
    return file_value(text + new, current.get('mode', 0o644)), new


def validate_files(project: Path, state: dict) -> None:
    for relative, expected in state['files'].items():
        if snapshot(project_path(project, relative)) != expected:
            raise ValueError(f'Installed file changed: {relative}; preserve edits and resolve the difference')
    ignored_value(project, state, state['hosts'])


def finish_transaction(record: Path, project: Path, journal: dict, *, forward: bool) -> None:
    if journal.get('project') != str(project) or journal.get('schema_version') != 1:
        raise ValueError('Recovery journal identity mismatch')
    entries = journal['entries']
    for relative, values in entries.items():
        actual = snapshot(project_path(project, relative))
        if actual not in (values['before'], values['after']):
            raise ValueError(f'Recovery found a later edit at {relative}; preserve it and resolve manually')
    pointer = snapshot(record / 'current')
    if pointer not in (journal['pointer_before'], journal['pointer_after']):
        raise ValueError('Recovery found a changed version pointer; preserve it')
    if (record / 'state.json').exists():
        if read_json(record / 'state.json') not in (journal['state_before'], journal['state_after']):
            raise ValueError('Recovery found a changed ownership record; preserve it')
    side = 'after' if forward else 'before'
    # Every discovery link goes through this one pointer, so version activation is one replace.
    for relative, values in entries.items():
        path = project_path(project, relative)
        if snapshot(path) not in (values['before'], values['after']):
            raise ValueError(f'Recovery found a concurrent edit at {relative}; preserve it')
        write_value(path, values[side])
    write_value(record / 'current', journal[f'pointer_{side}'])
    atomic_json(record / 'state.json', journal[f'state_{side}'])
    (record / 'pending.json').unlink()


def transact(record: Path, project: Path, old: dict, new: dict, desired: dict, baseline: dict) -> None:
    if (record / 'pending.json').exists():
        raise ValueError('An interrupted switch needs explicit recovery first')
    for name, expected in baseline.items():
        if snapshot(project_path(project, name)) != expected:
            raise ValueError(f'Project changed after planning: {name}; preserve it and plan again')
    entries = {name: {'before': baseline[name], 'after': value}
               for name, value in desired.items()}
    journal = {'schema_version': 1, 'project': str(project), 'entries': entries,
               'pointer_before': snapshot(record / 'current'),
               'pointer_after': ({'kind': 'link', 'target': new['binding']}
                                 if new['binding'] else {'kind': 'absent'}),
               'state_before': old, 'state_after': new}
    atomic_json(record / 'pending.json', journal)
    try:
        finish_transaction(record, project, journal, forward=True)
    except Exception:
        # A hard process kill leaves the journal; normal errors attempt an exact rollback.
        if (record / 'pending.json').exists():
            finish_transaction(record, project, journal, forward=False)
        raise
