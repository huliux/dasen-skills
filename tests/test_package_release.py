"""A release archive must preserve and authenticate exactly the built payload."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

spec = importlib.util.spec_from_file_location("package_release", Path(__file__).parents[1] / "scripts/package_release.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def artifact(tmp_path):
    root = tmp_path / "install"
    root.mkdir()
    (root / "prepare-macos.sh").write_text("#!/bin/sh\nexit 0\n")
    (root / "prepare-macos.sh").chmod(0o755)
    (root / "artifact-manifest.json").write_text(json.dumps({
        "kind": "install", "source_revision": "commit",
        "files": {"prepare-macos.sh": hashlib.sha256((root / "prepare-macos.sh").read_bytes()).hexdigest()},
    }))
    return root


def test_archive_round_trip_and_reproducibility(artifact, tmp_path):
    first = module.package(artifact, tmp_path / "first", "v0.1.0-alpha.1", "commit")
    second = module.package(artifact, tmp_path / "second", "v0.1.0-alpha.1", "commit")
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / "SHA256SUMS").read_text() == f"{hashlib.sha256(first.read_bytes()).hexdigest()}  {first.name}\n"
    with zipfile.ZipFile(first) as archive:
        for info in archive.infolist():
            name = info.filename.split("/", 1)[1]
            assert archive.read(info) == (artifact / name).read_bytes()
        assert archive.getinfo("dasen-skills-0.1.0-alpha.1/prepare-macos.sh").external_attr >> 16 & 0o777 == (artifact / "prepare-macos.sh").stat().st_mode & 0o777


@pytest.mark.parametrize("change", ["tamper", "extra", "link", "wrong-revision"])
def test_refuses_unverified_payload(artifact, tmp_path, change):
    if change == "tamper":
        (artifact / "prepare-macos.sh").write_text("modified")
    elif change == "extra":
        (artifact / "private.txt").write_text("not in manifest")
    elif change == "link":
        (artifact / "prepare-macos.sh").unlink()
        try:
            (artifact / "prepare-macos.sh").symlink_to(tmp_path / "outside")
        except OSError:
            pytest.skip("native symlink creation is unavailable")
    with pytest.raises(ValueError):
        module.package(artifact, tmp_path / "release", "v0.1.0-alpha.1", "other" if change == "wrong-revision" else "commit")
    assert not (tmp_path / "release").exists()
