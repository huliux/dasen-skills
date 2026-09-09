"""Package a verified installation tree without changing its manifest or payload."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile

from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent


def package(install: Path, output: Path, tag: str, revision: str) -> Path:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-alpha\.\d+)?", tag):
        raise ValueError("expected a fixed release tag, such as v0.1.0-alpha.1")
    if output.exists():
        raise ValueError("output must not exist")
    manifest = json.loads((install / "artifact-manifest.json").read_text())
    if manifest.get("kind") != "install" or manifest.get("source_revision") != revision:
        raise ValueError("installation manifest does not identify the release commit")
    files = manifest["files"]
    actual = set()
    for path in install.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("installation contains a link or special file")
        if path.is_file():
            actual.add(path.relative_to(install).as_posix())
    if actual != set(files) | {"artifact-manifest.json"}:
        raise ValueError("installation inventory differs from its manifest")
    for name, digest in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe manifest path")
        if hashlib.sha256((install / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"installation checksum mismatch: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dasen-release-", dir=output.parent) as work:
        staged = Path(work) / "assets"
        staged.mkdir()
        stem = f"dasen-skills-{tag[1:]}"
        archive = staged / f"{stem}-install.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stream:
            for name in sorted(actual):
                path = install / name
                info = zipfile.ZipInfo(f"{stem}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100000 | (path.stat().st_mode & 0o777)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                stream.writestr(info, path.read_bytes())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (staged / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
        staged.rename(output)
    return output / archive.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    version = re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(), re.M)
    if not version or Version(args.tag) != Version(version.group(1)):
        raise ValueError("tag must match the project version")
    if subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"]).strip():
        raise ValueError("release source must be clean and committed")
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    print(package(args.install.resolve(), args.output.resolve(), args.tag, revision))


if __name__ == "__main__":
    main()
