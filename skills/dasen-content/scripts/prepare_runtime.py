#!/usr/bin/env python3
"""Prepare a complete artifact and an immutable local runtime; never enable a host."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

sys.dont_write_bytecode = True
from install_integrity import inspect_distribution


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifact(root: Path) -> dict:
    result = inspect_distribution(root)
    if result['status'] != 'ready':
        raise ValueError('Artifact verification failed; preserve edits and recover a complete '
                         'verified copy: ' + '; '.join(result['errors'][:8]))
    return result


@contextmanager
def preparation_lock(data: Path):
    import fcntl  # The current bootstrap route is macOS only.
    data.mkdir(parents=True, exist_ok=True)
    if (data / 'preparation.lock').is_symlink():
        raise ValueError('Preparation lock is a link; resolve ownership first.')
    with (data / 'preparation.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another preparation is active. Retry after it finishes.') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def command(arguments: list[str], phase: str, *, environment: dict, cwd: Path) -> str:
    try:
        result = subprocess.run(arguments, cwd=cwd, env=environment, capture_output=True,
                                text=True, encoding='utf-8', timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'{phase} could not finish. Previous ready environments are preserved; '
                         'check connectivity and retry.') from exc
    if result.returncode:
        if phase == 'Local readiness check':
            raise ValueError('Local checks failed. Run install_check.py --json with the reported '
                             'generation interpreter to inspect dependency/import/render failures.')
        # Package-manager output can contain authenticated index/proxy URLs. Do not persist it.
        raise ValueError(f'{phase} failed (exit {result.returncode}). Check access to the official '
                         'Python downloads and PyPI, disk space and file permissions; retry. '
                         'No previous ready environment was changed.')
    return result.stdout.strip()


def store_release(source: Path, data: Path, identity: str) -> Path:
    releases = data / 'releases'
    if releases.is_symlink():
        raise ValueError('Release storage is a link; resolve ownership first.')
    releases.mkdir(exist_ok=True)
    target = releases / identity
    if target.is_symlink():
        raise ValueError('Managed release path is a link; preserve it and resolve ownership first.')
    if target.exists():
        verify_artifact(target)
        if digest(target / 'artifact-manifest.json') != identity:
            raise ValueError('Stored release manifest changed; preserve it and recover explicitly.')
        return target
    staging = Path(tempfile.mkdtemp(prefix='.preparing-', dir=releases))
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True, symlinks=True)
        verify_artifact(staging)
        if digest(staging / 'artifact-manifest.json') != identity:
            raise ValueError('Source changed while copying; retry with a fixed artifact.')
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target


def runtime_identity(release: Path) -> dict:
    interpreter = Path(sys.executable).resolve()
    return {'release': digest(release / 'artifact-manifest.json'),
            'lock': digest(release / 'requirements.txt'), 'python': sys.version,
            'interpreter': str(interpreter), 'interpreter_sha256': digest(interpreter),
            'os': sys.platform, 'architecture': platform.machine()}


def local_check(python: Path, release: Path, environment: dict, cwd: Path) -> dict:
    output = command([str(python), '-B', str(release / 'skills/dasen-content/scripts/install_check.py'),
                      '--local-only', '--json'], 'Local readiness check',
                     environment=environment, cwd=cwd)
    checks = json.loads(output)
    if checks.get('local_readiness') != 'ready':
        raise ValueError('Local readiness is blocked; preserve this generation and prepare a repair.')
    return checks


def prepare(source: Path, data: Path, uv: Path, *, repair: bool = False) -> dict:
    metadata = verify_artifact(source)
    if data == source or source in data.parents or data in source.parents:
        raise ValueError('Data storage and input artifact must be separate directory trees.')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('UV_', 'PIP_', 'PYTHON', 'VIRTUAL_ENV'))}
    for key in ('UV_CACHE_DIR', 'UV_PYTHON_INSTALL_DIR'):
        if key in os.environ:
            environment[key] = os.environ[key]
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    with preparation_lock(data):
        release = store_release(source, data, digest(source / 'artifact-manifest.json'))
        identity = runtime_identity(release)
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        generations = data / 'runtimes' / key
        if (data / 'runtimes').is_symlink() or generations.is_symlink():
            raise ValueError('Runtime storage is a link; resolve ownership first.')
        generations.mkdir(parents=True, exist_ok=True)
        generation = None
        checks = None
        if not repair:
            for candidate in sorted(generations.iterdir(), reverse=True):
                receipt = candidate / 'ready.json'
                if not receipt.is_file():
                    continue  # Interrupted generations are retained, never activated or repaired in place.
                if candidate.is_symlink() or receipt.is_symlink():
                    raise ValueError('Runtime ownership conflict: linked generation or receipt.')
                recorded = json.loads(receipt.read_text(encoding='utf-8'))
                if not isinstance(recorded, dict) or recorded.get('identity') != identity:
                    raise ValueError('Ready receipt changed; preserve it and use an explicit repair.')
                try:
                    checks = local_check(candidate / 'venv/bin/python', release, environment, data)
                except ValueError as exc:
                    raise ValueError('Existing ready runtime failed recheck. Preserve it; '
                                     'run again with --repair to prepare a new generation.') from exc
                generation = candidate
                break
        reused = generation is not None
        if generation is None:
            generation = generations / f'{time.time_ns():020d}-{uuid.uuid4().hex}'
            generation.mkdir()
            venv = generation / 'venv'
            command([str(uv), '--no-config', 'venv', '--python', sys.executable,
                     '--no-python-downloads', str(venv)], 'Virtual environment preparation',
                    environment=environment, cwd=data)
            command([str(uv), '--no-config', 'pip', 'sync', '--python', str(venv / 'bin/python'),
                     '--require-hashes', '--only-binary', ':all:', '--link-mode', 'copy',
                     '--default-index', 'https://pypi.org/simple',
                     str(release / 'requirements.txt')], 'Locked dependency download',
                    environment=environment, cwd=data)
            checks = local_check(venv / 'bin/python', release, environment, data)
            receipt = {'schema_version': 1, 'owner': 'dasen-artifact', 'identity': identity,
                       'generation': str(generation), 'checks': checks}
            pending = generation / 'ready.pending.json'
            pending.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            pending.replace(generation / 'ready.json')
        return {'schema_version': 1, 'status': 'local-ready', 'owner': 'dasen-artifact',
                'source_revision': metadata['source_revision'], 'release_id': identity['release'],
                'artifact_root': str(release), 'python': str(generation / 'venv/bin/python'),
                'receipt': str(generation / 'ready.json'), 'reused': reused,
                'uv': str(uv), 'managed_python': str(Path(sys.executable).resolve()),
                'download_cache': command([str(uv), '--no-config', 'cache', 'dir'],
                                          'Cache location', environment=environment, cwd=data),
                'enabled_scope': 'none', 'native_discovery': 'unverified',
                'first_creation': 'not-run',
                'next_action': 'Bind the six Skills to the chosen project/host and verify native discovery.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--uv', type=Path, required=True)
    parser.add_argument('--repair', action='store_true', help='Prepare a new runtime generation; preserve old ones')
    args = parser.parse_args()
    try:
        if sys.platform != 'darwin':
            raise ValueError('This preparation route currently supports macOS only.')
        result = prepare(args.artifact_root.expanduser().resolve(), args.data_root.expanduser().resolve(),
                         args.uv.expanduser().resolve(), repair=args.repair)
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc), 'enabled_scope': 'none'}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
