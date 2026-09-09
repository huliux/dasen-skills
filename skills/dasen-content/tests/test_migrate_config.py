from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_config.py"


def run(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def test_project_migration_previews_then_writes_once(tmp_path: Path) -> None:
    project = tmp_path / "project.md"
    original = """---
project: example
platform: wechat
system_brand: Northstar
channel:
  theme: mweb-indigo
  highlight: atom-one-light
hard_rules:
  asset_root: media
  cover_generation_model: image-provider/model
  cover_size: [2000, 850]
  cover_template_library: templates/covers
---

# Project
"""
    project.write_text(original, encoding="utf-8")
    preview = run(project)
    assert preview.returncode == 0
    assert "PREVIEW: no files changed" in preview.stdout
    assert project.read_text(encoding="utf-8") == original

    written = run(project, "--write")
    assert written.returncode == 0, written.stderr
    assert (tmp_path / "project.md.pre-v3.bak").read_text(encoding="utf-8") == original
    migrated = frontmatter(project)
    assert migrated["schema_version"] == 3
    assert migrated["brand"]["name"] == "Northstar"
    assert migrated["assets"]["root"] == "media"
    assert migrated["visual"]["generation"]["model"] == "image-provider/model"
    assert migrated["visual"]["defaults"] == {
        "body_style": "body-clean-editorial",
        "cover_style": "cover-clean-editorial",
    }
    assert migrated["visual"]["layout_library"] == "templates/covers"
    assert migrated["channels"]["wechat"] == {
        "theme": "dasen-default",
        "highlight": "dasen-light",
        "image_policy": "platform-upload",
    }
    assert migrated["writing"] == {"style_library": None}
    assert "scope" not in migrated and "platform" not in migrated and "channel" not in migrated
    assert run(project, "--write").returncode == 0


def test_brief_migration_generalizes_product_and_persona(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    brief.write_text(
        """id: 2026-09-07-example
system_brand: Northstar
status: draft
project_root: ../../..
image_policy: wenyan-upload
product_placement:
  bitbook:
    enabled: true
    mode: soft
    max_ratio: 0.05
    required_facts: [fact]
author_persona:
  enabled: true
  name: Example Author
  email: author@example.test
  uses: [contact]
""",
        encoding="utf-8",
    )
    assert run(brief, "--write").returncode == 0
    data = yaml.safe_load(brief.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["configuration"] == "standalone"
    assert data["workspace_root"] == "../../.."
    assert "project_root" not in data
    assert data["brand"]["name"] == "Northstar"
    assert data["product_placement"]["product_name"] == "Northstar"
    assert "bitbook" not in data["product_placement"]
    assert data["author_persona"]["contacts"] == ["author@example.test"]
    assert data["author_persona"]["profile_id"] is None
    assert data["image_policy"] == "platform-upload"
    assert data["visual"]["body"]["style_id"] == "body-clean-editorial"
    assert data["visual"]["cover"]["style_id"] == "cover-clean-editorial"


def test_migration_refuses_delivered_history(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    brief.write_text("id: old\nstatus: delivered\nsystem_brand: bitbook\n", encoding="utf-8")
    result = run(brief, "--write")
    assert result.returncode == 3
    assert "immutable" in result.stderr
    assert not (tmp_path / "brief.yaml.v1.bak").exists()


def test_project_persona_and_default_image_policy_move_to_owned_sections(tmp_path: Path) -> None:
    project = tmp_path / "project.md"
    project.write_text(
        """---
schema_version: 2
project: example
platform: [wechat, reddit]
brand: {name: null, aliases: []}
channel: {default_author: Lin}
author_persona:
  name: Lin
  contacts: [lin@example.test]
defaults:
  profile: practical
  image_policy: stable-cdn
---
""",
        encoding="utf-8",
    )
    assert run(project, "--write").returncode == 0
    data = frontmatter(project)
    assert data["authors"] == {
        "default": "default",
        "profiles": {"default": {"name": "Lin", "contacts": ["lin@example.test"]}},
    }
    assert data["channels"]["wechat"]["image_policy"] == "stable-cdn"
    assert data["channels"]["reddit"]["image_policy"] == "stable-cdn"
    assert "image_policy" not in data["defaults"]


def test_global_scope_requires_manual_relocation(tmp_path: Path) -> None:
    project = tmp_path / "project.md"
    project.write_text("---\nscope: global\nproject: example\n---\n", encoding="utf-8")
    result = run(project, "--write")
    assert result.returncode == 2
    assert "全局配置不再受支持" in result.stderr
    assert not (tmp_path / "project.md.pre-v3.bak").exists()
