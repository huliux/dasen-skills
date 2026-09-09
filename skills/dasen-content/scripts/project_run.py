"""Run a selected Skill script using one captured project binding."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

sys.dont_write_bytecode = True
from install_integrity import PUBLIC_SKILLS
from install_state import SELECTION, read_json


def run(binding: Path, relative: str, arguments: list[str]) -> int:
    record = binding.parent.parent
    if (record / 'pending.json').exists():
        raise ValueError('Project switch is incomplete; recover it before content execution')
    state = read_json(record / 'state.json')
    project = Path(state['project'])
    if (record / 'current').resolve() != binding:
        raise ValueError('Project version changed; refresh the binding before starting this call')
    metadata = read_json(binding / 'binding.json')
    selected = read_json(project / SELECTION)
    if selected.get('release_id') != metadata.get('release_id'):
        raise ValueError('Portable version selection differs from this machine; rebind before running')
    path = PurePosixPath(relative)
    if (path.is_absolute() or '..' in path.parts or len(path.parts) < 3
            or path.parts[0] not in PUBLIC_SKILLS or path.parts[1] != 'scripts'
            or path.suffix != '.py' or '\\' in relative):
        raise ValueError('Use <dasen-skill>/scripts/<script>.py relative to the selected release')
    release = (binding / 'release').resolve()
    script = (release / 'skills' / path).resolve()
    if not script.is_relative_to(release / 'skills') or not script.is_file():
        raise ValueError('Script does not belong to the selected complete release')
    # Interpreter flags are not inherited by nested Python subprocesses.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('PYTHON')}
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    return subprocess.run([sys.executable, '-E', '-s', '-B', str(script), *arguments],
                          cwd=project, env=environment, check=False).returncode


if __name__ == '__main__':
    try:
        if len(sys.argv) < 3:
            raise ValueError('Usage: .dasen-skills/run <dasen-skill>/scripts/<script>.py [arguments]')
        code = run(Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3:])
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        code = 1
    raise SystemExit(code)
