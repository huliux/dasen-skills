from pathlib import Path
import subprocess
import sys

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/migrate_namespace.py"


def run(root, path="brief.yaml", *options):
    return subprocess.run([sys.executable, str(SCRIPT), path, "--workspace", str(root),
                           *options], capture_output=True, text=True)


def test_migrates_only_technical_values_and_preserves_body(tmp_path):
    path = tmp_path / "brief.yaml"
    original = """---
status: drafted
brand: {name: Bitbook}
product_placement: {product_name: bitbook, required_facts: [bitbook-original]}
channel: {theme: bitbook-default, highlight: bitbook-light, default_author: Example Author}
style_profile: {source: {kind: bitbook-original}, voice: [bitbook-original]}
visual: {body: {style: {source: {kind: bitbook-original}}}}
---
Keep Bitbook product facts and this prose unchanged.
"""
    path.write_text(original)
    assert run(tmp_path).returncode == 0
    assert path.read_text() == original
    assert run(tmp_path, "brief.yaml", "--write").returncode == 0
    changed = path.read_text()
    data = yaml.safe_load(changed.split("---", 2)[1])
    assert data["brand"]["name"] == "Bitbook"
    assert data["product_placement"]["required_facts"] == ["bitbook-original"]
    assert data["channel"] == dict(theme="dasen-default", highlight="dasen-light", default_author="Example Author")
    assert data["style_profile"]["source"]["kind"] == "dasen-original"
    assert data["style_profile"]["voice"] == ["bitbook-original"]
    assert data["visual"]["body"]["style"]["source"]["kind"] == "dasen-original"
    assert changed.endswith(original.split("---", 2)[2])
    assert path.with_name("brief.yaml.pre-dasen.bak").read_text() == original
    assert run(tmp_path, "brief.yaml", "--write").returncode == 0


def test_history_and_existing_backup_are_protected(tmp_path):
    path = tmp_path / "brief.yaml"
    original = "status: delivered\nchannel: {theme: bitbook-default}\n"
    path.write_text(original)
    assert run(tmp_path, "brief.yaml", "--write").returncode == 2
    assert path.read_text() == original
    path.write_text(original.replace("delivered", "drafted"))
    backup = tmp_path / "brief.yaml.pre-dasen.bak"
    backup.write_text("previous backup")
    assert run(tmp_path, "brief.yaml", "--write").returncode == 2
    assert backup.read_text() == "previous backup"
    assert "bitbook-default" in path.read_text()


def test_project_and_catalog_values_are_supported(tmp_path):
    path = tmp_path / "project.md"
    path.write_text("channels: {wechat: {theme: bitbook-default}}\nstyles: {practical: {source: {kind: bitbook-original}}}\n")
    assert run(tmp_path, "project.md", "--write").returncode == 0
    data = yaml.safe_load(path.read_text())
    assert data["channels"]["wechat"]["theme"] == "dasen-default"
    assert data["styles"]["practical"]["source"]["kind"] == "dasen-original"


def test_escape_and_symlink_inputs_are_rejected(tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text("channel: {theme: bitbook-default}\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert run(workspace, "../outside.yaml", "--write").returncode == 2
    try:
        (workspace / "brief.yaml").symlink_to(outside)
    except OSError:
        return  # Windows without symlink privileges still checks lexical escape.
    assert run(workspace, "brief.yaml", "--write").returncode == 2
    assert outside.read_text() == "channel: {theme: bitbook-default}\n"


def test_backup_preserves_original_crlf_bytes(tmp_path):
    path = tmp_path / "project.md"
    original = b"---\r\nchannel: {theme: bitbook-default}\r\n---\r\nOriginal body.\r\n"
    path.write_bytes(original)
    assert run(tmp_path, "project.md", "--write").returncode == 0
    assert (tmp_path / "project.md.pre-dasen.bak").read_bytes() == original
