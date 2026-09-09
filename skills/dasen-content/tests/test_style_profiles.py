from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
INIT_CONTENT = SCRIPTS / "init_content.py"
sys.path.insert(0, str(SCRIPTS))
from style_profiles import (  # noqa: E402
    BUILTIN_CATALOG,
    available_styles,
    load_catalog,
    resolve_style,
    save_project_style,
)


EXPECTED_BUILTINS = {
    "practical",
    "explainer",
    "casual",
    "flash",
    "tutorial",
    "human-natural",
    "energetic-tech-commentary",
    "concise-business-commentary",
}


def dump_catalog(path: Path, styles: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "styles": styles}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def style(label: str = "Project style", *, kind: str = "project-authored") -> dict:
    return {
        "label": label,
        "revision": 1,
        "summary": "A project-owned writing style.",
        "source": {"kind": kind, "sample_refs": [], "captured_at": None},
        "voice": ["direct"],
        "rhythm": ["varied"],
        "structure": ["result then explanation"],
        "evidence": ["claims near sources"],
        "avoid": ["fabricated experience"],
    }


def test_builtin_catalog_has_stable_public_style_ids(tmp_path: Path) -> None:
    styles = available_styles({}, tmp_path)
    assert set(styles) == EXPECTED_BUILTINS
    assert all(item["source"]["kind"] == "dasen-original" for item in styles.values())


def test_resolution_is_brief_then_series_then_project_then_fallback(tmp_path: Path) -> None:
    catalog = tmp_path / "styles.yaml"
    dump_catalog(catalog, {"project-style": style()})
    project = {
        "writing": {"style_library": "styles.yaml"},
        "defaults": {"profile": "project-style"},
    }
    series = {"profile": "casual"}

    assert resolve_style(
        requested="tutorial", project_config=project, series_config=series,
        project_root=tmp_path, journey="material",
    )["selected_from"] == "brief"
    assert resolve_style(
        requested=None, project_config=project, series_config=series,
        project_root=tmp_path, journey="material",
    )["id"] == "casual"
    assert resolve_style(
        requested=None, project_config=project, series_config={},
        project_root=tmp_path, journey="breaking",
    )["id"] == "project-style"
    fallback = resolve_style(
        requested=None, project_config={}, series_config={},
        project_root=tmp_path, journey="breaking",
    )
    assert fallback["id"] == "flash" and fallback["selected_from"] == "fallback"


def test_project_style_is_compiled_as_frozen_brief_snapshot(tmp_path: Path) -> None:
    dump_catalog(tmp_path / "styles.yaml", {"project-style": style("My style")})
    project = {
        "schema_version": 3,
        "project": "example-project",
        "brand": {"name": None, "aliases": []},
        "channels": {},
        "authors": {"default": None, "profiles": {}},
        "writing": {"style_library": "styles.yaml"},
        "defaults": {"profile": "project-style", "language": "zh-CN"},
    }
    (tmp_path / "project.md").write_text(
        "---\n" + yaml.safe_dump(project, allow_unicode=True, sort_keys=False) + "---\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable, str(INIT_CONTENT),
            "--id", "2026-09-08-style-test", "--journey", "material",
            "--length", "quick", "--method", "original",
            "--objective", "test", "--audience", "reader", "--deliverable", "article",
        ],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-08/style-test/brief.yaml").read_text())
    assert brief["profile"] == "project-style"
    assert brief["style_profile"]["id"] == "project-style"
    assert brief["style_profile"]["origin"] == "project:styles.yaml"
    assert brief["style_profile"]["selected_from"] == "project"


def test_project_catalog_cannot_override_builtin_or_escape_workspace(tmp_path: Path) -> None:
    dump_catalog(tmp_path / "collision.yaml", {"practical": style()})
    with pytest.raises(ValueError, match="不得覆盖"):
        available_styles({"writing": {"style_library": "collision.yaml"}}, tmp_path)

    outside = tmp_path.parent / f"{tmp_path.name}-outside-styles.yaml"
    dump_catalog(outside, {"outside": style()})
    with pytest.raises(ValueError, match="项目根目录内"):
        available_styles({"writing": {"style_library": "../outside-styles.yaml"}}, tmp_path)


