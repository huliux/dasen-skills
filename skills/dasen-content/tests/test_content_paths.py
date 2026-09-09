from pathlib import Path
import os
import subprocess
import sys

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from content_paths import bundle_root, evidence_dir, select_content_root


def run(script, cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, capture_output=True, text=True)


def create(cwd, *args):
    result = run('init_content.py', cwd, '--id', '2026-09-09-layout-test', '--journey', 'material', '--length', 'quick', '--method', 'original', '--objective', 'Explain a verified result', '--audience', 'Readers', '--deliverable', 'Article', *args)
    assert result.returncode == 0, result.stderr
    return Path(yaml.safe_load(result.stdout)['bundle'])


def test_source_workspace_isolates_owned_files_and_ignores_unrelated_project(tmp_path):
    (tmp_path / '.git').mkdir()
    unrelated = tmp_path / 'project.md'; unrelated.write_text('# Software design\n')
    bundle = create(tmp_path)
    brief = yaml.safe_load((bundle / 'brief.yaml').read_text())
    assert bundle == tmp_path / 'content/writing/2026-09-09/layout-test'
    assert brief['configuration'] == 'standalone'
    assert brief['content_root'] == 'content'
    assert bundle_root(bundle, brief) == tmp_path / 'content'
    assert evidence_dir(bundle) == bundle / 'evidence'
    assert not (bundle / 'assets').exists()
    assert not (tmp_path / 'assets').exists()
    assert unrelated.read_text() == '# Software design\n'


def test_custom_content_root_persists_via_explicit_project_reference(tmp_path):
    result = run('init_project.py', tmp_path, '--project', 'example', '--content-root', 'editorial')
    assert result.returncode == 0, result.stderr
    bundle = create(tmp_path, '--project-file', 'editorial/project.md')
    brief = yaml.safe_load((bundle / 'brief.yaml').read_text())
    assert brief['project_file'] == 'project.md'
    assert bundle_root(bundle, brief) == tmp_path / 'editorial'
    assert bundle.parent.parent.parent == tmp_path / 'editorial'


def test_existing_content_project_keeps_workspace_root(tmp_path):
    (tmp_path / '.git').mkdir()
    config = tmp_path / 'projects/news/project.md'; config.parent.mkdir(parents=True)
    config.write_text('---\nschema_version: 3\nproject: news\n---\n')
    assert select_content_root(tmp_path) == tmp_path
    bundle = create(tmp_path, '--project-file', 'projects/news/project.md')
    assert yaml.safe_load((bundle / 'brief.yaml').read_text())['content_root'] == '.'


def test_legacy_state_stays_in_assets_and_alternate_state_is_refused(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'brief.yaml').write_text('schema_version: 3\n')
    state = tmp_path / 'assets/delivery.json'; state.write_text('{"status":"uncertain"}')
    assert evidence_dir(tmp_path) / 'delivery.json' == state
    (tmp_path / 'evidence').mkdir()
    (tmp_path / 'evidence/delivery.json').write_text('{}')
    with pytest.raises(ValueError, match='conflicts'):
        evidence_dir(tmp_path)
    assert state.read_text() == '{"status":"uncertain"}'


def test_new_layout_never_bypasses_legacy_pending_state(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/delivery.json').write_text('{"status":"submitting"}')
    with pytest.raises(ValueError, match='conflicts'):
        evidence_dir(tmp_path, {'layout_version': 2})


def test_evidence_and_content_roots_reject_escape(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + '-external'); outside.mkdir()
    (tmp_path / 'evidence').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='escapes'):
        evidence_dir(tmp_path, {'layout_version': 2})
    with pytest.raises(ValueError):
        select_content_root(tmp_path, '../outside')
    (tmp_path / 'content').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='escapes'):
        select_content_root(tmp_path, 'content')


def test_new_layout_local_preflight_resolves_images_from_content_root(tmp_path):
    (tmp_path / '.git').mkdir()
    bundle = create(tmp_path)
    brief = yaml.safe_load((bundle / 'brief.yaml').read_text())
    brief['source_policy'] = {'minimum': 1, 'primary_required': True}
    (bundle / 'brief.yaml').write_text(yaml.safe_dump(brief))
    media = tmp_path / 'content/assets/sample.png'; media.parent.mkdir(); media.write_bytes(b'image-fixture')
    (bundle / 'article.md').write_text('---\ntitle: 核验结果说明\n---\n\n本次依据单一官方来源，范围仅限所列结果。\n\n![结果](../../../assets/sample.png)\n')
    (bundle / 'sources.md').write_text('---\nsingle_source: true\nsources:\n  - id: S1\n    type: official\n    title: Result\n    url: https://example.com/result\n    checked_at: 2026-09-09T12:00:00+08:00\n    confidence: high\n    supports: [结果]\n---\n')
    before = (bundle / 'record.md').read_bytes()
    result = run('preflight.py', tmp_path, '--bundle', str(bundle), '--stage', 'render', '--json')
    assert result.returncode == 0, result.stdout + result.stderr
    assert (bundle / 'record.md').read_bytes() == before
    assert not (bundle / 'exports').exists()
    assert not (tmp_path / 'assets').exists()
