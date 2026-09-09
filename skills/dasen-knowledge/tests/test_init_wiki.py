from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def run(name, cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd, capture_output=True, text=True)


def test_optional_wiki_initializes_in_selected_source_content_root(tmp_path):
    (tmp_path / '.git').mkdir()
    result = run('init_wiki.py', tmp_path)
    assert result.returncode == 0, result.stderr
    wiki = tmp_path / 'content/wiki'
    assert (wiki / 'schema.md').is_file()
    before = (wiki / 'schema.md').read_bytes()
    assert run('init_wiki.py', tmp_path).returncode != 0
    assert (wiki / 'schema.md').read_bytes() == before
    assert not (wiki / 'raw').exists()
    assert not (wiki / '.kb').exists()
    lint = run('wiki_lint.py', tmp_path, '--wiki', 'content/wiki', '--json')
    assert lint.returncode == 0, lint.stdout + lint.stderr


def test_explicit_missing_wiki_does_not_select_ancestor(tmp_path):
    assert run('init_wiki.py', tmp_path).returncode == 0
    child = tmp_path / 'child'; child.mkdir()
    result = run('wiki_lint.py', child, '--wiki', '.', '--json')
    assert result.returncode == 2
