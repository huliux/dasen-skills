#!/usr/bin/env python3
"""Plan/apply project bindings, inspect state, uninstall or recover an interrupted switch."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from install_state import finish_transaction, read_json, record_dir
from prepare_runtime import preparation_lock
from project_bindings import apply, checked_runtime, inspect, plan


def storage_inventory(data: Path) -> dict:
    projects = []
    protected = set()
    uncertain = []
    for record in sorted((data / 'projects').glob('*')):
        try:
            state = read_json(record / 'state.json')
            project = Path(state['project'])
            if not project.is_dir() or (record / 'pending.json').exists():
                raise ValueError('Project missing or recovery pending')
            status = inspect(data, project, check_runtime=False)
            projects.append({'project': str(project), 'status': status['status']})
            if status.get('ready'):
                protected.add(status['ready'])
        except (OSError, ValueError, KeyError) as exc:
            uncertain.append({'record': str(record), 'reason': str(exc)})
    runtimes = []
    for ready in sorted((data / 'runtimes').glob('*/*/ready.json')):
        runtimes.append({'ready': str(ready), 'bytes': sum(p.stat().st_size for p in ready.parent.rglob('*')
                                                        if p.is_file() and not p.is_symlink()),
                         'reference': 'registered-current' if str(ready) in protected else 'not-proven-unused'})
    return {'status': 'inventory-only', 'projects': projects, 'uncertain': uncertain,
            'runtimes': runtimes, 'deleted': [],
            'reason': 'Retained: receipts cannot prove absence of direct or unregistered use. No whole-machine scan or deletion is performed.'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply', 'status', 'uninstall', 'recover', 'cleanup'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--data-root', type=Path,
                        default=Path.home() / 'Library/Application Support/dasen-skills')
    parser.add_argument('--ready', type=Path, help='Managed generation ready.json; also selects an older version for rollback')
    parser.add_argument('--host', action='append', choices=['codex', 'claude-code'], default=[])
    parser.add_argument('--rebind', action='store_true', help='Rebuild from an exact portable selection on a fresh clone')
    parser.add_argument('--finish', action='store_true', help='Finish an interrupted switch (default recovery rolls back)')
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'darwin':
            raise ValueError('This binding route currently supports macOS only')
        data = args.data_root.expanduser().resolve()
        if args.action == 'cleanup':
            result = storage_inventory(data)
        else:
            if args.project is None:
                raise ValueError('Specify the intended consumer project with --project')
            project = args.project.expanduser().resolve()
            ready = args.ready.expanduser().absolute() if args.ready else None
            if args.action in {'plan', 'apply'} and ready is None:
                raise ValueError('Select a verified runtime using --ready')
            if args.action == 'status':
                result = inspect(data, project)
            elif args.action == 'plan':
                proposal = plan(data, project, ready, args.host, rebind=args.rebind)
                result = {'status': 'plan-only', 'project': str(project), 'hosts': proposal['new']['hosts'],
                          'runtime': proposal['runtime'], 'shared_discovery': True,
                          'inherited_entries': proposal['inherited_entries'],
                          'managed_paths': sorted(proposal['desired']), 'native_discovery': 'unverified'}
            else:
                os.umask(0o077)
                with preparation_lock(data):
                    if args.action == 'recover':
                        record = record_dir(data, project)
                        journal = read_json(record / 'pending.json')
                        if args.finish and journal['state_after']['binding']:
                            binding = read_json(record / journal['state_after']['binding'] / 'binding.json')
                            checked_runtime(data, Path(binding['ready']))
                        finish_transaction(record, project, journal, forward=args.finish)
                        result = inspect(data, project)
                    else:
                        result = apply(data, project, ready, args.host, uninstall=args.action == 'uninstall', rebind=args.rebind)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['status'] == 'recovery-required' else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
