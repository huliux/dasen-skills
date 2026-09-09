#!/usr/bin/env python3
"""Run one frozen conversational turn and retain per-turn filesystem evidence.

Preparation uses artifact_eval.py with a suite containing optional followups.
Sessions persist for explicit-ID resume. Each case has a fresh first context.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import time

from artifact_eval import command_output, digest, read_json, write_json


def full_inventory(root: Path) -> dict[str, str]:
    # Include caches: status-only acceptance really means no workspace writes.
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def run_turn(run: Path, case_id: str, turn: int, model: str, effort: str, timeout: int) -> int:
    manifest = read_json(run / 'manifest.json')
    if case_id not in manifest['cases'] or turn < 1:
        raise ValueError('unknown case or invalid turn')
    base = run / case_id
    prompt = base / ('prompt.txt' if turn == 1 else f'prompt-{turn}.txt')
    expected = (manifest['cases'][case_id]['prompt_sha256'] if turn == 1
                else manifest['cases'][case_id].get('followups', {}).get(prompt.name))
    if not prompt.is_file() or digest(prompt) != expected:
        raise ValueError('missing or changed frozen prompt')
    output = base / f'turn-{turn}'
    if output.exists():
        raise ValueError('turn already started; preserve evidence and prepare a new case for retries')
    previous = None
    if turn > 1:
        previous = read_json(base / f'turn-{turn - 1}/execution.json')
        if previous['status'] != 'completed' or not previous.get('thread_id'):
            raise ValueError('previous turn did not complete with a resumable session')
        if (previous['model'], previous['effort']) != (model, effort):
            raise ValueError('model settings changed within a case')
    output.mkdir()
    workspace = base / 'workspace'
    before = full_inventory(workspace)
    write_json(output / 'before.json', before)
    cmd = ['codex', 'exec', '--ignore-user-config', '--skip-git-repo-check',
           '--sandbox', 'workspace-write', '--model', model, '-c', f'model_reasoning_effort="{effort}"',
           '--cd', str(workspace), '--json', '--output-last-message', str(output / 'final.md')]
    cmd += ['resume', previous['thread_id'], '-'] if previous else ['-']
    execution = {'status': 'running', 'model': model, 'effort': effort, 'command': cmd,
                 'harness': command_output('codex', '--version'), 'turn': turn}
    write_json(output / 'execution.json', execution)
    start = time.monotonic()
    code = 1
    try:
        with (output / 'trace.jsonl').open('w') as trace, (output / 'stderr.txt').open('w') as errors:
            result = subprocess.run(cmd, input=prompt.read_text(), text=True, cwd=workspace,
                                    stdout=trace, stderr=errors, timeout=timeout, check=False,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        code = result.returncode
        execution.update(status='completed' if code == 0 else 'failed', exit_code=code)
    except subprocess.TimeoutExpired:
        code = 124
        execution.update(status='timeout', exit_code=None)
    except OSError as exc:
        execution.update(status='failed', exit_code=None, error=str(exc))
    finally:
        import json
        events = []
        for line in (output / 'trace.jsonl').read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        execution['thread_id'] = next((e.get('thread_id') for e in events if e.get('type') == 'thread.started'),
                                      previous.get('thread_id') if previous else None)
        execution['usage'] = [e['usage'] for e in events if e.get('usage')]
        execution['elapsed_seconds'] = round(time.monotonic() - start, 2)
        after = full_inventory(workspace)
        write_json(output / 'after.json', after)
        execution['changed_files'] = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
        execution['assessment'] = 'NOT_ASSESSED'
        write_json(output / 'execution.json', execution)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--turn', type=int, default=1)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', default='high', choices=['low', 'medium', 'high', 'xhigh', 'max', 'ultra'])
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    try:
        return run_turn(args.run.resolve(), args.id, args.turn, args.model, args.effort, args.timeout)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