def test_sample_derived_style_requires_source_receipts(tmp_path: Path) -> None:
    derived = style(kind="sample-derived")
    dump_catalog(tmp_path / "derived.yaml", {"derived": derived})
    with pytest.raises(ValueError, match="sample_refs"):
        load_catalog(tmp_path / "derived.yaml", origin="project:derived.yaml")

    derived["source"]["sample_refs"] = ["samples/one.md", "samples/two.md", "samples/three.md"]
    derived["source"]["conflicts"] = ["开头有两种不同节奏"]
    derived["source"]["captured_at"] = "2026-09-08"
    dump_catalog(tmp_path / "derived.yaml", {"derived": derived})
    loaded = load_catalog(tmp_path / "derived.yaml", origin="project:derived.yaml")
    assert loaded["derived"]["source"]["conflicts"] == ["开头有两种不同节奏"]


def test_confirmed_sample_style_is_written_only_to_project_library(tmp_path: Path) -> None:
    for name in ("one.md", "two.md", "three.md"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    project = {"writing": {"style_library": "private/writing-styles.yaml"}}

    saved = save_project_style(
        project_config=project,
        project_root=tmp_path,
        style_id="sample-style",
        label="Sample style",
        summary="Stable traits from authorized project samples.",
        source_kind="sample-derived",
        sample_refs=["one.md", "two.md", "three.md"],
        conflicts=["two openings differ"],
        captured_at="2026-09-08",
        voice=["direct"],
        rhythm=["varied"],
        structure=["result first"],
        evidence=["claims near sources"],
        avoid=["copied phrases"],
        confirmed=True,
    )

    assert saved["revision"] == 1
    assert (tmp_path / "private/writing-styles.yaml").is_file()
    assert available_styles(project, tmp_path)["sample-style"]["origin"] == "project:private/writing-styles.yaml"


def test_project_style_write_requires_confirmation_and_never_overwrites_builtin(tmp_path: Path) -> None:
    project = {"writing": {"style_library": "styles.yaml"}}
    common = dict(
        project_config=project,
        project_root=tmp_path,
        label="Project style",
        summary="A project-owned style.",
        source_kind="project-authored",
        sample_refs=[],
        conflicts=[],
        captured_at="2026-09-08",
        voice=["direct"], rhythm=["varied"], structure=["result first"],
        evidence=["claims near sources"], avoid=["fabrication"],
    )
    with pytest.raises(ValueError, match="用户确认"):
        save_project_style(style_id="new-style", confirmed=False, **common)
    with pytest.raises(ValueError, match="内置 Style ID"):
        save_project_style(style_id="practical", confirmed=True, **common)
    assert not (tmp_path / "styles.yaml").exists()


def test_project_style_revision_is_explicit_and_monotonic(tmp_path: Path) -> None:
    project = {"writing": {"style_library": "styles.yaml"}}
    fields = dict(
        project_config=project,
        project_root=tmp_path,
        style_id="house-style",
        label="House style",
        summary="Project house style.",
        source_kind="project-authored",
        sample_refs=[], conflicts=[], captured_at="2026-09-08",
        voice=["direct"], rhythm=["varied"], structure=["result first"],
        evidence=["claims near sources"], avoid=["fabrication"], confirmed=True,
    )
    save_project_style(**fields)
    with pytest.raises(ValueError, match="已存在"):
        save_project_style(**fields)
    revised = save_project_style(expected_revision=1, **{**fields, "summary": "Revised house style."})
    assert revised["revision"] == 2


def test_project_style_writer_refuses_the_central_builtin_catalog(tmp_path: Path) -> None:
    project = {"writing": {"style_library": str(BUILTIN_CATALOG)}}
    with pytest.raises(ValueError, match="中央内置风格库"):
        save_project_style(
            project_config=project, project_root=tmp_path, style_id="unsafe",
            label="Unsafe", summary="Must not write centrally.", source_kind="project-authored",
            sample_refs=[], conflicts=[], captured_at="2026-09-08", voice=["direct"],
            rhythm=["varied"], structure=["result first"], evidence=["sources"],
            avoid=["fabrication"], confirmed=True,
        )
