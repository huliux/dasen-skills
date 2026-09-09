"""Export a clean Git revision without history or filesystem-link traversal."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments])


@contextmanager
def source_snapshot(root: Path):
    if git(root, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("build requires a clean committed source, including untracked files")
    revision = git(root, "rev-parse", "HEAD").decode().strip()
    archive = git(root, "archive", "--format=tar", revision)
    with tempfile.TemporaryDirectory(prefix="dasen-source-") as directory:
        snapshot = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            for member in stream:
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("unsafe archive path")
                if not (member.isfile() or member.isdir()):
                    raise ValueError(f"source archive contains a link or special file: {member.name}")
                target = snapshot.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(stream.extractfile(member).read())
                    target.chmod(member.mode & 0o777)
        yield snapshot, revision


def write_manifest(root: Path, revision: str, kind: str) -> None:
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }
    (root / "artifact-manifest.json").write_text(json.dumps({
        "schema_version": 1, "kind": kind, "source_revision": revision,
        "files": files, "status": "built",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
