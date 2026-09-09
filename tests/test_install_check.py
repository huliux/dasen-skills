"""A runtime artifact must prove local execution without claiming host discovery."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills/dasen-content/scripts"))
import build_public
import install_check
import install_dependencies
from install_integrity import inspect_distribution


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    target = tmp_path_factory.mktemp("distribution") / "install"
    build_public.build_snapshot(ROOT, "a" * 40, target, run_tests=False, kind="install")
    return target


def invoke(root, *arguments, cwd=None):
    script = root / "skills/dasen-content/scripts/install_check.py"
    result = subprocess.run(
        [sys.executable, "-B", str(script), "--json", *arguments],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PATH": "", "PYTHONIOENCODING": "utf-8"},
    )
    return result.returncode, json.loads(result.stdout)


def test_complete_artifact_requires_separate_discovery(artifact, tmp_path):
    code, report = invoke(artifact, cwd=tmp_path)
    assert code == 2
    assert report["local_readiness"] == "ready"
    assert report["native_discovery"]["status"] == "unverified"
    assert report["first_creation"]["status"] == "not-run"
    assert not list(tmp_path.iterdir())
    assert inspect_distribution(artifact)["status"] == "ready"


def test_explicit_local_check_retains_html_without_creating_articles(artifact, tmp_path):
    output = tmp_path / "检查输出"
    code, report = invoke(artifact, "--local-only", "--output", str(output), cwd=tmp_path)
    assert code == 0 and report["overall"] == "local-ready"
    html = (output / "sample-wechat.html").read_text(encoding="utf-8")
    assert "安装检查示例" in html and "<table" in html and "<script" not in html
    assert report["local_html"]["sha256"] == hashlib.sha256((output / "sample-wechat.html").read_bytes()).hexdigest()
    assert not (tmp_path / "writing").exists()


@pytest.mark.parametrize("relative", ["LICENSE", "ORIGIN.md", "requirements.txt",
                                      "skills/dasen-writing/SKILL.md"])
def test_missing_required_files_block_before_render(artifact, tmp_path, relative):
    target = tmp_path / "damaged"
    shutil.copytree(artifact, target)
    (target / relative).unlink()
    code, report = invoke(target, "--local-only", cwd=tmp_path)
    assert code == 1
    assert report["distribution"]["status"] == "blocked"
    assert len(report["distribution"]["errors"]) == len(set(report["distribution"]["errors"]))
    assert report["local_html"]["status"] == "not-run"


def test_tampered_and_unlisted_files_are_rejected(artifact, tmp_path):
    target = tmp_path / "tampered"
    shutil.copytree(artifact, target)
    (target / "LICENSE").write_text("changed", encoding="utf-8")
    (target / "extra.py").write_text("raise RuntimeError('unused')", encoding="utf-8")
    report = inspect_distribution(target)
    assert report["status"] == "blocked"
    assert any("hash mismatch: LICENSE" in e for e in report["errors"])
    assert any("unlisted artifact file: extra.py" in e for e in report["errors"])


@pytest.mark.parametrize("bad_path", ["../outside", "/outside", "C:/outside", "a\\b", "a/../b"])
def test_manifest_cannot_escape_root(artifact, tmp_path, bad_path):
    target = tmp_path / "malformed"
    shutil.copytree(artifact, target)
    path = target / "artifact-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["files"][bad_path] = "a" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert inspect_distribution(target)["status"] == "blocked"


@pytest.mark.parametrize("value", [[], {}, {"schema_version": 9}, {"files": []}])
def test_invalid_manifest_is_structured_failure(artifact, tmp_path, value):
    target = tmp_path / "malformed"
    shutil.copytree(artifact, target)
    (target / "artifact-manifest.json").write_text(json.dumps(value), encoding="utf-8")
    assert inspect_distribution(target)["status"] == "blocked"


@pytest.mark.parametrize("name", ["pillow", "markdown-it-py", "pyyaml", "mdurl", "packaging"])
def test_missing_or_wrong_version_blocks(name, monkeypatch):
    original = install_dependencies.metadata.version
    monkeypatch.setattr(install_dependencies.metadata, "version",
                        lambda package: "0.0.1" if package.lower() == name else original(package))
    report = install_dependencies.inspect_dependencies(ROOT / "requirements.txt")
    assert report["status"] == "blocked"
    assert report["packages"][name]["status"] == "blocked"


def test_import_failure_is_not_version_success(monkeypatch):
    original = importlib.import_module
    def importing(name):
        if name == "PIL":
            raise ImportError("broken binary fixture")
        return original(name)
    monkeypatch.setattr(install_dependencies.importlib, "import_module", importing)
    assert install_dependencies.inspect_dependencies(ROOT / "requirements.txt")["status"] == "blocked"


def test_windows_marker_requires_timezone_data():
    requirements = install_dependencies.locked_requirements(
        ROOT / "requirements.txt", {"sys_platform": "win32"})
    assert "tzdata" in {r.name for r in requirements}
    requirements = install_dependencies.locked_requirements(
        ROOT / "requirements.txt", {"sys_platform": "darwin"})
    assert "tzdata" not in {r.name for r in requirements}


@pytest.mark.parametrize("text", ["pillow>=11\n", "pillow==12.3.0\n", "# empty\n"])
def test_unlocked_or_incomplete_requirements_fail(tmp_path, text):
    path = tmp_path / "requirements.txt"
    path.write_text(text, encoding="utf-8")
    assert install_dependencies.inspect_dependencies(path)["status"] == "blocked"


def test_output_is_never_overwritten(artifact, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    saved = output / "keep.txt"
    saved.write_text("user data", encoding="utf-8")
    code, _ = invoke(artifact, "--output", str(output))
    assert code == 1
    assert saved.read_text(encoding="utf-8") == "user data"


def test_render_failure_blocks_even_with_dependencies(monkeypatch, artifact, tmp_path):
    monkeypatch.setattr(install_check, "local_conversion",
                        lambda root, output: {"status": "blocked", "error": "fixture renderer failure"})
    assert install_check.report(artifact, tmp_path)["local_readiness"] == "blocked"
