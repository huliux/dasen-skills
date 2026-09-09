"""Release candidates must bind one clean revision and preserve the public boundary."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_public
import export_runtime
from source_snapshot import source_snapshot


def git(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def repository(root):
    git(root, "init", "-q")
    git(root, "config", "user.name", "Example")
    git(root, "config", "user.email", "example@example.com")
    (root / "tracked.txt").write_text("original")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-qm", "test: fixture")


def test_snapshot_is_revision_bound_and_excludes_git(tmp_path):
    repository(tmp_path)
    with source_snapshot(tmp_path) as (snapshot, revision):
        (tmp_path / "tracked.txt").write_text("later edit")
        assert (snapshot / "tracked.txt").read_text() == "original"
        assert not (snapshot / ".git").exists()
        assert revision == git(tmp_path, "rev-parse", "HEAD")


@pytest.mark.parametrize("path", ["tracked.txt", "untracked.txt"])
def test_dirty_source_is_refused(tmp_path, path):
    repository(tmp_path)
    (tmp_path / path).write_text("uncommitted")
    with pytest.raises(ValueError, match="clean committed"):
        with source_snapshot(tmp_path):
            pass


def test_scanner_preserves_public_identity_boundary():
    assert not build_public.scan_text(Path("README.md"), "dasen / 大森")
    assert build_public.scan_text(Path("skills/dasen-content/template.md"), "author: 大森")
    assert not build_public.scanner_contract_errors()


def test_broken_navigation_is_rejected(tmp_path):
    (tmp_path / "README.md").write_text("[Missing](docs/missing.md)")
    assert build_public.validate_document_links(tmp_path)


def test_runtime_lock_matches_canonical_uv_export():
    export_runtime.verify(Path(__file__).resolve().parents[1])


def test_stale_runtime_lock_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(export_runtime, "exported", lambda root: "current")
    with pytest.raises(ValueError, match="stale"):
        export_runtime.verify(tmp_path)


def test_changed_dependency_bounds_require_relocking(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ("pyproject.toml", "uv.lock", "requirements.txt"):
        shutil.copyfile(root / name, tmp_path / name)
    project = tmp_path / "pyproject.toml"
    project.write_text(project.read_text(encoding="utf-8").replace(
        "packaging>=26,<27", "packaging>=27,<28"), encoding="utf-8")
    with pytest.raises(ValueError, match="locked runtime requirements"):
        export_runtime.verify(tmp_path)


def test_source_and_runtime_outputs_have_distinct_contents(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in ("dasen-content", "dasen-video"):
        directory = source / "skills" / name
        (directory / "tests").mkdir(parents=True)
        (directory / "tests/test_stub.py").write_text("def test_stub(): pass\n")
        (directory / "SKILL.md").write_text("# Fixture\n")
    (source / "LICENSE").write_text("MIT fixture")
    (source / "AGENTS.md").write_text("# Fixture engineering")
    (source / "README.md").write_text("[Install](docs/zh-CN/installation.md)\n")
    (source / "docs/zh-CN").mkdir(parents=True)
    (source / "docs/zh-CN/installation.md").write_text("# User installation\n")
    (source / "docs/spec.md").write_text("# Engineering specification\n")
    (source / "private-record.md").write_text("private fixture")
    (source / "public-source.yaml").write_text(
        "files: [LICENSE, AGENTS.md, README.md, docs/zh-CN/installation.md, docs/spec.md]\n")
    registry = {"skills": {"dasen-content": {"routes_to": ["dasen-video"]}, "dasen-video": {}}}
    packs = {"public_subset": {"skills": ["dasen-content"], "excludes": ["dasen-video"],
              "distribution_files": ["LICENSE", "README.md", "docs/zh-CN/installation.md"]}, "packs": {}}
    for name, data in (("registry.yaml", registry), ("packs.yaml", packs)):
        (source / name).write_text(yaml.safe_dump(data))
    for kind in ("source", "install"):
        output = tmp_path / kind / "output"
        build_public.build_snapshot(source, "fixed-revision", output, run_tests=False, kind=kind)
        assert not (output / "private-record.md").exists()
        assert not (output / "skills/dasen-video").exists()
        assert (output / "AGENTS.md").exists() == (kind == "source")
        assert (output / "README.md").read_bytes() == (source / "README.md").read_bytes()
        assert (output / "docs/zh-CN/installation.md").is_file()
        assert (output / "docs/spec.md").exists() == (kind == "source")
        assert (output / "skills/dasen-content/tests").exists() == (kind == "source")
        assert yaml.safe_load((output / "registry.yaml").read_text())["skills"]["dasen-content"]["routes_to"] == []
        manifest = json.loads((output / "artifact-manifest.json").read_text())
        assert manifest["source_revision"] == "fixed-revision"
        assert manifest["kind"] == kind
        for path, digest in manifest["files"].items():
            assert hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
        if kind == "install":
            (output / "docs/unselected.md").write_text("Unselected document")
            assert any("unlisted installation document" in error for error in
                       build_public.validate_tree(output, ["dasen-content"], kind))
    (tmp_path / "outside.txt").write_text("Outside the selected source")
    for relative in ("../outside.txt", str(tmp_path / "outside.txt")):
        packs["public_subset"]["distribution_files"] = [relative]
        (source / "packs.yaml").write_text(yaml.safe_dump(packs))
        with pytest.raises(ValueError, match="installation selection must stay within"):
            build_public.build_snapshot(source, "fixed-revision", tmp_path / "refused",
                                        run_tests=False, kind="install")
